import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# -------------------------------
# Load Processed Dataset
# -------------------------------
df = pd.read_csv("../data/processed/processed_endometriosis.csv")

# Create folder to save plots
os.makedirs("../results/plots", exist_ok=True)

# Plot style
plt.style.use("ggplot")
sns.set(font_scale=1.0)

# -------------------------------
# Basic Information
# -------------------------------
print("=" * 60)
print("DATASET INFORMATION")
print("=" * 60)

print("\nFirst Five Records")
print(df.head())

print("\nDataset Shape")
print(df.shape)

print("\nDataset Information")
print(df.info())

print("\nSummary Statistics")
print(df.describe())

print("\nMissing Values")
print(df.isnull().sum())

print("\nDuplicate Rows")
print(df.duplicated().sum())

print("\nClass Distribution")
print(df["Endometriosis_Stage"].value_counts())

# -------------------------------
# Class Distribution Plot
# -------------------------------
plt.figure(figsize=(6, 5))

sns.countplot(data=df, x="Endometriosis_Stage", palette="Set2")

plt.title("Distribution of Endometriosis Classes")
plt.xlabel("Class")
plt.ylabel("Number of Patients")

plt.tight_layout()
plt.savefig("../results/plots/class_distribution.png")
plt.show()

# -------------------------------
# Histograms
# -------------------------------
features = ["Age", "Cycle_Length", "Pelvic_Pain_Score", "Urinary_Symptoms_Score"]

for feature in features:
    plt.figure(figsize=(6, 4))

    sns.histplot(df[feature], bins=20, kde=True)

    plt.title(f"{feature} Distribution")
    plt.xlabel(feature)
    plt.ylabel("Frequency")

    plt.tight_layout()
    plt.savefig(f"../results/plots/{feature}_histogram.png")
    plt.show()

# -------------------------------
# Family History Distribution
# -------------------------------
plt.figure(figsize=(5, 4))

sns.countplot(data=df, x="Family_History", palette="Set1")

plt.title("Family History Distribution")
plt.xlabel("Family History")
plt.ylabel("Count")

plt.tight_layout()
plt.savefig("../results/plots/family_history.png")
plt.show()

# -------------------------------
# Correlation Heatmap
# -------------------------------
plt.figure(figsize=(8, 6))

corr = df.corr()

sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", linewidths=0.5)

plt.title("Correlation Heatmap")

plt.tight_layout()
plt.savefig("../results/plots/correlation_heatmap.png")
plt.show()

# -------------------------------
# Boxplots
# -------------------------------
numeric_features = [
    "Age",
    "Cycle_Length",
    "Pelvic_Pain_Score",
    "Urinary_Symptoms_Score",
]

for feature in numeric_features:
    plt.figure(figsize=(6, 3))

    sns.boxplot(x=df[feature], color="skyblue")

    plt.title(f"Boxplot of {feature}")

    plt.tight_layout()
    plt.savefig(f"../results/plots/{feature}_boxplot.png")
    plt.show()

# -------------------------------
# Pairplot
# -------------------------------
sns.pairplot(df, hue="Endometriosis_Stage", corner=True)

plt.savefig("../results/plots/pairplot.png")
plt.show()

# -------------------------------
# Target vs Features
# -------------------------------
selected_features = [
    "Age",
    "Cycle_Length",
    "Pelvic_Pain_Score",
    "Urinary_Symptoms_Score",
]

for feature in selected_features:
    plt.figure(figsize=(6, 4))

    sns.boxplot(data=df, x="Endometriosis_Stage", y=feature)

    plt.title(f"{feature} vs Endometriosis Prediction")

    plt.tight_layout()
    plt.savefig(f"../results/plots/{feature}_vs_target.png")
    plt.show()

print("\nEDA COMPLETED SUCCESSFULLY")
print("Plots saved in: results/plots/")
