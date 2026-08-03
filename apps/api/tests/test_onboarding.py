"""The second step of signing up, and where its answers are allowed to go.

Two things here are worth more than the rest:

  * the experience answer must never come back out of the API, and
  * editing goals from the account page must not erase it.

Both are quiet failures. The first leaks nothing dramatic, it just breaks a
promise made on the form. The second would destroy the field the tutor uses to
pitch its explanations, with no error and nothing on screen to notice.
"""

from app.models import LearnerProfile
from app.routers.tutor import _learner_brief
from app.services.tutor import LearnerBrief, _context_block, TutorContext

from conftest import login


def _profile(client, **body) -> dict:
    response = client.patch("/auth/me/profile", headers=login(client), json=body)
    assert response.status_code == 200, response.text
    return response.json()


# --- what comes back --------------------------------------------------------


def test_a_new_account_has_not_been_asked_yet(client):
    """`completed` is what sends someone to the welcome page, so it starts False."""
    body = client.get("/auth/me/profile", headers=login(client)).json()
    assert body == {"goals": "", "project_ideas": "", "completed": False}


def test_answers_come_back_except_the_experience(client):
    saved = _profile(
        client,
        goals="Automate my spreadsheets",
        experience="other_language",
        experience_note="I write a lot of SQL",
        project_ideas="A tracker for my running times",
    )
    assert saved["goals"] == "Automate my spreadsheets"
    assert saved["project_ideas"] == "A tracker for my running times"
    assert saved["completed"] is True

    # The promise on the form: the experience question is asked to pitch the
    # teaching, and is not read back. No endpoint may return it.
    fetched = client.get("/auth/me/profile", headers=login(client)).json()
    assert set(fetched) == {"goals", "project_ideas", "completed"}
    assert "experience" not in str(fetched)
    assert "SQL" not in str(fetched)

    # It is stored, though -- it exists for the tutor.
    with client.session_factory() as db:
        row = db.query(LearnerProfile).one()
        assert row.experience == "other_language"
        assert row.experience_note == "I write a lot of SQL"


def test_skipping_still_counts_as_asked(client):
    """Otherwise the welcome step reappears on every single visit."""
    saved = _profile(
        client, goals="", experience="", experience_note="", project_ideas=""
    )
    assert saved["completed"] is True
    assert saved["goals"] == ""


def test_editing_goals_does_not_wipe_the_experience(client):
    """The account page can edit goals but cannot read the experience answer.

    If a partial save cleared what it omitted, editing a goal there would
    silently destroy the field the tutor relies on -- no error, nothing on
    screen, and only the tutor quietly getting worse.
    """
    _profile(
        client,
        goals="Automate my spreadsheets",
        experience="rusty",
        experience_note="Did a bit at school",
        project_ideas="",
    )

    # Exactly what the account page sends: the two fields it owns.
    _profile(client, goals="Build a game", project_ideas="Something like Wordle")

    with client.session_factory() as db:
        row = db.query(LearnerProfile).one()
        assert row.goals == "Build a game"
        assert row.project_ideas == "Something like Wordle"
        assert row.experience == "rusty"
        assert row.experience_note == "Did a bit at school"


def test_saving_twice_leaves_one_profile(client):
    _profile(client, goals="First")
    _profile(client, goals="Second")
    with client.session_factory() as db:
        assert db.query(LearnerProfile).count() == 1
        assert db.query(LearnerProfile).one().goals == "Second"


def test_an_unknown_experience_option_is_refused(client):
    """An unrecognised key would reach the tutor as a level it's never heard of."""
    response = client.patch(
        "/auth/me/profile", headers=login(client), json={"experience": "expert"}
    )
    assert response.status_code == 422


def test_the_profile_is_private_to_its_owner(client):
    _profile(client, goals="Mine alone")
    instructor = login(client, "instructor@example.com", "password123")
    body = client.get("/auth/me/profile", headers=instructor).json()
    # An instructor gets their own (empty) profile, never the student's.
    assert body == {"goals": "", "project_ideas": "", "completed": False}


def test_the_endpoint_needs_a_login(client):
    assert client.get("/auth/me/profile").status_code == 401
    assert client.patch("/auth/me/profile", json={"goals": "x"}).status_code == 401


# --- what the tutor is told -------------------------------------------------


def _ctx(learner: LearnerBrief | None) -> str:
    return _context_block(
        TutorContext(
            title="Quest log",
            concept="lists",
            prompt_md="Build a list.",
            entrypoint="quests",
            latest_code="pass",
            solved=False,
            attempts=1,
            last_summary=None,
            learner=learner,
        )
    )


def test_the_tutor_is_given_the_answers(client):
    block = _ctx(
        LearnerBrief(
            goals="Automate my spreadsheets",
            experience="Comfortable in another language, new to Python",
            experience_note="I write a lot of SQL",
            project_ideas="A running tracker",
        )
    )
    assert "Automate my spreadsheets" in block
    assert "Comfortable in another language" in block
    assert "A running tracker" in block
    # And told what to do with it, so it doesn't read the list back at them.
    assert "Do not recite it back" in block


def test_a_skipped_profile_tells_the_tutor_nothing(client):
    """Not "they left it blank" -- nothing at all.

    A model told a field is empty comments on the emptiness, which would punish
    someone for using a skip button we offered them.
    """
    for learner in (None, LearnerBrief()):
        block = _ctx(learner)
        assert "signed up" not in block
        assert "want to be able to do" not in block


def test_the_brief_uses_the_label_not_the_stored_key(client):
    """The model should read a description, not a database enum."""
    headers = login(client)
    _profile(client, experience="other_language")
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    with client.session_factory() as db:
        brief = _learner_brief(user_id, db)
    assert brief is not None
    assert brief.experience == "Comfortable in another language, new to Python"


def test_no_brief_when_the_step_was_never_reached(client):
    headers = login(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    with client.session_factory() as db:
        assert _learner_brief(user_id, db) is None
