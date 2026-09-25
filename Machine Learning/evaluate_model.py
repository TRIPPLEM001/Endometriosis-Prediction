"""
evaluate_model.py

Evaluates the Tier 1 (home-only) and Tier 2 (+ CA-125/CRP) models
separately on their respective held-out test sets. For each tier,
prints classification metrics and saves a confusion matrix, ROC
curve, and feature importance/coefficient plot.

Usage:
    python src/evaluate_model.py
"""

import os
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display needed, just save to file
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    roc_curve,
    confusion_matrix,
    classification_report,
)

# ---- Config ----
PROCESSED_DIR = "data/processed"
MODEL_DIR = "models"
REPORT_DIR = "reports"

TIERS = ["tier1", "tier2"]


def load_test_data(tier_name: str):
    tier_dir = f"{PROCESSED_DIR}/{tier_name}"
    X_test = pd.read_csv(f"{tier_dir}/X_test.csv")
    y_test = pd.read_csv(f"{tier_dir}/y_test.csv").squeeze("columns")
    return X_test, y_test


def load_model(tier_name: str):
    bundle = joblib.load(f"{MODEL_DIR}/{tier_name}_model.pkl")
    return bundle["model"], bundle["model_name"], bundle["feature_names"]


def compute_metrics(model, X_test, y_test):
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba),
    }

    print("  Test set metrics:")
    for name, value in metrics.items():
        print(f"    {name:<10} {value:.4f}")

    print("\n  Classification report:")
    report = classification_report(
        y_test, y_pred, target_names=["No Endometriosis", "Endometriosis"]
    )
    print("  " + report.replace("\n", "\n  "))

    return y_pred, y_proba, metrics


def plot_confusion_matrix(y_test, y_pred, title, out_path):
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")

    labels = ["No Endometriosis", "Endometriosis"]
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)

    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black")

    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_roc_curve(y_test, y_proba, auc, title, out_path):
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, label=f"AUC = {auc:.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Chance")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_feature_importance(model, model_name, feature_names, title, out_path):
    if hasattr(model, "coef_"):
        importance = model.coef_[0]
    elif hasattr(model, "feature_importances_"):
        importance = model.feature_importances_
    else:
        print("  Model has no coef_/feature_importances_ attribute; skipping plot.")
        return

    order = np.argsort(importance)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(np.array(feature_names)[order], importance[order])
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def evaluate_tier(tier_name: str):
    print(f"\n=== {tier_name.upper()} ===")
    out_dir = f"{REPORT_DIR}/{tier_name}"
    os.makedirs(out_dir, exist_ok=True)

    X_test, y_test = load_test_data(tier_name)
    model, model_name, feature_names = load_model(tier_name)
    print(f"  Model: {model_name} | {len(feature_names)} features")

    y_pred, y_proba, metrics = compute_metrics(model, X_test, y_test)

    plot_confusion_matrix(
        y_test, y_pred, f"{tier_name.capitalize()} Confusion Matrix",
        f"{out_dir}/confusion_matrix.png"
    )
    plot_roc_curve(
        y_test, y_proba, metrics["roc_auc"], f"{tier_name.capitalize()} ROC Curve",
        f"{out_dir}/roc_curve.png"
    )
    plot_feature_importance(
        model, model_name, feature_names, f"{tier_name.capitalize()} — {model_name} Importances",
        f"{out_dir}/feature_importance.png"
    )
    print(f"  Saved plots to '{out_dir}/'")


def main():
    for tier_name in TIERS:
        evaluate_tier(tier_name)


if __name__ == "__main__":
    main()
