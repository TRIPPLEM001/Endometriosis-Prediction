"""
Tests for the database layer, run against in-memory SQLite.

The most important tests here are the ownership ones: one user must never
be able to read, change, or delete another user's screenings.

Run with pytest from the backend/ folder:  pytest tests/test_repositories.py
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import RECOMMENDATION_CODES, Screening
from app.repositories import screenings as screening_repo
from app.repositories import users as user_repo
from app.services.prediction import Recommendation


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared in-memory database for the whole test
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_user(db, email="a@example.com"):
    return user_repo.create_user(
        db, email=email, password_hash="not-a-real-hash", consent_version="v1"
    )


def screening_kwargs(**overrides):
    base = dict(
        inputs={"Age": 29, "BMI": 24.5},
        lab_inputs=None,
        tier1_probability=0.88,
        tier1_flagged=True,
        tier2_probability=None,
        tier2_flagged=None,
        recommendation="elevated_needs_labs",
        factors={"tier1": [], "tier2": []},
        report_text="report",
        model_version="2026-10-v1",
        tier2_model_version=None,
        model_validated=False,
    )
    base.update(overrides)
    return base


def labs_kwargs(**overrides):
    base = dict(
        lab_inputs={"CA_125_Level": 165.0, "CRP_Level": 16.5},
        tier2_probability=0.999,
        tier2_flagged=True,
        recommendation="elevated_confirmed",
        factors={"tier1": [], "tier2": []},
        report_text="report with labs",
        tier2_model_version="2026-10-v1",
        model_validated=False,
    )
    base.update(overrides)
    return base


# ---------- users ----------

def test_email_is_normalised_and_unique_case_insensitively(db):
    user = make_user(db, "  Alice@Example.COM ")
    assert user.email == "alice@example.com"
    assert user_repo.get_by_email(db, "ALICE@example.com").id == user.id
    with pytest.raises(user_repo.EmailAlreadyRegistered):
        make_user(db, "alice@example.com")


def test_consent_is_recorded(db):
    user = make_user(db)
    assert user.consent_version == "v1"
    assert user.consented_at is not None


# ---------- screenings: basic behaviour ----------

def test_create_and_get_own_screening(db):
    user = make_user(db)
    created = screening_repo.create_screening(db, user.id, **screening_kwargs())
    fetched = screening_repo.get_screening(db, user.id, created.id)
    assert fetched is not None
    assert fetched.inputs == {"Age": 29, "BMI": 24.5}
    assert fetched.tier2_probability is None


def test_add_labs_updates_the_screening(db):
    user = make_user(db)
    s = screening_repo.create_screening(db, user.id, **screening_kwargs())
    updated = screening_repo.add_labs(db, user.id, s.id, **labs_kwargs())
    assert updated.tier2_probability == pytest.approx(0.999)
    assert updated.lab_inputs["CRP_Level"] == 16.5
    assert updated.recommendation == "elevated_confirmed"
    assert updated.tier2_model_version == "2026-10-v1"


def test_list_is_newest_first_and_paginated(db):
    user = make_user(db)
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for i in range(5):
        s = screening_repo.create_screening(db, user.id, **screening_kwargs(report_text=f"r{i}"))
        s.created_at = start + timedelta(days=i)
    db.commit()

    page1, total = screening_repo.list_screenings(db, user.id, limit=2, offset=0)
    page2, _ = screening_repo.list_screenings(db, user.id, limit=2, offset=2)
    assert total == 5
    assert [s.report_text for s in page1] == ["r4", "r3"]
    assert [s.report_text for s in page2] == ["r2", "r1"]


def test_list_limit_is_clamped(db):
    user = make_user(db)
    screening_repo.create_screening(db, user.id, **screening_kwargs())
    items, _ = screening_repo.list_screenings(db, user.id, limit=10_000)
    assert len(items) == 1
    items, _ = screening_repo.list_screenings(db, user.id, limit=-5)
    assert len(items) == 1  # clamped up to 1, not an error


# ---------- ownership isolation (the important ones) ----------

def test_user_cannot_read_another_users_screening(db):
    alice, bob = make_user(db, "alice@example.com"), make_user(db, "bob@example.com")
    s = screening_repo.create_screening(db, alice.id, **screening_kwargs())
    assert screening_repo.get_screening(db, bob.id, s.id) is None


def test_user_cannot_add_labs_to_another_users_screening(db):
    alice, bob = make_user(db, "alice@example.com"), make_user(db, "bob@example.com")
    s = screening_repo.create_screening(db, alice.id, **screening_kwargs())
    assert screening_repo.add_labs(db, bob.id, s.id, **labs_kwargs()) is None
    untouched = screening_repo.get_screening(db, alice.id, s.id)
    assert untouched.lab_inputs is None and untouched.tier2_probability is None


def test_user_cannot_delete_another_users_screening(db):
    alice, bob = make_user(db, "alice@example.com"), make_user(db, "bob@example.com")
    s = screening_repo.create_screening(db, alice.id, **screening_kwargs())
    assert screening_repo.delete_screening(db, bob.id, s.id) is False
    assert screening_repo.get_screening(db, alice.id, s.id) is not None


def test_list_only_returns_own_screenings(db):
    alice, bob = make_user(db, "alice@example.com"), make_user(db, "bob@example.com")
    screening_repo.create_screening(db, alice.id, **screening_kwargs())
    screening_repo.create_screening(db, bob.id, **screening_kwargs())
    screening_repo.create_screening(db, bob.id, **screening_kwargs())
    items, total = screening_repo.list_screenings(db, alice.id)
    assert total == 1 and len(items) == 1


def test_unknown_id_behaves_like_someone_elses(db):
    user = make_user(db)
    assert screening_repo.get_screening(db, user.id, uuid.uuid4()) is None
    assert screening_repo.delete_screening(db, user.id, uuid.uuid4()) is False


# ---------- deletion, erasure, export ----------

def test_delete_own_screening(db):
    user = make_user(db)
    s = screening_repo.create_screening(db, user.id, **screening_kwargs())
    assert screening_repo.delete_screening(db, user.id, s.id) is True
    assert screening_repo.get_screening(db, user.id, s.id) is None


def test_delete_all_for_user_keeps_account_and_other_users(db):
    alice, bob = make_user(db, "alice@example.com"), make_user(db, "bob@example.com")
    screening_repo.create_screening(db, alice.id, **screening_kwargs())
    screening_repo.create_screening(db, alice.id, **screening_kwargs())
    screening_repo.create_screening(db, bob.id, **screening_kwargs())
    assert screening_repo.delete_all_for_user(db, alice.id) == 2
    assert user_repo.get_by_id(db, alice.id) is not None
    assert screening_repo.list_screenings(db, bob.id)[1] == 1


def test_erasing_a_user_removes_their_data_only(db):
    alice, bob = make_user(db, "alice@example.com"), make_user(db, "bob@example.com")
    screening_repo.create_screening(db, alice.id, **screening_kwargs())
    screening_repo.create_screening(db, bob.id, **screening_kwargs())

    assert user_repo.delete_user_and_data(db, alice.id) is True
    assert user_repo.get_by_id(db, alice.id) is None
    assert db.scalar(select(func.count()).select_from(Screening).where(Screening.user_id == alice.id)) == 0
    assert screening_repo.list_screenings(db, bob.id)[1] == 1
    assert user_repo.delete_user_and_data(db, alice.id) is False  # already gone


def test_export_contains_only_that_users_data_and_no_password_hash(db):
    alice, bob = make_user(db, "alice@example.com"), make_user(db, "bob@example.com")
    screening_repo.create_screening(db, alice.id, **screening_kwargs(report_text="alice-report"))
    screening_repo.create_screening(db, bob.id, **screening_kwargs(report_text="bob-report"))

    exported = user_repo.export_user_data(db, alice)
    assert exported["account"]["email"] == "alice@example.com"
    assert [s["report_text"] for s in exported["screenings"]] == ["alice-report"]
    assert "password" not in str(exported).lower()


# ---------- database-level constraints ----------

def test_probability_outside_0_to_1_is_rejected(db):
    user = make_user(db)
    with pytest.raises(IntegrityError):
        screening_repo.create_screening(db, user.id, **screening_kwargs(tier1_probability=1.5))
    db.rollback()


def test_tier2_fields_must_be_set_together(db):
    user = make_user(db)
    with pytest.raises(IntegrityError):
        screening_repo.create_screening(
            db, user.id, **screening_kwargs(tier2_probability=0.7, tier2_flagged=None)
        )
    db.rollback()


def test_unknown_recommendation_is_rejected(db):
    user = make_user(db)
    with pytest.raises(IntegrityError):
        screening_repo.create_screening(db, user.id, **screening_kwargs(recommendation="maybe"))
    db.rollback()


def test_recommendation_codes_match_the_service_enum():
    assert set(RECOMMENDATION_CODES) == {r.value for r in Recommendation}
