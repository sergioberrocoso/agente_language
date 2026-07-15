"""Speech-to-Text: transcripción de audio a texto con degradación elegante.

Uso básico::

    from voice.speech_to_text import SpeechToText
    from voice.config import VoiceConfig

    stt = SpeechToText(VoiceConfig())
    result = stt.listen()
    if result["success"]:
        print("Transcripción:", result["text"])
    else:
        print("Error:", result["error"])
        # Fallback: pide al usuario que escriba el mensaje
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Optional

from voice.config import VoiceConfig

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Detección de dependencias opcionales
# ---------------------------------------------------------------------------
try:
    import speech_recognition as sr  # type: ignore
    _SR_AVAILABLE = True
except ImportError:
    _SR_AVAILABLE = False
    _LOG.warning(
        "SpeechRecognition not installed — STT will return fallback text. "
        "Install with: pip install SpeechRecognition pyaudio"
    )


class SpeechToText:
    """Transcribe audio a texto usando el micrófono o un archivo de audio.

    Si la dependencia ``SpeechRecognition`` no está instalada, o si ocurre
    cualquier error de hardware/red, el método devuelve ``success=False``
    con un mensaje descriptivo y la aplicación puede solicitar input de texto
    como alternativa.
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self._recognizer = None
        if _SR_AVAILABLE:
            self._recognizer = sr.Recognizer()

    # ------------------------------------------------------------------
    # Capacidades
    # ------------------------------------------------------------------
    @staticmethod
    def is_available() -> bool:
        """Devuelve True si SpeechRecognition está disponible."""
        return _SR_AVAILABLE

    def capabilities(self) -> dict:
        """Devuelve las capacidades disponibles del STT."""
        return {
            "available": _SR_AVAILABLE,
            "backend": self.config.stt_backend if _SR_AVAILABLE else "none",
            "language": self.config.language,
        }

    # ------------------------------------------------------------------
    # Escucha desde micrófono
    # ------------------------------------------------------------------
    def listen(self) -> dict:
        """Graba audio desde el micrófono y transcribe.

        Devuelve::

            {
                "success": bool,
                "text": str | None,
                "error": str | None,
                "fallback_needed": bool,
            }
        """
        if not self.config.enabled:
            return self._fallback("Voice is disabled in configuration.")

        if not _SR_AVAILABLE:
            return self._fallback(
                "SpeechRecognition is not installed. "
                "Install with: pip install SpeechRecognition pyaudio"
            )

        try:
            with sr.Microphone() as source:
                _LOG.info("Adjusting for ambient noise…")
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                _LOG.info("Listening (timeout=%ss)…", self.config.audio_timeout)
                audio = self._recognizer.listen(
                    source,
                    timeout=self.config.audio_timeout,
                    phrase_time_limit=self.config.phrase_time_limit,
                )

            return self._transcribe(audio)

        except Exception as exc:  # noqa: BLE001
            _LOG.warning("STT listen error: %s", exc)
            return self._fallback(f"Could not capture audio: {exc}")

    # ------------------------------------------------------------------
    # Transcripción desde archivo
    # ------------------------------------------------------------------
    def transcribe_file(self, audio_path: str) -> dict:
        """Transcribe un archivo de audio (.wav, .aiff, .flac).

        Útil para tests y entornos sin micrófono.
        """
        if not _SR_AVAILABLE:
            return self._fallback("SpeechRecognition is not installed.")

        path = Path(audio_path)
        if not path.exists():
            return self._fallback(f"Audio file not found: {audio_path}")

        try:
            with sr.AudioFile(str(path)) as source:
                audio = self._recognizer.record(source)
            return self._transcribe(audio)
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("STT file transcription error: %s", exc)
            return self._fallback(f"Could not transcribe file: {exc}")

    # ------------------------------------------------------------------
    # Transcripción desde bytes de audio
    # ------------------------------------------------------------------
    def transcribe_bytes(self, audio_bytes: bytes, sample_rate: int = 16000) -> dict:
        """Transcribe audio desde bytes raw (WAV).

        Pensado para integraciones con la API REST donde el cliente
        envía el audio en base64/bytes.
        """
        if not _SR_AVAILABLE:
            return self._fallback("SpeechRecognition is not installed.")

        try:
            audio_file = io.BytesIO(audio_bytes)
            with sr.AudioFile(audio_file) as source:
                audio = self._recognizer.record(source)
            return self._transcribe(audio)
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("STT bytes transcription error: %s", exc)
            return self._fallback(f"Could not transcribe audio bytes: {exc}")

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------
    def _transcribe(self, audio) -> dict:  # type: ignore[return]
        """Envía el audio al backend seleccionado y devuelve el resultado."""
        backend = self.config.stt_backend
        lang = self.config.language

        try:
            if backend == "google":
                text = self._recognizer.recognize_google(audio, language=lang)
            elif backend == "sphinx":
                text = self._recognizer.recognize_sphinx(audio)
            else:
                return self._fallback(f"Unknown STT backend: {backend}")

            return {
                "success": True,
                "text": text,
                "error": None,
                "fallback_needed": False,
            }

        except sr.UnknownValueError:
            return self._fallback("Could not understand audio. Please speak clearly.")
        except sr.RequestError as exc:
            return self._fallback(f"STT service unavailable: {exc}")
        except Exception as exc:  # noqa: BLE001
            return self._fallback(f"Transcription error: {exc}")

    @staticmethod
    def _fallback(reason: str) -> dict:
        return {
            "success": False,
            "text": None,
            "error": reason,
            "fallback_needed": True,
        }
