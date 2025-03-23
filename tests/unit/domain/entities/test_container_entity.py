import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.entities.container import Container, ContainerType, ContainerValidationError


class TestContainer:
    """Test cases for the Container entity."""

    def test_container_creation_with_valid_inputs(self):
        """Test creating a container with valid inputs."""
        # Arrange
        container_id = str(uuid4())
        name = "test-container"
        title = "Test Container"
        container_type = "code"
        source_path = "/path/to/source"
        description = "A test container"
        priority = 5

        # Act
        container = Container(
            id=container_id,
            name=name,
            title=title,
            container_type=container_type,
            source_path=source_path,
            description=description,
            priority=priority
        )

        # Assert
        assert container.id == container_id
        assert container.name == name
        assert container.title == title
        assert container.container_type == ContainerType.CODE
        assert container.source_path == source_path
        assert container.description == description
        assert container.priority == priority
        assert isinstance(container.created_at, datetime)
        assert isinstance(container.updated_at, datetime)
        assert container.size == 0  # No items added yet

    def test_container_validation(self):
        """Test validation for required fields and invalid inputs."""
        # Test empty name
        with pytest.raises(ContainerValidationError, match="Name cannot be empty"):
            Container(
                id=str(uuid4()),
                name="",
                title="Test Container",
                container_type="code",
                source_path="/path/to/source"
            )

        # Test empty title
        with pytest.raises(ContainerValidationError, match="Title cannot be empty"):
            Container(
                id=str(uuid4()),
                name="test-container",
                title="",
                container_type="code",
                source_path="/path/to/source"
            )

        # Test invalid container type
        with pytest.raises(ContainerValidationError, match="Invalid container type"):
            Container(
                id=str(uuid4()),
                name="test-container",
                title="Test Container",
                container_type="invalid_type",
                source_path="/path/to/source"
            )

        # Test invalid priority (should be between 1 and 10)
        with pytest.raises(ContainerValidationError, match="Priority must be between 1 and 10"):
            Container(
                id=str(uuid4()),
                name="test-container",
                title="Test Container",
                container_type="code",
                source_path="/path/to/source",
                priority=11
            )

        with pytest.raises(ContainerValidationError, match="Priority must be between 1 and 10"):
            Container(
                id=str(uuid4()),
                name="test-container",
                title="Test Container",
                container_type="code",
                source_path="/path/to/source",
                priority=0
            )

    def test_container_default_values(self):
        """Test default values for optional fields and timestamps."""
        # Arrange
        container_id = str(uuid4())
        name = "test-container"
        title = "Test Container"
        container_type = "code"
        source_path = "/path/to/source"

        # Act
        container = Container(
            id=container_id,
            name=name,
            title=title,
            container_type=container_type,
            source_path=source_path
        )

        # Assert
        assert container.id == container_id
        assert container.name == name
        assert container.title == title
        assert container.container_type == ContainerType.CODE
        assert container.source_path == source_path
        assert container.description == ""  # Default empty string
        assert container.priority == 5  # Default priority
        assert isinstance(container.created_at, datetime)
        assert isinstance(container.updated_at, datetime)
        assert container.size == 0  # Default size

    def test_container_context_items_relationship(self):
        """Test the relationship between container and context items."""
        # Arrange
        container = Container(
            id=str(uuid4()),
            name="test-container",
            title="Test Container",
            container_type="code",
            source_path="/path/to/source"
        )

        # Mock context items
        mock_context_item1 = {"id": "item1", "content": "content1"}
        mock_context_item2 = {"id": "item2", "content": "content2"}

        # Act
        container.add_context_item(mock_context_item1)
        container.add_context_item(mock_context_item2)

        # Assert
        assert container.size == 2
        assert mock_context_item1 in container.get_context_items()
        assert mock_context_item2 in container.get_context_items()

        # Test removing an item
        container.remove_context_item("item1")
        assert container.size == 1
        assert mock_context_item1 not in container.get_context_items()
        assert mock_context_item2 in container.get_context_items()