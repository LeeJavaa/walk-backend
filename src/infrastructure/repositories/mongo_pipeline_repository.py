import pymongo
from pymongo.errors import DuplicateKeyError, PyMongoError
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from src.domain.entities.task import Task, TaskStatus
from src.domain.entities.pipeline_state import PipelineState
from src.domain.ports.pipeline_repository import PipelineRepository
from src.infrastructure.adapters.mongodb_connection import MongoDBConnection


class MongoPipelineRepository(PipelineRepository):
    """MongoDB implementation of the PipelineRepository interface."""

    def __init__(
            self,
            connection: Optional[MongoDBConnection] = None,
            db_name: Optional[str] = None,
            tasks_collection_name: str = "tasks",
            states_collection_name: str = "pipeline_states"
    ):
        """
        Initialize the MongoDB pipeline repository.

        Args:
            connection: MongoDB connection (optional)
            db_name: Name of the database (optional, if connection is provided)
            tasks_collection_name: Name of the collection for tasks
            states_collection_name: Name of the collection for pipeline states
        """
        self.connection = connection
        self.db_name = db_name
        self.tasks_collection_name = tasks_collection_name
        self.states_collection_name = states_collection_name
        self._tasks_collection = None
        self._states_collection = None
        self.logger = logging.getLogger(__name__)

    def _ensure_connection(self) -> None:
        """Ensure MongoDB connection is established."""
        if self.connection and not self.connection.client:
            self.connection.connect()

        if self._tasks_collection is None or self._states_collection is None:
            if self.connection:
                self._tasks_collection = self.connection.get_collection(
                    self.tasks_collection_name)
                self._states_collection = self.connection.get_collection(
                    self.states_collection_name)
            else:
                # Create a new connection if one wasn't provided
                client = pymongo.MongoClient()
                db = client[self.db_name or "walk"]
                self._tasks_collection = db[self.tasks_collection_name]
                self._states_collection = db[self.states_collection_name]

        # Create indexes if they don't exist
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create necessary indexes in MongoDB collections."""
        try:
            # Tasks collection indexes
            self._tasks_collection.create_index("id", unique=True)
            self._tasks_collection.create_index("status")

            # Pipeline states collection indexes
            self._states_collection.create_index("id", unique=True)
            self._states_collection.create_index("task_id")
            self._states_collection.create_index(
                [("task_id", 1), ("updated_at", -1)])
        except PyMongoError as e:
            self.logger.warning(f"Failed to create indexes: {str(e)}")

    def _task_to_document(self, task: Task) -> Dict[str, Any]:
        """
        Convert a Task entity to a MongoDB document.

        Args:
            task: Task entity to convert

        Returns:
            MongoDB document representation
        """
        return {
            "id": task.id,
            "description": task.description,
            "requirements": task.requirements,
            "constraints": task.constraints,
            "context_ids": task.context_ids,
            "status": task.status,
            "created_at": task.created_at
        }

    def _document_to_task(self, document: Dict[str, Any]) -> Task:
        """
        Convert a MongoDB document to a Task entity.

        Args:
            document: MongoDB document

        Returns:
            Task entity
        """
        if not document:
            return None

        # Handle the ObjectId
        if "_id" in document:
            document.pop("_id")

        # Convert status string to enum if it's a string
        status = document["status"]
        if isinstance(status, str):
            status = TaskStatus(status)

        return Task(
            id=document["id"],
            description=document["description"],
            requirements=document["requirements"],
            constraints=document.get("constraints", []),
            context_ids=document.get("context_ids", []),
            status=status,
            created_at=document.get("created_at")
        )

    def _state_to_document(self, state: PipelineState) -> Dict[str, Any]:
        """
        Convert a PipelineState entity to a MongoDB document.

        Args:
            state: PipelineState entity to convert

        Returns:
            MongoDB document representation
        """
        return {
            "id": state.id,
            "task_id": state.task_id,
            "current_stage": state.current_stage,
            "stages_completed": state.stages_completed,
            "artifacts": state.artifacts,
            "feedback": state.feedback,
            "checkpoint_data": state.checkpoint_data,
            "created_at": state.created_at,
            "updated_at": state.updated_at
        }

    def _document_to_state(self, document: Dict[str, Any]) -> PipelineState:
        """
        Convert a MongoDB document to a PipelineState entity.

        Args:
            document: MongoDB document

        Returns:
            PipelineState entity
        """
        if not document:
            return None

        # Handle the ObjectId
        if "_id" in document:
            document.pop("_id")

        return PipelineState(
            id=document["id"],
            task_id=document["task_id"],
            current_stage=document["current_stage"],
            stages_completed=document["stages_completed"],
            artifacts=document["artifacts"],
            feedback=document["feedback"],
            checkpoint_data=document.get("checkpoint_data", {}),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at")
        )

    def save_task(self, task: Task) -> Task:
        """
        Save a task to the repository.

        This method handles both creation and update operations.

        Args:
            task: The task to save

        Returns:
            The saved task

        Raises:
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            # Convert task to document
            document = self._task_to_document(task)

            # Check if task already exists
            existing = self._tasks_collection.find_one({"id": task.id})

            if existing:
                # Update existing task
                self._tasks_collection.update_one(
                    {"id": task.id},
                    {"$set": document}
                )
            else:
                # Insert new task
                self._tasks_collection.insert_one(document)

            return task

        except PyMongoError as e:
            self.logger.error(f"Failed to save task {task.id}: {str(e)}")
            raise

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            The task, or None if not found

        Raises:
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            document = self._tasks_collection.find_one({"id": task_id})
            return self._document_to_task(document)

        except PyMongoError as e:
            self.logger.error(f"Failed to get task {task_id}: {str(e)}")
            raise

    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """
        List tasks in the repository.

        Args:
            status: Optional status to filter by

        Returns:
            List of tasks matching the criteria

        Raises:
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            # Prepare query
            query = {}
            if status:
                query["status"] = status

            # Execute query
            cursor = self._tasks_collection.find(query)
            documents = list(cursor)

            # Convert to tasks
            return [self._document_to_task(doc) for doc in documents]

        except PyMongoError as e:
            self.logger.error(f"Failed to list tasks: {str(e)}")
            raise

    def save_pipeline_state(self, state: PipelineState) -> PipelineState:
        """
        Save a pipeline state to the repository.

        This method handles both creation and update operations.

        Args:
            state: The pipeline state to save

        Returns:
            The saved pipeline state

        Raises:
            KeyError: If the associated task does not exist
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            # Check if the task exists
            task = self.get_task(state.task_id)
            if not task:
                raise KeyError(f"Task with ID {state.task_id} not found")

            # Ensure updated_at is set
            state.updated_at = datetime.now()

            # Convert state to document
            document = self._state_to_document(state)

            # Check if state already exists
            existing = self._states_collection.find_one({"id": state.id})

            if existing:
                # Update existing state
                self._states_collection.update_one(
                    {"id": state.id},
                    {"$set": document}
                )
            else:
                # Insert new state
                self._states_collection.insert_one(document)

            return state

        except KeyError:
            raise
        except PyMongoError as e:
            self.logger.error(
                f"Failed to save pipeline state {state.id}: {str(e)}")
            raise

    def get_pipeline_state(self, state_id: str) -> Optional[PipelineState]:
        """
        Get a pipeline state by ID.

        Args:
            state_id: ID of the pipeline state to retrieve

        Returns:
            The pipeline state, or None if not found

        Raises:
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            document = self._states_collection.find_one({"id": state_id})
            return self._document_to_state(document)

        except PyMongoError as e:
            self.logger.error(
                f"Failed to get pipeline state {state_id}: {str(e)}")
            raise

    def get_latest_pipeline_state(self, task_id: str) -> Optional[PipelineState]:
        """
        Get the latest pipeline state for a task.

        Args:
            task_id: ID of the task

        Returns:
            The latest pipeline state, or None if not found

        Raises:
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            # Find the latest state for the task based on updated_at timestamp
            cursor = self._states_collection.find({"task_id": task_id}) \
                .sort("updated_at", -1) \
                .limit(1)

            documents = list(cursor)
            if not documents:
                return None

            return self._document_to_state(documents[0])

        except PyMongoError as e:
            self.logger.error(
                f"Failed to get latest pipeline state for task {task_id}: {str(e)}")
            raise

    def start_transaction(self):
        """
        Start a MongoDB transaction.

        Returns:
            A session object for the transaction
        """
        if self.connection:
            return self.connection.start_transaction()
        else:
            raise ValueError("No MongoDB connection available for transactions")

    def commit_transaction(self, session):
        """
        Commit a MongoDB transaction.

        Args:
            session: Session object from start_transaction
        """
        if self.connection:
            self.connection.commit_transaction(session)
        else:
            raise ValueError("No MongoDB connection available for transactions")

    def abort_transaction(self, session):
        """
        Abort a MongoDB transaction.

        Args:
            session: Session object from start_transaction
        """
        if self.connection:
            self.connection.abort_transaction(session)
        else:
            raise ValueError("No MongoDB connection available for transactions")