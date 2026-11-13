"""
users.py

All database access for accounts. Write functions commit before returning,
so callers never have to remember to.
"""

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Screening, User, utcnow


class EmailAlreadyRegistered(Exception):
    """Raised when registering an email that already has an account."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def create_user(
    db: Session,
    *,
    email: str,
    password_hash: str,
    consent_version: str,
    consented_at: datetime | None = None,
) -> User:
    normalized = normalize_email(email)
    user = User(
        email=normalized,
        password_hash=password_hash,
        consent_version=consent_version,
        consented_at=consented_at or utcnow(),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # The unique index on email also protects against two simultaneous
        # registrations slipping past a "does it exist?" check.
        db.rollback()
        raise EmailAlreadyRegistered(normalized) from None
    return user


def update_password_hash(db: Session, user: User, new_hash: str) -> None:
    """Replace a stored hash (used to upgrade to stronger parameters after a successful login)."""
    user.password_hash = new_hash
    db.commit()


def delete_user_and_data(db: Session, user_id: uuid.UUID) -> bool:
    """Permanently erase an account and every screening it owns. Returns False if no such user."""
    user = db.get(User, user_id)
    if user is None:
        return False
    # Explicit delete rather than relying on the database cascade, so erasure
    # behaves the same on every backend (SQLite ignores foreign keys by default).
    db.execute(delete(Screening).where(Screening.user_id == user_id))
    db.delete(user)
    db.commit()
    return True


def export_user_data(db: Session, user: User) -> dict:
    """Everything stored about one user, as JSON-serialisable data. Never includes the password hash."""
    screenings = db.scalars(
        select(Screening)
        .where(Screening.user_id == user.id)
        .order_by(Screening.created_at, Screening.id)
    ).all()

    return {
        "account": {
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "consent_version": user.consent_version,
            "consented_at": user.consented_at.isoformat(),
        },
        "screenings": [
            {
                "id": str(s.id),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "inputs": s.inputs,
                "lab_inputs": s.lab_inputs,
                "tier1_probability": s.tier1_probability,
                "tier1_flagged": s.tier1_flagged,
                "tier2_probability": s.tier2_probability,
                "tier2_flagged": s.tier2_flagged,
                "recommendation": s.recommendation,
                "factors": s.factors,
                "report_text": s.report_text,
                "model_version": s.model_version,
                "tier2_model_version": s.tier2_model_version,
                "model_validated": s.model_validated,
            }
            for s in screenings
        ],
    }
