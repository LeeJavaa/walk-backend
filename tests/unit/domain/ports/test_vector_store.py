import pytest
from abc import ABC
from typing import Dict, Any, List, Tuple, Optional

from src.domain.ports.vector_store import VectorStore


class TestVectorStore:
    """Test cases for the VectorStore port."""

    def test_vector_store_interface(self):
        """Test that VectorStore defines the expected interface (U-HA-3)."""
        # Verify that VectorStore is an abstract base class
        assert issubclass(VectorStore, ABC)

        # Check that all required methods are defined
        required_methods = [
            "add_vector",
            "update_vector",
            "delete_vector",
            "search_vectors",
        ]

        for method_name in required_methods:
            assert hasattr(VectorStore,
                           method_name), f"VectorStore should define '{method_name}' method"
            method = getattr(VectorStore, method_name)
            assert callable(method), f"'{method_name}' should be a method"

    def test_vector_store_independency(self):
        """Test that VectorStore has no infrastructure dependencies (U-HA-2)."""
        import inspect

        # Get the source code of the interface
        source = inspect.getsource(VectorStore)

        # Check for implementation-related terms
        implementation_terms = [
            "mongodb",
            "mongo",
            "pinecone",
            "elasticsearch",
            "opensearch",
            "faiss",
            "annoy",
            "hnswlib",
        ]

        for term in implementation_terms:
            assert term.lower() not in source.lower(), f"VectorStore should not reference '{term}'"

    def test_vector_store_contract(self):
        """Test the contract that implementations of VectorStore must adhere to."""

        # A concrete implementation for testing
        class MockVectorStore(VectorStore):
            def __init__(self):
                self.vectors = {}
                self.metadata = {}

            def add_vector(self, id: str, vector: List[float],
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
                self.vectors[id] = vector
                if metadata:
                    self.metadata[id] = metadata
                return True

            def update_vector(self, id: str, vector: List[float],
                              metadata: Optional[
                                  Dict[str, Any]] = None) -> bool:
                if id not in self.vectors:
                    return False

                self.vectors[id] = vector
                if metadata:
                    self.metadata[id] = metadata
                return True

            def delete_vector(self, id: str) -> bool:
                if id not in self.vectors:
                    return False

                del self.vectors[id]
                if id in self.metadata:
                    del self.metadata[id]
                return True

            def search_vectors(self, query_vector: List[float],
                               limit: int = 10) -> List[
                Tuple[str, float, Optional[Dict[str, Any]]]]:
                # Simplified implementation for testing - just return the first 'limit' vectors
                # with a mock similarity score
                results = []
                for id, vector in list(self.vectors.items())[:limit]:
                    similarity = 0.9  # Mock similarity score
                    metadata = self.metadata.get(id)
                    results.append((id, similarity, metadata))
                return results

        # Create a mock vector store for testing
        store = MockVectorStore()

        # Test add_vector method
        test_id = "test1"
        test_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        test_metadata = {"source": "test_file.py", "type": "python"}

        assert store.add_vector(test_id, test_vector, test_metadata) is True

        # Test update_vector method
        updated_vector = [0.5, 0.4, 0.3, 0.2, 0.1]
        assert store.update_vector(test_id, updated_vector) is True
        assert store.update_vector("nonexistent", updated_vector) is False

        # Test search_vectors method
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        store.add_vector("test2", [0.2, 0.3, 0.4, 0.5, 0.6],
                         {"source": "test_file2.py"})

        results = store.search_vectors(query_vector, 2)
        assert len(results) == 2

        for result in results:
            assert len(result) == 3
            assert isinstance(result[0], str)  # ID
            assert isinstance(result[1], float)  # Similarity score
            assert isinstance(result[2], dict) or result[2] is None  # Metadata

        # Test delete_vector method
        assert store.delete_vector(test_id) is True
        assert store.delete_vector("nonexistent") is False

        # After deletion, search should return fewer results
        results_after_delete = store.search_vectors(query_vector, 2)
        assert len(results_after_delete) == 1