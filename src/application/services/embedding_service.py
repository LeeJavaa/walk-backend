"""
Service for generating and managing embeddings for text and context items.
"""
import logging
from typing import List, Dict, Any, Optional

from src.domain.entities.context_item import ContextItem
from src.domain.ports.llm_provider import LLMProvider


class EmbeddingService:
    """
    Service for generating vector embeddings for text and context items.

    This service provides methods to generate embeddings for text strings and
    for ContextItem entities, handling chunking for large texts if needed.
    """

    # Maximum text length to send in a single embedding request
    # This is a conservative limit to avoid token limits
    MAX_TEXT_LENGTH = 8000

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the embedding service.

        Args:
            llm_provider: LLM provider for generating embeddings
        """
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(__name__)

    def generate_embedding_for_text(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text.

        Args:
            text: Text to generate embedding for

        Returns:
            Vector embedding as a list of floats
        """
        if not text:
            self.logger.warning("Empty text provided for embedding generation")
            return []

        # Handle large texts by chunking if needed
        if len(text) > self.MAX_TEXT_LENGTH:
            return self._handle_large_text(text)

        try:
            return self.llm_provider.generate_embedding(text)
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            raise

    def generate_embedding_for_context_item(self,
                                            context_item: ContextItem) -> ContextItem:
        """
        Generate an embedding for a context item.

        Args:
            context_item: Context item to generate embedding for

        Returns:
            The same context item with embedding added
        """
        if not context_item.content:
            self.logger.warning(
                f"Empty content in context item {context_item.id}")
            context_item.embedding = []
            return context_item

        try:
            context_item.embedding = self.generate_embedding_for_text(
                context_item.content)
            return context_item
        except Exception as e:
            self.logger.error(
                f"Error generating embedding for context item {context_item.id}: {str(e)}")
            raise

    def generate_embeddings_for_context_items(self, context_items: List[
        ContextItem]) -> List[ContextItem]:
        """
        Generate embeddings for multiple context items.

        Args:
            context_items: List of context items to generate embeddings for

        Returns:
            The same context items with embeddings added
        """
        result = []
        for item in context_items:
            try:
                item_with_embedding = self.generate_embedding_for_context_item(
                    item)
                result.append(item_with_embedding)
            except Exception as e:
                self.logger.error(
                    f"Error processing context item {item.id}: {str(e)}")
                # Add the item without embedding rather than skipping it entirely
                result.append(item)

        return result

    def _handle_large_text(self, text: str) -> List[float]:
        """
        Handle large text by chunking and combining embeddings.

        For simplicity, this implementation just uses the first chunk.
        A more sophisticated approach would be to split the text semantically
        and combine the embeddings in a meaningful way.

        Args:
            text: Large text to generate embedding for

        Returns:
            Vector embedding as a list of floats
        """
        self.logger.info(
            f"Text length {len(text)} exceeds limit, using chunking strategy")

        # Simple chunking: just use the first MAX_TEXT_LENGTH characters
        # This is a simplification - a better approach would use semantic chunking
        chunk = text[:self.MAX_TEXT_LENGTH]

        try:
            return self.llm_provider.generate_embedding(chunk)
        except Exception as e:
            self.logger.error(
                f"Error generating embedding for chunked text: {str(e)}")
            raise