"""The "Continue with Google / Microsoft" flow.

Read top to bottom: `providers` says what is switched on, `start` sends the
browser off, `callback` catches it coming back. The provider specifics live in
app/oauth.py so this file stays a readable sequence of steps.

Two decisions worth knowing before changing anything here.

**The pending flow lives in a signed cookie, not the database.** Between `start`
and `callback` we have to remember one `state` value and one PKCE verifier for a
few minutes. A table for that would need cleanup, and a server-side session
store is exactly what this API avoided by using bearer tokens (see app/auth.py).
A short-lived JWT in an httpOnly cookie needs neither.

**The finished token comes back in a URL fragment, not a query string.**
`/auth/callback#token=...` rather than `?token=...`. Fragments are never sent to
a server, so the access token stays out of web-server logs, out of `Referer`
headers on the next click, and out of anything that records URLs. The SPA reads
it with JavaScript and clears it immediately.
"""

from __future__ import annotations

import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlencode

import jwt
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import oauth
from ..auth import ALGORITHM, UNUSABLE_PASSWORD, create_access_token
from ..config import get_settings
from ..db import get_db
from ..models import OAuthAccount, User

router = APIRouter(prefix="/auth/oauth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]

#: Name of the cookie carrying the in-flight flow. Prefixed like the token key
#: in the web app so it is obvious whose it is in a browser inspector.
FLOW_COOKIE = "codejourney_oauth_flow"
#: How long someone has to finish signing in at the provider before the attempt
#: goes stale. Long enough to create an account mid-flow; short enough that a
#: forgotten tab isn't a standing invitation.
FLOW_TTL_MINUTES = 15


class ProviderOut(BaseModel):
    key: str
    label: str
    #: False means "we know about this provider but it has no credentials".
    #: Only ever sent in development -- see list_providers.
    configured: bool = True


class ProvidersOut(BaseModel):
    providers: list[ProviderOut]


@router.get("/providers", response_model=ProvidersOut)
def list_providers() -> ProvidersOut:
    """Which sign-in buttons the front end should render.

    In production, only providers with both a client id and a secret. The web
    app draws its buttons from this list rather than hard-coding two, so a
    deployment without Microsoft credentials shows one button instead of a
    second that leads to an error page.

    In development, unconfigured providers are listed too, flagged
    `configured: false`, and the web app draws them disabled with a note saying
    what is missing. Hiding them completely is right for a student and wrong for
    whoever is building this: "the button isn't there and nothing says why" is a
    genuinely confusing half hour, and the fix is to say why.
    """
    dev = get_settings().environment == "development"
    out: list[ProviderOut] = []
    for key, provider in oauth.providers().items():
        ready = oauth.get_provider(key) is not None
        if ready or dev:
            out.append(
                ProviderOut(key=key, label=provider.label, configured=ready)
            )
    return ProvidersOut(providers=out)


def _web_url(path: str, **params: str) -> str:
    base = get_settings().web_app_url.rstrip("/")
    query = f"?{urlencode(params)}" if params else ""
    return f"{base}{path}{query}"


def _fail(mode: str, message: str) -> RedirectResponse:
    """Send the user back to the form they came from, with something readable.

    Never surfaces the provider's own error text -- those are written for
    whoever registered the OAuth app, and read as gibberish to a student who
    just wanted to log in.
    """
    path = "/signup" if mode == "signup" else "/login"
    return RedirectResponse(_web_url(path, error=message), status_code=302)


@router.get("/{provider_key}/start")
async def start(provider_key: str, mode: str = "login") -> Response:
    """Send the browser to the provider's consent screen."""
    provider = oauth.get_provider(provider_key)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That sign-in method isn't available.",
        )

    settings = get_settings()
    try:
        # The university provider's endpoints come from its discovery document
        # and aren't known until now.
        provider = await oauth.resolve(provider)
        client_id, _ = oauth.client_credentials(provider)
    except oauth.OAuthError:
        return _fail(mode, f"{provider.label} sign-in isn't available right now.")

    state = secrets.token_urlsafe(32)
    verifier = oauth.new_verifier()

    params = {
        "client_id": client_id,
        "redirect_uri": oauth.redirect_uri(provider.key),
        "response_type": "code",
        "scope": provider.scope,
        "state": state,
        "code_challenge": oauth.challenge_for(verifier),
        "code_challenge_method": "S256",
        **provider.extra_authorize,
    }
    if provider.style == "oidc":
        # Ask for an account chooser rather than silently reusing whichever
        # account the browser is already signed into. On a shared lab machine,
        # silently signing someone into the previous user's account is the worst
        # possible outcome. Only the OIDC providers accept this parameter --
        # Apple and GitHub reject or ignore it.
        params["prompt"] = "select_account"
    if provider.response_mode != "query":
        params["response_mode"] = provider.response_mode

    response = RedirectResponse(
        f"{provider.authorize_url}?{urlencode(params)}", status_code=302
    )

    now = datetime.now(timezone.utc)
    flow = jwt.encode(
        {
            "provider": provider.key,
            "state": state,
            "verifier": verifier,
            "mode": mode,
            "exp": now + timedelta(minutes=FLOW_TTL_MINUTES),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    # SameSite has to match how the provider sends the user back.
    #
    # Lax, not Strict, for the usual case: the provider redirects the browser to
    # us as a top-level GET, which Lax allows and Strict would drop -- taking the
    # state with it and breaking every sign-in.
    #
    # Apple posts a form instead, and a cross-site POST does NOT carry a Lax
    # cookie. That needs None, which browsers only honour together with Secure,
    # which needs HTTPS -- which Apple demands anyway, since it refuses
    # plain-http redirect URIs including localhost.
    cross_site_post = provider.response_mode == "form_post"
    response.set_cookie(
        FLOW_COOKIE,
        flow,
        max_age=FLOW_TTL_MINUTES * 60,
        httponly=True,
        samesite="none" if cross_site_post else "lax",
        secure=cross_site_post or settings.environment != "development",
        path="/auth/oauth",
    )
    return response


@router.get("/{provider_key}/callback")
async def callback(
    provider_key: str,
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    flow_cookie: Annotated[str | None, Cookie(alias=FLOW_COOKIE)] = None,
) -> Response:
    """Catch the browser coming back, and turn the code into a session."""
    return await _complete(db, provider_key, code, state, error, flow_cookie, {})


@router.post("/{provider_key}/callback")
async def callback_post(
    provider_key: str,
    db: DbSession,
    request: Request,
    flow_cookie: Annotated[str | None, Cookie(alias=FLOW_COOKIE)] = None,
) -> Response:
    """The same thing, for providers that POST their result instead.

    Apple, with `response_mode=form_post`. It is the only reason this route
    exists, and the only reason it is needed: Apple sends the display name in
    this body and nowhere else, which is why the form is threaded through to
    fetch_profile rather than discarded.
    """
    form = {key: str(value) for key, value in (await request.form()).items()}
    return await _complete(
        db,
        provider_key,
        form.get("code"),
        form.get("state"),
        form.get("error"),
        flow_cookie,
        form,
    )


async def _complete(
    db: Session,
    provider_key: str,
    code: str | None,
    state: str | None,
    error: str | None,
    flow_cookie: str | None,
    form: dict[str, str],
) -> Response:
    provider = oauth.get_provider(provider_key)
    if provider is None:
        return _fail("login", "That sign-in method isn't available.")

    settings = get_settings()

    # The provider itself said no -- most often the user pressed cancel.
    if error:
        return _fail("login", "Sign-in was cancelled.")

    if not code or not state or not flow_cookie:
        return _fail("login", "That sign-in link has expired. Please try again.")

    try:
        flow = jwt.decode(flow_cookie, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return _fail("login", "That sign-in link has expired. Please try again.")

    mode = flow.get("mode", "login")

    # CSRF: the state we are handed must be the one we minted, for the provider
    # we minted it for. `compare_digest` rather than `==` so a mismatch cannot
    # be found a character at a time by timing the response.
    if flow.get("provider") != provider.key or not secrets.compare_digest(
        str(flow.get("state", "")), state
    ):
        return _fail(mode, "That sign-in couldn't be verified. Please try again.")

    try:
        provider = await oauth.resolve(provider)
        tokens = await oauth.exchange_code(provider, code, flow["verifier"])
        profile = await oauth.fetch_profile(provider, tokens, form)
    except oauth.OAuthError:
        return _fail(mode, f"Couldn't finish signing in with {provider.label}.")
    except Exception:
        # A timeout or DNS failure reaching the provider. Same message: from
        # the user's side "it didn't work, try again" is the whole truth.
        return _fail(mode, f"Couldn't reach {provider.label}. Please try again.")

    try:
        user, created = _sign_in_or_create(db, provider.key, profile)
    except _LinkRefused as refusal:
        return _fail(mode, str(refusal))

    # The token rides in the fragment, deliberately -- see the module docstring.
    # `new=1` tells the web app this account did not exist a moment ago, so it
    # can send them to the welcome step. It is a hint for routing only; nothing
    # is authorised by it, so it is fine for it to be visible.
    destination = f"{_web_url('/auth/callback')}#token={create_access_token(user)}"
    if created:
        destination += "&new=1"
    response = RedirectResponse(destination, status_code=302)
    # One-time: the flow is spent, and leaving it set would let a stale verifier
    # be replayed against a second callback.
    response.delete_cookie(FLOW_COOKIE, path="/auth/oauth")
    return response


class _LinkRefused(Exception):
    """We know who they are, but linking would be unsafe. Carries user-facing text."""


def _sign_in_or_create(
    db: Session, provider_key: str, profile: oauth.Profile
) -> tuple[User, bool]:
    """Find the CodeJourney account for this identity, creating one if needed.

    Returns (user, created). `created` is True only when the account did not
    exist at all -- linking a provider to someone's existing password account is
    not a signup, and must not send them back through the welcome step.

    Three cases, in order:

      1. We have seen this provider identity before -> sign that user in. Matched
         on the provider's subject, never the email, so a changed or recycled
         address cannot move someone into the wrong account.
      2. The email matches an existing account -> link the identity to it, so
         someone who signed up with a password can later use the button and land
         in the same account rather than a confusing duplicate. Only when the
         provider verified the address.
      3. Nobody matches -> create an account with no password.
    """
    link = db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider_key,
            OAuthAccount.subject == profile.subject,
        )
    )
    if link is not None:
        user = db.get(User, link.user_id)
        if user is not None:
            return user, False
        # The account was deleted but its link outlived it. Drop the orphan and
        # fall through to make a fresh one.
        db.delete(link)
        db.flush()

    existing = db.scalar(select(User).where(User.email == profile.email))

    if existing is not None and not profile.email_verified:
        # The whole attack this guards: sign up at a provider using someone
        # else's address, press the button, inherit their account.
        raise _LinkRefused(
            "We can't match that to your CodeJourney account automatically. "
            "Please log in with your email and password."
        )

    created = existing is None
    if existing is not None:
        user = existing
    else:
        user = User(
            email=profile.email,
            # No password was ever chosen. See UNUSABLE_PASSWORD in app/auth.py.
            password_hash=UNUSABLE_PASSWORD,
            display_name=profile.display_name,
            # Assigned once at enrolment, exactly as in the password signup
            # path -- an account created here is a study participant like any
            # other, and must not be left ungrouped.
            counterbalance_group=random.choice(["A", "B"]),
            # Consent is never implied by a sign-in method. Opted out until they
            # say otherwise on /account, same as everyone else.
            consented_at=None,
        )
        db.add(user)
        db.flush()

    db.add(
        OAuthAccount(
            user_id=user.id,
            provider=provider_key,
            subject=profile.subject,
            email=profile.email,
        )
    )
    db.commit()
    db.refresh(user)
    return user, created
