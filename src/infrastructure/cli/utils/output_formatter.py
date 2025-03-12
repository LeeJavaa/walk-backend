"""
Utility functions for formatting CLI output.
"""
import json
from typing import List, Dict, Any, Tuple
import click

from src.domain.entities.context_item import ContextItem
from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState


def format_success(message: str, data: Any = None) -> str:
    """
    Format a success message with optional data.

    Args:
        message: Success message
        data: Optional data to display

    Returns:
        Formatted success message
    """
    result = click.style(f"✓ {message}", fg="green", bold=True)

    if data:
        if isinstance(data, dict):
            # Format dictionary nicely
            for key, value in data.items():
                result += f"\n  {click.style(key, fg='green')}: {value}"
        elif isinstance(data, str):
            # Simple string data
            result += f"\n{data}"
        else:
            # Any other data type
            result += f"\n{str(data)}"

    return result


def format_error(message: str) -> str:
    """
    Format an error message.

    Args:
        message: Error message

    Returns:
        Formatted error message
    """
    return click.style(f"✗ Error: {message}", fg="red", bold=True)


def format_context_item(item: ContextItem) -> str:
    """
    Format a context item for display.

    Args:
        item: Context item to format

    Returns:
        Formatted context item
    """
    return (
        f"ID: {click.style(item.id, fg='blue')}\n"
        f"Source: {item.source}\n"
        f"Type: {item.content_type}\n"
        f"Created: {item.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Metadata: {json.dumps(item.metadata, indent=2) if item.metadata else 'None'}\n"
    )


def format_context_list(items: List[ContextItem]) -> str:
    """
    Format a list of context items for display.

    Args:
        items: List of context items to format

    Returns:
        Formatted list of context items
    """
    if not items:
        return "No context items found."

    # Create a table-like output
    headers = ["ID", "Source", "Type", "Created"]
    rows = []

    for item in items:
        rows.append([
            item.id,
            item.source,
            item.content_type,
            item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    # Calculate column widths
    col_widths = [
        max(len(headers[i]), max(len(row[i]) for row in rows))
        for i in range(len(headers))
    ]

    # Format the headers
    header_row = " | ".join(
        click.style(headers[i].ljust(col_widths[i]), bold=True)
        for i in range(len(headers))
    )

    # Format the separator
    separator = "-+-".join("-" * width for width in col_widths)

    # Format the data rows
    data_rows = []
    for row in rows:
        data_rows.append(" | ".join(
            row[i].ljust(col_widths[i])
            for i in range(len(row))
        ))

    # Combine everything
    return "\n".join([header_row, separator] + data_rows)


def format_search_results(results: List[Tuple[ContextItem, float]]) -> str:
    """
    Format search results for display.

    Args:
        results: List of tuples of (context item, similarity score)

    Returns:
        Formatted search results
    """
    if not results:
        return "No matching context items found."

    # Create a table-like output
    headers = ["ID", "Source", "Type", "Similarity"]
    rows = []

    for item, score in results:
        rows.append([
            item.id,
            item.source,
            item.content_type,
            f"{score:.2f}"
        ])

    # Calculate column widths
    col_widths = [
        max(len(headers[i]), max(len(row[i]) for row in rows))
        for i in range(len(headers))
    ]

    # Format the headers
    header_row = " | ".join(
        click.style(headers[i].ljust(col_widths[i]), bold=True)
        for i in range(len(headers))
    )

    # Format the separator
    separator = "-+-".join("-" * width for width in col_widths)

    # Format the data rows
    data_rows = []
    for row in rows:
        data_rows.append(" | ".join(
            row[i].ljust(col_widths[i])
            for i in range(len(row))
        ))

    # Combine everything
    return "\n".join([header_row, separator] + data_rows)


def format_task_detail(task: Task) -> Dict[str, Any]:
    """
    Format task details for display.

    Args:
        task: Task to format

    Returns:
        Dictionary with formatted task details
    """
    return {
        "id": task.id,
        "description": task.description,
        "status": task.status,
        "requirements": "\n".join(f"- {req}" for req in task.requirements),
        "constraints": "\n".join(f"- {constraint}" for constraint in
                                 task.constraints) if task.constraints else "None",
        "context_ids": ", ".join(
            task.context_ids) if task.context_ids else "None",
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }


def format_task_list(tasks: List[Task], task_states: Dict[str, str] = None) -> str:
    """
    Format a list of tasks for display.

    Args:
        tasks: List of tasks to format
        task_states: Dictionary mapping task IDs to their latest pipeline state IDs

    Returns:
        Formatted list of tasks
    """
    if not tasks:
        return "No tasks found."

    # Create a table-like output
    headers = ["ID", "Description", "Status", "Pipeline State", "Created"]
    rows = []

    # Choose colors for different statuses
    status_colors = {
        "pending": "yellow",
        "in_progress": "blue",
        "completed": "green",
        "failed": "red"
    }

    task_states = task_states or {}

    # First pass: collect all rows to calculate proper column widths
    formatted_rows = []
    for task in tasks:
        status_color = status_colors.get(task.status, "white")
        pipeline_state_id = task_states.get(task.id, "None")
        
        # Store the actual values that will be displayed
        formatted_row = [
            task.id,
            task.description[:50] + ("..." if len(task.description) > 50 else ""),
            task.status,  # Store raw status for width calculation
            pipeline_state_id,
            task.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ]
        formatted_rows.append(formatted_row)

    # Calculate column widths based on both headers and actual content
    col_widths = [
        max(len(headers[i]), max(len(str(row[i])) for row in formatted_rows))
        for i in range(len(headers))
    ]

    # Format the headers with proper padding
    header_row = " | ".join(
        click.style(headers[i].ljust(col_widths[i]), bold=True)
        for i in range(len(headers))
    )

    # Format the separator matching the exact width
    separator = "-+-".join("-" * width for width in col_widths)

    # Format the data rows with colors and proper padding
    data_rows = []
    for row in formatted_rows:
        colored_row = [
            str(row[0]).ljust(col_widths[0]),  # ID
            str(row[1]).ljust(col_widths[1]),  # Description
            click.style(str(row[2]).ljust(col_widths[2]), fg=status_colors.get(row[2], "white")),  # Status
            click.style(str(row[3]).ljust(col_widths[3]), fg="blue") if row[3] != "None" else "None".ljust(col_widths[3]),  # Pipeline State
            str(row[4]).ljust(col_widths[4])   # Created
        ]
        data_rows.append(" | ".join(colored_row))

    # Combine everything
    return "\n".join([header_row, separator] + data_rows)


def format_pipeline_state(state: PipelineState) -> str:
    """
    Format pipeline state for display.

    Args:
        state: Pipeline state to format

    Returns:
        Formatted pipeline state
    """
    # Format the pipeline stages as a progress bar
    stages = state.PIPELINE_STAGES
    current_stage_idx = stages.index(state.current_stage)

    progress_bar = []
    for i, stage in enumerate(stages):
        if i < current_stage_idx:
            # Completed stage
            stage_str = click.style(f"[{stage}]", fg="green")
        elif i == current_stage_idx:
            # Current stage
            stage_str = click.style(f"[{stage}]", fg="yellow", bold=True)
        else:
            # Future stage
            stage_str = f"[{stage}]"

        progress_bar.append(stage_str)

    # Format checkpoint information
    checkpoints = []
    for checkpoint_id, checkpoint_data in state.checkpoint_data.items():
        checkpoint_stage = checkpoint_data.get("current_stage", "unknown")
        timestamp = checkpoint_data.get("timestamp", "unknown")
        checkpoints.append(
            f"- {checkpoint_id}: {checkpoint_stage} ({timestamp})")

    checkpoint_str = "\n".join(checkpoints) if checkpoints else "No checkpoints"

    # Format artifacts information with truncated values
    artifacts = []
    for stage, artifact in state.artifacts.items():
        artifact_details = []
        for key, value in artifact.items():
            # Convert value to string and truncate if needed
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:30] + "..."
            artifact_details.append(f"{key}: {value_str}")
        artifacts.append(f"- {stage}:\n    " + "\n    ".join(artifact_details))

    artifact_str = "\n".join(artifacts) if artifacts else "No artifacts"

    # Format feedback information
    feedback_items = []
    for feedback_item in state.feedback:
        feedback_items.append(format_feedback(feedback_item))

    feedback_str = "\n".join(feedback_items) if feedback_items else "No feedback"

    # Combine everything
    return (
        f"Pipeline State ID: {click.style(state.id, fg='blue')}\n"
        f"Task ID: {state.task_id}\n"
        f"Progress: {' → '.join(progress_bar)}\n"
        f"Completed Stages: {', '.join(state.stages_completed) if state.stages_completed else 'None'}\n"
        f"Checkpoints:\n{checkpoint_str}\n"
        f"Artifacts:\n{artifact_str}\n"
        f"Feedback:\n{feedback_str}\n"
    )


def format_feedback(feedback_item: Dict[str, Any]) -> str:
    """
    Format a feedback item for display.

    Args:
        feedback_item: Feedback item to format

    Returns:
        Formatted feedback item
    """
    feedback_type = feedback_item.get("type", "unknown")
    type_colors = {
        "suggestion": "blue",
        "correction": "red",
        "enhancement": "green"
    }
    color = type_colors.get(feedback_type, "white")

    return (
        f"ID: {click.style(feedback_item.get('id', 'unknown'), fg='blue')}\n"
        f"Stage: {feedback_item.get('stage_name', 'unknown')}\n"
        f"Type: {click.style(feedback_type, fg=color)}\n"
        f"Timestamp: {feedback_item.get('timestamp', 'unknown')}\n"
        f"Incorporated: {feedback_item.get('incorporated', False)}\n"
        f"Content:\n{feedback_item.get('content', '')}\n"
    )