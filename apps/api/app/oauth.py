"""Sign in with Google, Microsoft, Apple, GitHub, Facebook, or a university.

The OAuth 2.0 authorization code flow with PKCE. Three exchanges:

    1. we send the browser to the provider with a `state` and a code challenge
    2. the provider sends the browser back with a one-time `code`
    3. we swap that code -- server to server, with our client secret -- for an
       access token, and ask the provider who the user is

This module is the provider knowledge and the HTTP calls. routers/oauth.py is
the flow itself; keeping them apart means the router can be read as a sequence
of steps without provider trivia in the way.

**Step 3 is where they stop agreeing**, which is what `Provider.style` selects
between:

    oidc        Google, Microsoft, university -- GET the userinfo endpoint.
    apple       no userinfo endpoint exists; identity comes out of the id_token,
                and the display name arrives once, in the callback form body.
    github      not OIDC at all. Addresses are private by default, so the
                primary verified one needs a second call to /user/emails.
    facebook    OAuth 2.0 with a Graph call, and `email` may simply be absent.

**Why the ID token's signature is not checked.** Verifying it would mean
fetching and caching JWKS and pulling `cryptography` in for its own sake. It
buys nothing here: the token arrives on a TLS connection we opened, to a URL we
hard-coded, authenticated with our client secret. That is exactly the case
OpenID Connect Core 3.1.3.7 (item 6) permits skipping signature validation for.
Where a provider offers a userinfo endpoint we call it over that same trusted
channel instead, which is simpler to reason about than a JWKS cache with its own
failure modes.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field, replace

import httpx
import jwt

from .config import get_settings


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    authorize_url: str
    token_url: str
    scope: str
    #: How to turn an access token into a Profile. See the module docstring.
    style: str
    userinfo_url: str = ""
    #: Whether an address from this provider can be trusted to belong to the
    #: person signing in. See `Profile.email_verified` for why this matters.
    emails_always_verified: bool = False
    #: Apple posts its result as a form instead of a redirect with a query
    #: string, which changes both the route that catches it and the cookie
    #: policy that has to survive it.
    response_mode: str = "query"
    #: Extra parameters this provider needs on the authorize URL.
    extra_authorize: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Profile:
    """Who the provider says this is."""

    subject: str
    email: str
    display_name: str
    #: True only when the provider has confirmed the person controls this
    #: address. Everything hangs off it: an unverified address must never be
    #: allowed to claim an existing CodeJourney account, or "sign in with X"
    #: becomes a way to take over any account whose email you can guess.
    email_verified: bool


class OAuthError(Exception):
    """A provider refused us, or answered with something unusable."""


def _microsoft_base() -> str:
    tenant = get_settings().microsoft_tenant.strip() or "common"
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"


#: Pinned Graph version. Facebook retires these on a schedule, and an unpinned
#: URL would break silently on their timetable rather than ours.
FACEBOOK_API = "https://graph.facebook.com/v21.0"


def providers() -> dict[str, Provider]:
    """The provider registry, in the order the buttons are drawn.

    Built per call rather than at import time because several URLs embed
    configured values, and tests override settings.
    """
    ms = _microsoft_base()
    settings = get_settings()
    return {
        "google": Provider(
            key="google",
            label="Google",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scope="openid email profile",
            style="oidc",
            # Google reports this per account in the `email_verified` claim, so
            # we read the claim rather than assuming.
            emails_always_verified=False,
        ),
        "microsoft": Provider(
            key="microsoft",
            label="Microsoft",
            authorize_url=f"{ms}/authorize",
            token_url=f"{ms}/token",
            # Microsoft's OIDC userinfo lives on Graph, not on login.microsoft.
            userinfo_url="https://graph.microsoft.com/oidc/userinfo",
            scope="openid email profile",
            style="oidc",
            # Microsoft returns no `email_verified` claim, so there is nothing
            # to read and we have to decide. We accept, because Microsoft
            # verifies an address before it can sign in either way: a personal
            # account's alias must be confirmed by email first, and a
            # work/school address only exists inside a domain the tenant proved
            # it owns.
            emails_always_verified=True,
        ),
        "apple": Provider(
            key="apple",
            label="Apple",
            authorize_url="https://appleid.apple.com/auth/authorize",
            token_url="https://appleid.apple.com/auth/token",
            scope="name email",
            style="apple",
            # Apple states email_verified in the id_token, including for the
            # @privaterelay.appleid.com addresses Hide My Email generates --
            # those are real, deliverable, and Apple's to vouch for.
            emails_always_verified=False,
            # Required by Apple whenever `name` or `email` is in scope.
            response_mode="form_post",
        ),
        "github": Provider(
            key="github",
            label="GitHub",
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            # read:user for the profile, user:email because the address is not
            # in it unless the account made it public.
            scope="read:user user:email",
            style="github",
            # GitHub marks each address verified or not; we read that per
            # address and only ever accept a verified one.
            emails_always_verified=False,
        ),
        "facebook": Provider(
            key="facebook",
            label="Facebook",
            authorize_url=f"{FACEBOOK_API.replace('graph.', 'www.')}/dialog/oauth",
            token_url=f"{FACEBOOK_API}/oauth/access_token",
            userinfo_url=f"{FACEBOOK_API}/me?fields=id,name,email",
            scope="email public_profile",
            style="facebook",
            # Facebook confirms an address at registration and will not hand one
            # out otherwise. Same reasoning as Microsoft above; if it ever needs
            # tightening, this is the line.
            emails_always_verified=True,
        ),
        "university": Provider(
            key="university",
            # Whatever the deployment calls itself -- "Northeastern", "your
            # university". The button reads "Sign in with <this>".
            label=settings.university_label.strip() or "University",
            # Filled in from the issuer's discovery document by resolve().
            authorize_url="",
            token_url="",
            userinfo_url="",
            scope="openid email profile",
            style="oidc",
            emails_always_verified=False,
        ),
    }


def is_configured(key: str) -> bool:
    settings = get_settings()
    if key == "apple":
        return settings.apple_ready
    if key == "university":
        return settings.university_ready
    return settings.oauth_client(key) is not None


def get_provider(key: str) -> Provider | None:
    """A provider, but only if it has credentials configured."""
    provider = providers().get(key)
    if provider is None or not is_configured(key):
        return None
    return provider


def configured() -> list[Provider]:
    return [p for key, p in providers().items() if is_configured(key)]


def redirect_uri(provider_key: str) -> str:
    base = get_settings().api_base_url.rstrip("/")
    return f"{base}/auth/oauth/{provider_key}/callback"


# --- OIDC discovery, for the university provider ----------------------------
# Its endpoints belong to whoever runs the IdP, so they are read from the
# standard discovery document rather than configured by hand. Cached because it
# changes about never and a fetch per sign-in would be absurd.

_discovery: dict[str, dict] = {}


async def _discover(issuer: str) -> dict:
    if issuer in _discovery:
        return _discovery[issuer]
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.get(url)
    if response.status_code != 200:
        raise OAuthError(f"Couldn't read the OpenID configuration at {url}.")
    document = response.json()
    for required in ("authorization_endpoint", "token_endpoint", "userinfo_endpoint"):
        if not document.get(required):
            raise OAuthError(f"{url} is missing {required}.")
    _discovery[issuer] = document
    return document


async def resolve(provider: Provider) -> Provider:
    """Fill in any endpoints that have to be discovered at run time."""
    if provider.key != "university":
        return provider
    document = await _discover(get_settings().university_issuer)
    return replace(
        provider,
        authorize_url=document["authorization_endpoint"],
        token_url=document["token_endpoint"],
        userinfo_url=document["userinfo_endpoint"],
    )


# --- PKCE -------------------------------------------------------------------
# Proof Key for Code Exchange. We hold a secret (the verifier), send only its
# hash up front, and reveal the secret when redeeming the code. An attacker who
# intercepts the code cannot spend it without the verifier.
#
# GitHub's OAuth apps ignore these parameters rather than honouring them, and
# Apple does not document support either. Sending them is harmless in both
# cases, and both are confidential clients here -- a stolen code is useless
# without our client secret regardless.


def new_verifier() -> str:
    return secrets.token_urlsafe(64)


def challenge_for(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# --- Apple's generated client secret ----------------------------------------


def apple_client_secret() -> str:
    """Sign the short-lived ES256 JWT Apple accepts in place of a secret.

    Apple never issues a client secret. You register a key, download a .p8 once,
    and mint one of these per request. Apple caps their lifetime at six months;
    minted per sign-in here, expiring in five minutes, because there is nothing
    to gain from a long-lived one when generating it is this cheap.
    """
    settings = get_settings()
    if not settings.apple_ready:
        raise OAuthError("Apple sign-in is not configured.")

    now = int(time.time())
    try:
        return jwt.encode(
            {
                "iss": settings.apple_team_id.strip(),
                "iat": now,
                "exp": now + 300,
                "aud": "https://appleid.apple.com",
                "sub": settings.apple_client_id.strip(),
            },
            settings.apple_private_key_pem,
            algorithm="ES256",
            headers={"kid": settings.apple_key_id.strip()},
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as a readable OAuthError
        # Almost always a malformed .p8 paste. Saying so beats a stack trace
        # about ASN.1 that means nothing to whoever set this up.
        raise OAuthError(f"Apple's signing key couldn't be used: {exc}") from exc


def client_credentials(provider: Provider) -> tuple[str, str]:
    """The (client_id, client_secret) to present at the token endpoint."""
    if provider.key == "apple":
        return get_settings().apple_client_id.strip(), apple_client_secret()
    client = get_settings().oauth_client(provider.key)
    if client is None:
        raise OAuthError(f"{provider.label} sign-in is not configured.")
    return client


# --- the network calls ------------------------------------------------------


async def exchange_code(provider: Provider, code: str, verifier: str) -> dict:
    """Swap the one-time code for tokens. Returns the provider's whole response.

    The whole thing rather than just the access token, because Apple's identity
    is in the `id_token` beside it and there is no second call to get it from.
    """
    client_id, client_secret = client_credentials(provider)

    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.post(
            provider.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri(provider.key),
                "client_id": client_id,
                "client_secret": client_secret,
                "code_verifier": verifier,
            },
            # GitHub answers form-encoded unless asked otherwise, and would
            # otherwise arrive as an unparseable string.
            headers={"Accept": "application/json"},
        )

    if response.status_code != 200:
        # Provider error bodies carry a machine-readable `error` plus a
        # description written for a developer. Neither belongs in front of a
        # student, so this is detail for the router to swallow.
        raise OAuthError(
            f"{provider.label} rejected the sign-in "
            f"({response.status_code}: {response.text[:200]})"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise OAuthError(f"{provider.label} returned an unreadable response.") from exc

    if payload.get("error"):
        # GitHub reports failures with HTTP 200 and an `error` field, so the
        # status check above misses them entirely.
        raise OAuthError(f"{provider.label} rejected the sign-in: {payload['error']}")

    return payload


async def fetch_profile(
    provider: Provider, tokens: dict, form: dict[str, str] | None = None
) -> Profile:
    """Identify the user, however this particular provider wants to be asked.

    `form` is the callback's POST body, which only Apple sends and only to carry
    a display name on the very first authorisation.
    """
    if provider.style == "apple":
        return _apple_profile(provider, tokens, form or {})

    access_token = tokens.get("access_token")
    if not access_token:
        raise OAuthError(f"{provider.label} returned no access token.")

    if provider.style == "github":
        return await _github_profile(provider, access_token)

    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.get(provider.userinfo_url, headers=headers)

    if response.status_code != 200:
        raise OAuthError(
            f"Couldn't read your {provider.label} profile ({response.status_code})."
        )
    return profile_from(provider, response.json())


def _decode_unverified(id_token: str) -> dict:
    """Read an id_token's claims without checking its signature.

    Safe only because of where it came from -- see the module docstring. Never
    call this on a token that arrived from a browser.
    """
    return jwt.decode(id_token, options={"verify_signature": False})


def _apple_profile(provider: Provider, tokens: dict, form: dict[str, str]) -> Profile:
    id_token = tokens.get("id_token")
    if not id_token:
        raise OAuthError("Apple returned no identity token.")
    claims = _decode_unverified(id_token)

    # Apple sends the display name exactly once -- in the body of the first
    # callback, never in the id_token and never again. Miss it and the account
    # is nameless forever, so it is read here and falls back to the address.
    name = ""
    raw = form.get("user")
    if raw:
        try:
            parsed = json.loads(raw).get("name", {})
            name = " ".join(
                part
                for part in (parsed.get("firstName"), parsed.get("lastName"))
                if part
            ).strip()
        except (ValueError, AttributeError):
            # Malformed name payload is not worth failing a sign-in over.
            name = ""

    if name:
        claims = {**claims, "name": name}
    return profile_from(provider, claims)


def pick_github_email(entries: list[dict]) -> tuple[str, bool]:
    """Choose an address from GitHub's /user/emails, and say if it's verified.

    Primary and verified first, then any verified one. An unverified address is
    deliberately never chosen here: GitHub lets you add any address to an
    account and it sits there unverified, so accepting one would hand over the
    ability to claim a CodeJourney account by typing its owner's email into
    GitHub's settings page.
    """
    chosen = next(
        (e for e in entries if e.get("primary") and e.get("verified")),
        next((e for e in entries if e.get("verified")), None),
    )
    if not chosen or not chosen.get("email"):
        return "", False
    return str(chosen["email"]), True


async def _github_profile(provider: Provider, access_token: str) -> Profile:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient(timeout=10) as http:
        user = await http.get(provider.userinfo_url, headers=headers)
        if user.status_code != 200:
            raise OAuthError(f"Couldn't read your GitHub profile ({user.status_code}).")
        account = user.json()

        # `email` on the profile is null unless the account made it public, so
        # the address nearly always comes from this second call.
        emails = await http.get("https://api.github.com/user/emails", headers=headers)

    address, verified = "", False
    if emails.status_code == 200:
        address, verified = pick_github_email(emails.json())

    if not address:
        # The profile's own address, which is only set when the account chose to
        # make it public. GitHub does not say whether it is verified, so it is
        # treated as not -- enough to create a new account, never enough to
        # claim an existing one.
        address = account.get("email") or ""
        verified = False

    return profile_from(
        provider,
        {
            "sub": account.get("id"),
            "email": address,
            "email_verified": verified,
            "name": account.get("name") or account.get("login"),
        },
    )


def profile_from(provider: Provider, claims: dict) -> Profile:
    """Normalise a provider's claims into a Profile.

    Split out from the HTTP calls so the claim handling -- which is where the
    provider differences actually live -- is testable without a network.
    """
    subject = str(claims.get("sub") or claims.get("id") or "").strip()
    if not subject:
        raise OAuthError(f"{provider.label} did not identify the account.")

    # Microsoft personal accounts sometimes carry the address in
    # `preferred_username` rather than `email`.
    email = str(claims.get("email") or claims.get("preferred_username") or "").strip()
    if not email or "@" not in email:
        raise OAuthError(
            f"Your {provider.label} account has no email address we can use. "
            "You can still sign up with an email and password."
        )

    if provider.emails_always_verified:
        verified = True
    else:
        # Apple spells this claim as the string "true"; everyone else uses a
        # boolean. An absent claim means "not stated", which is treated as not
        # verified -- the conservative reading is the correct one here.
        raw = claims.get("email_verified")
        verified = raw is True or raw == "true"

    name = str(claims.get("name") or "").strip()
    if not name:
        # A display name is required by the User model, and "there" is a worse
        # greeting than the local part of their address.
        name = email.split("@", 1)[0]

    return Profile(
        subject=subject,
        email=email.lower(),
        display_name=name[:120],
        email_verified=verified,
    )
