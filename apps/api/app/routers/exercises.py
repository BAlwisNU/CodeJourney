from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import Exercise, ExerciseSession, HintEvent, RunMode, Submission
from ..schemas import (
    BranchLink,
    ExerciseOut,
    ExerciseSummary,
    HintRequest,
    HintResponse,
    SessionStartResponse,
    SolutionResponse,
    TestOut,
)
from ..services import hints, tutor

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
    # The taught curriculum plus this student's own AI branches; never another
    # student's branches. Same visibility rule as the dashboard.
    return list(
        db.scalars(
            select(Exercise)
            .where(
                (Exercise.created_by_user_id.is_(None))
                | (Exercise.created_by_user_id == user.id)
            )
            .order_by(Exercise.order_index, Exercise.title)
        )
    )


def _visible_to(exercise: Exercise, user_id: str) -> bool:
    """A student sees the curriculum and their own branches, nothing else."""
    return (
        exercise.created_by_user_id is None
        or exercise.created_by_user_id == user_id
    )


@router.get("/{slug}", response_model=ExerciseOut)
def get_exercise(slug: str, user: CurrentUser, db: DbSession) -> ExerciseOut:
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    # Same 404 for missing and for someone else's branch: don't reveal that
    # another student's generated lesson exists.
    if exercise is None or not _visible_to(exercise, user.id):
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


def _status_of(db: Session, user_id: str, exercise_id: str) -> str:
    """This student's status on one exercise: solved / in_progress / not_started.

    Mirrors the dashboard's rule -- solved once a submit passes, in progress once
    the lesson has been opened or submitted, otherwise not started."""
    passed = db.scalar(
        select(Submission.id).where(
            Submission.user_id == user_id,
            Submission.exercise_id == exercise_id,
            Submission.run_mode == RunMode.SUBMIT,
            Submission.passed.is_(True),
        )
    )
    if passed:
        return "solved"
    touched = db.scalar(
        select(Submission.id).where(
            Submission.user_id == user_id,
            Submission.exercise_id == exercise_id,
            Submission.run_mode == RunMode.SUBMIT,
        )
    ) or db.scalar(
        select(ExerciseSession.id).where(
            ExerciseSession.user_id == user_id,
            ExerciseSession.exercise_id == exercise_id,
        )
    )
    return "in_progress" if touched else "not_started"


@router.get("/{slug}/branches", response_model=list[BranchLink])
def list_branches(slug: str, user: CurrentUser, db: DbSession) -> list[BranchLink]:
    """The practice exercises this student built off this lesson.

    Used by the parent lesson's page to link to its branches -- at the top and
    bottom -- in addition to the tutor chat where each was made."""
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None or not _visible_to(exercise, user.id):
        raise HTTPException(status_code=404, detail="Exercise not found")

    children = db.scalars(
        select(Exercise)
        .where(
            Exercise.parent_exercise_id == exercise.id,
            Exercise.created_by_user_id == user.id,
        )
        .order_by(Exercise.created_at)
    )
    return [
        BranchLink(
            slug=child.slug,
            title=child.title,
            status=_status_of(db, user.id, child.id),
        )
        for child in children
    ]


@router.post("/{slug}/hint", response_model=HintResponse)
def request_hint(
    slug: str, body: HintRequest, user: CurrentUser, db: DbSession
) -> HintResponse:
    """A hint the student asked for, rather than one the ladder pushed.

    This is the 'pull' path the model always anticipated (HintEvent.trigger =
    'requested'). It reveals the next rung -- starting at L2, climbing one per
    press -- and never past L4, because the answer is a separate, deliberate
    choice. A pulled hint raises the ratchet exactly like a pushed one, so it
    still counts toward hint depth; a student who pulls every hint is a different
    phenomenon from one the system escalated, and the trigger records which.
    """
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    session = db.get(ExerciseSession, body.session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    current = hints.current_max_hint_level(db, user.id, exercise.id)
    level = hints.next_requested_level(current)
    exhausted = level >= hints.MAX_AUTOMATIC_LEVEL

    if level > current:
        now = datetime.now(timezone.utc)
        started = session.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        db.add(
            HintEvent(
                user_id=user.id,
                exercise_id=exercise.id,
                session_id=session.id,
                level=level,
                trigger="requested",
                failures_at_trigger=hints.consecutive_failures(db, user.id, exercise.id),
                seconds_at_trigger=int((now - started).total_seconds()),
            )
        )
        db.commit()

    return HintResponse(
        level=level, hint=hints.hint_text(exercise, level), exhausted=exhausted
    )


@router.get("/{slug}/solution", response_model=SolutionResponse)
def get_solution(slug: str, user: CurrentUser, db: DbSession) -> SolutionResponse:
    """The full worked answer, when a student chooses to see it.

    The hint ladder deliberately stops short of the answer; this endpoint is the
    student stepping past that on purpose. Solutions are not stored (the
    reference `_solution` is stripped before an exercise reaches the database),
    so the tutor solves the exercise fresh and the answer is VERIFIED against the
    exercise's real tests -- hidden ones included -- before it is returned. A
    student who asks for the answer gets a working answer, not a guess.
    """
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if not tutor.enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "The worked answer isn't available right now — the tutor that "
                "writes it isn't switched on. The hints above will still get you "
                "there."
            ),
        )

    try:
        solution = tutor.solve(
            exercise.id, exercise.entrypoint, exercise.prompt_md, exercise.tests
        )
    except tutor.GenerationError:
        raise HTTPException(
            status_code=502,
            detail=(
                "I couldn't put a clean answer together just now — try again in a "
                "moment, or lean on the hints above."
            ),
        ) from None

    return SolutionResponse(solution=solution)
