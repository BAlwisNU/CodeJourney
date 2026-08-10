"""Teacher accounts, classes, the teaching dashboard, and student questions.

The tests that matter most here are the negative ones. A teacher account can
read progress, hint depth and private journals, so the things worth asserting
are the ones that must NOT happen: a student cannot become a teacher by asking,
and a teacher cannot see a student who never joined their class.
"""

import pytest

from app.config import get_settings
from conftest import CORRECT, WRONG, login, open_exercise, submit

TEACHER_CODE = "let-me-teach"


@pytest.fixture(autouse=True)
def teacher_code_set():
    """Turn teacher signup on for this module only.

    Settings are lru_cached, so the cache is cleared on the way in and out --
    otherwise a value set here leaks into every module that runs after it.
    """
    settings = get_settings()
    original = settings.teacher_signup_code
    settings.teacher_signup_code = TEACHER_CODE
    yield
    settings.teacher_signup_code = original


def make_teacher(client, email="teacher@example.com", name="Ms Okafor", code=TEACHER_CODE):
    return client.post(
        "/auth/register/teacher",
        json={
            "email": email,
            "password": "password123",
            "display_name": name,
            "teacher_code": code,
        },
    )


def teacher_headers(client, email="teacher@example.com"):
    response = make_teacher(client, email=email)
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def make_student(client, email, name="Sam"):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": name},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Becoming a teacher
# ---------------------------------------------------------------------------


def test_teacher_signup_needs_the_code(client):
    response = make_teacher(client, code="obviously-wrong")
    assert response.status_code == 403
    assert "teacher code" in response.json()["detail"].lower()


def test_teacher_signup_is_refused_when_the_deployment_has_no_code(client):
    """Absent configuration means the feature is off, never half-open."""
    settings = get_settings()
    settings.teacher_signup_code = ""
    try:
        assert make_teacher(client, code="anything").status_code == 503
        assert client.get("/auth/register/teacher/available").json() == {
            "enabled": False
        }
    finally:
        settings.teacher_signup_code = TEACHER_CODE


def test_a_correct_code_creates_an_instructor(client):
    headers = teacher_headers(client)
    me = client.get("/auth/me", headers=headers).json()
    assert me["role"] == "instructor"


def test_a_teacher_is_not_a_study_participant(client):
    """No consent stamp and no counterbalance group: staff rows must not reach
    the Week 8 analysis."""
    headers = teacher_headers(client)
    me = client.get("/auth/me", headers=headers).json()
    assert me["consented_at"] is None

    from app.models import User

    with client.session_factory() as db:
        user = db.query(User).filter(User.email == "teacher@example.com").one()
        assert user.counterbalance_group is None


def test_the_ordinary_signup_route_cannot_mint_a_teacher(client):
    """The privilege must not be reachable by adding a key to /auth/register."""
    response = client.post(
        "/auth/register",
        json={
            "email": "sneaky@example.com",
            "password": "password123",
            "display_name": "Sneaky",
            "role": "instructor",
            "teacher_code": TEACHER_CODE,
        },
    )
    assert response.status_code == 201
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/auth/me", headers=headers).json()["role"] == "student"
    assert client.get("/teacher", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------


def test_a_class_gets_a_readable_join_code(client):
    headers = teacher_headers(client)
    created = client.post(
        "/teacher/classes", headers=headers, json={"name": "Year 9 Python"}
    )
    assert created.status_code == 201
    code = created.json()["join_code"]
    assert len(code) == 6
    # The characters that get misread off a whiteboard are absent by design.
    assert not set(code) & set("IO01S5")


def test_a_student_joins_with_the_code_and_the_teacher_sees_them(client):
    teacher = teacher_headers(client)
    code = client.post(
        "/teacher/classes", headers=teacher, json={"name": "Year 9"}
    ).json()["join_code"]

    student = make_student(client, "pupil@example.com", "Priya")
    joined = client.post("/classes/join", headers=student, json={"code": code})
    assert joined.status_code == 201
    assert joined.json()["teacher_name"] == "Ms Okafor"

    home = client.get("/teacher", headers=teacher).json()
    assert home["total_students"] == 1
    assert home["students"][0]["display_name"] == "Priya"


def test_a_join_code_is_forgiving_about_how_it_was_typed(client):
    teacher = teacher_headers(client)
    code = client.post(
        "/teacher/classes", headers=teacher, json={"name": "Year 9"}
    ).json()["join_code"]

    student = make_student(client, "pupil@example.com")
    messy = f" {code.lower()[:3]}-{code.lower()[3:]} "
    assert client.post("/classes/join", headers=student, json={"code": messy}).status_code == 201


def test_joining_twice_is_a_no_op(client):
    teacher = teacher_headers(client)
    code = client.post(
        "/teacher/classes", headers=teacher, json={"name": "Year 9"}
    ).json()["join_code"]
    student = make_student(client, "pupil@example.com")

    client.post("/classes/join", headers=student, json={"code": code})
    client.post("/classes/join", headers=student, json={"code": code})

    assert client.get("/teacher", headers=teacher).json()["total_students"] == 1


def test_a_bad_code_says_so_without_leaking_whether_classes_exist(client):
    student = make_student(client, "pupil@example.com")
    response = client.post("/classes/join", headers=student, json={"code": "ZZZZZZ"})
    assert response.status_code == 404
    assert "No class has that code" in response.json()["detail"]


def test_a_teacher_cannot_join_a_class_as_a_student(client):
    """A teacher on a roster would pollute every average on that dashboard."""
    first = teacher_headers(client)
    code = client.post(
        "/teacher/classes", headers=first, json={"name": "Year 9"}
    ).json()["join_code"]
    second = teacher_headers(client, email="other@example.com")
    assert client.post("/classes/join", headers=second, json={"code": code}).status_code == 409


def test_leaving_a_class_keeps_the_work(client):
    teacher = teacher_headers(client)
    code = client.post(
        "/teacher/classes", headers=teacher, json={"name": "Year 9"}
    ).json()["join_code"]
    student = make_student(client, "pupil@example.com")
    classroom_id = client.post(
        "/classes/join", headers=student, json={"code": code}
    ).json()["id"]

    exercise, session_id = open_exercise(client, student)
    submit(client, student, exercise, session_id, CORRECT)

    assert client.delete(f"/classes/{classroom_id}", headers=student).status_code == 204
    assert client.get("/teacher", headers=teacher).json()["total_students"] == 0
    # Their own progress is untouched.
    assert client.get("/progress", headers=student).json()["solved"] >= 1


# ---------------------------------------------------------------------------
# Scoping -- the tests that matter
# ---------------------------------------------------------------------------


def test_a_teacher_sees_only_their_own_students(client):
    alice = teacher_headers(client, email="alice@example.com")
    bob = teacher_headers(client, email="bob@example.com")

    alice_code = client.post(
        "/teacher/classes", headers=alice, json={"name": "Alice's class"}
    ).json()["join_code"]
    student = make_student(client, "pupil@example.com", "Priya")
    client.post("/classes/join", headers=student, json={"code": alice_code})

    assert client.get("/teacher", headers=alice).json()["total_students"] == 1
    # Bob has a class of his own and nobody in it.
    client.post("/teacher/classes", headers=bob, json={"name": "Bob's class"})
    assert client.get("/teacher", headers=bob).json()["total_students"] == 0


def test_a_teacher_cannot_read_the_journal_of_a_student_not_in_their_class(client):
    """The single most sensitive read in the platform, scoped by roster."""
    alice = teacher_headers(client, email="alice@example.com")
    bob = teacher_headers(client, email="bob@example.com")
    code = client.post(
        "/teacher/classes", headers=alice, json={"name": "Alice's"}
    ).json()["join_code"]

    student = make_student(client, "pupil@example.com")
    client.post("/classes/join", headers=student, json={"code": code})
    exercise, _ = open_exercise(client, student)
    client.put(
        f"/reflections/{exercise['id']}",
        headers=student,
        json={"tried": "loops", "stuck": "I felt stupid", "fixed": "asked"},
    )

    student_id = client.get("/auth/me", headers=student).json()["id"]
    assert client.get(
        f"/teacher/students/{student_id}/reflections", headers=alice
    ).status_code == 200
    assert client.get(
        f"/teacher/students/{student_id}/reflections", headers=bob
    ).status_code == 404


def test_students_are_refused_the_whole_teacher_surface(client):
    headers = make_student(client, "pupil@example.com")
    for path in ("/teacher", "/teacher/classes", "/help/inbox"):
        assert client.get(path, headers=headers).status_code == 403, path


# ---------------------------------------------------------------------------
# The dashboard's numbers
# ---------------------------------------------------------------------------


def enrolled(client):
    """A teacher, a class, and one student in it."""
    teacher = teacher_headers(client)
    code = client.post(
        "/teacher/classes", headers=teacher, json={"name": "Year 9"}
    ).json()["join_code"]
    student = make_student(client, "pupil@example.com", "Priya")
    client.post("/classes/join", headers=student, json={"code": code})
    return teacher, student


def test_a_new_teachers_dashboard_has_a_class_and_no_students(client):
    """This used to assert the opposite -- that a new teacher had no class and
    was shown a setup form. That form was the only thing between them and the
    code they signed up to get, so signup makes the class now. What is still
    true, and still worth pinning, is that the roster is empty until somebody
    joins.
    """
    headers = teacher_headers(client)
    home = client.get("/teacher", headers=headers).json()
    assert home["has_class"] is True
    assert home["classrooms"][0]["join_code"]
    assert home["students"] == []
    assert home["total_students"] == 0


def test_solving_an_exercise_moves_the_dashboard(client):
    teacher, student = enrolled(client)
    exercise, session_id = open_exercise(client, student)
    submit(client, student, exercise, session_id, CORRECT)

    row = client.get("/teacher", headers=teacher).json()["students"][0]
    assert row["solved"] == 1
    assert row["attempts"] == 1
    assert row["last_active_at"] is not None


def test_a_stuck_student_is_flagged_and_named_with_what_they_are_stuck_on(client):
    """The row has to say *what* they are stuck on -- 'Priya needs help' alone
    makes the teacher go and find out."""
    teacher, student = enrolled(client)
    exercise, session_id = open_exercise(client, student)
    for _ in range(7):
        submit(client, student, exercise, session_id, WRONG)

    home = client.get("/teacher", headers=teacher).json()
    row = home["students"][0]
    assert row["needs_help"] is True
    assert row["stuck_on"] == exercise["title"]
    assert home["needs_help"] == 1


def test_difficulty_counts_a_student_who_never_solved_it_as_struggling(client):
    teacher, student = enrolled(client)
    exercise, session_id = open_exercise(client, student)
    submit(client, student, exercise, session_id, WRONG)

    home = client.get("/teacher", headers=teacher).json()
    hardest = home["hardest"][0]
    assert hardest["label"] == exercise["title"]
    assert hardest["attempted"] == 1
    assert hardest["solved"] == 0
    assert hardest["struggled"] == 1
    assert hardest["struggle_rate"] == 1.0


def test_difficulty_leaves_out_ai_practice_built_for_one_student(client):
    """A branch built for one person is not coursework, and folding it into
    class difficulty would compare it against a lesson thirty people took."""
    from app.models import Exercise, ThemeVariant, Theme, Concept

    teacher, student = enrolled(client)
    student_id = client.get("/auth/me", headers=student).json()["id"]
    with client.session_factory() as db:
        db.add(
            Exercise(
                slug="ai-lists-deadbeef",
                title="Private practice",
                theme=Theme.GENERIC,
                concept=Concept.LISTS,
                variant=ThemeVariant.GENERIC,
                pair_id="ai-lists-deadbeef",
                entrypoint="f",
                prompt_md="x",
                starter_code="def f():\n    pass\n",
                tests=[{"name": "t", "args": [], "expected": None, "hidden": False}],
                created_by_user_id=student_id,
            )
        )
        db.commit()

    home = client.get("/teacher", headers=teacher).json()
    assert "Private practice" not in [row["label"] for row in home["hardest"]]


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------


def test_a_student_asks_and_the_teacher_sees_it(client):
    teacher, student = enrolled(client)
    asked = client.post(
        "/help",
        headers=student,
        json={"body": "I don't get why the list is empty", "exercise_slug": "expired-quests"},
    )
    assert asked.status_code == 201
    assert asked.json()["status"] == "open"

    inbox = client.get("/help/inbox", headers=teacher).json()
    assert len(inbox) == 1
    assert inbox[0]["student_name"] == "Priya"
    assert inbox[0]["exercise_slug"] == "expired-quests"


def test_a_student_with_no_class_is_told_how_to_get_one(client):
    headers = make_student(client, "lonely@example.com")
    response = client.post("/help", headers=headers, json={"body": "help"})
    assert response.status_code == 409
    assert "class code" in response.json()["detail"]

    state = client.get("/help/mine", headers=headers).json()
    assert state["can_ask"] is False


def test_answering_reaches_the_student(client):
    teacher, student = enrolled(client)
    request_id = client.post(
        "/help", headers=student, json={"body": "why?"}
    ).json()["id"]

    answered = client.post(
        f"/help/{request_id}/answer",
        headers=teacher,
        json={"answer": "Because the filter runs before the append."},
    )
    assert answered.status_code == 200
    assert answered.json()["answered_by"] == "Ms Okafor"

    mine = client.get("/help/mine", headers=student).json()
    assert mine["requests"][0]["status"] == "answered"
    assert "filter runs" in mine["requests"][0]["answer"]


def test_only_the_student_closes_their_own_question(client):
    """Closing measures whether it helped, so it is not the teacher's to do."""
    teacher, student = enrolled(client)
    request_id = client.post(
        "/help", headers=student, json={"body": "why?"}
    ).json()["id"]

    other = make_student(client, "other@example.com")
    assert client.post(f"/help/{request_id}/close", headers=other).status_code == 404
    assert client.post(f"/help/{request_id}/close", headers=student).status_code == 200
    # Closed questions leave the inbox.
    assert client.get("/help/inbox", headers=teacher).json() == []


def test_a_teacher_cannot_answer_another_teachers_student(client):
    alice = teacher_headers(client, email="alice@example.com")
    bob = teacher_headers(client, email="bob@example.com")
    code = client.post(
        "/teacher/classes", headers=alice, json={"name": "Alice's"}
    ).json()["join_code"]
    student = make_student(client, "pupil@example.com")
    client.post("/classes/join", headers=student, json={"code": code})
    request_id = client.post("/help", headers=student, json={"body": "?"}).json()["id"]

    assert client.post(
        f"/help/{request_id}/answer", headers=bob, json={"answer": "no"}
    ).status_code == 404


def test_an_open_question_raises_the_student_up_the_dashboard(client):
    """Someone who asked is someone who wants attention, even if the platform's
    own signals say they are fine."""
    teacher = teacher_headers(client)
    code = client.post(
        "/teacher/classes", headers=teacher, json={"name": "Year 9"}
    ).json()["join_code"]

    quiet = make_student(client, "quiet@example.com", "Quiet")
    asker = make_student(client, "asker@example.com", "Asker")
    for headers in (quiet, asker):
        client.post("/classes/join", headers=headers, json={"code": code})
    # The quiet one is further behind, so ordering by progress alone would put
    # them first.
    exercise, session_id = open_exercise(client, asker)
    submit(client, asker, exercise, session_id, CORRECT)
    client.post("/help", headers=asker, json={"body": "one more thing"})

    home = client.get("/teacher", headers=teacher).json()
    assert home["students"][0]["display_name"] == "Asker"
    assert home["students"][0]["open_questions"] == 1
    assert home["open_questions"] == 1


# ---------------------------------------------------------------------------
# Class codes
# ---------------------------------------------------------------------------


def test_a_new_teacher_arrives_with_a_class_and_a_code(client):
    """Signing up used to leave a teacher on an empty dashboard whose only
    action was a form. The one thing they came for is a code to read out, so
    it exists before they touch anything."""
    headers = teacher_headers(client)
    classes = client.get("/teacher/classes", headers=headers).json()
    assert len(classes) == 1
    assert classes[0]["name"] == "Ms Okafor's class"
    assert len(classes[0]["join_code"]) == 6
    # And the dashboard is past its setup state, not stuck on it.
    assert client.get("/teacher", headers=headers).json()["has_class"] is True


def test_a_teacher_can_use_a_code_of_their_own(client):
    """"Join YEAR10" is a sentence a room can act on; "join Q69NEK" gets
    misheard twice and typed wrong three times."""
    headers = teacher_headers(client)
    classroom_id = client.get("/teacher/classes", headers=headers).json()[0]["id"]
    response = client.patch(
        f"/teacher/classes/{classroom_id}/code",
        headers=headers,
        json={"join_code": " year-10 "},
    )
    assert response.status_code == 200
    assert response.json()["join_code"] == "YEAR10"


def test_a_chosen_code_is_forgiving_about_how_it_was_typed(client):
    """The same code gets written on a board, said aloud and pasted into a
    chat, and none of those agree on formatting."""
    teacher = teacher_headers(client)
    classroom_id = client.get("/teacher/classes", headers=teacher).json()[0]["id"]
    client.patch(
        f"/teacher/classes/{classroom_id}/code",
        headers=teacher,
        json={"join_code": "Year10"},
    )
    student = make_student(client, "pupil@example.com")
    joined = client.post("/classes/join", headers=student, json={"code": " year 10 "})
    assert joined.status_code == 201


def test_a_code_that_cannot_be_typed_is_refused_with_a_reason(client):
    headers = teacher_headers(client)
    classroom_id = client.get("/teacher/classes", headers=headers).json()[0]["id"]

    for code, expect in [
        ("abc", "too short"),
        ("x" * 20, "too long"),
        ("!!!", "letters or numbers"),
    ]:
        response = client.patch(
            f"/teacher/classes/{classroom_id}/code",
            headers=headers,
            json={"join_code": code},
        )
        assert response.status_code == 422, code
        assert expect in response.json()["detail"], code


def test_two_classes_cannot_share_a_code(client):
    """A student typing a code must land in one place, not whichever row the
    database happened to return first."""
    alice = teacher_headers(client, email="alice@example.com")
    bob = teacher_headers(client, email="bob@example.com")
    a_id = client.get("/teacher/classes", headers=alice).json()[0]["id"]
    b_id = client.get("/teacher/classes", headers=bob).json()[0]["id"]

    assert (
        client.patch(
            f"/teacher/classes/{a_id}/code", headers=alice, json={"join_code": "YEAR10"}
        ).status_code
        == 200
    )
    clash = client.patch(
        f"/teacher/classes/{b_id}/code", headers=bob, json={"join_code": "year10"}
    )
    assert clash.status_code == 422
    assert "already using" in clash.json()["detail"]


def test_re_saving_your_own_code_is_not_a_clash_with_yourself(client):
    headers = teacher_headers(client)
    classroom_id = client.get("/teacher/classes", headers=headers).json()[0]["id"]
    client.patch(
        f"/teacher/classes/{classroom_id}/code", headers=headers, json={"join_code": "YEAR10"}
    )
    again = client.patch(
        f"/teacher/classes/{classroom_id}/code", headers=headers, json={"join_code": "YEAR10"}
    )
    assert again.status_code == 200


def test_changing_the_code_keeps_the_students_already_in(client):
    """Membership is a row, not a password -- which is what makes this the way
    to retire a code that escaped into the wrong group chat."""
    teacher = teacher_headers(client)
    classroom = client.get("/teacher/classes", headers=teacher).json()[0]
    student = make_student(client, "pupil@example.com", "Priya")
    client.post("/classes/join", headers=student, json={"code": classroom["join_code"]})
    assert client.get("/teacher", headers=teacher).json()["total_students"] == 1

    client.patch(
        f"/teacher/classes/{classroom['id']}/code",
        headers=teacher,
        json={"join_code": "NEWCODE"},
    )
    assert client.get("/teacher", headers=teacher).json()["total_students"] == 1
    # And the old code no longer lets anyone new in.
    late = make_student(client, "late@example.com")
    assert (
        client.post(
            "/classes/join", headers=late, json={"code": classroom["join_code"]}
        ).status_code
        == 404
    )


def test_a_teacher_cannot_rename_another_teachers_code(client):
    alice = teacher_headers(client, email="alice@example.com")
    bob = teacher_headers(client, email="bob@example.com")
    a_id = client.get("/teacher/classes", headers=alice).json()[0]["id"]
    assert (
        client.patch(
            f"/teacher/classes/{a_id}/code", headers=bob, json={"join_code": "STOLEN"}
        ).status_code
        == 404
    )
