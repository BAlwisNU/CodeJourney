"""Throwaway accounts for the landing page's two demo buttons.

The tests that matter most here are not about the buttons working. They are
about a stranger who clicked one on a public page never turning into a row in
the Week 8 analysis, and never being able to log in as anybody.
"""

from sqlalchemy import select

from app.models import Submission, User
from app.services.demo import DEMO_DOMAIN, is_demo_email, purge_expired

from conftest import login


def _start(client, with_progress=False) -> dict:
    response = client.post("/auth/demo", json={"with_progress": with_progress})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- what a demo account is -------------------------------------------------


def test_a_demo_needs_no_account_and_works_immediately(client):
    headers = _start(client)
    me = client.get("/auth/me", headers=headers).json()
    assert me["is_demo"] is True
    assert me["email"].endswith(f"@{DEMO_DOMAIN}")
    # And it is a real, usable account -- the whole point is to show the product.
    assert client.get("/progress", headers=headers).status_code == 200


def test_every_click_gets_its_own_account(client):
    """A shared login would let two visitors undo each other's work."""
    first = client.get("/auth/me", headers=_start(client)).json()
    second = client.get("/auth/me", headers=_start(client)).json()
    assert first["id"] != second["id"]
    assert first["email"] != second["email"]


def test_a_real_account_is_not_flagged_as_a_demo(client):
    me = client.get("/auth/me", headers=login(client)).json()
    assert me["is_demo"] is False
    assert is_demo_email(me["email"]) is False


# --- the two rules that actually matter -------------------------------------


def test_a_demo_is_never_study_data(client):
    """A stranger clicking a button on a marketing page consented to nothing.

    `consented_at` is what every analysis filters on, so it has to be None --
    and there must be no way for the demo path to set it.
    """
    headers = _start(client, with_progress=True)
    me = client.get("/auth/me", headers=headers).json()
    assert me["consented_at"] is None

    with client.session_factory() as db:
        user = db.get(User, me["id"])
        assert user.consented_at is None
        # Still counterbalanced like any other account, so the app behaves
        # identically -- the study simply never looks at this row.
        assert user.counterbalance_group in {"A", "B"}


def test_a_demo_account_cannot_be_logged_into(client):
    """It has no password, and the address is not guessable or shared.

    A demo that could be signed into later would be a permanent unauthenticated
    account sitting in the users table.
    """
    headers = _start(client)
    email = client.get("/auth/me", headers=headers).json()["email"]

    for password in ("", "password123", "demo", "!oauth-only-no-password-set"):
        response = client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 401, password


# --- the seeded history -----------------------------------------------------


def test_the_account_demo_arrives_with_work_already_in_it(client):
    """An empty dashboard demonstrates nothing about what the product does."""
    headers = _start(client, with_progress=True)
    me = client.get("/auth/me", headers=headers).json()

    with client.session_factory() as db:
        rows = list(
            db.scalars(select(Submission).where(Submission.user_id == me["id"]))
        )
    assert rows, "the demo account should have submissions to show"
    assert any(r.passed for r in rows), "something should be solved"
    assert any(not r.passed for r in rows), "and something should have failed"
    # Hints used, because the hint ladder is the thing worth demonstrating.
    assert any(r.max_hint_level > 0 for r in rows)


def test_the_lesson_demo_starts_clean(client):
    """Straight into an exercise, with nothing pre-filled to explain away."""
    headers = _start(client, with_progress=False)
    me = client.get("/auth/me", headers=headers).json()
    with client.session_factory() as db:
        count = db.query(Submission).filter(Submission.user_id == me["id"]).count()
    assert count == 0


def test_seeding_survives_a_renamed_exercise(client, monkeypatch):
    """Content slugs get edited often; a demo must not 500 because one moved."""
    from app.services import demo as demo_service

    monkeypatch.setattr(demo_service, "_STORY", [("no-such-exercise", 2, 1)])
    headers = _start(client, with_progress=True)
    assert client.get("/auth/me", headers=headers).status_code == 200


# --- cleanup ----------------------------------------------------------------


def test_stale_demo_accounts_are_purged_with_their_work(client):
    """Anyone can create these, so something has to remove them again."""
    from datetime import datetime, timedelta, timezone

    headers = _start(client, with_progress=True)
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    with client.session_factory() as db:
        # Age it past the cutoff.
        user = db.get(User, user_id)
        user.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        db.commit()

        assert purge_expired(db, older_than_days=7) == 1
        assert db.get(User, user_id) is None
        # And nothing of theirs is left orphaned behind them.
        assert (
            db.query(Submission).filter(Submission.user_id == user_id).count() == 0
        )


def test_purging_leaves_fresh_demos_and_real_accounts_alone(client):
    headers = _start(client)
    fresh_id = client.get("/auth/me", headers=headers).json()["id"]
    real_id = client.get("/auth/me", headers=login(client)).json()["id"]

    with client.session_factory() as db:
        assert purge_expired(db, older_than_days=7) == 0
        assert db.get(User, fresh_id) is not None
        assert db.get(User, real_id) is not None
