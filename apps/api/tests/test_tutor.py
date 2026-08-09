"""The reflection tutor.

The tutor is the one place an LLM touches the platform, so these tests guard the
two things that must not slip:

  1. It NEVER sees the private journal. This is the same guarantee
     reflections.py exists to keep -- here it's checked at the tutor's own door.
  2. Every exercise it builds is proven solvable through the real harness before
     a student can open it. A tutor that hands a beginner a broken exercise does
     the opposite of helping.

The model itself is never called over the network here: the chat client is
faked and the generator's model step is monkeypatched, so the tests exercise the
routing, the context boundary, and the harness verification -- the parts that are
ours to get right.
"""

import json
from types import SimpleNamespace

import pytest
from conftest import CORRECT, WRONG, login, open_exercise, submit  # noqa: F401

from app.services import tutor


def _exercise_id(client, headers, slug="expired-quests") -> str:
    return client.get(f"/exercises/{slug}", headers=headers).json()["id"]


# --- the switched-off state is complete, not broken ------------------------


def test_chat_when_off_is_friendly_and_flagged(client, monkeypatch):
    monkeypatch.setattr(tutor, "enabled", lambda: False)
    headers = login(client)
    ex_id = _exercise_id(client, headers)

    res = client.post(
        "/tutor/chat",
        headers=headers,
        json={"exercise_id": ex_id, "message": "hi"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["configured"] is False
    assert body["proposal"] is None
    assert body["reply"]  # a real, human message, not an empty string


def test_lesson_when_off_refuses_gently(client, monkeypatch):
    monkeypatch.setattr(tutor, "enabled", lambda: False)
    headers = login(client)
    res = client.post(
        "/tutor/lesson",
        headers=headers,
        json={
            "concept": "functions",
            "focus": "returning values",
            "title": "Practice",
            "parent_exercise_id": _exercise_id(client, headers),
        },
    )
    assert res.status_code == 503


def test_chat_requires_auth(client):
    assert client.post("/tutor/chat", json={"exercise_id": "x", "message": "hi"}).status_code == 401


# --- a fake model, so we can test routing and the journal boundary ---------


class _FakeMessages:
    def __init__(self, blocks, capture):
        self._blocks = blocks
        self._capture = capture

    def create(self, **kwargs):
        self._capture.update(kwargs)
        return SimpleNamespace(content=self._blocks)


class _FakeClient:
    def __init__(self, blocks, capture):
        self.messages = _FakeMessages(blocks, capture)


def _text_block(text):
    return SimpleNamespace(type="text", text=text)


def _tool_block(name, data):
    return SimpleNamespace(type="tool_use", name=name, input=data)


def test_chat_parses_text_and_a_lesson_offer(client, monkeypatch):
    capture: dict = {}
    blocks = [
        _text_block("Nice work getting that! How secure do you feel on loops?"),
        _tool_block(
            "propose_lesson",
            {
                "scope": "concept",
                "concept": "loops",
                "focus": "the off-by-one on the last item",
                "title": "One more loop",
                "rationale": "You slipped on the boundary twice.",
            },
        ),
    ]
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(tutor, "_client", lambda: _FakeClient(blocks, capture))

    headers = login(client)
    ex_id = _exercise_id(client, headers)
    res = client.post(
        "/tutor/chat",
        headers=headers,
        json={
            "exercise_id": ex_id,
            "message": "it was hard",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert "secure" in body["reply"]
    assert body["proposal"]["scope"] == "concept"
    assert body["proposal"]["concept"] == "loops"
    assert body["configured"] is True


def test_tutor_never_receives_the_private_journal(client, monkeypatch):
    """The load-bearing test. What a student writes in the journal must never
    reach the model, even though the tutor lives on the same page."""
    capture: dict = {}
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(
        tutor, "_client", lambda: _FakeClient([_text_block("hello")], capture)
    )

    headers = login(client)
    ex_id = _exercise_id(client, headers)

    secret = "MY-DEEPLY-PERSONAL-STRUGGLE-42"
    saved = client.post(
        "/reflections",
        headers=headers,
        json={
            "exercise_id": ex_id,
            "what_i_tried": secret,
            "where_i_got_stuck": secret,
            "how_i_fixed_it": secret,
        },
    )
    assert saved.status_code == 201

    client.post(
        "/tutor/chat",
        headers=headers,
        json={"exercise_id": ex_id, "message": "hi"},
    )

    # Everything the model was sent, stringified: system prompt + messages.
    sent = json.dumps({"system": capture.get("system"), "messages": capture.get("messages")})
    assert secret not in sent, "the private journal leaked into the tutor prompt"


def test_tutor_context_includes_the_students_own_code(client, monkeypatch):
    """It DOES see the code they wrote and ran -- that's the point -- so the
    context boundary is 'no journal', not 'no student text at all'."""
    capture: dict = {}
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(
        tutor, "_client", lambda: _FakeClient([_text_block("hi")], capture)
    )

    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)
    ex_id = exercise["id"]

    client.post(
        "/tutor/chat",
        headers=headers,
        json={"exercise_id": ex_id, "message": "hi"},
    )
    assert "expired_quests" in capture.get("system", "")


# --- the chat is saved and comes back exactly as it was --------------------


def test_chat_is_saved_and_reloads(client, monkeypatch):
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(
        tutor, "_client", lambda: _FakeClient([_text_block("Good question!")], {})
    )
    headers = login(client)
    ex_id = _exercise_id(client, headers)

    # Empty to begin with.
    assert client.get(f"/tutor/history?exercise_id={ex_id}", headers=headers).json() == []

    client.post("/tutor/chat", headers=headers, json={"exercise_id": ex_id, "message": "why lists?"})

    # The turn is persisted -- the user's message and the reply, in order.
    hist = client.get(f"/tutor/history?exercise_id={ex_id}", headers=headers).json()
    assert [(m["role"], m["content"]) for m in hist] == [
        ("user", "why lists?"),
        ("assistant", "Good question!"),
    ]

    # A second turn appends rather than replacing -- the conversation grows.
    client.post("/tutor/chat", headers=headers, json={"exercise_id": ex_id, "message": "and loops?"})
    hist2 = client.get(f"/tutor/history?exercise_id={ex_id}", headers=headers).json()
    assert len(hist2) == 4
    assert hist2[2]["content"] == "and loops?"


def test_saved_chat_is_private_and_per_exercise(client, monkeypatch):
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(tutor, "_client", lambda: _FakeClient([_text_block("ok")], {}))
    headers = login(client)
    ex_id = _exercise_id(client, headers)
    other_id = _exercise_id(client, headers, "filter-records-generic")

    client.post("/tutor/chat", headers=headers, json={"exercise_id": ex_id, "message": "hello"})

    # A different lesson has its own, separate history.
    assert client.get(f"/tutor/history?exercise_id={other_id}", headers=headers).json() == []

    # Another student never sees this conversation.
    other = client.post(
        "/auth/register",
        json={"email": "c@example.com", "password": "password123", "display_name": "C"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert client.get(f"/tutor/history?exercise_id={ex_id}", headers=other_headers).json() == []


def test_off_tutor_saves_nothing(client, monkeypatch):
    monkeypatch.setattr(tutor, "enabled", lambda: False)
    headers = login(client)
    ex_id = _exercise_id(client, headers)
    client.post("/tutor/chat", headers=headers, json={"exercise_id": ex_id, "message": "hi"})
    # A switched-off tutor returns a canned note but persists no conversation.
    assert client.get(f"/tutor/history?exercise_id={ex_id}", headers=headers).json() == []


# --- generation is verified through the real harness -----------------------

_GOOD_SPEC = {
    "title": "Add two numbers",
    "entrypoint": "add",
    "prompt_md": "Write `add(a, b)` that returns their sum.",
    "starter_code": "def add(a, b):\n    # your code here\n    pass\n",
    "reference_solution": "def add(a, b):\n    return a + b\n",
    "hint_l2": "Look at the return line.",
    "hint_l3": "You need the + operator.",
    "hint_l4": "return a + b",
    "tests_json": json.dumps(
        [
            {"name": "positives", "args": [2, 3], "expected": 5, "hidden": False},
            {"name": "with a negative", "args": [-1, 1], "expected": 0, "hidden": False},
            {"name": "zeros", "args": [0, 0], "expected": 0, "hidden": True},
        ]
    ),
}


def test_generated_exercise_is_verified_and_openable(client, monkeypatch):
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(tutor, "_ask_model", lambda *a, **k: dict(_GOOD_SPEC))

    headers = login(client)
    parent_id = _exercise_id(client, headers)
    res = client.post(
        "/tutor/lesson",
        headers=headers,
        json={
            "concept": "functions",
            "focus": "returning a sum",
            "title": "Add",
            "parent_exercise_id": parent_id,
        },
    )
    assert res.status_code == 201
    slug = res.json()["slug"]
    assert slug.startswith("ai-")

    # The student can actually open it, and its own reference solution passes --
    # the whole promise of pre-verification.
    fetched = client.get(f"/exercises/{slug}", headers=headers)
    assert fetched.status_code == 200
    exercise, session_id = open_exercise(client, headers, slug)
    verdict = submit(
        client, headers, exercise, session_id, _GOOD_SPEC["reference_solution"]
    ).json()
    assert verdict["passed"] is True

    # The branch is linked to its parent and reachable from it.
    branches = client.get("/exercises/expired-quests/branches", headers=headers)
    assert branches.status_code == 200
    assert any(b["slug"] == slug for b in branches.json())


def _make_branch(client, headers, monkeypatch, parent_slug="expired-quests"):
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(tutor, "_ask_model", lambda *a, **k: dict(_GOOD_SPEC))
    parent_id = _exercise_id(client, headers, parent_slug)
    res = client.post(
        "/tutor/lesson",
        headers=headers,
        json={
            "concept": "functions",
            "focus": "returning a sum",
            "title": "Add practice",
            "parent_exercise_id": parent_id,
        },
    )
    assert res.status_code == 201
    return res.json()["slug"]


def test_a_branch_is_private_to_its_owner(client, monkeypatch):
    headers = login(client)
    slug = _make_branch(client, headers, monkeypatch)

    # A second student must not see someone else's generated lesson anywhere.
    other = client.post(
        "/auth/register",
        json={"email": "b@example.com", "password": "password123", "display_name": "B"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    assert slug in {e["slug"] for e in client.get("/exercises", headers=headers).json()}
    assert slug not in {
        e["slug"] for e in client.get("/exercises", headers=other_headers).json()
    }
    assert client.get(f"/exercises/{slug}", headers=other_headers).status_code == 404


def test_a_branch_shows_in_the_dashboard_under_its_parent(client, monkeypatch):
    headers = login(client)
    slug = _make_branch(client, headers, monkeypatch)

    dash = client.get("/progress", headers=headers).json()
    branch = next(b for b in dash["branches"] if b["slug"] == slug)
    assert branch["parent_slug"] == "expired-quests"
    assert branch["title"] == _GOOD_SPEC["title"]  # the generated title
    assert branch["status"] == "not_started"


def test_generating_from_a_missing_parent_is_rejected(client, monkeypatch):
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(tutor, "_ask_model", lambda *a, **k: dict(_GOOD_SPEC))
    headers = login(client)
    res = client.post(
        "/tutor/lesson",
        headers=headers,
        json={
            "concept": "functions",
            "focus": "x",
            "title": "Add",
            "parent_exercise_id": "no-such-exercise",
        },
    )
    assert res.status_code == 404


def test_generation_rejects_an_unsolvable_exercise(client, monkeypatch):
    """If the model's own reference solution fails the tests, the student must
    never see it -- they get an apology, not a broken exercise."""
    broken = dict(_GOOD_SPEC, reference_solution="def add(a, b):\n    return a - b\n")
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(tutor, "_ask_model", lambda *a, **k: dict(broken))

    headers = login(client)
    res = client.post(
        "/tutor/lesson",
        headers=headers,
        json={
            "concept": "functions",
            "focus": "x",
            "title": "Add",
            "parent_exercise_id": _exercise_id(client, headers),
        },
    )
    assert res.status_code == 502


def test_generation_rejects_tests_that_dont_survive_json():
    """The int-keyed-dict trap, caught before it can reach a student."""
    bad = json.dumps(
        [
            {"name": "a", "args": [1], "expected": 1, "hidden": False},
            {"name": "b", "args": [2], "expected": 2, "hidden": False},
            {"name": "c", "args": [3], "expected": 3, "hidden": False},
        ]
    )
    # Valid case parses fine.
    assert len(tutor._validate_tests(bad)) == 3

    # A dict with a non-string key does not round-trip through JSON.
    int_keyed = '[{"name": "x", "args": [], "expected": {"1": "a"}, "hidden": false}]'
    # (JSON can't even express int keys, so simulate the post-load mismatch via
    # the round-trip helper directly.)
    assert tutor._round_trips({1: "a"}) is False
    assert tutor._round_trips({"1": "a"}) is True

    with pytest.raises(tutor.GenerationError):
        tutor._validate_tests('[{"name": "x", "args": [], "expected": 1, "hidden": false}]')  # too few


# --- "show me the answer" --------------------------------------------------

_EXPIRED_QUESTS_ANSWER = (
    "def expired_quests(quests, today):\n"
    '    return [q["name"] for q in quests '
    'if q["due_day"] < today and not q["done"]]\n'
)


def _earn_the_answer(client, headers, slug="expired-quests"):
    """Submit enough wrong attempts to unlock the worked answer.

    The endpoint is gated on real submits -- see ANSWER_AFTER_ATTEMPTS in
    routers/exercises.py -- because handing the answer over on request
    contradicted the promise on the landing page and made the hint ladder
    skippable in one click.
    """
    from app.routers.exercises import ANSWER_AFTER_ATTEMPTS

    exercise, session_id = open_exercise(client, headers, slug)
    for _ in range(ANSWER_AFTER_ATTEMPTS):
        submit(client, headers, exercise, session_id, WRONG)


def test_show_answer_when_off_refuses_gently(client, monkeypatch):
    monkeypatch.setattr(tutor, "enabled", lambda: False)
    headers = login(client)
    _earn_the_answer(client, headers)
    res = client.get("/exercises/expired-quests/solution", headers=headers)
    assert res.status_code == 503


def test_show_answer_returns_a_verified_solution(client, monkeypatch):
    """The answer is run through the real harness before it's returned, so what
    the student sees actually passes the tests -- including the hidden ones."""
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(
        tutor, "_client", lambda: _FakeClient([_text_block(_EXPIRED_QUESTS_ANSWER)], {})
    )
    tutor._SOLUTION_CACHE.clear()

    headers = login(client)
    _earn_the_answer(client, headers)
    res = client.get("/exercises/expired-quests/solution", headers=headers)
    assert res.status_code == 200
    assert "def expired_quests" in res.json()["solution"]


def test_show_answer_strips_markdown_fences(client, monkeypatch):
    fenced = "```python\n" + _EXPIRED_QUESTS_ANSWER + "```"
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(tutor, "_client", lambda: _FakeClient([_text_block(fenced)], {}))
    tutor._SOLUTION_CACHE.clear()

    headers = login(client)
    _earn_the_answer(client, headers)
    res = client.get("/exercises/expired-quests/solution", headers=headers)
    assert res.status_code == 200
    sol = res.json()["solution"]
    assert "```" not in sol
    assert sol.startswith("def expired_quests")


def test_show_answer_rejects_a_wrong_solution(client, monkeypatch):
    """If the model's answer doesn't pass the tests, the student never sees it."""
    wrong = "def expired_quests(quests, today):\n    return []\n"
    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(tutor, "_client", lambda: _FakeClient([_text_block(wrong)], {}))
    tutor._SOLUTION_CACHE.clear()

    headers = login(client)
    _earn_the_answer(client, headers)
    res = client.get("/exercises/expired-quests/solution", headers=headers)
    assert res.status_code == 502


def test_show_answer_requires_auth(client):
    assert client.get("/exercises/expired-quests/solution").status_code == 401


def test_show_answer_is_gated_on_having_tried(client, monkeypatch):
    """The landing page promises the answer is not handed over. It has to be true.

    Before this the endpoint answered any signed-in student from the moment
    the page loaded, which made the whole hint ladder skippable in one click
    and the promise false.
    """
    from app.routers.exercises import ANSWER_AFTER_ATTEMPTS

    monkeypatch.setattr(tutor, "enabled", lambda: True)
    monkeypatch.setattr(
        tutor, "_client", lambda: _FakeClient([_text_block(_EXPIRED_QUESTS_ANSWER)], {})
    )
    tutor._SOLUTION_CACHE.clear()
    headers = login(client)

    # Cold: refused, and the refusal says what to do about it.
    res = client.get("/exercises/expired-quests/solution", headers=headers)
    assert res.status_code == 403
    assert str(ANSWER_AFTER_ATTEMPTS) in res.json()["detail"]

    # One short of the threshold: still refused.
    exercise, session_id = open_exercise(client, headers)
    for _ in range(ANSWER_AFTER_ATTEMPTS - 1):
        submit(client, headers, exercise, session_id, WRONG)
    assert client.get(
        "/exercises/expired-quests/solution", headers=headers
    ).status_code == 403

    # The last one opens it.
    submit(client, headers, exercise, session_id, WRONG)
    assert client.get(
        "/exercises/expired-quests/solution", headers=headers
    ).status_code == 200
