import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import engine
from .services import demo
from .models import Base
from sqlalchemy.orm import Session
from .routers import (
    auth,
    classes,
    drafts,
    exercises,
    help,
    instructor,
    learn,
    oauth,
    onboarding,
    portfolio,
    progress,
    projects,
    reflections,
    submissions,
    teacher,
    tutor,
)

logging.basicConfig(level=logging.INFO)
settings = get_settings()

if settings.environment != "development" and settings.secret_key.startswith("dev-only"):
    raise RuntimeError("SECRET_KEY must be set outside development")

app = FastAPI(
    title="CodeJourney API",
    version="0.1.0",
    description=(
        "Logical separation, monolithic deployment. Feedback, hints, grading and "
        "analytics are modules in this one app, not separate services. The only "
        "genuinely separate process is the code sandbox. See docs/architecture.md."
    ),
)

# Dev accepts any localhost port; production accepts only its configured list.
# The regex is never applied outside development -- a wildcard localhost origin
# in production would be a real hole.
_is_dev = settings.environment == "development"
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex_dev if _is_dev else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(onboarding.router)
app.include_router(exercises.router)
app.include_router(submissions.router)
app.include_router(progress.router)
app.include_router(projects.router)
app.include_router(drafts.router)
app.include_router(reflections.router)
app.include_router(learn.router)
app.include_router(portfolio.router)
app.include_router(instructor.router)
# Teaching. `instructor` stays the programme-wide research view; these three are
# the class-scoped teaching surface -- see routers/teacher.py for the split.
app.include_router(teacher.router)
app.include_router(classes.router)
app.include_router(help.router)
app.include_router(tutor.router)


@app.on_event("startup")
def startup() -> None:
    # Fine for Weeks 1-2. Swap for Alembic before the first migration that has
    # to preserve data -- which in practice means before the Week 5 pilot,
    # because after that point dropping the DB destroys study data.
    Base.metadata.create_all(engine)

    # Sweep up throwaway demo accounts. Anyone who finds the landing page can
    # create one, so without this the users table fills with rows nobody will
    # ever log into again. On startup rather than on a schedule: there is no
    # scheduler here, and "whenever the server restarts" is often enough for
    # junk with no reader. Never fatal -- a failed tidy-up must not stop the
    # API from serving.
    try:
        with Session(engine) as db:
            removed = demo.purge_expired(db)
        if removed:
            logging.getLogger(__name__).info("purged %d stale demo account(s)", removed)
    except Exception:  # noqa: BLE001 - housekeeping, never a startup blocker
        logging.getLogger(__name__).exception("demo account purge failed")


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        # Surfaced so the frontend can assert its Pyodide build matches the
        # server's CPython. A mismatch here is the divergence rule's early
        # warning; see docs/architecture.md.
        "python_version": settings.python_version,
        "pyodide_version": settings.pyodide_version,
    }
