"""Core SMS processing service."""

import logging
from datetime import datetime
from typing import Literal

from app.providers.base import AIProvider
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.outbox import OutboxMessage, OutboxRepository
from app.services.auth import AuthService

logger = logging.getLogger(__name__)


class SMSService:
    """
    Core SMS processing service.

    This is a "deep module" following Ousterhout's principles:
    - Simple interface (process_incoming, get_outgoing_messages, acknowledge_sent)
    - Complex implementation hidden (auth, storage, AI generation, queuing)
    """

    def __init__(
        self,
        auth_service: AuthService,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        outbox_repo: OutboxRepository,
        ai_provider: AIProvider,
        system_prompt: str,
        max_context: int = 20,
    ):
        self._auth = auth_service
        self._conversations = conversation_repo
        self._messages = message_repo
        self._outbox = outbox_repo
        self._ai = ai_provider
        self._system_prompt = system_prompt
        self._max_context = max_context

    async def process_incoming(
        self,
        phone_number: str,
        content: str,
        timestamp: datetime | None = None,
    ) -> bool:
        """
        Process an incoming SMS message.

        1. Check authorization (unauthorized = log and return False)
        2. Find or create conversation
        3. Store incoming message
        4. Get conversation history
        5. Generate AI response
        6. Store response and queue for sending

        Returns True if processed, False if unauthorized.
        Never raises exceptions to caller.
        """
        # Authorization check
        if not self._auth.is_authorized(phone_number):
            return False

        try:
            # Find or create conversation
            conversation = await self._conversations.find_or_create(phone_number)
            logger.info(f"Processing message from {phone_number} (conversation {conversation.id})")

            # Store incoming message
            await self._messages.create(
                conversation_id=conversation.id,
                role="user",
                content=content,
                status="received",
            )

            # Get conversation history for AI context
            history = await self._messages.get_history(
                conversation_id=conversation.id,
                limit=self._max_context,
            )

            # Format messages for AI
            ai_messages = [{"role": msg.role, "content": msg.content} for msg in history]

            # Generate AI response
            logger.info(f"Generating AI response for conversation {conversation.id}")
            response = await self._ai.generate_response(
                messages=ai_messages,
                system_prompt=self._system_prompt,
            )

            # Store response
            await self._messages.create(
                conversation_id=conversation.id,
                role="assistant",
                content=response,
                status="pending",
            )

            # Queue for sending
            await self._outbox.enqueue(
                phone_number=phone_number,
                content=response,
            )

            # Update conversation timestamp
            await self._conversations.touch(conversation.id)

            logger.info(f"Successfully processed message from {phone_number}")
            return True

        except Exception as e:
            logger.error(f"Error processing message from {phone_number}: {e}")
            return False

    async def get_outgoing_messages(
        self,
        limit: int = 10,
    ) -> list[OutboxMessage]:
        """Get pending messages for phone to send."""
        return await self._outbox.get_pending(limit)

    async def acknowledge_sent(
        self,
        message_id: int,
        status: Literal["sent", "failed"],
    ) -> bool:
        """Mark outgoing message as sent/failed. Idempotent."""
        success = await self._outbox.acknowledge(message_id, status)
        if success:
            logger.info(f"Outbox message {message_id} marked as {status}")
        return success
