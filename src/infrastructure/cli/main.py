import click
import os
import sys
import logging
from typing import List

from dotenv import load_dotenv

from src.infrastructure.cli.commands.context_commands import context_group
from src.infrastructure.cli.commands.task_commands import task_group
from src.infrastructure.cli.commands.feedback_commands import feedback_group
from src.infrastructure.cli.utils.output_formatter import format_error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("walk-cli")


@click.group()
@click.version_option(package_name="walk")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def cli(verbose: bool):
    """
    CLI for the Walk Agentic Coding System.

    Use this tool to manage context, tasks, and the code generation pipeline.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


# Add command groups
cli.add_command(context_group)
cli.add_command(task_group)
cli.add_command(feedback_group)


def main():
    """Entry point for the CLI."""
    try:
        load_dotenv()
        cli()
    except Exception as e:
        click.echo(format_error(f"Unexpected error: {str(e)}"))
        logger.exception("Unhandled exception")
        sys.exit(1)


if __name__ == "__main__":
    main()