"""
Tests for registration, login and get_current_user, through the real FastAPI
app with an in-memory SQLite database.

Run from backend/:  pytest tests/test_auth.py
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import (
    InvalidToken,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.models import User

PASSWORD = "correct horse battery"  # same value conftest uses
SETTINGS = get_settings()


# --------------------------------------------------------------------------- #
# Helpers (the `client` and `session_factory` fixtures live in conftest.py)
# --------------------------------------------------------------------------- #
def register_payload(**overrides):
    payload = {
        "email": "a@example.com",
        "password": PASSWORD,
        "consent_accepted": True,
        "consent_version": SETTINGS.consent_version,
    }
    payload.update(overrides)
    return payload


def register(client, **overrides):
    return client.post("/auth/register", json=register_payload(**overrides))


def login(client, email="a@example.com", password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def make_token(user_id, **overrides):
    kwargs = dict(
        secret=SETTINGS.jwt_secret,
        algorithm=SETTINGS.jwt_algorithm,
        expires_minutes=5,
    )
    kwargs.update(overrides)
    return create_access_token(user_id, **kwargs)


def registered_user_id(client):
    return uuid.UUID(register(client).json()["id"])


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #
def test_register_creates_account(client, session_factory):
    response = register(client, email="  Mixed.Case@Example.com ")
    assert response.status_code == 201
    body = response.json()

    # Only the intended fields come back; never anything password-related.
    assert set(body) == {"id", "email", "consent_version", "consented_at", "created_at"}
    assert body["email"] == "mixed.case@example.com"
    assert body["consent_version"] == SETTINGS.consent_version

    with session_factory() as db:
        user = db.scalar(select(User))
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2id$")


def test_register_rejects_duplicate_email_in_any_case(client):
    assert register(client).status_code == 201
    assert register(client, email="A@EXAMPLE.COM").status_code == 409


def test_register_requires_consent(client):
    assert register(client, consent_accepted=False).status_code == 422
    # Must be a real boolean, not a truthy string.
    assert register(client, consent_accepted="yes").status_code == 422
    missing = register_payload()
    del missing["consent_accepted"]
    assert client.post("/auth/register", json=missing).status_code == 422


def test_register_rejects_outdated_consent_version(client):
    response = register(client, consent_version="1999-01-v0")
    assert response.status_code == 409


def test_register_rejects_bad_email_and_weak_password(client):
    assert register(client, email="not-an-email").status_code == 422
    assert register(client, password="short").status_code == 422
    assert register(client, password="x" * 129).status_code == 422


def test_validation_errors_do_not_echo_the_submitted_password(client):
    secret = "tooshort"
    response = register(client, password=secret)
    assert response.status_code == 422
    assert secret not in response.text
    assert "input" not in response.text


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #
def test_login_returns_working_token(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == SETTINGS.access_token_expire_minutes * 60

    me = client.get("/auth/me", headers=auth_header(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_login_email_is_case_insensitive(client):
    register(client)
    assert login(client, email="A@Example.COM").status_code == 200


def test_wrong_password_and_unknown_email_look_identical(client):
    register(client)
    wrong_password = login(client, password="not the password")
    unknown_email = login(client, email="nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_login_upgrades_outdated_password_hash(client, session_factory, monkeypatch):
    register(client)
    # Pretend the stored hash was made with weaker settings than today's.
    monkeypatch.setattr("app.api.routes.auth.needs_rehash", lambda _hash: True)
    with session_factory() as db:
        old_hash = db.scalar(select(User)).password_hash

    assert login(client).status_code == 200

    with session_factory() as db:
        new_hash = db.scalar(select(User)).password_hash
    assert new_hash != old_hash
    assert verify_password(PASSWORD, new_hash)
    assert login(client).status_code == 200


# --------------------------------------------------------------------------- #
# get_current_user (exercised through /auth/me)
# --------------------------------------------------------------------------- #
def test_me_requires_a_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Bearer garbage", "Bearer ", "Basic abc123", "token"])
def test_me_rejects_malformed_authorization_headers(client, header):
    assert client.get("/auth/me", headers={"Authorization": header}).status_code == 401


def test_me_rejects_expired_token(client):
    user_id = registered_user_id(client)
    token = make_token(user_id, expires_minutes=-5)
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401


def test_me_rejects_token_signed_with_another_secret(client):
    user_id = registered_user_id(client)
    token = make_token(user_id, secret="a-different-secret-" + "y" * 40)
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401


def test_me_rejects_unsigned_token(client):
    user_id = registered_user_id(client)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": str(user_id), "exp": now + timedelta(minutes=5)}, None, algorithm="none"
    )
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401


def test_me_rejects_token_without_expiry(client):
    user_id = registered_user_id(client)
    token = jwt.encode({"sub": str(user_id)}, SETTINGS.jwt_secret, algorithm=SETTINGS.jwt_algorithm)
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401


@pytest.mark.parametrize("subject", ["not-a-uuid", 12345, None])
def test_me_rejects_tokens_with_bad_subject(client, subject):
    exp = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode(
        {"sub": subject, "exp": exp}, SETTINGS.jwt_secret, algorithm=SETTINGS.jwt_algorithm
    )
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401


def test_token_for_deleted_user_stops_working(client, session_factory):
    register(client)
    token = login(client).json()["access_token"]
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 200

    with session_factory() as db:
        db.delete(db.scalar(select(User)))
        db.commit()

    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401


def test_token_identifies_its_own_user_only(client):
    register(client, email="a@example.com")
    register(client, email="b@example.com")
    token_b = login(client, email="b@example.com").json()["access_token"]
    me = client.get("/auth/me", headers=auth_header(token_b)).json()
    assert me["email"] == "b@example.com"


# --------------------------------------------------------------------------- #
# security.py on its own
# --------------------------------------------------------------------------- #
def test_password_hashes_are_salted_and_verifiable():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first != second
    assert verify_password(PASSWORD, first)
    assert not verify_password("wrong", first)


def test_verify_password_treats_a_malformed_hash_as_a_mismatch():
    assert verify_password(PASSWORD, "not-a-hash") is False


def test_token_round_trip_and_tamper_detection():
    user_id = uuid.uuid4()
    token = make_token(user_id)
    assert decode_access_token(
        token, secret=SETTINGS.jwt_secret, algorithm=SETTINGS.jwt_algorithm
    ) == user_id

    header, payload, signature = token.split(".")
    tampered = ".".join([header, payload, signature[:-2] + ("AA" if signature[-2:] != "AA" else "BB")])
    with pytest.raises(InvalidToken):
        decode_access_token(tampered, secret=SETTINGS.jwt_secret, algorithm=SETTINGS.jwt_algorithm)


def test_settings_reject_a_short_jwt_secret():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+pysqlite:///:memory:", jwt_secret="change-me")


# --------------------------------------------------------------------------- #
# Hostile and unusual input
# --------------------------------------------------------------------------- #
HOSTILE_EMAILS = [
    "' OR '1'='1",
    "a@example.com'; DROP TABLE users;--",
    "a@example.com\x00",
    "a" * 10_000 + "@example.com",
    "<script>alert(1)</script>@example.com",
    "",
]
HOSTILE_PASSWORDS = ["' OR 1=1 --", "\x00" * 12, "x" * 129, "", "\u202e" * 12]


def test_hostile_emails_are_rejected_without_server_errors(client):
    for email in HOSTILE_EMAILS:
        assert register(client, email=email).status_code == 422, email
        assert login(client, email=email).status_code == 422, email


def test_hostile_passwords_never_log_anyone_in_or_crash(client):
    register(client)
    for password in HOSTILE_PASSWORDS:
        assert login(client, password=password).status_code in (401, 422), repr(password)


def test_unicode_passwords_work(client):
    password = "p\u00e4ssw\u00f6rd-\u30d1\u30b9\u30ef\u30fc\u30c9-\U0001f512"
    assert register(client, email="u@example.com", password=password).status_code == 201
    assert login(client, email="u@example.com", password=password).status_code == 200
    assert login(client, email="u@example.com", password=PASSWORD).status_code == 401


def test_register_ignores_fields_the_caller_should_not_control(client, session_factory):
    chosen_id = str(uuid.uuid4())
    response = register(
        client, id=chosen_id, is_admin=True, created_at="2000-01-01T00:00:00Z",
        consented_at="2000-01-01T00:00:00Z", password_hash="$argon2id$forged",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] != chosen_id
    assert not body["created_at"].startswith("2000")
    assert not body["consented_at"].startswith("2000")

    with session_factory() as db:
        user = db.scalar(select(User))
        assert user.password_hash != "$argon2id$forged"
    assert login(client).status_code == 200


def test_token_in_the_query_string_is_not_accepted(client):
    register(client)
    token = login(client).json()["access_token"]
    assert client.get("/auth/me", params={"access_token": token}).status_code == 401
    assert client.get("/auth/me", params={"token": token}).status_code == 401


def test_malformed_json_bodies_are_rejected(client):
    for path in ("/auth/register", "/auth/login"):
        assert client.post(path, content=b"{not json").status_code == 422
        assert client.post(path, json=["a@example.com", PASSWORD]).status_code == 422
        assert client.post(path, json=None).status_code == 422
