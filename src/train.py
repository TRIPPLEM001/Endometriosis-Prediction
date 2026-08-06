import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from sklearn.svm import SVC

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

# -----------------------------------
# Load Dataset
# -----------------------------------

df = pd.read_csv("../data/processed/processed_endometriosis.csv")

# -----------------------------------
# Features and Target
# -----------------------------------

X = df.drop("Endometriosis_Stage", axis=1)
y = df["Endometriosis_Stage"]

# -----------------------------------
# Train/Test Split
# -----------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

print("Training Samples:", len(X_train))
print("Testing Samples:", len(X_test))

# -----------------------------------
# Models
# -----------------------------------

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Decision Tree": DecisionTreeClassifier(random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
    "Support Vector Machine": SVC(probability=True, random_state=42),
}

results = []

best_model = None
best_accuracy = 0

# -----------------------------------
# Train Models
# -----------------------------------

for name, model in models.items():
    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions)
    recall = recall_score(y_test, predictions)
    f1 = f1_score(y_test, predictions)

    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 Score : {f1:.4f}")

    print("\nConfusion Matrix")
    print(confusion_matrix(y_test, predictions))

    print("\nClassification Report")
    print(classification_report(y_test, predictions))

    results.append([name, accuracy, precision, recall, f1])

    if accuracy > best_accuracy:
        best_accuracy = accuracy
        best_model = model

# -----------------------------------
# Results Table
# -----------------------------------

results_df = pd.DataFrame(
    results, columns=["Model", "Accuracy", "Precision", "Recall", "F1 Score"]
)

print("\n")
print(results_df)

# -----------------------------------
# Save Results
# -----------------------------------

os.makedirs("../results", exist_ok=True)

results_df.to_csv("../results/model_results.csv", index=False)

# -----------------------------------
# Save Best Model
# -----------------------------------

os.makedirs("../models", exist_ok=True)

joblib.dump(best_model, "../models/endometriosis_model.pkl")

print("\nBest model saved successfully.")
