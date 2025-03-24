import pytest
from unittest.mock import Mock
from uuid import uuid4
from typing import Dict, List, Any, Optional

from src.domain.entities.container import Container, ContainerType
from src.domain.ports.context_repository import ContextRepository
from src.domain.usecases.container_management import (
    CreateContainerUseCase,
    ListContainersUseCase,
    UpdateContainerUseCase
)


class TestContainerManagementUseCases:
    """Test cases for container management use cases."""

    @pytest.fixture
    def mock_context_repository(self):
        """Create a mock context repository."""
        repo = Mock(spec=ContextRepository)

        # Setup mock behaviors
        repo.add_container.side_effect = lambda container: container
        repo.list_containers.return_value = []

        return repo

    @pytest.fixture
    def sample_container_data(self):
        """Sample data for creating a container."""
        return {
            "name": "test-container",
            "title": "Test Container",
            "container_type": "code",
            "source_path": "/path/to/source",
            "description": "A test container",
            "priority": 5
        }

    def test_create_container_use_case(self, mock_context_repository,
                                       sample_container_data):
        """Test creating a container."""
        # Arrange
        use_case = CreateContainerUseCase(
            context_repository=mock_context_repository)

        # Act
        container = use_case.execute(**sample_container_data)

        # Assert
        assert container is not None
        assert container.name == sample_container_data["name"]
        assert container.title == sample_container_data["title"]
        assert container.container_type == ContainerType.CODE
        assert container.source_path == sample_container_data["source_path"]
        assert container.description == sample_container_data["description"]
        assert container.priority == sample_container_data["priority"]

        mock_context_repository.add_container.assert_called_once()

    def test_create_container_with_minimal_data(self, mock_context_repository):
        """Test creating a container with minimal required data."""
        # Arrange
        use_case = CreateContainerUseCase(
            context_repository=mock_context_repository)
        minimal_data = {
            "name": "minimal-container",
            "title": "Minimal Container",
            "container_type": "documentation",
            "source_path": "/path/to/docs"
        }

        # Act
        container = use_case.execute(**minimal_data)

        # Assert
        assert container is not None
        assert container.name == minimal_data["name"]
        assert container.title == minimal_data["title"]
        assert container.container_type == ContainerType.DOCUMENTATION
        assert container.source_path == minimal_data["source_path"]
        assert container.description == ""  # Default value
        assert container.priority == 5  # Default value

        mock_context_repository.add_container.assert_called_once()

    def test_list_containers_use_case(self, mock_context_repository):
        """Test listing containers."""
        # Arrange
        use_case = ListContainersUseCase(
            context_repository=mock_context_repository)

        # Mock repository to return sample containers
        container1 = Container(
            id=str(uuid4()),
            name="container1",
            title="Container 1",
            container_type="code",
            source_path="/path/1"
        )
        container2 = Container(
            id=str(uuid4()),
            name="container2",
            title="Container 2",
            container_type="documentation",
            source_path="/path/2"
        )
        mock_context_repository.list_containers.return_value = [container1,
                                                                container2]

        # Act
        containers = use_case.execute()

        # Assert
        assert len(containers) == 2
        assert containers[0].name == "container1"
        assert containers[1].name == "container2"
        mock_context_repository.list_containers.assert_called_once_with(None)

    def test_list_containers_with_filter(self, mock_context_repository):
        """Test listing containers with a filter."""
        # Arrange
        use_case = ListContainersUseCase(
            context_repository=mock_context_repository)

        # Act
        use_case.execute(container_type=ContainerType.CODE)

        # Assert
        mock_context_repository.list_containers.assert_called_once_with(
            {"container_type": ContainerType.CODE}
        )

    def test_update_container_use_case(self, mock_context_repository):
        """Test updating a container."""
        # Arrange
        use_case = UpdateContainerUseCase(
            context_repository=mock_context_repository)

        # Create a sample container to update
        container_id = str(uuid4())
        container = Container(
            id=container_id,
            name="original-container",
            title="Original Container",
            container_type="code",
            source_path="/original/path",
            description="Original description",
            priority=3
        )

        # Mock repository to return the container when get_container is called
        mock_context_repository.get_container.return_value = container

        # Updates to apply
        updates = {
            "title": "Updated Container",
            "description": "Updated description",
            "priority": 7
        }

        # Act
        updated_container = use_case.execute(container_id, **updates)

        # Assert
        assert updated_container.id == container_id
        assert updated_container.name == "original-container"  # Unchanged
        assert updated_container.title == "Updated Container"  # Changed
        assert updated_container.description == "Updated description"  # Changed
        assert updated_container.priority == 7  # Changed
        assert updated_container.source_path == "/original/path"  # Unchanged

        mock_context_repository.get_container.assert_called_once_with(
            container_id)
        mock_context_repository.update_container.assert_called_once()

    def test_update_container_not_found(self, mock_context_repository):
        """Test updating a non-existent container."""
        # Arrange
        use_case = UpdateContainerUseCase(
            context_repository=mock_context_repository)

        # Mock repository to return None for get_container
        mock_context_repository.get_container.return_value = None

        # Act & Assert
        with pytest.raises(KeyError, match="Container not found"):
            use_case.execute("non-existent-id", title="New Title")

        mock_context_repository.get_container.assert_called_once()
        mock_context_repository.update_container.assert_not_called()