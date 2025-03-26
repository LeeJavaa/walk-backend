from typing import List

from src.domain.entities.context_item import ContextItem
from src.domain.ports.document_chunker import DocumentChunker
from src.application.services.chunking_service import ChunkingService


class ChunkingServiceAdapter(DocumentChunker):
    """
    Adapter that implements the DocumentChunker port using the ChunkingService.

    This adapter bridges the domain layer with the application's chunking service.
    """

    def __init__(self, chunking_service: ChunkingService):
        """
        Initialize the adapter with a chunking service.

        Args:
            chunking_service: The chunking service to use
        """
        self.chunking_service = chunking_service

    def chunk_document(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk a document using the chunking service.

        Args:
            document: The document to chunk

        Returns:
            List of context items representing chunks of the document
        """
        return self.chunking_service.chunk_document(document)