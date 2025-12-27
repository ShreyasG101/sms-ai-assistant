"""Database connection management and auto-migration."""

import logging
from pathlib import Path
from typing import AsyncGenerator

import aiosqlite

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Schema version for future migrations
SCHEMA_VERSION = 1

SCHEMA = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'received' CHECK (status IN ('received', 'pending', 'sent', 'failed')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Outbox table for pending outgoing messages
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    sent_at TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
"""


async def init_db() -> None:
    """Initialize database with schema. Creates data directory if needed."""
    settings = get_settings()
    db_path = Path(settings.database_path)

    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")

        # Check current schema version
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        table_exists = await cursor.fetchone()

        if not table_exists:
            # Fresh database - create all tables
            await db.executescript(SCHEMA)
            await db.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
            )
            await db.commit()
            logger.info(f"Database initialized with schema version {SCHEMA_VERSION}")
        else:
            # Check version for future migrations
            cursor = await db.execute("SELECT version FROM schema_version")
            row = await cursor.fetchone()
            current_version = row[0] if row else 0

            if current_version < SCHEMA_VERSION:
                # Future: run migrations here
                logger.info(
                    f"Database migration needed: {current_version} -> {SCHEMA_VERSION}"
                )

    logger.info(f"Database ready at {db_path}")


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield a database connection."""
    settings = get_settings()
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()
