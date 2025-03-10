import pytest
import os
from unittest.mock import patch, Mock
from dotenv import load_dotenv

from src.infrastructure.adapters.openai_adapter import OpenAIAdapter
from src.application.services.embedding_service import EmbeddingService
from src.application.services.rag_service import RAGService
from src.domain.entities.context_item import ContextItem, ContentType

# Mark the whole file as integration tests
pytestmark = pytest.mark.integration

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection details from environment variables with fallbacks
API_KEY = os.getenv("OPENAI_TEST_API_KEY", "")


class TestOpenAIAdapterIntegration:
    """Integration tests for the OpenAI adapter."""

    @pytest.fixture
    def openai_adapter(self):
        """Create an OpenAI adapter for testing, using mock if no API key."""
        if API_KEY:
            return OpenAIAdapter(
                api_key=API_KEY,
                model="gpt-3.5-turbo",  # Use cheaper model for testing
                embedding_model="text-embedding-ada-002"
            )
        else:
            pytest.skip("OpenAI API key not available")

    @pytest.mark.skipif(not API_KEY, reason="OpenAI API key not available")
    def test_generate_text_live(self, openai_adapter):
        """Test generating text with actual OpenAI API call (I-LLM-1)."""
        # Arrange
        prompt = "Write a one-sentence summary of what an agentic coding system does."

        # Act
        response = openai_adapter.generate_text(prompt)

        # Assert
        assert response is not None
        assert len(response) > 0
        assert isinstance(response, str)

    @pytest.mark.skipif(not API_KEY, reason="No OpenAI API key")
    def test_generate_embedding_live(self, openai_adapter):
        """Test generating embeddings with actual OpenAI API call (I-LLM-1)."""
        # Arrange
        text = "Testing embedding generation with the OpenAI API."

        # Act
        embedding = openai_adapter.generate_embedding(text)

        # Assert
        assert embedding is not None
        assert len(embedding) > 0
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)

    def test_generate_text_mock(self):
        """Test generating text with mocked OpenAI client for CI (I-LLM-1)."""
        # Arrange
        with patch("openai.OpenAI") as mock_openai:
            # Configure mock
            mock_client = Mock()
            mock_openai.return_value = mock_client

            mock_response = Mock()
            mock_response.choices = [
                Mock(message=Mock(content="Mocked response"))]
            mock_client.chat.completions.create.return_value = mock_response

            adapter = OpenAIAdapter(api_key="mock-key", model="gpt-4")
            prompt = "Test prompt"

            # Act
            response = adapter.generate_text(prompt)

            # Assert
            assert response == "Mocked response"
            mock_client.chat.completions.create.assert_called_once()

    def test_rate_limit_retry_mechanism(self):
        """Test rate limit retry mechanism (I-LLM-2)."""
        # Arrange
        with patch("openai.OpenAI") as mock_openai:
            # Configure mock
            mock_client = Mock()
            mock_openai.return_value = mock_client

            # Create a rate limit error for the first call, then succeed
            mock_client.chat.completions.create.side_effect = [
                Exception("Rate limit exceeded"),
                Mock(
                    choices=[Mock(message=Mock(content="Success after retry"))])
            ]

            adapter = OpenAIAdapter(api_key="mock-key", model="gpt-4")

            # Act
            response = adapter.generate_text("Test prompt")

            # Assert
            assert response == "Success after retry"
            assert mock_client.chat.completions.create.call_count == 2

    def test_context_window_management(self):
        """Test context window management with large inputs (I-LLM-3)."""
        # Arrange
        with patch("openai.OpenAI") as mock_openai:
            # Configure mock
            mock_client = Mock()
            mock_openai.return_value = mock_client

            mock_response = Mock()
            mock_response.choices = [
                Mock(message=Mock(content="Response for large input"))]
            mock_client.chat.completions.create.return_value = mock_response

            adapter = OpenAIAdapter(api_key="mock-key", model="gpt-4")

            # Create a large prompt that exceeds typical token limits
            large_prompt = "word " * 10000  # This would be ~10k tokens

            # Act
            response = adapter.generate_text(large_prompt)

            # Assert
            assert response == "Response for large input"

            # Verify the messages parameter to check if truncation occurred
            call_args = mock_client.chat.completions.create.call_args[1]
            messages = call_args["messages"]
            user_message = next((m for m in messages if m["role"] == "user"),
                                None)

            # The model should still have received something, even if truncated
            assert user_message is not None
            assert "content" in user_message
            assert len(user_message["content"]) > 0


class TestEmbeddingServiceIntegration:
    """Integration tests for the Embedding Service."""

    @pytest.fixture
    def embedding_service(self):
        """Create an Embedding Service with mock OpenAI adapter."""
        with patch("openai.OpenAI") as mock_openai:
            # Configure mock
            mock_client = Mock()
            mock_openai.return_value = mock_client

            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3, 0.4, 0.5])]
            mock_client.embeddings.create.return_value = mock_response

            adapter = OpenAIAdapter(api_key="mock-key", model="gpt-4")
            return EmbeddingService(llm_provider=adapter)

    def test_chunking_large_text(self, embedding_service):
        """Test embedding service handles large text properly (I-LLM-3)."""
        # Arrange
        # Create text larger than the MAX_TEXT_LENGTH in EmbeddingService
        large_text = "word " * 10000  # Well over 8000 chars

        # Act
        embedding = embedding_service.generate_embedding_for_text(large_text)

        # Assert
        assert embedding is not None
        assert len(embedding) > 0
        assert embedding == [0.1, 0.2, 0.3, 0.4, 0.5]

        # The provider should have been called with a truncated version
        provider = embedding_service.llm_provider
        args = provider.generate_embedding.call_args[0]
        assert len(args[0]) <= embedding_service.MAX_TEXT_LENGTH

    def test_handling_multiple_context_items(self, embedding_service):
        """Test embedding service handles multiple context items (I-LLM-1)."""
        # Arrange
        context_items = [
            ContextItem(
                id="test-id-1",
                source="test1.py",
                content="def test_function1():\n    pass",
                content_type=ContentType.PYTHON
            ),
            ContextItem(
                id="test-id-2",
                source="test2.py",
                content="def test_function2():\n    pass",
                content_type=ContentType.PYTHON
            )
        ]

        # Act
        results = embedding_service.generate_embeddings_for_context_items(
            context_items)

        # Assert
        assert len(results) == 2
        assert all(item.embedding is not None for item in results)
        assert embedding_service.llm_provider.generate_embedding.call_count == 2


class TestRAGServiceIntegration:
    """Integration tests for the RAG Service."""

    @pytest.fixture
    def mock_context_repository(self):
        """Create a mock context repository."""
        repo = Mock()
        repo.search_by_vector.return_value = [
            (
                ContextItem(
                    id="test-id-1",
                    source="test1.py",
                    content="def fibonacci(n):\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                    content_type=ContentType.PYTHON
                ),
                0.9
            ),
            (
                ContextItem(
                    id="test-id-2",
                    source="test2.py",
                    content="def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n-1)",
                    content_type=ContentType.PYTHON
                ),
                0.8
            )
        ]
        return repo

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        provider = Mock()
        provider.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        provider.generate_text.return_value = "This is a response using the provided context."
        return provider

    @pytest.fixture
    def rag_service(self, mock_context_repository, mock_llm_provider):
        """Create a RAG service with mock dependencies."""
        embedding_service = EmbeddingService(llm_provider=mock_llm_provider)
        return RAGService(
            context_repository=mock_context_repository,
            llm_provider=mock_llm_provider,
            embedding_service=embedding_service
        )

    def test_retrieval_and_generation(self, rag_service,
                                      mock_context_repository,
                                      mock_llm_provider):
        """Test end-to-end retrieval and generation (I-LLM-3)."""
        # Arrange
        query = "How to implement a fibonacci function?"

        # Act
        response = rag_service.generate_with_context(query)

        # Assert
        # Verify embedding was generated for search
        mock_llm_provider.generate_embedding.assert_called_once()

        # Verify repository was searched
        mock_context_repository.search_by_vector.assert_called_once()

        # Verify text generation was called with a prompt containing context
        mock_llm_provider.generate_text.assert_called_once()
        prompt = mock_llm_provider.generate_text.call_args[0][0]
        assert "fibonacci" in prompt
        assert "factorial" in prompt
        assert query in prompt

        # Check that a response was returned
        assert response == "This is a response using the provided context."

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"),
                        reason="No OpenAI API key")
    def test_live_rag_with_openai(self, mock_context_repository):
        """Test RAG with actual OpenAI API if key is available (I-LLM-1)."""
        # Arrange
        api_key = os.getenv("OPENAI_API_KEY")
        openai_adapter = OpenAIAdapter(
            api_key=api_key,
            model="gpt-3.5-turbo",  # Use cheaper model for testing
            embedding_model="text-embedding-ada-002"
        )
        embedding_service = EmbeddingService(llm_provider=openai_adapter)
        rag_service = RAGService(
            context_repository=mock_context_repository,
            llm_provider=openai_adapter,
            embedding_service=embedding_service
        )

        query = "How do I implement a recursive function?"

        # Act
        response = rag_service.generate_with_context(query)

        # Assert
        assert response is not None
        assert len(response) > 0
        assert isinstance(response, str)