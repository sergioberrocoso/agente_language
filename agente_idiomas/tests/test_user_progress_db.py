"""Tests para la persistencia de progreso de usuario (UserProgressDB)."""

import os
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from db.user_progress_db import UserProgressDB


class UserProgressDBTests(unittest.TestCase):
    def setUp(self):
        self.db = UserProgressDB(db_path=":memory:")

    def tearDown(self):
        self.db.close()

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def test_set_and_get_preference(self):
        self.db.set_preference(1, "voice_enabled", True)
        self.assertEqual(True, self.db.get_preference(1, "voice_enabled"))

    def test_get_preference_returns_default_when_missing(self):
        result = self.db.get_preference(1, "non_existent_key", default="fallback")
        self.assertEqual("fallback", result)

    def test_update_preference(self):
        self.db.set_preference(1, "language", "en-US")
        self.db.set_preference(1, "language", "es-ES")
        self.assertEqual("es-ES", self.db.get_preference(1, "language"))

    def test_preferences_isolated_by_user(self):
        self.db.set_preference(1, "theme", "dark")
        self.db.set_preference(2, "theme", "light")
        self.assertEqual("dark", self.db.get_preference(1, "theme"))
        self.assertEqual("light", self.db.get_preference(2, "theme"))

    def test_get_all_preferences(self):
        self.db.set_preference(1, "key1", "value1")
        self.db.set_preference(1, "key2", 42)
        prefs = self.db.get_all_preferences(1)
        self.assertIn("key1", prefs)
        self.assertIn("key2", prefs)
        self.assertEqual("value1", prefs["key1"])
        self.assertEqual(42, prefs["key2"])

    def test_preference_supports_complex_values(self):
        self.db.set_preference(1, "tags", ["animals", "food"])
        result = self.db.get_preference(1, "tags")
        self.assertEqual(["animals", "food"], result)

    # ------------------------------------------------------------------
    # Exercise history
    # ------------------------------------------------------------------
    def test_record_exercise_returns_id(self):
        ex_id = self.db.record_exercise(
            user_id=1,
            exercise_type="fill_blank",
            prompt="I ___ a dog.",
            user_answer="have",
            correct=True,
        )
        self.assertIsInstance(ex_id, int)
        self.assertGreater(ex_id, 0)

    def test_get_exercise_history(self):
        self.db.record_exercise(1, "fill_blank", "I ___ a dog.", correct=True)
        self.db.record_exercise(1, "translate", "My cat is small.", correct=False)
        history = self.db.get_exercise_history(1)
        self.assertEqual(2, len(history))

    def test_get_exercise_history_filter_by_mission(self):
        self.db.record_exercise(1, "fill_blank", "Q1", mission_id="m1")
        self.db.record_exercise(1, "translate", "Q2", mission_id="m2")
        history = self.db.get_exercise_history(1, mission_id="m1")
        self.assertEqual(1, len(history))
        self.assertEqual("m1", history[0]["mission_id"])

    def test_exercise_stats_accuracy(self):
        self.db.record_exercise(1, "fill_blank", "Q1", correct=True)
        self.db.record_exercise(1, "fill_blank", "Q2", correct=True)
        self.db.record_exercise(1, "fill_blank", "Q3", correct=False)
        stats = self.db.get_exercise_stats(1)
        self.assertEqual(3, stats["total"])
        self.assertEqual(2, stats["total_correct"])
        self.assertAlmostEqual(0.667, stats["accuracy"], places=2)

    def test_exercise_stats_empty_returns_zero(self):
        stats = self.db.get_exercise_stats(99)
        self.assertEqual(0, stats["total"])
        self.assertEqual(0.0, stats["accuracy"])

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------
    def test_record_turn_and_retrieve(self):
        turn_id = self.db.record_turn(
            user_id=1,
            role="student",
            text="Hello, how are you?",
            corrections=[],
        )
        self.assertIsInstance(turn_id, int)
        history = self.db.get_conversation_history(1)
        self.assertEqual(1, len(history))
        self.assertEqual("student", history[0]["role"])
        self.assertEqual("Hello, how are you?", history[0]["text"])

    def test_conversation_with_corrections(self):
        corrections = [{"rule": "contraction", "original": "dont", "suggested": "don't"}]
        self.db.record_turn(1, "student", "I dont know.", corrections=corrections)
        history = self.db.get_conversation_history(1)
        self.assertEqual(1, len(history))
        self.assertIsInstance(history[0]["corrections"], list)
        self.assertEqual(1, len(history[0]["corrections"]))

    def test_conversation_isolated_by_user(self):
        self.db.record_turn(1, "student", "Hello!")
        self.db.record_turn(2, "student", "Hi!")
        h1 = self.db.get_conversation_history(1)
        h2 = self.db.get_conversation_history(2)
        self.assertEqual(1, len(h1))
        self.assertEqual(1, len(h2))
        self.assertEqual("Hello!", h1[0]["text"])

    # ------------------------------------------------------------------
    # Flashcard states
    # ------------------------------------------------------------------
    def test_upsert_and_get_flashcard_state(self):
        self.db.upsert_flashcard_state(1, "dog", known=True)
        state = self.db.get_flashcard_state(1, "dog")
        self.assertIsNotNone(state)
        self.assertEqual(1, state["known"])
        self.assertEqual(1, state["review_count"])

    def test_flashcard_review_count_increments(self):
        self.db.upsert_flashcard_state(1, "cat", known=False)
        self.db.upsert_flashcard_state(1, "cat", known=True)
        state = self.db.get_flashcard_state(1, "cat")
        self.assertEqual(2, state["review_count"])

    def test_get_unknown_flashcards(self):
        self.db.upsert_flashcard_state(1, "apple", known=True)
        self.db.upsert_flashcard_state(1, "run", known=False)
        self.db.upsert_flashcard_state(1, "travel", known=False)
        unknown = self.db.get_unknown_flashcards(1)
        words = [u["word"] for u in unknown]
        self.assertIn("run", words)
        self.assertIn("travel", words)
        self.assertNotIn("apple", words)

    def test_flashcard_states_isolated_by_user(self):
        self.db.upsert_flashcard_state(1, "book", known=True)
        self.db.upsert_flashcard_state(2, "book", known=False)
        s1 = self.db.get_flashcard_state(1, "book")
        s2 = self.db.get_flashcard_state(2, "book")
        self.assertEqual(1, s1["known"])
        self.assertEqual(0, s2["known"])

    # ------------------------------------------------------------------
    # Progress summary
    # ------------------------------------------------------------------
    def test_progress_summary_structure(self):
        self.db.record_exercise(1, "fill_blank", "Q1", correct=True)
        self.db.record_turn(1, "student", "Hello!")
        self.db.upsert_flashcard_state(1, "dog", known=True)
        summary = self.db.get_progress_summary(1)
        self.assertIn("user_id", summary)
        self.assertIn("exercises", summary)
        self.assertIn("conversation_turns", summary)
        self.assertIn("flashcards", summary)
        self.assertEqual(1, summary["exercises"]["total"])
        self.assertEqual(1, summary["conversation_turns"])
        self.assertEqual(1, summary["flashcards"]["known"])

    # ------------------------------------------------------------------
    # Schema versioning
    # ------------------------------------------------------------------
    def test_schema_version_recorded(self):
        """La versión del esquema se registra durante la inicialización."""
        import sqlite3
        conn = sqlite3.connect(":memory:")
        # Use a fresh DB to check versioning
        fresh_db = UserProgressDB(":memory:")
        # schema_version table should exist and have at least 1 row
        row = fresh_db._conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        self.assertIsNotNone(row[0])
        self.assertGreaterEqual(row[0], 1)
        fresh_db.close()


if __name__ == "__main__":
    unittest.main()
