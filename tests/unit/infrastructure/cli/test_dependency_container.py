import pytest
from unittest.mock import patch, MagicMock

from src.infrastructure.cli.utils.dependency_container import (
    create_mongodb_connection,
    create_openai_adapter,
    create_file_system_adapter,
    create_context_repository,
    create_pipeline_repository,
    create_embedding_service,
    create_rag_service,
    create_add_context_use_case,
    create_search_context_use_case,
    create_pipeline_use_case,
    create_execute_pipeline_stage_use_case,
    create_submit_feedback_use_case
)


class TestDependencyContainer:
    """Test cases for the dependency container utility."""

    @patch(
        "src.infrastructure.cli.utils.dependency_container.MongoDBConnection")
    @patch("src.infrastructure.cli.utils.dependency_container.MONGODB_URI",
           "test-uri")
    @patch("src.infrastructure.cli.utils.dependency_container.MONGODB_DB_NAME",
           "test-db")
    def test_create_mongodb_connection(self, mock_connection_class):
        """Test creating a MongoDB connection."""
        # Arrange
        mock_connection = MagicMock()
        mock_connection_class.return_value = mock_connection

        # Act
        connection1 = create_mongodb_connection()
        connection2 = create_mongodb_connection()  # Should return the same instance

        # Assert
        mock_connection_class.assert_called_once_with("test-uri", "test-db")
        assert connection1 == connection2  # Singleton behavior
        assert connection1 == mock_connection

    @patch("src.infrastructure.cli.utils.dependency_container.OpenAIAdapter")
    @patch("src.infrastructure.cli.utils.dependency_container.OPENAI_API_KEY",
           "test-key")
    @patch("src.infrastructure.cli.utils.dependency_container.OPENAI_MODEL",
           "test-model")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.OPENAI_EMBEDDING_MODEL",
        "test-embed-model")
    def test_create_openai_adapter(self, mock_adapter_class):
        """Test creating an OpenAI adapter."""
        # Arrange
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        # Act
        adapter1 = create_openai_adapter()
        adapter2 = create_openai_adapter()  # Should return the same instance

        # Assert
        mock_adapter_class.assert_called_once_with(
            api_key="test-key",
            model="test-model",
            embedding_model="test-embed-model"
        )
        assert adapter1 == adapter2  # Singleton behavior
        assert adapter1 == mock_adapter

    @patch(
        "src.infrastructure.cli.utils.dependency_container.FileSystemAdapter")
    def test_create_file_system_adapter(self, mock_adapter_class):
        """Test creating a file system adapter."""
        # Arrange
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        # Act
        adapter1 = create_file_system_adapter()
        adapter2 = create_file_system_adapter()  # Should return the same instance

        # Assert
        mock_adapter_class.assert_called_once()
        assert adapter1 == adapter2  # Singleton behavior
        assert adapter1 == mock_adapter

    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_mongodb_connection")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.MongoContextRepository")
    def test_create_context_repository(self, mock_repo_class,
                                       mock_create_connection):
        """Test creating a context repository."""
        # Arrange
        mock_connection = MagicMock()
        mock_create_connection.return_value = mock_connection

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Act
        repo1 = create_context_repository()
        repo2 = create_context_repository()  # Should return the same instance

        # Assert
        mock_create_connection.assert_called_once()
        mock_repo_class.assert_called_once_with(
            connection=mock_connection,
            collection_name="context_items",
            vector_collection_name="context_vectors"
        )
        assert repo1 == repo2  # Singleton behavior
        assert repo1 == mock_repo

    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_mongodb_connection")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.MongoPipelineRepository")
    def test_create_pipeline_repository(self, mock_repo_class,
                                        mock_create_connection):
        """Test creating a pipeline repository."""
        # Arrange
        mock_connection = MagicMock()
        mock_create_connection.return_value = mock_connection

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Act
        repo1 = create_pipeline_repository()
        repo2 = create_pipeline_repository()  # Should return the same instance

        # Assert
        mock_create_connection.assert_called_once()
        mock_repo_class.assert_called_once_with(
            connection=mock_connection,
            tasks_collection_name="tasks",
            states_collection_name="pipeline_states"
        )
        assert repo1 == repo2  # Singleton behavior
        assert repo1 == mock_repo

    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_openai_adapter")
    @patch("src.infrastructure.cli.utils.dependency_container.EmbeddingService")
    def test_create_embedding_service(self, mock_service_class,
                                      mock_create_adapter):
        """Test creating an embedding service."""
        # Arrange
        mock_adapter = MagicMock()
        mock_create_adapter.return_value = mock_adapter

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Act
        service1 = create_embedding_service()
        service2 = create_embedding_service()  # Should return the same instance

        # Assert
        mock_create_adapter.assert_called_once()
        mock_service_class.assert_called_once_with(llm_provider=mock_adapter)
        assert service1 == service2  # Singleton behavior
        assert service1 == mock_service

    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_context_repository")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_openai_adapter")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_embedding_service")
    @patch("src.infrastructure.cli.utils.dependency_container.RAGService")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.VECTOR_SIMILARITY_THRESHOLD",
        0.7)
    @patch(
        "src.infrastructure.cli.utils.dependency_container.MAX_CONTEXT_ITEMS",
        10)
    def test_create_rag_service(self, mock_service_class, mock_create_embedding,
                                mock_create_openai, mock_create_context):
        """Test creating a RAG service."""
        # Arrange
        mock_context = MagicMock()
        mock_create_context.return_value = mock_context

        mock_openai = MagicMock()
        mock_create_openai.return_value = mock_openai

        mock_embedding = MagicMock()
        mock_create_embedding.return_value = mock_embedding

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Act
        service1 = create_rag_service()
        service2 = create_rag_service()  # Should return the same instance

        # Assert
        mock_create_context.assert_called_once()
        mock_create_openai.assert_called_once()
        mock_create_embedding.assert_called_once()
        mock_service_class.assert_called_once_with(
            context_repository=mock_context,
            llm_provider=mock_openai,
            embedding_service=mock_embedding,
            similarity_threshold=0.7,
            max_context_items=10
        )
        assert service1 == service2  # Singleton behavior
        assert service1 == mock_service

    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_context_repository")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_openai_adapter")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_file_system_adapter")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.AddContextUseCase")
    def test_create_add_context_use_case(self, mock_use_case_class,
                                         mock_create_fs,
                                         mock_create_openai,
                                         mock_create_context):
        """Test creating an add context use case."""
        # Arrange
        mock_context = MagicMock()
        mock_create_context.return_value = mock_context

        mock_openai = MagicMock()
        mock_create_openai.return_value = mock_openai

        mock_fs = MagicMock()
        mock_create_fs.return_value = mock_fs

        mock_use_case = MagicMock()
        mock_use_case_class.return_value = mock_use_case

        # Act
        use_case = create_add_context_use_case()

        # Assert
        mock_create_context.assert_called_once()
        mock_create_openai.assert_called_once()
        mock_create_fs.assert_called_once()
        mock_use_case_class.assert_called_once_with(
            context_repository=mock_context,
            llm_provider=mock_openai,
            file_system=mock_fs
        )
        assert use_case == mock_use_case

    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_pipeline_repository")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.CreatePipelineUseCase")
    def test_create_pipeline_use_case(self, mock_use_case_class,
                                      mock_create_pipeline_repo):
        """Test creating a pipeline use case."""
        # Arrange
        mock_repo = MagicMock()
        mock_create_pipeline_repo.return_value = mock_repo

        mock_use_case = MagicMock()
        mock_use_case_class.return_value = mock_use_case

        # Act
        use_case = create_pipeline_use_case()

        # Assert
        mock_create_pipeline_repo.assert_called_once()
        mock_use_case_class.assert_called_once_with(
            pipeline_repository=mock_repo)
        assert use_case == mock_use_case

    @patch(
        "src.infrastructure.cli.utils.dependency_container.create_pipeline_repository")
    @patch(
        "src.infrastructure.cli.utils.dependency_container.SubmitFeedbackUseCase")
    def test_create_submit_feedback_use_case(self, mock_use_case_class,
                                             mock_create_pipeline_repo):
        """Test creating a submit feedback use case."""
        # Arrange
        mock_repo = MagicMock()
        mock_create_pipeline_repo.return_value = mock_repo

        mock_use_case = MagicMock()
        mock_use_case_class.return_value = mock_use_case

        # Act
        use_case = create_submit_feedback_use_case()

        # Assert
        mock_create_pipeline_repo.assert_called_once()
        mock_use_case_class.assert_called_once_with(
            pipeline_repository=mock_repo)
        assert use_case == mock_use_case