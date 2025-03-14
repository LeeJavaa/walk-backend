import pytest
from unittest.mock import Mock, patch, MagicMock

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.pipeline_stage import PipelineStageStatus
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.context_repository import ContextRepository
from src.application.services.rag_service import RAGService
from src.application.pipeline.stages.implementation_planning_stage import \
    ImplementationPlanningStage
from src.application.pipeline.stages.knowledge_gathering_stage import \
    KnowledgeGatheringStage
from src.infrastructure.adapters.prompt_utils import \
    create_implementation_planning_prompt


class TestImplementationPlanningStage:
    """Unit tests for the ImplementationPlanningStage."""

    @pytest.fixture
    def llm_provider_mock(self):
        """Mock LLM provider for testing."""
        provider = Mock(spec=LLMProvider)
        provider.generate_text.return_value = """
# Implementation Plan for REST API Blog Platform

## Components
1. Authentication Module
2. Blog Post Module
3. Comment Module
4. User Module
5. Database Models

## Detailed Steps

### 1. Project Setup
- Initialize Flask application
- Set up SQLAlchemy integration
- Configure JWT authentication
- Implement error handling middleware

### 2. Database Models
- Define User model
- Define BlogPost model
- Define Comment model
- Define relationships between models

### 3. Authentication Endpoints
- Implement user registration
- Implement login and token issuance
- Implement token validation middleware
- Implement password reset functionality

### 4. Blog Post Endpoints
- Implement create post endpoint
- Implement retrieve posts (list, detail) endpoints
- Implement update post endpoint
- Implement delete post endpoint

### 5. Comment Endpoints
- Implement add comment endpoint
- Implement retrieve comments endpoint
- Implement update/delete comment endpoints

### 6. Testing
- Write unit tests for each module
- Write integration tests for API endpoints
- Implement test fixtures and helpers

### 7. Documentation
- Generate OpenAPI specification
- Add docstrings to all functions
- Create README with setup instructions

## Implementation Order
1. Project setup and database models
2. Authentication module
3. Blog post module
4. Comment module
5. Testing
6. Documentation
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
                content_type=ContentType.PYTHON
            ),
            ContextItem(
                id="context-2",
                source="auth_example.py",
                content="def create_token(user_id):\n    payload = {'user_id': user_id}\n    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')",
                content_type=ContentType.PYTHON
            )
        ]

        # Set up the mock to return these items when requested by ID
        repo.get_by_id.side_effect = lambda id: next(
            (item for item in context_items if item.id == id), None)

        return repo

    @pytest.fixture
    def rag_service_mock(self):
        """Mock RAG service for testing."""
        service = Mock(spec=RAGService)
        service.generate_with_context.return_value = """
# Implementation Plan

## Components
1. Component A
2. Component B

## Steps
1. Step 1
2. Step 2

## Architecture
- Layer 1
- Layer 2
"""
        return service

    @pytest.fixture
    def planning_stage(self, llm_provider_mock, context_repository_mock,
                       rag_service_mock):
        """Create an ImplementationPlanningStage instance with dependencies."""
        return ImplementationPlanningStage(
            id="test-stage-id",
            name="implementation_planning",
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
            current_stage="implementation_planning",
            stages_completed=["requirements_gathering", "knowledge_gathering"],
            artifacts={
                "requirements_gathering": {
                    "requirements": sample_task.requirements,
                    "constraints": sample_task.constraints,
                    "clarifications": ["Authentication will be token-based"]
                },
                "knowledge_gathering": {
                    "domain_knowledge": ["REST API principles",
                                         "Authentication mechanisms"],
                    "libraries_frameworks": ["Flask", "SQLAlchemy", "PyJWT"],
                    "best_practices": ["Repository pattern",
                                       "Input validation"],
                    "challenges": ["Security concerns",
                                   "Performance optimization"],
                    "context_items": ["context-1", "context-2"]
                }
            },
            feedback=[]
        )

    def test_initialization(self, planning_stage, llm_provider_mock,
                            context_repository_mock, rag_service_mock):
        """Test stage initialization with dependencies."""
        assert planning_stage.id == "test-stage-id"
        assert planning_stage.name == "implementation_planning"
        assert planning_stage.llm_provider == llm_provider_mock
        assert planning_stage.context_repository == context_repository_mock
        assert planning_stage.rag_service == rag_service_mock

    def test_execute_with_existing_context(self, planning_stage, sample_task,
                                           sample_pipeline_state,
                                           context_repository_mock):
        """Test executing the stage with existing context items from previous stage."""
        # Act
        result = planning_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.stage_id == planning_stage.id
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify context repository was used to retrieve context items
        context_repository_mock.get_by_id.assert_any_call("context-1")
        context_repository_mock.get_by_id.assert_any_call("context-2")

        # Check the output contains the implementation plan
        output = result.output
        assert "plan" in output
        assert isinstance(output["plan"], str)
        assert "Components" in output["plan"]
        assert "Authentication Module" in output["plan"]

        # Check that components and steps were extracted
        assert "components" in output
        assert isinstance(output["components"], list)
        assert len(output["components"]) > 0

        assert "steps" in output
        assert isinstance(output["steps"], list)
        assert len(output["steps"]) > 0

    def test_execute_with_rag_service(self, planning_stage, sample_task,
                                      sample_pipeline_state, rag_service_mock):
        """Test executing the stage using the RAG service for planning."""
        # Arrange - Set up to use the RAG service instead of direct LLM
        planning_stage.use_rag = True  # Switch to using RAG

        # Act
        result = planning_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify RAG service was called with context
        rag_service_mock.generate_with_context.assert_called_once()

        # Output should contain plan from RAG service
        assert "plan" in result.output
        assert "Components" in result.output["plan"]
        assert "components" in result.output
        assert "steps" in result.output

    def test_parse_implementation_plan(self, planning_stage):
        """Test parsing implementation plan into structured components."""
        # Arrange
        plan_text = """
# Implementation Plan

## Components
- Component A
- Component B

## Steps
1. Step 1
2. Step 2

## Architecture
- Layer 1
- Layer 2
"""

        # Act
        components, steps = planning_stage._parse_implementation_plan(plan_text)

        # Assert
        assert components == ["Component A", "Component B"]
        assert steps == ["Step 1", "Step 2"]

    def test_parse_implementation_plan_alternative_format(self, planning_stage):
        """Test parsing implementation plan with alternative formatting."""
        # Arrange - Different formatting structure
        plan_text = """
Implementation Plan:

1. Component A
   - Step A1
   - Step A2
2. Component B
   - Step B1
   - Step B2

Sequential Steps:
* First do X
* Then do Y
* Finally do Z
"""

        # Act
        components, steps = planning_stage._parse_implementation_plan(plan_text)

        # Assert
        assert len(components) >= 2
        assert "Component A" in components
        assert "Component B" in components

        assert len(steps) >= 3
        assert "First do X" in steps or "do X" in steps
        assert "Then do Y" in steps or "do Y" in steps
        assert "Finally do Z" in steps or "do Z" in steps

    def test_validate_transition_from(self, planning_stage):
        """Test validation of transitions from previous stages."""
        # Create a mock of the knowledge gathering stage
        knowledge_stage = Mock()
        knowledge_stage.__class__.__name__ = "KnowledgeGatheringStage"

        # Should allow transitions from KnowledgeGatheringStage
        assert planning_stage.validate_transition_from(knowledge_stage) is True

        # Should not allow transitions from other stages or None
        other_stage = Mock()
        other_stage.__class__.__name__ = "OtherStage"
        assert planning_stage.validate_transition_from(other_stage) is False
        assert planning_stage.validate_transition_from(None) is False

    def test_validate_transition_from_name(self, planning_stage):
        """Test validation of transitions from previous stage names."""
        # Should allow transitions from knowledge_gathering
        assert planning_stage.validate_transition_from_name(
            "knowledge_gathering") is True

        # Should not allow transitions from other stage names
        assert planning_stage.validate_transition_from_name(
            "requirements_gathering") is False
        assert planning_stage.validate_transition_from_name("") is False

    def test_get_next_stage_name(self, planning_stage):
        """Test getting the name of the next stage."""
        assert planning_stage.get_next_stage_name() == "implementation_writing"

    def test_with_llm_error(self, planning_stage, sample_task,
                            sample_pipeline_state):
        """Test behavior when LLM provider encounters an error."""
        # Arrange
        planning_stage.llm_provider.generate_text.side_effect = Exception(
            "LLM API error")

        # Act
        result = planning_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.status == PipelineStageStatus.FAILED
        assert "error" in result.output
        assert "LLM API error" in result.error

    def test_with_missing_prior_stage_artifacts(self, planning_stage,
                                                sample_task):
        """Test behavior when prior stage artifacts are missing."""
        # Arrange - Create a state with minimal artifacts
        state = PipelineState(
            id="state-id",
            task_id=sample_task.id,
            current_stage="implementation_planning",
            stages_completed=["requirements_gathering", "knowledge_gathering"],
            artifacts={
                # Missing the knowledge_gathering artifacts
                "requirements_gathering": {
                    "requirements": sample_task.requirements,
                    "constraints": sample_task.constraints
                }
            },
            feedback=[]
        )

        # Act
        result = planning_stage.execute(sample_task, state)

        # Assert - Should execute normally using task data
        assert result.status == PipelineStageStatus.COMPLETED
        assert "plan" in result.output