"""Provider factory for creating AI providers."""

import logging

from app.core.config import Settings
from app.providers.base import AIProvider
from app.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


def get_ai_provider(settings: Settings) -> AIProvider:
    """
    Create and return the configured AI provider.

    Currently supports:
    - openai: OpenAI API (GPT models)

    Future providers can be added here (anthropic, ollama, etc.)
    """
    match settings.ai_provider:
        case "openai":
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.ai_model,
            )
        case _:
            # Fallback to OpenAI for unknown providers
            logger.warning(
                f"Unknown AI provider '{settings.ai_provider}', defaulting to OpenAI"
            )
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.ai_model,
            )
