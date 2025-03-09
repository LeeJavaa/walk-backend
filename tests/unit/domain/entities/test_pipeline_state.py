import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.entities.pipeline_state import PipelineState, \
    PipelineStateValidationError
from src.domain.entities.pipeline_stage import PipelineStageResult, \
    PipelineStageStatus


class TestPipelineState:
    """Test cases for the PipelineState entity."""

    def test_pipeline_state_creation(self):
        """Test creating a pipeline state with valid inputs (U-PS-2)."""
        # Arrange
        state_id = str(uuid4())
        task_id = str(uuid4())
        current_stage = "implementation_planning"
        stages_completed = ["requirements_gathering", "knowledge_gathering"]
        artifacts = {
            "requirements_gathering": {"requirements": ["req1", "req2"]},
            "knowledge_gathering": {"context_items": ["item1", "item2"]},
        }
        feedback = []

        # Act
        state = PipelineState(
            id=state_id,
            task_id=task_id,
            current_stage=current_stage,
            stages_completed=stages_completed,
            artifacts=artifacts,
            feedback=feedback,
        )

        # Assert
        assert state.id == state_id
        assert state.task_id == task_id
        assert state.current_stage == current_stage
        assert state.stages_completed == stages_completed
        assert state.artifacts == artifacts
        assert state.feedback == feedback
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.updated_at, datetime)
        assert state.checkpoint_data == {}

    def test_validate_state_transitions(self):
        """Test state transition validation (U-PS-2)."""
        # Arrange
        state = PipelineState(
            id=str(uuid4()),
            task_id=str(uuid4()),
            current_stage="requirements_gathering",
            stages_completed=[],
            artifacts={},
            feedback=[],
        )

        # Act & Assert
        # Valid transition
        assert state.validate_transition_to("knowledge_gathering") is True

        # Invalid transition - skipping stages
        assert state.validate_transition_to("implementation_writing") is False

        # Update state and test another transition
        state.current_stage = "knowledge_gathering"
        state.stages_completed.append("requirements_gathering")

        # Valid transition
        assert state.validate_transition_to("implementation_planning") is True

        # Invalid transition - going backwards
        assert state.validate_transition_to("requirements_gathering") is False

    def test_record_stage_result(self):
        """Test recording stage results in pipeline state (U-PS-2)."""
        # Arrange
        state = PipelineState(
            id=str(uuid4()),
            task_id=str(uuid4()),
            current_stage="requirements_gathering",
            stages_completed=[],
            artifacts={},
            feedback=[],
        )

        stage_result = PipelineStageResult(
            stage_id=str(uuid4()),
            status=PipelineStageStatus.COMPLETED,
            output={"requirements": ["req1", "req2"]},
        )

        # Act
        updated_state = state.record_stage_result(
            stage_name="requirements_gathering",
            stage_result=stage_result,
            next_stage="knowledge_gathering",
        )

        # Assert
        assert updated_state.current_stage == "knowledge_gathering"
        assert updated_state.stages_completed == ["requirements_gathering"]
        assert updated_state.artifacts["requirements_gathering"] == {
            "requirements": ["req1", "req2"]}

    def test_create_checkpoint(self):
        """Test creating checkpoints for rollback (U-PS-3)."""
        # Arrange
        state = PipelineState(
            id=str(uuid4()),
            task_id=str(uuid4()),
            current_stage="implementation_planning",
            stages_completed=["requirements_gathering", "knowledge_gathering"],
            artifacts={
                "requirements_gathering": {"requirements": ["req1", "req2"]},
                "knowledge_gathering": {"context_items": ["item1", "item2"]},
            },
            feedback=[],
        )

        # Act
        checkpoint_id = state.create_checkpoint("before_implementation")

        # Assert
        assert checkpoint_id in state.checkpoint_data
        assert state.checkpoint_data[checkpoint_id][
                   "current_stage"] == "implementation_planning"
        assert "timestamp" in state.checkpoint_data[checkpoint_id]

    def test_rollback_to_checkpoint(self):
        """Test rolling back to a checkpoint (U-PS-3)."""
        # Arrange
        state = PipelineState(
            id=str(uuid4()),
            task_id=str(uuid4()),
            current_stage="implementation_writing",
            stages_completed=["requirements_gathering", "knowledge_gathering",
                              "implementation_planning"],
            artifacts={
                "requirements_gathering": {"requirements": ["req1", "req2"]},
                "knowledge_gathering": {"context_items": ["item1", "item2"]},
                "implementation_planning": {"plan": "step 1, step 2, step 3"},
            },
            feedback=[],
        )

        # Create checkpoint before implementation_writing stage
        checkpoint_data = {
            "current_stage": "implementation_planning",
            "stages_completed": ["requirements_gathering",
                                 "knowledge_gathering"],
            "artifacts": {
                "requirements_gathering": {"requirements": ["req1", "req2"]},
                "knowledge_gathering": {"context_items": ["item1", "item2"]},
            },
            "timestamp": datetime.now().isoformat(),
        }
        checkpoint_id = "before_implementation"
        state.checkpoint_data[checkpoint_id] = checkpoint_data

        # Act
        rolled_back_state = state.rollback_to_checkpoint(checkpoint_id)

        # Assert
        assert rolled_back_state.current_stage == "implementation_planning"
        assert rolled_back_state.stages_completed == ["requirements_gathering",
                                                      "knowledge_gathering"]
        assert "implementation_planning" not in rolled_back_state.artifacts
        assert rolled_back_state.checkpoint_data[
                   checkpoint_id] == checkpoint_data