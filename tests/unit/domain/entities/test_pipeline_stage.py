import pytest
from uuid import uuid4

from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult, PipelineStageStatus
from src.domain.entities.task import Task


class TestPipelineStage:
    """Test cases for the PipelineStage abstract base class and implementations."""

    def test_pipeline_stage_interface(self):
        """Test the PipelineStage interface (U-PS-1)."""

        # A concrete implementation for testing
        class TestStage(PipelineStage):
            def execute(self, task, state=None):
                return PipelineStageResult(
                    stage_id=self.id,
                    status=PipelineStageStatus.COMPLETED,
                    output={"test": "data"},
                )

            def validate_transition_from(self, previous_stage):
                return True

        # Arrange
        stage_id = str(uuid4())
        stage_name = "test_stage"
        stage = TestStage(stage_id, stage_name)

        # Assert
        assert stage.id == stage_id
        assert stage.name == stage_name
        assert hasattr(stage, "execute")
        assert hasattr(stage, "validate_transition_from")

    def test_stage_execution(self):
        """Test execution of a pipeline stage (U-PS-1)."""

        # A concrete implementation for testing
        class TestStage(PipelineStage):
            def execute(self, task, state=None):
                return PipelineStageResult(
                    stage_id=self.id,
                    status=PipelineStageStatus.COMPLETED,
                    output={"test_key": task.description},
                )

            def validate_transition_from(self, previous_stage):
                return True

        # Arrange
        stage = TestStage(str(uuid4()), "test_stage")
        task = Task(
            id=str(uuid4()),
            description="Test task",
            requirements=["req1", "req2"],
            constraints=["con1", "con2"],
        )

        # Act
        result = stage.execute(task)

        # Assert
        assert result.stage_id == stage.id
        assert result.status == PipelineStageStatus.COMPLETED
        assert result.output == {"test_key": "Test task"}

    def test_pipeline_stage_transition_validation(self):
        """Test validation of transitions between pipeline stages (U-PS-4)."""

        # Define concrete implementations for testing
        class Stage1(PipelineStage):
            def execute(self, task, state=None):
                return PipelineStageResult(
                    stage_id=self.id,
                    status=PipelineStageStatus.COMPLETED,
                    output={},
                )

            def validate_transition_from(self, previous_stage):
                # First stage, no previous stage needed
                return previous_stage is None

        class Stage2(PipelineStage):
            def execute(self, task, state=None):
                return PipelineStageResult(
                    stage_id=self.id,
                    status=PipelineStageStatus.COMPLETED,
                    output={},
                )

            def validate_transition_from(self, previous_stage):
                # Must come after Stage1
                return isinstance(previous_stage, Stage1)

        # Arrange
        stage1 = Stage1(str(uuid4()), "stage1")
        stage2 = Stage2(str(uuid4()), "stage2")
        stage3 = Stage2(str(uuid4()), "another_stage2")

        # Assert
        assert stage1.validate_transition_from(None) is True
        assert stage1.validate_transition_from(stage2) is False
        assert stage2.validate_transition_from(stage1) is True
        assert stage2.validate_transition_from(stage3) is False
        assert stage2.validate_transition_from(None) is False