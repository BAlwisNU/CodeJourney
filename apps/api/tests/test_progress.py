"""Tests for the dashboard rollup.

The important ones here are the two absences: time-on-task and hint depth must
not appear in this response. Both are Week 7 dependent variables, and showing a
participant their own values changes the behaviour being measured.
"""

from conftest import CORRECT, WRONG, login, open_exercise, submit  # noqa: F401


def get_dashboard(client, headers) -> dict:
    response = client.get("/progress", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_requires_auth(client):
    assert client.get("/progress").status_code == 401


def test_fresh_account_shows_nothing_done_and_somewhere_to_start(client):
    headers = login(client)
    data = get_dashboard(client, headers)

    assert data["solved"] == 0
    assert data["total_attempts"] == 0
    # At least the seeded pair; don't hardcode the count -- the exercise library
    # grows, and a test that breaks every time content is added is noise.
    assert data["total_exercises"] >= 2
    assert all(e["status"] == "not_started" for e in data["exercises"])
    # A brand-new student must still be pointed somewhere, or the dashboard is a
    # dead end on the one visit where that matters most.
    assert data["continue_slug"] is not None


def test_solving_an_exercise_marks_it_solved(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)

    data = get_dashboard(client, headers)
    assert data["solved"] == 1
    themed = next(
        e for e in data["exercises"] if e["slug"] == "expired-quests"
    )
    assert themed["status"] == "solved"
    assert themed["attempts"] == 1


def test_failing_marks_in_progress_not_solved(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, WRONG)
    submit(client, headers, exercise, session_id, WRONG)

    data = get_dashboard(client, headers)
    assert data["solved"] == 0
    themed = next(
        e for e in data["exercises"] if e["slug"] == "expired-quests"
    )
    assert themed["status"] == "in_progress"
    assert themed["attempts"] == 2


def test_solved_stays_solved_after_a_later_failure(client):
    """Breaking it again afterwards must not un-solve it.

    Otherwise a student who returns to tinker with working code watches their
    own progress bar go backwards, which punishes exactly the curiosity the
    platform is trying to encourage.
    """
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)
    submit(client, headers, exercise, session_id, WRONG)

    data = get_dashboard(client, headers)
    themed = next(
        e for e in data["exercises"] if e["slug"] == "expired-quests"
    )
    assert themed["status"] == "solved"
    assert data["solved"] == 1


def test_runs_do_not_count_as_graded_attempts(client):
    """Pressing Run isn't a graded attempt -- but opening the lesson is a start.

    A Run doesn't add to the graded attempt count or solve anything. Opening the
    lesson (which `open_exercise` does) still marks it in progress, because the
    student has started it and left before finishing.
    """
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT, mode="run")

    data = get_dashboard(client, headers)
    assert data["total_attempts"] == 0
    assert data["solved"] == 0
    themed = next(
        e for e in data["exercises"] if e["slug"] == "expired-quests"
    )
    assert themed["status"] == "in_progress"


def test_opening_a_lesson_and_leaving_marks_it_in_progress(client):
    """Start it, leave before finishing -> in progress, with nothing submitted."""
    headers = login(client)
    exercise, _ = open_exercise(client, headers)  # opens a session, no submit

    data = get_dashboard(client, headers)
    themed = next(e for e in data["exercises"] if e["slug"] == "expired-quests")
    assert themed["status"] == "in_progress"
    assert themed["attempts"] == 0
    # And it becomes the place to carry on from.
    assert data["continue_slug"] == "expired-quests"


def test_continue_points_at_the_unfinished_one(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, WRONG)

    data = get_dashboard(client, headers)
    assert data["continue_slug"] == "expired-quests"


def test_continue_moves_on_once_solved(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)

    data = get_dashboard(client, headers)
    # Solved this one, so "continue" must point elsewhere -- not back to it.
    assert data["continue_slug"] is not None
    assert data["continue_slug"] != "expired-quests"


def test_continue_is_null_when_everything_is_done(client):
    """Solve the entire library, whatever its size, and there's nowhere left to go.

    Iterates over the real exercise list rather than a hardcoded pair, so it
    keeps testing the right thing as the content grows.
    """
    headers = login(client)
    all_exercises = client.get("/exercises", headers=headers).json()

    for summary in all_exercises:
        exercise, session_id = open_exercise(client, headers, summary["slug"])
        code = _reference_solution(exercise["slug"], exercise["entrypoint"])
        submit(client, headers, exercise, session_id, code)

    data = get_dashboard(client, headers)
    assert data["solved"] == len(all_exercises)
    assert data["continue_slug"] is None


def _reference_solution(slug: str, entrypoint: str) -> str:
    """A passing solution for any seeded exercise.

    Prefers the exercise's own co-located `_solution` (all the lesson content),
    falls back to the themed-games SOLUTIONS table, and handles the one inline
    generic twin. Keeps the "solve everything" test independent of how many
    exercises exist.
    """
    from app.content import ALL_EXERCISES
    from test_content import SOLUTIONS

    for spec in ALL_EXERCISES:
        if spec["slug"] == slug and spec.get("_solution"):
            return spec["_solution"]
    if slug in SOLUTIONS:
        return SOLUTIONS[slug]
    if slug == "filter-records-generic":
        return (
            "def filter_records(records, threshold):\n"
            "    return [r['name'] for r in records "
            "if r['due_day'] < threshold and not r['done']]\n"
        )
    return SOLUTIONS["expired-quests"].replace("expired_quests", entrypoint)


def test_concept_progress_aggregates(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)

    data = get_dashboard(client, headers)
    lists = next(c for c in data["concepts"] if c["concept"] == "lists")
    # One Lists exercise solved; the total is however many Lists exercises are
    # seeded (don't hardcode -- the library grows).
    assert lists["concept"] == "lists"
    assert lists["solved"] == 1
    assert lists["total"] >= 2


def test_dependent_variables_are_not_exposed_to_the_participant(client):
    """The load-bearing test in this file.

    time-on-task and hint depth are Week 7 dependent variables. Showing a
    participant their own values creates measurement reactivity -- someone who
    can see "you used hint 4" avoids hints next time, and someone watching a
    timer works differently than someone who isn't. If a future change adds
    either to this payload, the study's own instrument starts biasing it.
    """
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    for _ in range(3):
        submit(client, headers, exercise, session_id, WRONG)

    data = get_dashboard(client, headers)
    blob = str(data).lower()
    for banned in ("seconds", "hint", "time_on_task", "duration"):
        assert banned not in blob, f"dashboard leaked {banned!r} to the participant"


def test_one_students_work_does_not_show_up_for_another(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)

    other = client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "password": "password123",
            "display_name": "Other",
        },
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    data = get_dashboard(client, other_headers)
    assert data["solved"] == 0
    assert data["total_attempts"] == 0
    assert data["display_name"] == "Other"
