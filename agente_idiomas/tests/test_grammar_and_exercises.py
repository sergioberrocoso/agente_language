"""Tests para las mejoras de corrección gramatical."""

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent.language_tutor import LanguageTutorAgent


class EnhancedGrammarCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.agent = LanguageTutorAgent(language="English")

    # ------------------------------------------------------------------
    # Contracciones
    # ------------------------------------------------------------------
    def test_contraction_correction_includes_why(self):
        corrections = self.agent.correct_text("I dont know")
        c = next((c for c in corrections if c["rule"] == "contraction"), None)
        self.assertIsNotNone(c)
        self.assertIn("why", c)
        self.assertIsInstance(c["why"], str)
        self.assertGreater(len(c["why"]), 0)

    def test_contraction_correction_includes_better_example(self):
        corrections = self.agent.correct_text("She cant come")
        c = next((c for c in corrections if c["rule"] == "contraction"), None)
        self.assertIsNotNone(c)
        self.assertIn("better_example", c)
        self.assertIsInstance(c["better_example"], str)

    # ------------------------------------------------------------------
    # Concordancia be
    # ------------------------------------------------------------------
    def test_be_rule_includes_why(self):
        corrections = self.agent.correct_text("I are happy")
        c = next((c for c in corrections if c["rule"] == "subject_verb_be"), None)
        self.assertIsNotNone(c)
        self.assertIn("why", c)
        self.assertGreater(len(c["why"]), 0)

    # ------------------------------------------------------------------
    # Tercera persona singular
    # ------------------------------------------------------------------
    def test_third_person_includes_why_and_example(self):
        corrections = self.agent.correct_text("She go to school")
        c = next((c for c in corrections if c["rule"] == "third_person_singular"), None)
        self.assertIsNotNone(c)
        self.assertIn("why", c)
        self.assertIn("better_example", c)
        self.assertIn("goes", c["better_example"])

    # ------------------------------------------------------------------
    # Doble negación (reglas nuevas)
    # ------------------------------------------------------------------
    def test_double_negative_detected(self):
        corrections = self.agent.correct_text("I don't know nothing")
        rules = [c["rule"] for c in corrections]
        self.assertIn("double_negative", rules)

    def test_double_negative_suggestion(self):
        corrections = self.agent.correct_text("I don't know nothing")
        c = next((c for c in corrections if c["rule"] == "double_negative"), None)
        self.assertIsNotNone(c)
        self.assertEqual("don't know anything", c["suggested"])

    def test_double_negative_includes_why(self):
        corrections = self.agent.correct_text("She didn't do nothing wrong")
        c = next((c for c in corrections if c["rule"] == "double_negative"), None)
        self.assertIsNotNone(c)
        self.assertIn("why", c)

    # ------------------------------------------------------------------
    # Preposiciones incorrectas (reglas nuevas)
    # ------------------------------------------------------------------
    def test_wrong_preposition_interested_on(self):
        corrections = self.agent.correct_text("I am interested on learning English")
        c = next((c for c in corrections if c["rule"] == "wrong_preposition"), None)
        self.assertIsNotNone(c)
        self.assertEqual("interested in", c["suggested"])

    def test_wrong_preposition_good_in(self):
        corrections = self.agent.correct_text("She is very good in mathematics")
        c = next((c for c in corrections if c["rule"] == "wrong_preposition"), None)
        self.assertIsNotNone(c)
        self.assertEqual("good at", c["suggested"])

    def test_wrong_preposition_married_with(self):
        corrections = self.agent.correct_text("He is married with a doctor")
        c = next((c for c in corrections if c["rule"] == "wrong_preposition"), None)
        self.assertIsNotNone(c)
        self.assertEqual("married to", c["suggested"])

    def test_wrong_preposition_includes_why(self):
        corrections = self.agent.correct_text("I am interested on history")
        c = next((c for c in corrections if c["rule"] == "wrong_preposition"), None)
        self.assertIsNotNone(c)
        self.assertIn("why", c)
        self.assertIn("better_example", c)

    # ------------------------------------------------------------------
    # Modal perfective (reglas nuevas)
    # ------------------------------------------------------------------
    def test_modal_would_of_detected(self):
        corrections = self.agent.correct_text("I would of helped you")
        c = next((c for c in corrections if c["rule"] == "modal_perfective"), None)
        self.assertIsNotNone(c)
        self.assertEqual("would have", c["suggested"])

    def test_modal_could_of_detected(self):
        corrections = self.agent.correct_text("She could of passed the exam")
        c = next((c for c in corrections if c["rule"] == "modal_perfective"), None)
        self.assertIsNotNone(c)
        self.assertEqual("could have", c["suggested"])

    def test_modal_should_of_detected(self):
        corrections = self.agent.correct_text("You should of called me")
        c = next((c for c in corrections if c["rule"] == "modal_perfective"), None)
        self.assertIsNotNone(c)
        self.assertEqual("should have", c["suggested"])

    def test_modal_perfective_includes_why(self):
        corrections = self.agent.correct_text("I would of helped you")
        c = next((c for c in corrections if c["rule"] == "modal_perfective"), None)
        self.assertIsNotNone(c)
        self.assertIn("why", c)

    # ------------------------------------------------------------------
    # Artículo a/an
    # ------------------------------------------------------------------
    def test_a_before_vowel(self):
        corrections = self.agent.correct_text("She is a engineer")
        c = next((c for c in corrections if c["rule"] == "article_a_an"), None)
        self.assertIsNotNone(c)
        self.assertIn("an", c["suggested"])

    def test_an_before_consonant(self):
        corrections = self.agent.correct_text("He is an doctor")
        c = next((c for c in corrections if c["rule"] == "article_a_an"), None)
        self.assertIsNotNone(c)
        self.assertIn("a ", c["suggested"])

    def test_an_hour_not_flagged(self):
        """'an hour' is correct (silent h) — should NOT be flagged."""
        corrections = self.agent.correct_text("I waited an hour for you")
        article_corrections = [c for c in corrections if c["rule"] == "article_a_an"]
        # "an hour" should not generate a correction
        self.assertEqual(0, len(article_corrections))

    # ------------------------------------------------------------------
    # Oraciones correctas — sin falsos positivos
    # ------------------------------------------------------------------
    def test_clean_sentence_returns_empty(self):
        corrections = self.agent.correct_text("She runs every morning.")
        self.assertEqual([], corrections)

    def test_correct_sentence_with_contractions(self):
        corrections = self.agent.correct_text("I don't know what to do.")
        self.assertEqual([], corrections)

    def test_correct_third_person(self):
        corrections = self.agent.correct_text("He goes to school every day.")
        self.assertEqual([], corrections)


class EnhancedExercisesTests(unittest.TestCase):
    def setUp(self):
        self.agent = LanguageTutorAgent(language="English")

    def test_exercises_include_difficulty_field(self):
        exercises = self.agent.generate_exercises(["animals"])
        for ex in exercises:
            self.assertIn("difficulty", ex)
            self.assertIn(ex["difficulty"], ("beginner", "intermediate", "advanced"))

    def test_exercises_include_feedback_field(self):
        exercises = self.agent.generate_exercises(["food"])
        for ex in exercises:
            self.assertIn("feedback", ex)
            self.assertIsInstance(ex["feedback"], str)
            self.assertGreater(len(ex["feedback"]), 0)

    def test_advanced_exercises_include_more_types(self):
        exercises = self.agent.generate_exercises(["animals"], difficulty="advanced")
        types = {e["type"] for e in exercises}
        self.assertIn("fill_blank", types)
        self.assertIn("multiple_choice", types)
        # Advanced should include at least one of reorder, error_correct, match
        advanced_types = types & {"reorder", "error_correct", "match"}
        self.assertGreater(len(advanced_types), 0)

    def test_beginner_exercises_do_not_include_advanced_only(self):
        exercises = self.agent.generate_exercises(["animals"], difficulty="beginner")
        for ex in exercises:
            self.assertNotEqual("advanced", ex.get("difficulty"))

    def test_exercises_for_new_topics(self):
        """Ejercicios para temas nuevos (tecnología, emociones, clima)."""
        for tag in ("technology", "emotions", "weather", "school"):
            exercises = self.agent.generate_exercises([tag])
            self.assertGreater(len(exercises), 0, f"No exercises for tag: {tag}")

    def test_error_correct_exercise_has_answer(self):
        exercises = self.agent.generate_exercises(["work"])
        error_exs = [e for e in exercises if e["type"] == "error_correct"]
        for ex in error_exs:
            self.assertIn("answer", ex)
            self.assertIsNotNone(ex["answer"])

    def test_multiple_choice_exercise_has_options_and_answer(self):
        exercises = self.agent.generate_exercises(["food"])
        mc_exs = [e for e in exercises if e["type"] == "multiple_choice"]
        for ex in mc_exs:
            self.assertIn("options", ex)
            self.assertIn("answer", ex)
            self.assertIn(ex["answer"], ex["options"])

    def test_reorder_exercise_has_answer(self):
        exercises = self.agent.generate_exercises(["travel"], difficulty="intermediate")
        reorder_exs = [e for e in exercises if e["type"] == "reorder"]
        for ex in reorder_exs:
            self.assertIn("answer", ex)

    def test_match_exercise_has_pairs(self):
        exercises = self.agent.generate_exercises(["animals"])
        match_exs = [e for e in exercises if e["type"] == "match"]
        for ex in match_exs:
            self.assertIn("pairs", ex)
            self.assertIsInstance(ex["pairs"], list)
            self.assertGreater(len(ex["pairs"]), 0)

    def test_create_open_mission_accepts_difficulty(self):
        self.agent.core_vocab = [
            {"word": "dog", "tags": ["animals"], "definition": "A pet",
             "example": "I have a dog.", "translation": "perro"},
        ]
        mission = self.agent.create_open_mission(
            description="Tell me about your dog",
            mission_id="test_difficulty",
            difficulty="intermediate",
        )
        self.assertEqual("test_difficulty", mission["id"])
        self.assertGreater(len(mission["exercises"]), 0)


if __name__ == "__main__":
    unittest.main()
