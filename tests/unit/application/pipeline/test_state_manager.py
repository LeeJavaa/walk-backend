import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.ports.pipeline_repository import PipelineRepository
from src.application.pipeline.state_manager import StateManager


class TestStateManager:
    """Unit tests for StateManager."""

    @pytest.fixture
    def pipeline_repository_mock(self):
        """Create a mock pipeline repository."""
        repo = Mock(spec=PipelineRepository)

        # Configure the mock to return the state it was given to save
        repo.save_pipeline_state.side_effect = lambda state: state

        return repo

    @pytest.fixture
    def state_manager(self, pipeline_repository_mock):
        """Create a StateManager with mocked dependencies."""
        return StateManager(pipeline_repository=pipeline_repository_mock)

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

    def test_create_initial_state(self, state_manager, pipeline_repository_mock,
                                  sample_task):
        """Test creating an initial pipeline state."""
        # Act
        state = state_manager.create_initial_state(sample_task)

        # Assert
        pipeline_repository_mock.save_pipeline_state.assert_called_once()
        assert state.task_id == sample_task.id
        assert state.current_stage == "requirements_gathering"
        assert not state.stages_completed
        assert not state.artifacts
        assert not state.feedback

    def test_get_pipeline_state(self, state_manager, pipeline_repository_mock,
                                sample_pipeline_state):
        """Test getting a pipeline state by ID."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Act
        state = state_manager.get_pipeline_state(sample_pipeline_state.id)

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            sample_pipeline_state.id)
        assert state == sample_pipeline_state

    def test_get_pipeline_state_not_found(self, state_manager,
                                          pipeline_repository_mock):
        """Test getting a non-existent pipeline state."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = None

        # Act & Assert
        with pytest.raises(KeyError):
            state_manager.get_pipeline_state("nonexistent-id")

    def test_get_latest_pipeline_state(self, state_manager,
                                       pipeline_repository_mock, sample_task,
                                       sample_pipeline_state):
        """Test getting the latest pipeline state for a task."""
        # Arrange
        pipeline_repository_mock.get_latest_pipeline_state.return_value = sample_pipeline_state

        # Act
        state = state_manager.get_latest_pipeline_state(sample_task.id)

        # Assert
        pipeline_repository_mock.get_latest_pipeline_state.assert_called_once_with(
            sample_task.id)
        assert state == sample_pipeline_state

    def test_create_checkpoint(self, state_manager, pipeline_repository_mock,
                               sample_pipeline_state):
        """Test creating a checkpoint in the pipeline state."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        checkpoint_name = "test_checkpoint"

        # Act
        checkpoint_id, updated_state = state_manager.create_checkpoint(
            pipeline_state_id=sample_pipeline_state.id,
            checkpoint_name=checkpoint_name
        )

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            sample_pipeline_state.id)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

        # Verify the checkpoint was created
        assert checkpoint_id in updated_state.checkpoint_data
        assert checkpoint_name in checkpoint_id
        assert updated_state.checkpoint_data[checkpoint_id][
                   "current_stage"] == sample_pipeline_state.current_stage
        assert "timestamp" in updated_state.checkpoint_data[checkpoint_id]

    def test_rollback_to_checkpoint(self, state_manager,
                                    pipeline_repository_mock,
                                    sample_pipeline_state):
        """Test rolling back to a checkpoint."""
        # Arrange
        # Create a state with a checkpoint
        checkpoint_id = "checkpoint-id"
        checkpoint_data = {
            "current_stage": "requirements_gathering",
            "stages_completed": [],
            "artifacts": {},
            "timestamp": datetime.now().isoformat()
        }
        state = sample_pipeline_state
        state.checkpoint_data[checkpoint_id] = checkpoint_data

        # Update the state to simulate progress
        state.current_stage = "knowledge_gathering"
        state.stages_completed = ["requirements_gathering"]
        state.artifacts = {
            "requirements_gathering": {"requirements": ["Requirement 1"]}
        }

        pipeline_repository_mock.get_pipeline_state.return_value = state

        # Act
        rolled_back_state = state_manager.rollback_to_checkpoint(
            pipeline_state_id=state.id,
            checkpoint_id=checkpoint_id
        )

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state.id)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

        # Verify the state was rolled back
        assert rolled_back_state.current_stage == "requirements_gathering"
        assert not rolled_back_state.stages_completed
        assert not rolled_back_state.artifacts

    def test_rollback_to_checkpoint_not_found(self, state_manager,
                                              pipeline_repository_mock,
                                              sample_pipeline_state):
        """Test rolling back to a non-existent checkpoint."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Act & Assert
        with pytest.raises(KeyError):
            state_manager.rollback_to_checkpoint(
                pipeline_state_id=sample_pipeline_state.id,
                checkpoint_id="nonexistent-checkpoint"
            )

    def test_get_pipeline_progress(self, state_manager,
                                   pipeline_repository_mock,
                                   sample_pipeline_state):
        """Test getting the pipeline progress."""
        # Arrange
        # Update state to have some progress
        state = sample_pipeline_state
        state.current_stage = "implementation_planning"
        state.stages_completed = ["requirements_gathering",
                                  "knowledge_gathering"]

        pipeline_repository_mock.get_pipeline_state.return_value = state

        # Act
        progress = state_manager.get_pipeline_progress(state.id)

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state.id)
        assert progress["current_stage"] == "implementation_planning"
        assert progress["completed_stages"] == ["requirements_gathering",
                                                "knowledge_gathering"]
        assert progress["total_stages"] == len(state.PIPELINE_STAGES)
        assert progress["percentage"] == (2 / len(state.PIPELINE_STAGES)) * 100

    def test_list_checkpoints(self, state_manager, pipeline_repository_mock,
                              sample_pipeline_state):
        """Test listing checkpoints in a pipeline state."""
        # Arrange
        # Create a state with multiple checkpoints
        state = sample_pipeline_state
        timestamp1 = datetime.now().isoformat()
        timestamp2 = datetime.now().isoformat()

        state.checkpoint_data = {
            "checkpoint-1": {
                "current_stage": "requirements_gathering",
                "stages_completed": [],
                "timestamp": timestamp1
            },
            "checkpoint-2": {
                "current_stage": "knowledge_gathering",
                "stages_completed": ["requirements_gathering"],
                "timestamp": timestamp2
            }
        }

        pipeline_repository_mock.get_pipeline_state.return_value = state

        # Act
        checkpoints = state_manager.list_checkpoints(state.id)

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state.id)
        assert len(checkpoints) == 2
        assert checkpoints[0]["id"] == "checkpoint-1"
        assert checkpoints[0]["stage"] == "requirements_gathering"
        assert checkpoints[0]["timestamp"] == timestamp1
        assert checkpoints[1]["id"] == "checkpoint-2"
        assert checkpoints[1]["stage"] == "knowledge_gathering"
        assert checkpoints[1]["timestamp"] == timestamp2

    def test_is_valid_transition(self, state_manager, sample_pipeline_state):
        """Test validating a stage transition."""
        # Arrange
        current_stage = "requirements_gathering"

        # Act & Assert - Valid transitions
        assert state_manager.is_valid_transition(current_stage,
                                                 "knowledge_gathering") is True

        # Act & Assert - Invalid transitions (skipping stages)
        assert state_manager.is_valid_transition(current_stage,
                                                 "implementation_planning") is False
        assert state_manager.is_valid_transition(current_stage,
                                                 "implementation_writing") is False
        assert state_manager.is_valid_transition(current_stage,
                                                 "review") is False

        # Act & Assert - Invalid transition (staying on same stage)
        assert state_manager.is_valid_transition(current_stage,
                                                 current_stage) is True

        # Act & Assert - Invalid transition (going backwards)
        current_stage = "knowledge_gathering"
        assert state_manager.is_valid_transition(current_stage,
                                                 "requirements_gathering") is False

    def test_transaction_support(self, state_manager, pipeline_repository_mock,
                                 sample_task):
        """Test transaction support for state operations."""
        # Arrange
        mock_session = Mock()
        pipeline_repository_mock.start_transaction.return_value = mock_session

        # Act
        with state_manager.transaction():
            state = state_manager.create_initial_state(sample_task)

        # Assert
        pipeline_repository_mock.start_transaction.assert_called_once()
        pipeline_repository_mock.commit_transaction.assert_called_once_with(
            mock_session)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

    def test_transaction_rollback_on_error(self, state_manager,
                                           pipeline_repository_mock):
        """Test transaction rollback on error."""
        # Arrange
        mock_session = Mock()
        pipeline_repository_mock.start_transaction.return_value = mock_session
        pipeline_repository_mock.save_pipeline_state.side_effect = Exception(
            "Database error")

        # Act & Assert
        with pytest.raises(Exception):
            with state_manager.transaction():
                # This will fail
                state_manager.create_initial_state(Mock(spec=Task))

        # Verify
        pipeline_repository_mock.start_transaction.assert_called_once()
        pipeline_repository_mock.abort_transaction.assert_called_once_with(
            mock_session)
        pipeline_repository_mock.commit_transaction.assert_not_called()