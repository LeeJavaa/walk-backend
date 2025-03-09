import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

from src.domain.entities.task import Task, TaskStatus
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult, PipelineStageStatus
from src.domain.ports.pipeline_repository import PipelineRepository
from src.domain.usecases.pipeline_management import (
    CreatePipelineUseCase,
    ExecutePipelineStageUseCase,
    RollbackPipelineUseCase,
    GetPipelineStateUseCase
)


class TestPipelineManagementUseCases:
    """Test cases for the pipeline management use cases."""

    @pytest.fixture
    def pipeline_repository_mock(self):
        """Mock for the pipeline repository."""
        repository = Mock(spec=PipelineRepository)
        return repository

    @pytest.fixture
    def sample_task(self):
        """Sample task for testing."""
        return Task(
            id="task-id",
            description="Test task",
            requirements=["Implement a test function"],
            constraints=["Use Python"],
            context_ids=["context-id-1", "context-id-2"]
        )

    @pytest.fixture
    def sample_pipeline_state(self):
        """Sample pipeline state for testing."""
        return PipelineState(
            id="state-id",
            task_id="task-id",
            current_stage="requirements_gathering",
            stages_completed=[],
            artifacts={},
            feedback=[]
        )

    @pytest.fixture
    def mock_pipeline_stage(self):
        """Mock pipeline stage for testing."""
        stage = Mock(spec=PipelineStage)
        stage.id = "stage-id"
        stage.name = "requirements_gathering"

        # Configure execute method to return a successful result
        stage.execute.return_value = PipelineStageResult(
            stage_id="stage-id",
            status=PipelineStageStatus.COMPLETED,
            output={"requirements": ["requirement1", "requirement2"]}
        )

        # Configure validate_transition_from to return True
        stage.validate_transition_from.return_value = True

        return stage

    def test_create_pipeline(self, pipeline_repository_mock, sample_task):
        """Test creating a pipeline (U-PS-2)."""
        # Arrange
        use_case = CreatePipelineUseCase(
            pipeline_repository=pipeline_repository_mock)

        # Configure save_task to return the saved task
        pipeline_repository_mock.save_task.return_value = sample_task

        # Act
        result_task, result_state = use_case.execute(sample_task)

        # Assert
        pipeline_repository_mock.save_task.assert_called_once()
        pipeline_repository_mock.save_pipeline_state.assert_called_once()
        assert result_task == sample_task
        assert result_state is not None
        assert result_state.task_id == sample_task.id
        assert result_state.current_stage == "requirements_gathering"
        assert result_state.stages_completed == []

    def test_execute_pipeline_stage(self, pipeline_repository_mock, sample_task,
                                    sample_pipeline_state, mock_pipeline_stage):
        """Test executing a pipeline stage (U-PS-1)."""
        # Arrange
        use_case = ExecutePipelineStageUseCase(
            pipeline_repository=pipeline_repository_mock)

        # Configure get_task to return the sample task
        pipeline_repository_mock.get_task.return_value = sample_task

        # Configure get_pipeline_state to return the sample state
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Act
        result = use_case.execute(
            pipeline_state_id=sample_pipeline_state.id,
            stage=mock_pipeline_stage,
            next_stage_name="knowledge_gathering"
        )

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            sample_pipeline_state.id)
        pipeline_repository_mock.get_task.assert_called_once_with(
            sample_pipeline_state.task_id)
        mock_pipeline_stage.execute.assert_called_once()
        pipeline_repository_mock.save_pipeline_state.assert_called_once()
        assert result is not None
        assert result.current_stage == "knowledge_gathering"
        assert "requirements_gathering" in result.stages_completed
        assert "requirements_gathering" in result.artifacts

    def test_rollback_pipeline(self, pipeline_repository_mock,
                               sample_pipeline_state):
        """Test rolling back a pipeline to a checkpoint (U-PS-3)."""
        # Arrange
        use_case = RollbackPipelineUseCase(
            pipeline_repository=pipeline_repository_mock)

        # Configure get_pipeline_state to return the sample state
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Create a checkpoint in the state
        checkpoint_id = sample_pipeline_state.create_checkpoint(
            "test_checkpoint")

        # Change the state to simulate progress
        updated_state = PipelineState(
            id=sample_pipeline_state.id,
            task_id=sample_pipeline_state.task_id,
            current_stage="knowledge_gathering",
            stages_completed=["requirements_gathering"],
            artifacts={"requirements_gathering": {"requirements": ["req1"]}},
            feedback=[],
            checkpoint_data=sample_pipeline_state.checkpoint_data
        )
        pipeline_repository_mock.get_pipeline_state.return_value = updated_state

        # Act
        result = use_case.execute(updated_state.id, checkpoint_id)

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            updated_state.id)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()
        assert result is not None
        assert result.current_stage == "requirements_gathering"
        assert result.stages_completed == []

    def test_get_pipeline_state(self, pipeline_repository_mock,
                                sample_pipeline_state):
        """Test getting a pipeline state (U-PS-4)."""
        # Arrange
        use_case = GetPipelineStateUseCase(
            pipeline_repository=pipeline_repository_mock)
        state_id = "state-id"
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Act
        result = use_case.execute(state_id)

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state_id)
        assert result == sample_pipeline_state

    def test_get_latest_pipeline_state(self, pipeline_repository_mock,
                                       sample_pipeline_state):
        """Test getting the latest pipeline state for a task (U-PS-4)."""
        # Arrange
        use_case = GetPipelineStateUseCase(
            pipeline_repository=pipeline_repository_mock)
        task_id = "task-id"
        pipeline_repository_mock.get_latest_pipeline_state.return_value = sample_pipeline_state

        # Act
        result = use_case.execute_get_latest(task_id)

        # Assert
        pipeline_repository_mock.get_latest_pipeline_state.assert_called_once_with(
            task_id)
        assert result == sample_pipeline_state