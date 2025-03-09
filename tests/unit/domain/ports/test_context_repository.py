import pytest
from typing import Dict, Any, List, Tuple, Optional
from abc import ABC

from src.domain.ports.context_repository import ContextRepository
from src.domain.entities.context_item import ContextItem, ContentType


class TestContextRepository:
    """Test cases for the ContextRepository port."""

    def test_context_repository_interface(self):
        """Test that ContextRepository defines the expected interface (U-HA-3)."""
        # Verify that ContextRepository is an abstract base class
        assert issubclass(ContextRepository, ABC)

        # Check that all required methods are defined
        required_methods = [
            "add",
            "get_by_id",
            "update",
            "delete",
            "list",
            "search_by_vector",
        ]

        for method_name in required_methods:
            assert hasattr(ContextRepository,
                           method_name), f"ContextRepository should define '{method_name}' method"
            method = getattr(ContextRepository, method_name)
            assert callable(method), f"'{method_name}' should be a method"

    def test_context_repository_independency(self):
        """Test that ContextRepository has no infrastructure dependencies (U-HA-2)."""
        import inspect

        # Get the source code of the interface
        source = inspect.getsource(ContextRepository)

        # Check for infrastructure-related terms
        infrastructure_terms = [
            "mongodb",
            "mongo",
            "database",
            "sql",
            "openai",
            "file system",
            "filesystem",
            "http",
            "api"
        ]

        for term in infrastructure_terms:
            assert term.lower() not in source.lower(), f"ContextRepository should not reference '{term}'"

    def test_context_repository_contract(self):
        """Test the contract that implementations of ContextRepository must adhere to."""

        # A concrete implementation for testing
        class MockContextRepository(ContextRepository):
            def __init__(self):
                self.items = {}

            def add(self, context_item: ContextItem) -> ContextItem:
                self.items[context_item.id] = context_item
                return context_item

            def get_by_id(self, context_id: str) -> Optional[ContextItem]:
                return self.items.get(context_id)

            def update(self, context_item: ContextItem) -> ContextItem:
                if context_item.id not in self.items:
                    raise KeyError(
                        f"Context item with ID {context_item.id} not found")
                self.items[context_item.id] = context_item
                return context_item

            def delete(self, context_id: str) -> bool:
                if context_id not in self.items:
                    return False
                del self.items[context_id]
                return True

            def list(self, filters: Dict[str, Any] = None) -> List[ContextItem]:
                if not filters:
                    return list(self.items.values())

                result = []
                for item in self.items.values():
                    match = True
                    for key, value in filters.items():
                        if hasattr(item, key) and getattr(item, key) != value:
                            match = False
                            break
                    if match:
                        result.append(item)
                return result

            def search_by_vector(self, query_vector: List[float],
                                 limit: int = 10) -> List[
                Tuple[ContextItem, float]]:
                # Simplified implementation for testing
                items = list(self.items.values())[:limit]
                return [(item, 0.9) for item in items]

        # Create a mock repository for testing
        repo = MockContextRepository()

        # Test add method
        context_item = ContextItem(
            id="test1",
            source="test_file.py",
            content="def test(): pass",
            content_type=ContentType.PYTHON,
        )
        added = repo.add(context_item)
        assert added.id == "test1"
        assert added == context_item

        # Test get_by_id method
        retrieved = repo.get_by_id("test1")
        assert retrieved is not None
        assert retrieved.id == "test1"
        assert retrieved.source == "test_file.py"

        # Test update method
        context_item.content = "def updated(): pass"
        updated = repo.update(context_item)
        assert updated.content == "def updated(): pass"

        # Test list method
        context_item2 = ContextItem(
            id="test2",
            source="test_file2.py",
            content="def test2(): pass",
            content_type=ContentType.PYTHON,
        )
        repo.add(context_item2)
        all_items = repo.list()
        assert len(all_items) == 2
        assert all_items[0].id in ["test1", "test2"]
        assert all_items[1].id in ["test1", "test2"]

        # Test list with filters
        python_items = repo.list({"content_type": ContentType.PYTHON})
        assert len(python_items) == 2

        # Test delete method
        deleted = repo.delete("test1")
        assert deleted is True
        assert repo.get_by_id("test1") is None

        # Test search_by_vector method
        vector_results = repo.search_by_vector([0.1, 0.2, 0.3])
        assert len(vector_results) == 1
        assert vector_results[0][0].id == "test2"
        assert isinstance(vector_results[0][1], float)