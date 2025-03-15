"""
Pipeline executor for executing individual pipeline stages.

This module provides the PipelineExecutor class that handles the execution
of individual pipeline stages and manages the pipeline state.
"""
import logging
from datetime import datetime
from typing import Optional

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageStatus
from src.domain.ports.pipeline_repository import PipelineRepository


class PipelineExecutor:
    """
    Executes individual pipeline stages and manages pipeline state transitions.

    This class is responsible for:
    - Executing a single stage in the pipeline
    - Validating stage transitions
    - Creating checkpoints
    - Managing stage-specific error handling
    """

    def __init__(self, pipeline_repository: PipelineRepository):
        """
        Initialize the pipeline executor.

        Args:
            pipeline_repository: Repository for storing pipeline state and tasks
        """
        self.pipeline_repository = pipeline_repository
        self.logger = logging.getLogger(__name__)

    def execute_stage(
            self,
            pipeline_state_id: str,
            stage: PipelineStage,
            next_stage_name: Optional[str] = None,
            create_checkpoint: bool = False,
            use_transaction: bool = False
    ) -> PipelineState:
        """
        Execute a single stage in the pipeline.

        Args:
            pipeline_state_id: ID of the pipeline state
            stage: The stage to execute
            next_stage_name: Optional override for the next stage name
            create_checkpoint: Whether to create a checkpoint before execution
            use_transaction: Whether to use a transaction for the operation

        Returns:
            Updated pipeline state

        Raises:
            KeyError: If the pipeline state or task is not found
            ValueError: If the stage transition is invalid
        """
        # Start a transaction if requested
        session = None
        if use_transaction:
            session = self.pipeline_repository.start_transaction()

        try:
            # Get the current pipeline state
            pipeline_state = self.pipeline_repository.get_pipeline_state(
                pipeline_state_id)
            if not pipeline_state:
                raise KeyError(
                    f"Pipeline state with ID {pipeline_state_id} not found")

            try:
                previous_stage = pipeline_state.stages_completed[-1]
            except IndexError:
                previous_stage = ""

            # Get the associated task
            task = self.pipeline_repository.get_task(pipeline_state.task_id)
            if not task:
                raise KeyError(
                    f"Task with ID {pipeline_state.task_id} not found")

            # Validate stage transition
            self.logger.debug(
                f"Validating transition from {previous_stage if previous_stage else "initial state"} to {stage.name}")
            if not stage.validate_transition_from_name(previous_stage):
                raise ValueError(
                    f"Invalid pipeline transition from {previous_stage if previous_stage else "initial state"} to {stage.name}"
                )

            # Create a checkpoint if requested
            if create_checkpoint:
                self.logger.info(
                    f"Creating checkpoint before executing stage {stage.name}")
                checkpoint_id = pipeline_state.create_checkpoint(
                    f"before_{stage.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                pipeline_state = self.pipeline_repository.save_pipeline_state(
                    pipeline_state)

            # Execute the stage
            self.logger.info(f"Executing stage {stage.name} for task {task.id}")
            stage_result = stage.execute(task, pipeline_state)

            # Determine the next stage
            actual_next_stage = next_stage_name or stage.get_next_stage_name()

            # Record the result in the pipeline state
            if stage_result.status == PipelineStageStatus.COMPLETED:
                self.logger.info(f"Stage {stage.name} completed successfully")
                updated_state = pipeline_state.record_stage_result(
                    stage_name=stage.name,
                    stage_result=stage_result,
                    next_stage=actual_next_stage
                )
            else:
                self.logger.warning(
                    f"Stage {stage.name} did not complete successfully: {stage_result.error}")
                # Just record the output without changing the stage
                updated_state = pipeline_state.record_stage_result(
                    stage_name=stage.name,
                    stage_result=stage_result,
                    next_stage=pipeline_state.current_stage
                    # Stay on the same stage
                )

            # Save the updated state
            updated_state = self.pipeline_repository.save_pipeline_state(
                updated_state)

            # Commit the transaction if we started one
            if use_transaction and session:
                self.pipeline_repository.commit_transaction(session)

            return updated_state

        except Exception as e:
            # Rollback the transaction if we started one
            if use_transaction and session:
                self.pipeline_repository.abort_transaction(session)

            self.logger.error(f"Error executing stage {stage.name}: {str(e)}",
                              exc_info=True)
            raise