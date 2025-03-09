from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from uuid import uuid4
import os
import re


class ContentType(str, Enum):
    """Enumeration of supported content types."""
    PYTHON = "python"
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"
    YAML = "yaml"
    HTML = "html"
    CSS = "css"
    JAVASCRIPT = "javascript"
    UNKNOWN = "unknown"

    @classmethod
    def from_file_extension(cls, file_path: str) -> "ContentType":
        """Determine content type from file extension."""
        extension = os.path.splitext(file_path)[1].lower()
        extension_map = {
            ".py": cls.PYTHON,
            ".md": cls.MARKDOWN,
            ".txt": cls.TEXT,
            ".json": cls.JSON,
            ".yaml": cls.YAML,
            ".yml": cls.YAML,
            ".html": cls.HTML,
            ".css": cls.CSS,
            ".js": cls.JAVASCRIPT,
        }
        return extension_map.get(extension, cls.UNKNOWN)


class ContextItemValidationError(Exception):
    """Exception raised for context item validation errors."""
    pass


class ContextItem:
    """
    Entity representing a unit of context.

    A context item can be a code file, documentation, or any other relevant information
    that the agent needs to generate code.
    """

    def __init__(
            self,
            id: str,
            source: str,
            content: str,
            content_type: ContentType,
            metadata: Optional[Dict[str, Any]] = None,
            embedding: Optional[List[float]] = None,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None,
    ):
        """
        Initialize a new ContextItem.

        Args:
            id: Unique identifier for the context item
            source: Source of the context (e.g., file path, URL)
            content: Actual content of the context item
            content_type: Type of content (e.g., Python, Markdown)
            metadata: Additional metadata about the context
            embedding: Vector embedding of the content for similarity search
            created_at: Creation timestamp
            updated_at: Last update timestamp

        Raises:
            ContextItemValidationError: If validation fails
        """
        self.validate_source(source)
        self.validate_content(content)
        self.validate_content_type(content_type)
        if embedding is not None:
            self.validate_embedding(embedding)

        self.id = id
        self.source = source
        self.content = content
        self.content_type = content_type
        self.metadata = metadata or {}
        self.embedding = embedding
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @staticmethod
    def validate_source(source: str) -> None:
        """Validate the source field."""
        if not source:
            raise ContextItemValidationError("Source cannot be empty")

    @staticmethod
    def validate_content(content: str) -> None:
        """Validate the content field."""
        if not content:
            raise ContextItemValidationError("Content cannot be empty")

    @staticmethod
    def validate_content_type(content_type: Any) -> None:
        """Validate the content_type field."""
        if not isinstance(content_type, ContentType):
            valid_types = [t.value for t in ContentType]
            raise ContextItemValidationError(
                f"Invalid content type. Expected one of: {valid_types}")

    @staticmethod
    def validate_embedding(embedding: List[float]) -> None:
        """Validate the embedding field."""
        if not isinstance(embedding, list):
            raise ContextItemValidationError(
                "Embedding must be a list of floats")

        if not all(isinstance(value, (int, float)) for value in embedding):
            raise ContextItemValidationError(
                "Embedding must be a list of floats")

    @classmethod
    def from_file_path(cls, file_path: str) -> "ContextItem":
        """
        Create a ContextItem from a file path.

        Args:
            file_path: Path to the file

        Returns:
            A new ContextItem instance

        Raises:
            FileNotFoundError: If the file does not exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        content_type = ContentType.from_file_extension(file_path)

        return cls.from_file_content(
            source=file_path,
            content=content,
            content_type=content_type,
        )

    @classmethod
    def from_file_content(cls, source: str, content: str,
                          content_type: ContentType) -> "ContextItem":
        """
        Create a ContextItem from file content.

        Args:
            source: Source of the content (e.g., file path)
            content: Content of the file
            content_type: Type of the content

        Returns:
            A new ContextItem instance
        """
        id = str(uuid4())
        metadata = cls._extract_metadata(content, content_type)

        return cls(
            id=id,
            source=source,
            content=content,
            content_type=content_type,
            metadata=metadata,
        )

    @staticmethod
    def _extract_metadata(content: str, content_type: ContentType) -> Dict[
        str, Any]:
        """
        Extract metadata from content.

        Args:
            content: Content to extract metadata from
            content_type: Type of the content

        Returns:
            Extracted metadata
        """
        metadata = {}

        # Extract metadata from comments based on content type
        if content_type == ContentType.PYTHON:
            # Extract Python comments (e.g., # Author: John Doe)
            comment_pattern = r"#\s*([A-Za-z_]+):\s*(.+)"
            for line in content.split("\n"):
                match = re.search(comment_pattern, line)
                if match:
                    key, value = match.groups()
                    metadata[key.lower()] = value.strip()

        elif content_type == ContentType.MARKDOWN:
            # Extract Markdown metadata from front matter
            front_matter_pattern = r"^---\s*\n(.*?)\n---"
            match = re.search(front_matter_pattern, content, re.DOTALL)
            if match:
                front_matter = match.group(1)
                for line in front_matter.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip().lower()] = value.strip()

        return metadata