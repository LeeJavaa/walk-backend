import pytest
from unittest.mock import Mock, patch

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.ports.llm_provider import LLMProvider
from src.application.services.embedding_service import EmbeddingService


class TestEmbeddingService:
    """Test cases for the embedding service."""

    @pytest.fixture
    def llm_provider_mock(self):
        """Mock LLM provider that returns predetermined embeddings."""
        provider = Mock(spec=LLMProvider)
        provider.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        return provider

    @pytest.fixture
    def embedding_service(self, llm_provider_mock):
        """Create an embedding service with mock LLM provider."""
        return EmbeddingService(llm_provider=llm_provider_mock)

    def test_initialization(self, embedding_service, llm_provider_mock):
        """Test embedding service initialization."""
        assert embedding_service.llm_provider == llm_provider_mock

    def test_generate_embedding_for_text(self, embedding_service,
                                         llm_provider_mock):
        """Test generating embeddings for text content."""
        # Arrange
        text = "This is a test document for embedding generation."

        # Act
        embedding = embedding_service.generate_embedding_for_text(text)

        # Assert
        llm_provider_mock.generate_embedding.assert_called_once_with(text)
        assert embedding == [0.1, 0.2, 0.3, 0.4, 0.5]

    def test_generate_embedding_for_context_item(self, embedding_service,
                                                 llm_provider_mock):
        """Test generating embeddings for a context item."""
        # Arrange
        context_item = ContextItem(
            id="test-id",
            source="test.py",
            content="def test_function():\n    return 'Hello, World!'",
            content_type=ContentType.PYTHON,
            metadata={"author": "Test Author"}
        )

        # Act
        updated_item = embedding_service.generate_embedding_for_context_item(
            context_item)

        # Assert
        llm_provider_mock.generate_embedding.assert_called_once_with(
            context_item.content)
        assert updated_item.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert updated_item.id == context_item.id  # Should be the same item, with embedding added

    def test_generate_embeddings_for_context_items(self, embedding_service,
                                                   llm_provider_mock):
        """Test generating embeddings for multiple context items."""
        # Arrange
        context_items = [
            ContextItem(
                id="test-id-1",
                source="test1.py",
                content="def test_function1():\n    return 'Hello, World!'",
                content_type=ContentType.PYTHON,
                metadata={"author": "Test Author"}
            ),
            ContextItem(
                id="test-id-2",
                source="test2.py",
                content="def test_function2():\n    return 'Goodbye, World!'",
                content_type=ContentType.PYTHON,
                metadata={"author": "Test Author"}
            )
        ]

        # Act
        updated_items = embedding_service.generate_embeddings_for_context_items(
            context_items)

        # Assert
        assert llm_provider_mock.generate_embedding.call_count == 2
        assert len(updated_items) == 2
        assert updated_items[0].embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert updated_items[1].embedding == [0.1, 0.2, 0.3, 0.4, 0.5]

    def test_chunking_strategy(self, embedding_service, llm_provider_mock):
        """Test chunking strategy for large text."""
        # Arrange
        # Create a long text that would need to be chunked
        long_text = "word " * 10000  # Create a very long text

        # Act
        embedding = embedding_service.generate_embedding_for_text(long_text)

        # Assert
        # Should have been chunked and processed - simplified call assertion
        assert llm_provider_mock.generate_embedding.called
        assert embedding == [0.1, 0.2, 0.3, 0.4,
                             0.5]  # Result should still be returned