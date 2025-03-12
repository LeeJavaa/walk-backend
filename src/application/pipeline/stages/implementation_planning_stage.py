from typing import Optional

from src.domain.entities.pipeline_stage import PipelineStage, PipelineStageResult, PipelineStageStatus
from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState

class ImplementationPlanningStage(PipelineStage):
    """Pipeline stage for planning the implementation."""

    def execute(self, task: Task,
                state: Optional[PipelineState] = None) -> PipelineStageResult:
        """
        Execute the implementation planning stage.

        Args:
            task: Task to process
            state: Current pipeline state (optional)

        Returns:
            Stage execution result
        """
        # For now, return a simple plan
        plan = [
            "1. Analyze the requirements",
            "2. Research necessary algorithms and data structures",
            "3. Create a design document",
            "4. Implement the solution",
            "5. Test the implementation",
            "6. Document the code"
        ]

        return PipelineStageResult(
            stage_id=self.id,
            status=PipelineStageStatus.COMPLETED,
            output={"plan": plan}
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
        # This stage can only be executed after the knowledge gathering stage
        return (previous_stage is not None and
                previous_stage.__class__.__name__ == "KnowledgeGatheringStage")

    def validate_transition_from_name(self, previous_stage_name: Optional[
        str]) -> bool:
        """
        Validate if this stage can be executed after a stage with the given name.

        Args:
            previous_stage_name: The name of the previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the knowledge gathering stage
        return previous_stage_name == "knowledge_gathering"