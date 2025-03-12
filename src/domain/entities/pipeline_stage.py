from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import uuid4


class PipelineStageStatus(str, Enum):
    """Enumeration of pipeline stage statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStageResult:
    """Result of a pipeline stage execution."""

    def __init__(
            self,
            stage_id: str,
            status: PipelineStageStatus,
            output: Dict[str, Any],
            error: Optional[str] = None,
            timestamp: Optional[datetime] = None,
    ):
        """
        Initialize a new PipelineStageResult.

        Args:
            stage_id: Identifier of the stage that produced this result
            status: Status of the stage execution
            output: Output data produced by the stage
            error: Error message if the stage failed
            timestamp: Time when the result was produced
        """
        self.stage_id = stage_id
        self.status = status
        self.output = output
        self.error = error
        self.timestamp = timestamp or datetime.now()


class PipelineStage(ABC):
    """
    Abstract base class for pipeline stages.

    A pipeline stage represents a step in the code generation pipeline,
    such as requirements gathering, knowledge gathering, etc.
    """

    def __init__(self, id: str, name: str):
        """
        Initialize a new PipelineStage.

        Args:
            id: Unique identifier for the stage
            name: Name of the stage
        """
        self.id = id
        self.name = name

    @abstractmethod
    def execute(self, task, state=None) -> PipelineStageResult:
        """
        Execute the pipeline stage.

        Args:
            task: The task to be processed
            state: Current pipeline state (optional)

        Returns:
            The result of the stage execution
        """
        pass

    @abstractmethod
    def validate_transition_from(self, previous_stage: Optional[
        "PipelineStage"]) -> bool:
        """
        Validate if this stage can be executed after the given previous stage.

        Args:
            previous_stage: The previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        pass

    @abstractmethod
    def validate_transition_from_name(self, previous_stage_name: Optional[
        str]) -> bool:
        """
        Validate if this stage can be executed after a stage with the given name.

        This allows for validation without requiring a concrete instance of the previous stage.

        Args:
            previous_stage_name: The name of the previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        pass

    @abstractmethod
    def get_next_stage_name(self) -> str:
        """
        Get the name of the next stage in the pipeline.

        Returns:
            Name of the next stage in the pipeline sequence
        """
        pass