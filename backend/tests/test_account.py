"""
Tests for the privacy endpoints: data export and the three kinds of deletion
(one screening, all screenings, the whole account).

Run from backend/:  pytest tests/test_account.py
"""

import json
import uuid

from sqlalchemy import func, select

from app.db.models import Screening, User
from tests.helpers import HIGH, LABS_ELEVATED, LOW, add_labs, create

PASSWORD = "correct horse battery"  # same value conftest uses
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def delete_account(client, headers, password=PASSWORD):
    return client.request("DELETE", "/account", json={"password": password}, headers=headers)


def count(session_factory, model, **filters):
    with session_factory() as db:
        stmt = select(func.count()).select_from(model)
        for column, value in filters.items():
            stmt = stmt.where(getattr(model, column) == value)
        return db.scalar(stmt)


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def test_export_requires_a_token(client):
    assert client.get("/account/export").status_code == 401


def test_export_contains_everything_stored_about_me(client, sign_in):
    headers = sign_in()
    first = create(client, headers).json()
    second = create(client, headers, LOW).json()
    add_labs(client, headers, first["id"], LABS_ELEVATED)

    response = client.get("/account/export", headers=headers)
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    data = response.json()

    assert data["format_version"] == 1
    assert data["exported_at"]
    assert data["account"]["email"] == "a@example.com"
    assert {"consent_version", "consented_at", "created_at"} <= set(data["account"])

    exported = {s["id"]: s for s in data["screenings"]}
    assert set(exported) == {first["id"], second["id"]}
    refined = exported[first["id"]]
    assert refined["lab_inputs"] == LABS_ELEVATED
    assert refined["recommendation"] == "elevated_confirmed"
    assert refined["inputs"]["Age"] == HIGH["Age"]
    assert "STEP 2" in refined["report_text"]
    assert exported[second["id"]]["lab_inputs"] is None


def test_export_never_contains_the_password_or_its_hash(client, sign_in, session_factory):
    headers = sign_in()
    create(client, headers)
    body = client.get("/account/export", headers=headers).text

    with session_factory() as db:
        password_hash = db.scalar(select(User)).password_hash
    assert password_hash not in body
    assert "argon2" not in body
    assert PASSWORD not in body
    assert "password" not in json.loads(body)["account"]


def test_export_contains_only_my_data(client, sign_in):
    a, b = sign_in("a@example.com"), sign_in("b@example.com")
    a_id = create(client, a).json()["id"]
    b_id = create(client, b, LOW).json()["id"]

    export_a = client.get("/account/export", headers=a).json()
    assert export_a["account"]["email"] == "a@example.com"
    assert [s["id"] for s in export_a["screenings"]] == [a_id]
    assert "b@example.com" not in json.dumps(export_a)
    assert b_id not in json.dumps(export_a)


def test_export_for_a_new_account_has_no_screenings(client, sign_in):
    data = client.get("/account/export", headers=sign_in()).json()
    assert data["screenings"] == []


def test_responses_are_marked_no_store(client, sign_in):
    headers = sign_in()
    assert client.get("/account/export", headers=headers).headers["cache-control"] == "no-store"
    assert create(client, headers).headers["cache-control"] == "no-store"
    assert client.get("/health").headers["cache-control"] == "no-store"


# --------------------------------------------------------------------------- #
# Delete one screening
# --------------------------------------------------------------------------- #
def test_delete_screening(client, sign_in, session_factory):
    headers = sign_in()
    keep = create(client, headers).json()["id"]
    remove = create(client, headers, LOW).json()["id"]

    response = client.delete(f"/screenings/{remove}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""

    assert client.get(f"/screenings/{remove}", headers=headers).status_code == 404
    assert [i["id"] for i in client.get("/screenings", headers=headers).json()["items"]] == [keep]
    assert count(session_factory, Screening) == 1
    # Deleting again is a 404, not a silent success.
    assert client.delete(f"/screenings/{remove}", headers=headers).status_code == 404


def test_delete_unknown_or_malformed_screening_id(client, sign_in):
    headers = sign_in()
    assert client.delete(f"/screenings/{UNKNOWN_ID}", headers=headers).status_code == 404
    assert client.delete("/screenings/not-a-uuid", headers=headers).status_code == 422


def test_cannot_delete_another_users_screening(client, sign_in, session_factory):
    a, b = sign_in("a@example.com"), sign_in("b@example.com")
    a_id = create(client, a).json()["id"]

    foreign = client.delete(f"/screenings/{a_id}", headers=b)
    missing = client.delete(f"/screenings/{UNKNOWN_ID}", headers=b)
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()

    assert count(session_factory, Screening) == 1
    assert client.get(f"/screenings/{a_id}", headers=a).status_code == 200


def test_delete_endpoints_require_a_token(client):
    assert client.delete(f"/screenings/{UNKNOWN_ID}").status_code == 401
    assert client.delete("/screenings", params={"confirm": "true"}).status_code == 401
    assert client.request("DELETE", "/account", json={"password": PASSWORD}).status_code == 401


# --------------------------------------------------------------------------- #
# Delete all screenings (account stays)
# --------------------------------------------------------------------------- #
def test_delete_all_screenings_requires_confirmation(client, sign_in, session_factory):
    headers = sign_in()
    create(client, headers)

    assert client.delete("/screenings", headers=headers).status_code == 422
    assert client.delete("/screenings", params={"confirm": "false"}, headers=headers).status_code == 400
    assert count(session_factory, Screening) == 1


def test_delete_all_screenings_only_touches_mine_and_keeps_the_account(
    client, sign_in, session_factory
):
    a, b = sign_in("a@example.com"), sign_in("b@example.com")
    create(client, a)
    create(client, a, LOW)
    b_id = create(client, b).json()["id"]

    response = client.delete("/screenings", params={"confirm": "true"}, headers=a)
    assert response.status_code == 200
    assert response.json() == {"deleted": 2}

    assert client.get("/screenings", headers=a).json()["total"] == 0
    assert client.get("/auth/me", headers=a).status_code == 200  # account still works
    assert client.get(f"/screenings/{b_id}", headers=b).status_code == 200
    assert count(session_factory, Screening) == 1

    # Nothing left to delete is still a success.
    again = client.delete("/screenings", params={"confirm": "true"}, headers=a)
    assert again.json() == {"deleted": 0}


# --------------------------------------------------------------------------- #
# Delete the account
# --------------------------------------------------------------------------- #
def test_delete_account_needs_the_correct_password(client, sign_in, session_factory):
    headers = sign_in()
    create(client, headers)

    assert delete_account(client, headers, password="wrong password!!").status_code == 403
    assert client.request("DELETE", "/account", headers=headers).status_code == 422  # no body
    assert delete_account(client, headers, password="").status_code == 422

    assert count(session_factory, User) == 1
    assert count(session_factory, Screening) == 1
    assert client.get("/auth/me", headers=headers).status_code == 200  # still signed in


def test_delete_account_erases_everything_and_ends_the_session(client, sign_in, session_factory):
    a, b = sign_in("a@example.com"), sign_in("b@example.com")
    for _ in range(2):
        create(client, a)
    b_id = create(client, b).json()["id"]
    with session_factory() as db:
        a_user_id = db.scalar(select(User).where(User.email == "a@example.com")).id

    response = delete_account(client, a)
    assert response.status_code == 204

    # Account and its screenings are gone from the database.
    assert count(session_factory, User, email="a@example.com") == 0
    assert count(session_factory, Screening, user_id=a_user_id) == 0

    # The old token stops working immediately, and the credentials no longer log in.
    assert client.get("/auth/me", headers=a).status_code == 401
    assert client.get("/screenings", headers=a).status_code == 401
    login = client.post("/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert login.status_code == 401

    # The other user is untouched.
    assert client.get(f"/screenings/{b_id}", headers=b).status_code == 200
    assert count(session_factory, User) == 1
    assert count(session_factory, Screening) == 1


def test_email_can_be_registered_again_after_deletion(client, sign_in):
    headers = sign_in("a@example.com")
    assert delete_account(client, headers).status_code == 204

    new_headers = sign_in("a@example.com")  # would 409 if the old row lingered
    assert client.get("/screenings", headers=new_headers).json()["total"] == 0


def test_deleting_twice_with_the_same_token_fails_cleanly(client, sign_in):
    headers = sign_in()
    assert delete_account(client, headers).status_code == 204
    assert delete_account(client, headers).status_code == 401
