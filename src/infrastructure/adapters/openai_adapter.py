import os
import logging
import time
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv

import openai
from tenacity import retry, stop_after_attempt, wait_exponential, \
    retry_if_exception_type

from src.domain.ports.llm_provider import LLMProvider

load_dotenv()


class OpenAIAdapter(LLMProvider):
    """
    Implementation of the LLMProvider interface using OpenAI's API.

    This adapter provides methods to generate text and embeddings using
    OpenAI's language models.
    """

    def __init__(
            self,
            api_key: Optional[str] = None,
            model: Optional[str] = None,
            embedding_model: Optional[str] = None
    ):
        """
        Initialize the OpenAI adapter.

        Args:
            api_key: OpenAI API key (optional, defaults to environment variable)
            model: Model ID to use for text generation (optional, defaults to environment variable)
            embedding_model: Model ID to use for embeddings (optional, defaults to environment variable)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4")
        self.embedding_model = embedding_model or os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Initialize OpenAI client
        self.client = openai.Client(api_key=self.api_key)

    @retry(
        retry=retry_if_exception_type(
            (openai.RateLimitError, openai.APITimeoutError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5)
    )
    def generate_text(self, prompt: str, options: Dict[str, Any] = None) -> str:
        """
        Generate text from a prompt using the language model.

        Args:
            prompt: The input prompt to send to the model
            options: Optional dictionary of generation parameters
                     (e.g., temperature, max_tokens, etc.)

        Returns:
            The generated text response

        Raises:
            Exception: If there's an error with the API call
        """
        try:
            options = options or {}

            # Default parameters
            params = {
                "model": self.model,
                "messages": [],
                "temperature": options.get("temperature", 0.7),
            }

            # Add system message if provided
            if options.get("system_message"):
                params["messages"].append({
                    "role": "system",
                    "content": options["system_message"]
                })

            # Add user message (the prompt)
            params["messages"].append({
                "role": "user",
                "content": prompt
            })

            # Add any other parameters
            for key, value in options.items():
                if key not in ["temperature",
                               "system_message"] and key not in params:
                    params[key] = value

            # Make the API call
            response = self.client.chat.completions.create(**params)

            print(response.choices)

            # Extract and return the generated text
            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error generating text with OpenAI: {str(e)}")
            raise

    @retry(
        retry=retry_if_exception_type(
            (openai.RateLimitError, openai.APITimeoutError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5)
    )
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a vector embedding for the given text.

        Args:
            text: The text to generate an embedding for

        Returns:
            Vector embedding as a list of floats

        Raises:
            Exception: If there's an error with the API call
        """
        try:
            # Make the API call
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )

            # Extract and return the embedding
            return response.data[0].embedding

        except Exception as e:
            self.logger.error(
                f"Error generating embedding with OpenAI: {str(e)}")
            raise