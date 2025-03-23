from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Set


class ContainerType(str, Enum):
    """Enumeration of container types."""
    CODE = "code"
    DOCUMENTATION = "documentation"
    MIXED = "mixed"
    OTHER = "other"


class ContainerValidationError(Exception):
    """Exception raised for container validation errors."""
    pass


class Container:
    """
    Entity representing a container for context items.

    A container groups related context items, typically corresponding to a
    directory or a logical collection.
    """

    def __init__(
            self,
            id: str,
            name: str,
            title: str,
            container_type: str,
            source_path: str,
            description: str = "",
            priority: int = 5,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None
    ):
        """
        Initialize a new Container.

        Args:
            id: Unique identifier for the container
            name: Machine-friendly name/identifier for the container
            title: Human-readable title for the container
            container_type: Type of container (code, documentation, etc.)
            source_path: Path to the source directory for this container
            description: Optional description of the container
            priority: Optional priority level (1-10, with 10 being highest)
            created_at: Creation timestamp (optional)
            updated_at: Last update timestamp (optional)

        Raises:
            ContainerValidationError: If validation fails
        """
        self.validate_name(name)
        self.validate_title(title)
        self.validate_container_type(container_type)
        self.validate_priority(priority)

        self.id = id
        self.name = name
        self.title = title
        self.container_type = self._parse_container_type(container_type)
        self.source_path = source_path
        self.description = description
        self.priority = priority
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

        # Store context item IDs and a cache of context items
        self._context_item_ids: Set[str] = set()
        self._context_items: List[
            Any] = []  # Using Any to avoid circular import

    @staticmethod
    def validate_name(name: str) -> None:
        """
        Validate the container name.

        Args:
            name: Name to validate

        Raises:
            ContainerValidationError: If validation fails
        """
        if not name:
            raise ContainerValidationError("Name cannot be empty")

    @staticmethod
    def validate_title(title: str) -> None:
        """
        Validate the container title.

        Args:
            title: Title to validate

        Raises:
            ContainerValidationError: If validation fails
        """
        if not title:
            raise ContainerValidationError("Title cannot be empty")

    @staticmethod
    def validate_container_type(container_type: str) -> None:
        """
        Validate the container type.

        Args:
            container_type: Container type to validate

        Raises:
            ContainerValidationError: If validation fails
        """
        try:
            ContainerType(container_type.lower())
        except ValueError:
            valid_types = [t.value for t in ContainerType]
            raise ContainerValidationError(
                f"Invalid container type. Expected one of: {valid_types}"
            )

    @staticmethod
    def validate_priority(priority: int) -> None:
        """
        Validate the priority value.

        Args:
            priority: Priority value to validate

        Raises:
            ContainerValidationError: If validation fails
        """
        if priority < 1 or priority > 10:
            raise ContainerValidationError("Priority must be between 1 and 10")

    def _parse_container_type(self, container_type: str) -> ContainerType:
        """
        Parse and convert container type string to enum.

        Args:
            container_type: Container type string

        Returns:
            ContainerType enum value
        """
        return ContainerType(container_type.lower())

    @property
    def size(self) -> int:
        """
        Get the number of context items in this container.

        Returns:
            Number of context items
        """
        return len(self._context_item_ids)

    def add_context_item(self, context_item: Any) -> None:
        """
        Add a context item to this container.

        Args:
            context_item: The context item to add
        """
        item_id = context_item["id"]
        if item_id not in self._context_item_ids:
            self._context_item_ids.add(item_id)
            self._context_items.append(context_item)
            self.updated_at = datetime.now()

    def remove_context_item(self, context_item_id: str) -> bool:
        """
        Remove a context item from this container.

        Args:
            context_item_id: ID of the context item to remove

        Returns:
            True if the item was removed, False if not found
        """
        if context_item_id in self._context_item_ids:
            self._context_item_ids.remove(context_item_id)
            # Remove from the cached items list
            self._context_items = [item for item in self._context_items
                                   if item["id"] != context_item_id]
            self.updated_at = datetime.now()
            return True
        return False

    def get_context_items(self) -> List[Any]:
        """
        Get all context items in this container.

        Returns:
            List of context items
        """
        return self._context_items.copy()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the container to a dictionary for serialization.

        Returns:
            Dictionary representation of the container
        """
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "container_type": self.container_type.value,
            "source_path": self.source_path,
            "description": self.description,
            "priority": self.priority,
            "size": self.size,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "context_item_ids": list(self._context_item_ids)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Container":
        """
        Create a container from a dictionary.

        Args:
            data: Dictionary with container data

        Returns:
            Container instance
        """
        container = cls(
            id=data["id"],
            name=data["name"],
            title=data["title"],
            container_type=data["container_type"],
            source_path=data["source_path"],
            description=data.get("description", ""),
            priority=data.get("priority", 5),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

        # Restore context item IDs
        for item_id in data.get("context_item_ids", []):
            container._context_item_ids.add(item_id)

        return container