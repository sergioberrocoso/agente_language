"""Modelos Pydantic para la API REST del tutor de idiomas."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Vocabulario
# ---------------------------------------------------------------------------
class VocabularyEntry(BaseModel):
    id: int
    headword: str
    forms: list[str]
    tags: list[str]
    frequency_rank: Optional[int] = None


# ---------------------------------------------------------------------------
# Misiones
# ---------------------------------------------------------------------------
class DialogueTurn(BaseModel):
    speaker: str
    text: str


class Exercise(BaseModel):
    type: str
    text: str
    blanks: Optional[list[str]] = None
    hint: Optional[str] = None
    options: Optional[list[str]] = None
    answer: Optional[str] = None


class Mission(BaseModel):
    id: str
    name: str
    goal: str
    vocabulary_tags: list[str]
    dialogues: list[DialogueTurn]
    exercises: list[Exercise]


class CreateOpenMissionRequest(BaseModel):
    description: str = Field(..., min_length=3)
    mission_id: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Flashcards
# ---------------------------------------------------------------------------
class FlashcardBack(BaseModel):
    definition: str
    example: str
    translation: str


class Flashcard(BaseModel):
    front: str
    back: FlashcardBack


class FlashcardExportRequest(BaseModel):
    flashcards: list[Flashcard]
    output_path: str = "exports/deck.tsv"


# ---------------------------------------------------------------------------
# Corrección
# ---------------------------------------------------------------------------
class Correction(BaseModel):
    original: str
    suggested: str
    position: int
    rule: str
    explanation: str


class CorrectTextRequest(BaseModel):
    text: str = Field(..., min_length=1)


class CorrectTextResponse(BaseModel):
    original: str
    corrected: str
    corrections: list[Correction]


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
class ChatHistoryTurn(BaseModel):
    role: str  # "student" | "tutor"
    text: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[ChatHistoryTurn] = Field(default_factory=list)
    mission_id: Optional[str] = None


class FillBlankExercise(BaseModel):
    original: str
    exercise: str
    blanks: list[str]


class ChatResponse(BaseModel):
    response: str
    corrections: list[Correction]
    exercise: Optional[FillBlankExercise] = None
    turn: int


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class AuthRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=12, max_length=128)


class AuthLoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=12, max_length=128)


class PublicUser(BaseModel):
    id: int
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
