import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from src.domain.ports.directory_processor import DirectoryProcessor
from src.domain.ports.file_system import FileSystem
from src.infrastructure.adapters.file_system_directory_processor import \
    FileSystemDirectoryProcessor


class TestFileSystemDirectoryProcessor:
    """Test cases for the FileSystemDirectoryProcessor."""

    @pytest.fixture
    def mock_file_system(self):
        """Create a mock file system."""
        mock_fs = Mock(spec=FileSystem)

        # Set up default behaviors
        mock_fs.file_exists.return_value = True
        mock_fs.read_file.return_value = "test content"

        return mock_fs

    @pytest.fixture
    def directory_processor(self, mock_file_system):
        """Create a directory processor with a mock file system."""
        return FileSystemDirectoryProcessor(file_system=mock_file_system)

    def test_directory_processor_initialization(self, directory_processor,
                                                mock_file_system):
        """Test that the directory processor initializes correctly."""
        assert isinstance(directory_processor, DirectoryProcessor)
        assert directory_processor.file_system == mock_file_system

    def test_traverse_directory(self, directory_processor, mock_file_system):
        """Test directory traversal."""
        # Arrange
        test_dir = "/test/dir"
        mock_file_system.list_files.return_value = [
            "/test/dir/file1.py",
            "/test/dir/file2.txt"
        ]

        # Act
        result = directory_processor.traverse_directory(test_dir, max_depth=1)

        # Assert
        mock_file_system.list_files.assert_called_once_with(test_dir,
                                                            recursive=False)
        assert len(result) == 2
        assert "/test/dir/file1.py" in result
        assert "/test/dir/file2.txt" in result

    def test_traverse_directory_with_depth(self, directory_processor,
                                           mock_file_system):
        """Test directory traversal with multiple depth levels."""
        # Arrange
        test_dir = "/test/dir"

        # Mock the file system to return different results for different directories
        def list_files_side_effect(directory, pattern=None, recursive=False):
            if directory == "/test/dir":
                return [
                    "/test/dir/file1.py",
                    "/test/dir/subdir"  # This is a directory, not a file
                ]
            elif directory == "/test/dir/subdir":
                return [
                    "/test/dir/subdir/file2.py"
                ]
            return []

        mock_file_system.list_files.side_effect = list_files_side_effect

        # Mock isdir to identify directories
        def is_dir_side_effect(path):
            return path == "/test/dir/subdir"

        with patch("os.path.isdir", side_effect=is_dir_side_effect):
            # Act
            result = directory_processor.traverse_directory(test_dir,
                                                            max_depth=2)

        # Assert
        assert len(result) == 2
        assert "/test/dir/file1.py" in result
        assert "/test/dir/subdir/file2.py" in result

    def test_traverse_directory_depth_limit(self, directory_processor,
                                            mock_file_system):
        """Test that directory traversal respects depth limits."""
        # Arrange
        test_dir = "/test/dir"

        # Mock the file system to return different results for different directories
        def list_files_side_effect(directory, pattern=None, recursive=False):
            if directory == "/test/dir":
                return [
                    "/test/dir/file1.py",
                    "/test/dir/subdir"  # This is a directory, not a file
                ]
            elif directory == "/test/dir/subdir":
                return [
                    "/test/dir/subdir/file2.py",
                    "/test/dir/subdir/subsubdir"  # Deeper directory
                ]
            elif directory == "/test/dir/subdir/subsubdir":
                return [
                    "/test/dir/subdir/subsubdir/file3.py"
                ]
            return []

        mock_file_system.list_files.side_effect = list_files_side_effect

        # Mock isdir to identify directories
        def is_dir_side_effect(path):
            return path in ["/test/dir/subdir", "/test/dir/subdir/subsubdir"]

        with patch("os.path.isdir", side_effect=is_dir_side_effect):
            # Act - with depth limit of 1
            result1 = directory_processor.traverse_directory(test_dir,
                                                             max_depth=1)

            # Act - with depth limit of 2
            result2 = directory_processor.traverse_directory(test_dir,
                                                             max_depth=2)

            # Act - with depth limit of 3
            result3 = directory_processor.traverse_directory(test_dir,
                                                             max_depth=3)

        # Assert
        assert len(result1) == 1  # Only the top-level file
        assert "/test/dir/file1.py" in result1
        assert "/test/dir/subdir/file2.py" not in result1

        assert len(result2) == 2  # Top level and first subdirectory
        assert "/test/dir/file1.py" in result2
        assert "/test/dir/subdir/file2.py" in result2
        assert "/test/dir/subdir/subsubdir/file3.py" not in result2

        assert len(result3) == 3  # All files at all levels
        assert "/test/dir/file1.py" in result3
        assert "/test/dir/subdir/file2.py" in result3
        assert "/test/dir/subdir/subsubdir/file3.py" in result3

    def test_get_file_content(self, directory_processor, mock_file_system):
        """Test getting file content."""
        # Arrange
        file_path = "/test/dir/file1.py"
        expected_content = "def test():\n    pass"
        mock_file_system.read_file.return_value = expected_content

        # Act
        content = directory_processor.get_file_content(file_path)

        # Assert
        mock_file_system.read_file.assert_called_once_with(file_path)
        assert content == expected_content

    def test_is_file_supported(self, directory_processor):
        """Test checking if a file is supported."""
        # Arrange & Act & Assert
        assert directory_processor.is_file_supported("/test/file.py") is True
        assert directory_processor.is_file_supported("/test/file.txt") is True
        assert directory_processor.is_file_supported("/test/file.md") is True
        assert directory_processor.is_file_supported("/test/file.json") is True
        assert directory_processor.is_file_supported("/test/file.yaml") is True
        assert directory_processor.is_file_supported("/test/file.yml") is True
        assert directory_processor.is_file_supported("/test/file.html") is True
        assert directory_processor.is_file_supported("/test/file.js") is True
        assert directory_processor.is_file_supported("/test/file.css") is True

        # Binary files should not be supported
        assert directory_processor.is_file_supported("/test/file.bin") is False
        assert directory_processor.is_file_supported("/test/file.exe") is False
        assert directory_processor.is_file_supported("/test/file.jpg") is False
        assert directory_processor.is_file_supported("/test/file.png") is False

    def test_process_directory(self, directory_processor, mock_file_system):
        """Test processing a directory."""
        # Arrange
        test_dir = "/test/dir"
        container_id = "test-container-id"

        # Mock the file system to return some files
        def list_files_side_effect(directory, pattern=None, recursive=False):
            if directory == test_dir:
                return [
                    "/test/dir/file1.py",
                    "/test/dir/file2.txt",
                    "/test/dir/subdir"
                ]
            elif directory == "/test/dir/subdir":
                return [
                    "/test/dir/subdir/file3.py"
                ]
            return []

        mock_file_system.list_files.side_effect = list_files_side_effect

        # Mock read_file to return different content for different files
        def read_file_side_effect(path):
            if path == "/test/dir/file1.py":
                return "def test1():\n    pass"
            elif path == "/test/dir/file2.txt":
                return "Test text content"
            elif path == "/test/dir/subdir/file3.py":
                return "def test3():\n    pass"
            return ""

        mock_file_system.read_file.side_effect = read_file_side_effect

        # Mock isdir to identify directories
        def is_dir_side_effect(path):
            return path in ["/test/dir", "/test/dir/subdir"]

        with patch("os.path.isdir", side_effect=is_dir_side_effect):
            # Act
            result = directory_processor.process_directory(test_dir,
                                                           container_id=container_id)

        # Assert
        assert result["directory"] == test_dir
        assert result["container_id"] == container_id
        assert len(result["processed_files"]) == 3

        # Check that each file was processed correctly
        processed_paths = [f["path"] for f in result["processed_files"]]
        assert "/test/dir/file1.py" in processed_paths
        assert "/test/dir/file2.txt" in processed_paths
        assert "/test/dir/subdir/file3.py" in processed_paths

        # Check that the content was retrieved
        for file_info in result["processed_files"]:
            if file_info["path"] == "/test/dir/file1.py":
                assert file_info["content"] == "def test1():\n    pass"
            elif file_info["path"] == "/test/dir/file2.txt":
                assert file_info["content"] == "Test text content"
            elif file_info["path"] == "/test/dir/subdir/file3.py":
                assert file_info["content"] == "def test3():\n    pass"

    def test_process_directory_with_file_types(self, directory_processor,
                                               mock_file_system):
        """Test processing a directory with specific file types."""
        # Arrange
        test_dir = "/test/dir"
        file_types = [".py"]  # Only process Python files

        # Mock the file system to return some files
        mock_file_system.list_files.return_value = [
            "/test/dir/file1.py",
            "/test/dir/file2.txt",
            "/test/dir/file3.py"
        ]

        # Mock read_file to return content
        mock_file_system.read_file.return_value = "test content"

        # Mock isdir to identify directories
        def is_dir_side_effect(path):
            return path == "/test/dir"

        with patch("os.path.isdir", side_effect=is_dir_side_effect):
            # Act
            result = directory_processor.process_directory(test_dir,
                                                       file_types=file_types)

        # Assert
        assert len(result["processed_files"]) == 2  # Only the Python files
        processed_paths = [f["path"] for f in result["processed_files"]]
        assert "/test/dir/file1.py" in processed_paths
        assert "/test/dir/file3.py" in processed_paths
        assert "/test/dir/file2.txt" not in processed_paths

    def test_process_directory_invalid_path(self, directory_processor,
                                            mock_file_system):
        """Test processing an invalid directory path."""
        # Arrange
        mock_file_system.file_exists.return_value = False

        # Act & Assert
        with pytest.raises(ValueError, match="Directory not found"):
            directory_processor.process_directory("/invalid/dir")

    def test_process_directory_not_a_directory(self, directory_processor,
                                               mock_file_system):
        """Test processing a path that is a file, not a directory."""
        # Arrange
        file_path = "/test/file.py"
        mock_file_system.file_exists.return_value = True

        with patch("os.path.isdir", return_value=False):
            # Act & Assert
            with pytest.raises(ValueError, match="Not a directory"):
                directory_processor.process_directory(file_path)