"""Dependencias compartidas: agente y base de datos de vocabulario."""

from __future__ import annotations

import os
import logging
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent.language_tutor import LanguageTutorAgent
from auth.security import TokenError, decode_access_token
from db.user_db import UserDB
from db.user_progress_db import UserProgressDB
from db.vocabulary_db import VocabularyDB

_DATA_DIR = Path(__file__).parent.parent / "data"
_VOCAB_JSON = _DATA_DIR / "core_vocab_500.json"
_MISSIONS_JSON = _DATA_DIR / "missions.json"
_NGSL_CSV = _DATA_DIR / "NGSL_1.2_lemmatized_for_teaching.csv"

# Instancias únicas (singleton de proceso)
_agent: LanguageTutorAgent | None = None
_vocab_db: VocabularyDB | None = None
_user_db: UserDB | None = None
_user_progress_db: UserProgressDB | None = None
_bearer = HTTPBearer(auto_error=False)
_LOG = logging.getLogger(__name__)


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


def get_user_db() -> UserDB:
    global _user_db
    if _user_db is None:
        _user_db = UserDB(
            db_path=os.getenv("USER_DB_PATH", str(_DATA_DIR / "users.db")),
        )
    return _user_db


def get_user_progress_db() -> UserProgressDB:
    global _user_progress_db
    if _user_progress_db is None:
        _user_progress_db = UserProgressDB(
            db_path=os.getenv(
                "USER_PROGRESS_DB_PATH",
                str(_DATA_DIR / "user_progress.db"),
            ),
        )
    return _user_progress_db


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    user_db: UserDB = Depends(get_user_db),
) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        _LOG.debug("Invalid token in authentication: %s", exc)
        raise unauthorized from exc

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        _LOG.debug("Token without valid sub claim: %s", payload.get("sub"))
        raise unauthorized

    user = user_db.get_by_id(user_id)
    if user is None:
        _LOG.debug("User not found for sub=%s", user_id)
        raise unauthorized

    return user
