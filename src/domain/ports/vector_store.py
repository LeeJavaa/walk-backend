from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional


class VectorStore(ABC):
    """
    Port interface for vector storage and similarity search.

    This interface abstracts vector database interactions, allowing
    the domain to remain independent of specific vector database implementations.
    """

    @abstractmethod
    def add_vector(self, id: str, vector: List[float],
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a vector to the store.

        Args:
            id: Unique identifier for the vector
            vector: The vector to store
            metadata: Optional metadata to associate with the vector

        Returns:
            True if the vector was added successfully, False otherwise
        """
        pass

    @abstractmethod
    def update_vector(self, id: str, vector: List[float],
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing vector in the store.

        Args:
            id: Unique identifier for the vector to update
            vector: The new vector
            metadata: Optional new metadata

        Returns:
            True if the vector was updated successfully, False if not found
        """
        pass

    @abstractmethod
    def delete_vector(self, id: str) -> bool:
        """
        Delete a vector from the store.

        Args:
            id: Unique identifier for the vector to delete

        Returns:
            True if the vector was deleted, False if not found
        """
        pass

    @abstractmethod
    def search_vectors(self, query_vector: List[float], limit: int = 10) -> \
    List[Tuple[str, float, Optional[Dict[str, Any]]]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Vector to search for
            limit: Maximum number of results to return

        Returns:
            List of tuples of (id, similarity_score, metadata)
            sorted by similarity_score in descending order
        """
        pass