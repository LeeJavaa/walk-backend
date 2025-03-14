import pytest
from unittest.mock import Mock, patch, MagicMock

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.pipeline_stage import PipelineStageStatus
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.context_repository import ContextRepository
from src.application.services.rag_service import RAGService
from src.application.services.embedding_service import EmbeddingService
from src.application.pipeline.stages.knowledge_gathering_stage import \
    KnowledgeGatheringStage
from src.application.pipeline.stages.requirements_gathering_stage import \
    RequirementsGatheringStage


class TestKnowledgeGatheringStage:
    """Unit tests for the KnowledgeGatheringStage."""

    @pytest.fixture
    def llm_provider_mock(self):
        """Mock LLM provider for testing."""
        provider = Mock(spec=LLMProvider)
        provider.generate_text.return_value = """
Key Concepts and Domain Knowledge:
- REST API principles and best practices
- Authentication mechanisms (JWT, OAuth)
- CRUD operations and HTTP methods
- Database design and normalization
- Error handling in web applications

Relevant Libraries and Frameworks:
- Flask - lightweight web framework
- SQLAlchemy - ORM for database operations
- Flask-RESTful - extension for building REST APIs
- PyJWT - for JWT token handling
- pytest - for testing

Best Practices and Design Patterns:
- Repository pattern for data access
- Factory pattern for object creation
- Middleware for authentication
- Input validation using schemas
- Error handling middleware

Potential Challenges:
- Security concerns with authentication
- Performance optimization for database queries
- Handling concurrent requests
- Proper error handling and logging
- API versioning strategy
"""
        return provider

    @pytest.fixture
    def context_repository_mock(self):
        """Mock context repository for testing."""
        repo = Mock(spec=ContextRepository)

        # Create sample context items to return
        context_items = [
            ContextItem(
                id="context-1",
                source="flask_example.py",
                content="from flask import Flask\napp = Flask(__name__)\n\n@app.route('/')\ndef hello():\n    return 'Hello World'",
                content_type=ContentType.PYTHON,
                embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
            ),
            ContextItem(
                id="context-2",
                source="auth_example.py",
                content="def create_token(user_id):\n    payload = {'user_id': user_id}\n    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')",
                content_type=ContentType.PYTHON,
                embedding=[0.2, 0.3, 0.4, 0.5, 0.6]
            )
        ]

        # Set up the mock to return these items when searching
        repo.search_by_vector.return_value = [(item, 0.85) for item in
                                              context_items]
        repo.get_by_id.side_effect = lambda id: next(
            (item for item in context_items if item.id == id), None)

        return repo

    @pytest.fixture
    def embedding_service_mock(self):
        """Mock embedding service for testing."""
        service = Mock(spec=EmbeddingService)
        service.generate_embedding_for_text.return_value = [0.1, 0.2, 0.3, 0.4,
                                                            0.5]
        return service

    @pytest.fixture
    def rag_service_mock(self):
        """Mock RAG service for testing."""
        service = Mock(spec=RAGService)
        service.retrieve_context.return_value = [
            ContextItem(
                id="context-1",
                source="flask_example.py",
                content="from flask import Flask\napp = Flask(__name__)",
                content_type=ContentType.PYTHON
            ),
            ContextItem(
                id="context-2",
                source="auth_example.py",
                content="def create_token(user_id):\n    return jwt.encode()",
                content_type=ContentType.PYTHON
            )
        ]
        service.generate_with_context.return_value = "Generated knowledge about REST APIs and Flask"
        return service

    @pytest.fixture
    def knowledge_stage(self, llm_provider_mock, context_repository_mock,
                        rag_service_mock):
        """Create a KnowledgeGatheringStage instance with dependencies."""
        return KnowledgeGatheringStage(
            id="test-stage-id",
            name="knowledge_gathering",
            llm_provider=llm_provider_mock,
            context_repository=context_repository_mock,
            rag_service=rag_service_mock
        )

    @pytest.fixture
    def sample_task(self):
        """Sample task for testing."""
        return Task(
            id="task-id",
            description="Create a REST API for a blog platform",
            requirements=[
                "Must implement a REST API with Flask",
                "Must support user authentication",
                "Must provide CRUD operations for resources",
                "Must include proper error handling"
            ],
            constraints=[
                "Must use Python 3.9+",
                "Must follow PEP 8 style guidelines",
                "Must include comprehensive unit tests",
                "Must use SQLAlchemy for database operations"
            ],
            context_ids=["context-1", "context-2"]
        )

    @pytest.fixture
    def sample_pipeline_state(self, sample_task):
        """Sample pipeline state for testing."""
        return PipelineState(
            id="state-id",
            task_id=sample_task.id,
            current_stage="knowledge_gathering",
            stages_completed=["requirements_gathering"],
            artifacts={
                "requirements_gathering": {
                    "requirements": sample_task.requirements,
                    "constraints": sample_task.constraints,
                    "clarifications": ["Authentication will be token-based"]
                }
            },
            feedback=[]
        )

    def test_initialization(self, knowledge_stage, llm_provider_mock,
                            context_repository_mock, rag_service_mock):
        """Test stage initialization with dependencies."""
        assert knowledge_stage.id == "test-stage-id"
        assert knowledge_stage.name == "knowledge_gathering"
        assert knowledge_stage.llm_provider == llm_provider_mock
        assert knowledge_stage.context_repository == context_repository_mock
        assert knowledge_stage.rag_service == rag_service_mock

    def test_execute_with_context_ids(self, knowledge_stage, sample_task,
                                      sample_pipeline_state,
                                      context_repository_mock):
        """Test executing the stage with existing context IDs."""
        # Act
        result = knowledge_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.stage_id == knowledge_stage.id
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify the context repository was used to retrieve context items
        context_repository_mock.get_by_id.assert_any_call("context-1")
        context_repository_mock.get_by_id.assert_any_call("context-2")

        # Check that the output contains the expected knowledge sections
        output = result.output
        assert "domain_knowledge" in output
        assert "libraries_frameworks" in output
        assert "best_practices" in output
        assert "challenges" in output
        assert "context_items" in output
        assert len(output["context_items"]) == 2  # The IDs from the task

    def test_execute_with_rag_search(self, knowledge_stage, sample_task,
                                     sample_pipeline_state, rag_service_mock):
        """Test executing the stage with RAG search for context."""
        # Arrange - Clear the context IDs to force RAG search
        sample_task.context_ids = []

        # Act
        result = knowledge_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify the RAG service was used to retrieve context
        rag_service_mock.retrieve_context.assert_called_once()
        call_args = rag_service_mock.retrieve_context.call_args[0][0]
        assert sample_task.description in call_args
        for req in sample_task.requirements:
            assert req in call_args

        # Check that the output contains context items from the RAG service
        output = result.output
        assert "context_items" in output
        assert len(output["context_items"]) > 0

    def test_execute_with_llm_analysis(self, knowledge_stage, sample_task,
                                       sample_pipeline_state,
                                       llm_provider_mock):
        """Test executing the stage with LLM analysis of knowledge."""
        # Act
        result = knowledge_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify the LLM was called with the correct prompt
        llm_provider_mock.generate_text.assert_called_once()
        call_args = llm_provider_mock.generate_text.call_args[0][0]
        assert sample_task.description in call_args
        for req in sample_task.requirements:
            assert req in call_args

        # Check that the parsed LLM response is in the output
        output = result.output
        assert len(output["domain_knowledge"]) > 0
        assert len(output["libraries_frameworks"]) > 0
        assert len(output["best_practices"]) > 0
        assert len(output["challenges"]) > 0

    def test_parse_llm_response(self, knowledge_stage):
        """Test parsing LLM response into structured knowledge sections."""
        # Arrange
        llm_response = """
Key Concepts and Domain Knowledge:
- Concept 1
- Concept 2

Relevant Libraries and Frameworks:
- Library 1
- Framework 1

Best Practices and Design Patterns:
- Practice 1
- Pattern 1

Potential Challenges:
- Challenge 1
- Challenge 2
"""

        # Act
        domain_knowledge, libraries, best_practices, challenges = knowledge_stage._parse_llm_response(
            llm_response)

        # Assert
        assert domain_knowledge == ["Concept 1", "Concept 2"]
        assert libraries == ["Library 1", "Framework 1"]
        assert best_practices == ["Practice 1", "Pattern 1"]
        assert challenges == ["Challenge 1", "Challenge 2"]

    def test_parse_llm_response_alternative_format(self, knowledge_stage):
        """Test parsing LLM response with alternative formatting."""
        # Arrange - LLM might return differently formatted response
        llm_response = """
# Domain Knowledge
1. Concept 1
2. Concept 2

# Libraries
* Library 1
* Framework 1

# Best Practices
- Practice 1
- Pattern 1

# Challenges
1) Challenge 1
2) Challenge 2
"""

        # Act
        domain_knowledge, libraries, best_practices, challenges = knowledge_stage._parse_llm_response(
            llm_response)

        # Assert
        assert len(domain_knowledge) == 2
        assert "Concept 1" in domain_knowledge
        assert "Concept 2" in domain_knowledge

        assert len(libraries) == 2
        assert "Library 1" in libraries
        assert "Framework 1" in libraries

        assert len(best_practices) == 2
        assert "Practice 1" in best_practices
        assert "Pattern 1" in best_practices

        assert len(challenges) == 2
        assert "Challenge 1" in challenges
        assert "Challenge 2" in challenges

    def test_validate_transition_from(self, knowledge_stage):
        """Test validation of transitions from previous stages."""
        # Create a mock of the requirements gathering stage
        req_stage = Mock()
        req_stage.__class__.__name__ = "RequirementsGatheringStage"

        # Should allow transitions from RequirementsGatheringStage
        assert knowledge_stage.validate_transition_from(req_stage) is True

        # Should not allow transitions from other stages or None
        other_stage = Mock()
        other_stage.__class__.__name__ = "OtherStage"
        assert knowledge_stage.validate_transition_from(other_stage) is False
        assert knowledge_stage.validate_transition_from(None) is False

    def test_validate_transition_from_name(self, knowledge_stage):
        """Test validation of transitions from previous stage names."""
        # Should allow transitions from requirements_gathering
        assert knowledge_stage.validate_transition_from_name(
            "requirements_gathering") is True

        # Should not allow transitions from other stage names
        assert knowledge_stage.validate_transition_from_name(
            "implementation_planning") is False
        assert knowledge_stage.validate_transition_from_name("") is False

    def test_get_next_stage_name(self, knowledge_stage):
        """Test getting the name of the next stage."""
        assert knowledge_stage.get_next_stage_name() == "implementation_planning"

    def test_with_llm_error(self, knowledge_stage, sample_task,
                            sample_pipeline_state):
        """Test behavior when LLM provider encounters an error."""
        # Arrange
        knowledge_stage.llm_provider.generate_text.side_effect = Exception(
            "LLM API error")

        # Act
        result = knowledge_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.status == PipelineStageStatus.FAILED
        assert "error" in result.output
        assert "LLM API error" in result.error

    def test_with_missing_prior_stage_artifacts(self, knowledge_stage,
                                                sample_task):
        """Test behavior when prior stage artifacts are missing."""
        # Arrange - Create a state without requirements_gathering artifacts
        state = PipelineState(
            id="state-id",
            task_id=sample_task.id,
            current_stage="knowledge_gathering",
            stages_completed=["requirements_gathering"],
            artifacts={},  # Empty artifacts
            feedback=[]
        )

        # Act
        result = knowledge_stage.execute(sample_task, state)

        # Assert - Should use task requirements directly
        assert result.status == PipelineStageStatus.COMPLETED
        # The LLM should be called with the task requirements
        knowledge_stage.llm_provider.generate_text.assert_called_once()