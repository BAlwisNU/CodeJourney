"""The two configurations the API refuses to start on.

Postgres in production, SQLite in tests and development. That split is a
deliberate one -- the suite needs no database to run and leaves nothing behind,
and neither does a checkout on somebody's laptop -- but it only holds if the
production side is enforced somewhere. A deployment is a set of environment
variables, and a missing one is easy to not notice.

Both failures these guard against are quiet at the moment they happen: a
container running SQLite serves traffic perfectly well right up until the
redeploy that discards its filesystem, and a dev SECRET_KEY signs tokens that
anyone holding the public repository can forge. Refusing to boot converts both
into a deploy that fails loudly instead.
"""

import pytest

from app.config import Settings
from app.main import check_production_settings

REAL_SECRET = "0" * 64
PG = "postgresql+psycopg://codejourney:pw@db:5432/codejourney"


def settings(**overrides) -> Settings:
    base = {
        "environment": "production",
        "secret_key": REAL_SECRET,
        "database_url": PG,
        # _env_file=None so a developer's own apps/api/.env cannot decide
        # whether this test passes. It is on disk on every machine that has run
        # the app, and it sets DATABASE_URL to SQLite.
        "_env_file": None,
    }
    return Settings(**{**base, **overrides})


def test_production_refuses_sqlite():
    with pytest.raises(RuntimeError, match="postgresql"):
        check_production_settings(settings(database_url="sqlite:///./codejourney.db"))


def test_the_refusal_says_what_is_actually_wrong():
    """The message has to be readable in a deploy log by someone in a hurry."""
    with pytest.raises(RuntimeError) as caught:
        check_production_settings(settings(database_url="sqlite://"))

    message = str(caught.value)
    assert "DATABASE_URL" in message, "name the variable to change"
    assert "sqlite://" in message, "say what it was actually set to"
    assert "redeploy" in message, "say why it matters, not just that it is banned"


def test_production_accepts_postgres():
    check_production_settings(settings())


@pytest.mark.parametrize("url", [PG, "postgresql://codejourney:pw@db:5432/codejourney"])
def test_both_postgres_url_spellings_are_accepted(url):
    """With and without the +psycopg driver suffix; production uses the former."""
    check_production_settings(settings(database_url=url))


def test_production_refuses_the_development_secret():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        check_production_settings(settings(secret_key="dev-only-not-a-real-secret"))


def test_development_is_left_alone():
    """Where SQLite is the point, and nobody should need to set anything."""
    check_production_settings(
        settings(
            environment="development",
            database_url="sqlite:///./codejourney.db",
            secret_key="dev-only-not-a-real-secret",
        )
    )
