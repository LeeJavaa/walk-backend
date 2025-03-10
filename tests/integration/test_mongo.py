import asyncio
import os
import pytest
from pymongo.errors import ConnectionFailure
import uuid

from dotenv import load_dotenv

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.task import Task, TaskStatus
from src.domain.entities.pipeline_state import PipelineState
from src.infrastructure.repositories.mongo_context_repository import \
    MongoContextRepository
from src.infrastructure.repositories.mongo_pipeline_repository import \
    MongoPipelineRepository
from src.infrastructure.adapters.mongodb_connection import MongoDBConnection

# Mark the whole file as integration tests
pytestmark = pytest.mark.integration

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection details from environment variables with fallbacks
MONGODB_URI = os.getenv("MONGODB_TEST_URI", "mongodb://localhost:27017")
TEST_DB_NAME = os.getenv("MONGODB_TEST_DB_NAME", "walk_test")


@pytest.fixture(scope="module")
async def mongodb_connection():
    """Create a MongoDB connection for testing."""
    # Use a separate test database
    connection = MongoDBConnection(
        connection_string=MONGODB_URI,
        db_name=TEST_DB_NAME,
    )

    try:
        # Connect to the database
        await connection.connect()

        # Provide the connection
        yield connection

        # Clean up after tests
        db = connection.client[TEST_DB_NAME]
        collections = await db.list_collection_names()
        for collection in collections:
            await db.drop_collection(collection)

        # Close the connection
        await connection.close()
    except (ConnectionFailure, Exception) as e:
        pytest.skip(f"MongoDB server not available: {str(e)}")


@pytest.fixture
async def context_repository(mongodb_connection, request):
    """Create a MongoContextRepository for testing."""
    repo = MongoContextRepository(
        connection=mongodb_connection,
        collection_name="context_items_test",
        vector_collection_name="context_vectors_test"
    )

    async def cleanup():
        # Cleanup after test
        await mongodb_connection.client[mongodb_connection.db_name].drop_collection(
            "context_items_test")
        await mongodb_connection.client[mongodb_connection.db_name].drop_collection(
            "context_vectors_test")

    request.addfinalizer(lambda: asyncio.run(cleanup()))

    return repo  # Return directly, not yield


@pytest.fixture
async def pipeline_repository(mongodb_connection, request):
    """Create a MongoPipelineRepository for testing."""
    repo = MongoPipelineRepository(
        connection=mongodb_connection,
        tasks_collection_name="tasks_test",
        states_collection_name="pipeline_states_test"
    )

    async def cleanup():
        # Drop collections
        await mongodb_connection.client[
            mongodb_connection.db_name].drop_collection("tasks_test")
        await mongodb_connection.client[
            mongodb_connection.db_name].drop_collection(
            "pipeline_states_test")

    request.addfinalizer(lambda: asyncio.run(cleanup()))

    return repo


@pytest.fixture
def sample_context_item():
    """Create a sample context item for testing."""
    return ContextItem(
        id=str(uuid.uuid4()),
        source="test_file.py",
        content="def test_function():\n    return 'Hello, World!'",
        content_type=ContentType.PYTHON,
        metadata={"author": "Test Author"},
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id=str(uuid.uuid4()),
        description="Test task",
        requirements=["Implement a test function"],
        constraints=["Use Python"],
        context_ids=[]
    )


@pytest.fixture
def sample_pipeline_state(sample_task):
    """Create a sample pipeline state for testing."""
    return PipelineState(
        id=str(uuid.uuid4()),
        task_id=sample_task.id,
        current_stage="requirements_gathering",
        stages_completed=[],
        artifacts={},
        feedback=[]
    )


@pytest.mark.asyncio
async def test_context_repository_crud(context_repository, sample_context_item):
    """Test CRUD operations for context items using MongoDB (I-CS-1)."""
    # Add context item
    saved_item = await context_repository.add(sample_context_item)
    assert saved_item is not None
    assert saved_item.id == sample_context_item.id

    # Get context item
    retrieved_item = await context_repository.get_by_id(sample_context_item.id)
    assert retrieved_item is not None
    assert retrieved_item.id == sample_context_item.id
    assert retrieved_item.source == sample_context_item.source
    assert retrieved_item.content == sample_context_item.content

    # Update context item
    retrieved_item.content = "def updated_function():\n    return 'Updated!'"
    updated_item = await context_repository.update(retrieved_item)
    assert updated_item is not None
    assert updated_item.content == "def updated_function():\n    return 'Updated!'"

    # List context items
    items = await context_repository.list()
    assert len(items) == 1
    assert items[0].id == sample_context_item.id

    # Delete context item
    deleted = await context_repository.delete(sample_context_item.id)
    assert deleted is True

    # Verify item is deleted
    items_after_delete = await context_repository.list()
    assert len(items_after_delete) == 0


@pytest.mark.asyncio
async def test_context_repository_filtering(context_repository,
                                            sample_context_item):
    """Test filtering context items (I-CS-2)."""
    # Add context item
    await context_repository.add(sample_context_item)

    # Add another item with different content type
    second_item = ContextItem(
        id=str(uuid.uuid4()),
        source="test_doc.md",
        content="# Test Document",
        content_type=ContentType.MARKDOWN,
        metadata={"author": "Test Author"},
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
    )
    await context_repository.add(second_item)

    # Filter by content type
    python_items = await context_repository.list(
        {"content_type": ContentType.PYTHON})
    assert len(python_items) == 1
    assert python_items[0].content_type == ContentType.PYTHON

    markdown_items = await context_repository.list(
        {"content_type": ContentType.MARKDOWN})
    assert len(markdown_items) == 1
    assert markdown_items[0].content_type == ContentType.MARKDOWN

    # Filter by metadata
    items_by_author = await context_repository.list(
        {"metadata.author": "Test Author"})
    assert len(items_by_author) == 2


@pytest.mark.asyncio
async def test_vector_search(context_repository, sample_context_item):
    """Test vector search functionality (I-CS-3)."""
    # Add multiple context items with different embeddings
    await context_repository.add(sample_context_item)

    # Add items with increasingly different embeddings
    for i in range(3):
        similar_factor = 0.1 * (i + 1)
        item = ContextItem(
            id=str(uuid.uuid4()),
            source=f"test_file_{i}.py",
            content=f"def function_{i}():\n    return '{i}'",
            content_type=ContentType.PYTHON,
            metadata={},
            embedding=[0.1 + similar_factor, 0.2 + similar_factor,
                       0.3 + similar_factor, 0.4 + similar_factor,
                       0.5 + similar_factor]
        )
        await context_repository.add(item)

    # Search with the original vector - should find the original item first
    results = await context_repository.search_by_vector(
        sample_context_item.embedding, limit=2)
    assert len(results) == 2
    # First result should be the original item (or something very close)
    assert results[0][0].id == sample_context_item.id
    # Check that similarity score is included
    assert 0 <= results[0][1] <= 1


@pytest.mark.asyncio
async def test_pipeline_repository_task_operations(pipeline_repository,
                                                   sample_task):
    """Test task operations using MongoDB (I-PS-4)."""
    # Save task
    saved_task = await pipeline_repository.save_task(sample_task)
    assert saved_task is not None
    assert saved_task.id == sample_task.id

    # Get task
    retrieved_task = await pipeline_repository.get_task(sample_task.id)
    assert retrieved_task is not None
    assert retrieved_task.id == sample_task.id
    assert retrieved_task.description == sample_task.description

    # List tasks
    tasks = await pipeline_repository.list_tasks()
    assert len(tasks) == 1
    assert tasks[0].id == sample_task.id

    # Update task status
    retrieved_task.status = TaskStatus.IN_PROGRESS
    updated_task = await pipeline_repository.save_task(retrieved_task)
    assert updated_task.status == TaskStatus.IN_PROGRESS

    # List tasks with status filter
    in_progress_tasks = await pipeline_repository.list_tasks(
        TaskStatus.IN_PROGRESS)
    assert len(in_progress_tasks) == 1
    assert in_progress_tasks[0].id == sample_task.id


@pytest.mark.asyncio
async def test_pipeline_state_operations(pipeline_repository, sample_task,
                                         sample_pipeline_state):
    """Test pipeline state operations using MongoDB (I-PS-4)."""
    # First save the task
    await pipeline_repository.save_task(sample_task)

    # Save pipeline state
    saved_state = await pipeline_repository.save_pipeline_state(
        sample_pipeline_state)
    assert saved_state is not None
    assert saved_state.id == sample_pipeline_state.id

    # Get pipeline state
    retrieved_state = await pipeline_repository.get_pipeline_state(
        sample_pipeline_state.id)
    assert retrieved_state is not None
    assert retrieved_state.id == sample_pipeline_state.id
    assert retrieved_state.task_id == sample_task.id

    # Update pipeline state
    retrieved_state.current_stage = "knowledge_gathering"
    retrieved_state.stages_completed.append("requirements_gathering")
    retrieved_state.artifacts["requirements_gathering"] = {
        "requirements": ["req1", "req2"]}

    updated_state = await pipeline_repository.save_pipeline_state(
        retrieved_state)
    assert updated_state.current_stage == "knowledge_gathering"
    assert "requirements_gathering" in updated_state.stages_completed
    assert "requirements_gathering" in updated_state.artifacts

    # Get latest pipeline state
    latest_state = await pipeline_repository.get_latest_pipeline_state(
        sample_task.id)
    assert latest_state is not None
    assert latest_state.id == sample_pipeline_state.id
    assert latest_state.current_stage == "knowledge_gathering"


@pytest.mark.asyncio
async def test_transaction_support(mongodb_connection):
    """Test MongoDB transaction support (I-DB-2)."""
    # This requires a MongoDB replica set for real transactions
    # For simplicity in our test environment, we'll just check that the methods exist
    # and don't raise exceptions when called

    # Skip the test if MongoDB is not available or doesn't support transactions
    if not hasattr(mongodb_connection, "client"):
        pytest.skip("MongoDB connection not established")

    try:
        session = await mongodb_connection.start_transaction()
        await mongodb_connection.commit_transaction(session)

        session = await mongodb_connection.start_transaction()
        await mongodb_connection.abort_transaction(session)
    except Exception as e:
        if "transactions are not supported" in str(e):
            pytest.skip("MongoDB transactions not supported in this deployment")
        else:
            raise


@pytest.mark.asyncio
async def test_error_handling(mongodb_connection):
    """Test error handling in MongoDB repositories (U-DB-2)."""
    # Create a repository with an invalid collection name
    invalid_repo = MongoContextRepository(
        connection=mongodb_connection,
        collection_name="",  # Invalid name
        vector_collection_name="vectors_test"
    )

    # Attempting operations should handle errors gracefully
    with pytest.raises(Exception):
        await invalid_repo.list()


async def test_repository_hexagonal_architecture_compliance():
    """Test repositories comply with hexagonal architecture (I-HA-1)."""
    # Verify that repositories implement the corresponding interfaces
    from src.domain.ports.context_repository import \
        ContextRepository as ContextRepositoryInterface
    from src.domain.ports.pipeline_repository import \
        PipelineRepository as PipelineRepositoryInterface

    # Check that our implementations satisfy the interface contracts
    assert isinstance(MongoContextRepository, ContextRepositoryInterface)
    assert isinstance(MongoPipelineRepository, PipelineRepositoryInterface)

    # Verify all required methods are implemented
    for method_name in ["add", "get_by_id", "update", "delete", "list",
                        "search_by_vector"]:
        assert hasattr(MongoContextRepository, method_name)
        assert callable(getattr(MongoContextRepository, method_name))

    for method_name in ["save_task", "get_task", "list_tasks",
                        "save_pipeline_state",
                        "get_pipeline_state", "get_latest_pipeline_state"]:
        assert hasattr(MongoPipelineRepository, method_name)
        assert callable(getattr(MongoPipelineRepository, method_name))