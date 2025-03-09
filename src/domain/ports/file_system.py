from abc import ABC, abstractmethod
from typing import List, Optional


class FileSystem(ABC):
    """
    Port interface for file system operations.

    This interface abstracts file system interactions, allowing
    the domain to remain independent of specific file system implementations.
    """

    @abstractmethod
    def read_file(self, path: str) -> str:
        """
        Read a file from the file system.

        Args:
            path: Path to the file to read

        Returns:
            Contents of the file as a string

        Raises:
            FileNotFoundError: If the file does not exist
        """
        pass

    @abstractmethod
    def write_file(self, path: str, content: str) -> bool:
        """
        Write content to a file in the file system.

        Args:
            path: Path where the file should be written
            content: Content to write to the file

        Returns:
            True if the file was written successfully, False otherwise
        """
        pass

    @abstractmethod
    def list_files(self, directory: str, pattern: Optional[str] = None) -> List[
        str]:
        """
        List files in a directory, optionally filtered by a pattern.

        Args:
            directory: Directory to list files from
            pattern: Optional glob pattern to filter files by (e.g., "*.py")

        Returns:
            List of file paths matching the criteria
        """
        pass

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: Path to the file to check

        Returns:
            True if the file exists, False otherwise
        """
        pass

    @abstractmethod
    def delete_file(self, path: str) -> bool:
        """
        Delete a file.

        Args:
            path: Path to the file to delete

        Returns:
            True if the file was deleted, False if it did not exist
        """
        pass