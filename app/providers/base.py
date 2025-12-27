"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod
from typing import Literal, TypedDict


class Message(TypedDict):
    """A message in a conversation."""

    role: Literal["user", "assistant", "system"]
    content: str


class AIProvider(ABC):
    """
    Abstract base class for AI providers.

    Implementations handle their own error recovery and return
    a user-friendly fallback message rather than raising exceptions.
    This follows Ousterhout's principle of "pulling complexity downward."
    """

    @abstractmethod
    async def generate_response(
        self,
        messages: list[Message],
        system_prompt: str,
    ) -> str:
        """
        Generate a response from the AI model.

        Args:
            messages: Conversation history (user/assistant messages).
            system_prompt: System instructions for the AI.

        Returns:
            Generated response text. On error, returns a user-friendly
            fallback message rather than raising an exception.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging (e.g., 'openai:gpt-4o-mini')."""
        ...
