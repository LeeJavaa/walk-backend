import pytest
from unittest.mock import Mock, patch
import click
from click.testing import CliRunner

from src.infrastructure.cli.main import cli
from src.infrastructure.cli.commands.context_commands import add_context, \
    list_contexts, remove_context, search_context
from src.infrastructure.cli.commands.task_commands import create_task, \
    list_tasks, execute_task
from src.infrastructure.cli.commands.feedback_commands import submit_feedback


class TestCliInterface:
    """Unit tests for the CLI interface."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_cli_command_group(self):
        """Test that the main CLI command group is properly initialized."""
        # Assert that cli is a Click command group
        assert isinstance(cli, click.Group)

        # Check for expected commands in the group
        command_names = cli.commands.keys()
        assert "context" in command_names
        assert "task" in command_names
        assert "feedback" in command_names

    def test_cli_help_output(self, cli_runner):
        """Test CLI help output includes all commands (U-CLI-1)."""
        # Act
        result = cli_runner.invoke(cli, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "context" in result.output
        assert "task" in result.output
        assert "feedback" in result.output


class TestContextCommands:
    """Unit tests for context management commands."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    @patch("src.infrastructure.cli.commands.context_commands.AddContextUseCase")
    def test_add_context_command(self, mock_use_case, cli_runner):
        """Test add context command (U-CLI-1, U-CLI-2)."""
        # Arrange
        mock_use_case_instance = Mock()
        mock_use_case.return_value = mock_use_case_instance
        mock_use_case_instance.execute_from_file_path.return_value = Mock(
            id="test-id", source="test-file.py")

        # Act
        result = cli_runner.invoke(add_context, ["--file", "test-file.py"])

        # Assert
        assert result.exit_code == 0
        mock_use_case_instance.execute_from_file_path.assert_called_once_with(
            "test-file.py")
        assert "Successfully added context" in result.output
        assert "test-id" in result.output

    @patch(
        "src.infrastructure.cli.commands.context_commands.ListContextUseCase")
    def test_list_contexts_command(self, mock_use_case, cli_runner):
        """Test list contexts command (U-CLI-1, U-CLI-2)."""
        # Arrange
        mock_use_case_instance = Mock()
        mock_use_case.return_value = mock_use_case_instance
        mock_item = Mock(id="test-id", source="test-file.py",
                         content_type="python")
        mock_use_case_instance.execute.return_value = [mock_item]

        # Act
        result = cli_runner.invoke(list_contexts)

        # Assert
        assert result.exit_code == 0
        mock_use_case_instance.execute.assert_called_once()
        assert "test-id" in result.output
        assert "test-file.py" in result.output

    @patch(
        "src.infrastructure.cli.commands.context_commands.RemoveContextUseCase")
    def test_remove_context_command(self, mock_use_case, cli_runner):
        """Test remove context command (U-CLI-1, U-CLI-2)."""
        # Arrange
        mock_use_case_instance = Mock()
        mock_use_case.return_value = mock_use_case_instance
        mock_use_case_instance.execute.return_value = True

        # Act
        result = cli_runner.invoke(remove_context, ["--id", "test-id"])

        # Assert
        assert result.exit_code == 0
        mock_use_case_instance.execute.assert_called_once_with("test-id")
        assert "Successfully removed context" in result.output

    @patch(
        "src.infrastructure.cli.commands.context_commands.SearchContextUseCase")
    def test_search_context_command(self, mock_use_case, cli_runner):
        """Test search context command (U-CLI-1, U-CLI-2)."""
        # Arrange
        mock_use_case_instance = Mock()
        mock_use_case.return_value = mock_use_case_instance
        mock_item = Mock(id="test-id", source="test-file.py",
                         content_type="python")
        mock_use_case_instance.execute.return_value = [(mock_item, 0.95)]

        # Act
        result = cli_runner.invoke(search_context, ["--query", "test query"])

        # Assert
        assert result.exit_code == 0
        mock_use_case_instance.execute.assert_called_once_with("test query", 10)
        assert "test-id" in result.output
        assert "test-file.py" in result.output
        assert "0.95" in result.output


class TestTaskCommands:
    """Unit tests for task management commands."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    @patch("src.infrastructure.cli.commands.task_commands.Task")
    @patch(
        "src.infrastructure.cli.commands.task_commands.CreatePipelineUseCase")
    def test_create_task_command(self, mock_use_case, mock_task, cli_runner):
        """Test create task command (U-CLI-1, U-CLI-2)."""
        # Arrange
        mock_task_instance = Mock(id="task-id", description="Test task")
        mock_task.parse_from_user_input.return_value = mock_task_instance

        mock_use_case_instance = Mock()
        mock_use_case.return_value = mock_use_case_instance
        mock_use_case_instance.execute.return_value = (
        mock_task_instance, Mock(id="state-id"))

        # Act
        result = cli_runner.invoke(create_task, ["--description", "Test task",
                                                 "--requirement", "req1",
                                                 "--requirement", "req2"])

        # Assert
        assert result.exit_code == 0
        mock_task.parse_from_user_input.assert_called()
        mock_use_case_instance.execute.assert_called_once()
        assert "task-id" in result.output
        assert "Test task" in result.output

    @patch("src.infrastructure.cli.commands.task_commands.PipelineRepository")
    def test_list_tasks_command(self, mock_repo, cli_runner):
        """Test list tasks command (U-CLI-1, U-CLI-2)."""
        # Arrange
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        mock_task = Mock(id="task-id", description="Test task",
                         status="pending")
        mock_repo_instance.list_tasks.return_value = [mock_task]

        # Act
        result = cli_runner.invoke(list_tasks)

        # Assert
        assert result.exit_code == 0
        mock_repo_instance.list_tasks.assert_called_once()
        assert "task-id" in result.output
        assert "Test task" in result.output
        assert "pending" in result.output


class TestFeedbackCommands:
    """Unit tests for feedback commands."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    @patch(
        "src.infrastructure.cli.commands.feedback_commands.SubmitFeedbackUseCase")
    def test_submit_feedback_command(self, mock_use_case, cli_runner):
        """Test submit feedback command (U-CLI-1, U-CLI-2)."""
        # Arrange
        mock_use_case_instance = Mock()
        mock_use_case.return_value = mock_use_case_instance
        mock_use_case_instance.execute.return_value = Mock(id="state-id")

        # Act
        result = cli_runner.invoke(submit_feedback, [
            "--pipeline-state-id", "state-id",
            "--stage", "implementation_planning",
            "--content", "This plan needs improvement",
            "--type", "suggestion"
        ])

        # Assert
        assert result.exit_code == 0
        mock_use_case_instance.execute.assert_called_once_with(
            "state-id", "implementation_planning",
            "This plan needs improvement", "suggestion"
        )
        assert "Successfully submitted feedback" in result.output


class TestErrorHandling:
    """Unit tests for CLI error handling."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    @patch("src.infrastructure.cli.commands.context_commands.AddContextUseCase")
    def test_error_handling(self, mock_use_case, cli_runner):
        """Test CLI error handling (U-CLI-3)."""
        # Arrange
        mock_use_case_instance = Mock()
        mock_use_case.return_value = mock_use_case_instance
        mock_use_case_instance.execute_from_file_path.side_effect = FileNotFoundError(
            "File not found")

        # Act
        result = cli_runner.invoke(add_context,
                                   ["--file", "nonexistent-file.py"])

        # Assert
        assert result.exit_code != 0
        assert "Error" in result.output
        assert "File not found" in result.output