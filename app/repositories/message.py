"""Repository for message data access."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import aiosqlite


@dataclass
class Message:
    """A message in a conversation."""

    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    status: str


class MessageRepository:
    """Repository for message data access."""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def create(
        self,
        conversation_id: int,
        role: Literal["user", "assistant"],
        content: str,
        status: str = "received",
    ) -> Message:
        """Create a new message."""
        now = datetime.utcnow().isoformat()
        cursor = await self._db.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, now, status),
        )
        await self._db.commit()
        return Message(
            id=cursor.lastrowid,
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.fromisoformat(now),
            status=status,
        )

    async def get_history(
        self,
        conversation_id: int,
        limit: int = 20,
    ) -> list[Message]:
        """Get recent messages for AI context, ordered oldest-first."""
        cursor = await self._db.execute(
            """
            SELECT id, conversation_id, role, content, timestamp, status
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (conversation_id, limit),
        )
        rows = await cursor.fetchall()

        # Reverse to get oldest-first order for AI context
        messages = [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                status=row["status"],
            )
            for row in reversed(rows)
        ]
        return messages

    async def get_all_for_conversation(
        self,
        conversation_id: int,
    ) -> list[Message]:
        """Get all messages for display, ordered oldest-first."""
        cursor = await self._db.execute(
            """
            SELECT id, conversation_id, role, content, timestamp, status
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            """,
            (conversation_id,),
        )
        rows = await cursor.fetchall()

        return [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                status=row["status"],
            )
            for row in rows
        ]

    async def update_status(
        self,
        message_id: int,
        status: str,
    ) -> None:
        """Update message status (pending -> sent/failed)."""
        await self._db.execute(
            "UPDATE messages SET status = ? WHERE id = ?",
            (status, message_id),
        )
        await self._db.commit()
