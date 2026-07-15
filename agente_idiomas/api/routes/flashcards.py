"""Rutas de la API para generación y exportación de flashcards."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import Flashcard, FlashcardBack, FlashcardExportRequest
from api.deps import get_agent
from flashcards.anki_export import export_flashcards_to_tsv

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
