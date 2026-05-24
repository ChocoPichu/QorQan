import json
import os
import sqlite3
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = "qorqan.db"


class DatabaseDAO:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._create_tables()
        self._sync_operators()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        with self._get_connection() as conn:
            # 1. Users
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    lang TEXT DEFAULT 'ru',
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Migration: add lang to existing databases
            try:
                conn.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'ru'")
            except Exception:
                pass
            # 2. Operators
            conn.execute("""
                CREATE TABLE IF NOT EXISTS operators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    display_name TEXT,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- <--- THE MISSING LINK
                )
            """)
            # 3. Sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER,
                    urgency TEXT,
                    status TEXT DEFAULT 'waiting',
                    operator_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    FOREIGN KEY(telegram_id) REFERENCES users(telegram_id),
                    FOREIGN KEY(operator_id) REFERENCES operators(id)
                )
            """)
            # 4. Messages
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    sender_type TEXT,
                    text TEXT,
                    photo_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_read INTEGER DEFAULT 0,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)
            # --- MIGRATION: safely add is_read to existing databases ---
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN is_read INTEGER DEFAULT 0")
            except Exception:
                pass
            # 5. Blacklist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    telegram_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    reason TEXT,
                    banned_by TEXT,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def update_operator_presence(self, operator_id: int):
        """Updates the last_seen timestamp for an operator."""
        with self._get_connection() as conn:
            conn.execute("UPDATE operators SET last_seen = CURRENT_TIMESTAMP WHERE id = ?", (operator_id,))

    def get_online_operators_count(self) -> int:
        """Counts operators active in the last 60 seconds."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM operators
                WHERE last_seen > datetime('now', '-1 minute')
            """)
            return cursor.fetchone()["count"]

    def _sync_operators(self):
        json_file = "admins.json"

        if not os.path.exists(json_file):
            default_admins = [
                {"username": "admin", "password": "123", "display_name": "Admin Boss"},
                {"username": "op1", "password": "123", "display_name": "Operator One"},
                {"username": "op2", "password": "123", "display_name": "Operator Two"},
            ]
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(default_admins, f, indent=4)

        with open(json_file, encoding="utf-8") as f:
            admins = json.load(f)

        with self._get_connection() as conn:
            for admin in admins:
                cursor = conn.execute("SELECT id FROM operators WHERE username = ?", (admin["username"],))
                if not cursor.fetchone():
                    pwd_hash = generate_password_hash(admin["password"])
                    conn.execute(
                        "INSERT INTO operators (username, password_hash, display_name) VALUES (?, ?, ?)",
                        (admin["username"], pwd_hash, admin["display_name"]),
                    )

    # --- AUTHENTICATION METHODS ---
    def verify_operator(self, username, password) -> dict | None:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM operators WHERE username = ?", (username,))
            operator = cursor.fetchone()
            if operator and check_password_hash(operator["password_hash"], password):
                return dict(operator)
            return None

    def get_operator_by_id(self, operator_id) -> dict | None:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM operators WHERE id = ?", (operator_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # --- USER METHODS ---
    def upsert_user(self, telegram_id: int, full_name: str, username: str, lang: str = None):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (telegram_id, full_name, username, lang)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    full_name=excluded.full_name,
                    username=excluded.username,
                    lang=COALESCE(excluded.lang, lang),
                    last_seen=CURRENT_TIMESTAMP
            """,
                (telegram_id, full_name, username, lang),
            )

    def get_user_lang(self, telegram_id: int) -> str:
        """Returns the user's preferred language code, defaulting to 'ru'."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT lang FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            if row and row["lang"]:
                return row["lang"]
            return "ru"

    # --- SESSION METHODS ---
    def create_session(self, telegram_id: int, urgency: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (telegram_id, urgency, status)
                VALUES (?, ?, 'waiting')
            """,
                (telegram_id, urgency),
            )
            return cursor.lastrowid

    def get_active_session(self, telegram_id: int) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sessions
                WHERE telegram_id = ? AND status IN ('waiting', 'active')
                ORDER BY created_at DESC LIMIT 1
            """,
                (telegram_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_session_status(self, session_id: int, status: str, operator_id: int = None):
        with self._get_connection() as conn:
            if status == "closed":
                conn.execute(
                    """
                    UPDATE sessions SET status = ?, closed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (status, session_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE sessions SET status = ?, operator_id = ?
                    WHERE id = ?
                """,
                    (status, operator_id, session_id),
                )

    def get_session_by_id(self, session_id: int) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # --- BLACKLIST METHODS ---
    def is_banned(self, telegram_id: int) -> bool:
        """Returns True if the user is on the blacklist."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM blacklist WHERE telegram_id = ?", (telegram_id,))
            return cursor.fetchone() is not None

    def ban_user(self, telegram_id: int, full_name: str, username: str, reason: str, banned_by: str):
        """Adds a user to the blacklist. Silently ignores if already banned."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO blacklist
                    (telegram_id, full_name, username, reason, banned_by)
                VALUES (?, ?, ?, ?, ?)
            """,
                (telegram_id, full_name, username, reason, banned_by),
            )

    def unban_user(self, telegram_id: int):
        """Removes a user from the blacklist."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM blacklist WHERE telegram_id = ?", (telegram_id,))

    def get_blacklist(self) -> list[dict[str, Any]]:
        """Returns all blacklisted users, newest first."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM blacklist ORDER BY banned_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    # --- DASHBOARD METHODS (UPDATED FOR MULTI-OPERATOR) ---
    def get_dashboard_tickets(self, operator_id: int) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT s.id, s.urgency, s.status, s.operator_id, s.created_at,
                       u.full_name, u.username,
                       EXISTS(
                           SELECT 1 FROM messages m
                           WHERE m.session_id = s.id
                             AND m.sender_type = 'kid'
                             AND m.is_read = 0
                       ) AS has_unread
                FROM sessions s
                JOIN users u ON s.telegram_id = u.telegram_id
                WHERE s.status = 'waiting' OR (s.status = 'active' AND s.operator_id = ?)
                ORDER BY s.status DESC, s.created_at ASC
            """,
                (operator_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # --- MESSAGE METHODS ---
    def add_message(self, session_id: int, sender_type: str, text: str, photo_id: str = None):
        """Inserts a new message. Kid messages start as unread (is_read=0)."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (session_id, sender_type, text, photo_id, is_read)
                VALUES (?, ?, ?, ?, 0)
            """,
                (session_id, sender_type, text, photo_id),
            )

    def mark_messages_read(self, session_id: int):
        """Marks all messages in a session as read. Called when operator opens a ticket."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE messages SET is_read = 1
                WHERE session_id = ? AND is_read = 0
            """,
                (session_id,),
            )

    def get_session_messages(self, session_id: int) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC
            """,
                (session_id,),
            )
            return [dict(row) for row in cursor.fetchall()]


db = DatabaseDAO()
