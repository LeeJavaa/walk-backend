from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional

from src.domain.entities.context_item import ContextItem


class ContextRepository(ABC):
    """
    Port interface for context item storage and retrieval.

    This interface abstracts the persistence mechanism for context items,
    allowing the domain to remain independent of specific storage technologies.
    """

    @abstractmethod
    def add(self, context_item: ContextItem) -> ContextItem:
        """
        Add a new context item to the repository.

        Args:
            context_item: The context item to add

        Returns:
            The added context item, potentially with updated metadata
        """
        pass

    @abstractmethod
    def get_by_id(self, context_id: str) -> Optional[ContextItem]:
        """
        Retrieve a context item by its ID.

        Args:
            context_id: ID of the context item to retrieve

        Returns:
            The retrieved context item, or None if not found
        """
        pass

    @abstractmethod
    def update(self, context_item: ContextItem) -> ContextItem:
        """
        Update an existing context item.

        Args:
            context_item: The context item with updated data

        Returns:
            The updated context item

        Raises:
            KeyError: If the context item does not exist
        """
        pass

    @abstractmethod
    def delete(self, context_id: str) -> bool:
        """
        Delete a context item by its ID.

        Args:
            context_id: ID of the context item to delete

        Returns:
            True if the item was deleted, False if not found
        """
        pass

    @abstractmethod
    def list(self, filters: Dict[str, Any] = None) -> List[ContextItem]:
        """
        List context items, optionally filtered.

        Args:
            filters: Optional dictionary of attribute-value pairs to filter by

        Returns:
            List of context items matching the filters
        """
        pass

    @abstractmethod
    def search_by_vector(self, query_vector: List[float], limit: int = 10) -> \
    List[Tuple[ContextItem, float]]:
        """
        Search for context items by vector similarity.

        Args:
            query_vector: Vector to search for
            limit: Maximum number of results to return

        Returns:
            List of tuples of (context_item, similarity_score)
        """
        pass