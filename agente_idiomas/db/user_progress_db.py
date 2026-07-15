"""Persistencia de progreso de usuario: historial, preferencias y estado de flashcards."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Optional


# Current schema version — bump when adding migrations
_SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserProgressDB:
    """Base de datos SQLite para almacenar el progreso de usuario.

    Tablas:
        schema_version  — versión del esquema para futuras migraciones
        preferences     — pares clave/valor por usuario
        exercise_history — registro de ejercicios realizados
        conversation_history — historial de conversaciones
        flashcard_states — estado de revisión de cada flashcard por usuario

    Cada tabla incluye ``user_id`` para aislar datos entre usuarios.
    Cuando se usa como base de datos de proceso único (sin auth) se puede
    emplear user_id=0 como usuario anónimo por defecto.
    """

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            isolation_level="DEFERRED",
        )
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._create_schema()
        self._run_migrations()

    # ------------------------------------------------------------------
    # Schema & migrations
    # ------------------------------------------------------------------
    def _create_schema(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version     INTEGER PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL DEFAULT 0,
                    key         TEXT    NOT NULL,
                    value       TEXT    NOT NULL,
                    updated_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, key)
                );

                CREATE TABLE IF NOT EXISTS exercise_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL DEFAULT 0,
                    mission_id  TEXT,
                    exercise_type TEXT NOT NULL,
                    prompt      TEXT NOT NULL,
                    user_answer TEXT,
                    correct     INTEGER NOT NULL DEFAULT 0,
                    difficulty  TEXT,
                    feedback    TEXT,
                    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_exhist_user ON exercise_history(user_id);

                CREATE TABLE IF NOT EXISTS conversation_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL DEFAULT 0,
                    mission_id  TEXT,
                    role        TEXT NOT NULL,
                    text        TEXT NOT NULL,
                    corrections TEXT DEFAULT '[]',
                    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_convhist_user ON conversation_history(user_id);

                CREATE TABLE IF NOT EXISTS flashcard_states (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL DEFAULT 0,
                    word        TEXT    NOT NULL,
                    source      TEXT    NOT NULL DEFAULT 'mission',
                    known       INTEGER NOT NULL DEFAULT 0,
                    review_count INTEGER NOT NULL DEFAULT 0,
                    last_reviewed TEXT,
                    next_review   TEXT,
                    UNIQUE(user_id, word)
                );
                CREATE INDEX IF NOT EXISTS idx_fc_user ON flashcard_states(user_id);
                """
            )
            self._conn.commit()

    def _run_migrations(self) -> None:
        """Aplica migraciones pendientes en orden."""
        with self._lock:
            row = self._conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            current = row[0] if row[0] is not None else 0

        # Each migration is keyed by the version it produces.
        # Version 1 is the baseline (already created above).
        migrations: dict[int, str] = {
            # Example of a future migration (placeholder):
            # 2: "ALTER TABLE preferences ADD COLUMN ...",
        }

        with self._lock:
            for version in sorted(migrations):
                if version > current:
                    self._conn.executescript(migrations[version])
                    self._conn.execute(
                        "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                        (version,),
                    )
                    self._conn.commit()
                    current = version

            # Record baseline version if not yet recorded
            if current < _SCHEMA_VERSION:
                self._conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                    (_SCHEMA_VERSION,),
                )
                self._conn.commit()

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def set_preference(self, user_id: int, key: str, value: Any) -> None:
        """Guarda o actualiza una preferencia de usuario."""
        serialized = json.dumps(value, ensure_ascii=False)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO preferences (user_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (user_id, key, serialized, _now_iso()),
            )
            self._conn.commit()

    def get_preference(self, user_id: int, key: str, default: Any = None) -> Any:
        """Recupera una preferencia de usuario."""
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM preferences WHERE user_id=? AND key=?",
                (user_id, key),
            ).fetchone()
        return json.loads(row["value"]) if row else default

    def get_all_preferences(self, user_id: int) -> dict:
        """Devuelve todas las preferencias de un usuario."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, value FROM preferences WHERE user_id=?",
                (user_id,),
            ).fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    # ------------------------------------------------------------------
    # Exercise history
    # ------------------------------------------------------------------
    def record_exercise(
        self,
        user_id: int,
        exercise_type: str,
        prompt: str,
        user_answer: Optional[str] = None,
        correct: bool = False,
        mission_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        feedback: Optional[str] = None,
    ) -> int:
        """Registra un ejercicio realizado. Devuelve el ID insertado."""
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO exercise_history
                    (user_id, mission_id, exercise_type, prompt, user_answer, correct,
                     difficulty, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, mission_id, exercise_type, prompt,
                    user_answer, int(correct), difficulty, feedback, _now_iso(),
                ),
            )
            self._conn.commit()
            return cursor.lastrowid

    def get_exercise_history(
        self,
        user_id: int,
        limit: int = 50,
        mission_id: Optional[str] = None,
    ) -> list[dict]:
        """Devuelve el historial de ejercicios de un usuario."""
        if mission_id:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM exercise_history WHERE user_id=? AND mission_id=? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (user_id, mission_id, limit),
                ).fetchall()
        else:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM exercise_history WHERE user_id=? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
        return [dict(r) for r in rows]

    def get_exercise_stats(self, user_id: int) -> dict:
        """Devuelve estadísticas de ejercicios del usuario."""
        with self._lock:
            row = self._conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(correct) as total_correct,
                    COUNT(DISTINCT mission_id) as missions_practiced,
                    COUNT(DISTINCT exercise_type) as exercise_types_used
                FROM exercise_history WHERE user_id=?
                """,
                (user_id,),
            ).fetchone()
        if not row:
            return {"total": 0, "total_correct": 0, "accuracy": 0.0}
        total = row["total"] or 0
        correct = row["total_correct"] or 0
        return {
            "total": total,
            "total_correct": correct,
            "accuracy": round(correct / total, 3) if total > 0 else 0.0,
            "missions_practiced": row["missions_practiced"] or 0,
            "exercise_types_used": row["exercise_types_used"] or 0,
        }

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------
    def record_turn(
        self,
        user_id: int,
        role: str,
        text: str,
        corrections: Optional[list] = None,
        mission_id: Optional[str] = None,
    ) -> int:
        """Registra un turno de conversación. Devuelve el ID insertado."""
        serialized_corrections = json.dumps(corrections or [], ensure_ascii=False)
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO conversation_history
                    (user_id, mission_id, role, text, corrections, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, mission_id, role, text, serialized_corrections, _now_iso()),
            )
            self._conn.commit()
            return cursor.lastrowid

    def get_conversation_history(
        self,
        user_id: int,
        limit: int = 100,
        mission_id: Optional[str] = None,
    ) -> list[dict]:
        """Devuelve el historial de conversaciones de un usuario."""
        if mission_id:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM conversation_history WHERE user_id=? AND mission_id=? "
                    "ORDER BY created_at ASC LIMIT ?",
                    (user_id, mission_id, limit),
                ).fetchall()
        else:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM conversation_history WHERE user_id=? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["corrections"] = json.loads(d.get("corrections") or "[]")
            result.append(d)
        return result

    # ------------------------------------------------------------------
    # Flashcard states
    # ------------------------------------------------------------------
    def upsert_flashcard_state(
        self,
        user_id: int,
        word: str,
        known: bool,
        source: str = "mission",
    ) -> None:
        """Actualiza el estado de una flashcard (conocida/desconocida)."""
        with self._lock:
            existing = self._conn.execute(
                "SELECT review_count FROM flashcard_states WHERE user_id=? AND word=?",
                (user_id, word),
            ).fetchone()
            count = (existing["review_count"] + 1) if existing else 1
            self._conn.execute(
                """
                INSERT INTO flashcard_states
                    (user_id, word, source, known, review_count, last_reviewed)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, word) DO UPDATE SET
                    known=excluded.known,
                    review_count=excluded.review_count,
                    last_reviewed=excluded.last_reviewed,
                    source=excluded.source
                """,
                (user_id, word, source, int(known), count, _now_iso()),
            )
            self._conn.commit()

    def get_flashcard_states(self, user_id: int) -> list[dict]:
        """Devuelve todos los estados de flashcards del usuario."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM flashcard_states WHERE user_id=? ORDER BY word",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_flashcard_state(self, user_id: int, word: str) -> Optional[dict]:
        """Devuelve el estado de una flashcard concreta."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM flashcard_states WHERE user_id=? AND word=?",
                (user_id, word),
            ).fetchone()
        return dict(row) if row else None

    def get_unknown_flashcards(self, user_id: int) -> list[dict]:
        """Devuelve las flashcards marcadas como desconocidas."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM flashcard_states WHERE user_id=? AND known=0 ORDER BY review_count ASC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Progress summary
    # ------------------------------------------------------------------
    def get_progress_summary(self, user_id: int) -> dict:
        """Devuelve un resumen del progreso del usuario."""
        exercise_stats = self.get_exercise_stats(user_id)
        with self._lock:
            conv_count = self._conn.execute(
                "SELECT COUNT(*) FROM conversation_history WHERE user_id=? AND role='student'",
                (user_id,),
            ).fetchone()[0]
            fc_total = self._conn.execute(
                "SELECT COUNT(*) FROM flashcard_states WHERE user_id=?",
                (user_id,),
            ).fetchone()[0]
            fc_known = self._conn.execute(
                "SELECT COUNT(*) FROM flashcard_states WHERE user_id=? AND known=1",
                (user_id,),
            ).fetchone()[0]
        return {
            "user_id": user_id,
            "exercises": exercise_stats,
            "conversation_turns": conv_count,
            "flashcards": {
                "total": fc_total,
                "known": fc_known,
                "unknown": fc_total - fc_known,
            },
            "preferences": self.get_all_preferences(user_id),
        }

    def close(self) -> None:
        self._conn.close()
