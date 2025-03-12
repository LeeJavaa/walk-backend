"""
Dependency container for the CLI.

This module provides factory functions for creating use cases and services
with their dependencies.
"""
import logging
from typing import Optional

from src.domain.usecases.context_management import (
    AddContextUseCase,
    RemoveContextUseCase,
    UpdateContextUseCase,
    ListContextUseCase,
    SearchContextUseCase
)
from src.domain.usecases.pipeline_management import (
    CreatePipelineUseCase,
    ExecutePipelineStageUseCase,
    RollbackPipelineUseCase,
    GetPipelineStateUseCase
)
from src.domain.usecases.feedback_management import (
    SubmitFeedbackUseCase,
    IncorporateFeedbackUseCase
)

from src.infrastructure.repositories.mongo_context_repository import \
    MongoContextRepository
from src.infrastructure.repositories.mongo_pipeline_repository import \
    MongoPipelineRepository
from src.infrastructure.adapters.mongodb_connection import MongoDBConnection
from src.infrastructure.adapters.openai_adapter import OpenAIAdapter
from src.infrastructure.adapters.file_system_adapter import FileSystemAdapter

from src.application.services.embedding_service import EmbeddingService
from src.application.services.rag_service import RAGService

# Connection and adapter instances
_mongodb_connection: Optional[MongoDBConnection] = None
_openai_adapter: Optional[OpenAIAdapter] = None
_file_system_adapter: Optional[FileSystemAdapter] = None

# Repository instances
_context_repository: Optional[MongoContextRepository] = None
_pipeline_repository: Optional[MongoPipelineRepository] = None

# Service instances
_embedding_service: Optional[EmbeddingService] = None
_rag_service: Optional[RAGService] = None

logger = logging.getLogger(__name__)


def create_mongodb_connection() -> MongoDBConnection:
    """Create or get the MongoDB connection."""
    global _mongodb_connection

    if _mongodb_connection is None:
        # Get connection details from environment or config
        from src.config import MONGODB_URI, MONGODB_DB_NAME

        logger.info(
            f"Creating MongoDB connection to {MONGODB_URI} using database {MONGODB_DB_NAME}")
        _mongodb_connection = MongoDBConnection(MONGODB_URI, MONGODB_DB_NAME)

    return _mongodb_connection


def create_openai_adapter() -> OpenAIAdapter:
    """Create or get the OpenAI adapter."""
    global _openai_adapter

    if _openai_adapter is None:
        # Get API key and model from environment or config
        from src.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_EMBEDDING_MODEL

        logger.info(f"Creating OpenAI adapter using model {OPENAI_MODEL}")
        _openai_adapter = OpenAIAdapter(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            embedding_model=OPENAI_EMBEDDING_MODEL
        )

    return _openai_adapter


def create_file_system_adapter() -> FileSystemAdapter:
    """Create or get the file system adapter."""
    global _file_system_adapter

    if _file_system_adapter is None:
        logger.info("Creating file system adapter")
        _file_system_adapter = FileSystemAdapter()

    return _file_system_adapter


def create_context_repository() -> MongoContextRepository:
    """Create or get the context repository."""
    global _context_repository

    if _context_repository is None:
        mongodb_connection = create_mongodb_connection()

        logger.info("Creating MongoDB context repository")
        _context_repository = MongoContextRepository(
            connection=mongodb_connection,
            collection_name="context_items",
            vector_collection_name="context_vectors"
        )

    return _context_repository


def create_pipeline_repository() -> MongoPipelineRepository:
    """Create or get the pipeline repository."""
    global _pipeline_repository

    if _pipeline_repository is None:
        mongodb_connection = create_mongodb_connection()

        logger.info("Creating MongoDB pipeline repository")
        _pipeline_repository = MongoPipelineRepository(
            connection=mongodb_connection,
            tasks_collection_name="tasks",
            states_collection_name="pipeline_states"
        )

    return _pipeline_repository


def create_embedding_service() -> EmbeddingService:
    """Create or get the embedding service."""
    global _embedding_service

    if _embedding_service is None:
        openai_adapter = create_openai_adapter()

        logger.info("Creating embedding service")
        _embedding_service = EmbeddingService(llm_provider=openai_adapter)

    return _embedding_service


def create_rag_service() -> RAGService:
    """Create or get the RAG service."""
    global _rag_service

    if _rag_service is None:
        from src.config import VECTOR_SIMILARITY_THRESHOLD, MAX_CONTEXT_ITEMS

        context_repository = create_context_repository()
        openai_adapter = create_openai_adapter()
        embedding_service = create_embedding_service()

        logger.info("Creating RAG service")
        _rag_service = RAGService(
            context_repository=context_repository,
            llm_provider=openai_adapter,
            embedding_service=embedding_service,
            similarity_threshold=VECTOR_SIMILARITY_THRESHOLD,
            max_context_items=MAX_CONTEXT_ITEMS
        )

    return _rag_service


# Factory functions for use cases

def create_add_context_use_case() -> AddContextUseCase:
    """Create an AddContextUseCase instance."""
    context_repository = create_context_repository()
    openai_adapter = create_openai_adapter()
    file_system_adapter = create_file_system_adapter()

    return AddContextUseCase(
        context_repository=context_repository,
        llm_provider=openai_adapter,
        file_system=file_system_adapter
    )


def create_remove_context_use_case() -> RemoveContextUseCase:
    """Create a RemoveContextUseCase instance."""
    context_repository = create_context_repository()

    return RemoveContextUseCase(context_repository=context_repository)


def create_update_context_use_case() -> UpdateContextUseCase:
    """Create an UpdateContextUseCase instance."""
    context_repository = create_context_repository()
    openai_adapter = create_openai_adapter()

    return UpdateContextUseCase(
        context_repository=context_repository,
        llm_provider=openai_adapter
    )


def create_list_context_use_case() -> ListContextUseCase:
    """Create a ListContextUseCase instance."""
    context_repository = create_context_repository()

    return ListContextUseCase(context_repository=context_repository)


def create_search_context_use_case() -> SearchContextUseCase:
    """Create a SearchContextUseCase instance."""
    context_repository = create_context_repository()
    openai_adapter = create_openai_adapter()

    return SearchContextUseCase(
        context_repository=context_repository,
        llm_provider=openai_adapter
    )


def create_pipeline_use_case() -> CreatePipelineUseCase:
    """Create a CreatePipelineUseCase instance."""
    pipeline_repository = create_pipeline_repository()

    return CreatePipelineUseCase(pipeline_repository=pipeline_repository)


def create_execute_pipeline_stage_use_case() -> ExecutePipelineStageUseCase:
    """Create an ExecutePipelineStageUseCase instance."""
    pipeline_repository = create_pipeline_repository()

    return ExecutePipelineStageUseCase(pipeline_repository=pipeline_repository)


def create_rollback_pipeline_use_case() -> RollbackPipelineUseCase:
    """Create a RollbackPipelineUseCase instance."""
    pipeline_repository = create_pipeline_repository()

    return RollbackPipelineUseCase(pipeline_repository=pipeline_repository)


def create_get_pipeline_state_use_case() -> GetPipelineStateUseCase:
    """Create a GetPipelineStateUseCase instance."""
    pipeline_repository = create_pipeline_repository()

    return GetPipelineStateUseCase(pipeline_repository=pipeline_repository)


def create_submit_feedback_use_case() -> SubmitFeedbackUseCase:
    """Create a SubmitFeedbackUseCase instance."""
    pipeline_repository = create_pipeline_repository()

    return SubmitFeedbackUseCase(pipeline_repository=pipeline_repository)


def create_incorporate_feedback_use_case() -> IncorporateFeedbackUseCase:
    """Create an IncorporateFeedbackUseCase instance."""
    pipeline_repository = create_pipeline_repository()

    return IncorporateFeedbackUseCase(pipeline_repository=pipeline_repository)