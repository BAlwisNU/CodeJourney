"""Step three of signing up: the welcome conversation.

The model is stubbed everywhere. What is exercised for real is the part that
would actually hurt if it broke: the conversation surviving a reload, the plan
being sanitised before it is stored, and the whole step standing down cleanly
when no API key is configured -- a signup flow that dead-ends on missing
configuration loses the account, not just the message.
"""

import pytest

from app.models import OnboardingMessage, OnboardingPlan
from app.services import tutor

from conftest import login


@pytest.fixture
def tutor_on(monkeypatch):
    """Pretend an API key is set, without ever calling one."""
    monkeypatch.setattr(tutor, "enabled", lambda: True)


@pytest.fixture
def tutor_off(monkeypatch):
    """Force the tutor off.

    Not the default: pydantic-settings reads apps/api/.env, so a developer with
    a real ANTHROPIC_API_KEY runs the suite with the tutor switched ON. These
    two tests are about the no-key path, so they have to say so rather than
    assume -- otherwise they pass on CI and quietly do nothing on a laptop.
    """
    monkeypatch.setattr(tutor, "enabled", lambda: False)


def _reply(monkeypatch, text="Tell me more.", plan=None):
    def fake(learner, history):
        return text, plan

    monkeypatch.setattr(tutor, "welcome_chat", fake)


# --- standing down ----------------------------------------------------------


def test_the_step_reports_itself_unavailable_without_a_key(client, tutor_off):
    """No key: the page shows a note and a way onward, not a dead chat box."""
    body = client.get("/onboarding/welcome", headers=login(client)).json()
    assert body["available"] is False
    # The greeting is still sent -- it costs nothing and the page may show it.
    assert body["greeting"]
    assert body["messages"] == []
    assert body["plan"]["recorded"] is False


def test_chatting_without_a_key_is_refused_cleanly(client, tutor_off):
    response = client.post(
        "/onboarding/welcome/chat", headers=login(client), json={"message": "hi"}
    )
    assert response.status_code == 503
    assert "isn't set up" in response.json()["detail"]


def test_the_endpoints_need_a_login(client):
    assert client.get("/onboarding/welcome").status_code == 401
    assert client.post("/onboarding/welcome/chat", json={"message": "x"}).status_code == 401
    assert client.get("/onboarding/plan").status_code == 401


# --- the conversation -------------------------------------------------------


def test_a_turn_saves_both_sides(client, tutor_on, monkeypatch):
    _reply(monkeypatch, "What sort of games?")
    headers = login(client)

    body = client.post(
        "/onboarding/welcome/chat", headers=headers, json={"message": "I like games"}
    ).json()
    assert body["reply"] == "What sort of games?"

    with client.session_factory() as db:
        rows = db.query(OnboardingMessage).order_by(OnboardingMessage.created_at).all()
        assert [(r.role, r.content) for r in rows] == [
            ("user", "I like games"),
            ("assistant", "What sort of games?"),
        ]


def test_the_conversation_survives_a_reload(client, tutor_on, monkeypatch):
    """Closing the tab mid-signup must not throw the conversation away."""
    _reply(monkeypatch, "Go on.")
    headers = login(client)
    client.post("/onboarding/welcome/chat", headers=headers, json={"message": "hello"})

    body = client.get("/onboarding/welcome", headers=headers).json()
    assert [m["content"] for m in body["messages"]] == ["hello", "Go on."]


def test_history_is_passed_back_to_the_model(client, tutor_on, monkeypatch):
    """Without this the mentor would forget everything after each message."""
    seen: list[list[dict]] = []

    def fake(learner, history):
        seen.append(list(history))
        return "ok", None

    monkeypatch.setattr(tutor, "welcome_chat", fake)
    headers = login(client)
    client.post("/onboarding/welcome/chat", headers=headers, json={"message": "one"})
    client.post("/onboarding/welcome/chat", headers=headers, json={"message": "two"})

    assert seen[0] == [{"role": "user", "content": "one"}]
    assert seen[1] == [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "two"},
    ]


def test_the_model_is_told_what_they_said_on_the_form(client, tutor_on, monkeypatch):
    """Otherwise its first question asks what they just finished answering."""
    headers = login(client)
    client.patch(
        "/auth/me/profile",
        headers=headers,
        json={"goals": "Automate my spreadsheets", "experience": "rusty"},
    )

    seen = {}

    def fake(learner, history):
        seen["learner"] = learner
        return "ok", None

    monkeypatch.setattr(tutor, "welcome_chat", fake)
    client.post("/onboarding/welcome/chat", headers=headers, json={"message": "hi"})

    brief = seen["learner"]
    assert brief is not None
    assert brief.goals == "Automate my spreadsheets"
    # The label, not the stored key.
    assert brief.experience == "Learnt some once, but it's rusty"


def test_a_very_long_conversation_is_stopped_politely(client, tutor_on, monkeypatch):
    _reply(monkeypatch)
    headers = login(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    with client.session_factory() as db:
        for i in range(40):
            db.add(OnboardingMessage(user_id=user_id, role="user", content=f"m{i}"))
        db.commit()

    response = client.post(
        "/onboarding/welcome/chat", headers=headers, json={"message": "more"}
    )
    assert response.status_code == 409
    assert "let's get you started" in response.json()["detail"]


# --- the plan ---------------------------------------------------------------


PLAN = {
    "interests": "Runs a lot, wants to track it",
    "topics": ["lists", "file_io"],
    "projects": [
        {
            "title": "Running log",
            "blurb": "Read your times from a file and work out your averages.",
            "topics": ["file_io", "lists"],
        }
    ],
}


def test_a_recorded_plan_is_saved_and_returned(client, tutor_on, monkeypatch):
    _reply(monkeypatch, "Here's an idea.", PLAN)
    headers = login(client)

    body = client.post(
        "/onboarding/welcome/chat", headers=headers, json={"message": "I run"}
    ).json()
    assert body["plan"]["recorded"] is True
    assert body["plan"]["topics"] == ["lists", "file_io"]
    assert body["plan"]["projects"][0]["title"] == "Running log"

    # And it is theirs to read later, from the account page.
    later = client.get("/onboarding/plan", headers=headers).json()
    assert later["interests"] == "Runs a lot, wants to track it"


def test_a_second_plan_replaces_the_first(client, tutor_on, monkeypatch):
    """The conversation can move on; the newest reading wins."""
    headers = login(client)
    _reply(monkeypatch, "ok", PLAN)
    client.post("/onboarding/welcome/chat", headers=headers, json={"message": "a"})

    _reply(
        monkeypatch,
        "ok",
        {"interests": "Actually into music", "topics": ["dicts"], "projects": []},
    )
    client.post("/onboarding/welcome/chat", headers=headers, json={"message": "b"})

    with client.session_factory() as db:
        assert db.query(OnboardingPlan).count() == 1
        plan = db.query(OnboardingPlan).one()
        assert plan.interests == "Actually into music"
        assert plan.topics == ["dicts"]


def test_invented_topics_are_dropped(client, tutor_on, monkeypatch):
    """A model can return a topic outside the enum despite the tool schema.

    An unknown key would render as a topic this platform does not teach --
    advertising something that does not exist, which is the one thing the
    landing page is careful never to do.
    """
    _reply(
        monkeypatch,
        "ok",
        {
            "interests": "Curious",
            "topics": ["lists", "machine_learning", "blockchain"],
            "projects": [
                {"title": "Thing", "blurb": "Does stuff", "topics": ["quantum", "dicts"]}
            ],
        },
    )
    headers = login(client)
    body = client.post(
        "/onboarding/welcome/chat", headers=headers, json={"message": "hi"}
    ).json()

    assert body["plan"]["topics"] == ["lists"]
    assert body["plan"]["projects"][0]["topics"] == ["dicts"]


def test_a_nameless_project_is_dropped(client, tutor_on, monkeypatch):
    _reply(
        monkeypatch,
        "ok",
        {
            "interests": "",
            "topics": [],
            "projects": [
                {"title": "", "blurb": "no name", "topics": []},
                {"title": "Real one", "blurb": "has a name", "topics": []},
            ],
        },
    )
    headers = login(client)
    body = client.post(
        "/onboarding/welcome/chat", headers=headers, json={"message": "hi"}
    ).json()
    assert [p["title"] for p in body["plan"]["projects"]] == ["Real one"]


def test_a_turn_without_a_plan_leaves_the_previous_one(client, tutor_on, monkeypatch):
    """Most turns record nothing; that must not wipe what's there."""
    headers = login(client)
    _reply(monkeypatch, "ok", PLAN)
    client.post("/onboarding/welcome/chat", headers=headers, json={"message": "a"})

    _reply(monkeypatch, "just chatting", None)
    body = client.post(
        "/onboarding/welcome/chat", headers=headers, json={"message": "b"}
    ).json()
    assert body["plan"]["interests"] == "Runs a lot, wants to track it"


def test_one_persons_plan_is_not_anothers(client, tutor_on, monkeypatch):
    _reply(monkeypatch, "ok", PLAN)
    client.post("/onboarding/welcome/chat", headers=login(client), json={"message": "a"})

    instructor = login(client, "instructor@example.com", "password123")
    assert client.get("/onboarding/plan", headers=instructor).json()["recorded"] is False


# --- what the model is told -------------------------------------------------


def test_the_mentor_is_told_to_ask_one_question_at_a_time():
    """A list of questions in a first conversation is an interrogation."""
    assert "ONE question at a time" in tutor._WELCOME_SYSTEM


def test_the_mentor_may_only_suggest_topics_that_exist():
    from app.models import Concept

    schema = tutor._RECORD_PLAN_TOOL["input_schema"]["properties"]
    assert schema["topics"]["items"]["enum"] == [c.value for c in Concept]
