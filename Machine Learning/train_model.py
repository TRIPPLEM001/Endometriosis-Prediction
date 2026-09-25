"""
train_model.py

Trains and compares candidate classifiers separately for each tier of
the pipeline:

  Tier 1: home-only symptoms/demographics -> instant risk flag.
  Tier 2: Tier 1 + CA-125/CRP (from a mail-in kit) -> refined risk.

For each tier, runs stratified cross-validation on ROC-AUC across a
few candidate models, fits the best one on the full training set, and
saves it separately so predict.py can route between them.

Usage:
    python src/train_model.py
"""

import os
import joblib
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

# ---- Config ----
PROCESSED_DIR = "data/processed"
MODEL_DIR = "models"
RANDOM_STATE = 42
N_FOLDS = 5

TIERS = ["tier1", "tier2"]


def make_candidate_models():
    """Fresh, unfitted model instances - called per tier so no state leaks between tiers."""
    return {
        "LogisticRegression": LogisticRegression(
            max_iter=1000, random_state=RANDOM_STATE
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=300, max_depth=6, random_state=RANDOM_STATE
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05, random_state=RANDOM_STATE
        ),
    }


def load_processed_data(tier_name: str):
    tier_dir = f"{PROCESSED_DIR}/{tier_name}"
    X_train = pd.read_csv(f"{tier_dir}/X_train.csv")
    y_train = pd.read_csv(f"{tier_dir}/y_train.csv").squeeze("columns")
    return X_train, y_train


def compare_models(X_train, y_train, candidates):
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    results = {}

    for name, model in candidates.items():
        scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="roc_auc")
        results[name] = scores
        print(f"    {name:<20} AUC = {scores.mean():.4f} (+/- {scores.std():.4f})")

    best_name = max(results, key=lambda k: results[k].mean())
    return best_name


def save_model(model, model_name, feature_names, tier_name):
    os.makedirs(MODEL_DIR, exist_ok=True)
    bundle = {
        "model": model,
        "model_name": model_name,
        "feature_names": feature_names,
        "tier": tier_name,
    }
    path = f"{MODEL_DIR}/{tier_name}_model.pkl"
    joblib.dump(bundle, path)
    print(f"  Saved best model ({model_name}) to '{path}'")


def train_tier(tier_name: str):
    print(f"\n=== {tier_name.upper()} ===")
    X_train, y_train = load_processed_data(tier_name)
    print(f"  Loaded {X_train.shape[0]} rows, {X_train.shape[1]} features")

    candidates = make_candidate_models()
    print(f"  {N_FOLDS}-fold cross-validation (ROC-AUC):")
    best_name = compare_models(X_train, y_train, candidates)
    print(f"  Best model: {best_name}")

    best_model = candidates[best_name]
    best_model.fit(X_train, y_train)
    save_model(best_model, best_name, X_train.columns.tolist(), tier_name)


def main():
    for tier_name in TIERS:
        train_tier(tier_name)


if __name__ == "__main__":
    main()
