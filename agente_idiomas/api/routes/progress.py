"""Rutas de la API para persistencia de progreso de usuario."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.schemas import (
    FlashcardStateRequest,
    RecordExerciseRequest,
    RecordTurnRequest,
    SetPreferenceRequest,
)
from api.deps import get_user_progress_db

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/{user_id}")
def get_progress(user_id: int):
    """Devuelve el resumen de progreso de un usuario."""
    db = get_user_progress_db()
    return db.get_progress_summary(user_id)


@router.get("/{user_id}/exercises")
def get_exercise_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=500),
    mission_id: str = Query(None),
):
    """Devuelve el historial de ejercicios del usuario."""
    db = get_user_progress_db()
    return db.get_exercise_history(user_id, limit=limit, mission_id=mission_id)


@router.post("/{user_id}/exercises")
def record_exercise(user_id: int, body: RecordExerciseRequest):
    """Registra un ejercicio realizado."""
    db = get_user_progress_db()
    exercise_id = db.record_exercise(
        user_id=user_id,
        exercise_type=body.exercise_type,
        prompt=body.prompt,
        user_answer=body.user_answer,
        correct=body.correct,
        mission_id=body.mission_id,
        difficulty=body.difficulty,
        feedback=body.feedback,
    )
    return {"id": exercise_id, "recorded": True}


@router.get("/{user_id}/conversation")
def get_conversation_history(
    user_id: int,
    limit: int = Query(100, ge=1, le=1000),
    mission_id: str = Query(None),
):
    """Devuelve el historial de conversación del usuario."""
    db = get_user_progress_db()
    return db.get_conversation_history(user_id, limit=limit, mission_id=mission_id)


@router.post("/{user_id}/conversation")
def record_conversation_turn(user_id: int, body: RecordTurnRequest):
    """Registra un turno de conversación."""
    db = get_user_progress_db()
    turn_id = db.record_turn(
        user_id=user_id,
        role=body.role,
        text=body.text,
        corrections=body.corrections,
        mission_id=body.mission_id,
    )
    return {"id": turn_id, "recorded": True}


@router.get("/{user_id}/preferences")
def get_preferences(user_id: int):
    """Devuelve todas las preferencias del usuario."""
    db = get_user_progress_db()
    return db.get_all_preferences(user_id)


@router.post("/{user_id}/preferences")
def set_preference(user_id: int, body: SetPreferenceRequest):
    """Guarda o actualiza una preferencia de usuario."""
    db = get_user_progress_db()
    db.set_preference(user_id, body.key, body.value)
    return {"key": body.key, "saved": True}


@router.get("/{user_id}/flashcards")
def get_flashcard_states(user_id: int):
    """Devuelve los estados de revisión de flashcards del usuario."""
    db = get_user_progress_db()
    return db.get_flashcard_states(user_id)


@router.get("/{user_id}/flashcards/unknown")
def get_unknown_flashcards(user_id: int):
    """Devuelve las flashcards que el usuario no domina todavía."""
    db = get_user_progress_db()
    return db.get_unknown_flashcards(user_id)


@router.post("/{user_id}/flashcards")
def update_flashcard_state(user_id: int, body: FlashcardStateRequest):
    """Actualiza el estado de una flashcard (conocida/desconocida)."""
    db = get_user_progress_db()
    db.upsert_flashcard_state(
        user_id=user_id,
        word=body.word,
        known=body.known,
        source=body.source,
    )
    return {"word": body.word, "known": body.known, "updated": True}
