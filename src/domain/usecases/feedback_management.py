from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from src.domain.entities.pipeline_state import PipelineState
from src.domain.ports.pipeline_repository import PipelineRepository


class SubmitFeedbackUseCase:
    """Use case for submitting feedback on a pipeline stage."""

    def __init__(self, pipeline_repository: PipelineRepository):
        """
        Initialize the use case.

        Args:
            pipeline_repository: Repository for storing pipeline state
        """
        self.pipeline_repository = pipeline_repository

    def execute(
            self,
            pipeline_state_id: str,
            stage_name: str,
            content: str,
            feedback_type: str = "suggestion"
    ) -> PipelineState:
        """
        Submit feedback for a pipeline stage.

        Args:
            pipeline_state_id: ID of the pipeline state
            stage_name: Name of the stage to provide feedback for
            content: Feedback content
            feedback_type: Type of feedback (suggestion, correction, enhancement)

        Returns:
            Updated pipeline state

        Raises:
            KeyError: If the pipeline state is not found
            ValueError: If the stage name is invalid
        """
        # Get the current pipeline state
        pipeline_state = self.pipeline_repository.get_pipeline_state(
            pipeline_state_id)
        if not pipeline_state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        # Validate that the stage exists in the pipeline
        if stage_name not in PipelineState.PIPELINE_STAGES:
            raise ValueError(f"Invalid stage name: {stage_name}")

        # Create the feedback item
        feedback_item = {
            "id": str(uuid4()),
            "stage_name": stage_name,
            "content": content,
            "type": feedback_type,
            "timestamp": datetime.now().isoformat(),
            "incorporated": False
        }

        # Add the feedback to the state
        pipeline_state.feedback.append(feedback_item)

        # Save the updated state
        return self.pipeline_repository.save_pipeline_state(pipeline_state)


class IncorporateFeedbackUseCase:
    """Use case for incorporating feedback into the pipeline."""

    def __init__(self, pipeline_repository: PipelineRepository):
        """
        Initialize the use case.

        Args:
            pipeline_repository: Repository for storing pipeline state
        """
        self.pipeline_repository = pipeline_repository

    def execute(self, pipeline_state_id: str,
                feedback_ids: List[str]) -> PipelineState:
        """
        Incorporate specific feedback into the pipeline.

        Args:
            pipeline_state_id: ID of the pipeline state
            feedback_ids: List of feedback IDs to incorporate

        Returns:
            Updated pipeline state

        Raises:
            KeyError: If the pipeline state is not found
            ValueError: If a feedback ID is not found
        """
        # Get the current pipeline state
        pipeline_state = self.pipeline_repository.get_pipeline_state(
            pipeline_state_id)
        if not pipeline_state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        # Mark feedback as incorporated
        for feedback_id in feedback_ids:
            for feedback in pipeline_state.feedback:
                if feedback["id"] == feedback_id:
                    feedback["incorporated"] = True
                    break
            else:
                raise ValueError(f"Feedback with ID {feedback_id} not found")

        # Save the updated state
        return self.pipeline_repository.save_pipeline_state(pipeline_state)

    def execute_prioritized(self, pipeline_state_id: str) -> PipelineState:
        """
        Incorporate all feedback with prioritization.

        Args:
            pipeline_state_id: ID of the pipeline state

        Returns:
            Updated pipeline state

        Raises:
            KeyError: If the pipeline state is not found
        """
        # Get the current pipeline state
        pipeline_state = self.pipeline_repository.get_pipeline_state(
            pipeline_state_id)
        if not pipeline_state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        # Skip if no feedback
        if not pipeline_state.feedback:
            return pipeline_state

        # Prioritize and incorporate feedback
        prioritized_feedback = self._prioritize_feedback(
            pipeline_state.feedback)

        # Mark all feedback as incorporated
        for feedback in pipeline_state.feedback:
            feedback["incorporated"] = True

        # Save the updated state
        return self.pipeline_repository.save_pipeline_state(pipeline_state)

    def _prioritize_feedback(self, feedback: List[Dict[str, Any]]) -> List[
        Dict[str, Any]]:
        """
        Prioritize feedback based on type.

        Priority order:
        1. Corrections (critical issues)
        2. Suggestions (improvements)
        3. Enhancements (nice-to-have features)

        Args:
            feedback: List of feedback items

        Returns:
            Prioritized list of feedback items
        """
        priority_map = {
            "correction": 1,
            "suggestion": 2,
            "enhancement": 3
        }

        # Sort by priority (lower number = higher priority)
        return sorted(
            feedback,
            key=lambda f: priority_map.get(f["type"], 999)
        )