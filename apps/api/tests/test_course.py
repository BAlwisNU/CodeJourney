"""Courses written for one project, and the chat that replaced the signup form.

Nothing here calls a model. The generation itself is covered by the fact that
`generate_exercise` proves every lesson against the real harness before it is
stored -- what these test is the machinery around it: who may build a course,
what happens to a project once it has one, and that a conversation writes the
same two rows the form used to.
"""

from app.models import (
    Concept,
    Exercise,
    LearnerIntake,
    LearnerProfile,
    LearnerProject,
    ProjectCourseLesson,
    Theme,
    ThemeVariant,
)
from app.routers.onboarding import _record_profile
from app.services import projects as svc
from app.services import tutor
from conftest import login


def make_project(client, headers, title="A tracker for my runs"):
    response = client.post(
        "/projects",
        headers=headers,
        json={"title": title, "blurb": "Log runs and work out paces.", "topics": ["lists"]},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def register(client, email="course@example.com"):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Cy"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---------------------------------------------------------------------------
# The conversation writes what the form used to
# ---------------------------------------------------------------------------


def test_the_chat_fills_in_the_rows_the_signup_form_used_to(client):
    """Everything downstream reads LearnerProfile and LearnerIntake. The form
    is gone, so the conversation has to write them, and nothing else may need
    to know which one produced the answer."""
    headers = login(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    with client.session_factory() as db:
        _record_profile(
            user_id,
            {
                "goals": "Stop keeping my times in a notebook",
                "experience": "none",
                "learn_style": "do",
                "time_available": "hour",
                "worries": ["maths", "stuck"],
                "interests": "Runs a lot, wants to track it",
            },
            db,
        )
        db.commit()

        profile = db.get(LearnerProfile, user_id)
        intake = db.get(LearnerIntake, user_id)
        assert profile.goals == "Stop keeping my times in a notebook"
        assert profile.experience == "none"
        assert intake.learn_style == "do"
        assert intake.time_available == "hour"
        assert set(intake.worries.split(",")) == {"maths", "stuck"}


def test_a_later_turn_cannot_blank_what_an_earlier_one_heard(client):
    """A conversation records as it goes, and the model is not obliged to
    repeat everything each time. Overwriting turn two's answer with turn
    five's silence would quietly lose it."""
    headers = login(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    with client.session_factory() as db:
        _record_profile(user_id, {"goals": "Build a run tracker", "experience": "none"}, db)
        db.commit()
        # A later call that only learned the learning style.
        _record_profile(user_id, {"learn_style": "do"}, db)
        db.commit()

        profile = db.get(LearnerProfile, user_id)
        assert profile.goals == "Build a run tracker"
        assert profile.experience == "none"
        assert db.get(LearnerIntake, user_id).learn_style == "do"


def test_an_invented_option_is_dropped_rather_than_stored(client):
    """The tool schema constrains these, but a model can still return
    something outside it, and an unknown key renders as a blank on the
    account page."""
    headers = login(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    with client.session_factory() as db:
        _record_profile(
            user_id,
            {"experience": "wizard", "learn_style": "osmosis", "worries": ["dragons"]},
            db,
        )
        db.commit()
        profile = db.get(LearnerProfile, user_id)
        intake = db.get(LearnerIntake, user_id)
        assert profile.experience in ("", None)
        assert intake is None or intake.learn_style in ("", None)


# ---------------------------------------------------------------------------
# The course itself
# ---------------------------------------------------------------------------


def test_building_a_course_is_refused_when_the_tutor_is_off(client, monkeypatch):
    """No API key means no lesson writing, and a friendly 503 rather than a
    stack trace -- the same posture as every other model-backed feature."""
    monkeypatch.setattr(tutor, "enabled", lambda: False)
    headers = register(client)
    project_id = make_project(client, headers)
    response = client.post(f"/projects/{project_id}/course/stream", headers=headers)
    assert response.status_code == 503
    assert "isn't switched on" in response.json()["detail"]


def test_a_course_cannot_be_built_for_someone_elses_project(client, monkeypatch):
    monkeypatch.setattr(tutor, "enabled", lambda: False)
    mine = register(client, "mine@example.com")
    theirs = register(client, "theirs@example.com")
    project_id = make_project(client, mine)
    assert (
        client.post(f"/projects/{project_id}/course/stream", headers=theirs).status_code
        == 404
    )


def _attach_course(db, project_id, user_id, titles):
    """Stand in for the generator: real Exercise rows, linked in order."""
    made = []
    for index, title in enumerate(titles):
        exercise = Exercise(
            slug=f"ai-lists-{index}-{user_id[:6]}",
            title=title,
            theme=Theme.GENERIC,
            concept=Concept.LISTS,
            variant=ThemeVariant.GENERIC,
            pair_id=f"ai-lists-{index}-{user_id[:6]}",
            entrypoint="f",
            prompt_md="x",
            starter_code="def f():\n    pass\n",
            tests=[{"name": "t", "args": [], "expected": None, "hidden": False}],
            created_by_user_id=user_id,
            order_index=9000 + index,
        )
        db.add(exercise)
        db.flush()
        db.add(
            ProjectCourseLesson(
                project_id=project_id, exercise_id=exercise.id, order_index=index
            )
        )
        made.append(exercise.id)
    db.commit()
    return made


def test_a_course_replaces_the_library_route_and_keeps_its_order(client):
    """The point of a written course is that it teaches these ideas *in this
    project*. Showing it alongside the generic lessons would offer the same
    concepts twice and bury the bespoke set under the borrowed one."""
    headers = register(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    project_id = make_project(client, headers)

    before = client.get("/projects", headers=headers).json()["projects"]
    mine_before = next(p for p in before if p["id"] == project_id)
    assert mine_before["has_course"] is False
    assert mine_before["total"] > 5, "should be showing the library's lists lessons"

    titles = ["Keep a list of distances", "Total miles", "Longest run", "Best week"]
    with client.session_factory() as db:
        _attach_course(db, project_id, user_id, titles)

    after = client.get("/projects", headers=headers).json()["projects"]
    mine = next(p for p in after if p["id"] == project_id)
    assert mine["has_course"] is True
    assert [lesson["title"] for lesson in mine["lessons"]] == titles


def test_rebuilding_is_refused_until_the_old_course_is_deleted(client, monkeypatch):
    # Guarded before generation starts, but never let a test reach a model:
    # a fall-through here would spend real minutes and real money.
    monkeypatch.setattr(tutor, "enabled", lambda: False)
    headers = register(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    project_id = make_project(client, headers)
    with client.session_factory() as db:
        _attach_course(db, project_id, user_id, ["One", "Two", "Three", "Four"])

    assert (
        client.post(f"/projects/{project_id}/course/stream", headers=headers).status_code
        == 409
    )


def test_deleting_a_course_takes_its_lessons_with_it(client):
    """The generated exercises exist only for this project. Unlinking without
    deleting them would leave orphans on the learner's dashboard with nothing
    pointing at them."""
    headers = register(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    project_id = make_project(client, headers)
    with client.session_factory() as db:
        made = _attach_course(db, project_id, user_id, ["One", "Two", "Three", "Four"])

    assert client.delete(f"/projects/{project_id}/course", headers=headers).status_code == 204

    with client.session_factory() as db:
        assert svc.course_for(project_id, db) == []
        for exercise_id in made:
            assert db.get(Exercise, exercise_id) is None
        # The project itself survives, and falls back to the library.
        assert db.get(LearnerProject, project_id) is not None

    back = client.get("/projects", headers=headers).json()["projects"]
    mine = next(p for p in back if p["id"] == project_id)
    assert mine["has_course"] is False
    assert mine["total"] > 5


def test_deleting_a_course_never_touches_the_taught_curriculum(client):
    """A generated lesson has an author; the shared library does not. Only the
    former may be deleted."""
    headers = register(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    project_id = make_project(client, headers)

    with client.session_factory() as db:
        shared = db.query(Exercise).filter(Exercise.created_by_user_id.is_(None)).first()
        db.add(
            ProjectCourseLesson(
                project_id=project_id, exercise_id=shared.id, order_index=0
            )
        )
        db.commit()
        shared_id = shared.id

    client.delete(f"/projects/{project_id}/course", headers=headers)
    with client.session_factory() as db:
        assert db.get(Exercise, shared_id) is not None
