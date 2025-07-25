import pytest
from unittest.mock import Mock, MagicMock
from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, List

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.container import Container, ContainerType
from src.infrastructure.repositories.mongo_context_repository import \
    MongoContextRepository


class TestMongoContextRepository:
    """Unit tests for the MongoDB context repository."""

    @pytest.fixture
    def mock_collection(self):
        """Mock MongoDB collection for testing."""
        collection = MagicMock()

        # For find_one
        collection.find_one.return_value = None
        collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        # For find
        cursor_mock = MagicMock()
        cursor_mock.to_list.return_value = []
        collection.find = MagicMock(return_value=cursor_mock)

        # Other operations
        collection.update_one.return_value = MagicMock(modified_count=1)
        collection.delete_one.return_value = MagicMock(deleted_count=1)

        return collection

    @pytest.fixture
    def mock_vector_collection(self):
        """Mock MongoDB vector collection for testing."""
        collection = MagicMock()

        # For find
        cursor_mock = MagicMock()
        cursor_mock.__iter__.return_value = []
        collection.find = MagicMock(return_value=cursor_mock)

        # For aggregate
        agg_cursor_mock = MagicMock()
        agg_cursor_mock.__iter__.return_value = []
        collection.aggregate = MagicMock(return_value=agg_cursor_mock)

        # Other operations
        collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        collection.update_one.return_value = MagicMock(modified_count=1)
        collection.delete_one.return_value = MagicMock(deleted_count=1)

        return collection

    @pytest.fixture
    def mock_container_collection(self):
        """Mock MongoDB container collection for testing."""
        collection = MagicMock()

        # For find_one
        collection.find_one.return_value = None
        collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        # For find
        cursor_mock = MagicMock()
        cursor_mock.to_list.return_value = []
        collection.find = MagicMock(return_value=cursor_mock)

        # Other operations
        collection.update_one.return_value = MagicMock(modified_count=1)
        collection.delete_one.return_value = MagicMock(deleted_count=1)

        return collection

    @pytest.fixture
    def mongo_repository(self, mock_collection, mock_vector_collection, mock_container_collection):
        """MongoDB repository with mocked collections."""
        repo = MongoContextRepository(
            db_name="test_db",
            collection_name="context_items",
            vector_collection_name="context_vectors",
            container_collection_name="containers"
        )
        # Replace the collections with mocks
        repo._collection = mock_collection
        repo._vector_collection = mock_vector_collection
        repo._container_collection = mock_container_collection
        return repo

    @pytest.fixture
    def sample_context_item(self):
        """Sample context item for testing."""
        return ContextItem(
            id="test-id",
            source="test_file.py",
            content="def test_function():\n    return 'Hello, World!'",
            content_type=ContentType.PYTHON,
            metadata={"author": "Test Author"},
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
        )

    @pytest.fixture
    def sample_container(self):
        """Sample container for testing."""
        return Container(
            id="container-id",
            name="test-container",
            title="Test Container",
            container_type="code",
            source_path="/path/to/source",
            description="Test container description",
            priority=5
        )

    def test_add_context_item(self, mongo_repository, mock_collection,
                            mock_vector_collection, sample_context_item):
        """Test adding a context item to MongoDB (U-DB-1)."""
        # Arrange
        mock_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId())
        mock_vector_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId())

        # Act
        result = mongo_repository.add(sample_context_item)

        # Assert
        mock_collection.insert_one.assert_called_once()
        mock_vector_collection.insert_one.assert_called_once()
        assert result is not None
        assert result.id == sample_context_item.id
        assert result.source == sample_context_item.source
        assert result.content == sample_context_item.content

    def test_get_context_item_by_id(self, mongo_repository,
                                  mock_collection, sample_context_item):
        """Test retrieving a context item by ID from MongoDB (U-DB-1)."""
        # Arrange
        mock_document = {
            "_id": ObjectId(),
            "id": sample_context_item.id,
            "source": sample_context_item.source,
            "content": sample_context_item.content,
            "content_type": sample_context_item.content_type,
            "metadata": sample_context_item.metadata,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        mock_collection.find_one.return_value = mock_document

        # Act
        result = mongo_repository.get_by_id(sample_context_item.id)

        # Assert
        mock_collection.find_one.assert_called_once_with(
            {"id": sample_context_item.id})
        assert result is not None
        assert result.id == sample_context_item.id
        assert result.source == sample_context_item.source
        assert result.content == sample_context_item.content

    def test_get_context_item_not_found(self, mongo_repository,
                                      mock_collection):
        """Test getting a non-existent context item (U-DB-1)."""
        # Arrange
        mock_collection.find_one.return_value = None

        # Act
        result = mongo_repository.get_by_id("nonexistent-id")

        # Assert
        mock_collection.find_one.assert_called_once_with(
            {"id": "nonexistent-id"})
        assert result is None

    def test_update_context_item(self, mongo_repository, mock_collection,
                               mock_vector_collection, sample_context_item):
        """Test updating a context item in MongoDB (U-DB-1)."""
        # Arrange
        mock_document = {
            "_id": ObjectId(),
            "id": sample_context_item.id,
            "source": sample_context_item.source,
            "content": sample_context_item.content,
            "content_type": sample_context_item.content_type,
            "metadata": sample_context_item.metadata,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        mock_collection.find_one.return_value = mock_document
        mock_collection.update_one.return_value = MagicMock(modified_count=1)
        mock_vector_collection.update_one.return_value = MagicMock(
            modified_count=1)

        # Update the sample item
        updated_item = sample_context_item
        updated_item.content = "def updated_function():\n    return 'Updated!'"

        # Act
        result = mongo_repository.update(updated_item)

        # Assert
        mock_collection.find_one.assert_called_once_with(
            {"id": updated_item.id})
        mock_collection.update_one.assert_called_once()
        mock_vector_collection.update_one.assert_called_once()
        assert result is not None
        assert result.content == updated_item.content

    def test_update_nonexistent_item(self, mongo_repository,
                                   mock_collection, sample_context_item):
        """Test updating a non-existent context item (U-DB-2)."""
        # Arrange
        mock_collection.find_one.return_value = None

        # Act & Assert
        with pytest.raises(KeyError):
            mongo_repository.update(sample_context_item)

    def test_delete_context_item(self, mongo_repository, mock_collection,
                               mock_vector_collection):
        """Test deleting a context item from MongoDB (U-DB-1)."""
        # Arrange
        context_id = "test-id"
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)
        mock_vector_collection.delete_one.return_value = MagicMock(
            deleted_count=1)

        # Act
        result = mongo_repository.delete(context_id)

        # Assert
        mock_collection.delete_one.assert_called_once_with({"id": context_id})
        mock_vector_collection.delete_one.assert_called_once_with(
            {"id": context_id})
        assert result is True

    def test_delete_nonexistent_item(self, mongo_repository,
                                   mock_collection, mock_vector_collection):
        """Test deleting a non-existent context item (U-DB-2)."""
        # Arrange
        context_id = "nonexistent-id"
        mock_collection.delete_one.return_value = MagicMock(deleted_count=0)
        mock_vector_collection.delete_one.return_value = MagicMock(
            deleted_count=0)

        # Act
        result = mongo_repository.delete(context_id)

        # Assert
        mock_collection.delete_one.assert_called_once_with({"id": context_id})
        mock_vector_collection.delete_one.assert_called_once_with(
            {"id": context_id})
        assert result is False

    def test_list_context_items(self, mongo_repository, mock_collection):
        """Test listing context items from MongoDB (U-DB-1)."""
        # Arrange
        mock_documents = [
            {
                "_id": ObjectId(),
                "id": "item1",
                "source": "file1.py",
                "content": "def function1():\n    pass",
                "content_type": ContentType.PYTHON,
                "metadata": {},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "_id": ObjectId(),
                "id": "item2",
                "source": "file2.py",
                "content": "def function2():\n    pass",
                "content_type": ContentType.PYTHON,
                "metadata": {},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        mock_collection.find.return_value.to_list.return_value = mock_documents

        # Act
        result = mongo_repository.list()

        # Assert
        mock_collection.find.assert_called_once()
        assert len(result) == 2
        assert result[0].id == "item1"
        assert result[1].id == "item2"

    def test_list_with_filters(self, mongo_repository, mock_collection):
        """Test listing context items with filters (U-DB-3)."""
        # Arrange
        filters = {"content_type": ContentType.PYTHON}
        mock_documents = [
            {
                "_id": ObjectId(),
                "id": "item1",
                "source": "file1.py",
                "content": "def function1():\n    pass",
                "content_type": ContentType.PYTHON,
                "metadata": {},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        mock_collection.find.return_value.to_list.return_value = mock_documents

        # Act
        result = mongo_repository.list(filters)

        # Assert
        mock_collection.find.assert_called_once()
        assert len(result) == 1
        assert result[0].id == "item1"
        assert result[0].content_type == ContentType.PYTHON

    def test_search_by_vector(self, mongo_repository,
                            mock_vector_collection, mock_collection):
        """Test vector similarity search (U-DB-3)."""
        # Arrange
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        limit = 2

        # Mock the vector search aggregation result
        mock_search_results = [
            {
                "_id": ObjectId(),
                "id": "item1",
                "vector": [0.2, 0.3, 0.4, 0.5, 0.6],
                "score": 0.95
            },
            {
                "_id": ObjectId(),
                "id": "item2",
                "vector": [0.3, 0.4, 0.5, 0.6, 0.7],
                "score": 0.85
            }
        ]

        # Mock the find method for each found item
        mock_documents = [
            {
                "_id": ObjectId(),
                "id": "item1",
                "source": "file1.py",
                "content": "def function1():\n    pass",
                "content_type": ContentType.PYTHON,
                "metadata": {},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "_id": ObjectId(),
                "id": "item2",
                "source": "file2.py",
                "content": "def function2():\n    pass",
                "content_type": ContentType.PYTHON,
                "metadata": {},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]

        mock_vector_collection.aggregate.return_value.__iter__.return_value = mock_search_results

        def mock_find_one_side_effect(query):
            item_id = query["id"]
            for doc in mock_documents:
                if doc["id"] == item_id:
                    return doc
            return None

        mock_collection.find_one.side_effect = mock_find_one_side_effect

        # Act
        result = mongo_repository.search_by_vector(query_vector, limit)

        # Assert
        mock_vector_collection.aggregate.assert_called_once()
        assert len(result) == 2
        assert result[0][0].id == "item1"
        assert result[0][1] == 0.95
        assert result[1][0].id == "item2"
        assert result[1][1] == 0.85

    def test_add_container(self, mongo_repository,
                           mock_container_collection, sample_container):
        """Test adding a container to MongoDB."""
        # Arrange
        mock_container_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId())

        # Act
        result = mongo_repository.add_container(
            sample_container)

        # Assert
        mock_container_collection.insert_one.assert_called_once()
        assert result is not None
        assert result.id == sample_container.id
        assert result.name == sample_container.name
        assert result.title == sample_container.title
        assert result.container_type == sample_container.container_type

    def test_get_container(self, mongo_repository,
                           mock_container_collection, sample_container):
        """Test retrieving a container by ID from MongoDB."""
        # Arrange
        mock_document = {
            "_id": ObjectId(),
            "id": sample_container.id,
            "name": sample_container.name,
            "title": sample_container.title,
            "container_type": sample_container.container_type.value,
            "source_path": sample_container.source_path,
            "description": sample_container.description,
            "priority": sample_container.priority,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "context_item_ids": []
        }
        mock_container_collection.find_one.return_value = mock_document

        # Act
        result = mongo_repository.get_container(
            sample_container.id)

        # Assert
        mock_container_collection.find_one.assert_called_once_with(
            {"id": sample_container.id})
        assert result is not None
        assert result.id == sample_container.id
        assert result.name == sample_container.name
        assert result.title == sample_container.title
        assert result.container_type == ContainerType.CODE

    def test_update_container(self, mongo_repository,
                              mock_container_collection, sample_container):
        """Test updating a container in MongoDB."""
        # Arrange
        mock_document = {
            "_id": ObjectId(),
            "id": sample_container.id,
            "name": sample_container.name,
            "title": sample_container.title,
            "container_type": sample_container.container_type.value,
            "source_path": sample_container.source_path,
            "description": sample_container.description,
            "priority": sample_container.priority,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "context_item_ids": []
        }
        mock_container_collection.find_one.return_value = mock_document
        mock_container_collection.update_one.return_value = MagicMock(
            modified_count=1)

        # Update the sample container
        updated_container = sample_container
        updated_container.title = "Updated Container Title"
        updated_container.description = "Updated container description"

        # Act
        result = mongo_repository.update_container(
            updated_container)

        # Assert
        mock_container_collection.find_one.assert_called_once_with(
            {"id": updated_container.id})
        mock_container_collection.update_one.assert_called_once()
        assert result is not None
        assert result.title == updated_container.title
        assert result.description == updated_container.description

    def test_delete_container(self, mongo_repository,
                              mock_container_collection):
        """Test deleting a container from MongoDB."""
        # Arrange
        container_id = "container-id"
        mock_container_collection.delete_one.return_value = MagicMock(
            deleted_count=1)

        # Act
        result = mongo_repository.delete_container(container_id)

        # Assert
        mock_container_collection.delete_one.assert_called_once_with(
            {"id": container_id})
        assert result is True

    def test_list_containers(self, mongo_repository,
                             mock_container_collection):
        """Test listing containers from MongoDB."""
        # Arrange
        mock_documents = [
            {
                "_id": ObjectId(),
                "id": "container1",
                "name": "container-1",
                "title": "Container 1",
                "container_type": "code",
                "source_path": "/path/to/source1",
                "description": "Container 1 description",
                "priority": 5,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "context_item_ids": []
            },
            {
                "_id": ObjectId(),
                "id": "container2",
                "name": "container-2",
                "title": "Container 2",
                "container_type": "documentation",
                "source_path": "/path/to/source2",
                "description": "Container 2 description",
                "priority": 3,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "context_item_ids": []
            }
        ]
        mock_container_collection.find.return_value.to_list.return_value = mock_documents

        # Act
        result = mongo_repository.list_containers()

        # Assert
        mock_container_collection.find.assert_called_once()
        assert len(result) == 2
        assert result[0].id == "container1"
        assert result[1].id == "container2"
        assert result[0].container_type == ContainerType.CODE
        assert result[1].container_type == ContainerType.DOCUMENTATION

    def test_list_containers_with_filters(self,
                                          mongo_repository,
                                          mock_container_collection):
        """Test listing containers with filters."""
        # Arrange
        filters = {"container_type": ContainerType.CODE}
        mock_documents = [
            {
                "_id": ObjectId(),
                "id": "container1",
                "name": "container-1",
                "title": "Container 1",
                "container_type": "code",
                "source_path": "/path/to/source1",
                "description": "Container 1 description",
                "priority": 5,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "context_item_ids": []
            }
        ]
        mock_container_collection.find.return_value.to_list.return_value = mock_documents

        # Act
        result = mongo_repository.list_containers(filters)

        # Assert
        mock_container_collection.find.assert_called_once()
        assert len(result) == 1
        assert result[0].id == "container1"
        assert result[0].container_type == ContainerType.CODE

    def test_list_by_container(self, mongo_repository,
                               mock_collection, mock_container_collection):
        """Test listing context items by container."""
        # Arrange
        container_id = "container-id"
        mock_documents = [
            {
                "_id": ObjectId(),
                "id": "item1",
                "source": "file1.py",
                "content": "def function1():\n    pass",
                "content_type": ContentType.PYTHON,
                "metadata": {},
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "container_id": container_id,
                "is_container_root": True,
                "parent_id": None,
                "is_chunk": False,
                "chunk_type": None,
                "chunk_metadata": {}
            },
            {
                "_id": ObjectId(),
                "id": "item2",
                "source": "file2.py",
                "content": "def function2():\n    pass",
                "content_type": ContentType.PYTHON,
                "metadata": {},
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "container_id": container_id,
                "is_container_root": False,
                "parent_id": None,
                "is_chunk": False,
                "chunk_type": None,
                "chunk_metadata": {}
            }
        ]
        mock_collection.find.return_value.to_list.return_value = mock_documents

        # Act
        result = mongo_repository.list_by_container(
            container_id)

        # Assert
        mock_collection.find.assert_called_once_with(
            {"container_id": container_id})
        assert len(result) == 2
        assert result[0].id == "item1"
        assert result[1].id == "item2"
        assert result[0].container_id == container_id
        assert result[1].container_id == container_id

    def test_handle_connection_error(self, mongo_repository,
                                   mock_collection):
        """Test handling MongoDB connection errors (U-DB-2)."""
        # Arrange
        mock_collection.find_one.side_effect = Exception("Connection error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            mongo_repository.get_by_id("test-id")

        assert "Connection error" in str(exc_info.value)