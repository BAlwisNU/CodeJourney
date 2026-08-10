"""Instructor analytics.

Answers one question: who needs help, and what is the class getting wrong?

Instructors DO see time-on-task and hint depth, unlike students -- see
docs/architecture.md. Measurement reactivity is a concern about showing
participants their own dependent variables; the instructor is not the
participant, and withholding this from them would defeat the point of the
dashboard.

Everything here is gated behind `require_instructor`. A student hitting these
endpoints gets a 403.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import Researcher
from ..db import get_db
from ..models import Exercise, Reflection, Role, RunMode, Submission, User
from ..schemas import CommonError, InstructorOut, ReflectionOut, StudentRow

router = APIRouter(prefix="/instructor", tags=["instructor"])

DbSession = Annotated[Session, Depends(get_db)]

# Someone this deep in the ladder and still failing is the case the dashboard
# exists to surface. Matches L5 in services/hints.py.
NEEDS_HELP_HINT_LEVEL = 4


@router.get("", response_model=InstructorOut)
def overview(researcher: Researcher, db: DbSession) -> InstructorOut:
    students = list(db.scalars(select(User).where(User.role == Role.STUDENT)))
    total_exercises = db.scalar(select(func.count(Exercise.id))) or 0

    submissions = list(
        db.scalars(select(Submission).where(Submission.run_mode == RunMode.SUBMIT))
    )

    by_user: dict[str, list[Submission]] = {}
    for submission in submissions:
        by_user.setdefault(submission.user_id, []).append(submission)

    rows: list[StudentRow] = []
    for student in students:
        attempts = by_user.get(student.id, [])
        solved_ids = {s.exercise_id for s in attempts if s.passed}
        max_hint = max((s.max_hint_level for s in attempts), default=0)

        # Still stuck on something they've exhausted the ladder for.
        unsolved_at_top = any(
            s.max_hint_level >= NEEDS_HELP_HINT_LEVEL
            and s.exercise_id not in solved_ids
            for s in attempts
        )

        rows.append(
            StudentRow(
                user_id=student.id,
                display_name=student.display_name,
                solved=len(solved_ids),
                total_exercises=total_exercises,
                attempts=len(attempts),
                max_hint_level=max_hint,
                needs_help=unsolved_at_top,
            )
        )

    # Struggling students first -- the dashboard should open on the people who
    # need something from you, not on an alphabetical list.
    rows.sort(key=lambda r: (not r.needs_help, r.solved))

    # What the class is getting wrong, by error type. Feeds curriculum decisions
    # and tells the content author which translations are earning their keep.
    counts: dict[str, int] = {}
    for submission in submissions:
        results = submission.test_results or {}
        error = results.get("error")
        if not error:
            error = next(
                (t.get("error") for t in results.get("tests", []) if t.get("error")),
                None,
            )
        if error and error.get("type"):
            counts[error["type"]] = counts.get(error["type"], 0) + 1

    common = [
        CommonError(error_type=name, count=count)
        for name, count in sorted(counts.items(), key=lambda kv: -kv[1])
    ][:10]

    return InstructorOut(
        students=rows,
        common_errors=common,
        total_students=len(students),
        total_submissions=len(submissions),
        divergence_incidents=sum(1 for s in submissions if s.divergence_flag),
    )


@router.get("/students/{user_id}/reflections", response_model=list[ReflectionOut])
def student_reflections(
    user_id: str, researcher: Researcher, db: DbSession
) -> list[Reflection]:
    """A student's journal.

    Instructors can read these -- the proposal says so, and students are told so
    on the signup and account pages. What must never happen is a machine reading
    them: no summarisation, no sentiment scoring, no flagging. A human
    instructor reading a student's reflection is teaching; a model doing it is
    the psychological judgement the proposal promises not to make.
    """
    return list(
        db.scalars(
            select(Reflection)
            .where(Reflection.user_id == user_id)
            .order_by(Reflection.updated_at.desc())
        )
    )
