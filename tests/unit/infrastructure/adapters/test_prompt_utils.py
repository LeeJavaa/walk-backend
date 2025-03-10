import pytest

from src.infrastructure.adapters.prompt_utils import (
    create_requirements_gathering_prompt,
    create_knowledge_gathering_prompt,
    create_implementation_planning_prompt,
    create_implementation_writing_prompt,
    create_review_prompt,
    format_context_items_for_prompt
)


class TestPromptUtils:
    """Test cases for prompt construction utilities."""

    def test_requirements_gathering_prompt(self):
        """Test creating a requirements gathering prompt (U-CG-1)."""
        # Arrange
        task_description = "Create a function to calculate fibonacci numbers"
        user_input = "I need a recursive and an iterative solution"

        # Act
        prompt = create_requirements_gathering_prompt(task_description,
                                                      user_input)

        # Assert
        assert task_description in prompt
        assert user_input in prompt
        assert "requirements" in prompt.lower()
        assert "constraints" in prompt.lower()

    def test_knowledge_gathering_prompt(self):
        """Test creating a knowledge gathering prompt (U-CG-1)."""
        # Arrange
        task_description = "Create a REST API"
        requirements = ["Must use Flask", "Should have authentication"]
        constraints = ["Python 3.9+", "No external databases"]

        # Act
        prompt = create_knowledge_gathering_prompt(task_description,
                                                   requirements, constraints)

        # Assert
        assert task_description in prompt
        assert "Flask" in prompt
        assert "authentication" in prompt
        assert "Python 3.9+" in prompt
        assert "knowledge" in prompt.lower() or "information" in prompt.lower()

    def test_implementation_planning_prompt(self):
        """Test creating an implementation planning prompt (U-CG-1)."""
        # Arrange
        task_description = "Build a web scraper"
        requirements = ["Extract article titles", "Save to CSV"]
        constraints = ["Use requests and BeautifulSoup"]
        context_items = [
            {
                "content": "# Web Scraping Example\n```python\nimport requests\n```",
                "source": "example.md"},
            {"content": "def parse_html(html):\n    return soup",
             "source": "utils.py"}
        ]

        # Act
        prompt = create_implementation_planning_prompt(
            task_description,
            requirements,
            constraints,
            context_items
        )

        # Assert
        assert task_description in prompt
        assert "Extract article titles" in prompt
        assert "requests and BeautifulSoup" in prompt
        assert "plan" in prompt.lower()
        assert "steps" in prompt.lower()
        # Should include context items
        assert "Web Scraping Example" in prompt
        assert "parse_html" in prompt

    def test_implementation_writing_prompt(self):
        """Test creating an implementation writing prompt (U-CG-1)."""
        # Arrange
        task_description = "Build a simple calculator"
        requirements = ["Support add, subtract, multiply, divide"]
        plan = "1. Create a Calculator class\n2. Implement operations"
        context_items = [
            {"content": "def add(a, b):\n    return a + b",
             "source": "math_utils.py"}
        ]

        # Act
        prompt = create_implementation_writing_prompt(
            task_description,
            requirements,
            plan,
            context_items
        )

        # Assert
        assert task_description in prompt
        assert "Support add, subtract" in prompt
        assert "Create a Calculator class" in prompt
        assert "def add(a, b)" in prompt
        assert "implementation" in prompt.lower() or "code" in prompt.lower()

    def test_review_prompt(self):
        """Test creating a review prompt (U-CG-1)."""
        # Arrange
        code = "def fibonacci(n):\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)"
        requirements = ["Implement recursive fibonacci"]
        constraints = ["Must be efficient"]

        # Act
        prompt = create_review_prompt(code, requirements, constraints)

        # Assert
        assert "def fibonacci(n)" in prompt
        assert "Implement recursive fibonacci" in prompt
        assert "Must be efficient" in prompt
        assert "review" in prompt.lower()
        assert "quality" in prompt.lower() or "issues" in prompt.lower()

    def test_format_context_items_for_prompt(self):
        """Test formatting context items for inclusion in prompts (U-CG-3)."""
        # Arrange
        context_items = [
            {"content": "def add(a, b):\n    return a + b",
             "source": "math_utils.py"},
            {
                "content": "class User:\n    def __init__(self, name):\n        self.name = name",
                "source": "models.py"}
        ]

        # Act
        formatted_context = format_context_items_for_prompt(context_items)

        # Assert
        assert "math_utils.py" in formatted_context
        assert "def add(a, b)" in formatted_context
        assert "models.py" in formatted_context
        assert "class User" in formatted_context
        # Should have a clear separator between items
        assert "---" in formatted_context or "===" in formatted_context or "##" in formatted_context