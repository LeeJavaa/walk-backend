import pytest
import os
import tempfile
from unittest.mock import patch, mock_open

from src.domain.ports.file_system import FileSystem
from src.infrastructure.adapters.file_system_adapter import FileSystemAdapter


class TestFileSystemAdapter:
    """Unit tests for the file system adapter implementation."""

    @pytest.fixture
    def file_system_adapter(self):
        """Create a file system adapter for testing."""
        return FileSystemAdapter()

    def test_initialization(self, file_system_adapter):
        """Test file system adapter initialization."""
        assert isinstance(file_system_adapter, FileSystem)

    def test_read_file(self, file_system_adapter):
        """Test reading a file."""
        # Arrange
        test_content = "This is test content"
        mock_file = mock_open(read_data=test_content)
        test_path = "/path/to/test_file.txt"

        # Act
        with patch("builtins.open", mock_file):
            content = file_system_adapter.read_file(test_path)

        # Assert
        mock_file.assert_called_once_with(test_path, "r", encoding="utf-8")
        assert content == test_content

    def test_read_file_binary(self, file_system_adapter):
        """Test reading a file in binary mode."""
        # Arrange
        test_content = b"This is binary test content"
        mock_file = mock_open(read_data=test_content)
        test_path = "/path/to/test_file.bin"

        # Act
        with patch("builtins.open", mock_file):
            content = file_system_adapter.read_file(test_path, binary=True)

        # Assert
        mock_file.assert_called_once_with(test_path, "rb")
        assert content == test_content

    def test_read_file_not_found(self, file_system_adapter):
        """Test reading a non-existent file."""
        # Arrange
        test_path = "/path/to/nonexistent_file.txt"

        # Act & Assert
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError):
                file_system_adapter.read_file(test_path)

    def test_write_file(self, file_system_adapter):
        """Test writing a file."""
        # Arrange
        test_content = "This is test content to write"
        mock_file = mock_open()
        test_path = "/path/to/write_file.txt"

        # Act
        with patch("builtins.open", mock_file), \
                patch("os.path.exists", return_value=True), \
                patch("os.makedirs"):
            result = file_system_adapter.write_file(test_path, test_content)

        # Assert
        mock_file.assert_called_once_with(test_path, "w", encoding="utf-8")
        mock_file().write.assert_called_once_with(test_content)
        assert result is True

    def test_write_file_binary(self, file_system_adapter):
        """Test writing a file in binary mode."""
        # Arrange
        test_content = b"This is binary test content to write"
        mock_file = mock_open()
        test_path = "/path/to/write_file.bin"

        # Act
        with patch("builtins.open", mock_file), \
                patch("os.path.exists", return_value=True), \
                patch("os.makedirs"):
            result = file_system_adapter.write_file(test_path, test_content,
                                                    binary=True)

        # Assert
        mock_file.assert_called_once_with(test_path, "wb")
        mock_file().write.assert_called_once_with(test_content)
        assert result is True

    def test_write_file_error(self, file_system_adapter):
        """Test writing a file with an error."""
        # Arrange
        test_content = "This is test content to write"
        test_path = "/path/to/write_file.txt"

        # Act & Assert
        with patch("builtins.open", side_effect=PermissionError()):
            result = file_system_adapter.write_file(test_path, test_content)
            assert result is False

    def test_list_files(self, file_system_adapter):
        """Test listing files in a directory."""
        # Arrange
        test_dir = "/path/to/directory"
        expected_files = [
            "/path/to/directory/file1.txt",
            "/path/to/directory/file2.py",
            "/path/to/directory/file3.md"
        ]
        file_list = ["file1.txt", "file2.py", "file3.md"]

        # Act
        with patch("os.path.isdir", return_value=True), \
                patch("os.listdir", return_value=file_list), \
                patch("os.path.isfile",
                      return_value=True):  # Mock these additional functions
            files = file_system_adapter.list_files(test_dir)

        # Assert
        assert sorted(files) == sorted(expected_files)

    def test_list_files_with_pattern(self, file_system_adapter):
        """Test listing files with a pattern."""
        # Arrange
        test_dir = "/path/to/directory"
        file_list = ["file1.txt", "file2.py", "file3.md", "test.py"]
        expected_files = [
            "/path/to/directory/file2.py",
            "/path/to/directory/test.py"
        ]

        # Act
        with patch("os.path.isdir", return_value=True), \
                patch("os.listdir", return_value=file_list), \
                patch("os.path.isfile",
                      return_value=True):  # Mock these additional functions
            files = file_system_adapter.list_files(test_dir, pattern="*.py")

        # Assert
        assert sorted(files) == sorted(expected_files)

    def test_list_files_directory_not_found(self, file_system_adapter):
        """Test listing files in a non-existent directory."""
        # Arrange
        test_dir = "/path/to/nonexistent_directory"

        # Act & Assert
        with patch("os.path.isdir", return_value=False):
            with pytest.raises(ValueError):
                file_system_adapter.list_files(test_dir)

    def test_file_exists(self, file_system_adapter):
        """Test checking if a file exists."""
        # Arrange
        test_path = "/path/to/existing_file.txt"

        # Act
        with patch("os.path.exists", return_value=True):
            result = file_system_adapter.file_exists(test_path)

        # Assert
        assert result is True

    def test_file_does_not_exist(self, file_system_adapter):
        """Test checking if a file does not exist."""
        # Arrange
        test_path = "/path/to/nonexistent_file.txt"

        # Act
        with patch("os.path.exists", return_value=False):
            result = file_system_adapter.file_exists(test_path)

        # Assert
        assert result is False

    def test_delete_file(self, file_system_adapter):
        """Test deleting a file."""
        # Arrange
        test_path = "/path/to/file_to_delete.txt"

        # Act
        with patch("os.path.exists", return_value=True):
            with patch("os.remove"):
                result = file_system_adapter.delete_file(test_path)

        # Assert
        assert result is True

    def test_delete_nonexistent_file(self, file_system_adapter):
        """Test deleting a non-existent file."""
        # Arrange
        test_path = "/path/to/nonexistent_file.txt"

        # Act
        with patch("os.path.exists", return_value=False):
            result = file_system_adapter.delete_file(test_path)

        # Assert
        assert result is False

    def test_delete_file_error(self, file_system_adapter):
        """Test deleting a file with an error."""
        # Arrange
        test_path = "/path/to/file_to_delete.txt"

        # Act
        with patch("os.path.exists", return_value=True):
            with patch("os.remove", side_effect=PermissionError()):
                result = file_system_adapter.delete_file(test_path)

        # Assert
        assert result is False