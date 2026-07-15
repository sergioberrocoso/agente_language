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
    difficulty: Optional[str] = None
    feedback: Optional[str] = None
    pairs: Optional[list[dict]] = None


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
    difficulty: str = Field(default="beginner", pattern=r"^(beginner|intermediate|advanced)$")


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


class FlashcardStateRequest(BaseModel):
    user_id: int = Field(default=0)
    word: str = Field(..., min_length=1)
    known: bool
    source: str = Field(default="mission")


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------
class CSVImportResult(BaseModel):
    imported: int
    skipped_duplicates: int
    errors: list[str]
    source: str
    imported_at: str


# ---------------------------------------------------------------------------
# Corrección
# ---------------------------------------------------------------------------
class Correction(BaseModel):
    original: str
    suggested: str
    position: int
    rule: str
    explanation: str
    why: Optional[str] = None
    better_example: Optional[str] = None


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
# Voz
# ---------------------------------------------------------------------------
class VoiceConfigRequest(BaseModel):
    enabled: bool = True
    language: str = "en-US"
    tts_backend: str = Field(default="pyttsx3", pattern=r"^(pyttsx3|gtts|none)$")
    stt_backend: str = Field(default="google", pattern=r"^(google|sphinx|none)$")
    tts_rate: int = Field(default=150, ge=50, le=400)
    tts_volume: float = Field(default=1.0, ge=0.0, le=1.0)


class VoiceTextTurnRequest(BaseModel):
    text: str = Field(..., min_length=1)
    mission_id: Optional[str] = None
    speak_response: bool = False


class VoiceTurnResponse(BaseModel):
    user_text: Optional[str] = None
    response: Optional[str] = None
    corrections: list[Correction] = Field(default_factory=list)
    exercise: Optional[FillBlankExercise] = None
    turn: int = 0
    stt_success: bool = False
    tts_success: bool = False
    fallback_to_text: bool = True
    stt_error: Optional[str] = None
    tts_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Progreso de usuario
# ---------------------------------------------------------------------------
class RecordExerciseRequest(BaseModel):
    user_id: int = Field(default=0)
    exercise_type: str
    prompt: str
    user_answer: Optional[str] = None
    correct: bool = False
    mission_id: Optional[str] = None
    difficulty: Optional[str] = None
    feedback: Optional[str] = None


class RecordTurnRequest(BaseModel):
    user_id: int = Field(default=0)
    role: str = Field(..., pattern=r"^(student|tutor)$")
    text: str = Field(..., min_length=1)
    corrections: list[dict] = Field(default_factory=list)
    mission_id: Optional[str] = None


class SetPreferenceRequest(BaseModel):
    user_id: int = Field(default=0)
    key: str = Field(..., min_length=1)
    value: Any


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
