import pytest
from unittest.mock import Mock, patch

from src.domain.entities.task import Task, TaskStatus
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.pipeline_stage import PipelineStageStatus
from src.domain.entities.code_artifact import CodeArtifact, CodeArtifactType
from src.domain.usecases.pipeline_management import ExecutePipelineStageUseCase
from src.application.pipeline.stage_factory import create_pipeline_stage

# Mark the whole file as integration tests
pytestmark = pytest.mark.integration


class TestPipelineIntegration:
    """Integration tests for the pipeline execution."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider for testing."""
        provider = Mock()

        # Define responses for each stage
        provider.generate_text.side_effect = [
            # Requirements gathering
            """
Requirements:
- Requirement 1
- Requirement 2

Constraints:
- Constraint 1
- Constraint 2

Clarifications/Assumptions:
- Clarification 1
""",
            # Knowledge gathering
            """
Key Concepts and Domain Knowledge:
- Concept 1
- Concept 2

Relevant Libraries and Frameworks:
- Library 1
- Framework 1

Best Practices and Design Patterns:
- Practice 1
- Pattern 1

Potential Challenges:
- Challenge 1
- Challenge 2
""",
            # Implementation planning
            """
# Implementation Plan

## Components
- Component A
- Component B

## Steps
1. Step 1
2. Step 2
""",
            # Implementation writing
            """
```python
def sample_function():
    print("Hello World")
    return True
```
""",
            # Review
            """
## Correctness
- ✓ Code implements the requirements
- ✗ Missing some functionality

## Recommendations
1. Add more test coverage
2. Improve error handling
"""
        ]

        return provider

    @pytest.fixture
    def mock_context_repository(self):
        """Create a mock context repository."""
        repo = Mock()
        repo.get_by_id.return_value = None  # No context items for simplicity
        return repo

    @pytest.fixture
    def mock_rag_service(self):
        """Create a mock RAG service."""
        service = Mock()
        service.retrieve_context.return_value = []  # Return empty context list
        service.generate_with_context.return_value = "Generated with RAG"
        return service

    @pytest.fixture
    def mock_pipeline_repository(self):
        """Create a mock pipeline repository."""
        repo = Mock()

        # Save pipeline state just returns the state object
        repo.save_pipeline_state.side_effect = lambda state: state

        # Store tasks and states for later retrieval
        task_dict = {}
        state_dict = {}

        repo.save_task.side_effect = lambda task: task_dict.setdefault(task.id,
                                                                       task) or task
        repo.get_task.side_effect = lambda task_id: task_dict.get(task_id)

        repo.save_pipeline_state.side_effect = lambda \
            state: state_dict.setdefault(state.id, state) or state
        repo.get_pipeline_state.side_effect = lambda state_id: state_dict.get(
            state_id)

        return repo

    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing."""
        return Task(
            id="test-task-id",
            description="Test task description",
            requirements=["Initial requirement"],
            constraints=["Initial constraint"]
        )

    @pytest.fixture
    def pipeline_state(self, sample_task):
        """Create a pipeline state for testing."""
        return PipelineState(
            id="test-state-id",
            task_id=sample_task.id,
            current_stage="requirements_gathering",
            stages_completed=[],
            artifacts={},
            feedback=[]
        )

    def test_full_pipeline_execution(self, sample_task, pipeline_state,
                                     mock_llm_provider,
                                     mock_pipeline_repository,
                                     mock_context_repository,
                                     mock_rag_service):
        """Test running the full pipeline from start to finish."""
        # Set up the pipeline repository to return our test objects
        mock_pipeline_repository.get_task.return_value = sample_task
        mock_pipeline_repository.get_pipeline_state.return_value = pipeline_state

        # Create execution use case
        execution_use_case = ExecutePipelineStageUseCase(
            pipeline_repository=mock_pipeline_repository
        )

        # Execute each stage in sequence
        current_state = pipeline_state

        # 1. Requirements Gathering Stage
        stage = create_pipeline_stage(
            "requirements_gathering",
            llm_provider=mock_llm_provider
        )
        result = execution_use_case.execute(
            pipeline_state_id=current_state.id,
            stage=stage,
            next_stage_name="knowledge_gathering"
        )

        # Verify stage execution was successful
        assert result.current_stage == "knowledge_gathering"
        assert "requirements_gathering" in result.stages_completed
        assert "requirements_gathering" in result.artifacts
        assert "requirements" in result.artifacts["requirements_gathering"]
        assert len(
            result.artifacts["requirements_gathering"]["requirements"]) > 0

        # Update current state for next stage
        current_state = result

        # 2. Knowledge Gathering Stage
        stage = create_pipeline_stage(
            "knowledge_gathering",
            llm_provider=mock_llm_provider,
            context_repository=mock_context_repository,
            rag_service=mock_rag_service
        )
        result = execution_use_case.execute(
            pipeline_state_id=current_state.id,
            stage=stage,
            next_stage_name="implementation_planning"
        )

        # Verify stage execution was successful
        assert result.current_stage == "implementation_planning"
        assert "knowledge_gathering" in result.stages_completed
        assert "knowledge_gathering" in result.artifacts
        assert "domain_knowledge" in result.artifacts["knowledge_gathering"]
        assert len(
            result.artifacts["knowledge_gathering"]["domain_knowledge"]) > 0

        # Update current state for next stage
        current_state = result

        # 3. Implementation Planning Stage
        stage = create_pipeline_stage(
            "implementation_planning",
            llm_provider=mock_llm_provider,
            context_repository=mock_context_repository,
            rag_service=mock_rag_service
        )
        result = execution_use_case.execute(
            pipeline_state_id=current_state.id,
            stage=stage,
            next_stage_name="implementation_writing"
        )

        # Verify stage execution was successful
        assert result.current_stage == "implementation_writing"
        assert "implementation_planning" in result.stages_completed
        assert "implementation_planning" in result.artifacts
        assert "plan" in result.artifacts["implementation_planning"]
        assert "components" in result.artifacts["implementation_planning"]
        assert len(
            result.artifacts["implementation_planning"]["components"]) > 0

        # Update current state for next stage
        current_state = result

        # 4. Implementation Writing Stage with CodeArtifact serialization
        with patch(
                "src.domain.entities.code_artifact.CodeArtifact.to_dict") as mock_to_dict:
            # Mock the to_dict method to return a dict representation of CodeArtifact
            mock_to_dict.side_effect = lambda: {
                "id": "artifact-id",
                "task_id": "test-task-id",
                "content": "def sample_function():\n    print('Hello World')\n    return True",
                "artifact_type": "implementation",
                "language": "python",
                "path": "sample_function.py"
            }

            stage = create_pipeline_stage(
                "implementation_writing",
                llm_provider=mock_llm_provider,
                context_repository=mock_context_repository,
                rag_service=mock_rag_service
            )

            # Patch CodeArtifact's to_dict method on each object created by the stage
            with patch.object(CodeArtifact, "to_dict") as instance_mock_to_dict:
                instance_mock_to_dict.return_value = {
                    "id": "artifact-id",
                    "task_id": "test-task-id",
                    "content": "def sample_function():\n    print('Hello World')\n    return True",
                    "artifact_type": "implementation",
                    "language": "python",
                    "path": "sample_function.py"
                }

                result = execution_use_case.execute(
                    pipeline_state_id=current_state.id,
                    stage=stage,
                    next_stage_name="review"
                )

        # Verify stage execution was successful
        assert result.current_stage == "review"
        assert "implementation_writing" in result.stages_completed
        assert "implementation_writing" in result.artifacts
        assert "code_artifacts" in result.artifacts["implementation_writing"]
        assert len(
            result.artifacts["implementation_writing"]["code_artifacts"]) > 0

        # Update current state for next stage
        current_state = result

        # 5. Review Stage with CodeArtifact deserialization
        with patch(
                "src.domain.entities.code_artifact.CodeArtifact.from_dict") as mock_from_dict:
            # Mock the from_dict method to return a CodeArtifact object
            artifact = CodeArtifact(
                id="artifact-id",
                task_id="test-task-id",
                content="def sample_function():\n    print('Hello World')\n    return True",
                artifact_type=CodeArtifactType.IMPLEMENTATION,
                language="python"
            )
            mock_from_dict.return_value = artifact

            stage = create_pipeline_stage(
                "review",
                llm_provider=mock_llm_provider,
                rag_service=mock_rag_service
            )

            # Patch the ReviewStage._get_inputs_from_state method to handle dict artifacts
            with patch(
                    "src.application.pipeline.stages.review_stage.ReviewStage._get_inputs_from_state") as mock_get_inputs:
                mock_get_inputs.return_value = (
                    sample_task.requirements,
                    sample_task.constraints,
                    [artifact]  # Return a list with our CodeArtifact object
                )

                result = execution_use_case.execute(
                    pipeline_state_id=current_state.id,
                    stage=stage,
                    next_stage_name=""  # No next stage after review
                )

        # Verify stage execution was successful
        assert "review" in result.stages_completed
        assert "review" in result.artifacts
        assert "recommendations" in result.artifacts["review"]
        assert len(result.artifacts["review"]["recommendations"]) > 0

        # Verify the entire pipeline was completed in sequence
        assert len(result.stages_completed) == 5
        assert result.stages_completed == [
            "requirements_gathering",
            "knowledge_gathering",
            "implementation_planning",
            "implementation_writing",
            "review"
        ]

        # Verify the LLM was called for each stage
        assert mock_llm_provider.generate_text.call_count == 5