import pytest
import os
import tempfile
from unittest.mock import patch
from click.testing import CliRunner

from src.infrastructure.cli.main import cli
from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.entities.task import Task, TaskStatus

# Mark the whole file as integration tests
pytestmark = pytest.mark.integration


class TestCliIntegration:
    """Integration tests for the CLI interface."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_file(self):
        """Create a temporary Python file for testing."""
        fd, path = tempfile.mkstemp(suffix=".py")
        with os.fdopen(fd, 'w') as f:
            f.write(
                "# Test Python file\ndef test_function():\n    return 'Hello, world!'")
        yield path
        os.remove(path)

    @pytest.fixture
    def context_repository_mock(self):
        """Mock the context repository."""
        with patch(
                "src.infrastructure.repositories.mongo_context_repository.MongoContextRepository") as mock:
            # Configure mock to return test items when searching
            mock_instance = mock.return_value
            mock_item = ContextItem(
                id="test-id",
                source="test_file.py",
                content="def test():\n    pass",
                content_type=ContentType.PYTHON
            )
            mock_instance.search_by_vector.return_value = [(mock_item, 0.95)]
            mock_instance.list.return_value = [mock_item]

            yield mock_instance

    @pytest.fixture
    def pipeline_repository_mock(self):
        """Mock the pipeline repository."""
        with patch(
                "src.infrastructure.repositories.mongo_pipeline_repository.MongoPipelineRepository") as mock:
            # Configure mock to return test tasks when listing
            mock_instance = mock.return_value
            mock_task = Task(
                id="task-id",
                description="Test task",
                requirements=["req1", "req2"]
            )
            mock_instance.list_tasks.return_value = [mock_task]
            mock_instance.save_task.return_value = mock_task

            yield mock_instance

    def test_cli_help(self, cli_runner):
        """Test the CLI help output (I-CLI-1)."""
        # Act
        result = cli_runner.invoke(cli, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands:" in result.output
        assert "context" in result.output
        assert "task" in result.output
        assert "feedback" in result.output

    def test_context_commands_help(self, cli_runner):
        """Test the context commands help output (I-CLI-1)."""
        # Act
        result = cli_runner.invoke(cli, ["context", "--help"])

        # Assert
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "search" in result.output
        assert "remove" in result.output

    def test_add_context_integration(self, cli_runner, temp_file,
                                     context_repository_mock):
        """Test adding a context item from a file (I-CLI-2)."""
        # Patch the use case factory to use our mock repository
        with patch(
                "src.infrastructure.cli.commands.context_commands.create_add_context_use_case") as mock_factory:
            from src.domain.usecases.context_management import AddContextUseCase

            # Configure the factory to return a use case with our mock repository
            mock_factory.return_value = AddContextUseCase(
                context_repository=context_repository_mock,
                llm_provider=None,
                file_system=None
            )

            # Override execute_from_file_path to avoid calling the real file system and LLM
            AddContextUseCase.execute_from_file_path = lambda self, path: ContextItem(
                id="new-context-id",
                source=path,
                content="# Test content",
                content_type=ContentType.PYTHON
            )

            # Act
            result = cli_runner.invoke(cli,
                                       ["context", "add", "--file", temp_file])

            # Assert
            assert result.exit_code == 0
            assert "Successfully added context" in result.output
            assert "new-context-id" in result.output

    def test_list_contexts_integration(self, cli_runner,
                                       context_repository_mock):
        """Test listing context items (I-CLI-2)."""
        # Patch the use case factory to use our mock repository
        with patch(
                "src.infrastructure.cli.commands.context_commands.create_list_context_use_case") as mock_factory:
            from src.domain.usecases.context_management import \
                ListContextUseCase

            # Configure the factory to return a use case with our mock repository
            mock_factory.return_value = ListContextUseCase(
                context_repository=context_repository_mock
            )

            # Act
            result = cli_runner.invoke(cli, ["context", "list"])

            # Assert
            assert result.exit_code == 0
            assert "test-id" in result.output
            assert "test_file.py" in result.output
            assert "python" in result.output.lower()

    def test_create_task_integration(self, cli_runner,
                                     pipeline_repository_mock):
        """Test creating a task (I-CLI-2)."""
        # Patch the use case factory to use our mock repository
        with patch(
                "src.infrastructure.cli.commands.task_commands.create_pipeline_use_case") as mock_factory:
            from src.domain.usecases.pipeline_management import \
                CreatePipelineUseCase

            # Configure the factory to return a use case with our mock repository
            mock_factory.return_value = CreatePipelineUseCase(
                pipeline_repository=pipeline_repository_mock
            )

            # Act
            result = cli_runner.invoke(cli, [
                "task", "create",
                "--description", "Create a new feature",
                "--requirement", "The feature must do X",
                "--requirement", "The feature must support Y"
            ])

            # Assert
            assert result.exit_code == 0
            assert "Created task" in result.output
            assert "task-id" in result.output

    def test_interactive_feedback_collection(self, cli_runner):
        """Test interactive feedback collection interface (I-CLI-2)."""
        # Patch the use case factory
        with patch(
                "src.infrastructure.cli.commands.feedback_commands.create_submit_feedback_use_case") as mock_factory:
            from src.domain.usecases.feedback_management import \
                SubmitFeedbackUseCase

            # Configure the mock use case
            mock_use_case = SubmitFeedbackUseCase(pipeline_repository=None)
            mock_use_case.execute = lambda pipeline_state_id, stage_name, content, feedback_type: None
            mock_factory.return_value = mock_use_case

            # Act - simulate interactive input
            result = cli_runner.invoke(cli, [
                "feedback", "submit",
                "--pipeline-state-id", "state-id",
                "--stage", "implementation_planning",
                "--interactive"
            ], input="This is feedback provided interactively\n\nsuggestion\n")

            # Assert
            assert result.exit_code == 0
            assert "Enter your feedback" in result.output
            assert "Successfully submitted feedback" in result.output

    def test_error_handling_integration(self, cli_runner):
        """Test error handling in CLI commands (I-CLI-2)."""
        # Test with a non-existent file
        result = cli_runner.invoke(cli, ["context", "add", "--file",
                                         "nonexistent_file.py"])

        # Assert that we get a proper error message
        assert result.exit_code != 0
        assert "Error" in result.output