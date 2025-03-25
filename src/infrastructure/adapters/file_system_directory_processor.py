import os
import fnmatch
import logging
from typing import List, Dict, Any, Optional

from src.domain.ports.directory_processor import DirectoryProcessor
from src.domain.ports.file_system import FileSystem


class FileSystemDirectoryProcessor(DirectoryProcessor):
    """
    Implementation of the DirectoryProcessor interface for the local file system.

    This class provides methods to traverse directories, collect files,
    and process file content.
    """

    # List of supported file extensions
    SUPPORTED_EXTENSIONS = [
        ".py", ".md", ".txt", ".json", ".yaml", ".yml",
        ".html", ".css", ".js", ".jsx", ".ts", ".tsx",
        ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rs",
        ".rb", ".php", ".sh", ".bat", ".ps1", ".sql"
    ]

    # List of extensions to explicitly exclude
    EXCLUDED_EXTENSIONS = [
        # Binary files
        ".exe", ".dll", ".so", ".dylib", ".bin", ".obj",
        # Image files
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".svg",
        # Audio/video files
        ".mp3", ".mp4", ".wav", ".avi", ".mov", ".flac",
        # Archive files
        ".zip", ".tar", ".gz", ".rar", ".7z",
        # Other binary formats
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"
    ]

    def __init__(self, file_system: FileSystem):
        """
        Initialize the FileSystemDirectoryProcessor.

        Args:
            file_system: FileSystem implementation to use for file operations
        """
        self.file_system = file_system
        self.logger = logging.getLogger(__name__)

    def process_directory(self, directory_path: str, max_depth: int = 10,
                          container_id: Optional[str] = None,
                          file_types: Optional[List[str]] = None) -> Dict[
        str, Any]:
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
        # Validate the directory path
        if not self.file_system.file_exists(directory_path):
            raise ValueError(f"Directory not found: {directory_path}")

        if not os.path.isdir(directory_path):
            raise ValueError(f"Not a directory: {directory_path}")

        self.logger.info(
            f"Processing directory: {directory_path} (max depth: {max_depth})")

        # Get all file paths in the directory up to max_depth
        file_paths = self.traverse_directory(directory_path, max_depth)

        # Filter by file type if specified
        if file_types:
            self.logger.info(f"Filtering by file types: {file_types}")
            file_paths = [path for path in file_paths if
                          any(path.endswith(ext) for ext in file_types)]

        # Process each file
        processed_files = []
        for file_path in file_paths:
            if self.is_file_supported(file_path):
                try:
                    # Get file content
                    content = self.get_file_content(file_path)

                    # Create file info
                    file_info = {
                        "path": file_path,
                        "content": content,
                        "container_id": container_id
                    }

                    processed_files.append(file_info)
                    self.logger.debug(f"Processed file: {file_path}")
                except Exception as e:
                    self.logger.error(
                        f"Error processing file {file_path}: {str(e)}")
            else:
                self.logger.debug(f"Skipping unsupported file: {file_path}")

        # Return processing results
        return {
            "directory": directory_path,
            "container_id": container_id,
            "processed_files": processed_files,
            "total_files": len(processed_files)
        }

    def traverse_directory(self, directory_path: str, max_depth: int = 10) -> \
    List[str]:
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
        if max_depth <= 0:
            return []

        result = []

        try:
            # List all files and directories at the current level
            items = self.file_system.list_files(directory_path, recursive=False)

            for item in items:
                # Check if item is a directory
                if os.path.isdir(item):
                    # If we still have depth, recurse into the directory
                    if max_depth > 1:
                        subdirectory_files = self.traverse_directory(item,
                                                                     max_depth - 1)
                        result.extend(subdirectory_files)
                else:
                    # It's a file, add it to our results
                    result.append(item)

            return result

        except Exception as e:
            self.logger.error(
                f"Error traversing directory {directory_path}: {str(e)}")
            raise ValueError(f"Failed to traverse directory: {str(e)}")

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
        try:
            return self.file_system.read_file(file_path)
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {str(e)}")
            raise

    def is_file_supported(self, file_path: str) -> bool:
        """
        Check if a file is supported for processing.

        Args:
            file_path: Path to the file

        Returns:
            True if the file is supported, False otherwise
        """
        # Extract file extension
        _, extension = os.path.splitext(file_path.lower())

        # Check if extension is in excluded list
        if extension in self.EXCLUDED_EXTENSIONS:
            return False

        # Either it's in the supported list or we have an allow-all policy
        if not self.SUPPORTED_EXTENSIONS:  # Empty list means accept all except excluded
            return True

        return extension in self.SUPPORTED_EXTENSIONS