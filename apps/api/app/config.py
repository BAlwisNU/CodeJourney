from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://codejourney:codejourney@localhost:5432/codejourney"

    # Dev default only. docker-compose sets this; production must set it or the
    # check in main.py refuses to start.
    secret_key: str = "dev-only-not-a-real-secret"
    access_token_ttl_minutes: int = 60 * 12

    # Production origins. Must be set explicitly outside development.
    cors_origins: list[str] = []

    # In development, allow any localhost port. Vite walks forward from 5173 when
    # the port is taken, and Expo's dev client picks its own -- pinning a list
    # here means the API silently CORS-blocks the frontend on any machine that
    # happens to have something else running. That failure looks like a broken
    # app, not a config problem, and it costs someone an afternoon.
    # Never used outside development: see main.py.
    cors_origin_regex_dev: str = r"http://(localhost|127\.0\.0\.1):\d+"

    # Pinned in lockstep with the Pyodide version in the web app. These two MUST
    # track the same CPython minor version -- Pyodide 0.27.x ships CPython 3.12,
    # so the sandbox runs python:3.12-slim. Bumping one without the other
    # reintroduces the run/submit divergence the shared harness exists to prevent.
    # See docs/architecture.md, "The divergence rule".
    python_version: str = "3.12"
    pyodide_version: str = "0.27.2"

    sandbox_image: str = "codejourney-sandbox:3.12"
    sandbox_timeout_seconds: int = 5

    environment: str = "development"

    # The reflection tutor. This is the ONE place an LLM enters the platform, and
    # it is deliberately kept away from the private journal (see
    # routers/reflections.py). The tutor only ever sees the lesson, the student's
    # own code, and how their attempts went -- never the tried/stuck/fixed text.
    #
    # No key => the tutor is switched off and its endpoints degrade to a friendly
    # "not set up yet" message rather than a 500. Set ANTHROPIC_API_KEY to turn it
    # on. The key is read from the environment; it is never committed.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"

    # --- the research dashboard ----------------------------------------------
    #
    # /instructor is the study's analytics: every student in the database, their
    # hint depth, and their private journals -- not one class, all of them. It
    # used to be gated on "has the instructor role", which was tolerable only
    # while becoming an instructor took a secret.
    #
    # Teachers now sign themselves up, so the role is no longer a credential and
    # this needs its own. An allowlist of email addresses, and empty means
    # nobody: a deployment that has not named its researchers does not have any,
    # and teaching is entirely served by /teacher, which is scoped to a class.
    research_emails: list[str] = []


    # --- "Continue with Google" / "Continue with Microsoft" -----------------
    #
    # Both are off until a client id AND secret are set for them. An
    # unconfigured provider is not listed by /auth/oauth/providers, so its
    # button never renders, and its endpoints 404 rather than bouncing someone
    # to a provider that will reject them. Same posture as the tutor above:
    # absent credentials degrade to "this feature isn't set up", never a 500.
    #
    # Nothing here is committed. Set them in apps/api/.env, which is gitignored.
    google_client_id: str = ""
    google_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    # "common" accepts personal accounts (outlook.com, hotmail.com, live.com)
    # AND work/school accounts. Use a tenant id instead to restrict sign-in to
    # one organisation -- which is what a university deployment would want.
    microsoft_tenant: str = "common"

    github_client_id: str = ""
    github_client_secret: str = ""

    facebook_client_id: str = ""
    facebook_client_secret: str = ""

    # Apple is the awkward one. Its "client secret" is not a string you are
    # given -- it is an ES256 JWT you sign yourself, from a .p8 private key,
    # valid six months at most. So it takes four values instead of two. See
    # oauth.apple_client_secret().
    #
    # apple_client_id is the *Services ID* (e.g. com.codejourney.web), not the
    # App ID. Apple also refuses plain-http redirect URIs, localhost included,
    # so this provider cannot be exercised without HTTPS.
    apple_client_id: str = ""
    apple_team_id: str = ""
    apple_key_id: str = ""
    # PEM contents of the .p8 file. Newlines survive .env quoting badly, so a
    # literal "\n" is accepted and unescaped in apple_private_key_pem below.
    apple_private_key: str = ""

    # A university's own login, via whatever OpenID Connect provider it runs.
    # Endpoints are read from the issuer's discovery document rather than
    # configured one by one, so this works for Entra, Okta, Keycloak, Shibboleth
    # with an OIDC front end, and anything else that speaks the standard.
    #
    # Northeastern and most US universities front their SSO with Entra, which
    # the Microsoft button already reaches -- this exists for deployments that
    # want their own branded button, or an IdP Microsoft doesn't cover.
    # Shown on the tile, under a "Sign in with" caption -- so this is a name,
    # not a phrase. Deployments should set their own ("Northeastern").
    university_label: str = "University"
    university_issuer: str = ""
    university_client_id: str = ""
    university_client_secret: str = ""

    # Where this API is reachable from a browser. The provider redirects the
    # user's own browser back to it, so it must be the public URL -- not a
    # container hostname -- and it must match the redirect URI registered with
    # the provider byte for byte, or the provider refuses the request.
    api_base_url: str = "http://localhost:8000"
    # Where to hand the user back to once they are signed in.
    web_app_url: str = "http://localhost:5273"

    @property
    def tutor_enabled(self) -> bool:
        return bool(self.anthropic_api_key.strip())

    def is_researcher(self, email: str) -> bool:
        """Whether this address may see the programme-wide study analytics."""
        wanted = email.strip().lower()
        return any(e.strip().lower() == wanted for e in self.research_emails if e.strip())

    def oauth_client(self, provider: str) -> tuple[str, str] | None:
        """The (client_id, secret) pair for a provider, or None if unconfigured.

        Apple is deliberately absent: its secret is generated, not stored. Ask
        `apple_ready` instead, and get the secret from oauth.apple_client_secret().
        """
        pairs = {
            "google": (self.google_client_id, self.google_client_secret),
            "microsoft": (self.microsoft_client_id, self.microsoft_client_secret),
            "github": (self.github_client_id, self.github_client_secret),
            "facebook": (self.facebook_client_id, self.facebook_client_secret),
            "university": (self.university_client_id, self.university_client_secret),
        }
        client_id, secret = pairs.get(provider, ("", ""))
        if not client_id.strip() or not secret.strip():
            return None
        return client_id.strip(), secret.strip()

    @property
    def apple_ready(self) -> bool:
        return all(
            value.strip()
            for value in (
                self.apple_client_id,
                self.apple_team_id,
                self.apple_key_id,
                self.apple_private_key,
            )
        )

    @property
    def apple_private_key_pem(self) -> str:
        """The .p8 contents, with escaped newlines restored.

        A PEM block is multi-line and .env files are not, so people paste it
        with literal backslash-n. Accepting both spellings avoids an error whose
        only symptom is an unreadable key.
        """
        return self.apple_private_key.replace("\\n", "\n").strip()

    @property
    def university_ready(self) -> bool:
        return (
            bool(self.university_issuer.strip())
            and self.oauth_client("university") is not None
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
