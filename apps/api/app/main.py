import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import engine
from .models import Base
from .routers import (
    auth,
    drafts,
    exercises,
    instructor,
    learn,
    portfolio,
    progress,
    reflections,
    submissions,
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
app.include_router(exercises.router)
app.include_router(submissions.router)
app.include_router(progress.router)
app.include_router(drafts.router)
app.include_router(reflections.router)
app.include_router(learn.router)
app.include_router(portfolio.router)
app.include_router(instructor.router)


@app.on_event("startup")
def startup() -> None:
    # Fine for Weeks 1-2. Swap for Alembic before the first migration that has
    # to preserve data -- which in practice means before the Week 5 pilot,
    # because after that point dropping the DB destroys study data.
    Base.metadata.create_all(engine)


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
