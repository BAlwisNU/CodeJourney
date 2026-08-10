"""Engine and session setup.

Two dialects, deliberately: Postgres in production, SQLite everywhere else.

Production runs Postgres 16 (deploy/docker-compose.prod.yml). The test suite
runs SQLite in-memory so it needs no database to start and no cleanup to
finish, and local development runs SQLite on disk for the same reason. The
schema is written to the portable subset both dialects share -- no JSONB, no
ARRAY, no server-side defaults that only one of them understands -- so the same
models.py builds the same tables on either.

The one place they genuinely disagree is enforcement, handled below.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(connection, _record) -> None:
    """Make SQLite enforce foreign keys, because by default it does not.

    SQLite parses REFERENCES clauses and then ignores them unless the pragma is
    set per connection. Postgres has no such switch -- it always enforces. The
    schema has 41 foreign keys and twelve ON DELETE CASCADEs, so without this
    the tests run against a database with no referential integrity at all and
    happily accept writes production would reject: a submission pointing at a
    deleted exercise, a roster row for a user who no longer exists. Deleting a
    classroom would orphan its members in the test suite and cascade in
    production, which is precisely the kind of divergence a test suite exists
    to catch rather than create.

    Registered against Engine rather than a particular engine so it also covers
    the one the tests build for themselves, and gated on the dialect so the
    Postgres path never sees it.
    """
    if connection.__class__.__module__.startswith("sqlite3"):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
