from typing import Optional

from src.domain.entities.pipeline_stage import PipelineStage, PipelineStageResult, PipelineStageStatus
from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState

class ImplementationWritingStage(PipelineStage):
    """Pipeline stage for writing the implementation."""

    def execute(self, task: Task,
                state: Optional[PipelineState] = None) -> PipelineStageResult:
        """
        Execute the implementation writing stage.

        Args:
            task: Task to process
            state: Current pipeline state (optional)

        Returns:
            Stage execution result
        """
        # For now, return placeholder code
        code = """
def placeholder_implementation():
    \"\"\"
    This is a placeholder implementation.

    In the full system, this would be generated based on the task requirements.
    \"\"\"
    print("Hello, world!")
    return "Implementation placeholder"
        """

        return PipelineStageResult(
            stage_id=self.id,
            status=PipelineStageStatus.COMPLETED,
            output={"code": code}
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
        # This stage can only be executed after the implementation planning stage
        return (previous_stage is not None and
                previous_stage.__class__.__name__ == "ImplementationPlanningStage")