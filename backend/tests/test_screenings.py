"""
Tests for the screening endpoints, through the real FastAPI app with the real
trained models and an in-memory SQLite database.

Run from backend/:  pytest tests/test_screenings.py
"""

from pathlib import Path

import pytest

from app.schemas.screening import LabResults, SymptomAnswers
from app.services.model_registry import load_registry
from tests.helpers import HIGH, LABS_ELEVATED, LABS_REASSURING, LOW, add_labs, create

ARTIFACTS = Path(__file__).resolve().parents[1] / "ml_artifacts"

# --------------------------------------------------------------------------- #
# Creating a screening
# --------------------------------------------------------------------------- #
def test_high_symptoms_are_flagged_and_offer_labs(client, sign_in):
    response = create(client, sign_in())
    assert response.status_code == 201
    body = response.json()

    assert body["tier1_flagged"] is True
    assert body["tier1_probability"] == pytest.approx(0.879, abs=0.001)
    assert body["recommendation"] == "elevated_needs_labs"
    assert body["can_add_labs"] is True
    assert body["tier2_probability"] is None
    assert body["lab_inputs"] is None

    # Stored in the model's own form (yes/no as 1/0), and explained.
    assert body["inputs"]["Family_History"] == 1
    assert len(body["factors"]["tier1"]) == 3
    assert {"feature", "label", "direction"} == set(body["factors"]["tier1"][0])
    assert body["factors"]["tier2"] == []
    assert "not a medical diagnosis" in body["report_text"]
    assert body["disclaimer"]


def test_low_symptoms_stop_at_tier1(client, sign_in):
    body = create(client, sign_in(), LOW).json()
    assert body["tier1_flagged"] is False
    assert body["recommendation"] == "low_risk"
    assert body["can_add_labs"] is False


def test_results_carry_the_prototype_notice_while_models_are_unvalidated(client, sign_in):
    body = create(client, sign_in()).json()
    assert body["model_validated"] is False
    assert body["prototype_notice"]
    assert "prototype" in body["report_text"].lower()


# --------------------------------------------------------------------------- #
# Invalid input
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("field", list(HIGH))
def test_every_field_is_required(client, sign_in, field):
    headers = sign_in()
    payload = {k: v for k, v in HIGH.items() if k != field}
    assert create(client, headers, payload).status_code == 422


@pytest.mark.parametrize(
    "field, value",
    [
        ("Age", 5), ("Age", 400), ("Age", "abc"), ("Age", 29.5),
        ("BMI", 0), ("BMI", -4), ("BMI", 500), ("BMI", "NaN"),
        ("Cycle_Length", 3), ("Age_of_Menarche", 40),
        ("Dysmenorrhea_Score", -1), ("Pelvic_Pain_Score", 11),
        ("Mental_Health_Score", None),
        ("Age", [29]), ("Age", {"years": 29}), ("BMI", [24.5]),
        ("Dysmenorrhea_Score", True), ("Age", True), ("BMI", False),  # booleans are not numbers
        ("Family_History", 1), ("Family_History", "yes"), ("Infertility_Status", None),
    ],
)
def test_out_of_range_or_wrong_type_values_are_rejected(client, sign_in, field, value):
    headers = sign_in()
    response = create(client, headers, {**HIGH, field: value})
    assert response.status_code == 422
    # Nothing was stored.
    assert client.get("/screenings", headers=headers).json()["total"] == 0


def test_unknown_fields_are_rejected(client, sign_in):
    headers = sign_in()
    assert create(client, headers, {**HIGH, "Shoe_Size": 38}).status_code == 422
    # Ownership can't be chosen by the caller.
    spoof = {**HIGH, "user_id": "00000000-0000-0000-0000-000000000000"}
    assert create(client, headers, spoof).status_code == 422
    # Labs are not accepted at creation; they have their own follow-up endpoint.
    assert create(client, headers, {**HIGH, **LABS_ELEVATED}).status_code == 422


def test_validation_errors_do_not_echo_health_answers_back(client, sign_in):
    response = create(client, sign_in(), {**HIGH, "Age": 123456789})
    assert response.status_code == 422
    assert "123456789" not in response.text


def test_non_json_and_empty_bodies_are_rejected(client, sign_in):
    headers = sign_in()
    assert client.post("/screenings", content=b"not json", headers=headers).status_code == 422
    assert client.post("/screenings", json={}, headers=headers).status_code == 422
    assert client.post("/screenings", json=[HIGH], headers=headers).status_code == 422


# --------------------------------------------------------------------------- #
# Lab follow-up
# --------------------------------------------------------------------------- #
def test_labs_refine_an_elevated_screening(client, sign_in):
    headers = sign_in()
    before = create(client, headers).json()

    response = add_labs(client, headers, before["id"])
    assert response.status_code == 200
    after = response.json()

    assert after["id"] == before["id"]
    assert after["recommendation"] == "elevated_confirmed"
    assert after["tier2_probability"] == pytest.approx(1.0, abs=0.001)
    assert after["tier2_flagged"] is True
    assert after["lab_inputs"] == LABS_ELEVATED
    assert after["can_add_labs"] is False
    assert len(after["factors"]["tier2"]) == 3
    assert "STEP 2" in after["report_text"]
    assert after["tier2_model_version"]

    # The original Tier 1 result is untouched.
    assert after["tier1_probability"] == before["tier1_probability"]
    assert after["tier1_flagged"] is True
    assert after["inputs"] == before["inputs"]
    assert after["factors"]["tier1"] == before["factors"]["tier1"]
    # (compared to the second: SQLite returns timezone-naive datetimes, Postgres aware ones)
    assert after["created_at"][:19] == before["created_at"][:19]

    # And it persisted.
    stored = client.get(f"/screenings/{before['id']}", headers=headers).json()
    assert stored["recommendation"] == "elevated_confirmed"


def test_reassuring_labs_give_not_confirmed(client, sign_in):
    headers = sign_in()
    screening = create(client, headers).json()
    body = add_labs(client, headers, screening["id"], LABS_REASSURING).json()
    assert body["recommendation"] == "elevated_not_confirmed"
    assert body["tier2_flagged"] is False


def test_labs_cannot_be_added_twice(client, sign_in):
    headers = sign_in()
    screening = create(client, headers).json()
    assert add_labs(client, headers, screening["id"]).status_code == 200
    second = add_labs(client, headers, screening["id"], LABS_REASSURING)
    assert second.status_code == 409
    # The first result stands.
    stored = client.get(f"/screenings/{screening['id']}", headers=headers).json()
    assert stored["lab_inputs"] == LABS_ELEVATED


def test_labs_are_refused_on_a_low_risk_screening(client, sign_in):
    headers = sign_in()
    screening = create(client, headers, LOW).json()
    response = add_labs(client, headers, screening["id"])
    assert response.status_code == 409
    stored = client.get(f"/screenings/{screening['id']}", headers=headers).json()
    assert stored["lab_inputs"] is None
    assert stored["recommendation"] == "low_risk"


@pytest.mark.parametrize(
    "labs",
    [
        {"CA_125_Level": 100.0},  # one value missing
        {"CRP_Level": 5.0},
        {},
        {"CA_125_Level": -1, "CRP_Level": 5},
        {"CA_125_Level": 100, "CRP_Level": -0.1},
        {"CA_125_Level": 10**9, "CRP_Level": 5},
        {"CA_125_Level": "high", "CRP_Level": 5},
        {"CA_125_Level": True, "CRP_Level": 5},  # booleans are not numbers
        {"CA_125_Level": "NaN", "CRP_Level": 5},
        {"CA_125_Level": [100], "CRP_Level": 5},
        {"CA_125_Level": 100, "CRP_Level": 5, "Age": 50},  # can't overwrite symptom answers
    ],
)
def test_invalid_lab_values_are_rejected_and_nothing_changes(client, sign_in, labs):
    headers = sign_in()
    screening = create(client, headers).json()
    assert add_labs(client, headers, screening["id"], labs).status_code == 422
    stored = client.get(f"/screenings/{screening['id']}", headers=headers).json()
    assert stored["lab_inputs"] is None
    assert stored["can_add_labs"] is True


def test_labs_for_unknown_screening_return_404(client, sign_in):
    headers = sign_in()
    response = add_labs(client, headers, "00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Listing and reading
# --------------------------------------------------------------------------- #
def test_list_is_newest_first_and_paginated(client, sign_in):
    headers = sign_in()
    ids = [create(client, headers, p).json()["id"] for p in (HIGH, LOW, HIGH)]

    listing = client.get("/screenings", headers=headers).json()
    assert listing["total"] == 3
    assert [item["id"] for item in listing["items"]] == ids[::-1]
    # The list is a summary: no answers and no report text.
    assert "inputs" not in listing["items"][0]
    assert "report_text" not in listing["items"][0]

    page = client.get("/screenings", params={"limit": 2, "offset": 2}, headers=headers).json()
    assert page["total"] == 3
    assert [item["id"] for item in page["items"]] == [ids[0]]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"limit": -1}, {"offset": -1}, {"limit": "x"}])
def test_bad_pagination_is_rejected(client, sign_in, params):
    assert client.get("/screenings", params=params, headers=sign_in()).status_code == 422


def test_get_with_a_malformed_id_is_rejected(client, sign_in):
    assert client.get("/screenings/not-a-uuid", headers=sign_in()).status_code == 422


# --------------------------------------------------------------------------- #
# Authentication and ownership
# --------------------------------------------------------------------------- #
def test_every_screening_endpoint_requires_a_token(client):
    some_id = "00000000-0000-0000-0000-000000000000"
    assert client.post("/screenings", json=HIGH).status_code == 401
    assert client.get("/screenings").status_code == 401
    assert client.get(f"/screenings/{some_id}").status_code == 401
    assert client.post(f"/screenings/{some_id}/labs", json=LABS_ELEVATED).status_code == 401


def test_users_only_see_their_own_screenings(client, sign_in):
    a, b = sign_in("a@example.com"), sign_in("b@example.com")
    a_id = create(client, a).json()["id"]
    b_id = create(client, b, LOW).json()["id"]

    assert [i["id"] for i in client.get("/screenings", headers=a).json()["items"]] == [a_id]
    assert [i["id"] for i in client.get("/screenings", headers=b).json()["items"]] == [b_id]
    assert client.get("/screenings", headers=b).json()["total"] == 1


def test_another_users_screening_looks_like_it_does_not_exist(client, sign_in):
    a, b = sign_in("a@example.com"), sign_in("b@example.com")
    a_id = create(client, a).json()["id"]

    missing = client.get("/screenings/00000000-0000-0000-0000-000000000000", headers=b)
    foreign = client.get(f"/screenings/{a_id}", headers=b)
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()  # nothing reveals that the id is real


def test_another_user_cannot_add_labs_to_my_screening(client, sign_in):
    a, b = sign_in("a@example.com"), sign_in("b@example.com")
    a_id = create(client, a).json()["id"]

    assert add_labs(client, b, a_id).status_code == 404

    mine = client.get(f"/screenings/{a_id}", headers=a).json()
    assert mine["lab_inputs"] is None
    assert mine["recommendation"] == "elevated_needs_labs"
    assert mine["can_add_labs"] is True


# --------------------------------------------------------------------------- #
# Schemas stay in sync with the models
# --------------------------------------------------------------------------- #
def test_request_schemas_match_the_model_features():
    registry = load_registry(ARTIFACTS)
    assert set(SymptomAnswers.model_fields) == set(registry.tier1.feature_names)
    assert set(LabResults.model_fields) == set(registry.lab_fields)
