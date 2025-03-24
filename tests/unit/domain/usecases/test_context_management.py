import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any, Tuple, Optional

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.container import Container
from src.domain.ports.context_repository import ContextRepository
from src.domain.ports.directory_processor import DirectoryProcessor
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.file_system import FileSystem
from src.domain.usecases.context_management import (
    AddContextUseCase,
    AddDirectoryUseCase,
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
    def directory_processor_mock(self):
        """Mock for the directory processor."""
        processor = Mock(spec=DirectoryProcessor)

        # Default behavior: return a list of file paths when traversing
        processor.traverse_directory.return_value = [
            "/test_dir/file1.py",
            "/test_dir/file2.txt",
            "/test_dir/subdir/file3.py"
        ]

        # Default behavior for file content
        processor.get_file_content.side_effect = lambda \
            path: f"Content of {path}"

        # Default behavior for file type support
        processor.is_file_supported.return_value = True

        # Default behavior for directory processing
        processor.process_directory.return_value = {
            "directory": "/test_dir",
            "processed_files": [
                {"path": "/test_dir/file1.py",
                 "content": "Content of /test_dir/file1.py"},
                {"path": "/test_dir/file2.txt",
                 "content": "Content of /test_dir/file2.txt"},
                {"path": "/test_dir/subdir/file3.py",
                 "content": "Content of /test_dir/subdir/file3.py"},
            ],
            "total_files": 3
        }

        return processor

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

    def test_add_directory_context_use_case(self, context_repository_mock,
                                            llm_provider_mock,
                                            directory_processor_mock):
        """Test adding an entire directory to the context system."""
        # Arrange
        use_case = AddDirectoryUseCase(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock,
            directory_processor=directory_processor_mock
        )
        directory_path = "/test_dir"

        # Mock repository to return a new container
        container = Container(
            id="container-id",
            name="test-dir",
            title="Test Directory",
            container_type="code",
            source_path=directory_path
        )
        context_repository_mock.add_container.return_value = container

        # Mock repository to return the context items when added
        context_repository_mock.add.side_effect = lambda item: item

        # Act
        result = use_case.execute(directory_path)

        # Assert
        directory_processor_mock.process_directory.assert_called_once_with(
            directory_path, max_depth=10, container_id="container-id",
            file_types=None
        )

        # Check that a container was created
        context_repository_mock.add_container.assert_called_once()
        container_arg = context_repository_mock.add_container.call_args[0][0]
        assert container_arg.source_path == directory_path

        # Check that the context items were added
        assert context_repository_mock.add.call_count == 3  # Three files

        # Check result
        assert result["container"] == container
        assert result["total_files"] == 3
        assert len(result["context_items"]) == 3

    def test_add_directory_with_depth_limit(self, context_repository_mock,
                                            llm_provider_mock,
                                            directory_processor_mock):
        """Test adding a directory with a specified depth limit."""
        # Arrange
        use_case = AddDirectoryUseCase(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock,
            directory_processor=directory_processor_mock
        )
        directory_path = "/test_dir"
        max_depth = 1  # Only include files directly in the directory

        # Mock repository to return a new container
        container = Container(
            id="container-id",
            name="test-dir",
            title="Test Directory",
            container_type="code",
            source_path=directory_path
        )
        context_repository_mock.add_container.return_value = container

        # Update mock for directory_processor to simulate depth limit
        limited_files = ["/test_dir/file1.py",
                         "/test_dir/file2.txt"]  # No subdirectory files
        directory_processor_mock.traverse_directory.return_value = limited_files

        directory_processor_mock.process_directory.return_value = {
            "directory": "/test_dir",
            "processed_files": [
                {"path": "/test_dir/file1.py",
                 "content": "Content of /test_dir/file1.py"},
                {"path": "/test_dir/file2.txt",
                 "content": "Content of /test_dir/file2.txt"},
            ],
            "total_files": 2
        }

        # Act
        result = use_case.execute(directory_path, max_depth=max_depth)

        # Assert
        directory_processor_mock.process_directory.assert_called_once_with(
            directory_path, max_depth=max_depth, container_id="container-id",
            file_types=None
        )

        # Check result
        assert result["total_files"] == 2
        assert len(result["context_items"]) == 2

    def test_add_directory_with_file_type_filter(self, context_repository_mock,
                                                 llm_provider_mock,
                                                 directory_processor_mock):
        """Test adding a directory with file type filtering."""
        # Arrange
        use_case = AddDirectoryUseCase(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock,
            directory_processor=directory_processor_mock
        )
        directory_path = "/test_dir"
        file_types = [".py"]  # Only include Python files

        # Mock repository to return a new container
        container = Container(
            id="container-id",
            name="test-dir",
            title="Test Directory",
            container_type="code",
            source_path=directory_path
        )
        context_repository_mock.add_container.return_value = container

        # Update mock for directory_processor to simulate file type filtering
        python_files = ["/test_dir/file1.py",
                        "/test_dir/subdir/file3.py"]  # Only Python files
        directory_processor_mock.traverse_directory.return_value = python_files

        directory_processor_mock.process_directory.return_value = {
            "directory": "/test_dir",
            "processed_files": [
                {"path": "/test_dir/file1.py",
                 "content": "Content of /test_dir/file1.py"},
                {"path": "/test_dir/subdir/file3.py",
                 "content": "Content of /test_dir/subdir/file3.py"},
            ],
            "total_files": 2
        }

        # Act
        result = use_case.execute(directory_path, file_types=file_types)

        # Assert
        directory_processor_mock.process_directory.assert_called_once_with(
            directory_path, max_depth=10, container_id="container-id",
            file_types=file_types
        )

        # Check result
        assert result["total_files"] == 2
        assert len(result["context_items"]) == 2

        # Verify only Python files were processed
        context_items = result["context_items"]
        assert all(item.source.endswith(".py") for item in context_items)

    def test_add_directory_with_existing_container(self,
                                                   context_repository_mock,
                                                   llm_provider_mock,
                                                   directory_processor_mock):
        """Test adding files to an existing container."""
        # Arrange
        use_case = AddDirectoryUseCase(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock,
            directory_processor=directory_processor_mock
        )
        directory_path = "/test_dir"
        container_id = "existing-container-id"

        # Mock repository to return an existing container
        existing_container = Container(
            id=container_id,
            name="existing-container",
            title="Existing Container",
            container_type="code",
            source_path="/original/path"
        )
        context_repository_mock.get_container.return_value = existing_container

        # Act
        result = use_case.execute(directory_path, container_id=container_id)

        # Assert
        # Check that we got the container by ID instead of creating a new one
        context_repository_mock.get_container.assert_called_once_with(
            container_id)
        context_repository_mock.add_container.assert_not_called()

        # Check that directory processor was called with the existing container ID
        directory_processor_mock.process_directory.assert_called_once_with(
            directory_path, max_depth=10, container_id=container_id,
            file_types=None
        )

        # Check result
        assert result["container"] == existing_container

    def test_add_directory_error_handling(self, context_repository_mock,
                                          llm_provider_mock,
                                          directory_processor_mock):
        """Test error handling when adding a directory."""
        # Arrange
        use_case = AddDirectoryUseCase(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock,
            directory_processor=directory_processor_mock
        )

        # Mock directory processor to raise exceptions
        directory_processor_mock.process_directory.side_effect = ValueError(
            "Invalid directory")

        # Act & Assert - Invalid directory path
        with pytest.raises(ValueError, match="Invalid directory"):
            use_case.execute("/invalid/directory")

        # Test with existing container that doesn't exist
        context_repository_mock.get_container.return_value = None

        # Act & Assert - Invalid container ID
        with pytest.raises(KeyError, match="Container not found"):
            use_case.execute("/test_dir", container_id="nonexistent-container")