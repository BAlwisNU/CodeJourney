"""Projects: the organising unit of the product.

A learner arrives wanting to build something, not wanting to learn
dictionaries. These pin the two halves of that: what becomes a project, and
which lessons end up underneath one.
"""

from sqlalchemy import select

from app.models import Concept, Exercise, LearnerProject, OnboardingPlan, User
from conftest import CORRECT, login, open_exercise, submit  # noqa: F401


def _uid(client, email="student@example.com"):
    with client.session_factory() as db:
        return db.scalar(select(User.id).where(User.email == email))


def test_a_learner_with_no_plan_still_gets_projects(client):
    """Nobody lands on an empty page.

    The welcome chat is skippable and every account made before projects
    existed has no plan at all, so falling back to the starter set is what
    stops the main view being blank for most of the userbase.
    """
    headers = login(client)
    body = client.get("/projects", headers=headers).json()
    assert len(body["projects"]) == 3
    assert all(p["total"] > 0 for p in body["projects"]), "a project with no lessons is not a route"


def test_the_signup_plan_becomes_the_projects(client):
    """What someone said they wanted to build is what they get."""
    headers = login(client)
    with client.session_factory() as db:
        db.add(
            OnboardingPlan(
                user_id=_uid(client),
                interests="games",
                topics=["lists"],
                projects=[
                    {"title": "A dungeon crawler", "blurb": "Rooms and monsters.",
                     "topics": ["lists", "dicts"]},
                    # Invented topics are dropped, the project survives.
                    {"title": "A chat bot", "blurb": "", "topics": ["strings", "quantum"]},
                    # No usable topic at all -- no lessons to show, so no project.
                    {"title": "Nonsense", "blurb": "", "topics": ["quantum"]},
                ],
            )
        )
        db.commit()

    projects = client.get("/projects", headers=headers).json()["projects"]
    assert [p["title"] for p in projects] == ["A dungeon crawler", "A chat bot"]
    assert projects[0]["topics"] == ["lists", "dicts"]
    assert projects[1]["topics"] == ["strings"]


def test_lessons_follow_the_project_s_topic_order(client):
    """A project reads "first lists, then dictionaries", not library order."""
    headers = login(client)
    with client.session_factory() as db:
        db.add(
            OnboardingPlan(
                user_id=_uid(client), interests="", topics=[],
                projects=[{"title": "P", "blurb": "", "topics": ["dicts", "lists"]}],
            )
        )
        db.commit()

    lessons = client.get("/projects", headers=headers).json()["projects"][0]["lessons"]
    concepts = [l["concept"] for l in lessons]
    assert concepts == sorted(concepts, key=lambda c: ["dicts", "lists"].index(c))
    assert len(set(l["slug"] for l in lessons)) == len(lessons)
    # The whole curriculum for those two topics, not a handful. Filtering on
    # the variant alone once cut this to three.
    assert len(lessons) > 15, f"only {len(lessons)} lessons -- the filter is eating the library"
    # The study's control twin is the one thing dropped, and only because its
    # themed partner teaches the same concept.
    assert "filter-records-generic" not in [l["slug"] for l in lessons]
    assert "expired-quests" in [l["slug"] for l in lessons]


def test_solving_a_lesson_moves_the_project_on(client):
    headers = login(client)
    before = client.get("/projects", headers=headers).json()["projects"][0]
    assert before["done"] == 0
    assert before["next_slug"] is not None

    exercise, session_id = open_exercise(client, headers, "expired-quests")
    submit(client, headers, exercise, session_id, CORRECT)

    after = client.get("/projects", headers=headers).json()["projects"][0]
    assert after["done"] == 1
    assert after["next_slug"] != before["next_slug"]


def test_known_clears_a_lesson_without_claiming_it_was_done(client):
    """"I know this" must not become a solve in the dataset."""
    headers = login(client)
    project = client.get("/projects", headers=headers).json()["projects"][0]
    slug = project["next_slug"]

    assert client.put(
        f"/projects/lessons/{slug}/known", headers=headers, json={"known": True}
    ).status_code == 204

    after = client.get("/projects", headers=headers).json()["projects"][0]
    marked = next(l for l in after["lessons"] if l["slug"] == slug)
    assert marked["status"] == "known"
    assert after["done"] == 1
    # And it is reversible.
    client.put(f"/projects/lessons/{slug}/known", headers=headers, json={"known": False})
    back = client.get("/projects", headers=headers).json()["projects"][0]
    assert next(l for l in back["lessons"] if l["slug"] == slug)["status"] == "not_started"


def test_building_is_separate_from_finishing_the_lessons(client):
    headers = login(client)
    project = client.get("/projects", headers=headers).json()["projects"][0]
    assert project["built"] is False
    res = client.patch(
        f"/projects/{project['id']}/built", headers=headers, json={"built": True}
    )
    assert res.status_code == 200 and res.json()["built"] is True


def test_starting_a_new_project(client):
    headers = login(client)
    res = client.post(
        "/projects",
        headers=headers,
        json={"title": "A Discord bot", "blurb": "Replies to my friends.",
              "topics": ["strings", "not_a_topic"]},
    )
    assert res.status_code == 201
    assert res.json()["topics"] == ["strings"]
    assert res.json()["total"] > 0
    # A project with nothing behind it is refused rather than created empty.
    assert client.post(
        "/projects", headers=headers, json={"title": "X", "topics": ["not_a_topic"]}
    ).status_code == 422


def test_a_lesson_knows_which_projects_want_it(client):
    """What the lesson page uses to say why it is asking you to learn this."""
    headers = login(client)
    client.get("/projects", headers=headers)
    with client.session_factory() as db:
        slug = db.scalar(
            select(Exercise.slug).where(Exercise.concept == Concept.LISTS)
        )
    body = client.get(f"/projects/for-lesson/{slug}", headers=headers).json()
    assert body["projects"], "the starter set includes lists, so something should want it"
    assert all("lists" in p["topics"] for p in body["projects"])


def test_projects_are_private(client):
    headers = login(client)
    mine = client.get("/projects", headers=headers).json()["projects"][0]
    other = login(client, email="instructor@example.com")
    assert client.patch(
        f"/projects/{mine['id']}/built", headers=other, json={"built": True}
    ).status_code == 404


def test_projects_require_auth(client):
    assert client.get("/projects").status_code == 401
