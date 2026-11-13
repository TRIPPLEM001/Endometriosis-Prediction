"""
security.py

Password hashing and access tokens. Nothing here touches the database or
FastAPI, so it can be tested on its own.

Passwords
  Argon2id (the argon2-cffi defaults, which follow RFC 9106). Each hash
  embeds its own random salt and parameters, so verification needs only the
  stored string, and parameters can be strengthened later: a successful
  login checks `needs_rehash` and upgrades the stored hash.

Tokens
  Short-lived signed JWTs carrying only the user id (`sub`) and issue/expiry
  times. No email, no health data. The accepted algorithm is pinned on
  decode, so a token claiming `alg: none` (or a different algorithm) is
  rejected rather than trusted.
"""

import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Small allowance for clock differences between servers when checking exp/iat.
_LEEWAY_SECONDS = 10


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """True only if the password matches. Malformed hashes count as a mismatch."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        # VerifyMismatchError is a subclass of VerificationError.
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if the hash was made with weaker parameters than the current defaults."""
    return _hasher.check_needs_rehash(password_hash)


@lru_cache
def dummy_hash() -> str:
    """
    A valid hash of a throwaway password. Login verifies against it when the
    email is unknown, so "no such account" costs the same time as "wrong
    password" and response timing doesn't reveal which emails are registered.
    """
    return _hasher.hash("timing-equalisation-only")


# --------------------------------------------------------------------------- #
# Access tokens
# --------------------------------------------------------------------------- #
class InvalidToken(Exception):
    """The token is missing required claims, malformed, expired, or wrongly signed."""


def create_access_token(
    user_id: uuid.UUID, *, secret: str, algorithm: str, expires_minutes: int
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, *, secret: str, algorithm: str) -> uuid.UUID:
    """Return the user id in a valid token, or raise InvalidToken (never anything else)."""
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],  # pinned: never trust the token's own alg header
            options={"require": ["exp", "sub"]},
            leeway=_LEEWAY_SECONDS,
        )
        subject = payload["sub"]
        if not isinstance(subject, str):
            raise InvalidToken
        return uuid.UUID(subject)
    except (jwt.PyJWTError, ValueError, KeyError):
        raise InvalidToken from None
