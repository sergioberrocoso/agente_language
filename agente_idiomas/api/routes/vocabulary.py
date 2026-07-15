"""Rutas de la API para vocabulario (base de datos NGSL)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.schemas import VocabularyEntry
from api.deps import get_vocab_db

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


@router.get("/search", response_model=list[VocabularyEntry])
def search_vocabulary(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(20, ge=1, le=100),
):
    """Busca palabras en la base de datos NGSL."""
    db = get_vocab_db()
    return db.search(q, limit=limit)


@router.get("/by-tag", response_model=list[VocabularyEntry])
def get_vocabulary_by_tag(
    tags: list[str] = Query(..., description="Lista de tags (p.ej. animals, food)"),
    limit: int = Query(50, ge=1, le=200),
):
    """Devuelve vocabulario filtrado por categorías/tags."""
    db = get_vocab_db()
    return db.get_by_tags(tags, limit=limit)


@router.get("/top", response_model=list[VocabularyEntry])
def get_top_vocabulary(
    min_rank: int = Query(1, ge=1),
    max_rank: int = Query(500, ge=1),
):
    """Devuelve palabras en un rango de frecuencia del NGSL."""
    db = get_vocab_db()
    return db.get_by_rank_range(min_rank, max_rank)


@router.get("/{headword}", response_model=VocabularyEntry)
def get_word(headword: str):
    """Devuelve los datos de una palabra concreta."""
    db = get_vocab_db()
    entry = db.get_by_headword(headword)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Palabra no encontrada: {headword}")
    return entry
