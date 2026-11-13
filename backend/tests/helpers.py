"""
Shared test data and helpers for the screening and account tests.
"""

# API form: yes/no fields are booleans.
HIGH = {
    "Age": 29, "BMI": 24.5, "Cycle_Length": 26, "Age_of_Menarche": 12,
    "Dysmenorrhea_Score": 8, "Pelvic_Pain_Score": 7, "Dyspareunia_Score": 6,
    "Dyschezia_Score": 6, "Urinary_Symptoms_Score": 5, "Family_History": True,
    "Infertility_Status": True, "Mental_Health_Score": 4,
}
LOW = {
    "Age": 33, "BMI": 22.0, "Cycle_Length": 28, "Age_of_Menarche": 13,
    "Dysmenorrhea_Score": 1, "Pelvic_Pain_Score": 1, "Dyspareunia_Score": 0,
    "Dyschezia_Score": 0, "Urinary_Symptoms_Score": 1, "Family_History": False,
    "Infertility_Status": False, "Mental_Health_Score": 7,
}
LABS_ELEVATED = {"CA_125_Level": 165.0, "CRP_Level": 16.5}  # Tier 2 says elevated
LABS_REASSURING = {"CA_125_Level": 20.0, "CRP_Level": 1.0}  # Tier 2 says not elevated


def create(client, headers, payload=HIGH):
    return client.post("/screenings", json=payload, headers=headers)


def add_labs(client, headers, screening_id, labs=LABS_ELEVATED):
    return client.post(f"/screenings/{screening_id}/labs", json=labs, headers=headers)
