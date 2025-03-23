from typing import Dict, Any, List, Tuple, Optional
from abc import ABC
from uuid import uuid4

from src.domain.ports.context_repository import ContextRepository
from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.container import Container, ContainerType


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
            # Container-related methods
            "add_container",
            "get_container",
            "update_container",
            "delete_container",
            "list_containers",
            "list_by_container",
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
                self.containers = {}

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

            # Container management methods
            def add_container(self, container: Container) -> Container:
                self.containers[container.id] = container
                return container

            def get_container(self, container_id: str) -> Optional[Container]:
                return self.containers.get(container_id)

            def update_container(self, container: Container) -> Container:
                if container.id not in self.containers:
                    raise KeyError(
                        f"Container with ID {container.id} not found")
                self.containers[container.id] = container
                return container

            def delete_container(self, container_id: str) -> bool:
                if container_id not in self.containers:
                    return False
                del self.containers[container_id]
                return True

            def list_containers(self, filters: Dict[str, Any] = None) -> List[
                Container]:
                if not filters:
                    return list(self.containers.values())

                result = []
                for container in self.containers.values():
                    match = True
                    for key, value in filters.items():
                        if hasattr(container, key) and getattr(container,
                                                               key) != value:
                            match = False
                            break
                    if match:
                        result.append(container)
                return result

            def list_by_container(self, container_id: str) -> List[ContextItem]:
                return [item for item in self.items.values() if
                        item.container_id == container_id]

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

    def test_context_repository_container_methods(self):
        """Test container-related methods."""

        # A concrete implementation for testing
        class MockContextRepository(ContextRepository):
            def __init__(self):
                self.items = {}
                self.containers = {}

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

            # Container management methods
            def add_container(self, container: Container) -> Container:
                self.containers[container.id] = container
                return container

            def get_container(self, container_id: str) -> Optional[Container]:
                return self.containers.get(container_id)

            def update_container(self, container: Container) -> Container:
                if container.id not in self.containers:
                    raise KeyError(
                        f"Container with ID {container.id} not found")
                self.containers[container.id] = container
                return container

            def delete_container(self, container_id: str) -> bool:
                if container_id not in self.containers:
                    return False
                del self.containers[container_id]
                return True

            def list_containers(self, filters: Dict[str, Any] = None) -> List[
                Container]:
                if not filters:
                    return list(self.containers.values())

                result = []
                for container in self.containers.values():
                    match = True
                    for key, value in filters.items():
                        if hasattr(container, key) and getattr(container,
                                                               key) != value:
                            match = False
                            break
                    if match:
                        result.append(container)
                return result

            def list_by_container(self, container_id: str) -> List[ContextItem]:
                return [item for item in self.items.values() if
                        item.container_id == container_id]

        # Create a mock repository for testing
        repo = MockContextRepository()

        # Create a test container
        container = Container(
            id=str(uuid4()),
            name="test-container",
            title="Test Container",
            container_type="code",
            source_path="/path/to/source"
        )

        # Test add_container method
        added_container = repo.add_container(container)
        assert added_container.id == container.id
        assert added_container.name == "test-container"

        # Test get_container method
        retrieved_container = repo.get_container(container.id)
        assert retrieved_container is not None
        assert retrieved_container.id == container.id
        assert retrieved_container.title == "Test Container"

        # Test update_container method
        container.description = "Updated description"
        updated_container = repo.update_container(container)
        assert updated_container.description == "Updated description"

        # Test list_containers method
        container2 = Container(
            id=str(uuid4()),
            name="docs-container",
            title="Documentation Container",
            container_type="documentation",
            source_path="/path/to/docs"
        )
        repo.add_container(container2)
        all_containers = repo.list_containers()
        assert len(all_containers) == 2

        # Test list_containers with filters
        code_containers = repo.list_containers(
            {"container_type": ContainerType.CODE})
        assert len(code_containers) == 1
        assert code_containers[0].name == "test-container"

        # Test delete_container method
        deleted = repo.delete_container(container.id)
        assert deleted is True
        assert repo.get_container(container.id) is None

    def test_context_repository_list_by_container(self):
        """Test retrieving items by container."""

        # A concrete implementation for testing
        class MockContextRepository(ContextRepository):
            def __init__(self):
                self.items = {}
                self.containers = {}

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

            # Container management methods
            def add_container(self, container: Container) -> Container:
                self.containers[container.id] = container
                return container

            def get_container(self, container_id: str) -> Optional[Container]:
                return self.containers.get(container_id)

            def update_container(self, container: Container) -> Container:
                if container.id not in self.containers:
                    raise KeyError(
                        f"Container with ID {container.id} not found")
                self.containers[container.id] = container
                return container

            def delete_container(self, container_id: str) -> bool:
                if container_id not in self.containers:
                    return False
                del self.containers[container_id]
                return True

            def list_containers(self, filters: Dict[str, Any] = None) -> List[
                Container]:
                if not filters:
                    return list(self.containers.values())

                result = []
                for container in self.containers.values():
                    match = True
                    for key, value in filters.items():
                        if hasattr(container, key) and getattr(container,
                                                               key) != value:
                            match = False
                            break
                    if match:
                        result.append(container)
                return result

            def list_by_container(self, container_id: str) -> List[ContextItem]:
                return [item for item in self.items.values() if
                        item.container_id == container_id]

        # Create a mock repository for testing
        repo = MockContextRepository()

        # Create test containers
        container1_id = str(uuid4())
        container1 = Container(
            id=container1_id,
            name="code-container",
            title="Code Container",
            container_type="code",
            source_path="/path/to/code"
        )

        container2_id = str(uuid4())
        container2 = Container(
            id=container2_id,
            name="docs-container",
            title="Documentation Container",
            container_type="documentation",
            source_path="/path/to/docs"
        )

        repo.add_container(container1)
        repo.add_container(container2)

        # Create test context items in different containers
        item1 = ContextItem(
            id="item1",
            source="file1.py",
            content="def function1(): pass",
            content_type=ContentType.PYTHON,
            container_id=container1_id
        )

        item2 = ContextItem(
            id="item2",
            source="file2.py",
            content="def function2(): pass",
            content_type=ContentType.PYTHON,
            container_id=container1_id
        )

        item3 = ContextItem(
            id="item3",
            source="doc1.md",
            content="# Documentation",
            content_type=ContentType.MARKDOWN,
            container_id=container2_id
        )

        item4 = ContextItem(
            id="item4",
            source="file3.py",
            content="def function3(): pass",
            content_type=ContentType.PYTHON,
            container_id=None  # No container
        )

        repo.add(item1)
        repo.add(item2)
        repo.add(item3)
        repo.add(item4)

        # Test list_by_container for code container
        code_items = repo.list_by_container(container1_id)
        assert len(code_items) == 2
        assert "item1" in [item.id for item in code_items]
        assert "item2" in [item.id for item in code_items]

        # Test list_by_container for documentation container
        doc_items = repo.list_by_container(container2_id)
        assert len(doc_items) == 1
        assert doc_items[0].id == "item3"

        # Test list_by_container for non-existent container
        nonexistent_items = repo.list_by_container("nonexistent-id")
        assert len(nonexistent_items) == 0

        # Test listing items with no container
        no_container_items = repo.list({"container_id": None})
        assert len(no_container_items) == 1
        assert no_container_items[0].id == "item4"