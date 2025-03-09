import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.domain.entities.pipeline_state import PipelineState
from src.domain.ports.pipeline_repository import PipelineRepository
from src.domain.usecases.feedback_management import (
    SubmitFeedbackUseCase,
    IncorporateFeedbackUseCase
)


class TestFeedbackManagementUseCases:
    """Test cases for the feedback management use cases."""

    @pytest.fixture
    def pipeline_repository_mock(self):
        """Mock for the pipeline repository."""
        repository = Mock(spec=PipelineRepository)
        return repository

    @pytest.fixture
    def sample_pipeline_state(self):
        """Sample pipeline state for testing."""
        return PipelineState(
            id="state-id",
            task_id="task-id",
            current_stage="implementation_planning",
            stages_completed=["requirements_gathering", "knowledge_gathering"],
            artifacts={
                "requirements_gathering": {
                    "requirements": ["requirement1", "requirement2"]},
                "knowledge_gathering": {
                    "context_items": ["context1", "context2"]}
            },
            feedback=[]
        )

    def test_submit_feedback(self, pipeline_repository_mock,
                             sample_pipeline_state):
        """Test submitting feedback (U-FS-1)."""
        # Arrange
        pipeline_repository_mock.save_pipeline_state.side_effect = lambda \
            state: state

        use_case = SubmitFeedbackUseCase(
            pipeline_repository=pipeline_repository_mock)
        state_id = "state-id"
        stage_name = "implementation_planning"
        feedback_content = "This plan needs more detail about error handling."
        feedback_type = "suggestion"

        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Act
        result = use_case.execute(
            pipeline_state_id=state_id,
            stage_name=stage_name,
            content=feedback_content,
            feedback_type=feedback_type
        )

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state_id)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()
        assert result is not None
        assert len(result.feedback) == 1
        assert result.feedback[0]["stage_name"] == stage_name
        assert result.feedback[0]["content"] == feedback_content
        assert result.feedback[0]["type"] == feedback_type
        assert "timestamp" in result.feedback[0]

    def test_submit_feedback_invalid_stage(self, pipeline_repository_mock,
                                           sample_pipeline_state):
        """Test submitting feedback for an invalid stage (U-FS-2)."""
        # Arrange
        use_case = SubmitFeedbackUseCase(
            pipeline_repository=pipeline_repository_mock)
        state_id = "state-id"
        stage_name = "nonexistent_stage"
        feedback_content = "This is feedback."

        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Act & Assert
        with pytest.raises(ValueError):
            use_case.execute(state_id, stage_name, feedback_content)

        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state_id)
        pipeline_repository_mock.save_pipeline_state.assert_not_called()

    def test_incorporate_feedback(self, pipeline_repository_mock,
                                  sample_pipeline_state):
        """Test incorporating feedback into the pipeline (U-FS-3)."""
        # Arrange
        pipeline_repository_mock.save_pipeline_state.side_effect = lambda \
                state: state

        use_case = IncorporateFeedbackUseCase(
            pipeline_repository=pipeline_repository_mock)
        state_id = "state-id"

        # Add feedback to the state
        sample_pipeline_state.feedback = [
            {
                "id": "feedback-1",
                "stage_name": "implementation_planning",
                "content": "Add more error handling",
                "type": "suggestion",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            },
            {
                "id": "feedback-2",
                "stage_name": "knowledge_gathering",
                "content": "Include database knowledge",
                "type": "correction",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            }
        ]

        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Act
        result = use_case.execute(
            pipeline_state_id=state_id,
            feedback_ids=["feedback-1"]
        )

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state_id)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()
        assert result is not None
        assert result.feedback[0]["incorporated"] is True
        assert result.feedback[1]["incorporated"] is False

    def test_incorporate_feedback_with_prioritization(self,
                                                      pipeline_repository_mock,
                                                      sample_pipeline_state):
        """Test incorporating feedback with prioritization (U-FS-3)."""
        # Arrange
        pipeline_repository_mock.save_pipeline_state.side_effect = lambda \
                state: state

        use_case = IncorporateFeedbackUseCase(
            pipeline_repository=pipeline_repository_mock)
        state_id = "state-id"

        # Add feedback with different types to the state
        sample_pipeline_state.feedback = [
            {
                "id": "feedback-1",
                "stage_name": "implementation_planning",
                "content": "Suggestion for improvement",
                "type": "suggestion",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            },
            {
                "id": "feedback-2",
                "stage_name": "implementation_planning",
                "content": "Critical error in design",
                "type": "correction",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            },
            {
                "id": "feedback-3",
                "stage_name": "implementation_planning",
                "content": "Optional enhancement",
                "type": "enhancement",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            }
        ]

        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Act
        result = use_case.execute_prioritized(pipeline_state_id=state_id)

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state_id)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

        # Verify that all feedback was incorporated
        assert all(feedback["incorporated"] for feedback in result.feedback)

        # Verify prioritization - corrections should be first, then suggestions, then enhancements
        prioritized_feedback = use_case._prioritize_feedback(
            sample_pipeline_state.feedback)
        assert prioritized_feedback[0]["type"] == "correction"
        assert prioritized_feedback[1]["type"] == "suggestion"
        assert prioritized_feedback[2]["type"] == "enhancement"