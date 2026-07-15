"""Rutas de autenticación de usuarios."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user, get_user_db
from api.schemas import AuthLoginRequest, AuthRegisterRequest, PublicUser, TokenResponse
from auth.security import create_access_token, hash_password, verify_password
from db.user_db import UserDB

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
def register_user(body: AuthRegisterRequest, user_db: UserDB = Depends(get_user_db)):
    """Registra un usuario con email único."""
    try:
        user = user_db.create_user(
            email=body.email,
            password_hash=hash_password(body.password),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        ) from exc

    return {"id": user["id"], "email": user["email"]}


@router.post("/login", response_model=TokenResponse)
def login_user(body: AuthLoginRequest, user_db: UserDB = Depends(get_user_db)):
    """Valida credenciales y devuelve token Bearer."""
    user = user_db.get_by_email(body.email)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(str(user["id"])),
        "token_type": "bearer",
    }


@router.get("/me", response_model=PublicUser)
def get_me(current_user: dict = Depends(get_current_user)):
    """Devuelve el usuario autenticado."""
    return {"id": current_user["id"], "email": current_user["email"]}

