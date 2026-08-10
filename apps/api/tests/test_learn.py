"""The Plan stage, error translation, portfolio, and instructor analytics."""

import pytest

from app.config import get_settings
from conftest import CORRECT, WRONG, login, open_exercise, submit  # noqa: F401

from app.services import translate


# --- error translation (L1) ------------------------------------------------


@pytest.mark.parametrize(
    "error,expected_fragment",
    [
        ({"type": "NameError", "message": "name 'totl' is not defined"}, "“totl”"),
        ({"type": "IndexError", "message": "list index out of range"}, "first item is at 0"),
        ({"type": "KeyError", "message": "'nmae'"}, "isn't in the dictionary"),
        ({"type": "ZeroDivisionError", "message": "division by zero"}, "list was empty"),
        ({"type": "TypeError", "message": "can only concatenate str (not \"int\") to str"}, "str()"),
        ({"type": "SyntaxError", "message": "expected ':'"}, "colon"),
        ({"type": "IndentationError", "message": "unexpected indent"}, "indented further"),
        ({"type": "RecursionError", "message": "maximum recursion depth exceeded"}, "calling itself"),
        ({"type": "Timeout", "message": "..."}, "never becomes false"),
        (
            {"type": "AttributeError", "message": "'str' object has no attribute 'apend'"},
            "a piece of text",
        ),
    ],
)
def test_translations_are_plain_english(error, expected_fragment):
    result = translate.translate(error)
    assert expected_fragment in result


def test_translation_never_contains_jargon_or_tracebacks():
    """A translation that says 'iterable' has explained nothing."""
    banned = ["Traceback", "iterable", "unhashable", "subscriptable", "NoneType"]
    for kind in [
        "NameError", "IndexError", "KeyError", "TypeError", "ValueError",
        "SyntaxError", "IndentationError", "AttributeError", "ZeroDivisionError",
    ]:
        text = translate.translate({"type": kind, "message": "x", "line": 1})
        for word in banned:
            assert word not in text, f"{kind} translation leaked {word!r}"


def test_unknown_error_still_gets_a_human_message():
    """Never leave a novice with nothing -- that's the failure this project fixes."""
    text = translate.translate({"type": "SomeWeirdError", "message": "?"})
    assert text and "SomeWeirdError" in text


def test_no_error_translates_to_nothing():
    assert translate.translate(None) is None


def test_translation_reaches_the_student_on_submit(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    body = submit(
        client,
        headers,
        exercise,
        session_id,
        "def expired_quests(quests, today):\n    return missing_name\n",
    ).json()

    assert body["translated_error"]
    assert "missing_name" in body["translated_error"]
    # And it points at the line they wrote.
    assert "line 2" in body["translated_error"]


# --- lessons & quiz --------------------------------------------------------


def test_lesson_is_served_for_a_concept(client):
    headers = login(client)
    lesson = client.get("/learn/lessons/lists", headers=headers).json()
    assert lesson["title"]
    # Enough to hand one to each section as a checkpoint and still close the
    # page with a recap. The exact count is content, and grows.
    assert len(lesson["questions"]) >= 5


def test_quiz_answers_never_reach_the_browser(client):
    """Otherwise the quiz is a devtools memory test."""
    headers = login(client)
    lesson = client.get("/learn/lessons/lists", headers=headers).json()
    blob = str(lesson)
    assert "correct_index" not in blob
    assert "explanation" not in blob


def test_quiz_grades_and_explains_both_right_and_wrong(client):
    headers = login(client)
    lesson = client.get("/learn/lessons/lists", headers=headers).json()

    # Answer everything 0 -- some right, some wrong.
    answers = [{"question_id": q["id"], "chosen_index": 0} for q in lesson["questions"]]
    grade = client.post(
        f"/learn/lessons/{lesson['id']}/quiz", headers=headers, json={"answers": answers}
    ).json()

    assert grade["total"] == len(lesson["questions"])
    # Every result carries an explanation, including the correct ones -- someone
    # who guessed right has learned nothing yet.
    assert all(r["explanation"] for r in grade["results"])


def test_quiz_is_not_a_gate(client):
    """Getting everything wrong must not block the editor."""
    headers = login(client)
    lesson = client.get("/learn/lessons/lists", headers=headers).json()
    answers = [{"question_id": q["id"], "chosen_index": 3} for q in lesson["questions"]]
    client.post(
        f"/learn/lessons/{lesson['id']}/quiz", headers=headers, json={"answers": answers}
    )
    # The exercise is still reachable and submittable.
    exercise, session_id = open_exercise(client, headers)
    assert submit(client, headers, exercise, session_id, CORRECT).json()["passed"]


def test_quiz_grades_one_question_on_its_own(client):
    """The checkpoints ask a single question in the middle of the lesson.

    Nothing about the endpoint required all four at once, but nothing pinned
    that down either, and the inline checks are unusable if it ever does.
    """
    headers = login(client)
    lesson = client.get("/learn/lessons/lists", headers=headers).json()
    first = lesson["questions"][0]

    grade = client.post(
        f"/learn/lessons/{lesson['id']}/quiz",
        headers=headers,
        json={"answers": [{"question_id": first["id"], "chosen_index": 0}]},
    ).json()

    assert len(grade["results"]) == 1
    assert grade["results"][0]["question_id"] == first["id"]
    assert grade["results"][0]["explanation"]


def test_reseeding_refreshes_the_lesson_text(client):
    """Seeding an existing database must update the teaching text.

    It only ever inserted before, so an edit to a lesson reached a fresh
    checkout and never a deployment.
    """
    from sqlalchemy import select

    from app.models import Lesson
    from app.seed import seed

    with client.session_factory() as db:
        lesson = db.scalar(select(Lesson).where(Lesson.slug == "lists-filtering"))
        lesson.body_md = "## Stale copy"
        db.commit()

        seed(db)
        db.commit()

        db.refresh(lesson)
        assert lesson.body_md != "## Stale copy"
        assert "```diff" in lesson.body_md


def test_reseeding_adds_new_questions_without_touching_the_old_ones(client):
    """Questions are additive. Never rewritten, never removed.

    Attempts point at question ids, so changing the options underneath an
    answer already recorded would change what a student was asked, and
    deleting one would orphan the attempt. Adding a question does neither --
    which is the only way a lesson can grow a question after release.
    """
    from sqlalchemy import select

    from app.models import Lesson, QuizQuestion
    from app.seed import seed

    with client.session_factory() as db:
        lesson = db.scalar(select(Lesson).where(Lesson.slug == "lists-filtering"))
        kept = sorted(lesson.questions, key=lambda q: q.order_index)[0]
        before_id, before_prompt = kept.id, kept.prompt
        before_options = list(kept.options)

        # Simulate a database seeded before the extra questions were written.
        for question in lesson.questions[3:]:
            db.delete(question)
        db.commit()
        assert len(db.scalars(select(QuizQuestion)).all()) == 3

        seed(db)
        db.commit()

        db.refresh(lesson)
        assert len(lesson.questions) == 10
        # The survivor is the same row, asking the same thing.
        survivor = db.get(QuizQuestion, before_id)
        assert survivor.prompt == before_prompt
        assert survivor.options == before_options

        # And seeding twice must not duplicate anything.
        seed(db)
        db.commit()
        db.refresh(lesson)
        assert len(lesson.questions) == 10


def test_missing_lesson_returns_null_not_an_error(client):
    """Unwritten content degrades to 'straight to the editor'."""
    headers = login(client)
    assert client.get("/learn/lessons/dicts", headers=headers).json() is None


# --- parsons ---------------------------------------------------------------


def test_parsons_offers_shuffled_lines_with_distractors(client):
    headers = login(client)
    problem = client.get("/learn/parsons/expired-quests", headers=headers).json()
    # 6 real lines + 2 distractors.
    assert len(problem["shuffled_lines"]) == 8
    assert "lines" not in problem  # the answer key must not ship


def test_parsons_shuffle_is_stable_across_requests(client):
    """A puzzle that rearranges itself on refresh reads as a bug."""
    headers = login(client)
    first = client.get("/learn/parsons/expired-quests", headers=headers).json()
    second = client.get("/learn/parsons/expired-quests", headers=headers).json()
    assert first["shuffled_lines"] == second["shuffled_lines"]


def test_parsons_accepts_the_right_order(client):
    headers = login(client)
    problem = client.get("/learn/parsons/expired-quests", headers=headers).json()

    with client.session_factory() as db:
        from app.models import ParsonsProblem

        correct = db.get(ParsonsProblem, problem["id"]).lines

    result = client.post(
        f"/learn/parsons/{problem['id']}/check",
        headers=headers,
        json={"ordering": correct},
    ).json()
    assert result["correct"] is True
    assert result["correct_prefix"] == len(correct)


def test_parsons_reports_prefix_without_revealing_the_answer(client):
    headers = login(client)
    problem = client.get("/learn/parsons/expired-quests", headers=headers).json()

    with client.session_factory() as db:
        from app.models import ParsonsProblem

        correct = db.get(ParsonsProblem, problem["id"]).lines

    # First two right, then wrong.
    wrong = correct[:2] + list(reversed(correct[2:]))
    result = client.post(
        f"/learn/parsons/{problem['id']}/check", headers=headers, json={"ordering": wrong}
    ).json()

    assert result["correct"] is False
    assert result["correct_prefix"] == 2
    # Must not hand back the solution.
    assert "lines" not in result and "ordering" not in result


def test_both_sides_of_a_pair_get_a_parsons_warm_up(client):
    """Unequal scaffolding would make the study measure support, not framing."""
    headers = login(client)
    themed = client.get("/learn/parsons/expired-quests", headers=headers).json()
    generic = client.get("/learn/parsons/filter-records-generic", headers=headers).json()
    assert themed and generic
    assert len(themed["shuffled_lines"]) == len(generic["shuffled_lines"])


# --- portfolio -------------------------------------------------------------


def test_portfolio_is_empty_before_any_work(client):
    headers = login(client)
    data = client.get("/portfolio", headers=headers).json()
    assert data["entries"] == []
    assert data["solved"] == 0


def test_portfolio_shows_solved_code_and_the_effort_it_took(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, WRONG)
    submit(client, headers, exercise, session_id, WRONG)
    submit(client, headers, exercise, session_id, CORRECT)

    entry = client.get("/portfolio", headers=headers).json()["entries"][0]
    assert entry["solved_at"] is not None
    # The attempt count is the evidence of progress, not just the final answer.
    assert entry["attempts"] == 3
    assert "for q in quests" in entry["code"]


def test_portfolio_includes_the_students_own_reflection(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)
    client.post(
        "/reflections",
        headers=headers,
        json={"exercise_id": exercise["id"], "what_i_tried": "a loop"},
    )

    entry = client.get("/portfolio", headers=headers).json()["entries"][0]
    assert entry["reflection"]["what_i_tried"] == "a loop"


def test_unsolved_work_shows_no_code(client):
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, WRONG)

    entry = client.get("/portfolio", headers=headers).json()["entries"][0]
    assert entry["solved_at"] is None
    assert entry["code"] is None


# --- instructor ------------------------------------------------------------


#: The seeded instructor's address. The study dashboard now takes a named
#: allowlist rather than the instructor role -- teachers sign themselves up,
#: so the role stopped being a credential. These tests are about what a
#: researcher sees, so they name one.
RESEARCHER = "instructor@example.com"


@pytest.fixture
def as_researcher():
    settings = get_settings()
    original = list(settings.research_emails)
    settings.research_emails = [RESEARCHER]
    yield
    settings.research_emails = original


def instructor_headers(client) -> dict:
    return login(client, email=RESEARCHER)


def test_students_cannot_reach_the_instructor_dashboard(client):
    assert client.get("/instructor", headers=login(client)).status_code == 403


def test_instructor_sees_the_class(client, as_researcher):
    student = login(client)
    exercise, session_id = open_exercise(client, student)
    submit(client, student, exercise, session_id, CORRECT)

    data = client.get("/instructor", headers=instructor_headers(client)).json()
    assert data["total_students"] >= 1
    assert data["total_submissions"] >= 1
    row = next(s for s in data["students"] if s["display_name"] == "Test Student")
    assert row["solved"] == 1


def test_struggling_students_are_flagged_and_sorted_first(client, as_researcher):
    student = login(client)
    exercise, session_id = open_exercise(client, student)
    # Exhaust the ladder without solving it.
    for _ in range(7):
        submit(client, student, exercise, session_id, WRONG)

    data = client.get("/instructor", headers=instructor_headers(client)).json()
    assert data["students"][0]["needs_help"] is True


def test_solving_it_clears_the_flag(client, as_researcher):
    student = login(client)
    exercise, session_id = open_exercise(client, student)
    for _ in range(7):
        submit(client, student, exercise, session_id, WRONG)
    submit(client, student, exercise, session_id, CORRECT)

    data = client.get("/instructor", headers=instructor_headers(client)).json()
    row = next(s for s in data["students"] if s["display_name"] == "Test Student")
    assert row["needs_help"] is False


def test_common_errors_are_aggregated(client, as_researcher):
    student = login(client)
    exercise, session_id = open_exercise(client, student)
    submit(
        client, student, exercise, session_id,
        "def expired_quests(quests, today):\n    return nope\n",
    )

    data = client.get("/instructor", headers=instructor_headers(client)).json()
    assert any(e["error_type"] == "NameError" for e in data["common_errors"])


def test_instructor_can_read_a_students_journal(client, as_researcher):
    """Allowed, and students are told so. What must never read them is a model."""
    student = login(client)
    exercise, _ = open_exercise(client, student)
    client.post(
        "/reflections",
        headers=student,
        json={"exercise_id": exercise["id"], "what_i_tried": "a loop"},
    )
    me = client.get("/auth/me", headers=student).json()

    entries = client.get(
        f"/instructor/students/{me['id']}/reflections",
        headers=instructor_headers(client),
    ).json()
    assert entries[0]["what_i_tried"] == "a loop"


def test_students_cannot_read_another_students_journal(client):
    student = login(client)
    me = client.get("/auth/me", headers=student).json()
    assert (
        client.get(
            f"/instructor/students/{me['id']}/reflections", headers=student
        ).status_code
        == 403
    )
