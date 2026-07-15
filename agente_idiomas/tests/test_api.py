"""Tests de los endpoints de la API FastAPI."""

import json
import sys
import unittest
from pathlib import Path

# Asegurar que el directorio agente_idiomas esté en el path
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi.testclient import TestClient

from api.app import app
import api.deps as deps


def _make_test_agent():
    """Crea un agente con datos mínimos para los tests de la API."""
    from agent.language_tutor import LanguageTutorAgent

    agent = LanguageTutorAgent(language="English")
    agent.core_vocab = [
        {"word": "dog",  "tags": ["animals"], "definition": "A pet", "example": "I have a dog.", "translation": "perro"},
        {"word": "cat",  "tags": ["animals"], "definition": "A pet", "example": "I have a cat.", "translation": "gato"},
        {"word": "eat",  "tags": ["food", "actions"], "definition": "To consume food", "example": "We eat.", "translation": "comer"},
        {"word": "walk", "tags": ["actions"], "definition": "To move on foot", "example": "I walk.", "translation": "caminar"},
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
                {"type": "fill_blank", "text": "I walk my dog in the park.", "blanks": ["walk"]},
            ],
        }
    ]
    return agent


class APIHealthTests(unittest.TestCase):
    def setUp(self):
        deps._agent = _make_test_agent()
        self.client = TestClient(app)

    def tearDown(self):
        deps._agent = None
        deps._vocab_db = None

    def test_health_returns_ok(self):
        r = self.client.get("/health")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual("ok", data["status"])
        self.assertEqual("English", data["language"])


class APIMissionsTests(unittest.TestCase):
    def setUp(self):
        deps._agent = _make_test_agent()
        self.client = TestClient(app)

    def tearDown(self):
        deps._agent = None
        deps._vocab_db = None

    def test_list_missions_returns_list(self):
        r = self.client.get("/missions")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIsInstance(data, list)
        self.assertEqual(1, len(data))

    def test_get_mission_by_id(self):
        r = self.client.get("/missions/mission_001")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual("mission_001", data["id"])

    def test_get_mission_not_found(self):
        r = self.client.get("/missions/does_not_exist")
        self.assertEqual(404, r.status_code)

    def test_create_open_mission(self):
        payload = {"description": "I want to talk about food", "mission_id": "open_test_1"}
        r = self.client.post("/missions", json=payload)
        self.assertEqual(201, r.status_code)
        data = r.json()
        self.assertEqual("open_test_1", data["id"])

    def test_create_open_mission_duplicate_id_returns_409(self):
        payload = {"description": "At the park again", "mission_id": "mission_001"}
        r = self.client.post("/missions", json=payload)
        self.assertEqual(409, r.status_code)

    def test_get_mission_vocabulary(self):
        r = self.client.get("/missions/mission_001/vocabulary")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIn("vocabulary", data)

    def test_get_mission_exercises(self):
        r = self.client.get("/missions/mission_001/exercises")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_get_mission_flashcards(self):
        r = self.client.get("/missions/mission_001/flashcards")
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn("front", data[0])
        self.assertIn("back", data[0])


class APIChatTests(unittest.TestCase):
    def setUp(self):
        deps._agent = _make_test_agent()
        self.client = TestClient(app)

    def tearDown(self):
        deps._agent = None
        deps._vocab_db = None

    def test_chat_returns_response(self):
        r = self.client.post("/chat", json={"message": "Hello!"})
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIn("response", data)
        self.assertIn("corrections", data)
        self.assertIn("turn", data)

    def test_chat_with_grammar_error_returns_corrections(self):
        history = [{"role": "tutor", "text": "Hello!"}]
        r = self.client.post("/chat", json={
            "message": "He go to school every day",
            "history": history,
        })
        self.assertEqual(200, r.status_code)
        data = r.json()
        rules = [c["rule"] for c in data["corrections"]]
        self.assertIn("third_person_singular", rules)

    def test_chat_with_mission_id(self):
        r = self.client.post("/chat", json={
            "message": "I love dogs",
            "mission_id": "mission_001",
        })
        self.assertEqual(200, r.status_code)

    def test_correct_endpoint(self):
        r = self.client.post("/correct", json={"text": "She dont know the answer"})
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIn("original", data)
        self.assertIn("corrected", data)
        self.assertIn("corrections", data)
        self.assertGreater(len(data["corrections"]), 0)


class APIFlashcardsTests(unittest.TestCase):
    def setUp(self):
        deps._agent = _make_test_agent()
        self.client = TestClient(app)

    def tearDown(self):
        deps._agent = None
        deps._vocab_db = None

    def test_export_flashcards(self):
        payload = {
            "flashcards": [
                {
                    "front": "dog",
                    "back": {
                        "definition":  "A common pet",
                        "example":     "I have a dog.",
                        "translation": "perro",
                    },
                }
            ],
            "output_path": "/tmp/test_deck.tsv",
        }
        r = self.client.post("/flashcards/export", json=payload)
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual(1, data["count"])
        self.assertIn("exported_to", data)


if __name__ == "__main__":
    unittest.main()
