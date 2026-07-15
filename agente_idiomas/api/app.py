"""Aplicación FastAPI del tutor de idiomas."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes.missions import router as missions_router
from api.routes.vocabulary import router as vocabulary_router
from api.routes.chat import router as chat_router
from api.routes.flashcards import router as flashcards_router
from api.routes.auth import router as auth_router
from api.routes.voice import router as voice_router
from api.routes.progress import router as progress_router
from api.deps import get_agent, get_vocab_db, get_user_progress_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Precarga el agente, la BD de vocabulario y la BD de progreso al arrancar."""
    get_agent()
    get_vocab_db()
    get_user_progress_db()
    yield


app = FastAPI(
    title="Agente Tutor de Idiomas",
    description=(
        "API REST para practicar idiomas: conversación, "
        "corrección gramatical mejorada, ejercicios con niveles, "
        "conversaciones por voz, flashcards con importación CSV "
        "y persistencia de progreso de usuario."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# Registrar rutas
app.include_router(missions_router)
app.include_router(vocabulary_router)
app.include_router(chat_router)
app.include_router(flashcards_router)
app.include_router(auth_router)
app.include_router(voice_router)
app.include_router(progress_router)


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
