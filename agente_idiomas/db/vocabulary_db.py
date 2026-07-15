"""Base de datos SQLite de vocabulario cargada desde el listado NGSL."""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Categorías temáticas: mapeo headword → lista de tags
# ---------------------------------------------------------------------------
_CATEGORY_MAP: dict[str, list[str]] = {
    "animals": [
        "animal", "dog", "cat", "bird", "fish", "horse", "cow", "pig", "sheep",
        "lion", "tiger", "elephant", "bear", "wolf", "rabbit", "mouse", "rat",
        "snake", "frog", "chicken", "duck", "deer", "fox", "monkey", "whale",
        "shark", "insect", "fly", "bee", "ant", "butterfly", "pet",
    ],
    "food": [
        "food", "eat", "drink", "bread", "water", "milk", "fruit", "vegetable",
        "meat", "rice", "coffee", "tea", "sugar", "salt", "meal", "lunch",
        "dinner", "breakfast", "cook", "restaurant", "menu", "cheese", "egg",
        "butter", "oil", "wine", "beer", "juice", "soup", "cake", "chocolate",
        "fish", "chicken", "beef", "pork", "potato", "tomato", "onion",
        "apple", "banana", "orange", "diet", "hunger", "hungry", "thirsty",
    ],
    "travel": [
        "travel", "trip", "airport", "hotel", "flight", "ticket", "passport",
        "luggage", "bus", "train", "car", "boat", "road", "map", "destination",
        "journey", "tourist", "tourism", "visa", "border", "station",
        "reservation", "guide", "foreign", "abroad", "depart", "arrive",
        "departure", "arrival", "taxi", "subway", "highway", "path", "route",
    ],
    "home": [
        "house", "home", "door", "room", "bed", "kitchen", "bathroom",
        "window", "garden", "floor", "wall", "roof", "furniture", "chair",
        "table", "sofa", "lamp", "curtain", "shelf", "cupboard", "closet",
        "apartment", "flat", "neighbor", "rent", "landlord", "move",
        "toilet", "shower", "garage", "yard",
    ],
    "actions": [
        "run", "walk", "eat", "sleep", "work", "play", "read", "write",
        "speak", "listen", "watch", "go", "come", "take", "give", "make",
        "do", "see", "know", "want", "think", "say", "tell", "ask", "help",
        "start", "stop", "open", "close", "put", "get", "bring", "carry",
        "move", "stand", "sit", "jump", "push", "pull", "throw", "catch",
        "drive", "ride", "swim", "climb", "fall", "rise", "turn", "hold",
        "wait", "choose", "try", "keep", "leave", "follow", "meet", "find",
        "lose", "win", "show", "send", "receive", "call", "visit", "return",
    ],
    "emotions": [
        "happy", "sad", "angry", "love", "hate", "fear", "hope", "worry",
        "enjoy", "like", "feel", "laugh", "cry", "smile", "surprise",
        "afraid", "lonely", "proud", "sorry", "glad", "upset", "excited",
        "nervous", "calm", "bored", "tired", "stress", "anxiety", "joy",
        "pleasure", "pain", "suffer", "regret", "jealous", "embarrass",
        "confidence", "courage", "shame", "disgust", "trust",
    ],
    "time": [
        "day", "week", "month", "year", "hour", "minute", "second",
        "morning", "afternoon", "evening", "night", "today", "yesterday",
        "tomorrow", "now", "then", "early", "late", "always", "never",
        "often", "sometimes", "soon", "already", "still", "again", "once",
        "before", "after", "during", "since", "until", "while", "season",
        "century", "decade", "period", "moment", "recent", "past", "future",
    ],
    "numbers": [
        "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "hundred", "thousand", "million",
        "first", "second", "third", "fourth", "fifth", "half", "quarter",
        "double", "triple", "dozen", "zero", "count", "number", "amount",
        "percent", "total", "sum", "average", "maximum", "minimum",
    ],
    "body": [
        "body", "head", "eye", "ear", "nose", "mouth", "hand", "foot",
        "leg", "arm", "heart", "face", "hair", "back", "shoulder", "knee",
        "finger", "tooth", "tongue", "neck", "chest", "stomach", "brain",
        "bone", "blood", "skin", "muscle", "health", "pain", "sick",
        "doctor", "hospital", "medicine", "disease", "illness", "symptom",
        "weight", "height",
    ],
    "work": [
        "work", "job", "office", "company", "boss", "colleague", "salary",
        "business", "meeting", "project", "report", "manager", "employee",
        "career", "profession", "industry", "economy", "market", "trade",
        "money", "pay", "earn", "spend", "cost", "price", "budget",
        "contract", "deadline", "task", "responsibility", "skill",
        "experience", "interview", "hire", "fire", "retire",
    ],
    "school": [
        "school", "student", "teacher", "class", "lesson", "study", "learn",
        "book", "homework", "university", "college", "exam", "test", "grade",
        "education", "knowledge", "subject", "history", "science", "math",
        "language", "literature", "art", "music", "sport", "library",
        "campus", "course", "degree", "graduate", "research", "lecture",
        "note", "pen", "pencil", "paper", "board", "rule",
    ],
    "weather": [
        "weather", "rain", "snow", "sun", "wind", "cloud", "hot", "cold",
        "warm", "cool", "temperature", "storm", "fog", "ice", "season",
        "summer", "winter", "spring", "autumn", "flood", "drought",
        "climate", "forecast", "degree", "humidity", "thunder", "lightning",
    ],
    "colors": [
        "red", "blue", "green", "yellow", "white", "black", "brown",
        "orange", "pink", "purple", "grey", "gray", "color", "colour",
        "light", "dark", "bright", "pale", "shade", "tone",
    ],
    "people": [
        "people", "person", "man", "woman", "child", "children", "family",
        "parent", "mother", "father", "sister", "brother", "friend",
        "neighbor", "husband", "wife", "couple", "baby", "adult", "senior",
        "teenager", "generation", "individual", "human", "population",
        "society", "community", "crowd", "group", "team", "partner",
        "relative", "grandmother", "grandfather", "uncle", "aunt", "cousin",
    ],
    "technology": [
        "computer", "phone", "internet", "software", "application", "app",
        "system", "digital", "data", "network", "email", "website", "online",
        "device", "screen", "keyboard", "mouse", "program", "code", "file",
        "download", "upload", "video", "photo", "camera", "message", "text",
        "search", "social", "media", "technology", "science", "machine",
    ],
    "nature": [
        "nature", "tree", "flower", "plant", "grass", "forest", "mountain",
        "river", "lake", "sea", "ocean", "beach", "island", "desert", "land",
        "earth", "sky", "star", "moon", "sun", "air", "water", "fire",
        "stone", "rock", "soil", "leaf", "branch", "root", "seed",
    ],
}

# Build an inverted index: headword → set of tags
_WORD_TAGS: dict[str, list[str]] = {}
for _tag, _words in _CATEGORY_MAP.items():
    for _w in _words:
        _WORD_TAGS.setdefault(_w, [])
        if _tag not in _WORD_TAGS[_w]:
            _WORD_TAGS[_w].append(_tag)


# ---------------------------------------------------------------------------
# VocabularyDB
# ---------------------------------------------------------------------------
class VocabularyDB:
    """Base de datos SQLite de vocabulario.

    Se inicializa una sola vez desde el CSV del NGSL. Las consultas
    posteriores son O(log n) gracias al índice del headword.
    """

    def __init__(self, db_path: str = ":memory:", ngsl_csv_path: Optional[str] = None):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._create_schema()
        if ngsl_csv_path:
            self.load_from_ngsl(ngsl_csv_path)

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _create_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    headword       TEXT    NOT NULL UNIQUE,
                    forms          TEXT    NOT NULL DEFAULT '[]',
                    tags           TEXT    NOT NULL DEFAULT '[]',
                    frequency_rank INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_vocabulary_headword
                    ON vocabulary(headword);
                """
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load_from_ngsl(self, csv_path: str) -> int:
        """Parsea el CSV del NGSL e inserta las entradas en la BD.

        Devuelve el número de palabras insertadas.
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"NGSL CSV no encontrado: {csv_path}")

        entries: list[tuple] = []
        rank = 1
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(",") if p.strip()]
            if not parts:
                continue

            headword = parts[0]
            forms = parts  # first element is the canonical headword
            tags = _WORD_TAGS.get(headword, [])

            entries.append((headword, json.dumps(forms, ensure_ascii=False),
                            json.dumps(tags, ensure_ascii=False), rank))
            rank += 1

        with self._lock:
            self._conn.executemany(
                "INSERT OR IGNORE INTO vocabulary (headword, forms, tags, frequency_rank) "
                "VALUES (?, ?, ?, ?)",
                entries,
            )
            self._conn.commit()
        return len(entries)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Busca palabras cuyo headword o formas contengan *query*."""
        q = f"%{query.lower()}%"
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM vocabulary "
                "WHERE lower(headword) LIKE ? OR lower(forms) LIKE ? "
                "ORDER BY frequency_rank "
                "LIMIT ?",
                (q, q, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_by_headword(self, headword: str) -> Optional[dict]:
        """Devuelve la entrada exacta para un headword, o None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM vocabulary WHERE lower(headword) = lower(?)",
                (headword,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_by_tags(self, tags: list[str], limit: int = 50) -> list[dict]:
        """Devuelve palabras que tengan al menos uno de los tags indicados."""
        if not tags:
            return []
        results: list[dict] = []
        seen: set[int] = set()
        for tag in tags:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM vocabulary "
                    "WHERE tags LIKE ? "
                    "ORDER BY frequency_rank "
                    "LIMIT ?",
                    (f'%"{tag}"%', limit),
                ).fetchall()
            for r in rows:
                d = self._row_to_dict(r)
                if d["id"] not in seen:
                    seen.add(d["id"])
                    results.append(d)
        return results[:limit]

    def get_by_rank_range(self, min_rank: int = 1, max_rank: int = 500) -> list[dict]:
        """Devuelve palabras en un rango de frecuencia."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM vocabulary "
                "WHERE frequency_rank BETWEEN ? AND ? "
                "ORDER BY frequency_rank",
                (min_rank, max_rank),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["forms"] = json.loads(d["forms"])
        d["tags"] = json.loads(d["tags"])
        return d

    def close(self) -> None:
        self._conn.close()
