"""
Pipeline orchestrator for coordinating the entire pipeline execution.

This module provides the PipelineOrchestrator class that handles the
high-level coordination of pipeline execution, feedback, and error handling.
"""
import contextlib
import logging
import time
from typing import Optional, List, Dict, Any, Callable, Union

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageStatus
from src.domain.ports.pipeline_repository import PipelineRepository
from src.application.pipeline.executor import PipelineExecutor
from src.application.pipeline.state_manager import StateManager
from src.application.pipeline.feedback_manager import FeedbackManager


class PipelineOrchestrator:
    """
    Orchestrates the execution of the entire pipeline.

    This class is responsible for:
    - Coordinating execution of all pipeline stages
    - Managing state transitions
    - Creating checkpoints
    - Handling errors
    - Pausing for feedback
    """

    def __init__(
            self,
            pipeline_repository: PipelineRepository,
            pipeline_executor: PipelineExecutor,
            state_manager: StateManager,
            feedback_manager: FeedbackManager,
            stage_factory: Callable[[str], Optional[PipelineStage]]
    ):
        """
        Initialize the pipeline orchestrator.

        Args:
            pipeline_repository: Repository for pipeline state and tasks
            pipeline_executor: Executor for individual pipeline stages
            state_manager: Manager for pipeline state operations
            feedback_manager: Manager for feedback operations
            stage_factory: Factory function for creating pipeline stages
        """
        self.pipeline_repository = pipeline_repository
        self.pipeline_executor = pipeline_executor
        self.state_manager = state_manager
        self.feedback_manager = feedback_manager
        self.stage_factory = stage_factory
        self.logger = logging.getLogger(__name__)

    def execute_pipeline(
            self,
            task_id: str,
            continue_from_current: bool = False,
            create_checkpoints: bool = False,
            wait_for_feedback: bool = False,
            use_transactions: bool = False
    ) -> PipelineState:
        """
        Execute the complete pipeline for a task.

        Args:
            task_id: ID of the task to execute
            continue_from_current: Whether to continue from the current state instead of starting from beginning
            create_checkpoints: Whether to create checkpoints before each stage
            wait_for_feedback: Whether to pause for feedback after each stage
            use_transactions: Whether to use transactions for state updates

        Returns:
            Final pipeline state

        Raises:
            KeyError: If the task is not found
        """
        self.logger.info(f"Starting pipeline execution for task {task_id}")

        # Get the task
        task = self.pipeline_repository.get_task(task_id)
        if not task:
            raise KeyError(f"Task with ID {task_id} not found")

        # Get or create the pipeline state
        if continue_from_current:
            # Get the latest pipeline state for the task
            state = self.state_manager.get_latest_pipeline_state(task_id)
            if not state:
                # If no state exists, create an initial one
                self.logger.info(
                    f"No existing pipeline state found for task {task_id}, creating a new one")
                state = self.state_manager.create_initial_state(task)
        else:
            # Create a new initial state
            self.logger.info(f"Creating new pipeline state for task {task_id}")
            state = self.state_manager.create_initial_state(task)

        try:
            # Execute all stages from the current state
            state = self._execute_stages_from_current(
                state,
                create_checkpoints=create_checkpoints,
                wait_for_feedback=wait_for_feedback,
                use_transactions=use_transactions
            )

            self.logger.info(f"Pipeline execution completed for task {task_id}")
            return state

        except Exception as e:
            self.logger.error(
                f"Error during pipeline execution for task {task_id}: {str(e)}",
                exc_info=True)
            # Try to handle the error and recover
            current_stage_name = state.current_stage
            stage = self.stage_factory(current_stage_name)
            return self._handle_execution_error(e, state, stage)

    def execute_single_stage(
            self,
            task_id: str,
            pipeline_state_id: str,
            stage_name: str,
            create_checkpoint: bool = True
    ) -> PipelineState:
        """
        Execute a single stage in the pipeline.

        Args:
            task_id: ID of the task
            pipeline_state_id: ID of the pipeline state
            stage_name: Name of the stage to execute
            create_checkpoint: Whether to create a checkpoint before execution

        Returns:
            Updated pipeline state

        Raises:
            KeyError: If the task or pipeline state is not found
            ValueError: If the stage name is invalid
        """
        self.logger.info(
            f"Executing single stage {stage_name} for task {task_id}")

        # Create the stage
        stage = self.stage_factory(stage_name)
        if not stage:
            raise ValueError(f"Invalid stage name: {stage_name}")

        # Execute the stage
        updated_state = self.pipeline_executor.execute_stage(
            pipeline_state_id=pipeline_state_id,
            stage=stage,
            create_checkpoint=create_checkpoint
        )

        return updated_state

    def _execute_stages_from_current(
            self,
            state: PipelineState,
            create_checkpoints: bool = False,
            wait_for_feedback: bool = False,
            use_transactions: bool = False
    ) -> PipelineState:
        """
        Execute all stages from the current state to completion.

        Args:
            state: Current pipeline state
            create_checkpoints: Whether to create checkpoints before each stage
            wait_for_feedback: Whether to pause for feedback after each stage
            use_transactions: Whether to use transactions for state updates

        Returns:
            Updated pipeline state
        """
        current_state = state

        # Get all pipeline stages in order
        all_stages = PipelineState.PIPELINE_STAGES

        # Find the index of the current stage
        try:
            current_idx = all_stages.index(current_state.current_stage)
        except ValueError:
            self.logger.error(
                f"Invalid current stage: {current_state.current_stage}")
            current_idx = 0  # Start from the beginning if stage is invalid

        # Execute each stage in sequence
        while current_idx < len(all_stages):
            stage_name = all_stages[current_idx]

            # Create the stage
            stage = self.stage_factory(stage_name)
            if not stage:
                self.logger.error(f"Failed to create stage {stage_name}")
                current_idx += 1
                continue

            self.logger.info(
                f"Executing stage {stage_name} for task {current_state.task_id}")

            # Use a transaction context if requested
            with self.state_manager.transaction() if use_transactions else contextlib.nullcontext():
                try:
                    # Execute the stage
                    updated_state = self.pipeline_executor.execute_stage(
                        pipeline_state_id=current_state.id,
                        stage=stage,
                        create_checkpoint=create_checkpoints,
                        use_transaction=use_transactions
                    )

                    # Update the current state
                    current_state = updated_state

                    # Wait for feedback if requested
                    if wait_for_feedback and current_idx < len(
                            all_stages) - 1:  # Don't wait after the last stage
                        self.logger.info(
                            f"Waiting for feedback after stage {stage_name}")
                        if self._wait_for_feedback(current_state):
                            # Incorporate feedback
                            current_state = self.feedback_manager.incorporate_all_feedback(
                                current_state.id)

                    # Update the current index based on the new state
                    try:
                        if all_stages[current_idx] == all_stages[-1]:
                            break

                        current_idx = all_stages.index(
                            current_state.current_stage)
                    except ValueError:
                        self.logger.error(
                            f"Invalid current stage after execution: {current_state.current_stage}")
                        current_idx += 1

                except Exception as e:
                    self.logger.error(
                        f"Error executing stage {stage_name}: {str(e)}",
                        exc_info=True)
                    # Try to handle the error and recover
                    current_state = self._handle_execution_error(e,
                                                                 current_state,
                                                                 stage)

                    # Update the current index based on the recovered state
                    try:
                        current_idx = all_stages.index(
                            current_state.current_stage)
                    except ValueError:
                        self.logger.error(
                            f"Invalid current stage after error recovery: {current_state.current_stage}")
                        current_idx += 1

        return current_state

    def _wait_for_feedback(self, state: PipelineState) -> bool:
        """
        Wait for human feedback after a stage execution.

        This is a simple interactive implementation that asks the user
        if they want to provide feedback.

        Args:
            state: Current pipeline state

        Returns:
            True if feedback was provided, False otherwise
        """
        print(f"\n=== Stage {state.current_stage} completed ===")
        print(
            f"Current progress: {len(state.stages_completed)}/{len(state.PIPELINE_STAGES)} stages")
        print("Would you like to provide feedback before continuing? (y/n)")

        try:
            response = input().strip().lower()
            return response == 'y' or response == 'yes'
        except Exception as e:
            self.logger.error(f"Error during feedback prompt: {str(e)}")
            return False

    def _handle_execution_error(self, error: Exception, state: PipelineState,
                                stage: PipelineStage) -> PipelineState:
        """
        Handle errors during pipeline execution.

        Currently implements a simple strategy:
        1. Roll back to the latest checkpoint if available
        2. If no checkpoint is available, stay at the current stage

        Args:
            error: The exception that occurred
            state: Current pipeline state
            stage: The stage that failed

        Returns:
            Recovered pipeline state
        """
        self.logger.error(
            f"Handling error during execution of stage {state.current_stage}: {str(error)}")

        # Print error information
        print(
            f"\n=== Error during execution of stage {state.current_stage} ===")
        print(f"Error: {str(error)}")

        # Try to roll back to the latest checkpoint
        rolled_back_state = self.state_manager.rollback_to_latest_checkpoint(
            state.id)

        if rolled_back_state:
            print(
                f"Rolled back to checkpoint at stage {rolled_back_state.current_stage}")
            return rolled_back_state
        else:
            print(
                "No checkpoint available for rollback, staying at current stage")
            return state