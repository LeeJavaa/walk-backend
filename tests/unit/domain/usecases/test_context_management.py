import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any, Tuple, Optional

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.ports.context_repository import ContextRepository
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.file_system import FileSystem
from src.domain.ports.vector_store import VectorStore
from src.domain.usecases.context_management import (
    AddContextUseCase,
    RemoveContextUseCase,
    UpdateContextUseCase,
    ListContextUseCase,
    SearchContextUseCase
)


class TestContextManagementUseCases:
    """Test cases for the context management use cases."""

    @pytest.fixture
    def context_repository_mock(self):
        """Mock for the context repository."""
        repository = Mock(spec=ContextRepository)
        return repository

    @pytest.fixture
    def llm_provider_mock(self):
        """Mock for the LLM provider."""
        provider = Mock(spec=LLMProvider)
        # Default embedding for tests
        provider.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        return provider

    @pytest.fixture
    def file_system_mock(self):
        """Mock for the file system."""
        file_system = Mock(spec=FileSystem)
        file_system.read_file.return_value = "def test_function():\n    return 'Hello, World!'"
        file_system.file_exists.return_value = True
        return file_system

    @pytest.fixture
    def vector_store_mock(self):
        """Mock for the vector store."""
        vector_store = Mock(spec=VectorStore)
        return vector_store

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

    def test_add_context_from_file_path(self, context_repository_mock,
                                        llm_provider_mock, file_system_mock):
        """Test adding context from a file path (U-CS-3)."""
        # Arrange
        context_repository_mock.add.side_effect = lambda \
            context_item: context_item

        use_case = AddContextUseCase(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock,
            file_system=file_system_mock
        )
        file_path = "test_file.py"

        # Act
        result = use_case.execute_from_file_path(file_path)

        # Assert
        file_system_mock.file_exists.assert_called_once_with(file_path)
        file_system_mock.read_file.assert_called_once_with(file_path)
        llm_provider_mock.generate_embedding.assert_called_once()
        context_repository_mock.add.assert_called_once()
        assert result is not None
        assert result.source == file_path
        assert result.content_type == ContentType.PYTHON

    def test_add_context_from_content(self, context_repository_mock,
                                      llm_provider_mock):
        """Test adding context from content (U-CS-3)."""
        # Arrange
        context_repository_mock.add.side_effect = lambda \
            context_item: context_item

        use_case = AddContextUseCase(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock,
            file_system=None
        )
        source = "test_source"
        content = "def test_function():\n    return 'Hello, World!'"
        content_type = ContentType.PYTHON

        # Act
        result = use_case.execute_from_content(source, content, content_type)

        # Assert
        llm_provider_mock.generate_embedding.assert_called_once()
        context_repository_mock.add.assert_called_once()
        assert result is not None
        assert result.source == source
        assert result.content == content
        assert result.content_type == content_type

    def test_remove_context(self, context_repository_mock, sample_context_item):
        """Test removing context."""
        # Arrange
        use_case = RemoveContextUseCase(
            context_repository=context_repository_mock)
        context_id = "test-id"
        context_repository_mock.get_by_id.return_value = sample_context_item
        context_repository_mock.delete.return_value = True

        # Act
        result = use_case.execute(context_id)

        # Assert
        context_repository_mock.get_by_id.assert_called_once_with(context_id)
        context_repository_mock.delete.assert_called_once_with(context_id)
        assert result is True

    def test_remove_context_not_found(self, context_repository_mock):
        """Test removing context that does not exist."""
        # Arrange
        use_case = RemoveContextUseCase(
            context_repository=context_repository_mock)
        context_id = "nonexistent-id"
        context_repository_mock.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(KeyError):
            use_case.execute(context_id)
        context_repository_mock.get_by_id.assert_called_once_with(context_id)
        context_repository_mock.delete.assert_not_called()

    def test_update_context(self, context_repository_mock, llm_provider_mock,
                            sample_context_item):
        """Test updating context."""
        # Arrange
        use_case = UpdateContextUseCase(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock
        )
        context_id = "test-id"
        new_content = "def updated_function():\n    return 'Updated!'"
        context_repository_mock.get_by_id.return_value = sample_context_item

        # Mocking the update method to return the updated item
        def update_mock(item):
            item.content = new_content
            return item

        context_repository_mock.update.side_effect = update_mock

        # Act
        result = use_case.execute(context_id, new_content)

        # Assert
        context_repository_mock.get_by_id.assert_called_once_with(context_id)
        llm_provider_mock.generate_embedding.assert_called_once()
        context_repository_mock.update.assert_called_once()
        assert result is not None
        assert result.content == new_content

    def test_list_context(self, context_repository_mock, sample_context_item):
        """Test listing context items."""
        # Arrange
        use_case = ListContextUseCase(
            context_repository=context_repository_mock)
        filters = {"content_type": ContentType.PYTHON}
        context_repository_mock.list.return_value = [sample_context_item]

        # Act
        result = use_case.execute(filters)

        # Assert
        context_repository_mock.list.assert_called_once_with(filters)
        assert result is not None
        assert len(result) == 1
        assert result[0] == sample_context_item

    def test_search_context(self, context_repository_mock, llm_provider_mock,
                            sample_context_item):
        """Test searching context based on query (U-CS-3)."""
        # Arrange
        use_case = SearchContextUseCase(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock
        )
        query = "How to implement a test function"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        llm_provider_mock.generate_embedding.return_value = embedding
        context_repository_mock.search_by_vector.return_value = [
            (sample_context_item, 0.9)]

        # Act
        result = use_case.execute(query)

        # Assert
        llm_provider_mock.generate_embedding.assert_called_once_with(query)
        context_repository_mock.search_by_vector.assert_called_once_with(
            embedding, 10)
        assert result is not None
        assert len(result) == 1
        assert result[0][0] == sample_context_item
        assert result[0][1] == 0.9