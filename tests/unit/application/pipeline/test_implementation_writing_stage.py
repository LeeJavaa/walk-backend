import pytest
from unittest.mock import Mock, patch, MagicMock

from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.code_artifact import CodeArtifact, CodeArtifactType
from src.domain.entities.pipeline_stage import PipelineStageStatus
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.context_repository import ContextRepository
from src.application.services.rag_service import RAGService
from src.application.pipeline.stages.implementation_writing_stage import \
    ImplementationWritingStage
from src.application.pipeline.stages.implementation_planning_stage import \
    ImplementationPlanningStage
from src.infrastructure.adapters.prompt_utils import \
    create_implementation_writing_prompt


class TestImplementationWritingStage:
    """Unit tests for the ImplementationWritingStage."""

    @pytest.fixture
    def llm_provider_mock(self):
        """Mock LLM provider for testing."""
        provider = Mock(spec=LLMProvider)
        provider.generate_text.return_value = """
```python
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-key-for-testing')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship('BlogPost', backref='author', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'), nullable=False)
    user = db.relationship('User', backref='comments')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Authentication routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()

    # Validate input
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if user already exists
    if User.query.filter_by(username=data['username']).first() or User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Username or email already exists'}), 409

    # Create new user
    new_user = User(username=data['username'], email=data['email'])
    new_user.set_password(data['password'])

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully', 'user_id': new_user.id}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()

    # Validate input
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400

    # Find the user
    user = User.query.filter_by(username=data['username']).first()

    # Check password
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401

    # Generate token
    access_token = create_access_token(identity=user.id)

    return jsonify({'access_token': access_token}), 200

# Blog post routes
@app.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # Validate input
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({'error': 'Missing title or content'}), 400

    # Create new post
    new_post = BlogPost(
        title=data['title'],
        content=data['content'],
        user_id=current_user_id
    )

    db.session.add(new_post)
    db.session.commit()

    return jsonify({'message': 'Post created successfully', 'post_id': new_post.id}), 201

# More routes would be added for listing posts, getting a single post, updating, and deleting...

# Initialize database
@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database initialized.')

if __name__ == '__main__':
    app.run(debug=True)
```

This implementation provides:
1. A Flask REST API with JWT authentication
2. SQLAlchemy models for User, BlogPost, and Comment
3. Routes for registration, login, and creating a blog post
4. Password hashing for security
5. JWT token-based authentication
6. Proper error handling and status codes
7. Basic validation of inputs

The implementation follows the requirements and constraints:
- Uses Flask for the REST API
- Implements user authentication with JWT
- Provides CRUD operations (partially shown)
- Includes error handling
- Uses Python 3.9 syntax
- Follows PEP 8 style guidelines
- Uses SQLAlchemy for database operations

To complete this implementation, you would need to add the remaining CRUD operations for posts and comments, as well as unit tests.
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
```python
def sample_function():
    print("Generated by RAG")
    return True
```
"""
        return service

    @pytest.fixture
    def implementation_stage(self, llm_provider_mock, context_repository_mock,
                             rag_service_mock):
        """Create an ImplementationWritingStage instance with dependencies."""
        return ImplementationWritingStage(
            id="test-stage-id",
            name="implementation_writing",
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
            current_stage="implementation_writing",
            stages_completed=["requirements_gathering", "knowledge_gathering",
                              "implementation_planning"],
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
                },
                "implementation_planning": {
                    "plan": "1. Set up Flask app\n2. Define database models\n3. Implement authentication\n4. Add CRUD operations",
                    "components": ["Flask application", "Database models",
                                   "Authentication module", "Blog post module"],
                    "steps": ["Set up Flask app", "Define database models",
                              "Implement authentication"]
                }
            },
            feedback=[]
        )

    def test_initialization(self, implementation_stage, llm_provider_mock,
                            context_repository_mock, rag_service_mock):
        """Test stage initialization with dependencies."""
        assert implementation_stage.id == "test-stage-id"
        assert implementation_stage.name == "implementation_writing"
        assert implementation_stage.llm_provider == llm_provider_mock
        assert implementation_stage.context_repository == context_repository_mock
        assert implementation_stage.rag_service == rag_service_mock

    def test_execute_stage(self, implementation_stage, sample_task,
                           sample_pipeline_state, llm_provider_mock):
        """Test executing the stage to generate implementation code."""
        # Act
        result = implementation_stage.execute(sample_task,
                                              sample_pipeline_state)

        # Assert
        assert result.stage_id == implementation_stage.id
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify the LLM was called with the correct prompt
        llm_provider_mock.generate_text.assert_called_once()
        call_args = llm_provider_mock.generate_text.call_args[0][0]
        assert sample_task.description in call_args

        # Check the output contains code artifacts
        output = result.output
        assert "code_artifacts" in output
        assert isinstance(output["code_artifacts"], list)
        assert len(output["code_artifacts"]) > 0

        # Verify the code artifact structure
        artifact = output["code_artifacts"][0]
        assert isinstance(artifact, CodeArtifact)
        assert artifact.task_id == sample_task.id
        assert artifact.artifact_type == CodeArtifactType.IMPLEMENTATION
        assert artifact.language == "python"
        assert "Flask" in artifact.content
        assert "BlogPost" in artifact.content

    def test_execute_with_rag_service(self, implementation_stage, sample_task,
                                      sample_pipeline_state, rag_service_mock):
        """Test executing the stage using the RAG service for code generation."""
        # Arrange - Set up to use the RAG service instead of direct LLM
        implementation_stage.use_rag = True  # Switch to using RAG

        # Act
        result = implementation_stage.execute(sample_task,
                                              sample_pipeline_state)

        # Assert
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify RAG service was called with context
        rag_service_mock.generate_with_context.assert_called_once()

        # Output should contain code artifact from RAG service
        output = result.output
        assert "code_artifacts" in output
        assert "Generated by RAG" in output["code_artifacts"][0].content

    def test_extract_code_blocks(self, implementation_stage):
        """Test extracting code blocks from LLM response."""
        # Arrange
        response = """
Here's the implementation:

```python
def test_function():
    return "Hello, World!"
```

And here's another part:

```python
class TestClass:
    def __init__(self):
        self.value = 42
```
"""

        # Act
        code_blocks = implementation_stage._extract_code_blocks(response)

        # Assert
        assert len(code_blocks) == 2
        assert "def test_function()" in code_blocks[0]
        assert "class TestClass:" in code_blocks[1]

    def test_create_code_artifacts(self, implementation_stage, sample_task):
        """Test creating code artifacts from extracted code blocks."""
        # Arrange
        code_blocks = [
            "def function1():\n    return 1",
            "def function2():\n    return 2"
        ]

        # Act
        artifacts = implementation_stage._create_code_artifacts(code_blocks,
                                                                sample_task.id)

        # Assert
        assert len(artifacts) == 2
        assert all(isinstance(a, CodeArtifact) for a in artifacts)
        assert all(a.task_id == sample_task.id for a in artifacts)
        assert all(a.artifact_type == CodeArtifactType.IMPLEMENTATION for a in
                   artifacts)
        assert all(a.language == "python" for a in artifacts)
        assert "function1" in artifacts[0].content
        assert "function2" in artifacts[1].content

    def test_validate_transition_from(self, implementation_stage):
        """Test validation of transitions from previous stages."""
        # Create a mock of the planning stage
        planning_stage = Mock()
        planning_stage.__class__.__name__ = "ImplementationPlanningStage"

        # Should allow transitions from ImplementationPlanningStage
        assert implementation_stage.validate_transition_from(
            planning_stage) is True

        # Should not allow transitions from other stages or None
        other_stage = Mock()
        other_stage.__class__.__name__ = "OtherStage"
        assert implementation_stage.validate_transition_from(
            other_stage) is False
        assert implementation_stage.validate_transition_from(None) is False

    def test_validate_transition_from_name(self, implementation_stage):
        """Test validation of transitions from previous stage names."""
        # Should allow transitions from implementation_planning
        assert implementation_stage.validate_transition_from_name(
            "implementation_planning") is True

        # Should not allow transitions from other stage names
        assert implementation_stage.validate_transition_from_name(
            "knowledge_gathering") is False
        assert implementation_stage.validate_transition_from_name("") is False

    def test_get_next_stage_name(self, implementation_stage):
        """Test getting the name of the next stage."""
        assert implementation_stage.get_next_stage_name() == "review"

    def test_with_llm_error(self, implementation_stage, sample_task,
                            sample_pipeline_state):
        """Test behavior when LLM provider encounters an error."""
        # Arrange
        implementation_stage.llm_provider.generate_text.side_effect = Exception(
            "LLM API error")

        # Act
        result = implementation_stage.execute(sample_task,
                                              sample_pipeline_state)

        # Assert
        assert result.status == PipelineStageStatus.FAILED
        assert "error" in result.output
        assert "LLM API error" in result.error

    def test_with_missing_prior_stage_artifacts(self, implementation_stage,
                                                sample_task):
        """Test behavior when prior stage artifacts are missing."""
        # Arrange - Create a state with minimal artifacts
        state = PipelineState(
            id="state-id",
            task_id=sample_task.id,
            current_stage="implementation_writing",
            stages_completed=["requirements_gathering", "knowledge_gathering",
                              "implementation_planning"],
            artifacts={
                # Missing implementation_planning artifacts
                "requirements_gathering": {
                    "requirements": sample_task.requirements,
                    "constraints": sample_task.constraints
                }
            },
            feedback=[]
        )

        # Act
        result = implementation_stage.execute(sample_task, state)

        # Assert - Should execute normally using task data
        assert result.status == PipelineStageStatus.COMPLETED
        assert "code_artifacts" in result.output