"""Flujo de conversación por voz: STT → agente → TTS.

Uso::

    from voice.voice_conversation import VoiceConversation
    from voice.config import VoiceConfig

    vc = VoiceConversation(agent, VoiceConfig())
    result = vc.voice_turn()  # escucha, procesa, habla
    if result["fallback_to_text"]:
        user_input = input("(TTS/STT no disponible) Escribe tu mensaje: ")
        result = vc.text_turn(user_input)
"""

from __future__ import annotations

import logging
from typing import Optional

from voice.config import VoiceConfig
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech

_LOG = logging.getLogger(__name__)


class VoiceConversation:
    """Orquesta un turno de conversación por voz.

    Si STT o TTS no están disponibles (o si la voz está desactivada),
    la clase opera en modo texto sin lanzar excepciones.
    """

    def __init__(self, agent, config: Optional[VoiceConfig] = None):
        """
        Args:
            agent:  Instancia de ``LanguageTutorAgent``.
            config: Configuración de voz (usa valores por defecto si no se pasa).
        """
        self.agent = agent
        self.config = config or VoiceConfig()
        self.stt = SpeechToText(self.config)
        self.tts = TextToSpeech(self.config)
        self._history: list[dict] = []

    # ------------------------------------------------------------------
    # Información de capacidades
    # ------------------------------------------------------------------
    def capabilities(self) -> dict:
        """Devuelve las capacidades disponibles para el turno de voz."""
        return {
            "voice_enabled": self.config.enabled,
            "stt": self.stt.capabilities(),
            "tts": self.tts.capabilities(),
        }

    # ------------------------------------------------------------------
    # Turno por voz
    # ------------------------------------------------------------------
    def voice_turn(
        self,
        mission_id: Optional[str] = None,
        speak_response: bool = True,
    ) -> dict:
        """Realiza un turno completo de conversación por voz.

        Flujo:
            1. Escucha al usuario (STT)
            2. Procesa el mensaje con el agente
            3. Sintetiza la respuesta (TTS)

        Devuelve::

            {
                "user_text": str | None,
                "response": str,
                "corrections": list,
                "exercise": dict | None,
                "turn": int,
                "stt_success": bool,
                "tts_success": bool,
                "fallback_to_text": bool,   # True si STT falló
                "stt_error": str | None,
                "tts_error": str | None,
            }
        """
        # Paso 1: STT
        stt_result = self.stt.listen()
        if not stt_result["success"]:
            _LOG.info("STT failed: %s", stt_result["error"])
            return {
                "user_text": None,
                "response": None,
                "corrections": [],
                "exercise": None,
                "turn": len(self._history) + 1,
                "stt_success": False,
                "tts_success": False,
                "fallback_to_text": True,
                "stt_error": stt_result["error"],
                "tts_error": None,
            }

        user_text = stt_result["text"]
        _LOG.info("STT transcribed: %s", user_text)

        # Paso 2: procesar con el agente
        return self._process_and_speak(
            user_text,
            mission_id=mission_id,
            speak_response=speak_response,
            stt_success=True,
        )

    # ------------------------------------------------------------------
    # Turno por texto (fallback)
    # ------------------------------------------------------------------
    def text_turn(
        self,
        user_text: str,
        mission_id: Optional[str] = None,
        speak_response: bool = True,
    ) -> dict:
        """Procesa un turno de texto y opcionalmente habla la respuesta.

        Útil cuando STT no está disponible o el usuario prefiere escribir.
        """
        return self._process_and_speak(
            user_text,
            mission_id=mission_id,
            speak_response=speak_response,
            stt_success=False,
        )

    # ------------------------------------------------------------------
    # Reset de historial
    # ------------------------------------------------------------------
    def reset_history(self) -> None:
        """Reinicia el historial de la conversación."""
        self._history.clear()

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------
    def _process_and_speak(
        self,
        user_text: str,
        mission_id: Optional[str],
        speak_response: bool,
        stt_success: bool,
    ) -> dict:
        """Procesa el texto con el agente y opcionalmente sintetiza la respuesta."""
        if mission_id:
            try:
                self.agent.select_mission(mission_id)
            except ValueError:
                _LOG.warning("Mission not found: %s", mission_id)

        agent_result = self.agent.chat(user_text, history=self._history)
        response_text = agent_result["response"]

        # Actualizar historial interno
        self._history.append({"role": "student", "text": user_text})
        self._history.append({"role": "tutor", "text": response_text})

        # Paso 3: TTS
        tts_success = False
        tts_error = None
        if speak_response and self.config.enabled:
            tts_result = self.tts.speak(response_text)
            tts_success = tts_result["success"]
            tts_error = tts_result.get("error")

        return {
            "user_text": user_text,
            "response": response_text,
            "corrections": agent_result.get("corrections", []),
            "exercise": agent_result.get("exercise"),
            "turn": agent_result.get("turn", len(self._history)),
            "stt_success": stt_success,
            "tts_success": tts_success,
            "fallback_to_text": not stt_success,
            "stt_error": None if stt_success else "Used text input",
            "tts_error": tts_error,
        }
