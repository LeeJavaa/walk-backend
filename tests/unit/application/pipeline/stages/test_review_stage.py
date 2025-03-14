import pytest
from unittest.mock import Mock, patch, MagicMock

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.code_artifact import CodeArtifact, CodeArtifactType
from src.domain.entities.pipeline_stage import PipelineStageStatus
from src.domain.ports.llm_provider import LLMProvider
from src.application.services.rag_service import RAGService
from src.application.pipeline.stages.review_stage import ReviewStage
from src.application.pipeline.stages.implementation_writing_stage import \
    ImplementationWritingStage
from src.infrastructure.adapters.prompt_utils import create_review_prompt


class TestReviewStage:
    """Unit tests for the ReviewStage."""

    @pytest.fixture
    def llm_provider_mock(self):
        """Mock LLM provider for testing."""
        provider = Mock(spec=LLMProvider)
        provider.generate_text.return_value = """
# Code Review: REST API for Blog Platform

## Correctness
- ✓ The implementation correctly uses Flask for the REST API
- ✓ Authentication is properly implemented with JWT
- ✓ Database models are defined correctly with appropriate relationships
- ✓ CRUD operations for posts are partially implemented
- ✗ Missing implementation for comments API endpoints
- ✗ Missing implementation for updating and deleting posts

## Completeness
- ✓ User registration and login are fully implemented
- ✓ Blog post creation is implemented
- ✗ Only 3 out of 7 required endpoints are implemented
- ✗ Missing error handling for several edge cases
- ✗ No implementation for the comment functionality

## Code Quality
- ✓ Code is well-structured and follows a logical organization
- ✓ Variable naming is clear and consistent
- ✓ PEP 8 style guidelines are generally followed
- ✗ Some functions lack docstrings
- ✗ Error handling could be more comprehensive

## Performance
- ✓ Database queries are straightforward and should perform well for small-to-medium sized loads
- ✗ No pagination implemented for listing posts, which could cause performance issues with large datasets
- ✗ No caching strategy for frequently accessed data

## Security
- ✓ Passwords are properly hashed using Werkzeug's security functions
- ✓ JWT authentication is correctly implemented
- ✓ Input validation is present in the user registration endpoint
- ✗ Missing CSRF protection
- ✗ No rate limiting for authentication endpoints
- ✗ Missing input validation for some endpoints

## Best Practices
- ✓ Separation of concerns between models and routes
- ✓ Use of environment variables for sensitive information
- ✗ No logging setup
- ✗ No configuration for different environments (development, testing, production)
- ✗ Missing unit tests as required in the constraints

## Overall Assessment
The implementation provides a solid foundation for a Flask-based blog API with authentication. It correctly implements the core functionality for user management and post creation. However, it is incomplete, missing several required endpoints and features.

## Key Recommendations
1. Complete the missing CRUD operations for posts and comments
2. Add comprehensive error handling
3. Implement pagination for listing endpoints
4. Add docstrings to all functions
5. Implement the required unit tests
6. Add CSRF protection and rate limiting
7. Set up proper logging
8. Create configuration for different environments
"""
        return provider

    @pytest.fixture
    def rag_service_mock(self):
        """Mock RAG service for testing."""
        service = Mock(spec=RAGService)
        service.generate_with_context.return_value = """
# Review

## Strengths
- Good structure
- Follows requirements

## Weaknesses
- Missing tests
- Incomplete implementation

## Recommendations
1. Add tests
2. Complete all endpoints
"""
        return service

    @pytest.fixture
    def review_stage(self, llm_provider_mock, rag_service_mock):
        """Create a ReviewStage instance with dependencies."""
        return ReviewStage(
            id="test-stage-id",
            name="review",
            llm_provider=llm_provider_mock,
            rag_service=rag_service_mock
        )

    @pytest.fixture
    def sample_code_artifact(self):
        """Sample code artifact for testing."""
        return CodeArtifact(
            id="artifact-id",
            task_id="task-id",
            content="""
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['JWT_SECRET_KEY'] = 'secret-key'

db = SQLAlchemy(app)
jwt = JWTManager(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    new_user = User(username=data['username'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password == data['password']:
        token = create_access_token(identity=user.id)
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

if __name__ == '__main__':
    app.run(debug=True)
""",
            artifact_type=CodeArtifactType.IMPLEMENTATION,
            language="python"
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
            context_ids=[]
        )

    @pytest.fixture
    def sample_pipeline_state(self, sample_task, sample_code_artifact):
        """Sample pipeline state for testing."""
        return PipelineState(
            id="state-id",
            task_id=sample_task.id,
            current_stage="review",
            stages_completed=["requirements_gathering", "knowledge_gathering",
                              "implementation_planning",
                              "implementation_writing"],
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
                                   "Performance optimization"]
                },
                "implementation_planning": {
                    "plan": "1. Set up Flask app\n2. Define database models\n3. Implement authentication\n4. Add CRUD operations",
                    "components": ["Flask application", "Database models",
                                   "Authentication module", "Blog post module"],
                    "steps": ["Set up Flask app", "Define database models",
                              "Implement authentication"]
                },
                "implementation_writing": {
                    "code_artifacts": [sample_code_artifact],
                    "full_response": "Sample full response with code"
                }
            },
            feedback=[]
        )

    def test_initialization(self, review_stage, llm_provider_mock,
                            rag_service_mock):
        """Test stage initialization with dependencies."""
        assert review_stage.id == "test-stage-id"
        assert review_stage.name == "review"
        assert review_stage.llm_provider == llm_provider_mock
        assert review_stage.rag_service == rag_service_mock

    def test_execute_review(self, review_stage, sample_task,
                            sample_pipeline_state, llm_provider_mock):
        """Test executing the review stage."""
        # Act
        result = review_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.stage_id == review_stage.id
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify the LLM was called with the correct prompt
        llm_provider_mock.generate_text.assert_called_once()
        call_args = llm_provider_mock.generate_text.call_args[0][0]
        assert sample_task.description in call_args
        for req in sample_task.requirements:
            assert req in call_args

        # Check the output contains the review analysis
        output = result.output
        assert "review_text" in output
        assert isinstance(output["review_text"], str)
        assert "Code Review" in output["review_text"]

        # Structured review sections
        assert "correctness" in output
        assert isinstance(output["correctness"], dict)
        assert "strengths" in output["correctness"]
        assert "weaknesses" in output["correctness"]

        assert "code_quality" in output
        assert isinstance(output["code_quality"], dict)

        assert "security" in output
        assert isinstance(output["security"], dict)

        assert "recommendations" in output
        assert isinstance(output["recommendations"], list)
        assert len(output["recommendations"]) > 0

    def test_execute_with_rag_service(self, review_stage, sample_task,
                                      sample_pipeline_state, rag_service_mock):
        """Test executing the stage using the RAG service for review."""
        # Arrange - Set up to use the RAG service instead of direct LLM
        review_stage.use_rag = True  # Switch to using RAG

        # Act
        result = review_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify RAG service was called
        rag_service_mock.generate_with_context.assert_called_once()

        # Output should contain review from RAG service
        output = result.output
        assert "review_text" in output
        assert "Strengths" in output["review_text"]
        assert "Weaknesses" in output["review_text"]
        assert "recommendations" in output

    def test_parse_review(self, review_stage):
        """Test parsing review text into structured categories."""
        # Arrange
        review_text = """
## Correctness
- ✓ Good: Feature A works
- ✗ Bad: Feature B is missing

## Code Quality
- ✓ Good: Clean code
- ✗ Bad: Missing documentation

## Security
- ✓ Good: Passwords hashed
- ✗ Bad: No CSRF protection

## Recommendations
1. Add Feature B
2. Add documentation
3. Implement CSRF protection
"""

        # Act
        review_data = review_stage._parse_review(review_text)

        # Assert
        assert "correctness" in review_data
        assert "strengths" in review_data["correctness"]
        assert "weaknesses" in review_data["correctness"]
        assert "Good: Feature A works" in review_data["correctness"][
            "strengths"]
        assert "Bad: Feature B is missing" in review_data["correctness"][
            "weaknesses"]

        assert "code_quality" in review_data
        assert "security" in review_data
        assert "recommendations" in review_data
        assert len(review_data["recommendations"]) == 3
        assert "Add Feature B" in review_data["recommendations"]

    def test_parse_review_alternative_format(self, review_stage):
        """Test parsing review with alternative formatting."""
        # Arrange - Different formatting structure
        review_text = """
# Review Summary

Strengths:
* Code is well-structured
* Authentication works properly

Weaknesses:
* Missing tests
* Incomplete error handling

What to improve:
- Add comprehensive tests
- Complete error handling
- Optimize database queries
"""

        # Act
        review_data = review_stage._parse_review(review_text)

        # Assert
        assert "general" in review_data
        assert "strengths" in review_data["general"]
        assert "weaknesses" in review_data["general"]
        assert "Code is well-structured" in review_data["general"]["strengths"]
        assert "Missing tests" in review_data["general"]["weaknesses"]

        assert "recommendations" in review_data
        assert len(review_data["recommendations"]) >= 3
        assert any(
            "tests" in rec.lower() for rec in review_data["recommendations"])

    def test_validate_transition_from(self, review_stage):
        """Test validation of transitions from previous stages."""
        # Create a mock of the implementation writing stage
        impl_stage = Mock()
        impl_stage.__class__.__name__ = "ImplementationWritingStage"

        # Should allow transitions from ImplementationWritingStage
        assert review_stage.validate_transition_from(impl_stage) is True

        # Should not allow transitions from other stages or None
        other_stage = Mock()
        other_stage.__class__.__name__ = "OtherStage"
        assert review_stage.validate_transition_from(other_stage) is False
        assert review_stage.validate_transition_from(None) is False

    def test_validate_transition_from_name(self, review_stage):
        """Test validation of transitions from previous stage names."""
        # Should allow transitions from implementation_writing
        assert review_stage.validate_transition_from_name(
            "implementation_writing") is True

        # Should not allow transitions from other stage names
        assert review_stage.validate_transition_from_name(
            "implementation_planning") is False
        assert review_stage.validate_transition_from_name("") is False

    def test_get_next_stage_name(self, review_stage):
        """Test getting the name of the next stage."""
        # Review is the last stage, should return empty string
        assert review_stage.get_next_stage_name() == ""

    def test_with_llm_error(self, review_stage, sample_task,
                            sample_pipeline_state):
        """Test behavior when LLM provider encounters an error."""
        # Arrange
        review_stage.llm_provider.generate_text.side_effect = Exception(
            "LLM API error")

        # Act
        result = review_stage.execute(sample_task, sample_pipeline_state)

        # Assert
        assert result.status == PipelineStageStatus.FAILED
        assert "error" in result.output
        assert "LLM API error" in result.error

    def test_with_missing_code_artifacts(self, review_stage, sample_task,
                                         sample_pipeline_state):
        """Test behavior when code artifacts are missing."""
        # Arrange - Remove code artifacts from state
        state = sample_pipeline_state
        state.artifacts["implementation_writing"] = {}  # Empty artifacts

        # Act
        result = review_stage.execute(sample_task, state)

        # Assert
        assert result.status == PipelineStageStatus.FAILED
        assert "error" in result.output
        assert "code artifacts" in result.error.lower()