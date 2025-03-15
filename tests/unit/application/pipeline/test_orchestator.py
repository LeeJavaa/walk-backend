import pytest
from unittest.mock import Mock, patch, MagicMock, call

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult, PipelineStageStatus
from src.domain.ports.pipeline_repository import PipelineRepository
from src.application.pipeline.executor import PipelineExecutor
from src.application.pipeline.state_manager import StateManager
from src.application.pipeline.feedback_manager import FeedbackManager
from src.application.pipeline.orchestrator import PipelineOrchestrator


class TestPipelineOrchestrator:
    """Unit tests for PipelineOrchestrator."""

    @pytest.fixture
    def pipeline_repository_mock(self):
        """Create a mock pipeline repository."""
        repo = Mock(spec=PipelineRepository)

        # Configure the mock to return the state it was given to save
        repo.save_pipeline_state.side_effect = lambda state: state
        repo.get_task.side_effect = lambda task_id: Task(
            id=task_id,
            description="Test task",
            requirements=["Requirement 1"],
            constraints=[]
        )

        return repo

    @pytest.fixture
    def pipeline_executor_mock(self):
        """Create a mock pipeline executor."""
        executor = Mock(spec=PipelineExecutor)
        return executor

    @pytest.fixture
    def state_manager_mock(self):
        """Create a mock state manager."""
        manager = Mock(spec=StateManager)
        return manager

    @pytest.fixture
    def feedback_manager_mock(self):
        """Create a mock feedback manager."""
        manager = Mock(spec=FeedbackManager)
        return manager

    @pytest.fixture
    def stage_factory_mock(self):
        """Create a mock stage factory function."""
        return Mock()

    @pytest.fixture
    def orchestrator(self, pipeline_repository_mock, pipeline_executor_mock,
                     state_manager_mock, feedback_manager_mock,
                     stage_factory_mock):
        """Create a PipelineOrchestrator with mocked dependencies."""
        return PipelineOrchestrator(
            pipeline_repository=pipeline_repository_mock,
            pipeline_executor=pipeline_executor_mock,
            state_manager=state_manager_mock,
            feedback_manager=feedback_manager_mock,
            stage_factory=stage_factory_mock
        )

    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing."""
        return Task(
            id="task-id",
            description="Test task",
            requirements=["Requirement 1"],
            constraints=["Constraint 1"]
        )

    @pytest.fixture
    def sample_pipeline_state(self, sample_task):
        """Create a sample pipeline state for testing."""
        return PipelineState(
            id="state-id",
            task_id=sample_task.id,
            current_stage="requirements_gathering",
            stages_completed=[],
            artifacts={},
            feedback=[]
        )

    @pytest.fixture
    def mock_stage(self):
        """Create a mock pipeline stage."""
        stage = Mock(spec=PipelineStage)
        stage.id = "stage-id"
        stage.name = "requirements_gathering"
        stage.get_next_stage_name.return_value = "knowledge_gathering"
        return stage

    def test_execute_pipeline_new_task(self, orchestrator,
                                       pipeline_repository_mock,
                                       state_manager_mock,
                                       pipeline_executor_mock,
                                       stage_factory_mock, sample_task,
                                       sample_pipeline_state):
        """Test executing a complete pipeline with a new task."""
        # Arrange
        # Configure state manager to create initial state
        state_manager_mock.create_initial_state.return_value = sample_pipeline_state

        # Configure stage factory to create stages
        stages = [
            Mock(spec=PipelineStage, name="requirements_gathering"),
            Mock(spec=PipelineStage, name="knowledge_gathering"),
            Mock(spec=PipelineStage, name="implementation_planning"),
            Mock(spec=PipelineStage, name="implementation_writing"),
            Mock(spec=PipelineStage, name="review")
        ]
        stage_factory_mock.side_effect = stages

        # Configure executor to simulate successful execution of each stage
        def execute_side_effect(state_id, stage, next_stage_name=None,
                                create_checkpoint=False, use_transaction=False):
            # Find the current stage being executed
            current_idx = next(
                i for i, s in enumerate(stages) if s.name == stage.name)

            # Set up the next stage
            next_idx = current_idx + 1
            next_stage = stages[next_idx].name if next_idx < len(
                stages) else None

            # Create new state with updated progress
            new_state = PipelineState(
                id=sample_pipeline_state.id,
                task_id=sample_pipeline_state.task_id,
                current_stage=next_stage if next_stage else "review",
                stages_completed=[s.name for s in stages[:current_idx + 1]],
                artifacts={},
                feedback=[]
            )
            return new_state

        pipeline_executor_mock.execute_stage.side_effect = execute_side_effect

        # Act
        result = orchestrator.execute_pipeline(sample_task.id)

        # Assert
        state_manager_mock.create_initial_state.assert_called_once()

        # Verify that each stage was created
        stage_factory_calls = [call(stage_name) for stage_name in [
            "requirements_gathering", "knowledge_gathering",
            "implementation_planning", "implementation_writing", "review"
        ]]
        stage_factory_mock.assert_has_calls(stage_factory_calls)

        # Verify that each stage was executed
        assert pipeline_executor_mock.execute_stage.call_count == 5

        # Verify final result
        assert result.current_stage == "review"
        assert len(result.stages_completed) == 5
        assert result.stages_completed == [
            "requirements_gathering",
            "knowledge_gathering",
            "implementation_planning",
            "implementation_writing",
            "review"
        ]

    def test_execute_pipeline_existing_state(self, orchestrator,
                                             pipeline_repository_mock,
                                             state_manager_mock,
                                             pipeline_executor_mock,
                                             stage_factory_mock,
                                             sample_pipeline_state):
        """Test executing a pipeline with an existing state."""
        # Arrange
        # Configure state manager to return existing state
        state_manager_mock.get_latest_pipeline_state.return_value = sample_pipeline_state

        # Set up remaining stages
        remaining_stages = [
            Mock(spec=PipelineStage, name="requirements_gathering"),
            Mock(spec=PipelineStage, name="knowledge_gathering"),
            Mock(spec=PipelineStage, name="implementation_planning"),
            Mock(spec=PipelineStage, name="implementation_writing"),
            Mock(spec=PipelineStage, name="review")
        ]
        stage_factory_mock.side_effect = remaining_stages

        # Configure executor to simulate successful execution
        def execute_side_effect(state_id, stage, next_stage_name=None,
                                create_checkpoint=False, use_transaction=False):
            # Find the current stage being executed
            current_idx = next(i for i, s in enumerate(remaining_stages) if
                               s.name == stage.name)

            # Set up the next stage
            next_idx = current_idx + 1
            next_stage = remaining_stages[next_idx].name if next_idx < len(
                remaining_stages) else None

            # Create new state with updated progress
            new_state = PipelineState(
                id=sample_pipeline_state.id,
                task_id=sample_pipeline_state.task_id,
                current_stage=next_stage if next_stage else "review",
                stages_completed=[s.name for s in
                                  remaining_stages[:current_idx + 1]],
                artifacts={},
                feedback=[]
            )
            return new_state

        pipeline_executor_mock.execute_stage.side_effect = execute_side_effect

        # Act
        result = orchestrator.execute_pipeline(
            task_id=sample_pipeline_state.task_id,
            continue_from_current=True
        )

        # Assert
        state_manager_mock.get_latest_pipeline_state.assert_called_once_with(
            sample_pipeline_state.task_id)
        state_manager_mock.create_initial_state.assert_not_called()

        # Verify executor was called for each stage
        assert pipeline_executor_mock.execute_stage.call_count == 5

        # Verify final result
        assert result.current_stage == "review"
        assert len(result.stages_completed) == 5

    def test_execute_pipeline_with_checkpoint(self, orchestrator,
                                              pipeline_executor_mock,
                                              state_manager_mock,
                                              stage_factory_mock,
                                              sample_pipeline_state):
        """Test executing a pipeline with checkpoints at each stage."""
        # Arrange
        # Configure state manager
        state_manager_mock.create_initial_state.return_value = sample_pipeline_state

        # Configure stage factory
        stages = [
            Mock(spec=PipelineStage, name="requirements_gathering"),
            Mock(spec=PipelineStage, name="knowledge_gathering")
        ]
        stage_factory_mock.side_effect = stages

        # Configure executor
        def execute_side_effect(state_id, stage, next_stage_name=None,
                                create_checkpoint=False, use_transaction=False):
            current_idx = next(
                i for i, s in enumerate(stages) if s.name == stage.name)
            next_idx = current_idx + 1
            next_stage = stages[next_idx].name if next_idx < len(
                stages) else None

            new_state = PipelineState(
                id=sample_pipeline_state.id,
                task_id=sample_pipeline_state.task_id,
                current_stage=next_stage if next_stage else "knowledge_gathering",
                stages_completed=[s.name for s in stages[:current_idx + 1]],
                artifacts={},
                feedback=[]
            )
            return new_state

        pipeline_executor_mock.execute_stage.side_effect = execute_side_effect

        # Act
        result = orchestrator.execute_pipeline(
            task_id=sample_pipeline_state.task_id,
            create_checkpoints=True
        )

        # Assert
        # Verify executor was called with create_checkpoint=True
        for call_args in pipeline_executor_mock.execute_stage.call_args_list:
            assert call_args[1]["create_checkpoint"] is True

    def test_execute_pipeline_with_feedback(self, orchestrator,
                                            pipeline_executor_mock,
                                            state_manager_mock,
                                            feedback_manager_mock,
                                            stage_factory_mock,
                                            sample_pipeline_state):
        """Test executing a pipeline with feedback at each stage."""
        # Arrange
        # Configure state manager
        state_manager_mock.create_initial_state.return_value = sample_pipeline_state

        # Configure stage factory
        stages = [
            Mock(spec=PipelineStage, name="requirements_gathering"),
            Mock(spec=PipelineStage, name="knowledge_gathering")
        ]
        stage_factory_mock.side_effect = stages

        # Configure executor
        def execute_side_effect(state_id, stage, next_stage_name=None,
                                create_checkpoint=False, use_transaction=False):
            current_idx = next(
                i for i, s in enumerate(stages) if s.name == stage.name)
            next_idx = current_idx + 1
            next_stage = stages[next_idx].name if next_idx < len(
                stages) else None

            new_state = PipelineState(
                id=sample_pipeline_state.id,
                task_id=sample_pipeline_state.task_id,
                current_stage=next_stage if next_stage else "knowledge_gathering",
                stages_completed=[s.name for s in stages[:current_idx + 1]],
                artifacts={},
                feedback=[]
            )
            return new_state

        pipeline_executor_mock.execute_stage.side_effect = execute_side_effect

        # Configure the wait_for_feedback function to simulate user feedback
        orchestrator._wait_for_feedback = Mock(return_value=True)

        # Act
        result = orchestrator.execute_pipeline(
            task_id=sample_pipeline_state.task_id,
            wait_for_feedback=True
        )

        # Assert
        # Verify the wait_for_feedback function was called after each stage
        assert orchestrator._wait_for_feedback.call_count == 1  # Only called after first stage

        # Verify feedback was incorporated
        assert feedback_manager_mock.incorporate_all_feedback.call_count == 1

    def test_execute_pipeline_with_error(self, orchestrator,
                                         pipeline_executor_mock,
                                         state_manager_mock, stage_factory_mock,
                                         sample_pipeline_state):
        """Test handling errors during pipeline execution."""
        # Arrange
        # Configure state manager
        state_manager_mock.create_initial_state.return_value = sample_pipeline_state

        # Configure stage factory
        stage = Mock(spec=PipelineStage, name="requirements_gathering")
        stage_factory_mock.return_value = stage

        # Configure executor to raise an exception
        pipeline_executor_mock.execute_stage.side_effect = Exception(
            "Execution error")

        # Configure the error handling
        orchestrator._handle_execution_error = Mock(
            return_value=sample_pipeline_state)

        # Act
        result = orchestrator.execute_pipeline(sample_pipeline_state.task_id)

        # Assert
        # Verify the error handler was called
        orchestrator._handle_execution_error.assert_called_once()

        # Verify the result is the state returned by the error handler
        assert result == sample_pipeline_state

    def test_execute_stages_from_current(self, orchestrator,
                                         pipeline_executor_mock,
                                         stage_factory_mock,
                                         sample_pipeline_state):
        """Test executing stages from the current state."""
        # Arrange
        # Update the sample state to be in the middle of the pipeline
        state = sample_pipeline_state
        state.current_stage = "knowledge_gathering"
        state.stages_completed = ["requirements_gathering"]

        # Configure stage factory
        stages = [
            Mock(spec=PipelineStage, name="knowledge_gathering"),
            Mock(spec=PipelineStage, name="implementation_planning"),
            Mock(spec=PipelineStage, name="implementation_writing"),
            Mock(spec=PipelineStage, name="review")
        ]
        stage_factory_mock.side_effect = stages

        # Configure executor
        def execute_side_effect(state_id, stage, next_stage_name=None,
                                create_checkpoint=False, use_transaction=False):
            current_idx = next(
                i for i, s in enumerate(stages) if s.name == stage.name)
            next_idx = current_idx + 1
            next_stage = stages[next_idx].name if next_idx < len(
                stages) else None

            new_state = PipelineState(
                id=state.id,
                task_id=state.task_id,
                current_stage=next_stage if next_stage else "review",
                stages_completed=state.stages_completed + [stage.name],
                artifacts={},
                feedback=[]
            )
            return new_state

        pipeline_executor_mock.execute_stage.side_effect = execute_side_effect

        # Act
        result = orchestrator._execute_stages_from_current(state)

        # Assert
        # Verify that stages were executed starting from knowledge_gathering
        assert pipeline_executor_mock.execute_stage.call_count == 4
        first_call = pipeline_executor_mock.execute_stage.call_args_list[0]
        assert first_call[1]["stage"].name == "knowledge_gathering"

        # Verify final result
        assert result.current_stage == "review"
        assert len(
            result.stages_completed) == 5  # Including requirements_gathering
        assert "requirements_gathering" in result.stages_completed
        assert "knowledge_gathering" in result.stages_completed
        assert "implementation_planning" in result.stages_completed
        assert "implementation_writing" in result.stages_completed
        assert "review" in result.stages_completed

    def test_execute_single_stage(self, orchestrator, pipeline_executor_mock,
                                  stage_factory_mock, sample_pipeline_state,
                                  sample_task):
        """Test executing a single stage in the pipeline."""
        # Arrange
        # Configure pipeline repository
        pipeline_executor_mock.execute_stage.return_value = sample_pipeline_state

        # Configure stage factory
        stage = Mock(spec=PipelineStage, name="requirements_gathering")
        stage_factory_mock.return_value = stage

        # Act
        result = orchestrator.execute_single_stage(
            task_id=sample_task.id,
            pipeline_state_id=sample_pipeline_state.id,
            stage_name="requirements_gathering"
        )

        # Assert
        stage_factory_mock.assert_called_once_with("requirements_gathering")
        pipeline_executor_mock.execute_stage.assert_called_once_with(
            pipeline_state_id=sample_pipeline_state.id,
            stage=stage,
            create_checkpoint=True
        )
        assert result == sample_pipeline_state

    def test_wait_for_feedback_implementation(self, orchestrator,
                                              sample_pipeline_state):
        """Test the implementation of the _wait_for_feedback method."""
        # This test doesn't mock _wait_for_feedback so we can test the actual implementation
        orchestrator._wait_for_feedback = PipelineOrchestrator._wait_for_feedback

        # We'll patch the input function to simulate user input
        with patch('builtins.input', return_value='y'):
            # Act
            result = orchestrator._wait_for_feedback(sample_pipeline_state)

            # Assert
            assert result is True

        # Test with 'n' input
        with patch('builtins.input', return_value='n'):
            # Act
            result = orchestrator._wait_for_feedback(sample_pipeline_state)

            # Assert
            assert result is False

    def test_handle_execution_error(self, orchestrator, state_manager_mock,
                                    sample_pipeline_state):
        """Test handling of execution errors."""
        # This test doesn't mock _handle_execution_error so we can test the actual implementation
        orchestrator._handle_execution_error = PipelineOrchestrator._handle_execution_error

        # Arrange
        error = Exception("Test error")
        stage = Mock(spec=PipelineStage, name="requirements_gathering")

        # Configure state manager to return to a checkpoint
        state_manager_mock.rollback_to_latest_checkpoint.return_value = sample_pipeline_state

        # Act
        with patch('builtins.print'):  # Suppress print output
            result = orchestrator._handle_execution_error(error,
                                                          sample_pipeline_state,
                                                          stage)

        # Assert
        state_manager_mock.rollback_to_latest_checkpoint.assert_called_once_with(
            sample_pipeline_state.id)
        assert result == sample_pipeline_state

    def test_transaction_support(self, orchestrator, pipeline_repository_mock,
                                 state_manager_mock, pipeline_executor_mock,
                                 stage_factory_mock, sample_pipeline_state,
                                 sample_task):
        """Test transaction support during pipeline execution."""
        # Arrange
        # Configure state manager
        state_manager_mock.create_initial_state.return_value = sample_pipeline_state
        state_manager_mock.transaction = MagicMock()

        # Configure pipeline executor to use transactions
        pipeline_executor_mock.execute_stage.return_value = sample_pipeline_state

        # Configure stage factory
        stage = Mock(spec=PipelineStage, name="requirements_gathering")
        stage_factory_mock.return_value = stage

        # Act
        orchestrator.execute_pipeline(
            task_id=sample_task.id,
            use_transactions=True
        )

        # Assert
        # Verify transaction context manager was used
        state_manager_mock.transaction.assert_called()

        # Verify executor was called with use_transaction=True
        call_args = pipeline_executor_mock.execute_stage.call_args
        assert call_args[1]["use_transaction"] is True