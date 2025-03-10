import os
import fnmatch
import logging
from typing import List, Optional

from src.domain.ports.file_system import FileSystem


class FileSystemAdapter(FileSystem):
    """
    Implementation of the FileSystem port for local file system operations.

    This adapter provides methods to read, write, list, and delete files
    on the local file system.
    """

    def __init__(self):
        """Initialize the file system adapter."""
        self.logger = logging.getLogger(__name__)

    def read_file(self, path: str, binary: bool = False) -> str:
        """
        Read a file from the file system.

        Args:
            path: Path to the file to read
            binary: Whether to read in binary mode

        Returns:
            Contents of the file as a string or bytes

        Raises:
            FileNotFoundError: If the file does not exist
        """
        try:
            mode = "rb" if binary else "r"
            kwargs = {} if binary else {"encoding": "utf-8"}

            with open(path, mode, **kwargs) as file:
                return file.read()

        except FileNotFoundError:
            self.logger.error(f"File not found: {path}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading file {path}: {str(e)}")
            raise

    def write_file(self, path: str, content: str, binary: bool = False) -> bool:
        """
        Write content to a file in the file system.

        Args:
            path: Path where the file should be written
            content: Content to write to the file
            binary: Whether to write in binary mode

        Returns:
            True if the file was written successfully, False otherwise
        """
        try:
            # Ensure the directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            mode = "wb" if binary else "w"
            kwargs = {} if binary else {"encoding": "utf-8"}

            with open(path, mode, **kwargs) as file:
                file.write(content)

            return True

        except Exception as e:
            self.logger.error(f"Error writing to file {path}: {str(e)}")
            return False

    def list_files(self, directory: str, pattern: Optional[str] = None,
                   recursive: bool = False) -> List[str]:
        if not os.path.isdir(directory):
            self.logger.error(f"Directory not found: {directory}")
            raise ValueError(f"Directory not found: {directory}")

        try:
            result = []

            if recursive:
                # Walk through all subdirectories
                for root, _, files in os.walk(directory):
                    # Only add files to result, filtered by pattern if provided
                    for filename in files:
                        if pattern is None or fnmatch.fnmatch(filename,
                                                              pattern):
                            file_path = os.path.join(root, filename)
                            result.append(file_path)
            else:
                # Only list files in the specified directory
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)

                    # Only include files, not directories
                    if os.path.isfile(item_path) and (
                            pattern is None or fnmatch.fnmatch(item, pattern)):
                        result.append(item_path)

            return result

        except Exception as e:
            self.logger.error(f"Error listing files in {directory}: {str(e)}")
            raise

    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: Path to the file to check

        Returns:
            True if the file exists, False otherwise
        """
        return os.path.exists(path)

    def delete_file(self, path: str) -> bool:
        """
        Delete a file.

        Args:
            path: Path to the file to delete

        Returns:
            True if the file was deleted, False if it did not exist or could not be deleted
        """
        if not os.path.exists(path):
            return False

        try:
            os.remove(path)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting file {path}: {str(e)}")
            return False