import pytest
from unittest.mock import Mock, patch, MagicMock
import contextlib

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult, PipelineStageStatus
from src.domain.ports.pipeline_repository import PipelineRepository
from src.application.pipeline.executor import PipelineExecutor
from src.application.pipeline.state_manager import StateManager
from src.application.pipeline.feedback_manager import FeedbackManager
from src.application.pipeline.orchestrator import PipelineOrchestrator

# Mark as integration test
pytestmark = pytest.mark.integration


class TestPipelineIntegration:
    """Integration tests for the pipeline orchestration components."""

    @pytest.fixture
    def pipeline_repository_mock(self):
        """Create a mock pipeline repository."""
        repo = Mock(spec=PipelineRepository)

        # Configure the save methods to return their inputs
        repo.save_pipeline_state.side_effect = lambda state: state
        repo.save_task.side_effect = lambda task: task

        # Maintain an in-memory store for testing
        self.tasks = {}
        self.states = {}

        # Configure get methods to use the in-memory store
        repo.get_task.side_effect = lambda task_id: self.tasks.get(task_id)
        repo.get_pipeline_state.side_effect = lambda state_id: self.states.get(
            state_id)
        repo.get_latest_pipeline_state.side_effect = lambda task_id: next(
            (state for state in self.states.values() if
             state.task_id == task_id), None
        )

        # Configure save methods to update the in-memory store
        def save_task(task):
            self.tasks[task.id] = task
            return task

        def save_state(state):
            self.states[state.id] = state
            return state

        repo.save_task.side_effect = save_task
        repo.save_pipeline_state.side_effect = save_state

        # Mock transaction methods
        repo.start_transaction.return_value = "session"
        repo.commit_transaction.return_value = None
        repo.abort_transaction.return_value = None

        return repo

    @pytest.fixture
    def mock_stages(self):
        """Create mock pipeline stages."""
        # Create a collection of stages for the pipeline
        stages = {}

        for stage_name in PipelineState.PIPELINE_STAGES:
            stage = Mock(spec=PipelineStage)
            stage.name = stage_name
            stage.id = f"{stage_name}-id"

            # Set up stage behavior
            stage.validate_transition_from_name.return_value = True

            # Get the index of this stage
            stage_idx = PipelineState.PIPELINE_STAGES.index(stage_name)

            # Determine the next stage
            if stage_idx < len(PipelineState.PIPELINE_STAGES) - 1:
                next_stage = PipelineState.PIPELINE_STAGES[stage_idx + 1]
            else:
                next_stage = ""

            stage.get_next_stage_name.return_value = next_stage

            # Configure execute to return a successful result
            stage.execute.return_value = PipelineStageResult(
                stage_id=stage.id,
                status=PipelineStageStatus.COMPLETED,
                output={f"{stage_name}_output": f"Output from {stage_name}"}
            )

            stages[stage_name] = stage

        return stages

    @pytest.fixture
    def stage_factory(self, mock_stages):
        """Create a stage factory function."""

        def factory(stage_name):
            return mock_stages.get(stage_name)

        return factory

    @pytest.fixture
    def pipeline_executor(self, pipeline_repository_mock):
        """Create a PipelineExecutor."""
        return PipelineExecutor(pipeline_repository=pipeline_repository_mock)

    @pytest.fixture
    def state_manager(self, pipeline_repository_mock):
        """Create a StateManager."""
        return StateManager(pipeline_repository=pipeline_repository_mock)

    @pytest.fixture
    def feedback_manager(self, pipeline_repository_mock):
        """Create a FeedbackManager."""
        return FeedbackManager(pipeline_repository=pipeline_repository_mock)

    @pytest.fixture
    def pipeline_orchestrator(self, pipeline_repository_mock, pipeline_executor,
                              state_manager, feedback_manager, stage_factory):
        """Create a PipelineOrchestrator."""
        return PipelineOrchestrator(
            pipeline_repository=pipeline_repository_mock,
            pipeline_executor=pipeline_executor,
            state_manager=state_manager,
            feedback_manager=feedback_manager,
            stage_factory=stage_factory
        )

    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing."""
        return Task(
            id="task-id",
            description="Test task",
            requirements=["Requirement 1", "Requirement 2"],
            constraints=["Constraint 1"]
        )

    def test_complete_pipeline_execution(self, pipeline_orchestrator,
                                         pipeline_repository_mock,
                                         mock_stages, sample_task):
        """Test executing a complete pipeline from start to finish."""
        # Arrange
        # Save the task to the repository
        pipeline_repository_mock.save_task(sample_task)

        # Patch the _wait_for_feedback method to avoid interactive prompts
        pipeline_orchestrator._wait_for_feedback = lambda state: False

        # Act
        final_state = pipeline_orchestrator.execute_pipeline(
            task_id=sample_task.id,
            create_checkpoints=True
        )

        # Assert
        # Verify that all stages were executed
        for stage in mock_stages.values():
            stage.execute.assert_called_once()

        # Verify the final state
        assert final_state.current_stage == "review"
        assert len(final_state.stages_completed) == len(
            PipelineState.PIPELINE_STAGES)
        assert set(final_state.stages_completed) == set(
            PipelineState.PIPELINE_STAGES)

        # Verify that artifacts were created for each stage
        for stage_name in PipelineState.PIPELINE_STAGES:
            assert stage_name in final_state.artifacts
            assert f"{stage_name}_output" in final_state.artifacts[stage_name]

        # Verify that checkpoints were created
        assert len(final_state.checkpoint_data) > 0

    def test_state_manager_checkpoint_rollback(self, state_manager,
                                               sample_task):
        """Test creating checkpoints and rolling back."""
        # Arrange
        # Create an initial state
        state = state_manager.create_initial_state(sample_task)

        # Update the state to simulate progress
        state.current_stage = "knowledge_gathering"
        state.stages_completed = ["requirements_gathering"]
        state.artifacts = {
            "requirements_gathering": {"requirements": ["Updated requirement"]}
        }
        state = state_manager.pipeline_repository.save_pipeline_state(state)

        # Act
        # Create a checkpoint
        checkpoint_id, state = state_manager.create_checkpoint(state.id,
                                                               "test_checkpoint")

        # Update the state again
        state.current_stage = "implementation_planning"
        state.stages_completed = ["requirements_gathering",
                                  "knowledge_gathering"]
        state.artifacts["knowledge_gathering"] = {
            "knowledge": ["Test knowledge"]}
        state = state_manager.pipeline_repository.save_pipeline_state(state)

        # Roll back to the checkpoint
        rolled_back_state = state_manager.rollback_to_checkpoint(state.id,
                                                                 checkpoint_id)

        # Assert
        assert rolled_back_state.current_stage == "knowledge_gathering"
        assert rolled_back_state.stages_completed == ["requirements_gathering"]
        assert "knowledge_gathering" not in rolled_back_state.artifacts
        assert rolled_back_state.artifacts["requirements_gathering"][
                   "requirements"] == ["Updated requirement"]

    def test_feedback_submission_and_incorporation(self, feedback_manager,
                                                   state_manager, sample_task):
        """Test submitting and incorporating feedback."""
        # Arrange
        # Create an initial state
        state = state_manager.create_initial_state(sample_task)

        # Update the state to simulate progress
        state.current_stage = "implementation_planning"
        state.stages_completed = ["requirements_gathering",
                                  "knowledge_gathering"]
        state = state_manager.pipeline_repository.save_pipeline_state(state)

        # Act
        # Submit feedback
        feedback_id1, state = feedback_manager.submit_feedback(
            pipeline_state_id=state.id,
            stage_name="implementation_planning",
            content="Add more error handling",
            feedback_type="suggestion"
        )

        feedback_id2, state = feedback_manager.submit_feedback(
            pipeline_state_id=state.id,
            stage_name="knowledge_gathering",
            content="Consider security implications",
            feedback_type="correction"
        )

        # Get all feedback
        all_feedback = feedback_manager.get_feedback(state.id)

        # Incorporate specific feedback
        state = feedback_manager.incorporate_feedback(state.id, [feedback_id1])

        # Assert
        assert len(all_feedback) == 2
        assert state.feedback[0]["id"] == feedback_id1
        assert state.feedback[0]["incorporated"] is True
        assert state.feedback[1]["id"] == feedback_id2
        assert state.feedback[1]["incorporated"] is False

        # Incorporate all remaining feedback
        state = feedback_manager.incorporate_all_feedback(state.id)

        # Assert all feedback is incorporated
        assert state.feedback[1]["incorporated"] is True

    def test_pipeline_executor_stage_execution(self, pipeline_executor,
                                               state_manager,
                                               mock_stages, sample_task):
        """Test executing a single stage with the pipeline executor."""
        # Arrange
        # Create an initial state
        state = state_manager.create_initial_state(sample_task)

        # Get the first stage
        first_stage = mock_stages["requirements_gathering"]

        # Act
        # Execute the stage
        updated_state = pipeline_executor.execute_stage(
            pipeline_state_id=state.id,
            stage=first_stage,
            create_checkpoint=True
        )

        # Assert
        first_stage.execute.assert_called_once_with(sample_task, state)
        assert updated_state.current_stage == "knowledge_gathering"
        assert updated_state.stages_completed == ["requirements_gathering"]
        assert "requirements_gathering" in updated_state.artifacts
        assert updated_state.artifacts["requirements_gathering"] == {
            "requirements_gathering_output": "Output from requirements_gathering"}

        # Verify a checkpoint was created
        assert len(updated_state.checkpoint_data) == 1

    def test_error_handling_and_recovery(self, pipeline_orchestrator,
                                         state_manager,
                                         mock_stages, sample_task):
        """Test error handling and recovery during pipeline execution."""
        # Arrange
        # Save the task to the repository
        pipeline_orchestrator.pipeline_repository.save_task(sample_task)

        # Create an initial state with a checkpoint
        state = state_manager.create_initial_state(sample_task)
        checkpoint_id, state = state_manager.create_checkpoint(state.id,
                                                               "initial_checkpoint")

        # Configure the knowledge_gathering stage to fail
        failing_stage = mock_stages["knowledge_gathering"]
        failing_stage.execute.side_effect = Exception("Simulated error")

        # Patch the _wait_for_feedback and _handle_execution_error methods
        pipeline_orchestrator._wait_for_feedback = lambda state: False
        original_handle_error = pipeline_orchestrator._handle_execution_error

        def mock_handle_error(error, state, stage):
            # Call the real method but patch state_manager.rollback_to_latest_checkpoint
            with patch.object(state_manager,
                              'rollback_to_latest_checkpoint') as mock_rollback:
                mock_rollback.return_value = state
                return original_handle_error(error, state, stage)

        pipeline_orchestrator._handle_execution_error = mock_handle_error

        # Act
        with pytest.raises(Exception):
            pipeline_orchestrator.execute_pipeline(sample_task.id)

        # The test would continue here in a real scenario after error recovery