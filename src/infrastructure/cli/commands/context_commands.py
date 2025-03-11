import click
import logging
from typing import Optional, List

from src.domain.usecases.context_management import (
    AddContextUseCase,
    RemoveContextUseCase,
    UpdateContextUseCase,
    ListContextUseCase,
    SearchContextUseCase
)
from src.infrastructure.cli.utils.dependency_container import (
    create_add_context_use_case,
    create_remove_context_use_case,
    create_list_context_use_case,
    create_search_context_use_case
)
from src.infrastructure.cli.utils.output_formatter import (
    format_success,
    format_error,
    format_context_item,
    format_context_list,
    format_search_results
)

logger = logging.getLogger(__name__)


@click.group(name="context")
def context_group():
    """Commands for managing context items."""
    pass


@context_group.command(name="add")
@click.option("--file", "-f", required=True,
              help="Path to the file to add to the context")
def add_context(file: str):
    """
    Add a file to the context repository.

    This command reads a file and adds it to the context repository for
    use in the code generation pipeline.
    """
    try:
        use_case = create_add_context_use_case()
        context_item = use_case.execute_from_file_path(file)

        click.echo(format_success(
            f"Successfully added context item from {file}",
            {"id": context_item.id, "source": context_item.source}
        ))
    except Exception as e:
        click.echo(format_error(f"Error adding context item: {str(e)}"))
        logger.exception("Error in add_context command")
        raise click.Abort()


@context_group.command(name="list")
@click.option("--content-type", "-t",
              help="Filter by content type (e.g., python, markdown)")
def list_contexts(content_type: Optional[str] = None):
    """
    List context items in the repository.

    Displays all context items or filters by content type if specified.
    """
    try:
        use_case = create_list_context_use_case()
        filters = {"content_type": content_type} if content_type else None
        items = use_case.execute(filters)

        if not items:
            click.echo("No context items found.")
        else:
            click.echo(format_context_list(items))
    except Exception as e:
        click.echo(format_error(f"Error listing context items: {str(e)}"))
        logger.exception("Error in list_contexts command")
        raise click.Abort()


@context_group.command(name="remove")
@click.option("--id", "-i", required=True,
              help="ID of the context item to remove")
def remove_context(id: str):
    """
    Remove a context item from the repository.

    Deletes the context item with the specified ID.
    """
    try:
        use_case = create_remove_context_use_case()
        result = use_case.execute(id)

        if result:
            click.echo(
                format_success(f"Successfully removed context item {id}"))
        else:
            click.echo(format_error(f"Failed to remove context item {id}"))
    except Exception as e:
        click.echo(format_error(f"Error removing context item: {str(e)}"))
        logger.exception("Error in remove_context command")
        raise click.Abort()


@context_group.command(name="search")
@click.option("--query", "-q", required=True, help="Search query")
@click.option("--limit", "-l", type=int, default=10,
              help="Maximum number of results")
def search_context(query: str, limit: int = 10):
    """
    Search for context items using semantic similarity.

    Returns context items that are semantically similar to the query.
    """
    try:
        use_case = create_search_context_use_case()
        results = use_case.execute(query, limit)

        if not results:
            click.echo("No matching context items found.")
        else:
            click.echo(format_search_results(results))
    except Exception as e:
        click.echo(format_error(f"Error searching context items: {str(e)}"))
        logger.exception("Error in search_context command")
        raise click.Abort()