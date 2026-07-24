"""End-to-end test of the submit path, against SQLite.

Covers the things that would be expensive to discover in Week 7: that the
research columns are actually populated, that the hint ladder escalates and
ratchets, and that divergence is detected rather than blamed on the student.

Fixtures and helpers live in conftest.py.
"""

import pytest
from sqlalchemy import select

from conftest import BOOM, CORRECT, WRONG, login, open_exercise, submit  # noqa: F401
from app.models import Concept, RunMode, Submission, Theme, ThemeVariant


# --- auth ------------------------------------------------------------------


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/exercises").status_code == 401


def test_login_and_me(client):
    headers = login(client)
    me = client.get("/auth/me", headers=headers).json()
    assert me["role"] == "student"


# --- exercise exposure -----------------------------------------------------


def test_hidden_test_args_never_reach_the_client(client):
    headers = login(client)
    exercise, _ = open_exercise(client, headers)
    hidden = [t for t in exercise["tests"] if t["hidden"]]
    assert hidden, "seed should include hidden tests"
    for test in hidden:
        assert test["args"] is None
        assert test["expected"] is None


def test_visible_tests_do_show_their_data(client):
    headers = login(client)
    exercise, _ = open_exercise(client, headers)
    visible = [t for t in exercise["tests"] if not t["hidden"]]
    assert visible[0]["args"] is not None


# --- the pair --------------------------------------------------------------


def test_themed_and_generic_twins_are_matched(client):
    """The twins must be identical in everything but framing.

    If this fails, the study is measuring difficulty rather than framing, and no
    amount of careful analysis downstream can recover from it.
    """
    headers = login(client)
    themed, _ = open_exercise(client, headers, "expired-quests")
    generic, _ = open_exercise(client, headers, "filter-records-generic")

    assert themed["variant"] == "themed"
    assert generic["variant"] == "generic"
    assert themed["concept"] == generic["concept"]
    # Same tests, in the same order, with the same visibility.
    assert [(t["name"], t["hidden"]) for t in themed["tests"]] == [
        (t["name"], t["hidden"]) for t in generic["tests"]
    ]
    # Different entrypoints: a control condition called `expired_quests` would
    # leak the theme into the control.
    assert themed["entrypoint"] != generic["entrypoint"]


# --- grading ---------------------------------------------------------------


def test_correct_submission_passes(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    body = submit(client, headers, exercise, session_id, CORRECT).json()
    assert body["passed"] is True
    assert body["attempt_number"] == 1
    assert body["test_results"]["summary"]["passed"] == 5


def test_wrong_submission_fails_without_an_exception(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    body = submit(client, headers, exercise, session_id, WRONG).json()
    assert body["passed"] is False
    # Returning [] passes the two tests that expect [], fails the rest.
    assert 0 < body["test_results"]["summary"]["passed"] < 5


# --- the research dataset --------------------------------------------------


def test_submission_records_the_research_columns(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)

    with client.session_factory() as db:
        row = db.scalar(select(Submission))
        # Every one of these is a Week 8 dependent variable. If any is missing
        # or wrong, the analysis has nothing to run on.
        assert row.theme_variant is ThemeVariant.THEMED
        assert row.run_mode is RunMode.SUBMIT
        assert row.session_id == session_id
        assert row.seconds_since_exercise_start >= 0
        assert row.attempt_number == 1
        assert row.code == CORRECT
        assert row.divergence_flag is False


def test_theme_variant_is_frozen_at_write_time(client):
    """Re-theming an exercise must not rewrite the condition of past submissions.

    The scenario: someone edits content mid-study -- pulls this exercise out of
    its pair and re-labels it as the generic condition. If `theme_variant` were
    joined through Exercise at analysis time instead of denormalised onto the
    Submission, this edit would silently rewrite every past attempt's condition
    and the Week 8 analysis would be wrong with no sign that anything happened.
    """
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)

    with client.session_factory() as db:
        from app.models import Exercise

        target = db.scalar(
            select(Exercise).where(Exercise.slug == "expired-quests")
        )
        # Re-pair before re-labelling: UNIQUE(pair_id, variant) correctly refuses
        # to let a pair have two generic sides, so a bare variant flip can't
        # happen. Moving it to a new pair is the edit that actually could.
        target.pair_id = "00000000-0000-0000-0000-0000000000ff"
        target.variant = ThemeVariant.GENERIC
        db.commit()

        row = db.scalar(select(Submission))
        # Still THEMED. The submission remembers the condition it was made under.
        assert row.theme_variant is ThemeVariant.THEMED


def test_a_pair_cannot_have_two_sides_of_the_same_variant(client):
    """The constraint that keeps pairs coherent.

    A pair with two themed sides and no control is a pair that can't be analysed.
    Better to fail loudly at write time than to discover it in Week 8.
    """
    from sqlalchemy.exc import IntegrityError

    from app.models import Exercise
    from app.seed import PAIR_ID

    with client.session_factory() as db:
        db.add(
            Exercise(
                slug="duplicate-side",
                title="Duplicate",
                theme=Theme.GAMES,
                concept=Concept.LISTS,
                variant=ThemeVariant.THEMED,  # already taken for this pair
                pair_id=PAIR_ID,
                entrypoint="x",
                prompt_md="",
                tests=[],
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_runs_are_logged_as_behaviour_not_just_submits(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, WRONG, mode="run")

    with client.session_factory() as db:
        row = db.scalar(select(Submission))
        assert row.run_mode is RunMode.RUN


# --- the hint ladder -------------------------------------------------------


def test_ladder_escalates_with_consecutive_failures(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)

    levels = []
    for _ in range(6):
        levels.append(submit(client, headers, exercise, session_id, WRONG).json()["hint_level"])

    # L2 after 2 failures, L3 after 4, L4 after 6 -- and never above 4, because
    # L5 is a human and the answer is never.
    assert levels[1] >= 2
    assert levels[3] >= 3
    assert levels[5] == 4
    assert max(levels) <= 4


def test_ladder_is_a_ratchet_and_never_goes_down(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    for _ in range(4):
        submit(client, headers, exercise, session_id, WRONG)
    high = submit(client, headers, exercise, session_id, WRONG).json()["hint_level"]

    # A passing submission must not un-reveal what they've already seen --
    # otherwise peek-then-reset would make the mastery penalty measure nothing.
    after = submit(client, headers, exercise, session_id, CORRECT).json()
    assert after["passed"] is True
    assert after["hint_level"] >= high


def test_hint_text_appears_at_l2_but_not_before(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)

    first = submit(client, headers, exercise, session_id, WRONG).json()
    assert first["hint"] is None  # L0/L1 are the test output, not a hint

    second = submit(client, headers, exercise, session_id, WRONG).json()
    assert second["hint_level"] >= 2
    assert second["hint"]


def test_exception_triggers_l1_immediately(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    body = submit(client, headers, exercise, session_id, BOOM).json()
    assert body["hint_level"] >= 1
    assert body["test_results"]["tests"][0]["error"]["type"] == "IndexError"


# --- the divergence rule ---------------------------------------------------


def test_divergence_is_flagged_when_client_and_server_disagree(client):
    """The browser says pass, the server says fail, on identical code.

    That is a platform fault. It must be recorded so the row can be excluded at
    analysis time, not silently shown to a student as their mistake.
    """
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)

    lying_client = {"passed": True, "summary": {"passed": 5, "total": 5}, "tests": []}
    submit(client, headers, exercise, session_id, WRONG, client_results=lying_client)

    with client.session_factory() as db:
        row = db.scalar(select(Submission))
        assert row.divergence_flag is True
        # The server's verdict still wins -- the client is never trusted to grade.
        assert row.passed is False


def test_agreeing_client_does_not_raise_a_false_alarm(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    honest = {"passed": True, "summary": {"passed": 5, "total": 5}, "tests": []}
    submit(client, headers, exercise, session_id, CORRECT, client_results=honest)

    with client.session_factory() as db:
        assert db.scalar(select(Submission)).divergence_flag is False


# --- sessions --------------------------------------------------------------


def test_reopening_an_exercise_resumes_the_same_session(client):
    """A page refresh must not reset the clock or fabricate a data point."""
    headers = login(client)
    _, first = open_exercise(client, headers)
    _, second = open_exercise(client, headers)
    assert first == second
