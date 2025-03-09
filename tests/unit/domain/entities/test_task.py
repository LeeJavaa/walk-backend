import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.entities.task import Task, TaskStatus, TaskValidationError


class TestTask:
    """Test cases for the Task entity."""

    def test_task_creation_with_valid_inputs(self):
        """Test creating a task with valid inputs."""
        # Arrange
        task_id = str(uuid4())
        description = "Create a simple web server in Python"
        requirements = ["Handle GET and POST requests", "Serve static files",
                        "Provide JSON API"]
        constraints = ["Use only standard library", "Minimize memory usage"]
        context_ids = [str(uuid4()), str(uuid4())]

        # Act
        task = Task(
            id=task_id,
            description=description,
            requirements=requirements,
            constraints=constraints,
            context_ids=context_ids,
        )

        # Assert
        assert task.id == task_id
        assert task.description == description
        assert task.requirements == requirements
        assert task.constraints == constraints
        assert task.context_ids == context_ids
        assert task.status == TaskStatus.PENDING
        assert isinstance(task.created_at, datetime)

    def test_task_validation(self):
        """Test validation of task inputs."""
        # Test empty description
        with pytest.raises(TaskValidationError,
                           match="Task description cannot be empty"):
            Task(
                id=str(uuid4()),
                description="",
                requirements=["req1"],
            )

        # Test requirements not a list
        with pytest.raises(TaskValidationError,
                           match="Requirements must be a list"):
            Task(
                id=str(uuid4()),
                description="Test task",
                requirements="not a list",
            )

        # Test constraints not a list
        with pytest.raises(TaskValidationError,
                           match="Constraints must be a list"):
            Task(
                id=str(uuid4()),
                description="Test task",
                requirements=["req1"],
                constraints="not a list",
            )

        # Test context_ids not a list
        with pytest.raises(TaskValidationError,
                           match="Context IDs must be a list"):
            Task(
                id=str(uuid4()),
                description="Test task",
                requirements=["req1"],
                context_ids="not a list",
            )

    def test_task_status_transitions(self):
        """Test task status transitions."""
        # Arrange
        task = Task(
            id=str(uuid4()),
            description="Test task",
            requirements=["req1"],
        )

        # Assert initial status
        assert task.status == TaskStatus.PENDING

        # Act & Assert - Valid transitions
        task.status = TaskStatus.IN_PROGRESS
        assert task.status == TaskStatus.IN_PROGRESS

        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

        # Create a new task for testing invalid transitions
        task = Task(
            id=str(uuid4()),
            description="Test task",
            requirements=["req1"],
        )

        # Act & Assert - Invalid transition
        with pytest.raises(TaskValidationError,
                           match="Invalid status transition"):
            task.status = TaskStatus.COMPLETED  # Can't go directly from PENDING to COMPLETED

    def test_parse_task_from_user_input(self):
        """Test parsing task from user input."""
        # Arrange
        user_input = """
        Create a simple web server in Python

        Requirements:
        - Handle GET and POST requests
        - Serve static files
        - Provide JSON API

        Constraints:
        - Use only standard library
        - Minimize memory usage
        """

        # Act
        task = Task.parse_from_user_input(user_input)

        # Assert
        assert task.description == "Create a simple web server in Python"
        assert "Handle GET and POST requests" in task.requirements
        assert "Serve static files" in task.requirements
        assert "Provide JSON API" in task.requirements
        assert "Use only standard library" in task.constraints
        assert "Minimize memory usage" in task.constraints
        assert task.status == TaskStatus.PENDING