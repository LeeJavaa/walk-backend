import pytest
from unittest.mock import Mock, MagicMock

from src.application.pipeline.stage_factory import (
    create_pipeline_stage,
    STAGE_REGISTRY
)

from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.context_repository import ContextRepository
from src.application.services.rag_service import RAGService
from src.application.pipeline.stages.requirements_gathering_stage import \
    RequirementsGatheringStage
from src.application.pipeline.stages.knowledge_gathering_stage import \
    KnowledgeGatheringStage
from src.application.pipeline.stages.implementation_planning_stage import \
    ImplementationPlanningStage
from src.application.pipeline.stages.implementation_writing_stage import \
    ImplementationWritingStage
from src.application.pipeline.stages.review_stage import ReviewStage


class TestPipelineStageFactory:
    """Unit tests for the pipeline stage factory."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        return Mock(spec=LLMProvider)

    @pytest.fixture
    def mock_context_repository(self):
        """Create a mock context repository."""
        return Mock(spec=ContextRepository)

    @pytest.fixture
    def mock_rag_service(self):
        """Create a mock RAG service."""
        return Mock(spec=RAGService)

    def test_stage_registry(self):
        """Test that all expected stages are in the registry."""
        expected_stages = [
            "requirements_gathering",
            "knowledge_gathering",
            "implementation_planning",
            "implementation_writing",
            "review"
        ]

        for stage_name in expected_stages:
            assert stage_name in STAGE_REGISTRY

    def test_create_pipeline_stage_invalid_name(self):
        """Test creating a stage with an invalid name returns None."""
        # Act
        stage = create_pipeline_stage("nonexistent_stage")

        # Assert
        assert stage is None

    def test_create_requirements_gathering_stage(self, mock_llm_provider):
        """Test creating a requirements gathering stage."""
        # Act
        stage = create_pipeline_stage(
            "requirements_gathering",
            llm_provider=mock_llm_provider
        )

        # Assert
        assert isinstance(stage, RequirementsGatheringStage)
        assert stage.name == "requirements_gathering"
        assert stage.llm_provider == mock_llm_provider

    def test_create_requirements_gathering_stage_missing_dependencies(self):
        """Test creating a requirements gathering stage without required dependencies returns None."""
        # Act
        stage = create_pipeline_stage("requirements_gathering")

        # Assert
        assert stage is None

    def test_create_knowledge_gathering_stage(self, mock_llm_provider,
                                              mock_context_repository,
                                              mock_rag_service):
        """Test creating a knowledge gathering stage."""
        # Act
        stage = create_pipeline_stage(
            "knowledge_gathering",
            llm_provider=mock_llm_provider,
            context_repository=mock_context_repository,
            rag_service=mock_rag_service
        )

        # Assert
        assert isinstance(stage, KnowledgeGatheringStage)
        assert stage.name == "knowledge_gathering"
        assert stage.llm_provider == mock_llm_provider
        assert stage.context_repository == mock_context_repository
        assert stage.rag_service == mock_rag_service

    def test_create_knowledge_gathering_stage_missing_dependencies(self,
                                                                   mock_llm_provider,
                                                                   mock_context_repository):
        """Test creating a knowledge gathering stage without required dependencies returns None."""
        # Act
        stage = create_pipeline_stage(
            "knowledge_gathering",
            llm_provider=mock_llm_provider,
            context_repository=mock_context_repository
        )

        # Assert
        assert stage is None

    def test_create_implementation_planning_stage(self, mock_llm_provider,
                                                  mock_context_repository,
                                                  mock_rag_service):
        """Test creating an implementation planning stage."""
        # Act
        stage = create_pipeline_stage(
            "implementation_planning",
            llm_provider=mock_llm_provider,
            context_repository=mock_context_repository,
            rag_service=mock_rag_service
        )

        # Assert
        assert isinstance(stage, ImplementationPlanningStage)
        assert stage.name == "implementation_planning"
        assert stage.llm_provider == mock_llm_provider
        assert stage.context_repository == mock_context_repository
        assert stage.rag_service == mock_rag_service

    def test_create_implementation_writing_stage(self, mock_llm_provider,
                                                 mock_context_repository,
                                                 mock_rag_service):
        """Test creating an implementation writing stage."""
        # Act
        stage = create_pipeline_stage(
            "implementation_writing",
            llm_provider=mock_llm_provider,
            context_repository=mock_context_repository,
            rag_service=mock_rag_service
        )

        # Assert
        assert isinstance(stage, ImplementationWritingStage)
        assert stage.name == "implementation_writing"
        assert stage.llm_provider == mock_llm_provider
        assert stage.context_repository == mock_context_repository
        assert stage.rag_service == mock_rag_service

    def test_create_review_stage(self, mock_llm_provider, mock_rag_service):
        """Test creating a review stage."""
        # Act
        stage = create_pipeline_stage(
            "review",
            llm_provider=mock_llm_provider,
            rag_service=mock_rag_service
        )

        # Assert
        assert isinstance(stage, ReviewStage)
        assert stage.name == "review"
        assert stage.llm_provider == mock_llm_provider
        assert stage.rag_service == mock_rag_service

    def test_create_review_stage_missing_dependencies(self, mock_llm_provider):
        """Test creating a review stage without required dependencies returns None."""
        # Act
        stage = create_pipeline_stage(
            "review",
            llm_provider=mock_llm_provider
        )

        # Assert
        assert stage is None