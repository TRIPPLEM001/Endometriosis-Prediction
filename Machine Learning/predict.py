"""
predict.py

Runs the two-tier prediction pipeline on a new patient:

  1. Tier 1 (instant, free): predict risk from home-only symptoms.
     If risk probability >= TIER1_THRESHOLD, flag as elevated risk
     and recommend a mail-in CA-125/CRP finger-prick kit.
  2. Tier 2 (few-day turnaround): if CA-125/CRP values are supplied
     (e.g. once the mail-in kit results arrive), predict again with
     the refined model for a refined estimate.

Usage:
    python src/predict.py                  # interactive prompt
    python src/predict.py --demo            # run on a built-in example
"""

import sys
import argparse
import joblib
import numpy as np
import pandas as pd

from prediction_explanation import explain_pipeline

MODEL_DIR = "models"
TIER1_THRESHOLD = 0.5  # standard cutoff

TIER1_FIELDS = [
    "Age", "BMI", "Cycle_Length", "Age_of_Menarche",
    "Dysmenorrhea_Score", "Pelvic_Pain_Score", "Dyspareunia_Score",
    "Dyschezia_Score", "Urinary_Symptoms_Score", "Family_History",
    "Infertility_Status", "Mental_Health_Score",
]
TIER2_EXTRA_FIELDS = ["CA_125_Level", "CRP_Level"]


def load_tier_bundle(tier_name: str):
    """Load {model, scaler, feature_names} for a tier."""
    model_bundle = joblib.load(f"{MODEL_DIR}/{tier_name}_model.pkl")
    scaler = joblib.load(f"data/processed/{tier_name}/scaler.pkl")
    return model_bundle["model"], scaler, model_bundle["feature_names"]


def predict_with_tier(model, scaler, feature_names, patient: dict):
    """Score a patient dict against a fitted tier model. Returns probability."""
    row = pd.DataFrame([{f: patient[f] for f in feature_names}])
    row_scaled = pd.DataFrame(scaler.transform(row), columns=feature_names)
    proba = model.predict_proba(row_scaled)[0, 1]
    return proba


def run_pipeline(patient: dict, verbose: bool = True):
    """
    Full two-tier pipeline for one patient.

    patient: dict containing at least all TIER1_FIELDS. May also
             contain TIER2_EXTRA_FIELDS if lab results are available.

    Returns a dict summarizing the outcome.
    """
    model1, scaler1, features1 = load_tier_bundle("tier1")
    proba1 = predict_with_tier(model1, scaler1, features1, patient)
    flagged = proba1 >= TIER1_THRESHOLD

    if verbose:
        print(f"\n[Tier 1] Home-symptom risk score: {proba1:.3f} "
              f"({'ELEVATED' if flagged else 'low'} risk, threshold={TIER1_THRESHOLD})")

    result = {
        "tier1_probability": proba1,
        "tier1_flagged": flagged,
        "tier2_probability": None,
        "recommendation": None,
        "explanation": None,
    }

    if not flagged:
        result["recommendation"] = (
            "Low home-symptom risk. No lab follow-up recommended at this time."
        )
        result["explanation"] = explain_pipeline(result, TIER1_THRESHOLD)
        if verbose:
            print(f"  -> {result['recommendation']}")
            print("\n" + result["explanation"])
        return result

    have_labs = all(f in patient and patient[f] is not None for f in TIER2_EXTRA_FIELDS)

    if not have_labs:
        result["recommendation"] = (
            "Elevated home-symptom risk. Recommend a mail-in CA-125/CRP "
            "finger-prick kit to refine this estimate before seeing a doctor."
        )
        result["explanation"] = explain_pipeline(result, TIER1_THRESHOLD)
        if verbose:
            print(f"  -> {result['recommendation']}")
            print("\n" + result["explanation"])
        return result

    model2, scaler2, features2 = load_tier_bundle("tier2")
    proba2 = predict_with_tier(model2, scaler2, features2, patient)
    result["tier2_probability"] = proba2
    result["recommendation"] = (
        "Tier 2 model indicates elevated predicted risk. Recommend seeing a doctor for clinical evaluation."
        if proba2 >= 0.5 else
        "Tier 2 model indicates lower predicted risk. Monitor symptoms and "
        "see a doctor if they persist or worsen."
    )

    result["explanation"] = explain_pipeline(result, TIER1_THRESHOLD)

    if verbose:
        print(f"[Tier 2] Refined risk score: {proba2:.3f}")
        print(f"  -> {result['recommendation']}")
        print("\n" + result["explanation"])

    return result


def prompt_float(label: str) -> float:
    while True:
        try:
            return float(input(f"  {label}: ").strip())
        except ValueError:
            print("  Please enter a number.")


def prompt_int01(label: str) -> int:
    while True:
        val = input(f"  {label} (0 = no, 1 = yes): ").strip()
        if val in ("0", "1"):
            return int(val)
        print("  Please enter 0 or 1.")


def interactive_patient() -> dict:
    print("Enter Tier 1 (home) symptom info:")
    patient = {
        "Age": prompt_float("Age"),
        "BMI": prompt_float("BMI"),
        "Cycle_Length": prompt_float("Cycle length (days)"),
        "Age_of_Menarche": prompt_float("Age at first period"),
        "Dysmenorrhea_Score": prompt_float("Dysmenorrhea (period pain) score, 0-10"),
        "Pelvic_Pain_Score": prompt_float("Pelvic pain score, 0-10"),
        "Dyspareunia_Score": prompt_float("Dyspareunia (pain during sex) score, 0-10"),
        "Dyschezia_Score": prompt_float("Dyschezia (painful bowel movements) score, 0-10"),
        "Urinary_Symptoms_Score": prompt_float("Urinary symptoms score, 0-10"),
        "Family_History": prompt_int01("Family history of endometriosis"),
        "Infertility_Status": prompt_int01("Current infertility"),
        "Mental_Health_Score": prompt_float("Mental health score, 0-10"),
    }

    proba_preview_ready = True
    print("\n(Optional) If you already have CA-125/CRP lab results, enter them now.")
    print("Otherwise press Enter to skip - you'll be told if a mail-in kit is recommended.")
    ca125_raw = input("  CA-125 level (or press Enter to skip): ").strip()
    crp_raw = input("  CRP level (or press Enter to skip): ").strip()
    patient["CA_125_Level"] = float(ca125_raw) if ca125_raw else None
    patient["CRP_Level"] = float(crp_raw) if crp_raw else None

    return patient


DEMO_PATIENT_NO_LABS = {
    "Age": 29, "BMI": 24.5, "Cycle_Length": 26, "Age_of_Menarche": 12,
    "Dysmenorrhea_Score": 8, "Pelvic_Pain_Score": 7, "Dyspareunia_Score": 6,
    "Dyschezia_Score": 6, "Urinary_Symptoms_Score": 5, "Family_History": 1,
    "Infertility_Status": 1, "Mental_Health_Score": 4,
    "CA_125_Level": None, "CRP_Level": None,
}


def main():
    parser = argparse.ArgumentParser(description="Two-tier endometriosis risk prediction")
    parser.add_argument("--demo", action="store_true", help="Run on a built-in example patient")
    args = parser.parse_args()

    if args.demo:
        print("Running on demo patient (no lab values supplied)...")
        run_pipeline(DEMO_PATIENT_NO_LABS)
    else:
        patient = interactive_patient()
        run_pipeline(patient)


if __name__ == "__main__":
    main()
