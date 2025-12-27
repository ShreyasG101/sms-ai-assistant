"""Repository for outgoing message queue."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import aiosqlite


@dataclass
class OutboxMessage:
    """A pending outgoing message."""

    id: int
    phone_number: str
    content: str
    created_at: datetime
    status: str
    sent_at: datetime | None


class OutboxRepository:
    """
    Repository for outgoing message queue.

    Operations are designed to be idempotent where possible,
    following Ousterhout's "define errors out of existence" principle.
    """

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def enqueue(
        self,
        phone_number: str,
        content: str,
    ) -> int:
        """Add message to outbox. Returns message ID."""
        now = datetime.utcnow().isoformat()
        cursor = await self._db.execute(
            """
            INSERT INTO outbox (phone_number, content, created_at, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (phone_number, content, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_pending(self, limit: int = 10) -> list[OutboxMessage]:
        """Get pending messages for phone to send."""
        cursor = await self._db.execute(
            """
            SELECT id, phone_number, content, created_at, status, sent_at
            FROM outbox
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()

        return [
            OutboxMessage(
                id=row["id"],
                phone_number=row["phone_number"],
                content=row["content"],
                created_at=datetime.fromisoformat(row["created_at"]),
                status=row["status"],
                sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
            )
            for row in rows
        ]

    async def acknowledge(
        self,
        message_id: int,
        status: Literal["sent", "failed"],
    ) -> bool:
        """
        Mark message as sent or failed. Idempotent.

        Returns True if message existed and was pending.
        """
        now = datetime.utcnow().isoformat() if status == "sent" else None
        cursor = await self._db.execute(
            """
            UPDATE outbox
            SET status = ?, sent_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (status, now, message_id),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def get_pending_count(self) -> int:
        """Count pending messages (for health check)."""
        cursor = await self._db.execute(
            "SELECT COUNT(*) FROM outbox WHERE status = 'pending'"
        )
        row = await cursor.fetchone()
        return row[0]

    async def cleanup_old(self, days: int = 7) -> int:
        """Remove sent/failed messages older than N days. Returns count deleted."""
        cursor = await self._db.execute(
            """
            DELETE FROM outbox
            WHERE status IN ('sent', 'failed')
            AND created_at < datetime('now', ?)
            """,
            (f"-{days} days",),
        )
        await self._db.commit()
        return cursor.rowcount
