from typing import Optional

from src.domain.entities.pipeline_stage import PipelineStage, PipelineStageResult, PipelineStageStatus
from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState

class ReviewStage(PipelineStage):
    """Pipeline stage for reviewing the implementation."""

    def execute(self, task: Task,
                state: Optional[PipelineState] = None) -> PipelineStageResult:
        """
        Execute the review stage.

        Args:
            task: Task to process
            state: Current pipeline state (optional)

        Returns:
            Stage execution result
        """
        # For now, return a placeholder review
        review = [
            "Code is functional but could be improved.",
            "Consider adding more comments.",
            "Add error handling.",
            "Optimize the algorithm."
        ]

        return PipelineStageResult(
            stage_id=self.id,
            status=PipelineStageStatus.COMPLETED,
            output={"review": review}
        )

    def validate_transition_from(self, previous_stage: Optional[
        PipelineStage]) -> bool:
        """
        Validate if this stage can be executed after the given previous stage.

        Args:
            previous_stage: The previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the implementation writing stage
        return (previous_stage is not None and
                previous_stage.__class__.__name__ == "ImplementationWritingStage")

    def validate_transition_from_name(self, previous_stage_name: Optional[
        str]) -> bool:
        """
        Validate if this stage can be executed after a stage with the given name.

        Args:
            previous_stage_name: The name of the previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the implementation writing stage
        return previous_stage_name == "implementation_writing"

    def get_next_stage_name(self) -> str:
        """
        Get the name of the next stage in the pipeline.

        Returns:
            Name of the next stage
        """
        return ""