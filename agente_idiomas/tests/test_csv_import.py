"""Tests para el parser de CSV de vocabulario."""

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flashcards.csv_import import VocabularyCSVImporter


class VocabularyCSVImporterTests(unittest.TestCase):
    def setUp(self):
        self.importer = VocabularyCSVImporter()

    # ------------------------------------------------------------------
    # Importación básica
    # ------------------------------------------------------------------
    def test_import_valid_csv(self):
        csv = "word,translation\napple,manzana\nrun,correr\n"
        result = self.importer.import_from_string(csv)
        self.assertEqual(2, result["imported"])
        self.assertEqual(0, result["skipped_duplicates"])
        self.assertEqual([], result["errors"])

    def test_imported_entries_have_expected_fields(self):
        csv = "word,translation,definition,example,tags\napple,manzana,A fruit,I eat apples,food\n"
        result = self.importer.import_from_string(csv)
        entry = result["entries"][0]
        self.assertEqual("apple", entry["word"])
        self.assertEqual("manzana", entry["translation"])
        self.assertEqual("A fruit", entry["definition"])
        self.assertEqual("I eat apples", entry["example"])
        self.assertEqual(["food"], entry["tags"])

    def test_tags_parsed_as_list(self):
        csv = "word,translation,tags\ndog,perro,animals,actions\n"
        result = self.importer.import_from_string(csv)
        # Note: CSV DictReader handles this — extra columns become separate fields
        # The tag field should still be a list
        self.assertEqual(1, result["imported"])

    def test_optional_columns_use_defaults(self):
        csv = "word,translation\ncat,gato\n"
        result = self.importer.import_from_string(csv)
        entry = result["entries"][0]
        self.assertIn("cat", entry["definition"])
        self.assertIn("cat", entry["example"])
        self.assertEqual([], entry["tags"])
        self.assertEqual("beginner", entry["difficulty"])

    # ------------------------------------------------------------------
    # Deduplicación
    # ------------------------------------------------------------------
    def test_skips_existing_words(self):
        csv = "word,translation\napple,manzana\nrun,correr\n"
        result = self.importer.import_from_string(csv, existing_words={"apple"})
        self.assertEqual(1, result["imported"])
        self.assertEqual(1, result["skipped_duplicates"])
        self.assertEqual("run", result["entries"][0]["word"])

    def test_deduplication_is_case_insensitive(self):
        csv = "word,translation\nApple,manzana\n"
        result = self.importer.import_from_string(csv, existing_words={"apple"})
        self.assertEqual(0, result["imported"])
        self.assertEqual(1, result["skipped_duplicates"])

    def test_no_duplicates_within_same_csv(self):
        csv = "word,translation\napple,manzana\napple,manzana\n"
        result = self.importer.import_from_string(csv)
        self.assertEqual(1, result["imported"])
        self.assertEqual(1, result["skipped_duplicates"])

    # ------------------------------------------------------------------
    # Validación de columnas
    # ------------------------------------------------------------------
    def test_missing_required_column_word_returns_error(self):
        csv = "translation\nmanzana\n"
        result = self.importer.import_from_string(csv)
        self.assertEqual(0, result["imported"])
        self.assertGreater(len(result["errors"]), 0)
        # Error should mention the missing column
        self.assertTrue(any("word" in e or "required" in e for e in result["errors"]))

    def test_missing_required_column_translation_returns_error(self):
        csv = "word\napple\n"
        result = self.importer.import_from_string(csv)
        self.assertEqual(0, result["imported"])
        self.assertGreater(len(result["errors"]), 0)
        # Error should mention the missing column
        self.assertTrue(any("translation" in e or "required" in e for e in result["errors"]))

    def test_empty_word_row_skipped_with_error(self):
        csv = "word,translation\n,manzana\napple,apple\n"
        result = self.importer.import_from_string(csv)
        self.assertEqual(1, result["imported"])
        self.assertEqual(1, len(result["errors"]))

    def test_empty_translation_row_skipped_with_error(self):
        csv = "word,translation\napple,\n"
        result = self.importer.import_from_string(csv)
        self.assertEqual(0, result["imported"])
        self.assertEqual(1, len(result["errors"]))

    def test_empty_csv_returns_zero_imported(self):
        csv = "word,translation\n"
        result = self.importer.import_from_string(csv)
        self.assertEqual(0, result["imported"])
        self.assertEqual(0, result["skipped_duplicates"])

    # ------------------------------------------------------------------
    # Manejo de errores de archivo
    # ------------------------------------------------------------------
    def test_file_not_found_returns_error(self):
        result = self.importer.import_from_file("/nonexistent/path/file.csv")
        self.assertEqual(0, result["imported"])
        self.assertGreater(len(result["errors"]), 0)

    # ------------------------------------------------------------------
    # Trazabilidad
    # ------------------------------------------------------------------
    def test_result_has_source_label(self):
        csv = "word,translation\napple,manzana\n"
        result = self.importer.import_from_string(csv, source_label="my_vocab.csv")
        self.assertEqual("my_vocab.csv", result["source"])

    def test_result_has_imported_at_timestamp(self):
        csv = "word,translation\napple,manzana\n"
        result = self.importer.import_from_string(csv)
        self.assertIn("imported_at", result)
        self.assertIsInstance(result["imported_at"], str)
        self.assertGreater(len(result["imported_at"]), 0)

    # ------------------------------------------------------------------
    # CSV con BOM
    # ------------------------------------------------------------------
    def test_handles_utf8_bom(self):
        # BOM at start of file
        csv = "\ufeffword,translation\napple,manzana\n"
        result = self.importer.import_from_string(csv)
        self.assertEqual(1, result["imported"])
        self.assertEqual("apple", result["entries"][0]["word"])

    # ------------------------------------------------------------------
    # Tags múltiples
    # ------------------------------------------------------------------
    def test_multiple_tags_in_single_field(self):
        csv = "word,translation,tags\nrun,correr,\"actions,sports\"\n"
        result = self.importer.import_from_string(csv)
        self.assertEqual(1, result["imported"])
        entry = result["entries"][0]
        self.assertIn("actions", entry["tags"])
        self.assertIn("sports", entry["tags"])


if __name__ == "__main__":
    unittest.main()
