"""
deps.py

Shared FastAPI dependencies. `get_current_user` is how every protected
route learns who is calling: it validates the bearer token and then loads
the user from the database.

Loading the user (rather than trusting the token alone) means a deleted
account stops working immediately, even if its token hasn't expired yet.
Every failure returns the same 401, so a caller can't tell a bad signature
from an expired token from a deleted account.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import InvalidToken, decode_access_token
from app.db.models import User
from app.db.session import get_db
from app.repositories import users as user_repo
from app.services.model_registry import ModelRegistry

# auto_error=False so a missing header goes through our 401 below rather than
# the framework's own response.
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        user_id = decode_access_token(
            credentials.credentials,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
    except InvalidToken:
        raise _unauthorized() from None

    user = user_repo.get_by_id(db, user_id)
    if user is None:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_registry(request: Request) -> ModelRegistry:
    """The models loaded once at startup (see the lifespan in main.py)."""
    return request.app.state.registry
