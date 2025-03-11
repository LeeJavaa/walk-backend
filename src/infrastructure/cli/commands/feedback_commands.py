import click
import logging
from typing import Optional
import sys

from src.domain.usecases.feedback_management import (
    SubmitFeedbackUseCase,
    IncorporateFeedbackUseCase
)
from src.infrastructure.cli.utils.dependency_container import (
    create_submit_feedback_use_case,
    create_incorporate_feedback_use_case
)
from src.infrastructure.cli.utils.output_formatter import (
    format_success,
    format_error,
    format_feedback
)

logger = logging.getLogger(__name__)


@click.group(name="feedback")
def feedback_group():
    """Commands for providing feedback to the pipeline."""
    pass


@feedback_group.command(name="submit")
@click.option("--pipeline-state-id", "-p", required=True,
              help="ID of the pipeline state")
@click.option("--stage", "-s", required=True,
              help="Stage to provide feedback for")
@click.option("--content", "-c", help="Feedback content")
@click.option("--type", "-t",
              type=click.Choice(["suggestion", "correction", "enhancement"]),
              default="suggestion", help="Type of feedback")
@click.option("--interactive", "-i", is_flag=True,
              help="Provide feedback interactively")
def submit_feedback(
        pipeline_state_id: str,
        stage: str,
        content: Optional[str] = None,
        type: str = "suggestion",
        interactive: bool = False
):
    """
    Submit feedback for a pipeline stage.

    Provides human feedback to improve the output of a pipeline stage.
    """
    try:
        # If interactive mode is enabled, prompt for feedback content
        if interactive:
            click.echo("Enter your feedback (press Enter twice when done):")

            lines = []
            while True:
                line = input()
                if not line and (not lines or not lines[-1]):
                    break
                lines.append(line)

            content = "\n".join(lines)

            # Prompt for feedback type if not provided
            if type == "suggestion":
                type_options = ["suggestion", "correction", "enhancement"]
                click.echo(f"Enter feedback type ({'/'.join(type_options)}):")
                entered_type = input().strip().lower()
                if entered_type in type_options:
                    type = entered_type

        # Ensure content is provided
        if not content:
            click.echo(format_error(
                "Feedback content is required. Use --content or --interactive option."))
            return

        # Submit the feedback
        use_case = create_submit_feedback_use_case()
        updated_state = use_case.execute(pipeline_state_id, stage, content,
                                         type)

        click.echo(format_success(
            "Successfully submitted feedback",
            {"pipeline_state_id": updated_state.id, "stage": stage,
             "type": type}
        ))

    except Exception as e:
        click.echo(format_error(f"Error submitting feedback: {str(e)}"))
        logger.exception("Error in submit_feedback command")
        raise click.Abort()


@feedback_group.command(name="incorporate")
@click.option("--pipeline-state-id", "-p", required=True,
              help="ID of the pipeline state")
@click.option("--feedback-id", "-f", multiple=True,
              help="ID of specific feedback to incorporate")
@click.option("--all", "-a", is_flag=True,
              help="Incorporate all available feedback")
def incorporate_feedback(
        pipeline_state_id: str,
        feedback_id: Optional[list] = None,
        all: bool = False
):
    """
    Incorporate feedback into the pipeline.

    Applies submitted feedback to update the pipeline state.
    """
    try:
        use_case = create_incorporate_feedback_use_case()

        if all:
            # Incorporate all feedback with prioritization
            updated_state = use_case.execute_prioritized(pipeline_state_id)

            click.echo(format_success(
                "Successfully incorporated all feedback",
                {"pipeline_state_id": updated_state.id}
            ))
        elif feedback_id:
            # Incorporate specific feedback items
            updated_state = use_case.execute(pipeline_state_id,
                                             list(feedback_id))

            click.echo(format_success(
                "Successfully incorporated specified feedback",
                {"pipeline_state_id": updated_state.id,
                 "feedback_ids": list(feedback_id)}
            ))
        else:
            click.echo(format_error("Please specify --feedback-id or --all"))
            return

    except Exception as e:
        click.echo(format_error(f"Error incorporating feedback: {str(e)}"))
        logger.exception("Error in incorporate_feedback command")
        raise click.Abort()