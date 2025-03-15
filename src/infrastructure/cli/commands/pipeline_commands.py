"""
CLI integration with pipeline orchestration components.

This shows how to integrate the pipeline orchestration components with the CLI commands.
"""
import click
import logging
from typing import Optional

from src.domain.entities.task import Task
from src.infrastructure.cli.utils.dependency_container import (
    create_pipeline_repository,
    create_pipeline_executor,
    create_state_manager,
    create_feedback_manager,
    create_pipeline_stage_with_dependencies
)
from src.infrastructure.cli.utils.output_formatter import (
    format_success,
    format_error,
    format_pipeline_state,
    format_task_detail
)
from src.application.pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)


def create_pipeline_orchestrator():
    """Create a PipelineOrchestrator with all required dependencies."""
    pipeline_repository = create_pipeline_repository()
    pipeline_executor = create_pipeline_executor()
    state_manager = create_state_manager()
    feedback_manager = create_feedback_manager()

    def stage_factory(stage_name):
        return create_pipeline_stage_with_dependencies(stage_name)

    return PipelineOrchestrator(
        pipeline_repository=pipeline_repository,
        pipeline_executor=pipeline_executor,
        state_manager=state_manager,
        feedback_manager=feedback_manager,
        stage_factory=stage_factory
    )


@click.group(name="pipeline")
def pipeline_group():
    """Commands for executing and managing pipelines."""
    pass


@pipeline_group.command(name="execute")
@click.option("--task-id", "-t", required=True,
              help="ID of the task to execute")
@click.option("--continue", "-c", "continue_from_current", is_flag=True,
              help="Continue from current state instead of starting from beginning")
@click.option("--checkpoints", "-k", is_flag=True,
              help="Create checkpoints before each stage")
@click.option("--feedback", "-f", is_flag=True,
              help="Pause for feedback after each stage")
@click.option("--transactions", "-x", is_flag=True,
              help="Use transactions for state updates")
def execute_pipeline(task_id: str, continue_from_current: bool = False,
                     checkpoints: bool = False, feedback: bool = False,
                     transactions: bool = False):
    """
    Execute the complete pipeline for a task.

    Runs all stages of the pipeline from beginning to end, or continues
    from the current state if --continue is specified.
    """
    try:
        orchestrator = create_pipeline_orchestrator()

        # Execute the pipeline
        final_state = orchestrator.execute_pipeline(
            task_id=task_id,
            continue_from_current=continue_from_current,
            create_checkpoints=checkpoints,
            wait_for_feedback=feedback,
            use_transactions=transactions
        )

        click.echo(format_success(
            "Pipeline execution completed",
            format_pipeline_state(final_state)
        ))

    except Exception as e:
        click.echo(format_error(f"Error executing pipeline: {str(e)}"))
        logger.exception("Error in execute_pipeline command")
        raise click.Abort()


@pipeline_group.command(name="execute-stage")
@click.option("--task-id", "-t", required=True, help="ID of the task")
@click.option("--pipeline-state-id", "-p", required=True,
              help="ID of the pipeline state")
@click.option("--stage", "-s", required=True,
              help="Name of the stage to execute")
@click.option("--no-checkpoint", "-n", is_flag=True,
              help="Skip creating a checkpoint before execution")
def execute_single_stage(task_id: str, pipeline_state_id: str,
                         stage: str, no_checkpoint: bool = False):
    """
    Execute a single stage in the pipeline.

    Runs the specified stage and updates the pipeline state.
    """
    try:
        orchestrator = create_pipeline_orchestrator()

        # Execute the stage
        updated_state = orchestrator.execute_single_stage(
            task_id=task_id,
            pipeline_state_id=pipeline_state_id,
            stage_name=stage,
            create_checkpoint=not no_checkpoint
        )

        click.echo(format_success(
            f"Successfully executed stage {stage}",
            format_pipeline_state(updated_state)
        ))

    except Exception as e:
        click.echo(format_error(f"Error executing stage: {str(e)}"))
        logger.exception("Error in execute_single_stage command")
        raise click.Abort()


@pipeline_group.command(name="rollback")
@click.option("--pipeline-state-id", "-p", required=True,
              help="ID of the pipeline state")
@click.option("--checkpoint-id", "-c", required=True,
              help="ID of the checkpoint to roll back to")
def rollback_pipeline(pipeline_state_id: str, checkpoint_id: str):
    """
    Roll back a pipeline to a previous checkpoint.

    Resets the pipeline state to the specified checkpoint.
    """
    try:
        state_manager = create_state_manager()

        # Roll back the pipeline
        rolled_back_state = state_manager.rollback_to_checkpoint(
            pipeline_state_id=pipeline_state_id,
            checkpoint_id=checkpoint_id
        )

        click.echo(format_success(
            f"Successfully rolled back to checkpoint {checkpoint_id}",
            format_pipeline_state(rolled_back_state)
        ))

    except Exception as e:
        click.echo(format_error(f"Error rolling back pipeline: {str(e)}"))
        logger.exception("Error in rollback_pipeline command")
        raise click.Abort()


@pipeline_group.command(name="list-checkpoints")
@click.option("--pipeline-state-id", "-p", required=True,
              help="ID of the pipeline state")
def list_checkpoints(pipeline_state_id: str):
    """
    List all checkpoints in a pipeline state.

    Displays checkpoint IDs, stages, and timestamps.
    """
    try:
        state_manager = create_state_manager()

        # Get the checkpoints
        checkpoints = state_manager.list_checkpoints(pipeline_state_id)

        if not checkpoints:
            click.echo("No checkpoints found.")
            return

        # Display checkpoints
        click.echo("Checkpoints:")
        for i, checkpoint in enumerate(checkpoints, 1):
            click.echo(f"{i}. ID: {click.style(checkpoint['id'], fg='blue')}")
            click.echo(f"   Stage: {checkpoint['stage']}")
            click.echo(f"   Timestamp: {checkpoint['timestamp']}")
            click.echo("")

    except Exception as e:
        click.echo(format_error(f"Error listing checkpoints: {str(e)}"))
        logger.exception("Error in list_checkpoints command")
        raise click.Abort()


@pipeline_group.command(name="progress")
@click.option("--pipeline-state-id", "-p", required=True,
              help="ID of the pipeline state")
def show_progress(pipeline_state_id: str):
    """
    Show the progress of a pipeline.

    Displays the current stage, completed stages, and percentage complete.
    """
    try:
        state_manager = create_state_manager()

        # Get the progress
        progress = state_manager.get_pipeline_progress(pipeline_state_id)

        # Display progress
        click.echo("Pipeline Progress:")
        click.echo(
            f"Current stage: {click.style(progress['current_stage'], fg='yellow', bold=True)}")
        click.echo(
            f"Completed stages: {', '.join(progress['completed_stages']) if progress['completed_stages'] else 'None'}")
        click.echo(
            f"Progress: {progress['percentage']:.1f}% ({len(progress['completed_stages'])}/{progress['total_stages']} stages)")

        # Create a simple progress bar
        bar_length = 40
        completed_length = int(bar_length * progress['percentage'] / 100)
        progress_bar = "[" + "#" * completed_length + "-" * (
                    bar_length - completed_length) + "]"
        click.echo(progress_bar)

    except Exception as e:
        click.echo(format_error(f"Error showing progress: {str(e)}"))
        logger.exception("Error in show_progress command")
        raise click.Abort()
