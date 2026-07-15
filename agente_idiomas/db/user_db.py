"""Base de datos SQLite para usuarios de autenticación."""

from __future__ import annotations

import sqlite3
import threading
from typing import Optional


class UserDB:
    """Persistencia de usuarios en SQLite."""

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            isolation_level="IMMEDIATE",
        )
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._create_schema()

    def _create_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._conn.commit()

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return dict(row)

    def create_user(self, email: str, password_hash: str) -> dict:
        normalized_email = self._normalize_email(email)
        with self._lock:
            try:
                cursor = self._conn.execute(
                    "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                    (normalized_email, password_hash),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("User already exists") from exc
            user_id = cursor.lastrowid

        created = self.get_by_id(user_id)
        if created is None:
            raise RuntimeError("Failed to create user")
        return created

    def get_by_email(self, email: str) -> Optional[dict]:
        normalized_email = self._normalize_email(email)
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (normalized_email,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def close(self) -> None:
        self._conn.close()
