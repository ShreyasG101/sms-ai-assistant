"""Repository for conversation data access."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import aiosqlite


@dataclass
class Conversation:
    """A conversation with a phone number."""

    id: int
    phone_number: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ConversationSummary:
    """Conversation summary with last message preview."""

    id: int
    phone_number: str
    last_message: str | None
    last_message_time: datetime | None
    last_message_role: Literal["user", "assistant"] | None
    updated_at: datetime


class ConversationRepository:
    """
    Repository for conversation data access.

    Provides a simple interface hiding SQL complexity.
    """

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def find_by_phone(self, phone_number: str) -> Conversation | None:
        """Find conversation by phone number, or None if not exists."""
        cursor = await self._db.execute(
            "SELECT id, phone_number, created_at, updated_at FROM conversations WHERE phone_number = ?",
            (phone_number,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return Conversation(
            id=row["id"],
            phone_number=row["phone_number"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def find_or_create(self, phone_number: str) -> Conversation:
        """Get existing conversation or create new one. Never fails."""
        existing = await self.find_by_phone(phone_number)
        if existing:
            return existing

        now = datetime.utcnow().isoformat()
        cursor = await self._db.execute(
            "INSERT INTO conversations (phone_number, created_at, updated_at) VALUES (?, ?, ?)",
            (phone_number, now, now),
        )
        await self._db.commit()
        return Conversation(
            id=cursor.lastrowid,
            phone_number=phone_number,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    async def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConversationSummary], int]:
        """List conversations with last message preview. Returns (conversations, total_count)."""
        # Get total count
        cursor = await self._db.execute("SELECT COUNT(*) FROM conversations")
        row = await cursor.fetchone()
        total = row[0]

        # Get conversations with last message
        cursor = await self._db.execute(
            """
            SELECT
                c.id, c.phone_number, c.updated_at,
                m.content as last_message,
                m.timestamp as last_message_time,
                m.role as last_message_role
            FROM conversations c
            LEFT JOIN messages m ON m.id = (
                SELECT id FROM messages
                WHERE conversation_id = c.id
                ORDER BY timestamp DESC LIMIT 1
            )
            ORDER BY c.updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = await cursor.fetchall()

        conversations = [
            ConversationSummary(
                id=row["id"],
                phone_number=row["phone_number"],
                last_message=row["last_message"],
                last_message_time=datetime.fromisoformat(row["last_message_time"]) if row["last_message_time"] else None,
                last_message_role=row["last_message_role"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]
        return conversations, total

    async def delete(self, phone_number: str) -> bool:
        """Delete conversation and all messages. Returns True if existed."""
        cursor = await self._db.execute(
            "DELETE FROM conversations WHERE phone_number = ?",
            (phone_number,),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def touch(self, conversation_id: int) -> None:
        """Update the updated_at timestamp."""
        now = datetime.utcnow().isoformat()
        await self._db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        await self._db.commit()
