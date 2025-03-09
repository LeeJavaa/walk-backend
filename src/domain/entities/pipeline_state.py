from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4
import copy

from src.domain.entities.pipeline_stage import PipelineStageResult


class PipelineStateValidationError(Exception):
    """Exception raised for pipeline state validation errors."""
    pass


class PipelineState:
    """
    Entity representing the state of a pipeline execution.

    The pipeline state tracks the current stage, completed stages, artifacts,
    and feedback during the execution of a pipeline.
    """

    # Define the valid pipeline stages and their order
    PIPELINE_STAGES = [
        "requirements_gathering",
        "knowledge_gathering",
        "implementation_planning",
        "implementation_writing",
        "review",
    ]

    def __init__(
            self,
            id: str,
            task_id: str,
            current_stage: str,
            stages_completed: List[str],
            artifacts: Dict[str, Any],
            feedback: List[Dict[str, Any]],
            checkpoint_data: Optional[Dict[str, Any]] = None,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None,
    ):
        """
        Initialize a new PipelineState.

        Args:
            id: Unique identifier for the pipeline state
            task_id: Identifier of the task being processed
            current_stage: Name of the current stage
            stages_completed: List of completed stage names
            artifacts: Map of stage name to output artifacts
            feedback: List of feedback items
            checkpoint_data: Map of checkpoint id to saved state data
            created_at: Creation timestamp
            updated_at: Last update timestamp

        Raises:
            PipelineStateValidationError: If validation fails
        """
        self.validate_current_stage(current_stage)

        self.id = id
        self.task_id = task_id
        self.current_stage = current_stage
        self.stages_completed = stages_completed
        self.artifacts = artifacts
        self.feedback = feedback
        self.checkpoint_data = checkpoint_data or {}
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @staticmethod
    def validate_current_stage(stage: str) -> None:
        """
        Validate that the stage is a valid pipeline stage.

        Args:
            stage: Stage name to validate

        Raises:
            PipelineStateValidationError: If validation fails
        """
        if stage not in PipelineState.PIPELINE_STAGES:
            raise PipelineStateValidationError(
                f"Invalid pipeline stage: {stage}. Must be one of: {', '.join(PipelineState.PIPELINE_STAGES)}"
            )

    def validate_transition_to(self, next_stage: str) -> bool:
        """
        Validate if the pipeline can transition to the given next stage.

        Args:
            next_stage: Next stage name

        Returns:
            True if the transition is valid, False otherwise
        """
        if next_stage not in self.PIPELINE_STAGES:
            return False

        current_index = self.PIPELINE_STAGES.index(self.current_stage)
        next_index = self.PIPELINE_STAGES.index(next_stage)

        # Can only proceed to the next stage or stay at the current stage
        return next_index == current_index or next_index == current_index + 1

    def record_stage_result(
            self,
            stage_name: str,
            stage_result: PipelineStageResult,
            next_stage: Optional[str] = None,
    ) -> "PipelineState":
        """
        Record the result of a stage execution and update the pipeline state.

        Args:
            stage_name: Name of the stage
            stage_result: Result of the stage execution
            next_stage: Name of the next stage (optional)

        Returns:
            Updated pipeline state

        Raises:
            PipelineStateValidationError: If the stage or transition is invalid
        """
        if stage_name not in self.PIPELINE_STAGES:
            raise PipelineStateValidationError(
                f"Invalid pipeline stage: {stage_name}")

        if next_stage and not self.validate_transition_to(next_stage):
            raise PipelineStateValidationError(
                f"Invalid pipeline transition from {self.current_stage} to {next_stage}"
            )

        # Create a new state object with updated values
        new_state = copy.deepcopy(self)

        # Update the artifacts
        new_state.artifacts[stage_name] = stage_result.output

        # Update stages completed if the stage was completed successfully
        if stage_result.status == "completed" and stage_name not in new_state.stages_completed:
            new_state.stages_completed.append(stage_name)

        # Update current stage if next_stage is provided
        if next_stage:
            new_state.current_stage = next_stage

        # Update timestamp
        new_state.updated_at = datetime.now()

        return new_state

    def create_checkpoint(self, checkpoint_id: str) -> str:
        """
        Create a checkpoint of the current state for potential rollback.

        Args:
            checkpoint_id: Identifier for the checkpoint

        Returns:
            The checkpoint identifier
        """
        # Store the current state in checkpoint_data
        self.checkpoint_data[checkpoint_id] = {
            "current_stage": self.current_stage,
            "stages_completed": copy.deepcopy(self.stages_completed),
            "artifacts": copy.deepcopy(self.artifacts),
            "timestamp": datetime.now().isoformat(),
        }

        return checkpoint_id

    def rollback_to_checkpoint(self, checkpoint_id: str) -> "PipelineState":
        """
        Roll back to a previous checkpoint.

        Args:
            checkpoint_id: Identifier of the checkpoint to roll back to

        Returns:
            New pipeline state rolled back to the checkpoint

        Raises:
            KeyError: If the checkpoint does not exist
        """
        if checkpoint_id not in self.checkpoint_data:
            raise KeyError(f"Checkpoint not found: {checkpoint_id}")

        checkpoint = self.checkpoint_data[checkpoint_id]

        # Create a new state object with checkpoint values
        new_state = copy.deepcopy(self)
        new_state.current_stage = checkpoint["current_stage"]
        new_state.stages_completed = copy.deepcopy(
            checkpoint["stages_completed"])
        new_state.artifacts = copy.deepcopy(checkpoint["artifacts"])
        new_state.updated_at = datetime.now()

        return new_state