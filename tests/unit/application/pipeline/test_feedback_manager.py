import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.domain.entities.pipeline_state import PipelineState
from src.domain.ports.pipeline_repository import PipelineRepository
from src.application.pipeline.feedback_manager import FeedbackManager


class TestFeedbackManager:
    """Unit tests for FeedbackManager."""

    @pytest.fixture
    def pipeline_repository_mock(self):
        """Create a mock pipeline repository."""
        repo = Mock(spec=PipelineRepository)

        # Configure the mock to return the state it was given to save
        repo.save_pipeline_state.side_effect = lambda state: state

        return repo

    @pytest.fixture
    def feedback_manager(self, pipeline_repository_mock):
        """Create a FeedbackManager with mocked dependencies."""
        return FeedbackManager(pipeline_repository=pipeline_repository_mock)

    @pytest.fixture
    def sample_pipeline_state(self):
        """Create a sample pipeline state for testing."""
        return PipelineState(
            id="state-id",
            task_id="task-id",
            current_stage="implementation_planning",
            stages_completed=["requirements_gathering", "knowledge_gathering"],
            artifacts={
                "requirements_gathering": {"requirements": ["Requirement 1"]},
                "knowledge_gathering": {"domain_knowledge": ["Knowledge 1"]}
            },
            feedback=[]
        )

    def test_submit_feedback(self, feedback_manager, pipeline_repository_mock,
                             sample_pipeline_state):
        """Test submitting feedback on a pipeline stage."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        stage_name = "implementation_planning"
        content = "Consider adding error handling"
        feedback_type = "suggestion"

        # Act
        feedback_id, updated_state = feedback_manager.submit_feedback(
            pipeline_state_id=sample_pipeline_state.id,
            stage_name=stage_name,
            content=content,
            feedback_type=feedback_type
        )

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            sample_pipeline_state.id)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

        # Verify the feedback was added
        assert len(updated_state.feedback) == 1
        assert updated_state.feedback[0]["id"] == feedback_id
        assert updated_state.feedback[0]["stage_name"] == stage_name
        assert updated_state.feedback[0]["content"] == content
        assert updated_state.feedback[0]["type"] == feedback_type
        assert updated_state.feedback[0]["incorporated"] is False
        assert "timestamp" in updated_state.feedback[0]

    def test_submit_feedback_invalid_stage(self, feedback_manager,
                                           pipeline_repository_mock,
                                           sample_pipeline_state):
        """Test submitting feedback for an invalid stage."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state

        # Act & Assert
        with pytest.raises(ValueError):
            feedback_manager.submit_feedback(
                pipeline_state_id=sample_pipeline_state.id,
                stage_name="nonexistent_stage",
                content="Feedback content"
            )

    def test_submit_feedback_state_not_found(self, feedback_manager,
                                             pipeline_repository_mock):
        """Test submitting feedback for a non-existent state."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = None

        # Act & Assert
        with pytest.raises(KeyError):
            feedback_manager.submit_feedback(
                pipeline_state_id="nonexistent-id",
                stage_name="requirements_gathering",
                content="Feedback content"
            )

    def test_incorporate_feedback(self, feedback_manager,
                                  pipeline_repository_mock,
                                  sample_pipeline_state):
        """Test incorporating specific feedback items."""
        # Arrange
        # Add feedback to the state
        state = sample_pipeline_state
        feedback_id_1 = "feedback-1"
        feedback_id_2 = "feedback-2"

        state.feedback = [
            {
                "id": feedback_id_1,
                "stage_name": "implementation_planning",
                "content": "Add more error handling",
                "type": "suggestion",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            },
            {
                "id": feedback_id_2,
                "stage_name": "knowledge_gathering",
                "content": "Consider security implications",
                "type": "correction",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            }
        ]

        pipeline_repository_mock.get_pipeline_state.return_value = state

        # Act
        updated_state = feedback_manager.incorporate_feedback(
            pipeline_state_id=state.id,
            feedback_ids=[feedback_id_1]  # Only incorporate the first feedback
        )

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state.id)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

        # Verify the first feedback was marked as incorporated
        assert updated_state.feedback[0]["incorporated"] is True
        # Verify the second feedback was not incorporated
        assert updated_state.feedback[1]["incorporated"] is False

    def test_incorporate_feedback_not_found(self, feedback_manager,
                                            pipeline_repository_mock,
                                            sample_pipeline_state):
        """Test incorporating non-existent feedback."""
        # Arrange
        # Add feedback to the state
        state = sample_pipeline_state
        state.feedback = [
            {
                "id": "feedback-1",
                "stage_name": "implementation_planning",
                "content": "Add more error handling",
                "type": "suggestion",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            }
        ]

        pipeline_repository_mock.get_pipeline_state.return_value = state

        # Act & Assert
        with pytest.raises(ValueError):
            feedback_manager.incorporate_feedback(
                pipeline_state_id=state.id,
                feedback_ids=["nonexistent-feedback"]
            )

    def test_incorporate_all_feedback(self, feedback_manager,
                                      pipeline_repository_mock,
                                      sample_pipeline_state):
        """Test incorporating all feedback items."""
        # Arrange
        # Add feedback to the state
        state = sample_pipeline_state
        state.feedback = [
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
                "content": "Consider security implications",
                "type": "correction",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            }
        ]

        pipeline_repository_mock.get_pipeline_state.return_value = state

        # Act
        updated_state = feedback_manager.incorporate_all_feedback(
            pipeline_state_id=state.id
        )

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state.id)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

        # Verify all feedback was marked as incorporated
        assert all(
            feedback["incorporated"] for feedback in updated_state.feedback)

    def test_get_feedback(self, feedback_manager, pipeline_repository_mock,
                          sample_pipeline_state):
        """Test getting all feedback items for a pipeline state."""
        # Arrange
        # Add feedback to the state
        state = sample_pipeline_state
        state.feedback = [
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
                "content": "Consider security implications",
                "type": "correction",
                "timestamp": datetime.now().isoformat(),
                "incorporated": True
            }
        ]

        pipeline_repository_mock.get_pipeline_state.return_value = state

        # Act
        feedback_items = feedback_manager.get_feedback(state.id)

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state.id)
        assert len(feedback_items) == 2
        assert feedback_items[0]["id"] == "feedback-1"
        assert feedback_items[1]["id"] == "feedback-2"

    def test_get_feedback_by_stage(self, feedback_manager,
                                   pipeline_repository_mock,
                                   sample_pipeline_state):
        """Test getting feedback items for a specific stage."""
        # Arrange
        # Add feedback to the state
        state = sample_pipeline_state
        state.feedback = [
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
                "content": "Consider security implications",
                "type": "correction",
                "timestamp": datetime.now().isoformat(),
                "incorporated": True
            }
        ]

        pipeline_repository_mock.get_pipeline_state.return_value = state

        # Act
        feedback_items = feedback_manager.get_feedback_by_stage(state.id,
                                                                "implementation_planning")

        # Assert
        pipeline_repository_mock.get_pipeline_state.assert_called_once_with(
            state.id)
        assert len(feedback_items) == 1
        assert feedback_items[0]["id"] == "feedback-1"
        assert feedback_items[0]["stage_name"] == "implementation_planning"

    def test_prioritize_feedback(self, feedback_manager):
        """Test prioritizing feedback based on type."""
        # Arrange
        feedback_items = [
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
                "content": "Critical security issue",
                "type": "correction",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            },
            {
                "id": "feedback-3",
                "stage_name": "implementation_planning",
                "content": "Consider adding feature",
                "type": "enhancement",
                "timestamp": datetime.now().isoformat(),
                "incorporated": False
            }
        ]

        # Act
        prioritized = feedback_manager._prioritize_feedback(feedback_items)

        # Assert
        # The correction should be first, then suggestion, then enhancement
        assert prioritized[0]["id"] == "feedback-2"  # correction
        assert prioritized[1]["id"] == "feedback-1"  # suggestion
        assert prioritized[2]["id"] == "feedback-3"  # enhancement

    def test_transaction_support(self, feedback_manager,
                                 pipeline_repository_mock,
                                 sample_pipeline_state):
        """Test transaction support for feedback operations."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.return_value = sample_pipeline_state
        mock_session = Mock()
        pipeline_repository_mock.start_transaction.return_value = mock_session

        # Act
        with feedback_manager.transaction():
            feedback_id, _ = feedback_manager.submit_feedback(
                pipeline_state_id=sample_pipeline_state.id,
                stage_name="implementation_planning",
                content="Test feedback with transaction"
            )

        # Assert
        pipeline_repository_mock.start_transaction.assert_called_once()
        pipeline_repository_mock.commit_transaction.assert_called_once_with(
            mock_session)
        pipeline_repository_mock.save_pipeline_state.assert_called_once()

    def test_transaction_rollback(self, feedback_manager,
                                  pipeline_repository_mock):
        """Test transaction rollback on error."""
        # Arrange
        pipeline_repository_mock.get_pipeline_state.side_effect = Exception(
            "Test error")
        mock_session = Mock()
        pipeline_repository_mock.start_transaction.return_value = mock_session

        # Act & Assert
        with pytest.raises(Exception):
            with feedback_manager.transaction():
                feedback_manager.submit_feedback(
                    pipeline_state_id="state-id",
                    stage_name="implementation_planning",
                    content="This will fail"
                )

        # Verify
        pipeline_repository_mock.start_transaction.assert_called_once()
        pipeline_repository_mock.abort_transaction.assert_called_once_with(
            mock_session)
        pipeline_repository_mock.commit_transaction.assert_not_called()