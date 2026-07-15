"""Rutas de la API para generación y exportación de flashcards."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import Flashcard, FlashcardBack, FlashcardExportRequest
from api.deps import get_agent
from flashcards.anki_export import export_flashcards_to_tsv

router = APIRouter(prefix="/flashcards", tags=["flashcards"])

# Directorio seguro donde se escriben los exports.
# Siempre se usa como base_dir para evitar path-traversal con la ruta
# proporcionada por el cliente.
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

    # Pasar base_dir para que la función restrinja la escritura al directorio
    # seguro y descarte cualquier componente de directorio del nombre de archivo.
    try:
        path = export_flashcards_to_tsv(raw_cards, body.output_path, base_dir=_EXPORT_BASE)
    except (ValueError, OSError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"exported_to": str(path), "count": len(raw_cards)}
