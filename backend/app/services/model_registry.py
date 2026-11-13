"""
model_registry.py

Loads the trained Tier 1 and Tier 2 models (and their fitted scalers)
from disk once, at application startup, and checks they are consistent
with each other. Everything downstream receives the immutable registry
instead of touching the filesystem.

Only load artifacts you produced yourself: joblib/pickle files can run
arbitrary code when loaded.
"""

from dataclasses import dataclass
from pathlib import Path

import joblib


class ModelLoadError(RuntimeError):
    """Raised when model artifacts are missing or inconsistent."""


@dataclass(frozen=True)
class TierBundle:
    tier: str
    model: object
    scaler: object
    feature_names: tuple[str, ...]
    model_name: str


@dataclass(frozen=True)
class ModelRegistry:
    tier1: TierBundle
    tier2: TierBundle

    @property
    def lab_fields(self) -> tuple[str, ...]:
        """Fields only Tier 2 uses (CA-125, CRP), derived rather than hardcoded."""
        return tuple(f for f in self.tier2.feature_names if f not in self.tier1.feature_names)


def _load_tier(artifacts_dir: Path, tier: str) -> TierBundle:
    model_path = artifacts_dir / f"{tier}_model.pkl"
    scaler_path = artifacts_dir / tier / "scaler.pkl"

    for path in (model_path, scaler_path):
        if not path.exists():
            raise ModelLoadError(f"Missing model artifact: {path}")

    bundle = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    feature_names = tuple(bundle["feature_names"])
    if bundle.get("tier") != tier:
        raise ModelLoadError(f"{model_path.name} is labelled tier {bundle.get('tier')!r}, expected {tier!r}")
    if getattr(scaler, "n_features_in_", None) != len(feature_names):
        raise ModelLoadError(f"{tier}: scaler and model disagree on the number of features")

    return TierBundle(
        tier=tier,
        model=bundle["model"],
        scaler=scaler,
        feature_names=feature_names,
        model_name=bundle["model_name"],
    )


def load_registry(artifacts_dir: Path) -> ModelRegistry:
    artifacts_dir = Path(artifacts_dir)
    tier1 = _load_tier(artifacts_dir, "tier1")
    tier2 = _load_tier(artifacts_dir, "tier2")

    missing = [f for f in tier1.feature_names if f not in tier2.feature_names]
    if missing:
        raise ModelLoadError(f"Tier 2 is missing Tier 1 features: {missing}")

    return ModelRegistry(tier1=tier1, tier2=tier2)
