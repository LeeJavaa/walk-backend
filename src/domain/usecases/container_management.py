from typing import Dict, List, Any, Optional
from uuid import uuid4

from src.domain.entities.container import Container, ContainerType
from src.domain.ports.context_repository import ContextRepository


class CreateContainerUseCase:
    """Use case for creating a new container."""

    def __init__(self, context_repository: ContextRepository):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing containers
        """
        self.context_repository = context_repository

    def execute(
            self,
            name: str,
            title: str,
            container_type: str,
            source_path: str,
            description: str = "",
            priority: int = 5
    ) -> Container:
        """
        Create a new container.

        Args:
            name: Machine-friendly name/identifier for the container
            title: Human-readable title for the container
            container_type: Type of container (code, documentation, etc.)
            source_path: Path to the source directory for this container
            description: Optional description of the container
            priority: Optional priority level (1-10, with 10 being highest)

        Returns:
            The created container

        Raises:
            ValueError: If validation fails
        """
        # Create a new container with a generated ID
        container = Container(
            id=str(uuid4()),
            name=name,
            title=title,
            container_type=container_type,
            source_path=source_path,
            description=description,
            priority=priority
        )

        # Save the container to the repository
        return self.context_repository.add_container(container)


class ListContainersUseCase:
    """Use case for listing containers."""

    def __init__(self, context_repository: ContextRepository):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing containers
        """
        self.context_repository = context_repository

    def execute(self, **filters) -> List[Container]:
        """
        List containers, optionally filtered.

        Args:
            **filters: Optional filters to apply (e.g., container_type=ContainerType.CODE)

        Returns:
            List of containers matching the filters
        """
        # Convert filters to a dictionary if any are provided
        filter_dict = None
        if filters:
            filter_dict = {key: value for key, value in filters.items() if value is not None}

        # Retrieve containers from the repository
        return self.context_repository.list_containers(filter_dict)


class UpdateContainerUseCase:
    """Use case for updating a container."""

    def __init__(self, context_repository: ContextRepository):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing containers
        """
        self.context_repository = context_repository

    def execute(
            self,
            container_id: str,
            **updates
    ) -> Container:
        """
        Update an existing container.

        Args:
            container_id: ID of the container to update
            **updates: Fields to update (name, title, description, etc.)

        Returns:
            The updated container

        Raises:
            KeyError: If the container is not found
            ValueError: If validation fails
        """
        # Get the existing container
        container = self.context_repository.get_container(container_id)
        if not container:
            raise KeyError(f"Container not found: {container_id}")

        # Apply updates
        if "name" in updates:
            container.validate_name(updates["name"])
            container.name = updates["name"]

        if "title" in updates:
            container.validate_title(updates["title"])
            container.title = updates["title"]

        if "container_type" in updates:
            container.validate_container_type(updates["container_type"])
            container.container_type = container._parse_container_type(updates["container_type"])

        if "source_path" in updates:
            container.source_path = updates["source_path"]

        if "description" in updates:
            container.description = updates["description"]

        if "priority" in updates:
            container.validate_priority(updates["priority"])
            container.priority = updates["priority"]

        # Save the updated container
        return self.context_repository.update_container(container)


class DeleteContainerUseCase:
    """Use case for deleting a container."""

    def __init__(self, context_repository: ContextRepository):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing containers
        """
        self.context_repository = context_repository

    def execute(self, container_id: str) -> bool:
        """
        Delete a container by ID.

        Args:
            container_id: ID of the container to delete

        Returns:
            True if the container was deleted, False if not found
        """
        return self.context_repository.delete_container(container_id)


class GetContainerUseCase:
    """Use case for retrieving a container by ID."""

    def __init__(self, context_repository: ContextRepository):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing containers
        """
        self.context_repository = context_repository

    def execute(self, container_id: str) -> Optional[Container]:
        """
        Get a container by ID.

        Args:
            container_id: ID of the container to retrieve

        Returns:
            The container if found, None otherwise
        """
        return self.context_repository.get_container(container_id)