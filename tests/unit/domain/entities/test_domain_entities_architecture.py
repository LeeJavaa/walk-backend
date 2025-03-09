import pytest
import inspect

from src.domain.entities.context_item import ContextItem
from src.domain.entities.pipeline_stage import PipelineStage
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.task import Task
from src.domain.entities.code_artifact import CodeArtifact


class TestDomainEntitiesArchitecture:
    """Test cases for the domain entities architecture."""

    def test_domain_entities_encapsulation(self):
        """Test that domain entities are properly encapsulated (U-HA-1)."""
        entities = [
            ContextItem,
            PipelineStage,
            PipelineState,
            Task,
            CodeArtifact,
        ]

        for entity_class in entities:
            # Check that the class has a proper constructor
            assert hasattr(entity_class,
                           "__init__"), f"{entity_class.__name__} should have a constructor"

            # Check that the class has proper validation
            validation_methods = [
                method_name for method_name, method in
                inspect.getmembers(entity_class, predicate=inspect.isfunction)
                if "validate" in method_name
            ]
            assert len(
                validation_methods) > 0, f"{entity_class.__name__} should have validation methods"

            # Check that the class doesn't have external dependencies in its core functionality
            # (excluding standard library, pytest, and datetime)
            allowed_imports = ["datetime", "uuid", "enum", "abc", "typing",
                               "os", "re"]

            # Get the source code of the class
            source = inspect.getsource(entity_class)

            # Check for imports that are not allowed
            import_lines = [
                line.strip() for line in source.split("\n")
                if
                line.strip().startswith("import ") or line.strip().startswith(
                    "from ")
            ]

            for import_line in import_lines:
                is_allowed = False
                for allowed_import in allowed_imports:
                    if allowed_import in import_line:
                        is_allowed = True
                        break

                if not is_allowed:
                    pytest.fail(
                        f"{entity_class.__name__} has an external dependency: {import_line}")

            # Check that the class doesn't have direct references to infrastructure
            infrastructure_terms = ["mongodb", "openai", "repository",
                                    "database", "api"]
            for term in infrastructure_terms:
                assert term not in source.lower(), f"{entity_class.__name__} should not reference {term}"