import unittest

from agent.language_tutor import LanguageTutorAgent


class LanguageTutorAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = LanguageTutorAgent(language="English")
        self.agent.core_vocab = [
            {"word": "dog",     "tags": ["animals"],  "definition": "A pet", "example": "I have a dog.", "translation": "perro"},
            {"word": "cat",     "tags": ["animals"],  "definition": "A pet", "example": "I have a cat.", "translation": "gato"},
            {"word": "run",     "tags": ["actions"],  "definition": "To move fast", "example": "I run daily.", "translation": "correr"},
            {"word": "eat",     "tags": ["actions"],  "definition": "To consume food", "example": "I eat breakfast.", "translation": "comer"},
            {"word": "airport", "tags": ["travel"],   "definition": "Where planes land", "example": "I am at the airport.", "translation": "aeropuerto"},
        ]
        self.agent.missions = [
            {
                "id": "mission_001",
                "name": "At the park",
                "goal": "Learn vocabulary related to animals and actions",
                "vocabulary_tags": ["animals", "actions"],
                "dialogues": [
                    {"speaker": "Tutor",   "text": "Do you have any pets?"},
                    {"speaker": "Student", "text": "Yes, I have a dog."},
                ],
                "exercises": [
                    {"type": "fill_blank", "text": "I usually ___ my dog in the park.", "blanks": ["walk"]},
                ],
            }
        ]

    # ------------------------------------------------------------------
    # Misiones
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Corrección de texto
    # ------------------------------------------------------------------
    def test_correct_text_detects_missing_apostrophe(self):
        corrections = self.agent.correct_text("I dont have a dog")
        originals = [c["original"] for c in corrections]
        self.assertIn("dont", originals)

    def test_correct_text_detects_third_person_verb(self):
        corrections = self.agent.correct_text("He go to school every day")
        rules = [c["rule"] for c in corrections]
        self.assertIn("third_person_singular", rules)

    def test_correct_text_detects_be_agreement(self):
        corrections = self.agent.correct_text("I are happy today")
        rules = [c["rule"] for c in corrections]
        self.assertIn("subject_verb_be", rules)

    def test_correct_text_clean_sentence_returns_empty(self):
        corrections = self.agent.correct_text("She runs every morning.")
        self.assertEqual([], corrections)

    def test_apply_corrections_fixes_contraction(self):
        result = self.agent.apply_corrections("I dont know")
        self.assertIn("don't", result)

    # ------------------------------------------------------------------
    # Fill-in-the-blank
    # ------------------------------------------------------------------
    def test_generate_fill_blank_replaces_vocab_word(self):
        self.agent.select_mission("mission_001")
        result = self.agent.generate_fill_blank("I walk my dog every morning")
        self.assertIn("___", result["exercise"])
        self.assertGreater(len(result["blanks"]), 0)

    def test_generate_fill_blank_original_preserved(self):
        self.agent.select_mission("mission_001")
        sentence = "She runs with her cat in the park"
        result = self.agent.generate_fill_blank(sentence)
        self.assertEqual(sentence, result["original"])

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    def test_chat_first_turn_returns_greeting(self):
        result = self.agent.chat("Hello")
        self.assertIn("response", result)
        self.assertIsInstance(result["response"], str)
        self.assertGreater(len(result["response"]), 0)
        self.assertEqual(1, result["turn"])

    def test_chat_detects_correction_in_response(self):
        self.agent.select_mission("mission_001")
        # Simular segundo turno con un error gramatical
        history = [{"role": "tutor", "text": "Hello!"}]
        result = self.agent.chat("He go to school", history=history)
        self.assertIsNotNone(result["corrections"])
        rules = [c["rule"] for c in result["corrections"]]
        self.assertIn("third_person_singular", rules)

    def test_chat_turn_counter_increments(self):
        history = [{"role": "tutor", "text": "Hi"}, {"role": "student", "text": "Hello"}]
        result = self.agent.chat("I am learning English", history=history)
        self.assertEqual(3, result["turn"])


if __name__ == "__main__":
    unittest.main()
