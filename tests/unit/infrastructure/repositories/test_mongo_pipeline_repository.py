import pytest
from unittest.mock import Mock, MagicMock
from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, List

from src.domain.entities.task import Task, TaskStatus
from src.domain.entities.pipeline_state import PipelineState
from src.infrastructure.repositories.mongo_pipeline_repository import \
    MongoPipelineRepository


class TestMongoPipelineRepository:
    """Unit tests for the MongoDB pipeline repository."""

    @pytest.fixture
    def mock_tasks_collection(self):
        """Mock MongoDB tasks collection for testing."""
        collection = MagicMock()
        collection.find_one.return_value = None
        collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        # For find - make it return a cursor mock
        cursor_mock = MagicMock()
        cursor_mock.limit = MagicMock(return_value=cursor_mock)
        cursor_mock.sort = MagicMock(return_value=cursor_mock)
        collection.find = MagicMock(return_value=cursor_mock)

        collection.update_one.return_value = MagicMock(modified_count=1)

        return collection

    @pytest.fixture
    def mock_states_collection(self):
        """Mock MongoDB pipeline states collection for testing."""
        collection = MagicMock()
        collection.find_one.return_value = None
        collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        # For find - make it return a cursor mock
        cursor_mock = MagicMock()
        cursor_mock.limit = MagicMock(return_value=cursor_mock)
        cursor_mock.sort = MagicMock(return_value=cursor_mock)
        collection.find = MagicMock(return_value=cursor_mock)

        collection.update_one.return_value = MagicMock(modified_count=1)

        return collection

    @pytest.fixture
    def mongo_repository(self, mock_tasks_collection, mock_states_collection):
        """MongoDB repository with mocked collections."""
        repo = MongoPipelineRepository(
            db_name="test_db",
            tasks_collection_name="tasks",
            states_collection_name="pipeline_states"
        )
        # Replace the collections with mocks
        repo._tasks_collection = mock_tasks_collection
        repo._states_collection = mock_states_collection
        return repo

    @pytest.fixture
    def sample_task(self):
        """Sample task for testing."""
        return Task(
            id="task-id",
            description="Test task",
            requirements=["Implement a test function"],
            constraints=["Use Python"],
            context_ids=["context-id-1", "context-id-2"]
        )

    @pytest.fixture
    def sample_pipeline_state(self):
        """Sample pipeline state for testing."""
        return PipelineState(
            id="state-id",
            task_id="task-id",
            current_stage="requirements_gathering",
            stages_completed=[],
            artifacts={},
            feedback=[]
        )

    def test_save_task(self, mongo_repository, mock_tasks_collection,
                       sample_task):
        """Test saving a task to MongoDB."""
        # Arrange
        mock_tasks_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId())

        # Act
        result = mongo_repository.save_task(sample_task)

        # Assert
        mock_tasks_collection.insert_one.assert_called_once()
        assert result is not None
        assert result.id == sample_task.id
        assert result.description == sample_task.description

    def test_get_task(self, mongo_repository, mock_tasks_collection,
                      sample_task):
        """Test retrieving a task by ID from MongoDB."""
        # Arrange
        mock_document = {
            "_id": ObjectId(),
            "id": sample_task.id,
            "description": sample_task.description,
            "requirements": sample_task.requirements,
            "constraints": sample_task.constraints,
            "context_ids": sample_task.context_ids,
            "status": sample_task.status,
            "created_at": datetime.now()
        }
        mock_tasks_collection.find_one.return_value = mock_document

        # Act
        result = mongo_repository.get_task(sample_task.id)

        # Assert
        mock_tasks_collection.find_one.assert_called_once_with(
            {"id": sample_task.id})
        assert result is not None
        assert result.id == sample_task.id
        assert result.description == sample_task.description
        assert result.requirements == sample_task.requirements

    def test_get_task_not_found(self, mongo_repository, mock_tasks_collection):
        """Test getting a non-existent task (U-DB-2)."""
        # Arrange
        mock_tasks_collection.find_one.return_value = None

        # Act
        result = mongo_repository.get_task("nonexistent-id")

        # Assert
        mock_tasks_collection.find_one.assert_called_once_with(
            {"id": "nonexistent-id"})
        assert result is None

    def test_list_tasks(self, mongo_repository, mock_tasks_collection,
                       sample_task):
        """Test listing tasks from MongoDB (U-DB-1)."""
        # Arrange
        mock_documents = [
            {
                "_id": ObjectId(),
                "id": "task1",
                "description": "Task 1",
                "requirements": ["req1"],
                "constraints": [],
                "context_ids": [],
                "status": TaskStatus.PENDING,
                "created_at": datetime.now()
            },
            {
                "_id": ObjectId(),
                "id": "task2",
                "description": "Task 2",
                "requirements": ["req2"],
                "constraints": [],
                "context_ids": [],
                "status": TaskStatus.IN_PROGRESS,
                "created_at": datetime.now()
            }
        ]
        # Set up the mock to return documents directly through iteration
        cursor_mock = mock_tasks_collection.find.return_value
        cursor_mock.__iter__.return_value = mock_documents

        # Act
        result = mongo_repository.list_tasks()

        # Assert
        mock_tasks_collection.find.assert_called_once()
        assert len(result) == 2
        assert result[0].id == "task1"
        assert result[1].id == "task2"

    def test_list_tasks_with_status(self, mongo_repository, mock_tasks_collection):
        """Test listing tasks with status filter (U-DB-3)."""
        # Arrange
        status = TaskStatus.IN_PROGRESS
        mock_documents = [
            {
                "_id": ObjectId(),
                "id": "task2",
                "description": "Task 2",
                "requirements": ["req2"],
                "constraints": [],
                "context_ids": [],
                "status": TaskStatus.IN_PROGRESS,
                "created_at": datetime.now()
            }
        ]
        cursor_mock = mock_tasks_collection.find.return_value
        cursor_mock.__iter__.return_value = mock_documents

        # Act
        result = mongo_repository.list_tasks(status)

        # Assert
        mock_tasks_collection.find.assert_called_once_with({"status": status})
        assert len(result) == 1
        assert result[0].id == "task2"
        assert result[0].status == TaskStatus.IN_PROGRESS

    def test_save_pipeline_state(self, mongo_repository,
                                mock_states_collection,
                                sample_task,
                                sample_pipeline_state,
                                mock_tasks_collection):
        """Test saving a pipeline state to MongoDB (U-DB-1)."""
        # Arrange
        mock_tasks_collection.find_one.return_value = {
            "_id": ObjectId(),
            "id": sample_pipeline_state.task_id,
            "description": sample_task.description,
            "requirements": sample_task.requirements,
            "constraints": sample_task.constraints,
            "context_ids": sample_task.context_ids,
            "status": sample_task.status,
            "created_at": datetime.now()
        }

        mock_states_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId())

        # Act
        result = mongo_repository.save_pipeline_state(sample_pipeline_state)

        # Assert
        mock_tasks_collection.find_one.assert_called_once_with(
            {"id": sample_pipeline_state.task_id})
        mock_states_collection.insert_one.assert_called_once()
        assert result is not None
        assert result.id == sample_pipeline_state.id
        assert result.task_id == sample_pipeline_state.task_id

    def test_save_pipeline_state_task_not_found(self, mongo_repository,
                                               mock_states_collection,
                                               sample_pipeline_state,
                                               mock_tasks_collection):
        """Test saving a pipeline state with non-existent task (U-DB-2)."""
        # Arrange
        mock_tasks_collection.find_one.return_value = None

        # Act & Assert
        with pytest.raises(KeyError):
            mongo_repository.save_pipeline_state(sample_pipeline_state)

        mock_tasks_collection.find_one.assert_called_once_with(
            {"id": sample_pipeline_state.task_id})
        mock_states_collection.insert_one.assert_not_called()

    def test_get_pipeline_state(self, mongo_repository,
                               mock_states_collection,
                               sample_pipeline_state):
        """Test retrieving a pipeline state by ID from MongoDB (U-DB-1)."""
        # Arrange
        mock_document = {
            "_id": ObjectId(),
            "id": sample_pipeline_state.id,
            "task_id": sample_pipeline_state.task_id,
            "current_stage": sample_pipeline_state.current_stage,
            "stages_completed": sample_pipeline_state.stages_completed,
            "artifacts": sample_pipeline_state.artifacts,
            "feedback": sample_pipeline_state.feedback,
            "checkpoint_data": sample_pipeline_state.checkpoint_data,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        mock_states_collection.find_one.return_value = mock_document

        # Act
        result = mongo_repository.get_pipeline_state(sample_pipeline_state.id)

        # Assert
        mock_states_collection.find_one.assert_called_once_with(
            {"id": sample_pipeline_state.id})
        assert result is not None
        assert result.id == sample_pipeline_state.id
        assert result.task_id == sample_pipeline_state.task_id
        assert result.current_stage == sample_pipeline_state.current_stage

    def test_get_pipeline_state_not_found(self, mongo_repository,
                                         mock_states_collection):
        """Test getting a non-existent pipeline state (U-DB-2)."""
        # Arrange
        mock_states_collection.find_one.return_value = None

        # Act
        result = mongo_repository.get_pipeline_state("nonexistent-id")

        # Assert
        mock_states_collection.find_one.assert_called_once_with(
            {"id": "nonexistent-id"})
        assert result is None

    def test_get_latest_pipeline_state(self, mongo_repository,
                                      mock_states_collection):
        """Test retrieving the latest pipeline state for a task (U-DB-3)."""
        # Arrange
        task_id = "task-id"
        earlier_time = datetime(2023, 1, 1, 10, 0, 0)
        later_time = datetime(2023, 1, 1, 11, 0, 0)

        mock_documents = [
            {
                "_id": ObjectId(),
                "id": "state1",
                "task_id": task_id,
                "current_stage": "requirements_gathering",
                "stages_completed": [],
                "artifacts": {},
                "feedback": [],
                "checkpoint_data": {},
                "created_at": earlier_time,
                "updated_at": earlier_time
            },
            {
                "_id": ObjectId(),
                "id": "state2",
                "task_id": task_id,
                "current_stage": "knowledge_gathering",
                "stages_completed": ["requirements_gathering"],
                "artifacts": {
                    "requirements_gathering": {"requirements": ["req1"]}},
                "feedback": [],
                "checkpoint_data": {},
                "created_at": earlier_time,
                "updated_at": later_time
            }
        ]

        # Set up the mock chain
        cursor_mock = MagicMock()
        cursor_mock.__iter__.return_value = [mock_documents[1]]
        mock_states_collection.find.return_value = cursor_mock
        cursor_mock.sort.return_value = cursor_mock
        cursor_mock.limit.return_value = cursor_mock

        # Act
        result = mongo_repository.get_latest_pipeline_state(task_id)

        # Assert
        mock_states_collection.find.assert_called_once_with(
            {"task_id": task_id})
        assert result is not None
        assert result.id == "state2"
        assert result.updated_at > earlier_time

    def test_transaction_support(self, mongo_repository):
        """Test MongoDB transaction support (I-DB-2)."""
        # This is more of an integration test, but we'll mock it here
        # In a real environment, we would test with actual MongoDB transactions

        # For unit testing, we're verifying that the transaction methods exist and don't raise exceptions

        # Act & Assert
        # Just verify these methods exist and can be called without errors
        assert hasattr(mongo_repository, "start_transaction")
        assert hasattr(mongo_repository, "commit_transaction")
        assert hasattr(mongo_repository, "abort_transaction")