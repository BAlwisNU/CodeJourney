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


@lru_cache
def get_settings() -> Settings:
    return Settings()
