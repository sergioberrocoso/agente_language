import unittest

from agent.language_tutor import LanguageTutorAgent


class LanguageTutorAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = LanguageTutorAgent(language="English")
        self.agent.core_vocab = [
            {"word": "dog", "tags": ["animals"]},
            {"word": "cat", "tags": ["animals"]},
            {"word": "run", "tags": ["actions"]},
            {"word": "eat", "tags": ["actions"]},
            {"word": "airport", "tags": ["travel"]},
        ]
        self.agent.missions = [
            {
                "id": "mission_001",
                "name": "At the park",
                "goal": "Learn vocabulary related to animals and actions",
                "vocabulary_tags": ["animals", "actions"],
                "dialogues": [],
                "exercises": [],
            }
        ]

    def test_select_mission_sets_current_mission(self):
        mission = self.agent.select_mission("mission_001")
        self.assertEqual("mission_001", mission["id"])
        self.assertEqual("mission_001", self.agent.current_mission["id"])

    def test_select_mission_raises_when_not_found(self):
        with self.assertRaises(ValueError):
            self.agent.select_mission("missing")

    def test_analyze_description_detects_expected_tags(self):
        tags = self.agent.analyze_description("I want to run with my dog in the park")
        self.assertIn("animals", tags)
        self.assertIn("actions", tags)

    def test_create_open_mission_builds_dialogues_and_exercises(self):
        mission = self.agent.create_open_mission(
            description="Let's talk about my dog in the park",
            mission_id="open_001",
        )
        self.assertEqual("open_001", mission["id"])
        self.assertIn("animals", mission["vocabulary_tags"])
        self.assertGreater(len(mission["dialogues"]), 0)
        self.assertGreater(len(mission["exercises"]), 0)

    def test_generate_flashcards_uses_current_mission_vocab(self):
        self.agent.select_mission("mission_001")
        cards = self.agent.generate_flashcards()

        fronts = [card["front"] for card in cards]
        self.assertIn("dog", fronts)
        self.assertIn("cat", fronts)
        self.assertIn("run", fronts)
        self.assertIn("eat", fronts)

    def test_generate_flashcards_raises_without_mission(self):
        with self.assertRaises(ValueError):
            self.agent.generate_flashcards()


if __name__ == "__main__":
    unittest.main()
