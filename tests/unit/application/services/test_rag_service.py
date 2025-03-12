import pytest
from unittest.mock import Mock, patch

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.ports.context_repository import ContextRepository
from src.domain.ports.llm_provider import LLMProvider
from src.application.services.embedding_service import EmbeddingService
from src.application.services.rag_service import RAGService


class TestRAGService:
    """Test cases for the RAG (Retrieval Augmented Generation) service."""

    @pytest.fixture
    def context_repository_mock(self):
        """Mock context repository for testing."""
        repo = Mock(spec=ContextRepository)

        # Sample context items to return for search
        context_items = [
            (ContextItem(
                id="test-id-1",
                source="test1.py",
                content="def fibonacci(n):\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                content_type=ContentType.PYTHON,
                metadata={"author": "Test Author"},
                embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
            ), 0.9),
            (ContextItem(
                id="test-id-2",
                source="test2.py",
                content="def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n-1)",
                content_type=ContentType.PYTHON,
                metadata={"author": "Test Author"},
                embedding=[0.2, 0.3, 0.4, 0.5, 0.6]
            ), 0.8)
        ]

        repo.search_by_vector.return_value = context_items
        return repo

    @pytest.fixture
    def llm_provider_mock(self):
        """Mock LLM provider for testing."""
        provider = Mock(spec=LLMProvider)
        provider.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        provider.generate_text.return_value = "This is a generated response based on context."
        return provider

    @pytest.fixture
    def embedding_service(self, llm_provider_mock):
        """Create an embedding service with mock LLM provider."""
        return EmbeddingService(llm_provider=llm_provider_mock)

    @pytest.fixture
    def rag_service(self, context_repository_mock, llm_provider_mock,
                    embedding_service):
        """Create a RAG service with mock dependencies."""
        return RAGService(
            context_repository=context_repository_mock,
            llm_provider=llm_provider_mock,
            embedding_service=embedding_service,
            similarity_threshold=0.7,
            max_context_items=5
        )

    def test_initialization(self, rag_service, context_repository_mock,
                            llm_provider_mock, embedding_service):
        """Test RAG service initialization."""
        assert rag_service.context_repository == context_repository_mock
        assert rag_service.llm_provider == llm_provider_mock
        assert rag_service.embedding_service == embedding_service
        assert rag_service.similarity_threshold == 0.7
        assert rag_service.max_context_items == 5

    def test_retrieve_context(self, rag_service, context_repository_mock,
                              llm_provider_mock):
        """Test retrieving context based on a query."""
        # Arrange
        query = "How to implement recursive functions?"

        # Act
        context_items = rag_service.retrieve_context(query)

        # Assert
        llm_provider_mock.generate_embedding.assert_called_once_with(query)
        context_repository_mock.search_by_vector.assert_called_once()
        assert len(context_items) == 2
        # Check that we only get the context items, not the similarity scores
        assert all(isinstance(item, ContextItem) for item in context_items)
        assert context_items[0].content.startswith("def fibonacci")
        assert context_items[1].content.startswith("def factorial")

    def test_retrieve_context_with_threshold(self, rag_service,
                                             context_repository_mock):
        """Test retrieving context with similarity threshold."""
        # Arrange
        query = "How to implement recursive functions?"
        # Mock results with lower similarity scores
        context_repository_mock.search_by_vector.return_value = [
            (ContextItem(
                id="test-id-1",
                source="test1.py",
                content="def fibonacci(n):\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                content_type=ContentType.PYTHON,
                metadata={},
                embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
            ), 0.9),
            (ContextItem(
                id="test-id-2",
                source="test2.py",
                content="def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n-1)",
                content_type=ContentType.PYTHON,
                metadata={},
                embedding=[0.2, 0.3, 0.4, 0.5, 0.6]
            ), 0.6)  # Below threshold
        ]

        # Act
        context_items = rag_service.retrieve_context(query)

        # Assert
        assert len(context_items) == 1  # Only one item above threshold
        assert context_items[0].content.startswith("def fibonacci")

    def test_generate_with_context(self, rag_service, llm_provider_mock):
        """Test generating text with retrieved context."""
        # Arrange
        query = "How to implement recursive functions?"

        # Act
        response = rag_service.generate_with_context(query)

        # Assert
        assert llm_provider_mock.generate_text.called
        # The context should be included in the prompt
        prompt = llm_provider_mock.generate_text.call_args[0][0]
        assert query in prompt
        assert "fibonacci" in prompt
        assert "factorial" in prompt
        assert response == "This is a generated response based on context."

    def test_generate_with_existing_context(self, rag_service,
                                            llm_provider_mock,
                                            context_repository_mock):
        """Test generating text with provided context items."""
        # Arrange
        query = "How to implement recursive functions?"
        context_items = [
            ContextItem(
                id="test-id-3",
                source="test3.py",
                content="def custom_function():\n    print('Hello')",
                content_type=ContentType.PYTHON,
                metadata={},
                embedding=None
            )
        ]

        # Act
        response = rag_service.generate_with_context(query, context_items)

        # Assert
        assert not context_repository_mock.search_by_vector.called  # Should not search repository
        assert llm_provider_mock.generate_text.called
        # The provided context should be included in the prompt
        prompt = llm_provider_mock.generate_text.call_args[0][0]
        assert "custom_function" in prompt
        assert response == "This is a generated response based on context."

    def test_retrieve_and_format_context(self, rag_service):
        """Test retrieving and formatting context for prompt."""
        # Arrange
        query = "How to implement recursive functions?"

        # Act
        formatted_context = rag_service.retrieve_and_format_context(query)

        # Assert
        assert "fibonacci" in formatted_context
        assert "factorial" in formatted_context
        assert "test1.py" in formatted_context
        assert "test2.py" in formatted_context