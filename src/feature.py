import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier

# Load dataset
df = pd.read_csv("../data/processed/processed_endometriosis.csv")

X = df.drop("Endometriosis_Stage", axis=1)
y = df["Endometriosis_Stage"]

# Train Random Forest
model = RandomForestClassifier(random_state=42)
model.fit(X, y)

# Feature importance
importance = pd.DataFrame(
    {"Feature": X.columns, "Importance": model.feature_importances_}
)

importance = importance.sort_values(by="Importance", ascending=False)

print(importance)

plt.figure(figsize=(8, 5))
plt.barh(importance["Feature"], importance["Importance"])
plt.xlabel("Importance")
plt.title("Feature Importance")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()
