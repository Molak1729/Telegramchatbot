"""SQLite persistence for to-dos and reminders.

Uses a thread-safe connection because APScheduler and the bot run in
different threads. All writes are committed immediately.
"""
import sqlite3
import threading
from datetime import datetime
from typing import Optional

import config

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db() -> None:
    conn = _connect()
    with _lock:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                task       TEXT    NOT NULL,
                done       INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                text       TEXT    NOT NULL,
                due_at     TEXT    NOT NULL,   -- ISO 8601 UTC
                fired      INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL
            );
            """
        )
        conn.commit()


# ---------------- To-dos ----------------

def add_todo(chat_id: int, task: str) -> int:
    conn = _connect()
    with _lock:
        cur = conn.execute(
            "INSERT INTO todos (chat_id, task, created_at) VALUES (?, ?, ?)",
            (chat_id, task, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def list_todos(chat_id: int, include_done: bool = False):
    conn = _connect()
    with _lock:
        query = "SELECT * FROM todos WHERE chat_id = ?"
        if not include_done:
            query += " AND done = 0"
        query += " ORDER BY id"
        return conn.execute(query, (chat_id,)).fetchall()


def complete_todo(chat_id: int, todo_id: int) -> bool:
    conn = _connect()
    with _lock:
        cur = conn.execute(
            "UPDATE todos SET done = 1 WHERE id = ? AND chat_id = ?",
            (todo_id, chat_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ---------------- Reminders ----------------

def add_reminder(chat_id: int, text: str, due_at_utc: datetime) -> int:
    conn = _connect()
    with _lock:
        cur = conn.execute(
            "INSERT INTO reminders (chat_id, text, due_at, created_at) "
            "VALUES (?, ?, ?, ?)",
            (chat_id, text, due_at_utc.isoformat(), datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def pending_reminders():
    """Reminders that have not fired yet, oldest due first."""
    conn = _connect()
    with _lock:
        return conn.execute(
            "SELECT * FROM reminders WHERE fired = 0 ORDER BY due_at"
        ).fetchall()


def mark_reminder_fired(reminder_id: int) -> None:
    conn = _connect()
    with _lock:
        conn.execute(
            "UPDATE reminders SET fired = 1 WHERE id = ?", (reminder_id,)
        )
        conn.commit()
