from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Message:
    session_id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    created_at: datetime


@dataclass(frozen=True)
class SessionSummary:
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime


class ConversationRepository:
    def create_session(self, title: Optional[str] = None, session_id: Optional[str] = None) -> str:
        raise NotImplementedError

    def session_exists(self, session_id: str) -> bool:
        raise NotImplementedError

    def append_message(self, session_id: str, role: str, content: str) -> None:
        raise NotImplementedError

    def get_messages(self, session_id: str, limit: int) -> List[Message]:
        raise NotImplementedError

    def update_session_title_if_empty(self, session_id: str, title: str) -> None:
        raise NotImplementedError

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[SessionSummary]:
        raise NotImplementedError

    def delete_session(self, session_id: str) -> None:
        raise NotImplementedError


class SQLiteConversationRepository(ConversationRepository):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at)"
            )
            conn.commit()

    def create_session(self, title: Optional[str] = None, session_id: Optional[str] = None) -> str:
        sid = session_id or str(uuid.uuid4())
        now = datetime.utcnow()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (id, title, created_at, updated_at) VALUES (?,?,?,?)",
                (sid, title, now, now),
            )
            conn.commit()
        return sid

    def session_exists(self, session_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,)).fetchone()
            return row is not None

    def append_message(self, session_id: str, role: str, content: str) -> None:
        now = datetime.utcnow()
        with self._connect() as conn:
            # Ensure session exists
            if not self.session_exists(session_id):
                self.create_session(session_id=session_id)
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
                (session_id, role, content, now),
            )
            conn.execute(
                "UPDATE sessions SET updated_at=? WHERE id=?",
                (now, session_id),
            )
            conn.commit()

    def get_messages(self, session_id: str, limit: int) -> List[Message]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT session_id, role, content, created_at FROM messages WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        messages = [
            Message(
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
        # Return chronological order
        return list(reversed(messages))

    def update_session_title_if_empty(self, session_id: str, title: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET title=COALESCE(NULLIF(title, ''), ?) WHERE id=?",
                (title, session_id),
            )
            conn.commit()

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[SessionSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [
            SessionSummary(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def delete_session(self, session_id: str) -> None:
        with self._connect() as conn:
            # Delete messages then session
            conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
            conn.commit()
