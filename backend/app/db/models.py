"""
models.py

Two tables:

  users      - account, password hash, and the consent the person gave.
  screenings - one row per screening: the answers, the scores, the
               explanation, and which model version produced them.

Design notes
  * Answers are stored as JSON rather than one column per symptom, so
    retraining with different features doesn't require a migration for
    every change. `model_version` says which feature set a row belongs to.
  * The database itself enforces basic sanity (probabilities in [0, 1],
    a known recommendation code, Tier 2 fields set together), so a bug in
    application code can't quietly store nonsense.
  * Types are portable: Postgres in production, SQLite in tests.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# JSONB on Postgres, plain JSON elsewhere. none_as_null stores Python None as a
# real SQL NULL (not the JSON value `null`), so `lab_inputs IS NULL` means what it says.
JSONType = JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql")

# Must match app.services.prediction.Recommendation (a test keeps them in sync).
RECOMMENDATION_CODES = (
    "low_risk",
    "elevated_needs_labs",
    "elevated_confirmed",
    "elevated_not_confirmed",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)  # stored lowercased
    password_hash: Mapped[str] = mapped_column(String(255))
    consent_version: Mapped[str] = mapped_column(String(32))
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    screenings: Mapped[list["Screening"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Screening(Base):
    __tablename__ = "screenings"
    __table_args__ = (
        CheckConstraint(
            "tier1_probability >= 0 AND tier1_probability <= 1",
            name="tier1_probability_range",
        ),
        CheckConstraint(
            "tier2_probability IS NULL OR (tier2_probability >= 0 AND tier2_probability <= 1)",
            name="tier2_probability_range",
        ),
        CheckConstraint(
            "(tier2_probability IS NULL) = (tier2_flagged IS NULL)",
            name="tier2_consistent",
        ),
        CheckConstraint(
            "recommendation IN ("
            + ", ".join(f"'{code}'" for code in RECOMMENDATION_CODES)
            + ")",
            name="recommendation_valid",
        ),
        # History listing: one user's screenings, newest first.
        Index("ix_screenings_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # What the person submitted
    inputs: Mapped[dict] = mapped_column(JSONType)  # Tier 1 answers
    lab_inputs: Mapped[dict | None] = mapped_column(JSONType, nullable=True)  # CA-125 / CRP, added later

    # What the models said
    tier1_probability: Mapped[float] = mapped_column(Float)
    tier1_flagged: Mapped[bool] = mapped_column(Boolean)
    tier2_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    tier2_flagged: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    recommendation: Mapped[str] = mapped_column(String(32))

    # How it was explained
    factors: Mapped[dict] = mapped_column(JSONType)  # {"tier1": [...], "tier2": [...]}
    report_text: Mapped[str] = mapped_column(Text)

    # Provenance. Tier 2 can be added days later, after a retrain, so it gets its own version.
    model_version: Mapped[str] = mapped_column(String(32))
    tier2_model_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Whether the report was worded as validated (False = prototype wording) when generated.
    model_validated: Mapped[bool] = mapped_column(Boolean)

    user: Mapped[User] = relationship(back_populates="screenings")
