"""
Feedback manager for handling human feedback in the pipeline.

This module provides the FeedbackManager class that handles feedback
collection, incorporation, and prioritization.
"""
import logging
import contextlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator
from uuid import uuid4

from src.domain.entities.pipeline_state import PipelineState
from src.domain.ports.pipeline_repository import PipelineRepository


class FeedbackManager:
    """
    Manages feedback collection and incorporation for the pipeline.

    This class is responsible for:
    - Collecting feedback on pipeline stages
    - Incorporating feedback into the pipeline execution
    - Prioritizing feedback based on type and urgency
    """

    def __init__(self, pipeline_repository: PipelineRepository):
        """
        Initialize the feedback manager.

        Args:
            pipeline_repository: Repository for storing pipeline state and tasks
        """
        self.pipeline_repository = pipeline_repository
        self.logger = logging.getLogger(__name__)

    @contextlib.contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """
        Context manager for transaction support.

        Yields:
            None

        Raises:
            Exception: If an error occurs during the transaction
        """
        session = self.pipeline_repository.start_transaction()
        try:
            yield
            self.pipeline_repository.commit_transaction(session)
        except Exception as e:
            self.pipeline_repository.abort_transaction(session)
            self.logger.error(f"Transaction failed: {str(e)}", exc_info=True)
            raise

    def submit_feedback(
            self,
            pipeline_state_id: str,
            stage_name: str,
            content: str,
            feedback_type: str = "suggestion"
    ) -> tuple[str, PipelineState]:
        """
        Submit feedback for a pipeline stage.

        Args:
            pipeline_state_id: ID of the pipeline state
            stage_name: Name of the stage to provide feedback for
            content: Feedback content
            feedback_type: Type of feedback (suggestion, correction, enhancement)

        Returns:
            Tuple of (feedback ID, updated pipeline state)

        Raises:
            KeyError: If the pipeline state is not found
            ValueError: If the stage name is invalid
        """
        # Get the current pipeline state
        state = self.pipeline_repository.get_pipeline_state(pipeline_state_id)
        if not state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        # Validate that the stage exists in the pipeline
        if stage_name not in PipelineState.PIPELINE_STAGES:
            raise ValueError(f"Invalid stage name: {stage_name}")

        # Create the feedback item
        feedback_id = str(uuid4())
        feedback_item = {
            "id": feedback_id,
            "stage_name": stage_name,
            "content": content,
            "type": feedback_type,
            "timestamp": datetime.now().isoformat(),
            "incorporated": False
        }

        self.logger.info(
            f"Submitting feedback for stage {stage_name} in pipeline state {pipeline_state_id}")

        # Add the feedback to the state
        state.feedback.append(feedback_item)

        # Save the updated state
        updated_state = self.pipeline_repository.save_pipeline_state(state)

        return feedback_id, updated_state

    def incorporate_feedback(
            self,
            pipeline_state_id: str,
            feedback_ids: List[str]
    ) -> PipelineState:
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
        state = self.pipeline_repository.get_pipeline_state(pipeline_state_id)
        if not state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        # Mark feedback as incorporated
        for feedback_id in feedback_ids:
            for feedback in state.feedback:
                if feedback["id"] == feedback_id:
                    feedback["incorporated"] = True
                    break
            else:
                raise ValueError(f"Feedback with ID {feedback_id} not found")

        self.logger.info(
            f"Incorporating {len(feedback_ids)} feedback items in pipeline state {pipeline_state_id}")

        # Save the updated state
        return self.pipeline_repository.save_pipeline_state(state)

    def incorporate_all_feedback(self, pipeline_state_id: str) -> PipelineState:
        """
        Incorporate all feedback in the pipeline state.

        Args:
            pipeline_state_id: ID of the pipeline state

        Returns:
            Updated pipeline state

        Raises:
            KeyError: If the pipeline state is not found
        """
        # Get the current pipeline state
        state = self.pipeline_repository.get_pipeline_state(pipeline_state_id)
        if not state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        # Skip if no feedback
        if not state.feedback:
            return state

        # Prioritize and incorporate feedback
        prioritized_feedback = self._prioritize_feedback(state.feedback)

        self.logger.info(
            f"Incorporating all feedback in pipeline state {pipeline_state_id}")

        # Mark all feedback as incorporated
        for feedback in state.feedback:
            feedback["incorporated"] = True

        # Save the updated state
        return self.pipeline_repository.save_pipeline_state(state)

    def get_feedback(self, pipeline_state_id: str) -> List[Dict[str, Any]]:
        """
        Get all feedback for a pipeline state.

        Args:
            pipeline_state_id: ID of the pipeline state

        Returns:
            List of feedback items

        Raises:
            KeyError: If the pipeline state is not found
        """
        # Get the current pipeline state
        state = self.pipeline_repository.get_pipeline_state(pipeline_state_id)
        if not state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        return state.feedback

    def get_feedback_by_stage(
            self,
            pipeline_state_id: str,
            stage_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get feedback for a specific stage in the pipeline.

        Args:
            pipeline_state_id: ID of the pipeline state
            stage_name: Name of the stage

        Returns:
            List of feedback items for the stage

        Raises:
            KeyError: If the pipeline state is not found
            ValueError: If the stage name is invalid
        """
        # Get the current pipeline state
        state = self.pipeline_repository.get_pipeline_state(pipeline_state_id)
        if not state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        # Validate that the stage exists in the pipeline
        if stage_name not in PipelineState.PIPELINE_STAGES:
            raise ValueError(f"Invalid stage name: {stage_name}")

        # Filter feedback by stage
        return [feedback for feedback in state.feedback if
                feedback["stage_name"] == stage_name]

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