import pytest
import os
import tempfile
import shutil
from pathlib import Path

from src.infrastructure.adapters.file_system_adapter import FileSystemAdapter

# Mark the whole file as integration tests
pytestmark = pytest.mark.integration


class TestFileSystemAdapterIntegration:
    """Integration tests for the file system adapter."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up after test
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def file_system_adapter(self):
        """Create a file system adapter for testing."""
        return FileSystemAdapter()

    def test_read_write_file(self, file_system_adapter, temp_dir):
        """Test reading and writing a file (I-CS-4)."""
        # Arrange
        test_content = "This is test content for read/write test"
        test_path = os.path.join(temp_dir, "test_file.txt")

        # Act - Write file
        write_result = file_system_adapter.write_file(test_path, test_content)

        # Assert write result
        assert write_result is True
        assert os.path.exists(test_path)

        # Act - Read file
        read_content = file_system_adapter.read_file(test_path)

        # Assert read result
        assert read_content == test_content

    def test_read_write_binary_file(self, file_system_adapter, temp_dir):
        """Test reading and writing a binary file (I-CS-4)."""
        # Arrange
        test_content = b"\x00\x01\x02\x03\x04"
        test_path = os.path.join(temp_dir, "test_binary.bin")

        # Act - Write file
        write_result = file_system_adapter.write_file(test_path, test_content,
                                                      binary=True)

        # Assert write result
        assert write_result is True
        assert os.path.exists(test_path)

        # Act - Read file
        read_content = file_system_adapter.read_file(test_path, binary=True)

        # Assert read result
        assert read_content == test_content

    def test_list_files(self, file_system_adapter, temp_dir):
        """Test listing files in a directory (I-CS-4)."""
        # Arrange - Create test files
        test_files = ["file1.txt", "file2.py", "file3.md"]
        for filename in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "w") as f:
                f.write(f"Content for {filename}")

        # Also create a subdirectory with files
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "subfile.txt"), "w") as f:
            f.write("Content for subfile")

        # Act
        files = file_system_adapter.list_files(temp_dir)

        # Assert
        assert len(files) == len(test_files)
        for filename in test_files:
            assert os.path.join(temp_dir, filename) in files
        assert subdir not in files

    def test_list_files_with_pattern(self, file_system_adapter, temp_dir):
        """Test listing files with a pattern (I-CS-4)."""
        # Arrange - Create test files
        test_files = ["file1.txt", "file2.py", "file3.py", "file4.md"]
        for filename in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "w") as f:
                f.write(f"Content for {filename}")

        # Act
        py_files = file_system_adapter.list_files(temp_dir, pattern="*.py")

        # Assert
        assert len(py_files) == 2
        assert os.path.join(temp_dir, "file2.py") in py_files
        assert os.path.join(temp_dir, "file3.py") in py_files
        assert os.path.join(temp_dir, "file1.txt") not in py_files
        assert os.path.join(temp_dir, "file4.md") not in py_files

    def test_file_exists(self, file_system_adapter, temp_dir):
        """Test checking if a file exists (I-CS-4)."""
        # Arrange
        test_path = os.path.join(temp_dir, "existing_file.txt")
        with open(test_path, "w") as f:
            f.write("This file exists")

        nonexistent_path = os.path.join(temp_dir, "nonexistent_file.txt")

        # Act & Assert
        assert file_system_adapter.file_exists(test_path) is True
        assert file_system_adapter.file_exists(nonexistent_path) is False

    def test_delete_file(self, file_system_adapter, temp_dir):
        """Test deleting a file (I-CS-4)."""
        # Arrange
        test_path = os.path.join(temp_dir, "file_to_delete.txt")
        with open(test_path, "w") as f:
            f.write("This file will be deleted")

        # Act
        delete_result = file_system_adapter.delete_file(test_path)

        # Assert
        assert delete_result is True
        assert not os.path.exists(test_path)

    def test_delete_nonexistent_file(self, file_system_adapter, temp_dir):
        """Test deleting a non-existent file (I-CS-4)."""
        # Arrange
        nonexistent_path = os.path.join(temp_dir, "nonexistent_file.txt")

        # Act
        delete_result = file_system_adapter.delete_file(nonexistent_path)

        # Assert
        assert delete_result is False

    def test_recursive_file_listing(self, file_system_adapter, temp_dir):
        """Test recursive listing of files (I-CS-4)."""
        # Arrange - Create a directory structure
        subdir1 = os.path.join(temp_dir, "subdir1")
        subdir2 = os.path.join(temp_dir, "subdir2")
        subdir1_1 = os.path.join(subdir1, "subdir1_1")

        os.makedirs(subdir1)
        os.makedirs(subdir2)
        os.makedirs(subdir1_1)

        # Create files in different directories
        files = {
            os.path.join(temp_dir, "root_file.txt"): "Root file",
            os.path.join(subdir1, "subdir1_file.txt"): "Subdir1 file",
            os.path.join(subdir2, "subdir2_file.py"): "Subdir2 file",
            os.path.join(subdir1_1, "subdir1_1_file.py"): "Subdir1_1 file",
        }

        for path, content in files.items():
            with open(path, "w") as f:
                f.write(content)

        # Act
        all_files = file_system_adapter.list_files(temp_dir, recursive=True)
        py_files = file_system_adapter.list_files(temp_dir, pattern="*.py",
                                                  recursive=True)

        # Assert
        assert len(all_files) == len(files)
        for file_path in files.keys():
            assert file_path in all_files

        assert len(py_files) == 2
        assert os.path.join(subdir2, "subdir2_file.py") in py_files
        assert os.path.join(subdir1_1, "subdir1_1_file.py") in py_files

    def test_error_handling(self, file_system_adapter):
        """Test error handling for invalid paths (I-CS-4)."""
        # Arrange
        invalid_dir = "/path/that/does/not/exist"

        # Act & Assert
        with pytest.raises(ValueError):
            file_system_adapter.list_files(invalid_dir)

        assert file_system_adapter.file_exists(invalid_dir) is False
        assert file_system_adapter.delete_file(invalid_dir) is False