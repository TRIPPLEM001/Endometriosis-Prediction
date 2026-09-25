"""
prediction_explanation.py

Human-readable explanations for the two-tier endometriosis prediction
pipeline used by predict.py.

This module explains model output without presenting it as a medical
 diagnosis. It is intentionally separate from the prediction logic so
that the wording can be updated without changing the model code.
"""


def _percent(probability: float) -> str:
    return f"{probability * 100:.1f}%"


def explain_tier1(probability: float, threshold: float = 0.5) -> str:
    """Explain the Tier 1 home-symptom prediction."""
    percentage = _percent(probability)

    if probability >= threshold:
        return (
            "TIER 1 RESULT\n"
            "Your estimated risk score is " + percentage + ".\n\n"
            "The model classified this as an ELEVATED predicted risk because "
            f"the score is at or above the {threshold:.0%} prediction threshold. "
            "This means that, based on the information entered, the model found "
            "a pattern associated with a higher predicted likelihood of "
            "endometriosis.\n\n"
            "This is a screening prediction, not a medical diagnosis. "
            "An elevated result does not mean that you have endometriosis. "
            "A qualified healthcare professional should evaluate your symptoms "
            "and decide whether further testing is appropriate."
        )

    return (
        "TIER 1 RESULT\n"
        "Your estimated risk score is " + percentage + ".\n\n"
        "The model classified this as a LOW predicted risk because the score "
        f"is below the {threshold:.0%} prediction threshold. This means that, "
        "based on the information entered, the model did not identify a pattern "
        "that reached its elevated-risk threshold.\n\n"
        "A low result does not rule out endometriosis. If you have persistent, "
        "severe, or worsening symptoms, please consult a qualified healthcare "
        "professional for appropriate evaluation."
    )


def explain_tier1_follow_up() -> str:
    """Explain why Tier 2 laboratory information may be requested."""
    return (
        "NEXT STEP\n"
        "Because the Tier 1 result is elevated, the two-tier pipeline can use "
        "the CA-125 and CRP laboratory values in Tier 2 to produce a refined "
        "model estimate. These laboratory results should be obtained and "
        "interpreted through an appropriate healthcare process.\n\n"
        "The laboratory values do not by themselves establish a diagnosis of "
        "endometriosis."
    )


def explain_tier2(probability: float, threshold: float = 0.5) -> str:
    """Explain the Tier 2 prediction using symptom + laboratory information."""
    percentage = _percent(probability)

    if probability >= threshold:
        classification = "ELEVATED predicted risk"
        detail = (
            "The Tier 2 model classified the result as elevated because the "
            f"score is at or above the {threshold:.0%} prediction threshold. "
            "The model is using the Tier 2 feature set, which includes the "
            "symptom/demographic information together with CA-125 and CRP values."
        )
        action = (
            "Consider discussing this result and your symptoms with a qualified "
            "healthcare professional for clinical evaluation and appropriate "
            "testing."
        )
    else:
        classification = "LOW predicted risk"
        detail = (
            "The Tier 2 model classified the result as low because the score is "
            f"below the {threshold:.0%} prediction threshold. The model is using "
            "the Tier 2 feature set, which includes the symptom/demographic "
            "information together with CA-125 and CRP values."
        )
        action = (
            "A low model result does not rule out endometriosis. If symptoms "
            "persist, are severe, or worsen, discuss them with a qualified "
            "healthcare professional."
        )

    return (
        "TIER 2 RESULT\n"
        "Your refined model score is " + percentage + ".\n\n"
        f"Classification: {classification}.\n\n"
        + detail
        + "\n\n"
        + action
        + "\n\n"
        "IMPORTANT: This model output is a prediction based on the project's "
        "training data. It is not a medical diagnosis and should not be used "
        "as a substitute for professional medical advice."
    )


def explain_no_labs() -> str:
    """Explain an elevated Tier 1 result when laboratory values are unavailable."""
    return (
        "LAB RESULTS NOT PROVIDED\n"
        "CA-125 and CRP values were not provided, so the Tier 2 model was not "
        "run. The result currently available is the Tier 1 home-symptom "
        "prediction only.\n\n"
        "If laboratory testing is appropriate, a qualified healthcare "
        "professional can advise you on suitable tests and how the results "
        "should be interpreted."
    )


def explain_pipeline(result: dict, threshold: float = 0.5) -> str:
    """Build one complete explanation from the dictionary returned by run_pipeline."""
    parts = [explain_tier1(result["tier1_probability"], threshold)]

    if not result["tier1_flagged"]:
        return "\n\n".join(parts)

    if result["tier2_probability"] is None:
        parts.extend([
            explain_no_labs(),
            explain_tier1_follow_up(),
        ])
    else:
        parts.append(explain_tier2(result["tier2_probability"], threshold))

    return "\n\n".join(parts)
