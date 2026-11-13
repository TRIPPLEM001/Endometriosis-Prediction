"""
prediction.py

The two-tier screening logic, with no printing, no file writing and no
web or database code, so it can be tested on its own:

  1. Score Tier 1 (home symptoms). If the probability reaches the
     Tier 1 threshold, the screening is flagged as elevated.
  2. If flagged AND both lab values (CA-125, CRP) are supplied, score
     Tier 2 for a refined estimate. Labs on an unflagged screening are
     ignored, because Tier 2 only exists to refine an elevated result.
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

from app.services.model_registry import ModelRegistry, TierBundle


class Recommendation(str, Enum):
    LOW_RISK = "low_risk"
    ELEVATED_NEEDS_LABS = "elevated_needs_labs"
    ELEVATED_CONFIRMED = "elevated_confirmed"
    ELEVATED_NOT_CONFIRMED = "elevated_not_confirmed"


@dataclass(frozen=True)
class Factor:
    """One input's influence on a score. `contribution` is signed for linear
    models; tree models only provide unsigned importance (direction 'influential')."""
    feature: str
    contribution: float
    direction: str  # "increases" | "decreases" | "influential"


@dataclass(frozen=True)
class TierScore:
    probability: float
    factors: tuple[Factor, ...]


@dataclass(frozen=True)
class ScreeningOutcome:
    tier1: TierScore
    tier1_flagged: bool
    tier2: TierScore | None
    tier2_flagged: bool | None
    recommendation: Recommendation


def _top_factors(model, feature_names: tuple[str, ...], scaled_row: np.ndarray, top_n: int) -> tuple[Factor, ...]:
    if hasattr(model, "coef_"):
        contributions = model.coef_[0] * scaled_row
        signed = True
    elif hasattr(model, "feature_importances_"):
        contributions = np.asarray(model.feature_importances_)
        signed = False
    else:
        return ()

    order = np.argsort(-np.abs(contributions))[:top_n]
    factors = []
    for i in order:
        c = float(contributions[i])
        direction = ("increases" if c > 0 else "decreases") if signed else "influential"
        factors.append(Factor(feature=feature_names[i], contribution=c, direction=direction))
    return tuple(factors)


def score_tier(bundle: TierBundle, patient: dict, top_n: int = 3) -> TierScore:
    """Score one patient against one tier. Raises ValueError on missing inputs."""
    missing = [f for f in bundle.feature_names if patient.get(f) is None]
    if missing:
        raise ValueError(f"Missing required fields for {bundle.tier}: {missing}")

    row = pd.DataFrame([{f: patient[f] for f in bundle.feature_names}])
    scaled = pd.DataFrame(bundle.scaler.transform(row), columns=list(bundle.feature_names))
    probability = float(bundle.model.predict_proba(scaled)[0, 1])
    factors = _top_factors(bundle.model, bundle.feature_names, scaled.to_numpy()[0], top_n)
    return TierScore(probability=probability, factors=factors)


def run_screening(
    registry: ModelRegistry,
    patient: dict,
    tier1_threshold: float = 0.5,
    tier2_threshold: float = 0.5,
) -> ScreeningOutcome:
    """Run the full two-tier pipeline for one patient."""
    lab_values = [patient.get(f) for f in registry.lab_fields]
    provided = [v is not None for v in lab_values]
    if any(provided) and not all(provided):
        raise ValueError(f"Provide all of {list(registry.lab_fields)} or none of them")
    have_labs = all(provided)

    tier1 = score_tier(registry.tier1, patient)
    flagged = tier1.probability >= tier1_threshold

    if not flagged:
        return ScreeningOutcome(tier1, False, None, None, Recommendation.LOW_RISK)

    if not have_labs:
        return ScreeningOutcome(tier1, True, None, None, Recommendation.ELEVATED_NEEDS_LABS)

    tier2 = score_tier(registry.tier2, patient)
    tier2_flagged = tier2.probability >= tier2_threshold
    recommendation = (
        Recommendation.ELEVATED_CONFIRMED if tier2_flagged else Recommendation.ELEVATED_NOT_CONFIRMED
    )
    return ScreeningOutcome(tier1, True, tier2, tier2_flagged, recommendation)
