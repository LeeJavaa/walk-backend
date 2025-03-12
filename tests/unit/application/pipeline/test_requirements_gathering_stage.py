import pytest
from unittest.mock import Mock, patch, MagicMock

from src.domain.entities.task import Task
from src.domain.entities.pipeline_stage import PipelineStageStatus
from src.domain.ports.llm_provider import LLMProvider
from src.application.pipeline.stages.requirements_gathering_stage import \
    RequirementsGatheringStage
from src.infrastructure.adapters.prompt_utils import \
    create_requirements_gathering_prompt


class TestRequirementsGatheringStage:
    """Unit tests for the RequirementsGatheringStage."""

    @pytest.fixture
    def llm_provider_mock(self):
        """Mock LLM provider for testing."""
        provider = Mock(spec=LLMProvider)
        provider.generate_text.return_value = """
Requirements:
- Must implement a REST API with Flask
- Must support user authentication
- Must provide CRUD operations for resources
- Must include proper error handling

Constraints:
- Must use Python 3.9+
- Must follow PEP 8 style guidelines
- Must include comprehensive unit tests
- Must use SQLAlchemy for database operations

Clarifications/Assumptions:
- Authentication will be token-based
- API will return JSON responses
- Database will be PostgreSQL
"""
        return provider

    @pytest.fixture
    def requirements_stage(self, llm_provider_mock):
        """Create a RequirementsGatheringStage instance with dependencies."""
        return RequirementsGatheringStage(
            id="test-stage-id",
            name="requirements_gathering",
            llm_provider=llm_provider_mock
        )

    @pytest.fixture
    def sample_task(self):
        """Sample task for testing."""
        return Task(
            id="task-id",
            description="Create a REST API for a blog platform",
            requirements=["Support user authentication",
                          "CRUD operations for blog posts"],
            constraints=["Use Python 3.9+"]
        )

    def test_initialization(self, requirements_stage, llm_provider_mock):
        """Test stage initialization with dependencies."""
        assert requirements_stage.id == "test-stage-id"
        assert requirements_stage.name == "requirements_gathering"
        assert requirements_stage.llm_provider == llm_provider_mock

    def test_execute_with_minimal_requirements(self, requirements_stage,
                                               sample_task):
        """Test executing the stage with minimal initial requirements."""
        # Act
        result = requirements_stage.execute(sample_task)

        # Assert
        assert result.stage_id == requirements_stage.id
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify the LLM was called with the correct prompt
        requirements_stage.llm_provider.generate_text.assert_called_once()
        call_args = requirements_stage.llm_provider.generate_text.call_args[0][
            0]
        assert sample_task.description in call_args

        # Check that the output contains structured requirements, constraints, and clarifications
        output = result.output
        assert "requirements" in output
        assert isinstance(output["requirements"], list)
        assert len(output["requirements"]) >= 4  # Based on our mock response

        assert "constraints" in output
        assert isinstance(output["constraints"], list)
        assert len(output["constraints"]) >= 3

        assert "clarifications" in output
        assert isinstance(output["clarifications"], list)

    def test_execute_with_existing_requirements(self, requirements_stage,
                                                sample_task):
        """Test executing the stage with existing requirements."""
        # Arrange - Add more requirements and constraints to the task
        sample_task.requirements = ["Support user authentication",
                                    "CRUD operations for blog posts",
                                    "API documentation", "Rate limiting"]
        sample_task.constraints = ["Use Python 3.9+", "Follow REST principles",
                                   "Include Swagger docs"]

        # Act
        result = requirements_stage.execute(sample_task)

        # Assert
        assert result.status == PipelineStageStatus.COMPLETED

        # Verify the LLM was called with the correct prompt that includes existing requirements
        requirements_stage.llm_provider.generate_text.assert_called_once()
        call_args = requirements_stage.llm_provider.generate_text.call_args[0][
            0]
        for req in sample_task.requirements:
            assert req in call_args
        for constraint in sample_task.constraints:
            assert constraint in call_args

    def test_parse_llm_response(self, requirements_stage):
        """Test parsing LLM response into structured requirements, constraints, and clarifications."""
        # Arrange
        llm_response = """
Requirements:
- Requirement 1
- Requirement 2

Constraints:
- Constraint 1
- Constraint 2

Clarifications/Assumptions:
- Clarification 1
- Clarification 2
"""

        # Act
        requirements, constraints, clarifications = requirements_stage._parse_llm_response(
            llm_response)

        # Assert
        assert requirements == ["Requirement 1", "Requirement 2"]
        assert constraints == ["Constraint 1", "Constraint 2"]
        assert clarifications == ["Clarification 1", "Clarification 2"]

    def test_parse_llm_response_alternative_format(self, requirements_stage):
        """Test parsing LLM response with alternative formatting."""
        # Arrange - LLM might return differently formatted response
        llm_response = """
Here are the requirements:
1. Requirement 1
2. Requirement 2

Here are the constraints:
1. Constraint 1
2. Constraint 2

Clarifications:
1. Clarification 1
2. Clarification 2
"""

        # Act
        requirements, constraints, clarifications = requirements_stage._parse_llm_response(
            llm_response)

        # Assert
        assert len(requirements) == 2
        assert "Requirement 1" in requirements
        assert "Requirement 2" in requirements

        assert len(constraints) == 2
        assert "Constraint 1" in constraints
        assert "Constraint 2" in constraints

        assert len(clarifications) == 2
        assert "Clarification 1" in clarifications
        assert "Clarification 2" in clarifications

    def test_validate_transition_from(self, requirements_stage):
        """Test validation of transitions from previous stages."""
        # This is the first stage, so it should only allow transitions from None
        assert requirements_stage.validate_transition_from(None) is True

        # Create a mock of another stage
        other_stage = Mock()
        other_stage.__class__.__name__ = "OtherStage"

        # Should not allow transitions from other stages
        assert requirements_stage.validate_transition_from(other_stage) is False

    def test_validate_transition_from_name(self, requirements_stage):
        """Test validation of transitions from previous stage names."""
        # This is the first stage, so it should only allow transitions from empty string
        assert requirements_stage.validate_transition_from_name("") is True

        # Should not allow transitions from other stage names
        assert requirements_stage.validate_transition_from_name(
            "any_other_stage") is False

    def test_get_next_stage_name(self, requirements_stage):
        """Test getting the name of the next stage."""
        # Should return the next stage in the pipeline sequence
        assert requirements_stage.get_next_stage_name() == "knowledge_gathering"

    def test_with_llm_error(self, requirements_stage, sample_task):
        """Test behavior when LLM provider encounters an error."""
        # Arrange
        requirements_stage.llm_provider.generate_text.side_effect = Exception(
            "LLM API error")

        # Act & Assert
        # The stage should handle the exception and return a failed result
        result = requirements_stage.execute(sample_task)
        assert result.status == PipelineStageStatus.FAILED
        assert "error" in result.output
        assert "LLM API error" in result.error