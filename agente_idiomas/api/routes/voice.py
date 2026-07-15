"""Rutas de la API para conversaciones por voz."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import (
    Correction,
    FillBlankExercise,
    VoiceConfigRequest,
    VoiceTextTurnRequest,
    VoiceTurnResponse,
)
from api.deps import get_agent
from voice.config import VoiceConfig
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech
from voice.voice_conversation import VoiceConversation

router = APIRouter(prefix="/voice", tags=["voice"])

# Conversación de voz por sesión (simplificado: una única sesión global)
_voice_session: VoiceConversation | None = None
_voice_config: VoiceConfig = VoiceConfig()


def _get_voice_session() -> VoiceConversation:
    global _voice_session
    if _voice_session is None:
        _voice_session = VoiceConversation(get_agent(), _voice_config)
    return _voice_session


@router.get("/capabilities")
def voice_capabilities():
    """Devuelve qué backends de voz están disponibles en este entorno."""
    stt = SpeechToText(_voice_config)
    tts = TextToSpeech(_voice_config)
    return {
        "stt": stt.capabilities(),
        "tts": tts.capabilities(),
        "config": _voice_config.to_dict(),
    }


@router.post("/config")
def set_voice_config(body: VoiceConfigRequest):
    """Actualiza la configuración de voz (idioma, backends, etc.)."""
    global _voice_config, _voice_session
    _voice_config = VoiceConfig(
        enabled=body.enabled,
        language=body.language,
        tts_backend=body.tts_backend,
        stt_backend=body.stt_backend,
        tts_rate=body.tts_rate,
        tts_volume=body.tts_volume,
    )
    _voice_session = None  # Reset the session with new config
    return {"status": "updated", "config": _voice_config.to_dict()}


@router.post("/turn/text", response_model=VoiceTurnResponse)
def voice_turn_text(body: VoiceTextTurnRequest):
    """Procesa un turno de texto con respuesta hablada opcional.

    Equivale a ``/chat`` pero usa el flujo de conversación por voz, con
    contexto de sesión mantenido. Si ``speak_response=true``, intenta
    sintetizar la respuesta del tutor (requiere TTS instalado).
    """
    session = _get_voice_session()
    result = session.text_turn(
        user_text=body.text,
        mission_id=body.mission_id,
        speak_response=body.speak_response,
    )

    corrections = [Correction(**c) for c in result.get("corrections", [])]
    exercise = None
    if result.get("exercise"):
        exercise = FillBlankExercise(**result["exercise"])

    return VoiceTurnResponse(
        user_text=result.get("user_text"),
        response=result.get("response"),
        corrections=corrections,
        exercise=exercise,
        turn=result.get("turn", 0),
        stt_success=result.get("stt_success", False),
        tts_success=result.get("tts_success", False),
        fallback_to_text=result.get("fallback_to_text", True),
        stt_error=result.get("stt_error"),
        tts_error=result.get("tts_error"),
    )


@router.post("/session/reset")
def reset_voice_session():
    """Reinicia el historial de la sesión de voz."""
    global _voice_session
    if _voice_session is not None:
        _voice_session.reset_history()
    return {"status": "session_reset"}
