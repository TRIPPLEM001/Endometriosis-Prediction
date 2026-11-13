"""
screenings.py

All database access for screenings.

Ownership rule: every function takes a user_id and filters by it. A
screening that exists but belongs to someone else is treated exactly like
one that doesn't exist (None / False), so the API can answer 404 for both
and never reveals which ids are real.

Write functions commit before returning.
"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Screening, utcnow

MAX_PAGE_SIZE = 100


def create_screening(
    db: Session,
    user_id: uuid.UUID,
    *,
    inputs: dict,
    lab_inputs: dict | None,
    tier1_probability: float,
    tier1_flagged: bool,
    tier2_probability: float | None,
    tier2_flagged: bool | None,
    recommendation: str,
    factors: dict,
    report_text: str,
    model_version: str,
    tier2_model_version: str | None,
    model_validated: bool,
) -> Screening:
    screening = Screening(
        user_id=user_id,
        inputs=inputs,
        lab_inputs=lab_inputs,
        tier1_probability=tier1_probability,
        tier1_flagged=tier1_flagged,
        tier2_probability=tier2_probability,
        tier2_flagged=tier2_flagged,
        recommendation=recommendation,
        factors=factors,
        report_text=report_text,
        model_version=model_version,
        tier2_model_version=tier2_model_version,
        model_validated=model_validated,
    )
    db.add(screening)
    db.commit()
    return screening


def get_screening(db: Session, user_id: uuid.UUID, screening_id: uuid.UUID) -> Screening | None:
    return db.scalar(
        select(Screening).where(Screening.id == screening_id, Screening.user_id == user_id)
    )


def list_screenings(
    db: Session, user_id: uuid.UUID, *, limit: int = 20, offset: int = 0
) -> tuple[list[Screening], int]:
    """One user's screenings, newest first, plus the total count for pagination."""
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    offset = max(0, offset)

    total = db.scalar(
        select(func.count()).select_from(Screening).where(Screening.user_id == user_id)
    )
    items = db.scalars(
        select(Screening)
        .where(Screening.user_id == user_id)
        .order_by(Screening.created_at.desc(), Screening.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), total or 0


def add_labs(
    db: Session,
    user_id: uuid.UUID,
    screening_id: uuid.UUID,
    *,
    lab_inputs: dict,
    tier2_probability: float,
    tier2_flagged: bool,
    recommendation: str,
    factors: dict,
    report_text: str,
    tier2_model_version: str,
    model_validated: bool,
) -> Screening | None:
    """Attach lab results and the Tier 2 outcome to an existing screening.

    Whether labs may be added (screening was flagged, labs not already
    present) is a business rule for the service/route layer, not enforced here.
    """
    screening = get_screening(db, user_id, screening_id)
    if screening is None:
        return None

    screening.lab_inputs = lab_inputs
    screening.tier2_probability = tier2_probability
    screening.tier2_flagged = tier2_flagged
    screening.recommendation = recommendation
    screening.factors = factors
    screening.report_text = report_text
    screening.tier2_model_version = tier2_model_version
    screening.model_validated = model_validated
    screening.updated_at = utcnow()
    db.commit()
    return screening


def delete_screening(db: Session, user_id: uuid.UUID, screening_id: uuid.UUID) -> bool:
    screening = get_screening(db, user_id, screening_id)
    if screening is None:
        return False
    db.delete(screening)
    db.commit()
    return True


def delete_all_for_user(db: Session, user_id: uuid.UUID) -> int:
    """Delete every screening a user owns (keeps the account). Returns how many were removed."""
    result = db.execute(delete(Screening).where(Screening.user_id == user_id))
    db.commit()
    return result.rowcount or 0
