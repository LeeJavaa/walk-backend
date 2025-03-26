from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.context_item import ContextItem


class DocumentChunker(ABC):
    """
    Port interface for document chunking operations.

    This interface abstracts the chunking mechanism, allowing the domain to remain
    independent of specific chunking implementations.
    """

    @abstractmethod
    def chunk_document(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk a document into smaller, semantically meaningful units.

        Args:
            document: The document to chunk

        Returns:
            List of context items representing chunks of the document
        """
        pass