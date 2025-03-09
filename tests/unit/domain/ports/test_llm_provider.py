import pytest
from abc import ABC
from typing import Dict, Any, List

from src.domain.ports.llm_provider import LLMProvider


class TestLLMProvider:
    """Test cases for the LLMProvider port."""

    def test_llm_provider_interface(self):
        """Test that LLMProvider defines the expected interface (U-HA-3)."""
        # Verify that LLMProvider is an abstract base class
        assert issubclass(LLMProvider, ABC)

        # Check that all required methods are defined
        required_methods = [
            "generate_text",
            "generate_embedding",
        ]

        for method_name in required_methods:
            assert hasattr(LLMProvider,
                           method_name), f"LLMProvider should define '{method_name}' method"
            method = getattr(LLMProvider, method_name)
            assert callable(method), f"'{method_name}' should be a method"

    def test_llm_provider_independency(self):
        """Test that LLMProvider has no infrastructure dependencies (U-HA-2)."""
        import inspect

        # Get the source code of the interface
        source = inspect.getsource(LLMProvider)

        # Check for specific implementation-related terms
        implementation_terms = [
            "openai",
            "gpt",
            "anthropic",
            "claude",
            "llama",
            "huggingface",
            "transformers",
            "api key",
            "apikey",
        ]

        for term in implementation_terms:
            assert term.lower() not in source.lower(), f"LLMProvider should not reference '{term}'"

    def test_llm_provider_contract(self):
        """Test the contract that implementations of LLMProvider must adhere to."""

        # A concrete implementation for testing
        class MockLLMProvider(LLMProvider):
            def generate_text(self, prompt: str,
                              options: Dict[str, Any] = None) -> str:
                return f"Mock response to: {prompt}"

            def generate_embedding(self, text: str) -> List[float]:
                # Return a simplified embedding for testing
                return [0.1, 0.2, 0.3, 0.4, 0.5]

        # Create a mock provider for testing
        provider = MockLLMProvider()

        # Test generate_text method
        prompt = "Hello, world!"
        response = provider.generate_text(prompt)
        assert isinstance(response, str)
        assert prompt in response

        # Test with options
        options = {"temperature": 0.7, "max_tokens": 100}
        response_with_options = provider.generate_text(prompt, options)
        assert isinstance(response_with_options, str)

        # Test generate_embedding method
        text = "This is a test document"
        embedding = provider.generate_embedding(text)
        assert isinstance(embedding, list)
        assert all(isinstance(value, float) for value in embedding)