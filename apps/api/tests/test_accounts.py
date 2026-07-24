"""Signup, consent, drafts, and the journal.

The consent tests are the ones that matter beyond the code: they encode the
participant protections the ethics submission promises.
"""

from conftest import CORRECT, login, open_exercise, submit  # noqa: F401


def register(client, email="new@example.com", password="password123", **kw):
    body = {"email": email, "password": password, "display_name": "New Person"}
    body.update(kw)
    return client.post("/auth/register", json=body)


def auth(response) -> dict:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- signup ----------------------------------------------------------------


def test_signup_returns_a_usable_token(client):
    response = register(client)
    assert response.status_code == 201
    me = client.get("/auth/me", headers=auth(response)).json()
    assert me["display_name"] == "New Person"
    assert me["role"] == "student"


def test_email_is_normalised_so_case_cannot_split_an_account(client):
    """Otherwise "Ben@X.com" and "ben@x.com" become two accounts."""
    first = register(client, email="Ben@Example.COM")
    assert first.status_code == 201

    me = client.get("/auth/me", headers=auth(first)).json()
    assert me["email"] == "ben@example.com"

    # The same address in different case must collide, not create a second one.
    assert register(client, email="ben@EXAMPLE.com").status_code == 409

    # ...and must be able to log in however they type it.
    assert (
        client.post(
            "/auth/login",
            json={"email": "BEN@example.com", "password": "password123"},
        ).status_code
        == 200
    )


def test_display_name_is_trimmed_and_cannot_be_only_whitespace(client):
    assert register(client, display_name="   ").status_code == 422
    response = register(client, email="spaced@example.com", display_name="  Ada  ")
    assert client.get("/auth/me", headers=auth(response)).json()["display_name"] == "Ada"


def test_short_password_is_rejected(client):
    assert register(client, password="short").status_code == 422


def test_overlong_password_is_rejected_rather_than_silently_truncated(client):
    """bcrypt ignores everything past 72 bytes.

    Accepting a 100-character passphrase and hashing only the first 72 would
    leave someone believing their password is stronger than it is.
    """
    assert register(client, password="x" * 100).status_code == 422


def test_duplicate_email_is_refused(client):
    register(client)
    assert register(client).status_code == 409


# --- consent ---------------------------------------------------------------


def test_signup_does_not_consent_by_default(client):
    """Silence is not consent. It has to be an explicit opt-in."""
    response = register(client)
    assert client.get("/auth/me", headers=auth(response)).json()["consented_at"] is None


def test_consent_can_be_given_at_signup(client):
    response = register(client, consent_to_research=True)
    assert client.get("/auth/me", headers=auth(response)).json()["consented_at"]


def test_platform_works_fully_without_consenting(client):
    """Consent governs analysis, not access.

    Gating the exercises on study participation would be coercive -- a student
    who needs them for their course cannot meaningfully refuse.
    """
    response = register(client)
    headers = auth(response)

    exercise, session_id = open_exercise(client, headers)
    result = submit(client, headers, exercise, session_id, CORRECT)
    assert result.status_code == 200
    assert result.json()["passed"] is True
    assert client.get("/progress", headers=headers).status_code == 200


def test_consent_can_be_withdrawn_and_is_recorded(client):
    response = register(client, consent_to_research=True)
    headers = auth(response)

    withdrawn = client.patch(
        "/auth/me/consent", headers=headers, json={"consent_to_research": False}
    ).json()
    assert withdrawn["consented_at"] is None
    # The withdrawal itself is recorded -- a right to withdraw that leaves no
    # trace can't be evidenced later.
    assert withdrawn["consent_withdrawn_at"] is not None


def test_withdrawing_does_not_destroy_their_work(client):
    """Leaving the study must never cost someone what they came for."""
    response = register(client, consent_to_research=True)
    headers = auth(response)
    exercise, session_id = open_exercise(client, headers)
    submit(client, headers, exercise, session_id, CORRECT)

    client.patch(
        "/auth/me/consent", headers=headers, json={"consent_to_research": False}
    )

    assert client.get("/progress", headers=headers).json()["solved"] == 1


def test_consent_can_be_given_later_and_clears_the_withdrawal(client):
    response = register(client)
    headers = auth(response)
    client.patch(
        "/auth/me/consent", headers=headers, json={"consent_to_research": True}
    )
    granted = client.get("/auth/me", headers=headers).json()
    assert granted["consented_at"] is not None
    assert granted["consent_withdrawn_at"] is None


def test_never_consenting_leaves_no_withdrawal_record(client):
    """Don't fill the audit trail with no-ops from people who never opted in."""
    response = register(client)
    headers = auth(response)
    client.patch(
        "/auth/me/consent", headers=headers, json={"consent_to_research": False}
    )
    assert client.get("/auth/me", headers=headers).json()["consent_withdrawn_at"] is None


# --- drafts ----------------------------------------------------------------


def test_no_draft_until_something_is_typed(client):
    headers = login(client)
    assert client.get(
        "/exercises/expired-quests/draft", headers=headers
    ).json() is None


def test_draft_survives_and_is_overwritten_in_place(client):
    headers = login(client)
    for code in ("# first thoughts", "# second thoughts"):
        assert (
            client.put(
                "/exercises/expired-quests/draft",
                headers=headers,
                json={"code": code},
            ).status_code
            == 200
        )

    saved = client.get("/exercises/expired-quests/draft", headers=headers).json()
    assert saved["code"] == "# second thoughts"


def test_draft_can_be_reset_to_starter_code(client):
    headers = login(client)
    client.put(
        "/exercises/expired-quests/draft",
        headers=headers,
        json={"code": "# tangled"},
    )
    assert (
        client.delete(
            "/exercises/expired-quests/draft", headers=headers
        ).status_code
        == 204
    )
    assert client.get(
        "/exercises/expired-quests/draft", headers=headers
    ).json() is None


def test_drafts_are_private_to_their_author(client):
    headers = login(client)
    client.put(
        "/exercises/expired-quests/draft",
        headers=headers,
        json={"code": "# mine"},
    )
    other = auth(register(client, email="nosy@example.com"))
    assert client.get(
        "/exercises/expired-quests/draft", headers=other
    ).json() is None


def test_absurdly_large_draft_is_refused(client):
    headers = login(client)
    response = client.put(
        "/exercises/expired-quests/draft",
        headers=headers,
        json={"code": "x" * 200_000},
    )
    assert response.status_code == 413


def test_saving_a_draft_does_not_disturb_the_hint_ladder(client):
    """Autosave must not touch ExerciseSession.last_activity_at.

    That field drives the idle-based L2 trigger. If typing reset it, a
    convenience feature would silently change when hints appear -- and hint depth
    is a dependent variable in the Week 7 study.
    """
    headers = login(client)
    exercise, session_id = open_exercise(client, headers)

    with client.session_factory() as db:
        from app.models import ExerciseSession

        before = db.get(ExerciseSession, session_id).last_activity_at

    client.put(
        "/exercises/expired-quests/draft",
        headers=headers,
        json={"code": "# typing away"},
    )

    with client.session_factory() as db:
        from app.models import ExerciseSession

        assert db.get(ExerciseSession, session_id).last_activity_at == before


# --- the journal -----------------------------------------------------------


def test_journal_entry_saves_and_updates_in_place(client):
    headers = login(client)
    exercise, _ = open_exercise(client, headers)

    first = client.post(
        "/reflections",
        headers=headers,
        json={
            "exercise_id": exercise["id"],
            "what_i_tried": "a for loop",
            "where_i_got_stuck": "the boundary",
            "how_i_fixed_it": "",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/reflections",
        headers=headers,
        json={
            "exercise_id": exercise["id"],
            "what_i_tried": "a for loop",
            "where_i_got_stuck": "the boundary",
            "how_i_fixed_it": "used < instead of <=",
        },
    )
    # Upsert, not append -- one honest account per exercise, revisable.
    assert second.json()["id"] == first.json()["id"]
    assert len(client.get("/reflections", headers=headers).json()) == 1


def test_journal_is_private_to_its_author(client):
    headers = login(client)
    exercise, _ = open_exercise(client, headers)
    client.post(
        "/reflections",
        headers=headers,
        json={"exercise_id": exercise["id"], "what_i_tried": "something personal"},
    )

    other = auth(register(client, email="nosy2@example.com"))
    assert client.get("/reflections", headers=other).json() == []


def test_journal_entry_can_be_deleted_for_real(client):
    headers = login(client)
    exercise, _ = open_exercise(client, headers)
    created = client.post(
        "/reflections",
        headers=headers,
        json={"exercise_id": exercise["id"], "what_i_tried": "regret this"},
    ).json()

    assert (
        client.delete(f"/reflections/{created['id']}", headers=headers).status_code
        == 204
    )
    assert client.get("/reflections", headers=headers).json() == []

    with client.session_factory() as db:
        from app.models import Reflection

        # Actually gone, not soft-deleted. Promising deletion while keeping the
        # text would be a lie to the participant and to the ethics committee.
        assert db.get(Reflection, created["id"]) is None


def test_cannot_delete_someone_elses_entry(client):
    headers = login(client)
    exercise, _ = open_exercise(client, headers)
    created = client.post(
        "/reflections",
        headers=headers,
        json={"exercise_id": exercise["id"], "what_i_tried": "mine"},
    ).json()

    other = auth(register(client, email="nosy3@example.com"))
    # 404 rather than 403: don't confirm that someone else's entry exists.
    assert client.delete(f"/reflections/{created['id']}", headers=other).status_code == 404


def test_all_new_endpoints_require_auth(client):
    assert client.get("/reflections").status_code == 401
    assert client.post("/reflections", json={}).status_code == 401
    assert client.get("/exercises/expired-quests/draft").status_code == 401
    assert (
        client.put(
            "/exercises/expired-quests/draft", json={"code": "x"}
        ).status_code
        == 401
    )
    assert (
        client.patch(
            "/auth/me/consent", json={"consent_to_research": True}
        ).status_code
        == 401
    )
