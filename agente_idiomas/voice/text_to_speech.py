"""Text-to-Speech: síntesis de voz desde texto con degradación elegante.

Uso básico::

    from voice.text_to_speech import TextToSpeech
    from voice.config import VoiceConfig

    tts = TextToSpeech(VoiceConfig())
    result = tts.speak("Hello! How are you today?")
    if not result["success"]:
        print("TTS no disponible:", result["error"])
        # La app muestra el texto en pantalla como fallback

Backends soportados:
    pyttsx3 — offline, sin coste, voz sintética local
    gtts    — Google Text-to-Speech online (necesita conexión + archivo MP3)
    none    — desactivado explícitamente
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from voice.config import VoiceConfig

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Detección de dependencias opcionales
# ---------------------------------------------------------------------------
try:
    import pyttsx3  # type: ignore
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False
    _LOG.warning(
        "pyttsx3 not installed — TTS offline unavailable. "
        "Install with: pip install pyttsx3"
    )

try:
    from gtts import gTTS  # type: ignore
    _GTTS_AVAILABLE = True
except ImportError:
    _GTTS_AVAILABLE = False
    _LOG.warning(
        "gTTS not installed — TTS online unavailable. "
        "Install with: pip install gtts"
    )


class TextToSpeech:
    """Sintetiza texto a voz con degradación elegante.

    Si ningún backend de TTS está disponible, los métodos devuelven
    ``success=False`` y la aplicación puede mostrar el texto en pantalla.
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self._pyttsx3_engine = None

    # ------------------------------------------------------------------
    # Capacidades
    # ------------------------------------------------------------------
    @staticmethod
    def is_available() -> bool:
        """Devuelve True si al menos un backend de TTS está disponible."""
        return _PYTTSX3_AVAILABLE or _GTTS_AVAILABLE

    def capabilities(self) -> dict:
        """Devuelve qué backends están disponibles."""
        return {
            "available": self.is_available(),
            "pyttsx3": _PYTTSX3_AVAILABLE,
            "gtts": _GTTS_AVAILABLE,
            "configured_backend": self.config.tts_backend,
            "language": self.config.language,
        }

    # ------------------------------------------------------------------
    # Síntesis principal
    # ------------------------------------------------------------------
    def speak(self, text: str) -> dict:
        """Sintetiza *text* y lo reproduce en el altavoz del sistema.

        Devuelve::

            {
                "success": bool,
                "text": str,
                "backend_used": str | None,
                "error": str | None,
                "fallback_needed": bool,
            }
        """
        if not self.config.enabled:
            return self._fallback(text, "Voice is disabled in configuration.")

        backend = self.config.tts_backend

        if backend == "pyttsx3":
            return self._speak_pyttsx3(text)
        if backend == "gtts":
            return self._speak_gtts(text, play=True)
        if backend == "none":
            return self._fallback(text, "TTS is set to 'none' — text-only mode.")

        # Auto-detect: intenta pyttsx3 primero, luego gTTS
        if _PYTTSX3_AVAILABLE:
            return self._speak_pyttsx3(text)
        if _GTTS_AVAILABLE:
            return self._speak_gtts(text, play=True)
        return self._fallback(text, "No TTS backend available.")

    def synthesize_to_file(self, text: str, output_path: str) -> dict:
        """Sintetiza *text* y guarda el audio en *output_path* (MP3 o WAV).

        Útil para generar respuestas de audio para la API REST.
        """
        if not self.config.enabled:
            return self._fallback(text, "Voice is disabled.")

        backend = self.config.tts_backend

        if backend == "gtts" or (not _PYTTSX3_AVAILABLE and _GTTS_AVAILABLE):
            return self._save_gtts(text, output_path)

        if backend == "pyttsx3" or _PYTTSX3_AVAILABLE:
            return self._save_pyttsx3(text, output_path)

        return self._fallback(text, "No TTS backend available.")

    def synthesize_to_bytes(self, text: str) -> dict:
        """Sintetiza *text* y devuelve los bytes del audio (MP3).

        Devuelve::

            {
                "success": bool,
                "text": str,
                "audio_bytes": bytes | None,
                "format": "mp3" | None,
                "backend_used": str | None,
                "error": str | None,
                "fallback_needed": bool,
            }
        """
        if not _GTTS_AVAILABLE:
            result = self._fallback(text, "gTTS is required for bytes synthesis.")
            result["audio_bytes"] = None
            result["format"] = None
            return result

        try:
            lang = self.config.language.split("-")[0]  # 'en-US' → 'en'
            tts_obj = gTTS(text=text, lang=lang, slow=False)
            buffer = io.BytesIO()
            tts_obj.write_to_fp(buffer)
            buffer.seek(0)
            return {
                "success": True,
                "text": text,
                "audio_bytes": buffer.read(),
                "format": "mp3",
                "backend_used": "gtts",
                "error": None,
                "fallback_needed": False,
            }
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("gTTS bytes synthesis error: %s", exc)
            result = self._fallback(text, f"gTTS error: {exc}")
            result["audio_bytes"] = None
            result["format"] = None
            return result

    # ------------------------------------------------------------------
    # Backends privados
    # ------------------------------------------------------------------
    def _speak_pyttsx3(self, text: str) -> dict:
        if not _PYTTSX3_AVAILABLE:
            return self._fallback(text, "pyttsx3 is not installed.")
        try:
            engine = self._get_pyttsx3_engine()
            engine.say(text)
            engine.runAndWait()
            return {
                "success": True,
                "text": text,
                "backend_used": "pyttsx3",
                "error": None,
                "fallback_needed": False,
            }
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("pyttsx3 speak error: %s", exc)
            return self._fallback(text, f"pyttsx3 error: {exc}")

    def _speak_gtts(self, text: str, play: bool = True) -> dict:
        if not _GTTS_AVAILABLE:
            return self._fallback(text, "gTTS is not installed.")
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            lang = self.config.language.split("-")[0]
            tts_obj = gTTS(text=text, lang=lang, slow=False)
            tts_obj.save(tmp_path)

            if play:
                # Intentar reproducir con playsound o el player del sistema
                _play_audio_file(tmp_path)

            return {
                "success": True,
                "text": text,
                "backend_used": "gtts",
                "audio_file": tmp_path,
                "error": None,
                "fallback_needed": False,
            }
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("gTTS speak error: %s", exc)
            return self._fallback(text, f"gTTS error: {exc}")

    def _save_gtts(self, text: str, output_path: str) -> dict:
        if not _GTTS_AVAILABLE:
            return self._fallback(text, "gTTS is not installed.")
        try:
            lang = self.config.language.split("-")[0]
            tts_obj = gTTS(text=text, lang=lang, slow=False)
            tts_obj.save(output_path)
            return {
                "success": True,
                "text": text,
                "backend_used": "gtts",
                "audio_file": output_path,
                "error": None,
                "fallback_needed": False,
            }
        except Exception as exc:  # noqa: BLE001
            return self._fallback(text, f"gTTS save error: {exc}")

    def _save_pyttsx3(self, text: str, output_path: str) -> dict:
        if not _PYTTSX3_AVAILABLE:
            return self._fallback(text, "pyttsx3 is not installed.")
        try:
            engine = self._get_pyttsx3_engine()
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            return {
                "success": True,
                "text": text,
                "backend_used": "pyttsx3",
                "audio_file": output_path,
                "error": None,
                "fallback_needed": False,
            }
        except Exception as exc:  # noqa: BLE001
            return self._fallback(text, f"pyttsx3 save error: {exc}")

    def _get_pyttsx3_engine(self):
        """Devuelve una instancia reutilizable del motor pyttsx3."""
        if self._pyttsx3_engine is None:
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", self.config.tts_rate)
            self._pyttsx3_engine.setProperty("volume", self.config.tts_volume)
        return self._pyttsx3_engine

    @staticmethod
    def _fallback(text: str, reason: str) -> dict:
        return {
            "success": False,
            "text": text,
            "backend_used": None,
            "error": reason,
            "fallback_needed": True,
        }


# ---------------------------------------------------------------------------
# Reproducción de audio (helper de sistema)
# ---------------------------------------------------------------------------
def _play_audio_file(path: str) -> None:
    """Intenta reproducir un archivo de audio sin bloquear la app."""
    try:
        import playsound  # type: ignore
        playsound.playsound(path, block=False)
        return
    except ImportError:
        pass

    # Fallback a reproductores del sistema
    import subprocess
    import sys
    if sys.platform.startswith("darwin"):
        subprocess.Popen(["afplay", path])
    elif sys.platform.startswith("linux"):
        for player in ("mpg123", "mpg321", "aplay", "ffplay"):
            try:
                subprocess.Popen(
                    [player, path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except FileNotFoundError:
                continue
        _LOG.warning("No audio player found to play %s", path)
    elif sys.platform.startswith("win"):
        import winsound  # type: ignore
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
