from typing import List, Dict, Any, Tuple, Optional
from uuid import uuid4

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.ports.context_repository import ContextRepository
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.file_system import FileSystem


class AddContextUseCase:
    """Use case for adding context items to the system."""

    def __init__(
            self,
            context_repository: ContextRepository,
            llm_provider: LLMProvider,
            file_system: Optional[FileSystem] = None
    ):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing context items
            llm_provider: Provider for generating embeddings
            file_system: Optional file system for reading files
        """
        self.context_repository = context_repository
        self.llm_provider = llm_provider
        self.file_system = file_system

    def execute_from_file_path(self, file_path: str) -> ContextItem:
        """
        Add a context item from a file path.

        Args:
            file_path: Path to the file

        Returns:
            The added context item

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file type is not supported
        """
        if not self.file_system:
            raise ValueError("File system is required for this operation")

        if not self.file_system.file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        content = self.file_system.read_file(file_path)
        content_type = ContentType.from_file_extension(file_path)

        return self.execute_from_content(file_path, content, content_type)

    def execute_from_content(
            self,
            source: str,
            content: str,
            content_type: ContentType,
            metadata: Optional[Dict[str, Any]] = None
    ) -> ContextItem:
        """
        Add a context item from its content.

        Args:
            source: Source of the content (e.g., file path, identifier)
            content: The actual content
            content_type: Type of the content
            metadata: Optional metadata for the context item

        Returns:
            The added context item
        """
        # Create context item
        context_item = ContextItem(
            id=str(uuid4()),
            source=source,
            content=content,
            content_type=content_type,
            metadata=metadata or {}
        )

        # Generate embedding
        embedding = self.llm_provider.generate_embedding(content)
        context_item.embedding = embedding

        # Save to repository
        return self.context_repository.add(context_item)


class RemoveContextUseCase:
    """Use case for removing context items from the system."""

    def __init__(self, context_repository: ContextRepository):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing context items
        """
        self.context_repository = context_repository

    def execute(self, context_id: str) -> bool:
        """
        Remove a context item.

        Args:
            context_id: ID of the context item to remove

        Returns:
            True if the item was removed, False otherwise

        Raises:
            KeyError: If the context item does not exist
        """
        # Check if the item exists
        item = self.context_repository.get_by_id(context_id)
        if not item:
            raise KeyError(f"Context item with ID {context_id} not found")

        # Remove from repository
        return self.context_repository.delete(context_id)


class UpdateContextUseCase:
    """Use case for updating context items in the system."""

    def __init__(
            self,
            context_repository: ContextRepository,
            llm_provider: LLMProvider
    ):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing context items
            llm_provider: Provider for generating embeddings
        """
        self.context_repository = context_repository
        self.llm_provider = llm_provider

    def execute(
            self,
            context_id: str,
            content: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> ContextItem:
        """
        Update a context item.

        Args:
            context_id: ID of the context item to update
            content: New content (optional)
            metadata: New metadata (optional)

        Returns:
            The updated context item

        Raises:
            KeyError: If the context item does not exist
        """
        # Get the existing item
        item = self.context_repository.get_by_id(context_id)
        if not item:
            raise KeyError(f"Context item with ID {context_id} not found")

        # Update content if provided
        if content is not None:
            item.content = content
            # Generate new embedding
            item.embedding = self.llm_provider.generate_embedding(content)

        # Update metadata if provided
        if metadata is not None:
            item.metadata.update(metadata)

        # Save to repository
        return self.context_repository.update(item)


class ListContextUseCase:
    """Use case for listing context items in the system."""

    def __init__(self, context_repository: ContextRepository):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing context items
        """
        self.context_repository = context_repository

    def execute(self, filters: Optional[Dict[str, Any]] = None) -> List[
        ContextItem]:
        """
        List context items.

        Args:
            filters: Optional filters for the query

        Returns:
            List of context items matching the filters
        """
        return self.context_repository.list(filters)


class SearchContextUseCase:
    """Use case for searching context items in the system."""

    def __init__(
            self,
            context_repository: ContextRepository,
            llm_provider: LLMProvider
    ):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing context items
            llm_provider: Provider for generating embeddings
        """
        self.context_repository = context_repository
        self.llm_provider = llm_provider

    def execute(self, query: str, limit: int = 10) -> List[
        Tuple[ContextItem, float]]:
        """
        Search for context items based on a natural language query.

        Args:
            query: Natural language query
            limit: Maximum number of results to return

        Returns:
            List of tuples containing context items and their similarity scores
        """
        # Generate embedding for the query
        query_embedding = self.llm_provider.generate_embedding(query)

        # Search by vector similarity
        return self.context_repository.search_by_vector(query_embedding, limit)