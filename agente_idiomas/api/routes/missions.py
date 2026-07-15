"""Rutas de la API para misiones."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import (
    CreateOpenMissionRequest,
    Exercise,
    Flashcard,
    FlashcardBack,
    Mission,
)
from api.deps import get_agent

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("", response_model=list[Mission])
def list_missions():
    """Devuelve todas las misiones disponibles."""
    agent = get_agent()
    return [Mission(**m) for m in agent.missions]


@router.get("/{mission_id}", response_model=Mission)
def get_mission(mission_id: str):
    """Devuelve el detalle de una misión por su ID."""
    agent = get_agent()
    for m in agent.missions:
        if m["id"] == mission_id:
            return Mission(**m)
    raise HTTPException(status_code=404, detail=f"Misión no encontrada: {mission_id}")


@router.post("", response_model=Mission, status_code=201)
def create_open_mission(body: CreateOpenMissionRequest):
    """Crea una misión abierta a partir de una descripción en lenguaje natural."""
    agent = get_agent()
    # Comprobar que el ID no exista ya
    if any(m["id"] == body.mission_id for m in agent.missions):
        raise HTTPException(status_code=409, detail=f"Ya existe la misión: {body.mission_id}")
    mission = agent.create_open_mission(
        description=body.description,
        mission_id=body.mission_id,
        difficulty=body.difficulty,
    )
    return Mission(**mission)


@router.get("/{mission_id}/vocabulary")
def get_mission_vocabulary(mission_id: str):
    """Devuelve el vocabulario relevante para una misión."""
    agent = get_agent()
    try:
        agent.select_mission(mission_id)
        vocab = agent.get_mission_vocabulary()
        return {"mission_id": mission_id, "vocabulary": vocab}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{mission_id}/exercises", response_model=list[Exercise])
def get_mission_exercises(mission_id: str):
    """Devuelve los ejercicios de una misión."""
    agent = get_agent()
    for m in agent.missions:
        if m["id"] == mission_id:
            return [Exercise(**e) for e in m.get("exercises", [])]
    raise HTTPException(status_code=404, detail=f"Misión no encontrada: {mission_id}")


@router.get("/{mission_id}/flashcards", response_model=list[Flashcard])
def get_mission_flashcards(mission_id: str):
    """Genera y devuelve las flashcards de una misión."""
    agent = get_agent()
    try:
        agent.select_mission(mission_id)
        cards = agent.generate_flashcards()
        return [
            Flashcard(
                front=c["front"],
                back=FlashcardBack(**c["back"]),
            )
            for c in cards
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
