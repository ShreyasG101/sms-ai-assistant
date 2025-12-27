"""FastAPI dependency injection setup."""

from typing import Annotated, AsyncGenerator

import aiosqlite
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.providers.base import AIProvider
from app.providers.factory import get_ai_provider
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.outbox import OutboxRepository
from app.services.auth import AuthService
from app.services.sms import SMSService

# Cached instances
_auth_service: AuthService | None = None
_ai_provider: AIProvider | None = None


def get_auth_service() -> AuthService:
    """Get or create AuthService singleton."""
    global _auth_service
    if _auth_service is None:
        settings = get_settings()
        _auth_service = AuthService(settings.allowed_phone_numbers)
    return _auth_service


def get_cached_ai_provider() -> AIProvider:
    """Get or create AIProvider singleton."""
    global _ai_provider
    if _ai_provider is None:
        settings = get_settings()
        _ai_provider = get_ai_provider(settings)
    return _ai_provider


# Type aliases for dependency injection
DbConnection = Annotated[aiosqlite.Connection, Depends(get_db)]


async def get_sms_service(
    db: DbConnection,
) -> SMSService:
    """Create SMSService with all dependencies."""
    settings = get_settings()

    return SMSService(
        auth_service=get_auth_service(),
        conversation_repo=ConversationRepository(db),
        message_repo=MessageRepository(db),
        outbox_repo=OutboxRepository(db),
        ai_provider=get_cached_ai_provider(),
        system_prompt=settings.system_prompt,
        max_context=settings.max_context_messages,
    )


async def get_outbox_repo(
    db: DbConnection,
) -> OutboxRepository:
    """Get OutboxRepository for health check."""
    return OutboxRepository(db)
