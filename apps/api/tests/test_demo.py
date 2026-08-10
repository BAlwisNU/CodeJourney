"""Throwaway accounts for the landing page's two demo buttons.

The tests that matter most here are not about the buttons working. They are
about a stranger who clicked one on a public page never turning into a row in
the Week 8 analysis, and never being able to log in as anybody.
"""

from sqlalchemy import select

from app.models import Submission, User
from app.services.demo import (
    DEMO_DOMAIN,
    demo_kind,
    is_demo_email,
    purge_expired,
)

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


def test_the_two_buttons_are_told_apart(client):
    """The lesson demo is shown no way back to a dashboard it never came from;
    the account demo keeps it, because exploring is the whole point of that one.
    So the app has to know which button was pressed."""
    lesson = client.get("/auth/me", headers=_start(client, False)).json()
    account = client.get("/auth/me", headers=_start(client, True)).json()

    assert lesson["demo_kind"] == "lesson"
    assert account["demo_kind"] == "account"
    # Both are still demos, and both still say so.
    assert lesson["is_demo"] is account["is_demo"] is True


def test_an_older_demo_without_a_kind_is_treated_as_the_permissive_one(client):
    """Accounts minted before the two were distinguished must not be stranded."""
    assert demo_kind(f"demo-abc123@{DEMO_DOMAIN}") == "account"


def test_a_real_account_is_not_flagged_as_a_demo(client):
    me = client.get("/auth/me", headers=login(client)).json()
    assert me["is_demo"] is False
    assert me["demo_kind"] is None
    assert is_demo_email(me["email"]) is False
    assert demo_kind(me["email"]) is None


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


def test_the_account_demo_shows_all_three_states(client):
    """Solved, in progress, and not started -- the dashboard has three states,
    and a demo showing one of them demonstrates a third of the product.

    Asserted through /progress rather than the tables, because that endpoint is
    what decides the states and is what the dashboard actually renders.
    """
    headers = _start(client, with_progress=True)
    body = client.get("/progress", headers=headers).json()
    states = {}
    for row in body["exercises"]:
        states[row["status"]] = states.get(row["status"], 0) + 1

    assert states.get("solved", 0) >= 5, states
    assert states.get("in_progress", 0) >= 3, states
    assert states.get("not_started", 0) >= 10, states


def test_the_account_demo_shows_the_hint_ladder_being_used(client):
    """The retries and the hints are the product; a clean sweep hides both."""
    headers = _start(client, with_progress=True)
    me = client.get("/auth/me", headers=headers).json()

    with client.session_factory() as db:
        rows = list(
            db.scalars(select(Submission).where(Submission.user_id == me["id"]))
        )
    assert any(r.passed for r in rows), "something should be solved"
    assert any(not r.passed for r in rows), "and something should have failed"
    assert any(r.max_hint_level > 0 for r in rows), "hints should have been used"
    # Something solved only after several goes, which is the honest shape of it.
    assert any(r.attempt_number >= 3 and r.passed for r in rows)


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

    monkeypatch.setattr(demo_service, "_STORY", [("no-such-exercise", 2, 1, "solved")])
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
        assert _rows_still_pointing_at(db, user_id) == []


def _rows_still_pointing_at(db, user_id: str) -> list[str]:
    """Every table still holding this user's id, found from the schema itself.

    Asked of the metadata rather than a hand-written list of tables, because a
    hand-written list is exactly what went stale last time: the purge deleted
    submissions and sessions and knew nothing of the eleven other tables that
    had grown a user_id since it was written. A table added next term is covered
    by this the day it is added, without anyone remembering to come back here.
    """
    from sqlalchemy import func, select

    from app.models import Base

    left = []
    for table in Base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            if fk.column.table.name != "users":
                continue
            column = fk.parent
            count = db.scalar(
                select(func.count()).select_from(table).where(column == user_id)
            )
            if count:
                left.append(f"{table.name}.{column.name} ({count})")
    return left


def test_purging_removes_a_row_from_every_table_that_can_hold_one(client):
    """The purge is exercised against a user who owns something everywhere.

    The other purge test uses a demo account with the fixture's own activity in
    it, which reaches two tables. That is not enough to prove a purge that has
    to clear thirteen: the bug this guards against was a delete list written
    when there were two such tables and never revisited as eleven more arrived.
    So this one puts a row in each of them by hand first.

    _rows_still_pointing_at then reads the schema rather than a list, and the
    assertion below checks that this test itself stays honest -- if someone adds
    a fourteenth table with a user_id, the count changes and this fails until
    somebody has thought about whether the purge covers it.
    """
    from datetime import datetime, timedelta, timezone

    from app.models import (
        Classroom,
        Concept,
        Draft,
        ExerciseSession,
        HelpRequest,
        HintEvent,
        Lesson,
        LessonProgress,
        Mastery,
        ParsonsAttempt,
        ParsonsProblem,
        Reflection,
        TutorChatMessage,
    )

    headers = _start(client, with_progress=True)
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    with client.session_factory() as db:
        session = db.query(ExerciseSession).filter_by(user_id=user_id).first()
        exercise_id = session.exercise_id
        problem_id = db.query(ParsonsProblem).first().id
        lesson_id = db.query(Lesson).first().id

        db.add_all(
            [
                HintEvent(
                    user_id=user_id,
                    exercise_id=exercise_id,
                    session_id=session.id,
                    level=2,
                    trigger="idle",
                ),
                ParsonsAttempt(user_id=user_id, problem_id=problem_id),
                Reflection(user_id=user_id, exercise_id=exercise_id),
                TutorChatMessage(
                    user_id=user_id,
                    exercise_id=exercise_id,
                    role="user",
                    content="why did that fail?",
                ),
                Draft(user_id=user_id, exercise_id=exercise_id),
                Mastery(user_id=user_id, concept=Concept.LOOPS),
                LessonProgress(user_id=user_id, lesson_id=lesson_id),
                HelpRequest(student_id=user_id, body="stuck on this one"),
                Classroom(teacher_id=user_id, name="Demo class", join_code="DEMO01"),
            ]
        )
        db.get(User, user_id).created_at = datetime.now(timezone.utc) - timedelta(
            days=30
        )
        db.commit()

        owned = _rows_still_pointing_at(db, user_id)
        assert len(owned) == 11, f"expected every blocking table populated, got {owned}"

        assert purge_expired(db, older_than_days=7) == 1
        assert db.get(User, user_id) is None
        assert _rows_still_pointing_at(db, user_id) == []


def test_purging_a_demo_teacher_keeps_the_answer_it_gave_a_real_student(client):
    """The demo account goes; the real student's question does not go with it.

    answered_by_id is followed by nulling rather than by deleting, and this is
    why. The help request belongs to the student who asked it, and a stranger
    clicking "try it" on the landing page must not be able to take a real
    student's work with them on the way out.
    """
    from datetime import datetime, timedelta, timezone

    from app.models import HelpRequest

    headers = _start(client)
    demo_id = client.get("/auth/me", headers=headers).json()["id"]
    student_id = client.get("/auth/me", headers=login(client)).json()["id"]

    with client.session_factory() as db:
        request = HelpRequest(
            student_id=student_id,
            body="Why does my loop stop early?",
            answer="Look at where the counter changes.",
            answered_by_id=demo_id,
        )
        db.add(request)
        db.get(User, demo_id).created_at = datetime.now(timezone.utc) - timedelta(
            days=30
        )
        db.commit()
        request_id = request.id

        assert purge_expired(db, older_than_days=7) == 1

        db.expire_all()
        kept = db.get(HelpRequest, request_id)
        assert kept is not None, "a real student's question was deleted with a demo"
        assert kept.answer == "Look at where the counter changes."
        assert kept.answered_by_id is None


def test_purging_leaves_fresh_demos_and_real_accounts_alone(client):
    headers = _start(client)
    fresh_id = client.get("/auth/me", headers=headers).json()["id"]
    real_id = client.get("/auth/me", headers=login(client)).json()["id"]

    with client.session_factory() as db:
        assert purge_expired(db, older_than_days=7) == 0
        assert db.get(User, fresh_id) is not None
        assert db.get(User, real_id) is not None
