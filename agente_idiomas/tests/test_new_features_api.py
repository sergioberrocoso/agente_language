"""Tests de las nuevas rutas de la API: voz, progreso y CSV."""

import io
import os
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi.testclient import TestClient

from api.app import app
import api.deps as deps


def _make_test_agent():
    from agent.language_tutor import LanguageTutorAgent
    agent = LanguageTutorAgent(language="English")
    agent.core_vocab = [
        {"word": "dog",  "tags": ["animals"], "definition": "A pet", "example": "I have a dog.", "translation": "perro"},
        {"word": "cat",  "tags": ["animals"], "definition": "A pet", "example": "I have a cat.", "translation": "gato"},
        {"word": "eat",  "tags": ["food", "actions"], "definition": "To consume food", "example": "We eat.", "translation": "comer"},
    ]
    agent.missions = [
        {
            "id": "mission_001",
            "name": "At the park",
            "goal": "Learn animals and actions",
            "vocabulary_tags": ["animals", "actions"],
            "dialogues": [
                {"speaker": "Tutor",   "text": "Do you have any pets?"},
                {"speaker": "Student", "text": "Yes, I have a dog."},
            ],
            "exercises": [
                {"type": "fill_blank", "text": "I walk my dog.", "blanks": ["walk"],
                 "difficulty": "beginner", "feedback": "Good job!"},
            ],
        }
    ]
    return agent


class APIVoiceTests(unittest.TestCase):
    def setUp(self):
        deps._agent = _make_test_agent()
        # Reset voice session
        import api.routes.voice as voice_module
        voice_module._voice_session = None
        self.client = TestClient(app)

    def tearDown(self):
        deps._agent = None
        deps._vocab_db = None

    def test_voice_capabilities_returns_structure(self):
        r = self.client.get("/voice/capabilities")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIn("stt", data)
        self.assertIn("tts", data)
        self.assertIn("config", data)

    def test_voice_capabilities_shows_available_field(self):
        r = self.client.get("/voice/capabilities")
        data = r.json()
        # These keys must exist (availability depends on installed packages)
        self.assertIn("available", data["stt"])
        self.assertIn("available", data["tts"])

    def test_voice_text_turn_returns_response(self):
        r = self.client.post("/voice/turn/text", json={"text": "Hello!"})
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIn("response", data)
        self.assertIn("corrections", data)
        self.assertIn("turn", data)
        self.assertIn("fallback_to_text", data)

    def test_voice_text_turn_with_grammar_error(self):
        r = self.client.post("/voice/turn/text", json={
            "text": "He go to school every day",
        })
        self.assertEqual(200, r.status_code)
        data = r.json()
        rules = [c["rule"] for c in data["corrections"]]
        self.assertIn("third_person_singular", rules)

    def test_voice_text_turn_corrections_include_why(self):
        r = self.client.post("/voice/turn/text", json={
            "text": "I dont know the answer",
        })
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertGreater(len(data["corrections"]), 0)
        c = data["corrections"][0]
        self.assertIn("why", c)

    def test_voice_config_update(self):
        r = self.client.post("/voice/config", json={
            "enabled": True,
            "language": "es-ES",
            "tts_backend": "none",
            "stt_backend": "none",
        })
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual("es-ES", data["config"]["language"])
        self.assertEqual("none", data["config"]["tts_backend"])

    def test_voice_session_reset(self):
        r = self.client.post("/voice/session/reset")
        self.assertEqual(200, r.status_code)
        self.assertEqual("session_reset", r.json()["status"])

    def test_voice_turn_maintains_history(self):
        """Successive turns should increment turn counter."""
        r1 = self.client.post("/voice/turn/text", json={"text": "Hello!"})
        r2 = self.client.post("/voice/turn/text", json={"text": "I love dogs"})
        self.assertEqual(200, r1.status_code)
        self.assertEqual(200, r2.status_code)
        # turn 2 should be higher than turn 1
        self.assertGreater(r2.json()["turn"], r1.json()["turn"])


class APIProgressTests(unittest.TestCase):
    def setUp(self):
        deps._agent = _make_test_agent()
        deps._user_progress_db = None
        os.environ["USER_PROGRESS_DB_PATH"] = ":memory:"
        self.client = TestClient(app)

    def tearDown(self):
        deps._agent = None
        deps._vocab_db = None
        deps._user_progress_db = None
        os.environ.pop("USER_PROGRESS_DB_PATH", None)

    def test_get_progress_summary(self):
        r = self.client.get("/progress/1")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIn("exercises", data)
        self.assertIn("flashcards", data)
        self.assertIn("conversation_turns", data)

    def test_record_exercise(self):
        r = self.client.post("/progress/1/exercises", json={
            "exercise_type": "fill_blank",
            "prompt": "I ___ a dog.",
            "user_answer": "have",
            "correct": True,
        })
        self.assertEqual(200, r.status_code)
        self.assertTrue(r.json()["recorded"])

    def test_get_exercise_history_after_recording(self):
        self.client.post("/progress/1/exercises", json={
            "exercise_type": "translate",
            "prompt": "My cat is small.",
            "user_answer": "Mi gato es pequeño.",
            "correct": True,
        })
        r = self.client.get("/progress/1/exercises")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIsInstance(data, list)
        self.assertEqual(1, len(data))

    def test_record_and_get_conversation_turn(self):
        self.client.post("/progress/1/conversation", json={
            "role": "student",
            "text": "Hello!",
        })
        r = self.client.get("/progress/1/conversation")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual(1, len(data))
        self.assertEqual("Hello!", data[0]["text"])

    def test_set_and_get_preference(self):
        self.client.post("/progress/1/preferences", json={
            "key": "voice_enabled",
            "value": True,
        })
        r = self.client.get("/progress/1/preferences")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIn("voice_enabled", data)
        self.assertTrue(data["voice_enabled"])

    def test_update_flashcard_state(self):
        r = self.client.post("/progress/1/flashcards", json={
            "word": "dog",
            "known": True,
        })
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual("dog", data["word"])
        self.assertTrue(data["known"])

    def test_get_flashcard_states(self):
        self.client.post("/progress/1/flashcards", json={"word": "cat", "known": False})
        r = self.client.get("/progress/1/flashcards")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIsInstance(data, list)
        self.assertEqual(1, len(data))

    def test_get_unknown_flashcards(self):
        self.client.post("/progress/1/flashcards", json={"word": "apple", "known": True})
        self.client.post("/progress/1/flashcards", json={"word": "run", "known": False})
        r = self.client.get("/progress/1/flashcards/unknown")
        self.assertEqual(200, r.status_code)
        data = r.json()
        words = [d["word"] for d in data]
        self.assertIn("run", words)
        self.assertNotIn("apple", words)

    def test_progress_summary_updates_after_recording(self):
        self.client.post("/progress/1/exercises", json={
            "exercise_type": "fill_blank",
            "prompt": "Test",
            "correct": True,
        })
        r = self.client.get("/progress/1")
        data = r.json()
        self.assertEqual(1, data["exercises"]["total"])


class APICSVImportTests(unittest.TestCase):
    def setUp(self):
        deps._agent = _make_test_agent()
        self.client = TestClient(app)

    def tearDown(self):
        deps._agent = None
        deps._vocab_db = None

    def test_import_valid_csv(self):
        csv_content = b"word,translation,definition,example\napple,manzana,A fruit,I eat apples.\nrun,correr,To move fast,She runs every day.\n"
        r = self.client.post(
            "/flashcards/import-csv",
            files={"file": ("vocab.csv", io.BytesIO(csv_content), "text/csv")},
        )
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual(2, data["imported"])
        self.assertEqual(0, data["skipped_duplicates"])
        self.assertEqual([], data["errors"])

    def test_import_csv_deduplicates(self):
        # "dog" and "cat" already exist in the agent's core_vocab
        csv_content = b"word,translation\ndog,perro\nnewword,nueva\n"
        r = self.client.post(
            "/flashcards/import-csv",
            files={"file": ("vocab.csv", io.BytesIO(csv_content), "text/csv")},
        )
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual(1, data["imported"])
        self.assertEqual(1, data["skipped_duplicates"])

    def test_import_csv_invalid_format(self):
        csv_content = b"wrong_column\nsome_value\n"
        r = self.client.post(
            "/flashcards/import-csv",
            files={"file": ("vocab.csv", io.BytesIO(csv_content), "text/csv")},
        )
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual(0, data["imported"])
        self.assertGreater(len(data["errors"]), 0)

    def test_import_non_csv_returns_400(self):
        r = self.client.post(
            "/flashcards/import-csv",
            files={"file": ("vocab.txt", io.BytesIO(b"word,translation\n"), "text/plain")},
        )
        self.assertEqual(400, r.status_code)

    def test_import_csv_adds_to_agent_vocab(self):
        initial_count = len(deps._agent.core_vocab)
        csv_content = b"word,translation\nnewword1,nueva1\nnewword2,nueva2\n"
        self.client.post(
            "/flashcards/import-csv",
            files={"file": ("vocab.csv", io.BytesIO(csv_content), "text/csv")},
        )
        self.assertEqual(initial_count + 2, len(deps._agent.core_vocab))

    def test_import_csv_result_has_source(self):
        csv_content = b"word,translation\napple,manzana\n"
        r = self.client.post(
            "/flashcards/import-csv",
            files={"file": ("my_vocab.csv", io.BytesIO(csv_content), "text/csv")},
        )
        data = r.json()
        self.assertEqual("my_vocab.csv", data["source"])

    def test_import_csv_result_has_imported_at(self):
        csv_content = b"word,translation\napple,manzana\n"
        r = self.client.post(
            "/flashcards/import-csv",
            files={"file": ("vocab.csv", io.BytesIO(csv_content), "text/csv")},
        )
        data = r.json()
        self.assertIn("imported_at", data)
        self.assertIsInstance(data["imported_at"], str)


class APIMissionsWithDifficultyTests(unittest.TestCase):
    def setUp(self):
        deps._agent = _make_test_agent()
        self.client = TestClient(app)

    def tearDown(self):
        deps._agent = None
        deps._vocab_db = None

    def test_create_mission_with_difficulty(self):
        r = self.client.post("/missions", json={
            "description": "I want to talk about food",
            "mission_id": "food_mission",
            "difficulty": "intermediate",
        })
        self.assertEqual(201, r.status_code)
        data = r.json()
        self.assertEqual("food_mission", data["id"])

    def test_mission_exercises_include_feedback(self):
        r = self.client.post("/missions", json={
            "description": "Let's discuss animals",
            "mission_id": "animals_test",
        })
        self.assertEqual(201, r.status_code)
        exercises = r.json()["exercises"]
        for ex in exercises:
            self.assertIn("feedback", ex)

    def test_correct_endpoint_includes_why(self):
        r = self.client.post("/correct", json={"text": "I would of done that"})
        self.assertEqual(200, r.status_code)
        data = r.json()
        corrections = data["corrections"]
        self.assertGreater(len(corrections), 0)
        c = corrections[0]
        self.assertIn("why", c)
        self.assertIn("better_example", c)


if __name__ == "__main__":
    unittest.main()
