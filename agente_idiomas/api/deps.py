"""Dependencias compartidas: agente y base de datos de vocabulario."""

from __future__ import annotations

from pathlib import Path

from agent.language_tutor import LanguageTutorAgent
from db.vocabulary_db import VocabularyDB

_DATA_DIR = Path(__file__).parent.parent / "data"
_VOCAB_JSON = _DATA_DIR / "core_vocab_500.json"
_MISSIONS_JSON = _DATA_DIR / "missions.json"
_NGSL_CSV = _DATA_DIR / "NGSL_1.2_lemmatized_for_teaching.csv"

# Instancias únicas (singleton de proceso)
_agent: LanguageTutorAgent | None = None
_vocab_db: VocabularyDB | None = None


def get_agent() -> LanguageTutorAgent:
    global _agent
    if _agent is None:
        _agent = LanguageTutorAgent(language="English")
        if _VOCAB_JSON.exists():
            _agent.load_core_vocab(str(_VOCAB_JSON))
        if _MISSIONS_JSON.exists():
            _agent.load_missions(str(_MISSIONS_JSON))
    return _agent


def get_vocab_db() -> VocabularyDB:
    global _vocab_db
    if _vocab_db is None:
        _vocab_db = VocabularyDB(
            db_path=":memory:",
            ngsl_csv_path=str(_NGSL_CSV) if _NGSL_CSV.exists() else None,
        )
    return _vocab_db
