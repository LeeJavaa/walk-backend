import os
import logging
from typing import List, Dict, Any, Tuple, Optional
from uuid import uuid4

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.container import Container
from src.domain.ports.context_repository import ContextRepository
from src.domain.ports.document_chunker import DocumentChunker
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.file_system import FileSystem
from src.domain.ports.directory_processor import DirectoryProcessor


class AddContextUseCase:
    """Use case for adding context items to the system."""

    def __init__(
            self,
            context_repository: ContextRepository,
            llm_provider: LLMProvider,
            file_system: Optional[FileSystem] = None,
            document_chunker: Optional[DocumentChunker] = None
    ):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing context items
            llm_provider: Provider for generating embeddings
            file_system: Optional file system for reading files
            document_chunker: Optional chunker for breaking down documents
        """
        self.context_repository = context_repository
        self.llm_provider = llm_provider
        self.file_system = file_system
        self.document_chunker = document_chunker
        self.logger = logging.getLogger(__name__)

    def execute_from_file_path(self, file_path: str,
                               container_id: Optional[str] = None,
                               is_container_root: bool = False,
                               enable_chunking: bool = True) -> ContextItem:
        """
        Add a context item from a file path.

        Args:
            file_path: Path to the file
            container_id: Optional ID of the container this item belongs to
            is_container_root: Whether this is a root item in the container
            enable_chunking: Whether to chunk the document if possible

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

        return self.execute_from_content(
            file_path,
            content,
            content_type,
            container_id=container_id,
            is_container_root=is_container_root,
            enable_chunking = enable_chunking
        )

    def execute_from_content(
            self,
            source: str,
            content: str,
            content_type: ContentType,
            metadata: Optional[Dict[str, Any]] = None,
            container_id: Optional[str] = None,
            is_container_root: bool = False,
            enable_chunking: bool = True
    ) -> ContextItem:
        """
        Add a context item from its content.

        Args:
            source: Source of the content (e.g., file path, identifier)
            content: The actual content
            content_type: Type of the content
            metadata: Optional metadata for the context item
            container_id: Optional ID of the container this item belongs to
            is_container_root: Whether this is a root item in the container
            enable_chunking: Whether to chunk the document if possible

        Returns:
            The added context item
        """
        # Create context item
        context_item = ContextItem(
            id=str(uuid4()),
            source=source,
            content=content,
            content_type=content_type,
            metadata=metadata or {},
            container_id=container_id,
            is_container_root=is_container_root
        )

        # Generate embedding
        embedding = self.llm_provider.generate_embedding(content)
        context_item.embedding = embedding

        # Save to repository
        saved_item = self.context_repository.add(context_item)

        # Perform chunking if relevant and enabled
        chunks_count = 0
        if self.document_chunker and enable_chunking and is_container_root:
            try:
                # Chunk the document
                chunks = self.document_chunker.chunk_document(saved_item)

                # Save all chunks to the repository
                for chunk in chunks:
                    self.context_repository.add(chunk)

                chunks_count = len(chunks)
                self.logger.info(f"Added {chunks_count} chunks for {source}")
            except Exception as e:
                self.logger.warning(
                    f"Failed to chunk document {source}: {str(e)}")
                # Continue execution even if chunking fails

        # Attach chunks count as metadata for the caller
        saved_item.metadata["chunks_count"] = chunks_count

        return saved_item


class AddDirectoryUseCase:
    """Use case for adding an entire directory to the context system."""

    def __init__(
            self,
            context_repository: ContextRepository,
            llm_provider: LLMProvider,
            directory_processor: DirectoryProcessor,
            document_chunker: Optional[DocumentChunker] = None
    ):
        """
        Initialize the use case.

        Args:
            context_repository: Repository for storing context items
            llm_provider: Provider for generating embeddings
            directory_processor: Processor for directory traversal and file handling
            document_chunker: Optional chunker for breaking down documents
        """
        self.context_repository = context_repository
        self.llm_provider = llm_provider
        self.directory_processor = directory_processor
        self.document_chunker = document_chunker
        self.logger = logging.getLogger(__name__)

    def execute(
            self,
            directory_path: str,
            max_depth: int = 10,
            file_types: Optional[List[str]] = None,
            container_id: Optional[str] = None,
            container_title: Optional[str] = None,
            container_type: str = "code",
            container_description: str = "",
            container_priority: int = 5,
            enable_chunking: bool = True
    ) -> Dict[str, Any]:
        """
        Add an entire directory to the context system.

        Args:
            directory_path: Path to the directory
            max_depth: Maximum recursion depth (default: 10)
            file_types: Optional list of file extensions to include (e.g., [".py", ".md"])
            container_id: Optional ID of an existing container to add files to
            container_title: Optional title for a new container
            container_type: Type of container (default: "code")
            container_description: Description of the container
            container_priority: Priority level for the container (1-10)
            enable_chunking: Whether to chunk the documents if possible

        Returns:
            Dictionary with processing results:
            - container: The container where files were added
            - context_items: List of added context items
            - total_files: Number of files processed
            - total_chunks: Number of chunks created

        Raises:
            ValueError: If the directory path is invalid
            KeyError: If the specified container doesn't exist
        """
        # Get or create container
        container = self._get_or_create_container(
            directory_path,
            container_id,
            container_title,
            container_type,
            container_description,
            container_priority
        )

        # Process the directory
        self.logger.info(
            f"Processing directory: {directory_path} (max depth: {max_depth})")
        processing_result = self.directory_processor.process_directory(
            directory_path,
            max_depth=max_depth,
            container_id=container.id,
            file_types=file_types
        )

        # Create context items from the processed files
        context_items = []
        total_chunks = 0

        for file_info in processing_result["processed_files"]:
            file_path = file_info["path"]
            content = file_info["content"]
            content_type = ContentType.from_file_extension(file_path)

            # Create and add context item
            context_item = ContextItem(
                id=str(uuid4()),
                source=file_path,
                content=content,
                content_type=content_type,
                metadata=self._extract_metadata(file_path, content,
                                                content_type),
                container_id=container.id,
                is_container_root=True
                # Files added directly are container roots
            )

            # Generate embedding
            try:
                embedding = self.llm_provider.generate_embedding(content)
                context_item.embedding = embedding
            except Exception as e:
                self.logger.warning(
                    f"Failed to generate embedding for {file_path}: {str(e)}")

            # Add the parent context item to repository
            added_item = self.context_repository.add(context_item)
            context_items.append(added_item)

            # Perform chunking if enabled
            file_chunks_count = 0
            if self.document_chunker and enable_chunking:
                try:
                    # Chunk the document
                    chunks = self.document_chunker.chunk_document(added_item)

                    # Save all chunks to the repository
                    for chunk in chunks:
                        self.context_repository.add(chunk)

                    file_chunks_count = len(chunks)
                    total_chunks += file_chunks_count

                    # Add chunks count to item metadata
                    added_item.metadata["chunks_count"] = file_chunks_count
                    # Update the item in the repository with the new metadata
                    self.context_repository.update(added_item)

                    self.logger.info(
                        f"Added {file_chunks_count} chunks for {file_path}")
                except Exception as e:
                    self.logger.warning(
                        f"Failed to chunk document {file_path}: {str(e)}")
                    # Continue processing other files even if chunking fails for one

        self.logger.info(
            f"Added {len(context_items)} files and {total_chunks} chunks from {directory_path} to container {container.id}")

        # Return processing results
        return {
            "container": container,
            "context_items": context_items,
            "total_files": len(context_items),
            "total_chunks": total_chunks
        }


    def _get_or_create_container(
            self,
            directory_path: str,
            container_id: Optional[str] = None,
            container_title: Optional[str] = None,
            container_type: str = "code",
            container_description: str = "",
            container_priority: int = 5
    ) -> Container:
        """
        Get an existing container or create a new one.

        Args:
            directory_path: Path to the directory
            container_id: Optional ID of an existing container
            container_title: Optional title for a new container
            container_type: Type of container
            container_description: Description of the container
            container_priority: Priority level for the container

        Returns:
            The container to use

        Raises:
            KeyError: If the specified container doesn't exist
        """
        # If container_id is provided, use existing container
        if container_id:
            container = self.context_repository.get_container(container_id)
            if container is None:
                raise KeyError(f"Container not found: {container_id}")
            return container

        # Create a new container
        # Generate container name from directory path
        directory_name = os.path.basename(os.path.normpath(directory_path))
        container_name = directory_name.lower().replace(" ", "-")

        # Use provided title or generate from directory name
        title = container_title or directory_name

        # Create and add the container
        container = Container(
            id=str(uuid4()),
            name=container_name,
            title=title,
            container_type=container_type,
            source_path=directory_path,
            description=container_description,
            priority=container_priority
        )

        return self.context_repository.add_container(container)

    def _extract_metadata(self, file_path: str, content: str,
                          content_type: ContentType) -> Dict[str, Any]:
        """
        Extract metadata from file path and content.

        Args:
            file_path: Path to the file
            content: Content of the file
            content_type: Type of the content

        Returns:
            Extracted metadata
        """
        # Extract basic file information
        metadata = {
            "filename": os.path.basename(file_path),
            "directory": os.path.dirname(file_path),
            "extension": os.path.splitext(file_path)[1],
            "size_bytes": len(content.encode('utf-8')),
            "line_count": content.count('\n') + 1
        }

        # Add file type specific metadata using ContextItem's built-in method
        file_specific_metadata = ContextItem._extract_metadata(content,
                                                               content_type)
        metadata.update(file_specific_metadata)

        return metadata


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
            filters: Optional filters for the query, can include 'container_id' to filter by container

        Returns:
            List of context items matching the filters
        """
        return self.context_repository.list(filters)

    def execute_list_by_container(self, container_id: str) -> List[ContextItem]:
        """
        List all context items that belong to a specific container.

        Args:
            container_id: ID of the container to list items from

        Returns:
            List of context items in the specified container
        """
        return self.context_repository.list_by_container(container_id)


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