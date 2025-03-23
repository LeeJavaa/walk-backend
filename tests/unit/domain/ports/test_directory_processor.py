import pytest
from typing import List, Dict, Any, Optional
from abc import ABC
import os

from src.domain.ports.directory_processor import DirectoryProcessor


class TestDirectoryProcessor:
    """Test cases for the DirectoryProcessor port."""

    def test_directory_processor_interface(self):
        """Test that DirectoryProcessor defines the expected interface."""
        # Verify that DirectoryProcessor is an abstract base class
        assert issubclass(DirectoryProcessor, ABC)

        # Check that all required methods are defined
        required_methods = [
            "process_directory",
            "traverse_directory",
            "get_file_content",
            "is_file_supported",
        ]

        for method_name in required_methods:
            assert hasattr(DirectoryProcessor, method_name), \
                f"DirectoryProcessor should define '{method_name}' method"
            method = getattr(DirectoryProcessor, method_name)
            assert callable(method), f"'{method_name}' should be a method"

    def test_directory_processor_independency(self):
        """Test that DirectoryProcessor has no infrastructure dependencies."""
        import inspect

        # Get the source code of the interface
        source = inspect.getsource(DirectoryProcessor)

        # Check for infrastructure-related terms
        infrastructure_terms = [
            "mongodb",
            "mongo",
            "database",
            "sql",
            "openai",
            "http",
            "api"
        ]

        for term in infrastructure_terms:
            assert term.lower() not in source.lower(), \
                f"DirectoryProcessor should not reference '{term}'"

    def test_directory_processor_contract(self):
        """Test the contract that implementations of DirectoryProcessor must adhere to."""

        # A concrete implementation for testing
        class MockDirectoryProcessor(DirectoryProcessor):
            def __init__(self):
                self.files = {
                    "/test_dir/file1.py": "def test(): pass",
                    "/test_dir/file2.txt": "Hello, world!",
                    "/test_dir/subdir/file3.py": "class TestClass: pass",
                }
                self.directories = {
                    "/test_dir": ["/test_dir/file1.py", "/test_dir/file2.txt",
                                  "/test_dir/subdir"],
                    "/test_dir/subdir": ["/test_dir/subdir/file3.py"],
                }

            def process_directory(self, directory_path: str,
                                  max_depth: int = 10,
                                  container_id: Optional[str] = None,
                                  file_types: Optional[List[str]] = None) -> \
            Dict[str, Any]:
                """Process a directory and create context items."""
                if directory_path not in self.directories:
                    raise ValueError(f"Directory not found: {directory_path}")

                processed_files = []
                files = self.traverse_directory(directory_path, max_depth)

                # Filter by file type if specified
                if file_types:
                    files = [f for f in files if
                             any(f.endswith(ft) for ft in file_types)]

                for file_path in files:
                    if self.is_file_supported(file_path):
                        content = self.get_file_content(file_path)
                        processed_files.append({
                            "path": file_path,
                            "content": content,
                            "container_id": container_id
                        })

                return {
                    "directory": directory_path,
                    "container_id": container_id,
                    "processed_files": processed_files,
                    "total_files": len(processed_files)
                }

            def traverse_directory(self, directory_path: str,
                                   max_depth: int = 10) -> List[str]:
                """Traverse a directory recursively and return all file paths."""
                if max_depth <= 0:
                    return []

                if directory_path not in self.directories:
                    return []

                result = []
                for item in self.directories.get(directory_path, []):
                    if item in self.files:
                        # It's a file
                        result.append(item)
                    else:
                        # It's a directory
                        if max_depth > 1:
                            result.extend(
                                self.traverse_directory(item, max_depth - 1))

                return result

            def get_file_content(self, file_path: str) -> str:
                """Get the content of a file."""
                if file_path not in self.files:
                    raise FileNotFoundError(f"File not found: {file_path}")

                return self.files[file_path]

            def is_file_supported(self, file_path: str) -> bool:
                """Check if a file is supported for processing."""
                # In this mock, all files are supported
                return file_path in self.files

        # Create a mock processor for testing
        processor = MockDirectoryProcessor()

        # Test process_directory method
        result = processor.process_directory("/test_dir")
        assert result["directory"] == "/test_dir"
        assert result["total_files"] == 3
        assert len(result["processed_files"]) == 3

        # Test with container_id
        result = processor.process_directory("/test_dir",
                                             container_id="test-container")
        assert result["container_id"] == "test-container"

        # Test with file_types filter
        result = processor.process_directory("/test_dir", file_types=[".py"])
        assert result["total_files"] == 2
        assert all(f["path"].endswith(".py") for f in result["processed_files"])

        # Test max_depth parameter
        result = processor.process_directory("/test_dir", max_depth=1)
        assert result[
                   "total_files"] == 2  # Should not include file3.py in subdir

        # Test traverse_directory method
        files = processor.traverse_directory("/test_dir")
        assert len(files) == 3
        assert "/test_dir/file1.py" in files
        assert "/test_dir/subdir/file3.py" in files

        # Test with restricted depth
        files = processor.traverse_directory("/test_dir", max_depth=1)
        assert len(files) == 2
        assert "/test_dir/file1.py" in files
        assert "/test_dir/file2.txt" in files
        assert "/test_dir/subdir/file3.py" not in files

        # Test get_file_content method
        content = processor.get_file_content("/test_dir/file1.py")
        assert content == "def test(): pass"

        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            processor.get_file_content("/test_dir/nonexistent.py")

        # Test is_file_supported method
        assert processor.is_file_supported("/test_dir/file1.py") is True
        assert processor.is_file_supported("/test_dir/nonexistent.py") is False