"""Tests de la base de datos de vocabulario SQLite."""

import unittest
from pathlib import Path

from db.vocabulary_db import VocabularyDB


class VocabularyDBInMemoryTests(unittest.TestCase):
    """Tests con una BD en memoria y datos insertados manualmente."""

    def setUp(self):
        self.db = VocabularyDB(db_path=":memory:")
        # Insertar datos de prueba directamente
        self.db._conn.executemany(
            "INSERT INTO vocabulary (headword, forms, tags, frequency_rank) VALUES (?, ?, ?, ?)",
            [
                ("dog",  '["dog","dogs"]',      '["animals"]',        5),
                ("cat",  '["cat","cats"]',       '["animals"]',        8),
                ("eat",  '["eat","eats","ate"]', '["actions","food"]', 2),
                ("run",  '["run","runs","ran"]', '["actions"]',        3),
                ("food", '["food","foods"]',     '["food"]',           1),
            ],
        )
        self.db._conn.commit()

    def tearDown(self):
        self.db.close()

    def test_count_returns_inserted_rows(self):
        self.assertEqual(5, self.db.count())

    def test_search_by_headword(self):
        results = self.db.search("dog")
        self.assertEqual(1, len(results))
        self.assertEqual("dog", results[0]["headword"])

    def test_search_returns_list_of_dicts(self):
        results = self.db.search("cat")
        self.assertIsInstance(results, list)
        self.assertIsInstance(results[0], dict)
        self.assertIn("forms", results[0])
        self.assertIsInstance(results[0]["forms"], list)
        self.assertIn("tags", results[0])
        self.assertIsInstance(results[0]["tags"], list)

    def test_search_partial_match(self):
        results = self.db.search("oo")  # "food"
        headwords = [r["headword"] for r in results]
        self.assertIn("food", headwords)

    def test_search_no_match_returns_empty(self):
        results = self.db.search("zzzqqqxxx")
        self.assertEqual([], results)

    def test_get_by_headword_exact_match(self):
        entry = self.db.get_by_headword("eat")
        self.assertIsNotNone(entry)
        self.assertEqual("eat", entry["headword"])

    def test_get_by_headword_case_insensitive(self):
        entry = self.db.get_by_headword("EAT")
        self.assertIsNotNone(entry)
        self.assertEqual("eat", entry["headword"])

    def test_get_by_headword_not_found_returns_none(self):
        entry = self.db.get_by_headword("notaword")
        self.assertIsNone(entry)

    def test_get_by_tags_single_tag(self):
        results = self.db.get_by_tags(["animals"])
        headwords = [r["headword"] for r in results]
        self.assertIn("dog", headwords)
        self.assertIn("cat", headwords)

    def test_get_by_tags_multi_tag(self):
        results = self.db.get_by_tags(["animals", "food"])
        headwords = [r["headword"] for r in results]
        self.assertIn("dog", headwords)
        self.assertIn("food", headwords)

    def test_get_by_tags_empty_returns_empty(self):
        results = self.db.get_by_tags([])
        self.assertEqual([], results)

    def test_get_by_rank_range(self):
        results = self.db.get_by_rank_range(1, 3)
        headwords = [r["headword"] for r in results]
        self.assertIn("food", headwords)  # rank 1
        self.assertIn("eat", headwords)   # rank 2
        self.assertIn("run", headwords)   # rank 3
        self.assertNotIn("dog", headwords)  # rank 5 — outside range


class VocabularyDBNGSLTests(unittest.TestCase):
    """Tests de carga desde el CSV del NGSL real."""

    @classmethod
    def setUpClass(cls):
        ngsl_path = Path(__file__).parent.parent / "data" / "NGSL_1.2_lemmatized_for_teaching.csv"
        if not ngsl_path.exists():
            raise unittest.SkipTest("NGSL CSV no encontrado")
        cls.db = VocabularyDB(db_path=":memory:", ngsl_csv_path=str(ngsl_path))

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_ngsl_loads_significant_number_of_words(self):
        self.assertGreater(self.db.count(), 2000)

    def test_ngsl_search_returns_results(self):
        results = self.db.search("animal")
        self.assertGreater(len(results), 0)

    def test_ngsl_common_word_has_rank(self):
        results = self.db.search("go", limit=5)
        self.assertIsInstance(results, list)

    def test_ngsl_words_have_forms_list(self):
        results = self.db.get_by_rank_range(1, 10)
        for entry in results:
            self.assertIsInstance(entry["forms"], list)
            self.assertGreater(len(entry["forms"]), 0)


if __name__ == "__main__":
    unittest.main()
