"""Tests de los endpoints de la API FastAPI."""

import json
import os
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
from auth.security import create_access_token


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
            # output_path is accepted by the schema but the server ignores it
            # and generates a safe UUID-based filename internally.
            "output_path": "ignored_by_server.tsv",
        }
        r = self.client.post("/flashcards/export", json=payload)
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertEqual(1, data["count"])
        self.assertIn("exported_to", data)
        # Verify the server used its own path (not the client-provided name)
        self.assertNotIn("ignored_by_server", data["exported_to"])


class APIAuthTests(unittest.TestCase):
    def setUp(self):
        deps._agent = _make_test_agent()
        deps._user_db = None
        os.environ["USER_DB_PATH"] = ":memory:"
        os.environ["JWT_SECRET"] = "test-jwt-secret"
        os.environ["JWT_EXPIRE_MINUTES"] = "60"
        self.client = TestClient(app)

    def tearDown(self):
        deps._agent = None
        deps._vocab_db = None
        deps._user_db = None
        os.environ.pop("USER_DB_PATH", None)
        os.environ.pop("JWT_SECRET", None)
        os.environ.pop("JWT_EXPIRE_MINUTES", None)

    def test_register_success(self):
        r = self.client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "super-secret"},
        )
        self.assertEqual(201, r.status_code)
        data = r.json()
        self.assertEqual("alice@example.com", data["email"])
        self.assertIn("id", data)

        user = deps.get_user_db().get_by_email("alice@example.com")
        self.assertIsNotNone(user)
        self.assertNotEqual("super-secret", user["password_hash"])

    def test_register_duplicate_returns_409(self):
        self.client.post(
            "/auth/register",
            json={"email": "Alice@Example.com", "password": "secret-1"},
        )
        r = self.client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "secret-2"},
        )
        self.assertEqual(409, r.status_code)

    def test_login_success(self):
        self.client.post(
            "/auth/register",
            json={"email": "bob@example.com", "password": "correct-password"},
        )
        r = self.client.post(
            "/auth/login",
            json={"email": "bob@example.com", "password": "correct-password"},
        )
        self.assertEqual(200, r.status_code)
        data = r.json()
        self.assertIn("access_token", data)
        self.assertEqual("bearer", data["token_type"])

    def test_login_wrong_password_returns_401(self):
        self.client.post(
            "/auth/register",
            json={"email": "carol@example.com", "password": "correct-password"},
        )
        r = self.client.post(
            "/auth/login",
            json={"email": "carol@example.com", "password": "wrong-password"},
        )
        self.assertEqual(401, r.status_code)

    def test_me_without_token_returns_401(self):
        r = self.client.get("/auth/me")
        self.assertEqual(401, r.status_code)

    def test_me_with_valid_token_returns_user(self):
        self.client.post(
            "/auth/register",
            json={"email": "dave@example.com", "password": "strong-pass"},
        )
        login = self.client.post(
            "/auth/login",
            json={"email": "dave@example.com", "password": "strong-pass"},
        )
        token = login.json()["access_token"]
        r = self.client.get("/auth/me", headers={"Authorization": "Bearer " + token})
        self.assertEqual(200, r.status_code)
        self.assertEqual("dave@example.com", r.json()["email"])

    def test_me_with_invalid_token_returns_401(self):
        invalid_header = {"Authorization": "Bearer " + "not-a-valid-token"}
        r = self.client.get("/auth/me", headers=invalid_header)
        self.assertEqual(401, r.status_code)

    def test_me_with_expired_token_returns_401(self):
        self.client.post(
            "/auth/register",
            json={"email": "eva@example.com", "password": "strong-pass"},
        )
        user = deps.get_user_db().get_by_email("eva@example.com")
        expired_token = create_access_token(str(user["id"]), expires_minutes=-1)
        r = self.client.get(
            "/auth/me",
            headers={"Authorization": "Bearer " + expired_token},
        )
        self.assertEqual(401, r.status_code)


if __name__ == "__main__":
    unittest.main()
