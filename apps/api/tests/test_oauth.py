"""Google/Microsoft sign-in.

No network anywhere in here. The two calls that leave the machine --
`exchange_code` and `fetch_profile` -- are stubbed, and everything else is
exercised for real: the redirect we build, the state check, the cookie, and the
account matching that decides whose account someone lands in.

That account matching is the part worth testing hardest. Getting it wrong does
not produce a broken page, it produces a student signed into somebody else's
work, so the unverified-email case has a test of its own.
"""

from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from sqlalchemy import select

from app.auth import ALGORITHM, UNUSABLE_PASSWORD, verify_password
from app.config import get_settings
from app.models import OAuthAccount, User
from app.oauth import OAuthError, Profile, get_provider, profile_from, providers
from app.routers.oauth import FLOW_COOKIE, _LinkRefused, _sign_in_or_create


@pytest.fixture
def google(monkeypatch):
    """Switch Google sign-in on for one test."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- what's switched on -----------------------------------------------------


def test_unconfigured_providers_are_flagged_in_development(client):
    """In dev they are listed but marked unusable, so the UI can say why.

    The conftest runs with ENVIRONMENT=development. A developer who has set no
    credentials should see the buttons greyed out rather than see nothing at all
    and have to go looking for the reason.
    """
    body = client.get("/auth/oauth/providers").json()
    assert [p["key"] for p in body["providers"]] == [
        "google",
        "microsoft",
        "apple",
        "github",
        "facebook",
        "university",
    ]
    assert all(p["configured"] is False for p in body["providers"])


def test_unconfigured_providers_are_hidden_in_production(client, monkeypatch):
    """A real user must never be shown a button that cannot work."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a-real-secret-for-this-test")
    get_settings.cache_clear()
    try:
        body = client.get("/auth/oauth/providers").json()
        assert body["providers"] == []
    finally:
        get_settings.cache_clear()


def test_start_404s_for_unconfigured_provider(client):
    """Listed in dev, but still not startable -- the flag is cosmetic only."""
    assert client.get("/auth/oauth/google/start").status_code == 404


def test_configured_provider_is_listed(client, google):
    body = client.get("/auth/oauth/providers").json()
    google_entry = next(p for p in body["providers"] if p["key"] == "google")
    assert google_entry == {"key": "google", "label": "Google", "configured": True}
    # Microsoft has no credentials, so it cannot be started...
    assert get_provider("microsoft") is None
    # ...and is listed only as the unusable placeholder.
    microsoft = next(p for p in body["providers"] if p["key"] == "microsoft")
    assert microsoft["configured"] is False


# --- the outbound redirect --------------------------------------------------


def test_start_redirects_to_provider_with_pkce(client, google):
    response = client.get("/auth/oauth/google/start", follow_redirects=False)
    assert response.status_code == 302

    target = urlparse(response.headers["location"])
    query = parse_qs(target.query)
    assert target.netloc == "accounts.google.com"
    assert query["client_id"] == ["test-client-id"]
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0]
    # The verifier itself must never be sent at this stage -- that would defeat
    # the entire point of PKCE.
    assert "code_verifier" not in query
    assert query["redirect_uri"] == ["http://localhost:8000/auth/oauth/google/callback"]
    # A shared machine must not silently reuse whoever signed in last.
    assert query["prompt"] == ["select_account"]

    assert FLOW_COOKIE in response.cookies


# --- the inbound callback ---------------------------------------------------


def _redirected_to(response) -> tuple[str, dict]:
    parsed = urlparse(response.headers["location"])
    return parsed.path, parse_qs(parsed.query)


def test_callback_without_a_flow_cookie_is_refused(client, google):
    response = client.get(
        "/auth/oauth/google/callback",
        params={"code": "abc", "state": "made-up"},
        follow_redirects=False,
    )
    path, query = _redirected_to(response)
    assert path == "/login"
    assert "expired" in query["error"][0]


def test_callback_rejects_a_state_that_isnt_ours(client, google, monkeypatch):
    """The CSRF guard: a code delivered with the wrong state is thrown away."""
    client.get("/auth/oauth/google/start", follow_redirects=False)

    async def unreachable(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("state check should have stopped the exchange")

    monkeypatch.setattr("app.oauth.exchange_code", unreachable)

    response = client.get(
        "/auth/oauth/google/callback",
        params={"code": "abc", "state": "not-the-state-we-issued"},
        follow_redirects=False,
    )
    path, query = _redirected_to(response)
    assert path == "/login"
    assert "couldn't be verified" in query["error"][0]


def test_callback_reports_a_cancelled_sign_in(client, google):
    response = client.get(
        "/auth/oauth/google/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )
    path, query = _redirected_to(response)
    assert path == "/login"
    assert query["error"] == ["Sign-in was cancelled."]


def test_full_sign_in_creates_an_account_and_returns_a_token(
    client, google, monkeypatch
):
    start = client.get("/auth/oauth/google/start", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]

    async def fake_exchange(provider, code, verifier):
        assert code == "one-time-code"
        assert verifier  # the verifier we stashed in the cookie came back to us
        return {"access_token": "provider-access-token"}

    async def fake_profile(provider, tokens, form=None):
        assert tokens["access_token"] == "provider-access-token"
        return Profile(
            subject="google-subject-1",
            email="newcomer@example.com",
            display_name="Newcomer",
            email_verified=True,
        )

    monkeypatch.setattr("app.oauth.exchange_code", fake_exchange)
    monkeypatch.setattr("app.oauth.fetch_profile", fake_profile)

    response = client.get(
        "/auth/oauth/google/callback",
        params={"code": "one-time-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 302

    location = response.headers["location"]
    # The token must be in the fragment, never the query string -- a query
    # string would put it in server logs and Referer headers.
    assert "/auth/callback#token=" in location
    assert "?token=" not in location

    # Parsed as a proper fragment, not split on "#token=" -- there is a second
    # parameter after it now.
    fragment = parse_qs(urlparse(location).fragment)
    granted = fragment["token"][0]
    payload = jwt.decode(granted, get_settings().secret_key, algorithms=[ALGORITHM])

    # A brand-new account, so the web app should send them to the welcome step.
    assert fragment["new"] == ["1"]

    with client.session_factory() as db:
        user = db.get(User, payload["sub"])
        assert user is not None
        assert user.email == "newcomer@example.com"
        assert user.display_name == "Newcomer"
        # Counterbalancing is assigned here exactly as at password signup; an
        # ungrouped participant is invisible to the study.
        assert user.counterbalance_group in {"A", "B"}
        # Signing in is not consenting to research.
        assert user.consented_at is None

        link = db.scalar(
            select(OAuthAccount).where(OAuthAccount.subject == "google-subject-1")
        )
        assert link is not None and link.user_id == user.id


# --- account matching -------------------------------------------------------


def _profile(**overrides) -> Profile:
    base = dict(
        subject="subject-1",
        email="person@example.com",
        display_name="Person",
        email_verified=True,
    )
    base.update(overrides)
    return Profile(**base)


def test_returning_user_is_matched_on_subject_not_email(client):
    """A changed email address must not create a second account."""
    with client.session_factory() as db:
        first, created = _sign_in_or_create(db, "google", _profile())
        assert created is True
        again, created_again = _sign_in_or_create(
            db, "google", _profile(email="renamed@example.com")
        )
        assert again.id == first.id
        # Not a signup -- they must not be sent through the welcome step again.
        assert created_again is False
        assert db.query(OAuthAccount).count() == 1


def test_verified_email_links_to_an_existing_password_account(client):
    """Someone who signed up with a password can later use the button."""
    with client.session_factory() as db:
        existing = db.scalar(select(User).where(User.email == "student@example.com"))
        assert existing is not None

        user, created = _sign_in_or_create(
            db, "google", _profile(email="student@example.com", email_verified=True)
        )
        assert user.id == existing.id
        # Linking a provider to an account someone already had is not a signup.
        assert created is False
        # Linking must not disturb the password they already had.
        assert verify_password("password123", user.password_hash)


def test_unverified_email_cannot_claim_an_existing_account(client):
    """The account-takeover case, and the reason email_verified exists.

    Register at a provider using someone else's address, press the button, and
    without this check you inherit their account.
    """
    with client.session_factory() as db:
        with pytest.raises(_LinkRefused):
            _sign_in_or_create(
                db,
                "google",
                _profile(email="student@example.com", email_verified=False),
            )

        # And nothing was linked on the way out.
        assert db.query(OAuthAccount).count() == 0


def test_oauth_only_account_cannot_be_password_logged_into(client):
    """An account with no password must 401, not 500.

    `password_hash` holds a marker that is not a bcrypt hash. Passlib raises on
    those, so without the guard in verify_password this route would return a
    server error and leak that the account exists.
    """
    with client.session_factory() as db:
        _sign_in_or_create(db, "google", _profile(email="button@example.com"))
        user = db.scalar(select(User).where(User.email == "button@example.com"))
        assert user.password_hash == UNUSABLE_PASSWORD

    response = client.post(
        "/auth/login", json={"email": "button@example.com", "password": "anything"}
    )
    assert response.status_code == 401
    assert not verify_password("anything", UNUSABLE_PASSWORD)
    assert not verify_password("", UNUSABLE_PASSWORD)


# --- claim handling ---------------------------------------------------------


def test_google_email_verification_is_read_from_the_claim():
    google = providers()["google"]
    verified = profile_from(google, {"sub": "1", "email": "a@b.com", "name": "A"})
    assert verified.email_verified is False, "absent claim must not mean verified"

    claimed = profile_from(
        google, {"sub": "1", "email": "a@b.com", "email_verified": True}
    )
    assert claimed.email_verified is True


def test_microsoft_emails_are_accepted_as_verified():
    """Microsoft returns no email_verified claim; see the note in oauth.py."""
    profile = profile_from(
        providers()["microsoft"], {"sub": "9", "email": "a@outlook.com"}
    )
    assert profile.email_verified is True


def test_microsoft_falls_back_to_preferred_username():
    profile = profile_from(
        providers()["microsoft"], {"sub": "9", "preferred_username": "A@Outlook.com"}
    )
    assert profile.email == "a@outlook.com"  # normalised to lower case


def test_missing_email_is_a_clear_error():
    with pytest.raises(OAuthError, match="no email address"):
        profile_from(providers()["google"], {"sub": "9"})


def test_missing_name_falls_back_to_the_local_part():
    """And capitalises it -- a local part is nearly always lowercase, which is
    exactly the case app/names.py exists to fix."""
    profile = profile_from(providers()["google"], {"sub": "9", "email": "kai@b.com"})
    assert profile.display_name == "Kai"


# --- the providers added later ---------------------------------------------


def test_apple_spells_email_verified_as_a_string():
    """Apple sends "true", not true. Read it as a boolean and every Apple user
    is treated as unverified, and can never link to an existing account."""
    apple = providers()["apple"]
    assert profile_from(
        apple, {"sub": "a1", "email": "x@privaterelay.appleid.com", "email_verified": "true"}
    ).email_verified is True
    assert (
        profile_from(apple, {"sub": "a1", "email": "x@y.com", "email_verified": "false"})
        .email_verified
        is False
    )


def test_github_uses_the_numeric_id_as_the_subject():
    """GitHub has no `sub`; its immutable id is `id`. The login name is not a
    substitute -- users rename themselves and the name is then reusable."""
    profile = profile_from(
        providers()["github"],
        {"id": 4823, "email": "dev@example.com", "email_verified": True, "name": "Dev"},
    )
    assert profile.subject == "4823"


def test_facebook_and_microsoft_emails_are_taken_as_verified():
    for key in ("facebook", "microsoft"):
        profile = profile_from(providers()[key], {"sub": "1", "email": "a@b.com"})
        assert profile.email_verified is True, key


def test_university_label_names_the_button(monkeypatch):
    """The tile shows this under a "Sign in with" caption, so it is a name the
    user reads and a deployment is expected to set."""
    assert providers()["university"].label == "University"

    monkeypatch.setenv("UNIVERSITY_LABEL", "Northeastern")
    get_settings.cache_clear()
    try:
        assert providers()["university"].label == "Northeastern"
    finally:
        get_settings.cache_clear()


def test_apple_needs_all_four_settings(monkeypatch):
    """Three of the four is not "nearly configured", it is unconfigured."""
    for name in ("APPLE_CLIENT_ID", "APPLE_TEAM_ID", "APPLE_KEY_ID"):
        monkeypatch.setenv(name, "x")
    get_settings.cache_clear()
    try:
        assert get_settings().apple_ready is False
        assert get_provider("apple") is None
        monkeypatch.setenv("APPLE_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\\nx\\n-----END PRIVATE KEY-----")
        get_settings.cache_clear()
        assert get_settings().apple_ready is True
        # The escaped newlines a .env file forces on you are restored.
        assert "\n" in get_settings().apple_private_key_pem
    finally:
        get_settings.cache_clear()


def test_apple_client_secret_is_signed_with_the_p8_key(monkeypatch):
    """Apple's secret is an ES256 JWT we mint, not a string Apple gives us."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    ).decode()

    monkeypatch.setenv("APPLE_CLIENT_ID", "com.codejourney.web")
    monkeypatch.setenv("APPLE_TEAM_ID", "TEAM123456")
    monkeypatch.setenv("APPLE_KEY_ID", "KEY1234567")
    monkeypatch.setenv("APPLE_PRIVATE_KEY", pem)
    get_settings.cache_clear()
    try:
        from app.oauth import apple_client_secret

        secret = apple_client_secret()
        header = jwt.get_unverified_header(secret)
        assert header["alg"] == "ES256"
        assert header["kid"] == "KEY1234567"

        claims = jwt.decode(secret, key.public_key(), algorithms=["ES256"], audience="https://appleid.apple.com")
        assert claims["iss"] == "TEAM123456"
        assert claims["sub"] == "com.codejourney.web"
        assert claims["exp"] > claims["iat"]
    finally:
        get_settings.cache_clear()


def test_a_broken_apple_key_is_a_readable_error(monkeypatch):
    """The common failure is a mangled .p8 paste, and an ASN.1 stack trace
    tells whoever set it up nothing."""
    monkeypatch.setenv("APPLE_CLIENT_ID", "com.codejourney.web")
    monkeypatch.setenv("APPLE_TEAM_ID", "TEAM123456")
    monkeypatch.setenv("APPLE_KEY_ID", "KEY1234567")
    monkeypatch.setenv("APPLE_PRIVATE_KEY", "not a key at all")
    get_settings.cache_clear()
    try:
        from app.oauth import apple_client_secret

        with pytest.raises(OAuthError, match="signing key couldn't be used"):
            apple_client_secret()
    finally:
        get_settings.cache_clear()


def test_github_prefers_the_primary_verified_address():
    from app.oauth import pick_github_email

    assert pick_github_email(
        [
            {"email": "old@example.com", "primary": False, "verified": True},
            {"email": "me@example.com", "primary": True, "verified": True},
        ]
    ) == ("me@example.com", True)

    # Primary but unverified: fall through to the verified one.
    assert pick_github_email(
        [
            {"email": "unconfirmed@example.com", "primary": True, "verified": False},
            {"email": "confirmed@example.com", "primary": False, "verified": True},
        ]
    ) == ("confirmed@example.com", True)


def test_github_never_picks_an_unverified_address():
    """Anyone can add any address to a GitHub account; only GitHub confirming it
    makes it evidence of anything."""
    from app.oauth import pick_github_email

    assert pick_github_email(
        [{"email": "victim@example.com", "primary": True, "verified": False}]
    ) == ("", False)
    assert pick_github_email([]) == ("", False)


def test_apple_reads_the_display_name_sent_once_in_the_callback_body():
    """Apple sends the name in the first callback's form and never again.

    Miss it and the account is nameless forever, so this is the one chance.
    """
    from app.oauth import _apple_profile

    id_token = jwt.encode(
        {"sub": "apple-1", "email": "kai@icloud.com", "email_verified": "true"},
        "irrelevant",
        algorithm="HS256",
    )
    profile = _apple_profile(
        providers()["apple"],
        {"id_token": id_token},
        {"user": '{"name": {"firstName": "Kai", "lastName": "Ng"}}'},
    )
    assert profile.display_name == "Kai Ng"
    assert profile.subject == "apple-1"

    # Later sign-ins carry no name; the address's local part stands in.
    returning = _apple_profile(providers()["apple"], {"id_token": id_token}, {})
    assert returning.display_name == "Kai"

    # A mangled name payload must not fail the sign-in.
    broken = _apple_profile(
        providers()["apple"], {"id_token": id_token}, {"user": "{not json"}
    )
    assert broken.display_name == "Kai"


def test_apple_posts_its_callback_instead_of_redirecting(client):
    """Apple uses response_mode=form_post, so the callback must accept POST.

    Unconfigured here, so this only proves the route exists and refuses
    cleanly -- a 405 would mean every Apple sign-in dead-ends.
    """
    response = client.post(
        "/auth/oauth/apple/callback",
        data={"code": "x", "state": "y"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.headers["location"]
