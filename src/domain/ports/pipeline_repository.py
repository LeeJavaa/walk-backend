from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.task import Task


class PipelineRepository(ABC):
    """
    Port interface for pipeline state and task storage.

    This interface abstracts the persistence mechanism for pipeline-related entities,
    allowing the domain to remain independent of specific storage technologies.
    """

    @abstractmethod
    def save_task(self, task: Task) -> Task:
        """
        Save a task to the repository.

        Args:
            task: The task to save

        Returns:
            The saved task, potentially with updated metadata
        """
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by its ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            The retrieved task, or None if not found
        """
        pass

    @abstractmethod
    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """
        List tasks, optionally filtered by status.

        Args:
            status: Optional status to filter by

        Returns:
            List of tasks matching the status filter
        """
        pass

    @abstractmethod
    def save_pipeline_state(self, state: PipelineState) -> PipelineState:
        """
        Save a pipeline state to the repository.

        Args:
            state: The pipeline state to save

        Returns:
            The saved pipeline state, potentially with updated metadata

        Raises:
            KeyError: If the associated task does not exist
        """
        pass

    @abstractmethod
    def get_pipeline_state(self, state_id: str) -> Optional[PipelineState]:
        """
        Retrieve a pipeline state by its ID.

        Args:
            state_id: ID of the pipeline state to retrieve

        Returns:
            The retrieved pipeline state, or None if not found
        """
        pass

    @abstractmethod
    def get_latest_pipeline_state(self, task_id: str) -> Optional[
        PipelineState]:
        """
        Retrieve the latest pipeline state for a task.

        Args:
            task_id: ID of the task to get the latest state for

        Returns:
            The latest pipeline state for the task, or None if not found
        """
        pass