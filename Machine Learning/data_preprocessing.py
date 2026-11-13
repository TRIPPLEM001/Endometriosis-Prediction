"""
data_preprocessing.py

Builds two processed datasets from the raw endometriosis data, for a
two-tier prediction pipeline:

  Tier 1 (instant, free, home-only):
      Symptom scores + demographics + family history. No lab test
      required. Used for an immediate risk flag.

  Tier 2 (few-day turnaround, mail-in finger-prick kit):
      Everything in Tier 1, plus CA-125 and CRP levels. Used to refine
      the risk estimate once lab values are available. Only reached
      if Tier 1 flags elevated risk.

Usage:
    python src/data_preprocessing.py
"""

import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

# ---- Config ----
RAW_DATA_PATH = "data/endometriosis_data.csv"
OUTPUT_DIR = "data/processed"
TARGET_COL = "Endometriosis_Stage"

# Tier 1 excludes only the lab markers - everything else (including
# BMI, which is free/instant to measure at home) stays in.
TIER1_DROP_COLS = ["CA_125_Level", "CRP_Level"]

# Tier 2 keeps everything - no columns dropped.
TIER2_DROP_COLS = []

TEST_SIZE = 0.2
RANDOM_STATE = 42


def load_data(path: str = RAW_DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"Loaded {df.shape[0]} rows, {df.shape[1]} columns from {path}")
    return df


def clean_data(df: pd.DataFrame, drop_cols: list) -> pd.DataFrame:
    cols_present = [c for c in drop_cols if c in df.columns]
    df = df.drop(columns=cols_present)

    n_missing = df.isnull().sum().sum()
    if n_missing > 0:
        print(f"Warning: {n_missing} missing values found. Filling with column median.")
        df = df.fillna(df.median(numeric_only=True))

    return df


def split_data(df: pd.DataFrame):
    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    return X_train, X_test, y_train, y_test


def scale_features(X_train: pd.DataFrame, X_test: pd.DataFrame):
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    return X_train_scaled, X_test_scaled, scaler


def save_outputs(X_train, X_test, y_train, y_test, scaler, feature_names, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    pd.DataFrame(X_train, columns=feature_names).to_csv(f"{out_dir}/X_train.csv", index=False)
    pd.DataFrame(X_test, columns=feature_names).to_csv(f"{out_dir}/X_test.csv", index=False)
    y_train.to_csv(f"{out_dir}/y_train.csv", index=False)
    y_test.to_csv(f"{out_dir}/y_test.csv", index=False)
    joblib.dump(scaler, f"{out_dir}/scaler.pkl")

    print(f"  -> saved to '{out_dir}/' ({len(feature_names)} features: {feature_names})")


def build_tier(df_raw: pd.DataFrame, drop_cols: list, tier_name: str):
    print(f"\n--- Building {tier_name} ---")
    df = clean_data(df_raw, drop_cols)

    X_train, X_test, y_train, y_test = split_data(df)
    feature_names = X_train.columns.tolist()

    X_train_scaled, X_test_scaled, scaler = scale_features(X_train, X_test)
    out_dir = f"{OUTPUT_DIR}/{tier_name}"
    save_outputs(X_train_scaled, X_test_scaled, y_train, y_test, scaler, feature_names, out_dir)


def main():
    df_raw = load_data()

    build_tier(df_raw, TIER1_DROP_COLS, "tier1")
    build_tier(df_raw, TIER2_DROP_COLS, "tier2")


if __name__ == "__main__":
    main()
