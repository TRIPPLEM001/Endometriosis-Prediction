"""
screening.py (service)

The two screening workflows, tying together scoring, explanation and storage:

  create_screening  Tier 1 answers -> scored, explained, stored.
  add_labs          CA-125 / CRP added to an existing screening -> Tier 2
                    scored, report regenerated, stored.

Routes stay thin: they validate the request and map the exceptions below to
HTTP status codes. Both functions take the owner's user_id and go through
the repository, so another user's screening is never reachable from here.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories import screenings as screening_repo
from app.services.explanation import build_report, factor_to_dict
from app.services.model_registry import ModelRegistry
from app.services.prediction import (
    Factor,
    Recommendation,
    ScreeningOutcome,
    TierScore,
    run_screening,
    score_tier,
)

if TYPE_CHECKING:
    from app.db.models import Screening


class LabsNotAllowed(Exception):
    """Labs can't be added to this screening. `reason` says why (shown to the user)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def create_screening(
    db: Session,
    user_id: uuid.UUID,
    answers: dict,
    registry: ModelRegistry,
    settings: Settings,
) -> "Screening":
    outcome = run_screening(
        registry,
        answers,
        tier1_threshold=settings.tier1_threshold,
        tier2_threshold=settings.tier2_threshold,
    )
    report = build_report(
        answers,
        outcome,
        registry,
        model_validated=settings.model_validated,
        model_version=settings.model_version,
    )
    return screening_repo.create_screening(
        db,
        user_id,
        inputs=answers,
        lab_inputs=None,
        tier1_probability=outcome.tier1.probability,
        tier1_flagged=outcome.tier1_flagged,
        tier2_probability=None,
        tier2_flagged=None,
        recommendation=outcome.recommendation.value,
        factors={"tier1": [factor_to_dict(f) for f in outcome.tier1.factors], "tier2": []},
        report_text=report,
        model_version=settings.model_version,
        tier2_model_version=None,
        model_validated=settings.model_validated,
    )


def add_labs(
    db: Session,
    user_id: uuid.UUID,
    screening_id: uuid.UUID,
    labs: dict,
    registry: ModelRegistry,
    settings: Settings,
) -> "Screening | None":
    """Returns the updated screening, None if it doesn't exist (or isn't the user's),
    or raises LabsNotAllowed."""
    screening = screening_repo.get_screening(db, user_id, screening_id)
    if screening is None:
        return None
    if not screening.tier1_flagged:
        raise LabsNotAllowed(
            "Lab results can only be added to a screening that showed elevated risk."
        )
    if screening.lab_inputs is not None:
        raise LabsNotAllowed("Lab results have already been added to this screening.")

    patient = {**screening.inputs, **labs}
    try:
        tier2 = score_tier(registry.tier2, patient)
    except ValueError:
        # The stored answers lack a field the current model needs (the models
        # were retrained with different features since this screening was made).
        raise LabsNotAllowed(
            "This screening was made with an earlier version of the models and can't "
            "be extended. Please run a new screening."
        ) from None

    tier2_flagged = tier2.probability >= settings.tier2_threshold
    recommendation = (
        Recommendation.ELEVATED_CONFIRMED if tier2_flagged else Recommendation.ELEVATED_NOT_CONFIRMED
    )

    # Tier 1 is NOT re-run: the stored result stays exactly what the person was
    # shown, even if the models have been retrained since. (Contribution values
    # aren't stored, and the report only uses each factor's feature and direction.)
    stored_tier1 = TierScore(
        probability=screening.tier1_probability,
        factors=tuple(
            Factor(feature=f["feature"], contribution=0.0, direction=f["direction"])
            for f in screening.factors.get("tier1", [])
        ),
    )
    outcome = ScreeningOutcome(
        tier1=stored_tier1,
        tier1_flagged=True,
        tier2=tier2,
        tier2_flagged=tier2_flagged,
        recommendation=recommendation,
    )

    if screening.model_version == settings.model_version:
        version_label = settings.model_version
    else:
        version_label = f"{screening.model_version} (symptoms), {settings.model_version} (labs)"

    report = build_report(
        patient,
        outcome,
        registry,
        model_validated=settings.model_validated,
        model_version=version_label,
    )
    return screening_repo.add_labs(
        db,
        user_id,
        screening_id,
        lab_inputs=labs,
        tier2_probability=tier2.probability,
        tier2_flagged=tier2_flagged,
        recommendation=recommendation.value,
        factors={
            "tier1": screening.factors.get("tier1", []),
            "tier2": [factor_to_dict(f) for f in tier2.factors],
        },
        report_text=report,
        tier2_model_version=settings.model_version,
        model_validated=settings.model_validated,
    )
