from typing import List, Dict, Any, Tuple, Optional
from uuid import uuid4

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult
from src.domain.ports.pipeline_repository import PipelineRepository


class CreatePipelineUseCase:
    """Use case for creating a new pipeline for a task."""

    def __init__(self, pipeline_repository: PipelineRepository):
        """
        Initialize the use case.

        Args:
            pipeline_repository: Repository for storing pipeline state and tasks
        """
        self.pipeline_repository = pipeline_repository

    def execute(self, task: Task) -> Tuple[Task, PipelineState]:
        """
        Create a new pipeline for a task.

        Args:
            task: The task to create a pipeline for

        Returns:
            Tuple of (saved task, initial pipeline state)
        """
        # Save the task
        saved_task = self.pipeline_repository.save_task(task)

        # Create initial pipeline state
        initial_state = PipelineState(
            id=str(uuid4()),
            task_id=saved_task.id,
            current_stage="requirements_gathering",
            stages_completed=[],
            artifacts={},
            feedback=[]
        )

        # Save the initial state
        saved_state = self.pipeline_repository.save_pipeline_state(
            initial_state)

        return saved_task, saved_state


class ExecutePipelineStageUseCase:
    """Use case for executing a stage in the pipeline."""

    def __init__(self, pipeline_repository: PipelineRepository):
        """
        Initialize the use case.

        Args:
            pipeline_repository: Repository for storing pipeline state and tasks
        """
        self.pipeline_repository = pipeline_repository

    def execute(
            self,
            pipeline_state_id: str,
            stage: PipelineStage,
            next_stage_name: Optional[str] = None
    ) -> PipelineState:
        """
        Execute a stage in the pipeline.

        Args:
            pipeline_state_id: ID of the pipeline state
            stage: The stage to execute
            next_stage_name: Optional override for the next stage name

        Returns:
            Updated pipeline state

        Raises:
            ValueError: If the stage transition is invalid
            KeyError: If the pipeline state or task is not found
        """
        # Get the current pipeline state
        pipeline_state = self.pipeline_repository.get_pipeline_state(
            pipeline_state_id)
        if not pipeline_state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        # Get the associated task
        task = self.pipeline_repository.get_task(pipeline_state.task_id)
        if not task:
            raise KeyError(f"Task with ID {pipeline_state.task_id} not found")

        # Validate that the current stage matches the stage being executed
        if pipeline_state.current_stage != stage.name:
            raise ValueError(
                f"Cannot execute {stage.name} - current stage is {pipeline_state.current_stage}")

        # Execute the stage
        previous_stage_name = pipeline_state.stages_completed[
            -1] if pipeline_state.stages_completed else None

        # Validate stage transition
        if previous_stage_name and not stage.validate_transition_from_name(
                previous_stage_name):
            raise ValueError(
                f"Invalid stage transition from {previous_stage_name} to {stage.name}")

        # Create a checkpoint before execution
        checkpoint_id = pipeline_state.create_checkpoint(f"before_{stage.name}")

        # Execute the stage
        stage_result = stage.execute(task, pipeline_state)

        # Determine the next stage
        actual_next_stage = next_stage_name or stage.get_next_stage_name()

        # Record the result in the pipeline state
        updated_state = pipeline_state.record_stage_result(
            stage_name=stage.name,
            stage_result=stage_result,
            next_stage=actual_next_stage
        )

        # Save the updated state
        return self.pipeline_repository.save_pipeline_state(updated_state)


class RollbackPipelineUseCase:
    """Use case for rolling back a pipeline to a previous checkpoint."""

    def __init__(self, pipeline_repository: PipelineRepository):
        """
        Initialize the use case.

        Args:
            pipeline_repository: Repository for storing pipeline state and tasks
        """
        self.pipeline_repository = pipeline_repository

    def execute(self, pipeline_state_id: str,
                checkpoint_id: str) -> PipelineState:
        """
        Roll back a pipeline to a previous checkpoint.

        Args:
            pipeline_state_id: ID of the pipeline state
            checkpoint_id: ID of the checkpoint to roll back to

        Returns:
            Updated pipeline state

        Raises:
            KeyError: If the pipeline state or checkpoint is not found
        """
        # Get the current pipeline state
        pipeline_state = self.pipeline_repository.get_pipeline_state(
            pipeline_state_id)
        if not pipeline_state:
            raise KeyError(
                f"Pipeline state with ID {pipeline_state_id} not found")

        # Roll back to the checkpoint
        rolled_back_state = pipeline_state.rollback_to_checkpoint(checkpoint_id)

        # Save the rolled back state
        return self.pipeline_repository.save_pipeline_state(rolled_back_state)


class GetPipelineStateUseCase:
    """Use case for retrieving pipeline state."""

    def __init__(self, pipeline_repository: PipelineRepository):
        """
        Initialize the use case.

        Args:
            pipeline_repository: Repository for storing pipeline state and tasks
        """
        self.pipeline_repository = pipeline_repository

    def execute(self, pipeline_state_id: str) -> Optional[PipelineState]:
        """
        Get a pipeline state by ID.

        Args:
            pipeline_state_id: ID of the pipeline state

        Returns:
            The pipeline state, or None if not found
        """
        return self.pipeline_repository.get_pipeline_state(pipeline_state_id)

    def execute_get_latest(self, task_id: str) -> Optional[PipelineState]:
        """
        Get the latest pipeline state for a task.

        Args:
            task_id: ID of the task

        Returns:
            The latest pipeline state, or None if not found
        """
        return self.pipeline_repository.get_latest_pipeline_state(task_id)