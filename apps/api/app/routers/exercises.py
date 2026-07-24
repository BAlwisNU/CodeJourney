from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import Exercise, ExerciseSession
from ..schemas import ExerciseOut, ExerciseSummary, SessionStartResponse, TestOut

router = APIRouter(prefix="/exercises", tags=["exercises"])

DbSession = Annotated[Session, Depends(get_db)]


def _public_tests(exercise: Exercise) -> list[TestOut]:
    """Strip hidden tests down to name + status-shape only.

    This is the only place test data crosses to the client. If a hidden test's
    args ever appear in a response, the exercise is gameable and any submission
    data collected after that point is suspect.
    """
    out = []
    for test in exercise.tests:
        hidden = test.get("hidden", False)
        out.append(
            TestOut(
                name=test.get("name", "test"),
                hidden=hidden,
                args=None if hidden else repr(test.get("args", [])),
                expected=None if hidden else repr(test.get("expected")),
            )
        )
    return out


@router.get("", response_model=list[ExerciseSummary])
def list_exercises(user: CurrentUser, db: DbSession) -> list[Exercise]:
    """List exercises for the current student.

    Week 1 returns everything, ordered. The recommender (Week 6) will filter and
    order this by mastery; the endpoint shape is already right for that, so the
    frontend won't need changing.
    """
    return list(
        db.scalars(select(Exercise).order_by(Exercise.order_index, Exercise.title))
    )


@router.get("/{slug}", response_model=ExerciseOut)
def get_exercise(slug: str, user: CurrentUser, db: DbSession) -> ExerciseOut:
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    return ExerciseOut(
        id=exercise.id,
        slug=exercise.slug,
        title=exercise.title,
        theme=exercise.theme,
        concept=exercise.concept,
        variant=exercise.variant,
        prompt_md=exercise.prompt_md,
        starter_code=exercise.starter_code,
        entrypoint=exercise.entrypoint,
        tests=_public_tests(exercise),
    )


@router.post("/{slug}/session", response_model=SessionStartResponse)
def start_session(slug: str, user: CurrentUser, db: DbSession) -> SessionStartResponse:
    """Open (or resume) a sitting at this exercise.

    Called when the student opens the editor. This is what makes time-on-task a
    measured quantity rather than one reconstructed from submission timestamps
    -- which would systematically under-count the thinking time before the first
    Run, i.e. exactly the interval the theme hypothesis predicts will differ.

    Resumes any still-open session for this (user, exercise) so that a page
    refresh doesn't reset the clock or fabricate a second data point.
    """
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    session = db.scalar(
        select(ExerciseSession)
        .where(
            ExerciseSession.user_id == user.id,
            ExerciseSession.exercise_id == exercise.id,
            ExerciseSession.ended_at.is_(None),
        )
        .order_by(ExerciseSession.started_at.desc())
    )
    if session is None:
        session = ExerciseSession(user_id=user.id, exercise_id=exercise.id)
        db.add(session)
        db.commit()

    return SessionStartResponse(session_id=session.id, started_at=session.started_at)
