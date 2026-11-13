"""
explanation.py

Turns a ScreeningOutcome into plain language for the user: a structured
list of top factors (for a frontend to render) and a full text report
(to read, save, or bring to a doctor).

While `model_validated` is False the wording is deliberately softer
(no "confirmed") and every report carries a prototype notice, because
the models were trained on synthetic data and have not been checked
against real patients.
"""

from datetime import datetime, timezone

from app.services.model_registry import ModelRegistry
from app.services.prediction import Factor, Recommendation, ScreeningOutcome, TierScore

DISCLAIMER = (
    "This is a screening tool, not a medical diagnosis. It estimates risk from "
    "symptoms (and lab values, if provided) using patterns learned from training "
    "data. Only a doctor can diagnose endometriosis."
)

PROTOTYPE_NOTICE = (
    "This service is a prototype. Its models were developed on synthetic data and "
    "have not yet been validated on real patients, so treat results as a prompt to "
    "talk to a doctor, not as information about your health status."
)

FRIENDLY_NAMES = {
    "Age": "Age",
    "BMI": "BMI",
    "Cycle_Length": "Menstrual cycle length (days)",
    "Age_of_Menarche": "Age at first period",
    "Dysmenorrhea_Score": "Period pain (dysmenorrhea)",
    "Pelvic_Pain_Score": "Pelvic pain",
    "Dyspareunia_Score": "Pain during sex (dyspareunia)",
    "Dyschezia_Score": "Painful bowel movements (dyschezia)",
    "Urinary_Symptoms_Score": "Urinary symptoms",
    "Family_History": "Family history of endometriosis",
    "Infertility_Status": "Current infertility",
    "Mental_Health_Score": "Mental health score",
    "CA_125_Level": "CA-125 (blood marker)",
    "CRP_Level": "CRP (blood marker for inflammation)",
}

YES_NO_FIELDS = {"Family_History", "Infertility_Status"}

_RECOMMENDATION_TEXT = {
    Recommendation.LOW_RISK: (
        "Your home-symptom screening does not point to elevated risk, so no lab "
        "follow-up is suggested right now. If your symptoms continue or get worse, "
        "see a doctor."
    ),
    Recommendation.ELEVATED_NEEDS_LABS: (
        "Your home-symptom screening points to elevated risk. A mail-in CA-125/CRP "
        "finger-prick kit can help refine this estimate before you see a doctor. "
        "You can also go straight to a doctor if you prefer."
    ),
    Recommendation.ELEVATED_NOT_CONFIRMED: (
        "The lab-refined estimate does not point to elevated risk. Keep monitoring "
        "your symptoms and see a doctor if they continue or get worse."
    ),
}

_CONFIRMED_VALIDATED = (
    "The lab-refined estimate also points to elevated risk. Please see a doctor "
    "to discuss these results."
)
_CONFIRMED_PROTOTYPE = (
    "The lab-refined estimate also points to elevated risk. Because this is a "
    "prototype and not a diagnosis, please discuss these results with a doctor."
)


def recommendation_message(code: Recommendation, model_validated: bool) -> str:
    if code is Recommendation.ELEVATED_CONFIRMED:
        return _CONFIRMED_VALIDATED if model_validated else _CONFIRMED_PROTOTYPE
    return _RECOMMENDATION_TEXT[code]


def format_probability(p: float) -> str:
    """Round for display, never implying certainty."""
    if p >= 0.99:
        return ">99%"
    if p <= 0.01:
        return "<1%"
    return f"{round(p * 100)}%"


def factor_label(feature: str) -> str:
    return FRIENDLY_NAMES.get(feature, feature)


def factor_to_dict(factor: Factor) -> dict:
    """Structured form for API responses."""
    return {
        "feature": factor.feature,
        "label": factor_label(factor.feature),
        "direction": factor.direction,
    }


def _describe_factor(factor: Factor) -> str:
    label = factor_label(factor.feature)
    if factor.direction == "influential":
        return f"  - {label} was one of the more influential factors."
    return f"  - {label} {factor.direction} the risk score."


def _format_value(feature: str, value) -> str:
    if feature in YES_NO_FIELDS:
        return "Yes" if int(value) == 1 else "No"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _answers_block(patient: dict, features) -> list[str]:
    return [
        f"  - {factor_label(f)}: {_format_value(f, patient[f])}"
        for f in features
        if patient.get(f) is not None
    ]


def _factors_block(score: TierScore) -> list[str]:
    return [_describe_factor(f) for f in score.factors]


def build_report(
    patient: dict,
    outcome: ScreeningOutcome,
    registry: ModelRegistry,
    *,
    model_validated: bool,
    model_version: str,
    generated_at: datetime | None = None,
) -> str:
    """Build the full plain-language report as text."""
    generated_at = generated_at or datetime.now(timezone.utc)
    rule = "-" * 60
    lines = [
        "=" * 60,
        "ENDOMETRIOSIS RISK SCREENING - RESULT SUMMARY",
        f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}  |  Model version: {model_version}",
        "=" * 60,
        "",
        DISCLAIMER,
    ]
    if not model_validated:
        lines += ["", PROTOTYPE_NOTICE]

    lines += ["", rule, "STEP 1: Home symptom screening", rule, "What you told us:"]
    lines += _answers_block(patient, registry.tier1.feature_names)
    lines += [
        "",
        f"Risk score: {format_probability(outcome.tier1.probability)} (from symptoms and history alone)",
        f"Result: {'ELEVATED RISK' if outcome.tier1_flagged else 'Low risk'}",
        "",
        "Factors that most influenced this score for you:",
    ]
    lines += _factors_block(outcome.tier1)

    if outcome.tier2 is not None:
        lines += ["", rule, "STEP 2: Lab-refined screening (CA-125 / CRP)", rule, "Lab values you provided:"]
        lines += _answers_block(patient, registry.lab_fields)
        lines += [
            "",
            "  Note: these values are compared with the model's training data, not with",
            "  standard clinical reference ranges. A doctor should interpret your actual lab report.",
            "",
            f"Refined risk score: {format_probability(outcome.tier2.probability)}",
            "",
            "Factors that most influenced this refined score:",
        ]
        lines += _factors_block(outcome.tier2)

    lines += [
        "",
        rule,
        "WHAT TO DO NEXT",
        rule,
        recommendation_message(outcome.recommendation, model_validated),
        "",
        "If your symptoms persist, worsen, or concern you at any point, see a doctor",
        "regardless of this result.",
        "=" * 60,
    ]
    return "\n".join(lines)
