"""Módulo de voz para el tutor de idiomas.

Proporciona:
  - VoiceConfig  : configuración de voz (idioma, activado/desactivado, etc.)
  - SpeechToText : transcripción de audio a texto (con fallback gracioso)
  - TextToSpeech : síntesis de voz desde texto (con fallback gracioso)

Dependencias opcionales:
  - SpeechRecognition (``speech_recognition``) para STT
  - pyttsx3 para TTS offline
  - gTTS (``gtts``) como alternativa online de TTS

Si alguna dependencia falta, el módulo opera en modo texto (fallback)
y registra un aviso en los logs.
"""
