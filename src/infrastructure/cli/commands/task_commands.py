import click
import logging
from typing import Optional, List

from src.domain.entities.task import Task, TaskStatus
from src.infrastructure.cli.utils.dependency_container import (
    create_pipeline_repository,
    create_pipeline_use_case,
    create_execute_pipeline_stage_use_case,
    create_rollback_pipeline_use_case,
    create_rag_service,
    create_get_pipeline_state_use_case,
    create_openai_adapter, create_context_repository
)
from src.infrastructure.cli.utils.output_formatter import (
    format_success,
    format_error,
    format_task_list,
    format_task_detail,
    format_pipeline_state,
    format_rag_response
)

logger = logging.getLogger(__name__)


@click.group(name="task")
def task_group():
    """Commands for managing tasks and pipeline execution."""
    pass


@task_group.command(name="create")
@click.option("--description", "-d", required=True, help="Task description")
@click.option("--requirement", "-r", multiple=True,
              help="Task requirement (can be used multiple times)")
@click.option("--constraint", "-c", multiple=True,
              help="Task constraint (can be used multiple times)")
@click.option("--context-id", "-i", multiple=True,
              help="ID of a context item to associate with the task")
@click.option("--input-file", "-f",
              help="File with additional task description")
def create_task(
        description: str,
        requirement: List[str],
        constraint: List[str],
        context_id: List[str],
        input_file: Optional[str] = None
):
    """
    Create a new task for code generation.

    A task represents a coding job to be executed by the agent. The task
    contains requirements, constraints, and associated context items.
    """
    try:
        # Build the task input string
        task_input = description + "\n\n"

        if requirement:
            task_input += "Requirements:\n"
            for req in requirement:
                task_input += f"- {req}\n"
            task_input += "\n"

        if constraint:
            task_input += "Constraints:\n"
            for con in constraint:
                task_input += f"- {con}\n"
            task_input += "\n"

        # Read additional input from file if provided
        if input_file:
            with open(input_file, "r") as f:
                additional_input = f.read()
                task_input += additional_input

        # Parse task from input
        task = Task.parse_from_user_input(task_input)

        # Add context IDs if provided
        if context_id:
            task.context_ids = list(context_id)

        # Create pipeline for the task
        use_case = create_pipeline_use_case()
        saved_task, pipeline_state = use_case.execute(task)

        click.echo(format_success(
            f"Created task {saved_task.id}",
            format_task_detail(saved_task)
        ))

        # Show initial pipeline state
        click.echo("\nInitial pipeline state:")
        click.echo(format_pipeline_state(pipeline_state))

    except Exception as e:
        click.echo(format_error(f"Error creating task: {str(e)}"))
        logger.exception("Error in create_task command")
        raise click.Abort()


@task_group.command(name="list")
@click.option("--status", "-s",
              help="Filter by status (e.g., pending, in_progress, completed, failed)")
def list_tasks(status: Optional[str] = None):
    """
    List all tasks in the repository.

    Displays task IDs, descriptions, and statuses. Can be filtered by status.
    """
    try:
        repo = create_pipeline_repository()

        # Convert status string to enum if provided
        status_enum = None
        if status:
            try:
                status_enum = TaskStatus(status)
            except ValueError:
                valid_statuses = [s.value for s in TaskStatus]
                click.echo(format_error(
                    f"Invalid status: {status}. Valid values: {', '.join(valid_statuses)}"))
                return

        tasks = repo.list_tasks(status_enum)

        if not tasks:
            click.echo("No tasks found.")
        else:
            # Get the latest pipeline state ID for each task
            task_states = {}
            for task in tasks:
                latest_state = repo.get_latest_pipeline_state(task.id)
                if latest_state:
                    task_states[task.id] = latest_state.id

            click.echo(format_task_list(tasks, task_states))

    except Exception as e:
        click.echo(format_error(f"Error listing tasks: {str(e)}"))
        logger.exception("Error in list_tasks command")
        raise click.Abort()


@task_group.command(name="execute")
@click.option("--pipeline-state-id", "-p", required=True,
              help="ID of the pipeline state to execute")
@click.option("--stage", "-s", required=True, help="Stage to execute")
@click.option("--next-stage", "-n",
              help="Next stage to transition to after execution")
def execute_task(pipeline_state_id: str, stage: str,
                 next_stage: Optional[str] = None):
    """
    Execute a stage in the pipeline.

    Runs the specified stage of the pipeline and updates the pipeline state.
    """
    try:
        use_case = create_execute_pipeline_stage_use_case()

        # Get the current pipeline state
        get_state_use_case = create_get_pipeline_state_use_case()
        current_state = get_state_use_case.execute(pipeline_state_id)

        if not current_state:
            click.echo(format_error(
                f"Pipeline state with ID {pipeline_state_id} not found"))
            return

        # Get the LLM provider
        openai_adapter = create_openai_adapter()
        # Get the Context repository
        mongo_context_repository = create_context_repository()
        # Get the RAG service
        rag_service = create_rag_service()

        # Create the appropriate stage instance
        from src.application.pipeline.stage_factory import create_pipeline_stage
        stage_instance = create_pipeline_stage(
            stage,
            llm_provider=openai_adapter,
            context_repository=mongo_context_repository,
            rag_service=rag_service,
        )

        if not stage_instance:
            valid_stages = ", ".join(current_state.PIPELINE_STAGES)
            click.echo(format_error(
                f"Invalid stage: {stage}. Valid stages: {valid_stages}"))
            return

        # Execute the stage
        updated_state = use_case.execute(pipeline_state_id, stage_instance,
                                         next_stage)

        click.echo(format_success(
            f"Successfully executed stage {stage}",
            format_pipeline_state(updated_state)
        ))

    except Exception as e:
        click.echo(format_error(f"Error executing task stage: {str(e)}"))
        logger.exception("Error in execute_task command")
        raise click.Abort()


@task_group.command(name="rollback")
@click.option("--pipeline-state-id", "-p", required=True,
              help="ID of the pipeline state to roll back")
@click.option("--checkpoint-id", "-c", required=True,
              help="ID of the checkpoint to roll back to")
def rollback_task(pipeline_state_id: str, checkpoint_id: str):
    """
    Roll back a pipeline to a previous checkpoint.

    Resets the pipeline state to the specified checkpoint, discarding any changes
    made after the checkpoint was created.
    """
    try:
        use_case = create_rollback_pipeline_use_case()

        # Roll back to the checkpoint
        updated_state = use_case.execute(pipeline_state_id, checkpoint_id)

        click.echo(format_success(
            f"Successfully rolled back to checkpoint {checkpoint_id}",
            format_pipeline_state(updated_state)
        ))

    except Exception as e:
        click.echo(format_error(f"Error rolling back pipeline: {str(e)}"))
        logger.exception("Error in rollback_task command")
        raise click.Abort()


@task_group.command(name="status")
@click.option("--pipeline-state-id", "-p", required=True,
              help="ID of the pipeline state")
def get_task_status(pipeline_state_id: str):
    """
    Get the current status of a pipeline.

    Displays the current stage, completed stages, and available checkpoints.
    """
    try:
        use_case = create_get_pipeline_state_use_case()
        pipeline_state = use_case.execute(pipeline_state_id)

        if not pipeline_state:
            click.echo(format_error(
                f"Pipeline state with ID {pipeline_state_id} not found"))
            return

        click.echo(format_pipeline_state(pipeline_state))

    except Exception as e:
        click.echo(format_error(f"Error getting task status: {str(e)}"))
        logger.exception("Error in get_task_status command")
        raise click.Abort()

@task_group.command(name="query")
@click.option("--text", "-t", required=True, help="Query text")
def query_context(text: str):
    """Query the system using RAG to get information."""
    try:
        rag_service = create_rag_service()
        response = rag_service.generate_with_context(text)
        click.echo(format_rag_response(response))
    except Exception as e:
        click.echo(format_error(f"Error querying: {str(e)}"))
        logger.exception("Error in query_context command")
        raise click.Abort()