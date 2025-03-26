import click
import logging
from typing import Optional, List

from src.infrastructure.cli.utils.dependency_container import (
    create_add_context_use_case,
    create_remove_context_use_case,
    create_list_context_use_case,
    create_search_context_use_case,
    create_add_directory_use_case,
    create_create_container_use_case,
    create_list_containers_use_case
)
from src.infrastructure.cli.utils.output_formatter import (
    format_success,
    format_error,
    format_context_item,
    format_context_list,
    format_search_results,
    format_container_list,
    format_container
)

logger = logging.getLogger(__name__)


@click.group(name="context")
def context_group():
    """Commands for managing context items and containers."""
    pass


@context_group.command(name="add")
@click.option("--file", "-f", required=True,
              help="Path to the file to add to the context")
@click.option("--container", "-c",
              help="ID of the container to add the file to")
@click.option("--root", "-r", is_flag=True, default=False,
              help="Mark this file as a container root item")
def add_context(file: str, container: Optional[str] = None, root: bool = False):
    """
    Add a file to the context repository.

    This command reads a file and adds it to the context repository for
    use in the code generation pipeline. Optionally associates the file
    with a container.
    """
    try:
        use_case = create_add_context_use_case()
        context_item = use_case.execute_from_file_path(
            file,
            container_id=container,
            is_container_root=root
        )

        result_data = {
            "id": context_item.id,
            "source": context_item.source
        }

        if container:
            result_data["container_id"] = container

        click.echo(format_success(
            f"Successfully added context item from {file}",
            result_data
        ))
    except Exception as e:
        click.echo(format_error(f"Error adding context item: {str(e)}"))
        logger.exception("Error in add_context command")
        raise click.Abort()


@context_group.command(name="add-directory")
@click.option("--directory", "-d", required=True,
              help="Path to the directory to add")
@click.option("--depth", type=int, default=10,
              help="Maximum depth for directory traversal (default: 10)")
@click.option("--file-type", "-t", multiple=True,
              help="File extensions to include (e.g., .py, .md) - can specify multiple")
@click.option("--container", "-c",
              help="ID of an existing container to add files to")
@click.option("--title",
              help="Title for a new container (if not using existing)")
@click.option("--type", "container_type", default="code",
              type=click.Choice(["code", "documentation", "mixed", "other"]),
              help="Type of container (default: code)")
@click.option("--description", default="",
              help="Description of the container")
@click.option("--priority", type=int, default=5,
              help="Priority level for the container (1-10, default: 5)")
def add_directory(
        directory: str,
        depth: int = 10,
        file_type: Optional[List[str]] = None,
        container: Optional[str] = None,
        title: Optional[str] = None,
        container_type: str = "code",
        description: str = "",
        priority: int = 5
):
    """
    Add an entire directory to the context system.

    This command processes a directory and adds all files to the context system.
    It can either create a new container for the directory or add to an existing one.

    By default, it traverses the directory recursively up to a depth of 10 levels,
    but this can be configured with the --depth option.
    """
    try:
        use_case = create_add_directory_use_case()

        # Convert file_type tuples to list
        file_types = list(file_type) if file_type else None

        result = use_case.execute(
            directory_path=directory,
            max_depth=depth,
            file_types=file_types,
            container_id=container,
            container_title=title,
            container_type=container_type,
            container_description=description,
            container_priority=priority
        )

        # Format the output
        container_info = result["container"]
        total_files = result["total_files"]

        click.echo(format_success(
            f"Successfully added directory {directory}",
            {
                "container_id": container_info.id,
                "container_name": container_info.name,
                "container_title": container_info.title,
                "files_added": f"{total_files} files"
            }
        ))

    except Exception as e:
        click.echo(format_error(f"Error adding directory: {str(e)}"))
        logger.exception("Error in add_directory command")
        raise click.Abort()


@context_group.command(name="create-container")
@click.option("--name", "-n", required=True,
              help="Machine-friendly name for the container")
@click.option("--title", "-t", required=True,
              help="Human-readable title for the container")
@click.option("--type", "container_type", default="code",
              type=click.Choice(["code", "documentation", "mixed", "other"]),
              help="Type of container (default: code)")
@click.option("--path", "-p", required=True,
              help="Source path for this container")
@click.option("--description", "-d", default="",
              help="Description of the container")
@click.option("--priority", type=int, default=5,
              help="Priority level (1-10, default: 5)")
def create_container(
        name: str,
        title: str,
        container_type: str,
        path: str,
        description: str = "",
        priority: int = 5
):
    """
    Create a new container for organizing context items.

    Containers group related context items and can represent code repositories,
    documentation sets, or other logical groupings.
    """
    try:
        use_case = create_create_container_use_case()

        container = use_case.execute(
            name=name,
            title=title,
            container_type=container_type,
            source_path=path,
            description=description,
            priority=priority
        )

        click.echo(format_success(
            f"Successfully created container {title}",
            {
                "id": container.id,
                "name": container.name,
                "title": container.title,
                "type": container.container_type.value,
                "priority": container.priority
            }
        ))

    except Exception as e:
        click.echo(format_error(f"Error creating container: {str(e)}"))
        logger.exception("Error in create_container command")
        raise click.Abort()


@context_group.command(name="list-containers")
@click.option("--type", "container_type",
              type=click.Choice(["code", "documentation", "mixed", "other"]),
              help="Filter by container type")
def list_containers(container_type: Optional[str] = None):
    """
    List all containers in the system.

    Displays container IDs, names, titles, and related metadata.
    Can be filtered by container type.
    """
    try:
        use_case = create_list_containers_use_case()

        # Prepare filters
        filters = {}
        if container_type:
            filters["container_type"] = container_type

        containers = use_case.execute(**filters)

        if not containers:
            click.echo("No containers found.")
        else:
            click.echo(format_container_list(containers))

    except Exception as e:
        click.echo(format_error(f"Error listing containers: {str(e)}"))
        logger.exception("Error in list_containers command")
        raise click.Abort()


@context_group.command(name="list")
@click.option("--content-type", "-t",
              help="Filter by content type (e.g., python, markdown)")
@click.option("--container", "-c",
              help="Filter by container ID")
def list_contexts(content_type: Optional[str] = None,
                  container: Optional[str] = None):
    """
    List context items in the repository.

    Displays all context items or filters by content type or container.
    """
    try:
        use_case = create_list_context_use_case()

        if container:
            # If container ID is provided, list items by container
            items = use_case.execute_list_by_container(container)
        else:
            # Otherwise, use regular filtering
            filters = {}
            if content_type:
                filters["content_type"] = content_type
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
@click.option("--container", "-c",
              help="Limit search to a specific container")
def search_context(query: str, limit: int = 10,
                   container: Optional[str] = None):
    """
    Search for context items using semantic similarity.

    Returns context items that are semantically similar to the query.
    Can be limited to a specific container.
    """
    try:
        use_case = create_search_context_use_case()

        # If container ID is provided, we need to implement container-specific search
        # This would require enhancing the SearchContextUseCase to support container filtering
        # For now, we'll just filter the results after search
        results = use_case.execute(query, limit)

        # Filter by container if specified
        if container and results:
            results = [(item, score) for item, score in results if
                       item.container_id == container]

        if not results:
            click.echo("No matching context items found.")
        else:
            click.echo(format_search_results(results))
    except Exception as e:
        click.echo(format_error(f"Error searching context items: {str(e)}"))
        logger.exception("Error in search_context command")
        raise click.Abort()