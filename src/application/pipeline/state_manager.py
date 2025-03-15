"""
State manager for pipeline state operations.

This module provides the StateManager class that handles pipeline state
creation, retrieval, checkpoint management, and state transitions.
"""
import logging
import contextlib
from datetime import datetime
from typing import Optional, List, Dict, Any, ContextManager, Generator

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.ports.pipeline_repository import PipelineRepository


class StateManager:
    """
    Manages pipeline state operations and checkpoints.

    This class is responsible for:
    - Creating and retrieving pipeline states
    - Managing checkpoints for rollback capability
    - Validating state transitions
    - Tracking progress through pipeline stages
    """

    def __init__(self, pipeline_repository: PipelineRepository):
        """
        Initialize the state manager.

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

    def create_initial_state(self, task: Task) -> PipelineState:
        """
        Create an initial pipeline state for a task.

        Args:
            task: Task to create a pipeline state for

        Returns:
            New pipeline state
        """
        from uuid import uuid4

        self.logger.info(f"Creating initial pipeline state for task {task.id}")
        initial_state = PipelineState(
            id=str(uuid4()),
            task_id=task.id,
            current_stage="requirements_gathering",
            # Always start with requirements gathering
            stages_completed=[],
            artifacts={},
            feedback=[]
        )

        return self.pipeline_repository.save_pipeline_state(initial_state)

    def get_pipeline_state(self, pipeline_state_id: str) -> PipelineState:
        """
        Get a pipeline state by ID.

        Args:
            pipeline_state_id: ID of the pipeline state

        Returns:
            Pipeline state

        Raises:
            KeyError: If the pipeline state is not found
        """
        state = self.pipeline_repository.get_pipeline_state(pipeline_state_id)
        if not state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")
        return state

    def get_latest_pipeline_state(self, task_id: str) -> Optional[
        PipelineState]:
        """
        Get the latest pipeline state for a task.

        Args:
            task_id: ID of the task

        Returns:
            Latest pipeline state, or None if not found
        """
        return self.pipeline_repository.get_latest_pipeline_state(task_id)

    def create_checkpoint(
            self,
            pipeline_state_id: str,
            checkpoint_name: str
    ) -> tuple[str, PipelineState]:
        """
        Create a checkpoint in the pipeline state.

        Args:
            pipeline_state_id: ID of the pipeline state
            checkpoint_name: Name for the checkpoint

        Returns:
            Tuple of (checkpoint ID, updated pipeline state)

        Raises:
            KeyError: If the pipeline state is not found
        """
        # Get the current state
        state = self.get_pipeline_state(pipeline_state_id)

        # Create a checkpoint
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"{checkpoint_name}_{timestamp}"

        self.logger.info(
            f"Creating checkpoint {checkpoint_id} for pipeline state {pipeline_state_id}")
        state.create_checkpoint(checkpoint_id)

        # Save the updated state
        updated_state = self.pipeline_repository.save_pipeline_state(state)

        return checkpoint_id, updated_state

    def rollback_to_checkpoint(
            self,
            pipeline_state_id: str,
            checkpoint_id: str
    ) -> PipelineState:
        """
        Roll back to a checkpoint in the pipeline state.

        Args:
            pipeline_state_id: ID of the pipeline state
            checkpoint_id: ID of the checkpoint to roll back to

        Returns:
            Updated pipeline state

        Raises:
            KeyError: If the pipeline state or checkpoint is not found
        """
        # Get the current state
        state = self.get_pipeline_state(pipeline_state_id)

        # Check if the checkpoint exists
        if checkpoint_id not in state.checkpoint_data:
            raise KeyError(
                f"Checkpoint {checkpoint_id} not found in pipeline state {pipeline_state_id}")

        self.logger.info(
            f"Rolling back pipeline state {pipeline_state_id} to checkpoint {checkpoint_id}")
        rolled_back_state = state.rollback_to_checkpoint(checkpoint_id)

        # Save the rolled back state
        return self.pipeline_repository.save_pipeline_state(rolled_back_state)

    def rollback_to_latest_checkpoint(self, pipeline_state_id: str) -> Optional[
        PipelineState]:
        """
        Roll back to the latest checkpoint in the pipeline state.

        Args:
            pipeline_state_id: ID of the pipeline state

        Returns:
            Updated pipeline state, or None if no checkpoints exist

        Raises:
            KeyError: If the pipeline state is not found
        """
        # Get the current state
        state = self.get_pipeline_state(pipeline_state_id)

        # Check if there are any checkpoints
        if not state.checkpoint_data:
            self.logger.warning(
                f"No checkpoints found for pipeline state {pipeline_state_id}")
            return None

        # Find the latest checkpoint based on timestamp
        latest_checkpoint_id = None
        latest_timestamp = None

        for checkpoint_id, checkpoint_data in state.checkpoint_data.items():
            timestamp_str = checkpoint_data.get("timestamp")
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if latest_timestamp is None or timestamp > latest_timestamp:
                    latest_timestamp = timestamp
                    latest_checkpoint_id = checkpoint_id
            except (ValueError, TypeError):
                self.logger.warning(
                    f"Invalid timestamp format in checkpoint {checkpoint_id}")

        if latest_checkpoint_id:
            self.logger.info(
                f"Rolling back to latest checkpoint {latest_checkpoint_id}")
            return self.rollback_to_checkpoint(pipeline_state_id,
                                               latest_checkpoint_id)

        return None

    def get_pipeline_progress(self, pipeline_state_id: str) -> Dict[str, Any]:
        """
        Get the progress of a pipeline.

        Args:
            pipeline_state_id: ID of the pipeline state

        Returns:
            Dictionary with progress information

        Raises:
            KeyError: If the pipeline state is not found
        """
        # Get the current state
        state = self.get_pipeline_state(pipeline_state_id)

        # Calculate progress
        total_stages = len(state.PIPELINE_STAGES)
        completed_stages = len(state.stages_completed)
        percentage = (
                                 completed_stages / total_stages) * 100 if total_stages > 0 else 0

        return {
            "current_stage": state.current_stage,
            "completed_stages": state.stages_completed,
            "total_stages": total_stages,
            "percentage": percentage
        }

    def list_checkpoints(self, pipeline_state_id: str) -> List[Dict[str, Any]]:
        """
        List all checkpoints in a pipeline state.

        Args:
            pipeline_state_id: ID of the pipeline state

        Returns:
            List of checkpoint information dictionaries

        Raises:
            KeyError: If the pipeline state is not found
        """
        # Get the current state
        state = self.get_pipeline_state(pipeline_state_id)

        # Extract checkpoint information
        checkpoints = []
        for checkpoint_id, checkpoint_data in state.checkpoint_data.items():
            checkpoints.append({
                "id": checkpoint_id,
                "stage": checkpoint_data.get("current_stage", "unknown"),
                "timestamp": checkpoint_data.get("timestamp", "unknown")
            })

        # Sort by timestamp (if available)
        checkpoints.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return checkpoints

    def is_valid_transition(self, current_stage: str, next_stage: str) -> bool:
        """
        Check if a stage transition is valid.

        Args:
            current_stage: Current stage name
            next_stage: Next stage name

        Returns:
            True if the transition is valid, False otherwise
        """
        # Get the list of stages
        stages = PipelineState.PIPELINE_STAGES

        # Check if both stages are valid
        if current_stage not in stages or next_stage not in stages:
            return False

        # Get the indices of the stages
        current_idx = stages.index(current_stage)
        next_idx = stages.index(next_stage)

        # Valid transitions:
        # 1. To the next stage in sequence
        # 2. Stay on the same stage
        return next_idx == current_idx + 1 or next_idx == current_idx