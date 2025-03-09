import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.entities.code_artifact import CodeArtifact, CodeArtifactType, \
    CodeArtifactValidationError


class TestCodeArtifact:
    """Test cases for the CodeArtifact entity."""

    def test_code_artifact_creation_with_valid_inputs(self):
        """Test creating a code artifact with valid inputs."""
        # Arrange
        artifact_id = str(uuid4())
        task_id = str(uuid4())
        content = "def hello_world():\n    print('Hello, World!')"
        artifact_type = CodeArtifactType.IMPLEMENTATION
        language = "python"
        path = "hello_world.py"
        metadata = {"author": "Test Author",
                    "description": "Simple hello world function"}
        quality_metrics = {"complexity": 1, "maintainability": 95}

        # Act
        artifact = CodeArtifact(
            id=artifact_id,
            task_id=task_id,
            content=content,
            artifact_type=artifact_type,
            language=language,
            path=path,
            metadata=metadata,
            quality_metrics=quality_metrics,
        )

        # Assert
        assert artifact.id == artifact_id
        assert artifact.task_id == task_id
        assert artifact.content == content
        assert artifact.artifact_type == artifact_type
        assert artifact.language == language
        assert artifact.path == path
        assert artifact.metadata == metadata
        assert artifact.quality_metrics == quality_metrics
        assert isinstance(artifact.created_at, datetime)
        assert isinstance(artifact.updated_at, datetime)

    def test_code_artifact_validation(self):
        """Test validation of code artifact inputs."""
        # Test empty content
        with pytest.raises(CodeArtifactValidationError,
                           match="Content cannot be empty"):
            CodeArtifact(
                id=str(uuid4()),
                task_id=str(uuid4()),
                content="",
                artifact_type=CodeArtifactType.IMPLEMENTATION,
                language="python",
            )

        # Test invalid artifact type
        with pytest.raises(ValueError):
            CodeArtifact(
                id=str(uuid4()),
                task_id=str(uuid4()),
                content="def test(): pass",
                artifact_type="invalid_type",
                language="python",
            )

        # Test empty language
        with pytest.raises(CodeArtifactValidationError,
                           match="Language cannot be empty"):
            CodeArtifact(
                id=str(uuid4()),
                task_id=str(uuid4()),
                content="def test(): pass",
                artifact_type=CodeArtifactType.IMPLEMENTATION,
                language="",
            )

    def test_generate_path_from_content(self):
        """Test generating a path from artifact content."""
        # Arrange - Python implementation
        python_content = "def calculator(a, b):\n    return a + b"

        # Act
        artifact = CodeArtifact(
            id=str(uuid4()),
            task_id=str(uuid4()),
            content=python_content,
            artifact_type=CodeArtifactType.IMPLEMENTATION,
            language="python",
        )

        # Assert
        assert artifact.path.endswith(".py")
        assert "calculator" in artifact.path

        # Arrange - Test code
        test_content = "def test_calculator():\n    assert calculator(1, 2) == 3"

        # Act
        test_artifact = CodeArtifact(
            id=str(uuid4()),
            task_id=str(uuid4()),
            content=test_content,
            artifact_type=CodeArtifactType.TEST,
            language="python",
        )

        # Assert
        assert test_artifact.path.startswith("test_")
        assert test_artifact.path.endswith(".py")

    def test_extract_dependencies(self):
        """Test extracting dependencies from code content."""
        # Arrange
        content = """
        import os
        import sys
        from datetime import datetime
        import numpy as np
        from my_module import MyClass

        def my_function():
            pass
        """

        # Act
        artifact = CodeArtifact(
            id=str(uuid4()),
            task_id=str(uuid4()),
            content=content,
            artifact_type=CodeArtifactType.IMPLEMENTATION,
            language="python",
        )
        dependencies = artifact.extract_dependencies()

        # Assert
        assert "os" in dependencies
        assert "sys" in dependencies
        assert "datetime" in dependencies
        assert "numpy" in dependencies
        assert "my_module" in dependencies