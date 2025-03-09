import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.entities.context_item import ContextItem, ContentType, \
    ContextItemValidationError


class TestContextItem:
    """Test cases for the ContextItem entity."""

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