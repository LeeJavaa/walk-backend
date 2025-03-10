"""
Retrieval Augmented Generation (RAG) service for enhancing LLM responses with context.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple

from src.domain.entities.context_item import ContextItem
from src.domain.ports.context_repository import ContextRepository
from src.domain.ports.llm_provider import LLMProvider
from src.application.services.embedding_service import EmbeddingService
from src.infrastructure.adapters.prompt_utils import \
    format_context_items_for_prompt


class RAGService:
    """
    Retrieval Augmented Generation (RAG) service.

    This service retrieves relevant context from the repository based on semantic
    similarity and uses it to enhance LLM responses.
    """

    def __init__(
            self,
            context_repository: ContextRepository,
            llm_provider: LLMProvider,
            embedding_service: EmbeddingService,
            similarity_threshold: float = 0.7,
            max_context_items: int = 10
    ):
        """
        Initialize the RAG service.

        Args:
            context_repository: Repository for retrieving context items
            llm_provider: LLM provider for generating text
            embedding_service: Service for generating embeddings
            similarity_threshold: Minimum similarity score for context items
            max_context_items: Maximum number of context items to include
        """
        self.context_repository = context_repository
        self.llm_provider = llm_provider
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.max_context_items = max_context_items
        self.logger = logging.getLogger(__name__)

    def retrieve_context(self, query: str) -> List[ContextItem]:
        """
        Retrieve relevant context items for a query.

        Args:
            query: The query to find relevant context for

        Returns:
            List of relevant context items
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_service.generate_embedding_for_text(
                query)

            # Search for similar context items
            results = self.context_repository.search_by_vector(
                query_embedding,
                limit=self.max_context_items
            )

            # Filter results by similarity threshold and extract just the items
            context_items = [
                item for item, score in results
                if score >= self.similarity_threshold
            ]

            self.logger.info(
                f"Retrieved {len(context_items)} relevant context items for query")
            return context_items

        except Exception as e:
            self.logger.error(f"Error retrieving context: {str(e)}")
            return []

    def generate_with_context(
            self,
            query: str,
            context_items: Optional[List[ContextItem]] = None,
            options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a response with relevant context.

        Args:
            query: The query to respond to
            context_items: Optional pre-retrieved context items
            options: Optional parameters for text generation

        Returns:
            Generated response with context
        """
        try:
            # Retrieve context if not provided
            if context_items is None:
                context_items = self.retrieve_context(query)

            # Format context items for the prompt
            formatted_context = self._format_context_items(context_items)

            # Construct prompt with context
            prompt = self._construct_prompt_with_context(query,
                                                         formatted_context)

            # Generate response
            response = self.llm_provider.generate_text(prompt, options)

            return response

        except Exception as e:
            self.logger.error(f"Error generating with context: {str(e)}")
            raise

    def retrieve_and_format_context(self, query: str) -> str:
        """
        Retrieve and format context for a query.

        Args:
            query: The query to find relevant context for

        Returns:
            Formatted context string
        """
        context_items = self.retrieve_context(query)
        return self._format_context_items(context_items)

    def _format_context_items(self, context_items: List[ContextItem]) -> str:
        """
        Format context items for inclusion in a prompt.

        Args:
            context_items: List of context items

        Returns:
            Formatted context string
        """
        context_data = [
            {"content": item.content, "source": item.source}
            for item in context_items
        ]
        return format_context_items_for_prompt(context_data)

    def _construct_prompt_with_context(self, query: str, context: str) -> str:
        """
        Construct a prompt that includes the context.

        Args:
            query: The original query
            context: Formatted context string

        Returns:
            Prompt with context
        """
        if not context:
            return query

        prompt = f"""
Please answer the following question based on the provided context information.
If the context doesn't contain relevant information, use your general knowledge
but prioritize the context when applicable.

CONTEXT INFORMATION:
{context}

QUESTION:
{query}

ANSWER:
"""
        return prompt