"""Aplicación FastAPI del tutor de idiomas."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes.missions import router as missions_router
from api.routes.vocabulary import router as vocabulary_router
from api.routes.chat import router as chat_router
from api.routes.flashcards import router as flashcards_router
from api.deps import get_agent, get_vocab_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Precarga el agente y la BD de vocabulario al arrancar."""
    get_agent()
    get_vocab_db()
    yield


app = FastAPI(
    title="Agente Tutor de Idiomas",
    description=(
        "API REST para practicar idiomas: conversación, "
        "corrección gramatical, ejercicios de relleno y flashcards."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Registrar rutas
app.include_router(missions_router)
app.include_router(vocabulary_router)
app.include_router(chat_router)
app.include_router(flashcards_router)


@app.get("/health", tags=["status"])
def health():
    """Comprueba que el servidor está activo."""
    agent = get_agent()
    db = get_vocab_db()
    return {
        "status":         "ok",
        "language":       agent.language,
        "missions_count": len(agent.missions),
        "vocab_count":    db.count(),
    }
