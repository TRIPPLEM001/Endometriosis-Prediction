import os
import pandas as pd

# Load dataset
df = pd.read_csv("../data/raw/endometriosis_data.csv")

# Select required features
selected_columns = [
    "Age",
    "Cycle_Length",
    "Pelvic_Pain_Score",
    "Family_History",
    "Urinary_Symptoms_Score",
    "Endometriosis_Stage",
]

df = df[selected_columns]

# Display first five rows
print("\nFirst 5 Records:")
print(df.head())

# Dataset information
print("\nDataset Information:")
print(df.info())

# Check for missing values
print("\nMissing Values:")
print(df.isnull().sum())

# Check for duplicate rows
duplicates = df.duplicated().sum()
print(f"\nDuplicate Rows: {duplicates}")

# Check class distribution
print("\nTarget Variable Distribution:")
print(df["Endometriosis_Stage"].value_counts())

# Check unique target values
print("\nUnique Target Values:")
print(df["Endometriosis_Stage"].unique())

# Remove duplicate rows
df.drop_duplicates(inplace=True)

print(f"Dataset shape after removing duplicates: {df.shape}")

# Save processed dataset
os.makedirs("../data/processed", exist_ok=True)
df.to_csv("../data/processed/processed_endometriosis.csv", index=False)

print("\n Processed dataset saved successfully!")
