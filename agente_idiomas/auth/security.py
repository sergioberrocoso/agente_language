"""Utilidades de seguridad para autenticación."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any


class TokenError(ValueError):
    """Error de token JWT."""


_LOG = logging.getLogger(__name__)
_WARNED_DEFAULT_SECRET = False
_DEFAULT_JWT_SECRET = base64.urlsafe_b64encode(os.urandom(48)).decode("ascii")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(encoded: str) -> bytes:
    padding = "=" * ((4 - (len(encoded) % 4)) % 4)
    return base64.urlsafe_b64decode(encoded + padding)


def _jwt_secret() -> str:
    global _WARNED_DEFAULT_SECRET
    secret = os.getenv("JWT_SECRET")
    if secret:
        return secret
    if not _WARNED_DEFAULT_SECRET:
        _LOG.warning(
            "JWT_SECRET no está configurado; usando secreto por defecto de desarrollo.",
        )
        _WARNED_DEFAULT_SECRET = True
    return _DEFAULT_JWT_SECRET


def _jwt_expire_minutes() -> int:
    raw = os.getenv("JWT_EXPIRE_MINUTES", "60")
    try:
        return int(raw)
    except ValueError:
        return 60


def hash_password(password: str) -> str:
    """Hashea contraseña con PBKDF2-HMAC-SHA256 + salt aleatoria."""
    iterations = 600_000
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return (
        f"pbkdf2_sha256${iterations}$"
        f"{_b64url_encode(salt)}${_b64url_encode(digest)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica contraseña contra hash almacenado."""
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = _b64url_decode(salt_raw)
        expected = _b64url_decode(digest_raw)
    except (ValueError, TypeError):
        return False

    current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(current, expected)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Crea JWT HS256 con `sub` y `exp`."""
    ttl = _jwt_expire_minutes() if expires_minutes is None else expires_minutes
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=ttl)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "exp": int(exp.timestamp())}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(_jwt_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Valida JWT HS256 y devuelve payload."""
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
    except ValueError as exc:
        raise TokenError("Malformed token") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_signature = hmac.new(
        _jwt_secret().encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    try:
        provided_signature = _b64url_decode(signature_b64)
    except (ValueError, binascii.Error) as exc:
        raise TokenError("Invalid token signature") from exc

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise TokenError("Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, binascii.Error) as exc:
        raise TokenError("Invalid token payload") from exc

    if not isinstance(payload, dict):
        raise TokenError("Invalid token payload")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise TokenError("Invalid token expiration")
    if exp <= int(datetime.now(UTC).timestamp()):
        raise TokenError("Token expired")

    return payload
