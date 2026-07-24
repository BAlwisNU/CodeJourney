"""Test environment and shared fixtures.

The env vars must be set BEFORE app.db is imported, because it creates its engine
at module scope. Without them, importing the app requires a working Postgres
driver -- which would make the suite need a database to test code that has
nothing to do with one, and would keep it out of CI's fast path.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SECRET_KEY", "test-only")

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.seed import seed  # noqa: E402

# Reference solutions, shared across test modules.
CORRECT = '''
def expired_quests(quests, today):
    out = []
    for q in quests:
        if q["due_day"] < today and not q["done"]:
            out.append(q["name"])
    return out
'''

WRONG = '''
def expired_quests(quests, today):
    return []
'''

BOOM = '''
def expired_quests(quests, today):
    return quests[99]
'''


@pytest.fixture
def client():
    """A TestClient backed by a fresh in-memory database, seeded.

    StaticPool keeps every connection pointed at the same in-memory database --
    without it each connection gets its own blank one and nothing persists
    between requests.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with TestingSession() as db:
        seed(db)

    def override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        # Exposed so tests can assert against the database directly, not just
        # through the API.
        c.session_factory = TestingSession
        yield c
    app.dependency_overrides.clear()


def login(client, email="student@example.com", password="password123") -> dict:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def open_exercise(client, headers, slug="expired-quests"):
    """Fetch an exercise and open a sitting at it, as the editor does on mount."""
    exercise = client.get(f"/exercises/{slug}", headers=headers).json()
    session = client.post(f"/exercises/{slug}/session", headers=headers).json()
    return exercise, session["session_id"]


def submit(
    client, headers, exercise, session_id, code, mode="submit", client_results=None
):
    return client.post(
        "/submissions",
        headers=headers,
        json={
            "exercise_id": exercise["id"],
            "session_id": session_id,
            "code": code,
            "run_mode": mode,
            "client_results": client_results,
        },
    )
