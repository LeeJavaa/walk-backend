from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from uuid import uuid4
import re
import os


class CodeArtifactType(str, Enum):
    """Enumeration of code artifact types."""
    IMPLEMENTATION = "implementation"
    TEST = "test"
    DOCUMENTATION = "documentation"
    PLAN = "plan"
    REVIEW = "review"


class CodeArtifactValidationError(Exception):
    """Exception raised for code artifact validation errors."""
    pass


class CodeArtifact:
    """
    Entity representing a code artifact generated by the agent.

    A code artifact can be implementation code, tests, documentation, etc.
    """

    def __init__(
            self,
            id: str,
            task_id: str,
            content: str,
            artifact_type: CodeArtifactType,
            language: str,
            path: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            quality_metrics: Optional[Dict[str, Any]] = None,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None,
    ):
        """
        Initialize a new CodeArtifact.

        Args:
            id: Unique identifier for the artifact
            task_id: Identifier of the task that this artifact is part of
            content: Actual content of the artifact (code, documentation, etc.)
            artifact_type: Type of the artifact
            language: Programming language or format of the content
            path: File path where the artifact should be saved (optional)
            metadata: Additional metadata about the artifact (optional)
            quality_metrics: Quality metrics about the artifact (optional)
            created_at: Creation timestamp (optional)
            updated_at: Last update timestamp (optional)

        Raises:
            CodeArtifactValidationError: If validation fails
        """
        self.validate_content(content)
        self.validate_language(language)
        self.validate_artifact_type(artifact_type)

        self.id = id
        self.task_id = task_id
        self.content = content
        self.artifact_type = artifact_type
        self.language = language
        self.path = path or self._generate_path()
        self.metadata = metadata or {}
        self.quality_metrics = quality_metrics or {}
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    # Add to your CodeArtifact class in src/domain/entities/code_artifact.py
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the code artifact to a dictionary for serialization.

        Returns:
            Dictionary representation of the code artifact
        """
        return {
            "id": self.id,
            "task_id": self.task_id,
            "content": self.content,
            "artifact_type": self.artifact_type.value,  # Convert enum to string
            "language": self.language,
            "path": self.path,
            "metadata": self.metadata,
            "quality_metrics": self.quality_metrics,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeArtifact':
        """
        Create a code artifact from a dictionary.

        Args:
            data: Dictionary with artifact data

        Returns:
            CodeArtifact instance
        """
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            content=data["content"],
            artifact_type=CodeArtifactType(data["artifact_type"]),
            # Convert string back to enum
            language=data["language"],
            path=data.get("path"),
            metadata=data.get("metadata", {}),
            quality_metrics=data.get("quality_metrics", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    @staticmethod
    def validate_content(content: str) -> None:
        """
        Validate the artifact content.

        Args:
            content: Content to validate

        Raises:
            CodeArtifactValidationError: If validation fails
        """
        if not content:
            raise CodeArtifactValidationError("Content cannot be empty")

    @staticmethod
    def validate_language(language: str) -> None:
        """
        Validate the artifact language.

        Args:
            language: Language to validate

        Raises:
            CodeArtifactValidationError: If validation fails
        """
        if not language:
            raise CodeArtifactValidationError("Language cannot be empty")

    @staticmethod
    def validate_artifact_type(artifact_type: Any) -> None:
        """
        Validate that the artifact type is a valid CodeArtifactType.

        Args:
            artifact_type: Type to validate

        Raises:
            ValueError: If the artifact_type is not a valid CodeArtifactType
        """
        if not isinstance(artifact_type, CodeArtifactType):
            valid_types = [t.value for t in CodeArtifactType]
            raise CodeArtifactValidationError(
                f"Invalid artifact type. Expected one of: {valid_types}")

    def _generate_path(self) -> str:
        """
        Generate a file path based on the artifact content and type.

        Returns:
            Generated file path
        """
        file_extension = self._get_file_extension()

        # For test artifacts, prefix with "test_"
        prefix = "test_" if self.artifact_type == CodeArtifactType.TEST else ""

        # Try to extract a meaningful name from the content
        if self.language == "python":
            # For Python, look for class or function definitions
            match = re.search(r"(class|def)\s+([A-Za-z0-9_]+)", self.content)
            if match:
                name = match.group(2).lower()
                return f"{prefix}{name}{file_extension}"

        # Default to a generic name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}{self.artifact_type.value}_{timestamp}{file_extension}"

    def _get_file_extension(self) -> str:
        """
        Get the file extension based on the artifact language.

        Returns:
            File extension including the dot
        """
        language_to_extension = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "csharp": ".cs",
            "go": ".go",
            "rust": ".rs",
            "markdown": ".md",
            "text": ".txt",
            "html": ".html",
            "css": ".css",
            "json": ".json",
            "yaml": ".yaml",
            "sql": ".sql",
        }

        return language_to_extension.get(self.language.lower(), ".txt")

    def extract_dependencies(self) -> List[str]:
        """
        Extract dependencies from the artifact content.

        Returns:
            List of dependency names
        """
        dependencies = []

        if self.language == "python":
            # Extract Python imports
            import_pattern = r"^\s*(import|from)\s+([a-zA-Z0-9_\.]+)"
            for line in self.content.split("\n"):
                match = re.search(import_pattern, line)
                if match:
                    if match.group(1) == "import":
                        # For "import X" or "import X as Y"
                        module = match.group(2).split(".")[0]
                        dependencies.append(module)
                    else:
                        # For "from X import Y"
                        module = match.group(2)
                        dependencies.append(module)

        elif self.language == "javascript" or self.language == "typescript":
            # Extract JavaScript/TypeScript imports
            import_pattern = r"(import|require)\s*\(?['\"]([^'\"]+)['\"]"
            for match in re.finditer(import_pattern, self.content):
                module = match.group(2)
                if not module.startswith("."):  # Exclude relative imports
                    dependencies.append(module.split("/")[0])

        return list(set(dependencies))  # Remove duplicates