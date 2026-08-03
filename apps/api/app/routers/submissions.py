import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import (
    Exercise,
    ExerciseSession,
    HintEvent,
    RunMode,
    Submission,
)
from ..schemas import SubmissionOut, SubmitRequest, SubmitResponse
from ..services import hints, translate
from ..services.grading import get_runner

log = logging.getLogger(__name__)
router = APIRouter(prefix="/submissions", tags=["submissions"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=SubmitResponse)
def submit(body: SubmitRequest, user: CurrentUser, db: DbSession) -> SubmitResponse:
    exercise = db.get(Exercise, body.exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    session = db.get(ExerciseSession, body.session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.now(timezone.utc)
    started = session.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    # Computed server-side. A client clock is never trusted for a measured
    # variable -- it's adjustable, and this one is a dependent variable.
    elapsed = int((now - started).total_seconds())

    last_activity = session.last_activity_at
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)
    idle_seconds = int((now - last_activity).total_seconds())

    prior = hints.consecutive_failures(db, user.id, exercise.id)
    attempt_number = (
        db.query(Submission)
        .filter(Submission.user_id == user.id, Submission.exercise_id == exercise.id)
        .count()
        + 1
    )

    # Grade authoritatively, server-side, always. A RUN is logged as behaviour,
    # but it is still re-graded here rather than trusting client_results,
    # because the client's verdict is the thing being checked -- see below.
    runner = get_runner()
    results = runner.run(body.code, exercise.entrypoint, exercise.tests)
    passed = bool(results.get("passed"))

    # --- the divergence rule -------------------------------------------------
    # If the browser and the server disagree about identical code, that is a
    # platform fault, not a student fault. Flag the row so it can be excluded or
    # inspected at analysis time, and log loudly so it gets fixed. Silently
    # showing the student a red they cannot explain is the exact failure this
    # architecture exists to prevent.
    divergence = False
    if body.client_results is not None:
        client_passed = bool(body.client_results.get("passed"))
        if client_passed != passed:
            divergence = True
            log.error(
                "run/submit divergence: user=%s exercise=%s client_passed=%s "
                "server_passed=%s",
                user.id,
                exercise.slug,
                client_passed,
                passed,
            )

    # L1 of the ladder: the error, rewritten in English. Automatic on any
    # exception -- a raw traceback is never the whole of what a novice gets.
    # Prefers the top-level error (syntax/import), falling back to the first
    # test that threw.
    raw_error = results.get("error")
    if raw_error is None:
        raw_error = next(
            (t.get("error") for t in results.get("tests", []) if t.get("error")),
            None,
        )
    translated = translate.translate(raw_error)
    where = translate.locate(raw_error)
    if translated and where:
        translated = f"{translated} {where}"

    has_error = results.get("error") is not None or any(
        t.get("status") == "error" for t in results.get("tests", [])
    )

    # The ratchet floor -- reads submissions AND pulled hints, so a hint the
    # student requested on demand counts exactly like one the ladder pushed.
    current_max_level = hints.current_max_hint_level(db, user.id, exercise.id)

    failures_now = prior if passed else prior + 1
    level = hints.level_for(
        exercise,
        consecutive_failures=failures_now,
        idle_seconds=idle_seconds,
        has_error=has_error,
        current_max_level=current_max_level,
    )

    submission = Submission(
        user_id=user.id,
        exercise_id=exercise.id,
        session_id=session.id,
        code=body.code,
        run_mode=body.run_mode,
        # Frozen at write time from the exercise's variant -- never joined at
        # analysis time, so re-theming an exercise mid-study can't rewrite history.
        theme_variant=exercise.variant,
        test_results=results,
        passed=passed,
        max_hint_level=level,
        seconds_since_exercise_start=elapsed,
        attempt_number=attempt_number,
        divergence_flag=divergence,
    )
    db.add(submission)

    if level > current_max_level:
        db.add(
            HintEvent(
                user_id=user.id,
                exercise_id=exercise.id,
                session_id=session.id,
                level=level,
                trigger="idle" if idle_seconds >= 300 and failures_now < 2 else "failures",
                failures_at_trigger=failures_now,
                seconds_at_trigger=elapsed,
            )
        )

    session.last_activity_at = now
    if passed and body.run_mode is RunMode.SUBMIT and session.ended_at is None:
        session.ended_at = now

    db.commit()

    return SubmitResponse(
        submission_id=submission.id,
        passed=passed,
        test_results=results,
        translated_error=translated,
        hint_level=level,
        hint=hints.hint_text(exercise, level),
        attempt_number=attempt_number,
    )


@router.get("", response_model=list[SubmissionOut])
def my_submissions(
    user: CurrentUser, db: DbSession, exercise_id: str | None = None
) -> list[Submission]:
    query = select(Submission).where(Submission.user_id == user.id)
    if exercise_id:
        query = query.where(Submission.exercise_id == exercise_id)
    return list(db.scalars(query.order_by(Submission.created_at.desc()).limit(200)))
