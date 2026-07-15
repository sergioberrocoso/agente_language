"""Rutas de la API para generación, exportación e importación de flashcards."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from api.schemas import (
    CSVImportResult,
    Flashcard,
    FlashcardBack,
    FlashcardExportRequest,
)
from api.deps import get_agent
from flashcards.anki_export import export_flashcards_to_tsv
from flashcards.csv_import import VocabularyCSVImporter

router = APIRouter(prefix="/flashcards", tags=["flashcards"])

# Directorio seguro donde se escriben los exports.
_EXPORT_BASE = Path(tempfile.gettempdir()) / "agente_language_exports"
_EXPORT_BASE.mkdir(parents=True, exist_ok=True)


@router.post("/export")
def export_flashcards(body: FlashcardExportRequest):
    """Exporta una lista de flashcards a formato TSV compatible con Anki."""
    raw_cards = [
        {
            "front": c.front,
            "back": {
                "definition":  c.back.definition,
                "example":     c.back.example,
                "translation": c.back.translation,
            },
        }
        for c in body.flashcards
    ]

    # El nombre de archivo lo genera el servidor (timestamp + UUID) para que ninguna
    # parte de la ruta proceda de input del cliente → sin path injection.
    import time as _time
    prefix = int(_time.time())
    safe_path = _EXPORT_BASE / f"{prefix}_{uuid.uuid4().hex}.tsv"

    try:
        path = export_flashcards_to_tsv(raw_cards, str(safe_path))
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"exported_to": str(path), "count": len(raw_cards)}


@router.post("/import-csv", response_model=CSVImportResult)
async def import_vocabulary_csv(
    file: UploadFile = File(..., description="Archivo CSV con vocabulario"),
    skip_duplicates: bool = Query(
        True,
        description="Si True, omite palabras ya existentes en el agente",
    ),
):
    """Importa vocabulario desde un archivo CSV y lo añade a las flashcards.

    **Formato del CSV** (columnas mínimas obligatorias: ``word``, ``translation``):

    ```csv
    word,translation,definition,example,tags
    apple,manzana,A round fruit,I eat an apple every day,food
    run,correr,To move fast,I run every morning,actions
    ```

    Columnas opcionales: ``definition``, ``example``, ``tags`` (separadas por comas),
    ``difficulty`` (beginner/intermediate/advanced).

    Las palabras ya existentes en el vocabulario del agente se omiten
    automáticamente (deduplicación insensible a mayúsculas).
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only .csv files are accepted.",
        )

    content_bytes = await file.read()
    try:
        csv_content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Could not decode the CSV file. Please use UTF-8 encoding.",
        )

    agent = get_agent()

    # Obtener palabras ya existentes para deduplicación
    existing_words: set[str] = set()
    if skip_duplicates:
        existing_words = {w["word"].lower() for w in agent.core_vocab}

    importer = VocabularyCSVImporter()
    result = importer.import_from_string(
        csv_content,
        existing_words=existing_words,
        source_label=file.filename,
    )

    # Integrar las entradas importadas en el vocabulario del agente
    for entry in result.get("entries", []):
        agent.core_vocab.append({
            "word":        entry["word"],
            "tags":        entry["tags"],
            "definition":  entry["definition"],
            "example":     entry["example"],
            "translation": entry["translation"],
        })

    return CSVImportResult(
        imported=result["imported"],
        skipped_duplicates=result["skipped_duplicates"],
        errors=result["errors"],
        source=result["source"],
        imported_at=result["imported_at"],
    )
