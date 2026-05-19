"""
session_store.py — SQLite-backed chat history.

Stores all messages per session_id.
No external setup needed — SQLite is built into Python.
DB file: backend/hr_chat_history.db (auto-created)
"""
import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime


DB_PATH = Path(__file__).parent.parent / "hr_chat_history.db"


def _get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Called at app startup."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL,       -- 'user' or 'assistant'
                content     TEXT NOT NULL,       -- message text
                agent       TEXT DEFAULT '',     -- which agent responded
                metadata    TEXT DEFAULT '{}',   -- JSON: sources, action_card, etc.
                timestamp   REAL NOT NULL        -- unix timestamp
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON messages (session_id, timestamp)
        """)
        conn.commit()


def save_message(
    session_id: str,
    role: str,
    content: str,
    agent: str = "",
    metadata: dict = None,
):
    """Save a message to the database."""
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (session_id, role, content, agent, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                content,
                agent,
                json.dumps(metadata or {}),
                time.time(),
            ),
        )
        conn.commit()


def get_history(session_id: str, limit: int = 50) -> list[dict]:
    """Get recent chat history for a session."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content, agent, metadata, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()

    messages = []
    for row in reversed(rows):  # return in chronological order
        messages.append({
            "role": row["role"],
            "content": row["content"],
            "agent": row["agent"],
            "metadata": json.loads(row["metadata"]),
            "timestamp": datetime.fromtimestamp(row["timestamp"]).isoformat(),
        })

    return messages


def get_all_sessions() -> list[dict]:
    """Get a summary of all chat sessions (for admin view)."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                session_id,
                COUNT(*) as message_count,
                MIN(timestamp) as started_at,
                MAX(timestamp) as last_active
            FROM messages
            GROUP BY session_id
            ORDER BY last_active DESC
            LIMIT 100
            """
        ).fetchall()

    return [
        {
            "session_id": row["session_id"],
            "message_count": row["message_count"],
            "started_at": datetime.fromtimestamp(row["started_at"]).isoformat(),
            "last_active": datetime.fromtimestamp(row["last_active"]).isoformat(),
        }
        for row in rows
    ]


def clear_session(session_id: str):
    """Delete all messages for a session."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()