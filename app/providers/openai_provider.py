"""OpenAI API provider implementation."""

import asyncio
import logging

from openai import AsyncOpenAI, APIError, RateLimitError

from app.providers.base import AIProvider, Message

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "I'm having trouble right now. Please try again in a moment."


class OpenAIProvider(AIProvider):
    """
    OpenAI API provider with retry logic and error handling.

    Handles its own complexity internally:
    - Retry with exponential backoff on transient errors
    - Rate limit handling with wait and retry
    - Returns fallback message on persistent failure
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._model = model
        self._max_retries = max_retries

    @property
    def name(self) -> str:
        return f"openai:{self._model}"

    async def generate_response(
        self,
        messages: list[Message],
        system_prompt: str,
    ) -> str:
        """Generate a response with retry logic."""
        # Build messages list with system prompt
        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend(messages)

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=api_messages,
                )
                content = response.choices[0].message.content
                return content or FALLBACK_MESSAGE

            except RateLimitError as e:
                last_error = e
                # Wait longer on rate limit
                wait_time = min(2 ** (attempt + 2), 30)
                logger.warning(
                    f"Rate limited by OpenAI, waiting {wait_time}s (attempt {attempt + 1}/{self._max_retries})"
                )
                await asyncio.sleep(wait_time)

            except APIError as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"OpenAI API error: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{self._max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"OpenAI API error after {self._max_retries} attempts: {e}")

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error calling OpenAI: {e}")
                break

        logger.error(f"Failed to generate response after {self._max_retries} attempts: {last_error}")
        return FALLBACK_MESSAGE
