import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.entities.context_item import ContextItem, ContentType, \
    ContextItemValidationError
from src.domain.entities.container import Container


class TestContextItem:
    """Test cases for the ContextItem entity."""

    @pytest.fixture
    def sample_container(self):
        """Create a sample container for testing."""
        return Container(
            id=str(uuid4()),
            name="test-container",
            title="Test Container",
            container_type="code",
            source_path="/path/to/source"
        )

    def test_create_context_item_with_valid_inputs(self):
        """Test creating a context item with valid inputs (U-CS-1)."""
        # Arrange
        context_id = str(uuid4())
        source = "test_file.py"
        content = "def hello_world():\n    print('Hello, World!')"
        content_type = ContentType.PYTHON
        metadata = {"author": "Test Author", "description": "Test file"}
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Act
        context_item = ContextItem(
            id=context_id,
            source=source,
            content=content,
            content_type=content_type,
            metadata=metadata,
            embedding=embedding,
        )

        # Assert
        assert context_item.id == context_id
        assert context_item.source == source
        assert context_item.content == content
        assert context_item.content_type == content_type
        assert context_item.metadata == metadata
        assert context_item.embedding == embedding
        assert isinstance(context_item.created_at, datetime)
        assert isinstance(context_item.updated_at, datetime)
        # New properties should have default values
        assert context_item.container_id is None
        assert context_item.is_container_root is False
        assert context_item.parent_id is None
        assert context_item.is_chunk is False
        assert context_item.chunk_type is None
        assert context_item.chunk_metadata == {}

    def test_reject_invalid_inputs(self):
        """Test context item validation rejects invalid inputs (U-CS-2)."""
        # Test empty source
        with pytest.raises(ContextItemValidationError,
                           match="Source cannot be empty"):
            ContextItem(
                id=str(uuid4()),
                source="",
                content="test content",
                content_type=ContentType.TEXT,
            )

        # Test empty content
        with pytest.raises(ContextItemValidationError,
                           match="Content cannot be empty"):
            ContextItem(
                id=str(uuid4()),
                source="test_file.txt",
                content="",
                content_type=ContentType.TEXT,
            )

        # Test invalid content type
        with pytest.raises(ContextItemValidationError,
                           match="Invalid content type. Expected one of:"):
            ContextItem(
                id=str(uuid4()),
                source="test_file.txt",
                content="test content",
                content_type="invalid_type",
            )

        # Test invalid embedding format
        with pytest.raises(ContextItemValidationError,
                           match="Embedding must be a list of floats"):
            ContextItem(
                id=str(uuid4()),
                source="test_file.txt",
                content="test content",
                content_type=ContentType.TEXT,
                embedding="not a list",
            )

    def test_metadata_extraction(self):
        """Test context item metadata extraction (U-CS-4)."""
        # Arrange
        file_content = "# Author: Test Author\n# Description: Test description\ndef hello_world():\n    print('Hello, World!')"

        # Act
        context_item = ContextItem.from_file_content(
            source="test_file.py",
            content=file_content,
            content_type=ContentType.PYTHON,
        )

        # Assert
        assert context_item.metadata.get("author") == "Test Author"
        assert context_item.metadata.get("description") == "Test description"
        assert context_item.content == file_content

    def test_from_file_path(self, mocker):
        """Test creating a context item from a file path."""
        # Arrange
        mock_open = mocker.patch("builtins.open",
                                 mocker.mock_open(read_data="def test(): pass"))
        mock_exists = mocker.patch("os.path.exists", return_value=True)

        # Act
        context_item = ContextItem.from_file_path("test_file.py")

        # Assert
        mock_exists.assert_called_once_with("test_file.py")
        mock_open.assert_called_once_with("test_file.py", "r", encoding="utf-8")
        assert context_item.source == "test_file.py"
        assert context_item.content == "def test(): pass"
        assert context_item.content_type == ContentType.PYTHON
        # New property assertion
        assert context_item.is_container_root is True

    # New tests for container association and chunking features
    def test_context_item_container_association(self, sample_container):
        """Test creating a context item with container association."""
        # Arrange
        context_id = str(uuid4())
        source = "test_file.py"
        content = "def hello_world():\n    print('Hello, World!')"
        content_type = ContentType.PYTHON

        # Act
        context_item = ContextItem(
            id=context_id,
            source=source,
            content=content,
            content_type=content_type,
            container_id=sample_container.id
        )

        # Assert
        assert context_item.id == context_id
        assert context_item.container_id == sample_container.id
        assert context_item.is_container_root is False  # Default

        # Test creating a context item with no container
        context_item_no_container = ContextItem(
            id=str(uuid4()),
            source=source,
            content=content,
            content_type=content_type
        )
        assert context_item_no_container.container_id is None

    def test_context_item_parent_child_relationship(self, sample_container):
        """Test parent-child relationship between context items."""
        # Create a parent context item (e.g., a file)
        parent_item = ContextItem(
            id=str(uuid4()),
            source="parent_file.py",
            content="class ParentClass:\n    def method(self):\n        pass",
            content_type=ContentType.PYTHON,
            container_id=sample_container.id,
            is_container_root=True
            # This is a root item in the container (a file)
        )

        # Create a child context item (e.g., a method within the file)
        child_item = ContextItem(
            id=str(uuid4()),
            source="parent_file.py:ParentClass.method",
            content="def method(self):\n    pass",
            content_type=ContentType.PYTHON,
            container_id=sample_container.id,
            parent_id=parent_item.id,
            is_chunk=True  # This is a chunk of the parent
        )

        # Assert parent-child relationship
        assert child_item.parent_id == parent_item.id
        assert child_item.is_chunk is True
        assert parent_item.is_chunk is False

        # Test that parent item is a container root
        assert parent_item.is_container_root is True

    def test_context_item_chunking_properties(self):
        """Test chunk-related properties and methods."""
        # Arrange
        context_id = str(uuid4())
        source = "test_file.py:TestClass.test_method"
        content = "def test_method(self):\n    return 'Hello, World!'"
        content_type = ContentType.PYTHON

        # Act
        chunk_item = ContextItem(
            id=context_id,
            source=source,
            content=content,
            content_type=content_type,
            parent_id=str(uuid4()),  # Reference to parent
            is_chunk=True,
            chunk_type="method",
            chunk_metadata={
                "class": "TestClass",
                "method": "test_method",
                "line_start": 10,
                "line_end": 12
            }
        )

        # Assert
        assert chunk_item.is_chunk is True
        assert chunk_item.chunk_type == "method"
        assert chunk_item.chunk_metadata["class"] == "TestClass"
        assert chunk_item.chunk_metadata["line_start"] == 10

        # Test extraction of chunk path components
        parent_path, chunk_name = chunk_item.extract_chunk_path_components()
        assert parent_path == "test_file.py"
        assert chunk_name == "TestClass.test_method"

    def test_context_item_validation_with_chunking(self):
        """Test validation with chunking properties."""
        # Test invalid parent reference when is_chunk=True
        with pytest.raises(ContextItemValidationError,
                           match="Chunk items must have a parent_id"):
            ContextItem(
                id=str(uuid4()),
                source="test_chunk.py:method",
                content="chunk content",
                content_type=ContentType.PYTHON,
                is_chunk=True,  # Is a chunk but no parent specified
                parent_id=None  # Missing parent reference
            )

        # Test setting chunk properties on non-chunk item
        with pytest.raises(ContextItemValidationError,
                           match="Only chunk items can have chunk_type"):
            ContextItem(
                id=str(uuid4()),
                source="test.py",
                content="content",
                content_type=ContentType.PYTHON,
                is_chunk=False,  # Not a chunk
                chunk_type="method"  # Should not have chunk type
            )

    def test_from_file_content_with_container(self, sample_container):
        """Test creating a context item from file content with container association."""
        # Arrange
        file_content = "def test_function():\n    pass"
        source = "test_file.py"

        # Act
        context_item = ContextItem.from_file_content(
            source=source,
            content=file_content,
            content_type=ContentType.PYTHON,
            container_id=sample_container.id,
            is_container_root=True
        )

        # Assert
        assert context_item.container_id == sample_container.id
        assert context_item.is_container_root is True
        assert context_item.parent_id is None
        assert context_item.is_chunk is False