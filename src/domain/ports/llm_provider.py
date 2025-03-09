from abc import ABC, abstractmethod
from typing import Dict, List, Any


class LLMProvider(ABC):
    """
    Port interface for language model interactions.

    This interface abstracts the specific language model provider,
    allowing the domain to remain independent of specific LLM technologies.
    """

    @abstractmethod
    def generate_text(self, prompt: str, options: Dict[str, Any] = None) -> str:
        """
        Generate text from a prompt using the language model.

        Args:
            prompt: The input prompt to send to the model
            options: Optional dictionary of generation parameters
                     (e.g., temperature, max_tokens, etc.)

        Returns:
            The generated text response
        """
        pass

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a vector embedding for the given text.

        Args:
            text: The text to generate an embedding for

        Returns:
            Vector embedding as a list of floats
        """
        pass