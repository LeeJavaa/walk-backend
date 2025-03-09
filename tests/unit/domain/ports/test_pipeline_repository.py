import pytest
from abc import ABC
from typing import Dict, Any, List, Optional

from src.domain.ports.pipeline_repository import PipelineRepository
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.task import Task


class TestPipelineRepository:
    """Test cases for the PipelineRepository port."""

    def test_pipeline_repository_interface(self):
        """Test that PipelineRepository defines the expected interface (U-HA-3)."""
        # Verify that PipelineRepository is an abstract base class
        assert issubclass(PipelineRepository, ABC)

        # Check that all required methods are defined
        required_methods = [
            "save_task",
            "get_task",
            "list_tasks",
            "save_pipeline_state",
            "get_pipeline_state",
            "get_latest_pipeline_state",
        ]

        for method_name in required_methods:
            assert hasattr(PipelineRepository,
                           method_name), f"PipelineRepository should define '{method_name}' method"
            method = getattr(PipelineRepository, method_name)
            assert callable(method), f"'{method_name}' should be a method"

    def test_pipeline_repository_independency(self):
        """Test that PipelineRepository has no infrastructure dependencies (U-HA-2)."""
        import inspect

        # Get the source code of the interface
        source = inspect.getsource(PipelineRepository)

        # Check for infrastructure-related terms
        infrastructure_terms = [
            "mongodb",
            "mongo",
            "database",
            "sql",
            "storage",
            "filesystem",
            "file system",
        ]

        for term in infrastructure_terms:
            assert term.lower() not in source.lower(), f"PipelineRepository should not reference '{term}'"

    def test_pipeline_repository_contract(self):
        """Test the contract that implementations of PipelineRepository must adhere to."""

        # A concrete implementation for testing
        class MockPipelineRepository(PipelineRepository):
            def __init__(self):
                self.tasks = {}
                self.states = {}

            def save_task(self, task: Task) -> Task:
                self.tasks[task.id] = task
                return task

            def get_task(self, task_id: str) -> Optional[Task]:
                return self.tasks.get(task_id)

            def list_tasks(self, status: Optional[str] = None) -> List[Task]:
                if status is None:
                    return list(self.tasks.values())

                return [task for task in self.tasks.values() if
                        task.status == status]

            def save_pipeline_state(self,
                                    state: PipelineState) -> PipelineState:
                if state.task_id not in self.tasks:
                    raise KeyError(f"Task with ID {state.task_id} not found")

                self.states[state.id] = state
                return state

            def get_pipeline_state(self, state_id: str) -> Optional[
                PipelineState]:
                return self.states.get(state_id)

            def get_latest_pipeline_state(self, task_id: str) -> Optional[
                PipelineState]:
                task_states = [state for state in self.states.values() if
                               state.task_id == task_id]
                if not task_states:
                    return None

                # Return the state with the latest updated_at timestamp
                return max(task_states, key=lambda state: state.updated_at)

        # Create a mock repository for testing
        repo = MockPipelineRepository()

        # Create a task for testing
        task = Task(
            id="task1",
            description="Test task",
            requirements=["req1", "req2"],
        )

        # Test save_task method
        saved_task = repo.save_task(task)
        assert saved_task.id == task.id

        # Test get_task method
        retrieved_task = repo.get_task("task1")
        assert retrieved_task is not None
        assert retrieved_task.id == "task1"
        assert retrieved_task.description == "Test task"

        # Test list_tasks method
        all_tasks = repo.list_tasks()
        assert len(all_tasks) == 1
        assert all_tasks[0].id == "task1"

        # Create a pipeline state for testing
        pipeline_state = PipelineState(
            id="state1",
            task_id="task1",
            current_stage="requirements_gathering",
            stages_completed=[],
            artifacts={},
            feedback=[],
        )

        # Test save_pipeline_state method
        saved_state = repo.save_pipeline_state(pipeline_state)
        assert saved_state.id == pipeline_state.id

        # Test non-existent task
        with pytest.raises(KeyError):
            repo.save_pipeline_state(PipelineState(
                id="state2",
                task_id="nonexistent",
                current_stage="requirements_gathering",
                stages_completed=[],
                artifacts={},
                feedback=[],
            ))

        # Test get_pipeline_state method
        retrieved_state = repo.get_pipeline_state("state1")
        assert retrieved_state is not None
        assert retrieved_state.id == "state1"
        assert retrieved_state.task_id == "task1"

        # Test get_latest_pipeline_state method
        latest_state = repo.get_latest_pipeline_state("task1")
        assert latest_state is not None
        assert latest_state.id == "state1"

        # Create another state for the same task with a later timestamp
        import time
        time.sleep(0.001)  # Ensure a different timestamp

        pipeline_state2 = PipelineState(
            id="state3",
            task_id="task1",
            current_stage="knowledge_gathering",
            stages_completed=["requirements_gathering"],
            artifacts={
                "requirements_gathering": {"requirements": ["req1", "req2"]}},
            feedback=[],
        )
        repo.save_pipeline_state(pipeline_state2)

        # Test that get_latest_pipeline_state returns the most recent state
        latest_state = repo.get_latest_pipeline_state("task1")
        assert latest_state is not None
        assert latest_state.id == "state3"
        assert latest_state.current_stage == "knowledge_gathering"