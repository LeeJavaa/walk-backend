from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class DirectoryProcessor(ABC):
    """
    Port interface for directory processing and traversal.

    This interface abstracts the directory processing mechanism,
    allowing the domain to remain independent of specific file system implementations.
    It provides methods for traversing directories, processing files, and creating
    context items from file content.
    """

    @abstractmethod
    def process_directory(self, directory_path: str, max_depth: int = 10,
                         container_id: Optional[str] = None,
                         file_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process a directory and create context items.

        Args:
            directory_path: Path to the directory to process
            max_depth: Maximum depth for directory traversal (default: 10)
            container_id: ID of the container to associate context items with (optional)
            file_types: List of file extensions to include (optional)

        Returns:
            Dictionary with processing results, including:
            - directory: The processed directory path
            - container_id: ID of the container (if provided)
            - processed_files: List of processed file information
            - total_files: Number of files processed

        Raises:
            ValueError: If the directory path is invalid
        """
        pass

    @abstractmethod
    def traverse_directory(self, directory_path: str, max_depth: int = 10) -> List[str]:
        """
        Traverse a directory recursively and return all file paths.

        Args:
            directory_path: Path to the directory to traverse
            max_depth: Maximum depth for recursion (default: 10)

        Returns:
            List of file paths found in the directory and its subdirectories

        Raises:
            ValueError: If the directory path is invalid
        """
        pass

    @abstractmethod
    def get_file_content(self, file_path: str) -> str:
        """
        Get the content of a file.

        Args:
            file_path: Path to the file

        Returns:
            Content of the file as a string

        Raises:
            FileNotFoundError: If the file does not exist
        """
        pass

    @abstractmethod
    def is_file_supported(self, file_path: str) -> bool:
        """
        Check if a file is supported for processing.

        Args:
            file_path: Path to the file

        Returns:
            True if the file is supported, False otherwise
        """
        pass