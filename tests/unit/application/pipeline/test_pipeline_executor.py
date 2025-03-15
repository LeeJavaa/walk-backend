import pytest
from unittest.mock import Mock, patch, MagicMock

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult, PipelineStageStatus
from src.domain.ports.pipeline_repository import PipelineRepository
from src.application.pipeline.executor import PipelineExecutor


class TestPipelineExecutor:
    """Unit tests for PipelineExecutor."""

    @pytest.fixture
    def pipeline_repository_mock(self):
        """Create a mock pipeline repository."""
        repo = Mock(spec=PipelineRepository)

        # Configure the mock to return the state it was given to save
        repo.save_pipeline_state.side_effect = lambda state: state

        return repo

    @pytest.fixture
    def pipeline_executor(self, pipeline_repository_mock):
        """Create a PipelineExecutor with mocked dependencies."""
        return PipelineExecutor(pipeline_repository=pipeline_repository_mock)

    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing."""
        return Task(
            id="task-id",
            description="Test task",
            requirements=["Requirement 1", "Requirement 2"],
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

        # Configure validate_transition_from_name to return True
        stage.validate_transition_from_name.return_value = True

        # Configure get_next_stage_name to return the next stage
        stage.get_next_stage_name.return_value = "knowledge_gathering"

        # Configure execute to return a successful result
        stage.execute.return_value = PipelineStageResult(
            stage_id="stage-id",
            status=PipelineStageStatus.COMPLETED,
            output={"requirements": ["Requirement 1", "Requirement 2"]}
        )

        return stage

    def test_execute_stage_success(self, pipeline_executor,
                                   pipeline_repository_mock,
                                   sample_task, sample_pipeline_state,
                                   mock_stage):
        """Test executing a stage successfully."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        pipeline_repository_mock.get_task.return_value = sample_task

        # Act
        result = pipeline_executor.execute_stage(
            pipeline_state_id=sample_pipeline_state.id,
            stage=mock_stage
        )

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            sample_pipeline_state.id)
        pipeline_repository_mock.get_task.assert_called_once_with(
            sample_task.id)
        mock_stage.execute.assert_called_once_with(sample_task,
                                                   sample_pipeline_state)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

        # Verify the result
        assert result.current_stage == "knowledge_gathering"
        assert "requirements_gathering" in result.stages_completed
        assert "requirements_gathering" in result.artifacts
        assert result.artifacts["requirements_gathering"]["requirements"] == [
            "Requirement 1", "Requirement 2"]

    def test_execute_stage_with_next_stage_override(self, pipeline_executor,
                                                    pipeline_repository_mock,
                                                    sample_task,
                                                    sample_pipeline_state,
                                                    mock_stage):
        """Test executing a stage with next stage name override."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        pipeline_repository_mock.get_task.return_value = sample_task
        next_stage_override = "implementation_planning"  # Skip knowledge_gathering

        # Act
        result = pipeline_executor.execute_stage(
            pipeline_state_id=sample_pipeline_state.id,
            stage=mock_stage,
            next_stage_name=next_stage_override
        )

        # Assert
        assert result.current_stage == next_stage_override
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

    def test_execute_stage_state_not_found(self, pipeline_executor,
                                           pipeline_repository_mock):
        """Test executing a stage when the pipeline state is not found."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = None

        # Act & Assert
        with pytest.raises(KeyError):
            pipeline_executor.execute_stage(
                pipeline_state_id="nonexistent-id",
                stage=Mock(spec=PipelineStage)
            )

    def test_execute_stage_task_not_found(self, pipeline_executor,
                                          pipeline_repository_mock,
                                          sample_pipeline_state):
        """Test executing a stage when the task is not found."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        pipeline_repository_mock.get_task.return_value = None

        # Act & Assert
        with pytest.raises(KeyError):
            pipeline_executor.execute_stage(
                pipeline_state_id=sample_pipeline_state.id,
                stage=Mock(spec=PipelineStage)
            )

    def test_execute_stage_invalid_transition(self, pipeline_executor,
                                              pipeline_repository_mock,
                                              sample_task,
                                              sample_pipeline_state):
        """Test executing a stage with an invalid transition."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        pipeline_repository_mock.get_task.return_value = sample_task

        # Create a stage that won't validate the transition
        invalid_stage = Mock(spec=PipelineStage)
        invalid_stage.name = "implementation_planning"  # Invalid for first stage
        invalid_stage.validate_transition_from_name.return_value = False

        # Act & Assert
        with pytest.raises(ValueError):
            pipeline_executor.execute_stage(
                pipeline_state_id=sample_pipeline_state.id,
                stage=invalid_stage
            )

    def test_execute_stage_failure(self, pipeline_executor,
                                   pipeline_repository_mock,
                                   sample_task, sample_pipeline_state):
        """Test executing a stage that fails."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        pipeline_repository_mock.get_task.return_value = sample_task

        # Create a stage that fails during execution
        failing_stage = Mock(spec=PipelineStage)
        failing_stage.name = "requirements_gathering"
        failing_stage.validate_transition_from_name.return_value = True
        failing_stage.execute.return_value = PipelineStageResult(
            stage_id="failing-stage-id",
            status=PipelineStageStatus.FAILED,
            output={"error": "Execution failed"},
            error="Execution failed"
        )

        # Act
        result = pipeline_executor.execute_stage(
            pipeline_state_id=sample_pipeline_state.id,
            stage=failing_stage
        )

        # Assert
        assert result.current_stage == "requirements_gathering"  # Stage doesn't change on failure
        assert not result.stages_completed  # No stages completed
        assert "requirements_gathering" in result.artifacts
        assert "error" in result.artifacts["requirements_gathering"]

    def test_create_checkpoint_before_execution(self, pipeline_executor,
                                                pipeline_repository_mock,
                                                sample_task,
                                                sample_pipeline_state,
                                                mock_stage):
        """Test creating a checkpoint before stage execution."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        pipeline_repository_mock.get_task.return_value = sample_task

        # Act
        result = pipeline_executor.execute_stage(
            pipeline_state_id=sample_pipeline_state.id,
            stage=mock_stage,
            create_checkpoint=True
        )

        # Assert
        # Verify a checkpoint was created
        assert len(result.checkpoint_data) > 0
        # Get the last added checkpoint (should be the one we just created)
        checkpoint_id = list(result.checkpoint_data.keys())[-1]
        assert f"before_{mock_stage.name}" in checkpoint_id
        assert result.checkpoint_data[checkpoint_id][
                   "current_stage"] == "requirements_gathering"

    def test_transaction_management(self, pipeline_executor,
                                    pipeline_repository_mock,
                                    sample_task, sample_pipeline_state,
                                    mock_stage):
        """Test transaction management during stage execution."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        pipeline_repository_mock.get_task.return_value = sample_task
        mock_session = Mock()
        pipeline_repository_mock.start_transaction.return_value = mock_session

        # Act
        result = pipeline_executor.execute_stage(
            pipeline_state_id=sample_pipeline_state.id,
            stage=mock_stage,
            use_transaction=True
        )

        # Assert
        pipeline_repository_mock.start_transaction.assert_called_once()
        pipeline_repository_mock.commit_transaction.assert_called_once_with(
            mock_session)

        # Verify result is still correct
        assert result.current_stage == "knowledge_gathering"
        assert "requirements_gathering" in result.stages_completed

    def test_transaction_rollback_on_error(self, pipeline_executor,
                                           pipeline_repository_mock,
                                           sample_task, sample_pipeline_state):
        """Test transaction rollback when an error occurs."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        pipeline_repository_mock.get_task.return_value = sample_task
        mock_session = Mock()
        pipeline_repository_mock.start_transaction.return_value = mock_session

        # Create a stage that raises an exception
        error_stage = Mock(spec=PipelineStage)
        error_stage.name = "requirements_gathering"
        error_stage.validate_transition_from_name.return_value = True
        error_stage.execute.side_effect = Exception("Stage execution error")

        # Act & Assert
        with pytest.raises(Exception):
            pipeline_executor.execute_stage(
                pipeline_state_id=sample_pipeline_state.id,
                stage=error_stage,
                use_transaction=True
            )

        # Verify transaction was rolled back
        pipeline_repository_mock.start_transaction.assert_called_once()
        pipeline_repository_mock.abort_transaction.assert_called_once_with(
            mock_session)
        pipeline_repository_mock.commit_transaction.assert_not_called()