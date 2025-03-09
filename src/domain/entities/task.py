from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4
import re


class TaskStatus(str, Enum):
    """Enumeration of task statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskValidationError(Exception):
    """Exception raised for task validation errors."""
    pass


class Task:
    """
    Entity representing a coding task.

    A task contains the requirements and constraints for the code to be generated.
    """

    def __init__(
            self,
            id: str,
            description: str,
            requirements: List[str],
            constraints: Optional[List[str]] = None,
            context_ids: Optional[List[str]] = None,
            status: Optional[TaskStatus] = None,
            created_at: Optional[datetime] = None,
    ):
        """
        Initialize a new Task.

        Args:
            id: Unique identifier for the task
            description: Description of the task
            requirements: List of requirements
            constraints: List of constraints (optional)
            context_ids: List of context item IDs relevant to the task (optional)
            status: Status of the task (optional, defaults to PENDING)
            created_at: Creation timestamp (optional)

        Raises:
            TaskValidationError: If validation fails
        """
        self.validate_description(description)
        self.validate_requirements(requirements)
        if constraints is not None:
            self.validate_constraints(constraints)
        if context_ids is not None:
            self.validate_context_ids(context_ids)

        self.id = id
        self.description = description
        self.requirements = requirements
        self.constraints = constraints or []
        self.context_ids = context_ids or []
        self._status = status or TaskStatus.PENDING
        self.created_at = created_at or datetime.now()

    @property
    def status(self) -> TaskStatus:
        """Get the task status."""
        return self._status

    @status.setter
    def status(self, value: TaskStatus) -> None:
        """
        Set the task status.

        Args:
            value: New status value

        Raises:
            TaskValidationError: If the status transition is invalid
        """
        # Validate status transitions
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.IN_PROGRESS],
            TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.FAILED],
            TaskStatus.COMPLETED: [],
            TaskStatus.FAILED: [TaskStatus.IN_PROGRESS],
        }

        if value not in valid_transitions[self._status]:
            raise TaskValidationError(
                f"Invalid status transition from {self._status} to {value}. "
                f"Valid transitions: {', '.join([str(s) for s in valid_transitions[self._status]])}"
            )

        self._status = value

    @staticmethod
    def validate_description(description: str) -> None:
        """
        Validate the task description.

        Args:
            description: Description to validate

        Raises:
            TaskValidationError: If validation fails
        """
        if not description:
            raise TaskValidationError("Task description cannot be empty")

    @staticmethod
    def validate_requirements(requirements: List[str]) -> None:
        """
        Validate the task requirements.

        Args:
            requirements: Requirements to validate

        Raises:
            TaskValidationError: If validation fails
        """
        if not isinstance(requirements, list):
            raise TaskValidationError("Requirements must be a list")
        if not requirements:
            raise TaskValidationError(
                "At least one requirement must be specified")

    @staticmethod
    def validate_constraints(constraints: List[str]) -> None:
        """
        Validate the task constraints.

        Args:
            constraints: Constraints to validate

        Raises:
            TaskValidationError: If validation fails
        """
        if not isinstance(constraints, list):
            raise TaskValidationError("Constraints must be a list")

    @staticmethod
    def validate_context_ids(context_ids: List[str]) -> None:
        """
        Validate the task context IDs.

        Args:
            context_ids: Context IDs to validate

        Raises:
            TaskValidationError: If validation fails
        """
        if not isinstance(context_ids, list):
            raise TaskValidationError("Context IDs must be a list")

    @classmethod
    def parse_from_user_input(cls, user_input: str) -> "Task":
        """
        Parse a task from user input.

        Args:
            user_input: User input string

        Returns:
            A new Task instance
        """
        # Extract description (first non-empty line)
        lines = user_input.strip().split("\n")
        description = next((line.strip() for line in lines if line.strip()), "")

        # Extract requirements and constraints
        requirements = []
        constraints = []

        # Find sections
        sections = {}
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a section header
            if line.lower().endswith(":") or line.lower().endswith("s:"):
                current_section = line.lower().rstrip(":").strip()
                sections[current_section] = []
            elif current_section:
                # Add to current section
                sections[current_section].append(line)

        # Extract requirements
        for section_name, section_lines in sections.items():
            if "requirement" in section_name:
                for line in section_lines:
                    if line.startswith("-") or line.startswith("*"):
                        requirements.append(line[1:].strip())
                    else:
                        requirements.append(line)
            elif "constraint" in section_name:
                for line in section_lines:
                    if line.startswith("-") or line.startswith("*"):
                        constraints.append(line[1:].strip())
                    else:
                        constraints.append(line)

        # If no explicit requirements section, treat the rest of the input as requirements
        if not requirements and not constraints:
            for line in lines[1:]:  # Skip description
                line = line.strip()
                if line and not line.lower().endswith(":"):
                    if line.startswith("-") or line.startswith("*"):
                        requirements.append(line[1:].strip())
                    else:
                        requirements.append(line)

        # If still no requirements, use the description as the only requirement
        if not requirements:
            requirements = [description]

        return cls(
            id=str(uuid4()),
            description=description,
            requirements=requirements,
            constraints=constraints,
        )