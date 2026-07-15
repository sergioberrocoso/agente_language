"""Parser y validador de CSV de vocabulario para importar a flashcards.

Formato esperado del CSV (columnas mínimas obligatorias):
    word, translation

Columnas opcionales:
    definition, example, tags, difficulty

Ejemplo de archivo CSV::

    word,translation,definition,example,tags
    apple,manzana,A round fruit,I eat an apple every day,food
    run,correr,To move fast,I run every morning,actions

Uso::

    from flashcards.csv_import import VocabularyCSVImporter

    importer = VocabularyCSVImporter()
    result = importer.import_from_file("vocabulary.csv", existing_words={"apple"})
    print(f"Imported: {result['imported']}, Skipped: {result['skipped_duplicates']}")
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Columnas obligatorias en el CSV
_REQUIRED_COLUMNS = {"word", "translation"}

# Columnas reconocidas (en cualquier orden, case-insensitive)
_KNOWN_COLUMNS = {"word", "translation", "definition", "example", "tags", "difficulty"}


class VocabularyCSVImporter:
    """Importa vocabulario desde un CSV y lo integra con las flashcards existentes.

    La lógica de deduplicación es simple: si la palabra (normalizada a
    minúsculas) ya existe en ``existing_words``, la entrada se omite.
    """

    def import_from_file(
        self,
        file_path: str,
        existing_words: Optional[set] = None,
        source_label: Optional[str] = None,
    ) -> dict:
        """Importa un CSV desde disco.

        Args:
            file_path:      Ruta al archivo CSV.
            existing_words: Conjunto de palabras (lowercase) ya existentes
                            para deduplicación.
            source_label:   Etiqueta para trazabilidad (p.ej. nombre del archivo).

        Devuelve::

            {
                "imported": int,
                "skipped_duplicates": int,
                "errors": list[str],
                "entries": list[dict],
                "source": str,
                "imported_at": str (ISO 8601),
            }
        """
        path = Path(file_path)
        if not path.exists():
            return self._error_result(f"File not found: {file_path}", source_label or file_path)

        try:
            content = path.read_text(encoding="utf-8-sig")  # handle BOM
        except OSError as exc:
            return self._error_result(str(exc), source_label or file_path)

        return self.import_from_string(
            content,
            existing_words=existing_words,
            source_label=source_label or path.name,
        )

    def import_from_string(
        self,
        csv_content: str,
        existing_words: Optional[set] = None,
        source_label: str = "inline",
    ) -> dict:
        """Importa un CSV desde una cadena de texto.

        Args:
            csv_content:    Contenido del CSV como string.
            existing_words: Conjunto de palabras ya existentes.
            source_label:   Etiqueta de trazabilidad.
        """
        # Strip BOM if present
        csv_content = csv_content.lstrip("\ufeff")

        existing = {w.lower() for w in (existing_words or set())}
        entries: list[dict] = []
        errors: list[str] = []
        skipped = 0

        reader_result = self._parse_csv(csv_content, errors)
        if reader_result is None:
            # errors list was populated by _parse_csv with details
            return {
                "imported": 0,
                "skipped_duplicates": 0,
                "errors": errors,
                "entries": [],
                "source": source_label,
                "imported_at": datetime.now(timezone.utc).isoformat(),
            }

        rows, column_map = reader_result

        for line_num, row in enumerate(rows, start=2):  # start=2 (row 1 = header)
            try:
                entry, err = self._parse_row(row, column_map, line_num)
                if err:
                    errors.append(err)
                    continue
                if entry["word"].lower() in existing:
                    skipped += 1
                    continue
                existing.add(entry["word"].lower())
                entries.append(entry)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Line {line_num}: unexpected error — {exc}")

        return {
            "imported": len(entries),
            "skipped_duplicates": skipped,
            "errors": errors,
            "entries": entries,
            "source": source_label,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Privados
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_csv(
        content: str,
        errors: list,
    ) -> Optional[tuple[list, dict]]:
        """Parsea el CSV y devuelve (rows, column_map) o None si hay error."""
        reader = csv.DictReader(io.StringIO(content))

        if reader.fieldnames is None:
            errors.append("CSV has no header row.")
            return None

        # Normalizar nombres de columnas a lowercase
        column_map: dict[str, str] = {}
        for col in reader.fieldnames:
            normalized = col.strip().lower()
            column_map[normalized] = col  # normalized → original name in CSV

        # Validar columnas obligatorias
        missing = _REQUIRED_COLUMNS - set(column_map.keys())
        if missing:
            errors.append(
                f"CSV is missing required columns: {', '.join(sorted(missing))}. "
                f"Found columns: {', '.join(sorted(column_map.keys()))}."
            )
            return None

        rows = list(reader)
        return rows, column_map

    @staticmethod
    def _parse_row(row: dict, column_map: dict, line_num: int) -> tuple[Optional[dict], Optional[str]]:
        """Parsea una fila del CSV y devuelve (entry, error_message)."""
        def get(normalized_key: str) -> str:
            original = column_map.get(normalized_key)
            if original is None:
                return ""
            return (row.get(original) or "").strip()

        word = get("word")
        if not word:
            return None, f"Line {line_num}: empty 'word' — row skipped."

        translation = get("translation")
        if not translation:
            return None, f"Line {line_num}: empty 'translation' for word '{word}' — row skipped."

        # Parse tags: comma-separated string → list
        raw_tags = get("tags")
        tags: list[str] = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else []

        entry = {
            "word": word,
            "translation": translation,
            "definition": get("definition") or f"Definition of '{word}'",
            "example": get("example") or f"I use the word '{word}' in a sentence.",
            "tags": tags,
            "difficulty": get("difficulty") or "beginner",
        }
        return entry, None

    @staticmethod
    def _error_result(message: str, source: str) -> dict:
        return {
            "imported": 0,
            "skipped_duplicates": 0,
            "errors": [message],
            "entries": [],
            "source": source,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }
