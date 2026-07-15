"""Rutas de la API para la conversación con el tutor."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import (
    ChatRequest,
    ChatResponse,
    Correction,
    FillBlankExercise,
)
from api.deps import get_agent

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    """Envía un mensaje al tutor y recibe respuesta con correcciones opcionales."""
    agent = get_agent()

    # Seleccionar misión si se especifica
    if body.mission_id:
        try:
            agent.select_mission(body.mission_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    history = [{"role": t.role, "text": t.text} for t in body.history]
    result = agent.chat(body.message, history=history)

    exercise = None
    if result.get("exercise"):
        exercise = FillBlankExercise(**result["exercise"])

    return ChatResponse(
        response=result["response"],
        corrections=[Correction(**c) for c in result["corrections"]],
        exercise=exercise,
        turn=result["turn"],
    )


@router.post("/correct")
def correct_text(body: dict):
    """Analiza un texto y devuelve sugerencias de corrección gramatical."""
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=422, detail="El campo 'text' es obligatorio.")

    agent = get_agent()
    corrections = agent.correct_text(text)
    corrected = agent.apply_corrections(text)

    return {
        "original":    text,
        "corrected":   corrected,
        "corrections": corrections,
    }
