"""
Tests for the service layer (no web or database involved).

Run with pytest from the backend/ folder:  pytest tests/test_services.py
"""

import copy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.explanation import build_report, format_probability, recommendation_message
from app.services.model_registry import ModelLoadError, load_registry
from app.services.prediction import Recommendation, run_screening

ARTIFACTS = Path(__file__).resolve().parents[1] / "ml_artifacts"

HIGH_SYMPTOMS = {
    "Age": 29, "BMI": 24.5, "Cycle_Length": 26, "Age_of_Menarche": 12,
    "Dysmenorrhea_Score": 8, "Pelvic_Pain_Score": 7, "Dyspareunia_Score": 6,
    "Dyschezia_Score": 6, "Urinary_Symptoms_Score": 5, "Family_History": 1,
    "Infertility_Status": 1, "Mental_Health_Score": 4,
}
LOW_SYMPTOMS = {
    "Age": 33, "BMI": 22.0, "Cycle_Length": 28, "Age_of_Menarche": 13,
    "Dysmenorrhea_Score": 1, "Pelvic_Pain_Score": 1, "Dyspareunia_Score": 0,
    "Dyschezia_Score": 0, "Urinary_Symptoms_Score": 1, "Family_History": 0,
    "Infertility_Status": 0, "Mental_Health_Score": 7,
}
LABS = {"CA_125_Level": 165.0, "CRP_Level": 16.5}
FIXED_TIME = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def registry():
    return load_registry(ARTIFACTS)


def test_registry_loads_and_derives_lab_fields(registry):
    assert len(registry.tier1.feature_names) == 12
    assert len(registry.tier2.feature_names) == 14
    assert set(registry.lab_fields) == {"CA_125_Level", "CRP_Level"}


def test_registry_rejects_missing_artifacts(tmp_path):
    with pytest.raises(ModelLoadError):
        load_registry(tmp_path)


def test_parity_with_original_pipeline(registry):
    """Scores must match what the original predict.py produced for the same patients."""
    high = run_screening(registry, HIGH_SYMPTOMS)
    assert high.tier1.probability == pytest.approx(0.879, abs=0.001)

    low = run_screening(registry, LOW_SYMPTOMS)
    assert low.tier1.probability == pytest.approx(0.067, abs=0.001)

    refined = run_screening(registry, {**HIGH_SYMPTOMS, **LABS})
    assert refined.tier2.probability == pytest.approx(1.0, abs=0.001)


def test_low_risk_stops_at_tier1(registry):
    outcome = run_screening(registry, LOW_SYMPTOMS)
    assert not outcome.tier1_flagged
    assert outcome.tier2 is None
    assert outcome.recommendation is Recommendation.LOW_RISK


def test_labs_are_ignored_when_tier1_does_not_flag(registry):
    outcome = run_screening(registry, {**LOW_SYMPTOMS, **LABS})
    assert outcome.tier2 is None
    assert outcome.recommendation is Recommendation.LOW_RISK


def test_elevated_without_labs_recommends_kit(registry):
    outcome = run_screening(registry, HIGH_SYMPTOMS)
    assert outcome.tier1_flagged
    assert outcome.tier2 is None
    assert outcome.recommendation is Recommendation.ELEVATED_NEEDS_LABS


def test_elevated_with_labs_runs_tier2(registry):
    outcome = run_screening(registry, {**HIGH_SYMPTOMS, **LABS})
    assert outcome.tier2 is not None
    assert outcome.recommendation is Recommendation.ELEVATED_CONFIRMED


def test_low_labs_do_not_confirm(registry):
    outcome = run_screening(registry, {**HIGH_SYMPTOMS, "CA_125_Level": 12.0, "CRP_Level": 0.5})
    assert outcome.tier2 is not None
    assert outcome.recommendation is Recommendation.ELEVATED_NOT_CONFIRMED


def test_only_one_lab_value_is_rejected(registry):
    with pytest.raises(ValueError, match="all of"):
        run_screening(registry, {**HIGH_SYMPTOMS, "CA_125_Level": 165.0})


def test_missing_symptom_field_is_rejected(registry):
    incomplete = copy.deepcopy(HIGH_SYMPTOMS)
    del incomplete["Age"]
    with pytest.raises(ValueError, match="Age"):
        run_screening(registry, incomplete)


def test_factors_are_returned_with_direction(registry):
    outcome = run_screening(registry, HIGH_SYMPTOMS)
    assert len(outcome.tier1.factors) == 3
    assert all(f.direction in {"increases", "decreases"} for f in outcome.tier1.factors)


def test_format_probability_never_implies_certainty():
    assert format_probability(1.0) == ">99%"
    assert format_probability(0.995) == ">99%"
    assert format_probability(0.0) == "<1%"
    assert format_probability(0.879) == "88%"


def test_prototype_mode_never_says_confirmed():
    text = recommendation_message(Recommendation.ELEVATED_CONFIRMED, model_validated=False)
    assert "confirm" not in text.lower()
    assert "prototype" in text.lower()


def test_report_prototype_vs_validated(registry):
    patient = {**HIGH_SYMPTOMS, **LABS}
    outcome = run_screening(registry, patient)
    kwargs = dict(model_version="test", generated_at=FIXED_TIME)

    proto = build_report(patient, outcome, registry, model_validated=False, **kwargs)
    assert "prototype" in proto.lower()
    assert "Family history of endometriosis: Yes" in proto
    assert ">99%" in proto and "100%" not in proto

    validated = build_report(patient, outcome, registry, model_validated=True, **kwargs)
    assert "This service is a prototype" not in validated
    assert "Generated: 2026-10-09 12:00 UTC" in validated
