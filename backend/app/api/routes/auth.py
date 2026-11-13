"""
auth.py (routes)

  POST /auth/register   create an account (requires explicit consent)
  POST /auth/login      exchange email + password for an access token
  GET  /auth/me         who am I (also a quick way to check a token works)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    dummy_hash,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.db.session import get_db
from app.repositories import users as user_repo
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: DbSession, settings: AppSettings) -> UserOut:
    if body.consent_version != settings.consent_version:
        # The privacy text changed since the page was loaded. Don't record
        # consent to wording the person may not have seen.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The privacy notice has been updated. Please reload and review it.",
        )

    try:
        user = user_repo.create_user(
            db,
            email=body.email,
            password_hash=hash_password(body.password),
            consent_version=settings.consent_version,
        )
    except user_repo.EmailAlreadyRegistered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession, settings: AppSettings) -> TokenResponse:
    bad_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = user_repo.get_by_email(db, body.email)
    if user is None:
        verify_password(body.password, dummy_hash())  # same cost as a real check
        raise bad_credentials
    if not verify_password(body.password, user.password_hash):
        raise bad_credentials

    if needs_rehash(user.password_hash):
        user_repo.update_password_hash(db, user, hash_password(body.password))

    token = create_access_token(
        user.id,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.access_token_expire_minutes,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return user
