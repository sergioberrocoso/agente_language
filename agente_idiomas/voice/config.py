"""Configuración de voz del tutor."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VoiceConfig:
    """Parámetros de configuración para el módulo de voz.

    Atributos:
        enabled         : activa/desactiva todo el módulo de voz.
        language        : código BCP-47 para STT y TTS (por defecto 'en-US').
        tts_backend     : 'pyttsx3' (offline) | 'gtts' (online) | 'none'.
        stt_backend     : 'google' (online) | 'sphinx' (offline) | 'none'.
        tts_rate        : velocidad del habla para pyttsx3 (palabras/min).
        tts_volume      : volumen pyttsx3 (0.0 – 1.0).
        audio_timeout   : segundos de espera para captura de audio.
        phrase_time_limit: límite de segundos por frase para STT.
    """

    enabled: bool = True
    language: str = "en-US"
    tts_backend: str = "pyttsx3"
    stt_backend: str = "google"
    tts_rate: int = 150
    tts_volume: float = 1.0
    audio_timeout: int = 5
    phrase_time_limit: int = 15

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "language": self.language,
            "tts_backend": self.tts_backend,
            "stt_backend": self.stt_backend,
            "tts_rate": self.tts_rate,
            "tts_volume": self.tts_volume,
            "audio_timeout": self.audio_timeout,
            "phrase_time_limit": self.phrase_time_limit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
