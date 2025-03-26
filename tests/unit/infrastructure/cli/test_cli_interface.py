# ALL OF THIS SHOULD ACTUALLY BE AN INTEGRATION TEST AND NOT UNIT TESTS!!!
# UPDATE IN FUTURE.



# import pytest
# from datetime import datetime
# from unittest.mock import Mock, patch
# import click
# from click.testing import CliRunner
#
# from src.domain.entities.task import Task
# from src.domain.entities.context_item import ContextItem, ContentType
# from src.domain.entities.container import Container, ContainerType
# from src.infrastructure.cli.main import cli
# from src.infrastructure.cli.commands.context_commands import add_context, \
#     list_contexts, remove_context, search_context, add_directory, create_container, \
#     list_containers
# from src.infrastructure.cli.commands.task_commands import create_task, \
#     list_tasks, execute_task
# from src.infrastructure.cli.commands.feedback_commands import submit_feedback
#
#
# class TestCliInterface:
#     """Unit tests for the CLI interface."""
#
#     @pytest.fixture
#     def cli_runner(self):
#         """Create a Click CLI test runner."""
#         return CliRunner()
#
#     def test_cli_command_group(self):
#         """Test that the main CLI command group is properly initialized."""
#         # Assert that cli is a Click command group
#         assert isinstance(cli, click.Group)
#
#         # Check for expected commands in the group
#         command_names = cli.commands.keys()
#         assert "context" in command_names
#         assert "task" in command_names
#         assert "feedback" in command_names
#
#     def test_cli_help_output(self, cli_runner):
#         """Test CLI help output includes all commands (U-CLI-1)."""
#         # Act
#         result = cli_runner.invoke(cli, ["--help"])
#
#         # Assert
#         assert result.exit_code == 0
#         assert "context" in result.output
#         assert "task" in result.output
#         assert "feedback" in result.output
#
#
# class TestContextCommands:
#     """Unit tests for context management commands."""
#
#     @pytest.fixture
#     def cli_runner(self):
#         """Create a Click CLI test runner."""
#         return CliRunner()
#
#     @patch("src.infrastructure.cli.commands.context_commands.create_add_context_use_case")
#     def test_add_context_command(self, mock_use_case, cli_runner):
#         """Test add context command (U-CLI-1, U-CLI-2)."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_use_case_instance.execute_from_file_path.return_value = Mock(
#             id="test-id", source="test-file.py")
#
#         # Act
#         result = cli_runner.invoke(add_context, ["--file", "test-file.py"])
#
#         # Assert
#         assert result.exit_code == 0
#         mock_use_case_instance.execute_from_file_path.assert_called_once_with(
#             "test-file.py",
#             container_id=None,
#             is_container_root=False
#         )
#         assert "Successfully added context" in result.output
#         assert "test-id" in result.output
#
#     @patch(
#         "src.infrastructure.cli.commands.context_commands.create_list_context_use_case")
#     def test_list_contexts_command(self, mock_use_case, cli_runner):
#         """Test list contexts command (U-CLI-1, U-CLI-2)."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_item = ContextItem(
#             id="test-id",
#             source="test-file.py",
#             content="test content",
#             content_type=ContentType.PYTHON,
#             created_at=datetime.now()
#         )
#         mock_use_case_instance.execute.return_value = [mock_item]
#
#         # Act
#         result = cli_runner.invoke(list_contexts)
#
#         # Assert
#         assert result.exit_code == 0
#         mock_use_case_instance.execute.assert_called_once()
#         assert "test-id" in result.output
#         assert "test-file.py" in result.output
#
#     @patch(
#         "src.infrastructure.cli.commands.context_commands.create_remove_context_use_case")
#     def test_remove_context_command(self, mock_use_case, cli_runner):
#         """Test remove context command (U-CLI-1, U-CLI-2)."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_use_case_instance.execute.return_value = True
#
#         # Act
#         result = cli_runner.invoke(remove_context, ["--id", "test-id"])
#
#         # Assert
#         assert result.exit_code == 0
#         mock_use_case_instance.execute.assert_called_once_with("test-id")
#         assert "Successfully removed context" in result.output
#
#     @patch(
#         "src.infrastructure.cli.commands.context_commands.create_search_context_use_case")
#     def test_search_context_command(self, mock_use_case, cli_runner):
#         """Test search context command (U-CLI-1, U-CLI-2)."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_item = ContextItem(
#             id="test-id",
#             source="test-file.py",
#             content="test content",
#             content_type=ContentType.PYTHON,
#             created_at=datetime.now()
#         )
#         mock_use_case_instance.execute.return_value = [(mock_item, 0.95)]
#
#         # Act
#         result = cli_runner.invoke(search_context, ["--query", "test query"])
#
#         # Assert
#         assert result.exit_code == 0
#         mock_use_case_instance.execute.assert_called_once_with("test query", 10)
#         assert "test-id" in result.output
#         assert "test-file.py" in result.output
#         assert "0.95" in result.output
#
#     @patch(
#         "src.infrastructure.cli.commands.context_commands.create_add_directory_use_case")
#     def test_context_add_directory_command(self, mock_use_case, cli_runner):
#         """Test adding a directory to the context system."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#
#         # Mock container
#         mock_container = Mock(id="container-id", name="test-container",
#                               title="Test Container")
#
#         # Mock processed files
#         mock_items = [
#             Mock(id="item1-id", source="dir/file1.py"),
#             Mock(id="item2-id", source="dir/file2.py")
#         ]
#
#         # Mock result from the use case
#         mock_use_case_instance.execute.return_value = {
#             "container": mock_container,
#             "context_items": mock_items,
#             "total_files": len(mock_items)
#         }
#
#         # Act
#         result = cli_runner.invoke(add_directory, [
#             "--directory", "/test/dir",
#             "--depth", "5",
#             "--title", "Test Directory"
#         ])
#
#         # Assert
#         assert result.exit_code == 0
#         mock_use_case_instance.execute.assert_called_once_with(
#             directory_path="/test/dir",
#             max_depth=5,
#             container_title="Test Directory",
#             file_types=None,
#             container_id=None,
#             container_type="code",
#             container_description="",
#             container_priority=5
#         )
#         assert "Successfully added directory" in result.output
#         assert "container-id" in result.output
#         assert "2 files" in result.output
#
#     @patch(
#         "src.infrastructure.cli.commands.context_commands.create_create_container_use_case")
#     def test_create_container_command(self, mock_use_case, cli_runner):
#         """Test creating a container."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_container = Container(
#             id="container-id",
#             name="test-container",
#             title="Test Container",
#             container_type=ContainerType("code"),
#             description="Test description",
#             source_path="/path/to/source"
#         )
#         mock_use_case_instance.execute.return_value = mock_container
#
#         # Act
#         result = cli_runner.invoke(create_container, [
#             "--name", "test-container",
#             "--title", "Test Container",
#             "--type", "code",
#             "--description", "Test description",
#             "--path", "/path/to/source"
#         ])
#
#         # Assert
#         assert result.exit_code == 0
#         mock_use_case_instance.execute.assert_called_once_with(
#             name="test-container",
#             title="Test Container",
#             container_type="code",
#             source_path="/path/to/source",
#             description="Test description",
#             priority=5
#         )
#         assert "Successfully created container" in result.output
#         assert "container-id" in result.output
#
#     @patch(
#         "src.infrastructure.cli.commands.context_commands.create_list_containers_use_case")
#     def test_list_containers_command(self, mock_use_case, cli_runner):
#         """Test listing containers."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_containers = [
#             Container(
#                 id="container1-id",
#                 name="container1",
#                 title="Container 1",
#                 container_type=ContainerType("code"),
#                 source_path="/path/to/source"
#             ),
#             Container(
#                 id="container2-id",
#                 name="container2",
#                 title="Container 2",
#                 container_type=ContainerType("documentation"),
#                 source_path="/path/to/source"
#             )
#         ]
#         mock_use_case_instance.execute.return_value = mock_containers
#
#         # Act
#         result = cli_runner.invoke(list_containers, [])
#
#         # Assert
#         assert result.exit_code == 0
#         mock_use_case_instance.execute.assert_called_once()
#         assert "container1-id" in result.output
#         assert "Container 1" in result.output
#         assert "container2-id" in result.output
#         assert "Container 2" in result.output
#
#     @patch(
#         "src.infrastructure.cli.commands.context_commands.create_list_context_use_case")
#     def test_list_contexts_with_container_filter(self, mock_use_case,
#                                                  cli_runner):
#         """Test listing context items with container filter."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_items = [
#             ContextItem(
#                 id="item1-id",
#                 source="file1.py",
#                 content_type=ContentType("python"),
#                 content="This is a python file",
#             ),
#             ContextItem(
#                 id="item2-id",
#                 source="file2.py",
#                 content_type=ContentType("python"),
#                 content="This is a python file too",
#             )
#         ]
#         mock_use_case_instance.execute_list_by_container.return_value = mock_items
#
#         # Act
#         result = cli_runner.invoke(list_contexts, [
#             "--container", "container-id"
#         ])
#
#         # Assert
#         assert result.exit_code == 0
#         mock_use_case_instance.execute_list_by_container.assert_called_once_with(
#             "container-id")
#         assert "item1-id" in result.output
#         assert "item2-id" in result.output
#
#
# class TestTaskCommands:
#     """Unit tests for task management commands."""
#
#     @pytest.fixture
#     def cli_runner(self):
#         """Create a Click CLI test runner."""
#         return CliRunner()
#
#     @patch("src.infrastructure.cli.commands.task_commands.Task")
#     @patch(
#         "src.infrastructure.cli.commands.task_commands.create_pipeline_use_case")
#     def test_create_task_command(self, mock_use_case, mock_task, cli_runner):
#         """Test create task command (U-CLI-1, U-CLI-2)."""
#         # Arrange
#         mock_task_instance = Task(
#             id="task-id",
#             description="Test task",
#             requirements=["Something", "Something else"]
#         )
#         mock_task.parse_from_user_input.return_value = mock_task_instance
#
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_use_case_instance.execute.return_value = (
#         mock_task_instance, Mock(id="state-id"))
#
#         # Act
#         result = cli_runner.invoke(create_task, ["--description", "Test task",
#                                                  "--requirement", "req1",
#                                                  "--requirement", "req2"])
#
#         # Assert
#         assert result.exit_code == 0
#         mock_task.parse_from_user_input.assert_called()
#         mock_use_case_instance.execute.assert_called_once()
#         assert "task-id" in result.output
#         assert "Test task" in result.output
#
#     @patch("src.infrastructure.cli.commands.task_commands.create_pipeline_repository")
#     def test_list_tasks_command(self, mock_repo, cli_runner):
#         """Test list tasks command (U-CLI-1, U-CLI-2)."""
#         # Arrange
#         mock_repo_instance = Mock()
#         mock_repo.return_value = mock_repo_instance
#         mock_task = Mock(id="task-id", description="Test task",
#                          status="pending")
#         mock_repo_instance.list_tasks.return_value = [mock_task]
#
#         # Act
#         result = cli_runner.invoke(list_tasks)
#
#         # Assert
#         assert result.exit_code == 0
#         mock_repo_instance.list_tasks.assert_called_once()
#         assert "task-id" in result.output
#         assert "Test task" in result.output
#         assert "pending" in result.output
#
#
# class TestFeedbackCommands:
#     """Unit tests for feedback commands."""
#
#     @pytest.fixture
#     def cli_runner(self):
#         """Create a Click CLI test runner."""
#         return CliRunner()
#
#     @patch(
#         "src.infrastructure.cli.commands.feedback_commands.create_submit_feedback_use_case")
#     def test_submit_feedback_command(self, mock_use_case, cli_runner):
#         """Test submit feedback command (U-CLI-1, U-CLI-2)."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_use_case_instance.execute.return_value = Mock(id="state-id")
#
#         # Act
#         result = cli_runner.invoke(submit_feedback, [
#             "--pipeline-state-id", "state-id",
#             "--stage", "implementation_planning",
#             "--content", "This plan needs improvement",
#             "--type", "suggestion"
#         ])
#
#         # Assert
#         assert result.exit_code == 0
#         mock_use_case_instance.execute.assert_called_once_with(
#             "state-id", "implementation_planning",
#             "This plan needs improvement", "suggestion"
#         )
#         assert "Successfully submitted feedback" in result.output
#
#
# class TestErrorHandling:
#     """Unit tests for CLI error handling."""
#
#     @pytest.fixture
#     def cli_runner(self):
#         """Create a Click CLI test runner."""
#         return CliRunner()
#
#     @patch("src.infrastructure.cli.commands.context_commands.create_add_context_use_case")
#     def test_error_handling(self, mock_use_case, cli_runner):
#         """Test CLI error handling (U-CLI-3)."""
#         # Arrange
#         mock_use_case_instance = Mock()
#         mock_use_case.return_value = mock_use_case_instance
#         mock_use_case_instance.execute_from_file_path.side_effect = FileNotFoundError(
#             "File not found")
#
#         # Act
#         result = cli_runner.invoke(add_context,
#                                    ["--file", "nonexistent-file.py"])
#
#         # Assert
#         assert result.exit_code != 0
#         assert "Error" in result.output
#         assert "File not found" in result.output