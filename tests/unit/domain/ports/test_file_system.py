import pytest
from abc import ABC
from typing import List, Optional

from src.domain.ports.file_system import FileSystem


class TestFileSystem:
    """Test cases for the FileSystem port."""

    def test_file_system_interface(self):
        """Test that FileSystem defines the expected interface (U-HA-3)."""
        # Verify that FileSystem is an abstract base class
        assert issubclass(FileSystem, ABC)

        # Check that all required methods are defined
        required_methods = [
            "read_file",
            "write_file",
            "list_files",
            "file_exists",
            "delete_file",
        ]

        for method_name in required_methods:
            assert hasattr(FileSystem,
                           method_name), f"FileSystem should define '{method_name}' method"
            method = getattr(FileSystem, method_name)
            assert callable(method), f"'{method_name}' should be a method"

    def test_file_system_independency(self):
        """Test that FileSystem has no infrastructure dependencies (U-HA-2)."""
        import inspect

        # Get the source code of the interface
        source = inspect.getsource(FileSystem)

        # Check for implementation-related terms
        implementation_terms = [
            "os.path",
            "pathlib",
            "io.",
            "open(",
            "shutil",
        ]

        for term in implementation_terms:
            assert term.lower() not in source.lower(), f"FileSystem should not reference '{term}'"

    def test_file_system_contract(self):
        """Test the contract that implementations of FileSystem must adhere to."""

        # A concrete implementation for testing
        class MockFileSystem(FileSystem):
            def __init__(self):
                self.files = {}

            def read_file(self, path: str) -> str:
                if path not in self.files:
                    raise FileNotFoundError(f"File not found: {path}")
                return self.files[path]

            def write_file(self, path: str, content: str) -> bool:
                self.files[path] = content
                return True

            def list_files(self, directory: str,
                           pattern: Optional[str] = None) -> List[str]:
                # Simplified implementation for testing
                if not pattern:
                    return list(self.files.keys())

                import re
                pattern_regex = re.compile(pattern.replace("*", ".*"))
                return [path for path in self.files.keys() if
                        pattern_regex.match(path)]

            def file_exists(self, path: str) -> bool:
                return path in self.files

            def delete_file(self, path: str) -> bool:
                if path not in self.files:
                    return False
                del self.files[path]
                return True

        # Create a mock file system for testing
        fs = MockFileSystem()

        # Test write_file method
        test_path = "/test/file.py"
        test_content = "print('Hello, World!')"
        assert fs.write_file(test_path, test_content) is True

        # Test file_exists method
        assert fs.file_exists(test_path) is True
        assert fs.file_exists("/nonexistent/file.py") is False

        # Test read_file method
        assert fs.read_file(test_path) == test_content
        with pytest.raises(FileNotFoundError):
            fs.read_file("/nonexistent/file.py")

        # Test list_files method
        fs.write_file("/test/file2.py", "# Another file")
        fs.write_file("/test/data.json", "{}")

        all_files = fs.list_files("/test")
        assert len(all_files) == 3
        assert test_path in all_files

        python_files = fs.list_files("/test", "*.py")
        assert len(python_files) == 2
        assert all(file.endswith(".py") for file in python_files)

        # Test delete_file method
        assert fs.delete_file(test_path) is True
        assert fs.file_exists(test_path) is False
        assert fs.delete_file("/nonexistent/file.py") is False