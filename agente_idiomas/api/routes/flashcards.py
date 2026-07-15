"""Rutas de la API para generación y exportación de flashcards."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import Flashcard, FlashcardBack, FlashcardExportRequest
from api.deps import get_agent
from flashcards.anki_export import export_flashcards_to_tsv

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


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

    try:
        path = export_flashcards_to_tsv(raw_cards, body.output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"exported_to": str(path), "count": len(raw_cards)}
