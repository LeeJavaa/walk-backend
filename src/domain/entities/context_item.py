from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
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
    that the agent needs to generate code. With the enhanced system, context items
    can be associated with containers and can have parent-child relationships for chunking.
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
            container_id: Optional[str] = None,
            is_container_root: bool = False,
            parent_id: Optional[str] = None,
            is_chunk: bool = False,
            chunk_type: Optional[str] = None,
            chunk_metadata: Optional[Dict[str, Any]] = None
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
            container_id: ID of the container this item belongs to (optional)
            is_container_root: Whether this is a root item in the container (e.g., a file)
            parent_id: ID of the parent context item (for chunks)
            is_chunk: Whether this item is a chunk of a larger item
            chunk_type: Type of chunk (e.g., class, function, method, section)
            chunk_metadata: Additional metadata about the chunk

        Raises:
            ContextItemValidationError: If validation fails
        """
        self.validate_source(source)
        self.validate_content(content)
        self.validate_content_type(content_type)
        if embedding is not None:
            self.validate_embedding(embedding)

        # Validate chunk-related properties
        self.validate_chunk_properties(is_chunk, parent_id, chunk_type)

        self.id = id
        self.source = source
        self.content = content
        self.content_type = content_type
        self.metadata = metadata or {}
        self.embedding = embedding
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

        # Container relationship
        self.container_id = container_id
        self.is_container_root = is_container_root

        # Chunking properties
        self.parent_id = parent_id
        self.is_chunk = is_chunk
        self.chunk_type = chunk_type if is_chunk else None
        self.chunk_metadata = chunk_metadata or {}

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

    @staticmethod
    def validate_chunk_properties(is_chunk: bool, parent_id: Optional[str],
                                  chunk_type: Optional[str]) -> None:
        """Validate chunk-related properties."""
        if is_chunk and not parent_id:
            raise ContextItemValidationError(
                "Chunk items must have a parent_id")

        if not is_chunk and chunk_type is not None:
            raise ContextItemValidationError(
                "Only chunk items can have chunk_type")

    def extract_chunk_path_components(self) -> Tuple[str, str]:
        """
        Extract the parent path and chunk identifier from the source path.

        For a source like "file.py:Class.method", extracts "file.py" and "Class.method".

        Returns:
            A tuple of (parent_path, chunk_name)
        """
        if ":" not in self.source:
            return self.source, ""

        parts = self.source.split(":", 1)
        return parts[0], parts[1]

    @classmethod
    def from_file_path(cls, file_path: str,
                       container_id: Optional[str] = None) -> "ContextItem":
        """
        Create a ContextItem from a file path.

        Args:
            file_path: Path to the file
            container_id: ID of the container (optional)

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
            container_id=container_id,
            is_container_root=True  # Files added directly are container roots
        )

    @classmethod
    def from_file_content(cls, source: str, content: str,
                          content_type: ContentType,
                          container_id: Optional[str] = None,
                          is_container_root: bool = False) -> "ContextItem":
        """
        Create a ContextItem from file content.

        Args:
            source: Source of the content (e.g., file path)
            content: Content of the file
            content_type: Type of the content
            container_id: ID of the container (optional)
            is_container_root: Whether this is a root item in the container

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
            container_id=container_id,
            is_container_root=is_container_root
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

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the context item to a dictionary for serialization.

        Returns:
            Dictionary representation of the context item
        """
        return {
            "id": self.id,
            "source": self.source,
            "content": self.content,
            "content_type": self.content_type.value,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "container_id": self.container_id,
            "is_container_root": self.is_container_root,
            "parent_id": self.parent_id,
            "is_chunk": self.is_chunk,
            "chunk_type": self.chunk_type,
            "chunk_metadata": self.chunk_metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextItem":
        """
        Create a context item from a dictionary.

        Args:
            data: Dictionary with context item data

        Returns:
            ContextItem instance
        """
        # Convert content_type string to enum
        content_type = ContentType(data["content_type"]) if isinstance(
            data["content_type"], str) else data["content_type"]

        return cls(
            id=data["id"],
            source=data["source"],
            content=data["content"],
            content_type=content_type,
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            container_id=data.get("container_id"),
            is_container_root=data.get("is_container_root", False),
            parent_id=data.get("parent_id"),
            is_chunk=data.get("is_chunk", False),
            chunk_type=data.get("chunk_type"),
            chunk_metadata=data.get("chunk_metadata", {})
        )