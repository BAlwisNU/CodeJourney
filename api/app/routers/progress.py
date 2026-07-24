"""The student dashboard's data.

Computed server-side rather than by rolling up `/submissions` in the browser, for
two reasons: the Expo companion (Week 5) needs the same numbers and shouldn't
reimplement them, and a client-side rollup would need every submission row just
to render a progress bar.

WHAT THIS ENDPOINT DELIBERATELY DOES NOT RETURN, and why it matters:

    time-on-task        omitted
    hint depth          omitted

Both are dependent variables in the Week 7 study. Showing a participant their own
time-on-task, or how deep into the hint ladder they went, changes the behaviour
being measured -- someone who can see "you used hint 4" is under quiet pressure to
avoid hints next time, and someone watching a timer works differently than someone
who isn't. That is measurement reactivity, and it would contaminate exactly the
variables the study exists to measure.

Completion is different: a student obviously knows which exercises they've solved,
so surfacing it adds no distortion. It is shown.

Instructors get these numbers for their students in the Week 6 dashboard, where
reactivity isn't a concern because the instructor isn't the participant.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import Exercise, RunMode, Submission
from ..schemas import ConceptProgress, DashboardOut, ExerciseProgress

router = APIRouter(prefix="/progress", tags=["progress"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=DashboardOut)
def dashboard(user: CurrentUser, db: DbSession) -> DashboardOut:
    exercises = list(
        db.scalars(select(Exercise).order_by(Exercise.order_index, Exercise.title))
    )

    # Only graded attempts count toward progress. Runs are logged as behaviour
    # (they're most of the learning signal) but a student hasn't "done" an
    # exercise by pressing Run in their own browser.
    submissions = list(
        db.scalars(
            select(Submission)
            .where(
                Submission.user_id == user.id,
                Submission.run_mode == RunMode.SUBMIT,
            )
            .order_by(Submission.created_at)
        )
    )

    # Roll up in Python rather than with window functions. At ~30 exercises and a
    # few hundred submissions per student this is trivially fast, and it stays
    # readable for a team of three who are also writing exercises this week.
    by_exercise: dict[str, list[Submission]] = {}
    for submission in submissions:
        by_exercise.setdefault(submission.exercise_id, []).append(submission)

    rows: list[ExerciseProgress] = []
    for exercise in exercises:
        attempts = by_exercise.get(exercise.id, [])
        solved = next((s for s in attempts if s.passed), None)
        if solved is not None:
            status = "solved"
        elif attempts:
            status = "in_progress"
        else:
            status = "not_started"

        rows.append(
            ExerciseProgress(
                id=exercise.id,
                slug=exercise.slug,
                title=exercise.title,
                concept=exercise.concept,
                theme=exercise.theme,
                variant=exercise.variant,
                status=status,
                attempts=len(attempts),
                last_attempt_at=attempts[-1].created_at if attempts else None,
            )
        )

    # Per-concept progress. Not mastery -- mastery is the weighted, hint-penalised
    # score in services/mastery.py and lands in Week 6. Calling this "mastery"
    # before that exists would be a claim the system can't back up.
    concept_totals: dict[str, list[int]] = {}
    for row in rows:
        counts = concept_totals.setdefault(row.concept.value, [0, 0])
        counts[1] += 1
        if row.status == "solved":
            counts[0] += 1

    concepts = [
        ConceptProgress(concept=name, solved=solved, total=total)
        for name, (solved, total) in sorted(concept_totals.items())
    ]

    # Where to send them next: the unsolved exercise they touched most recently,
    # otherwise the first one they haven't started. Picking up where you left off
    # beats making someone re-find their place in a list.
    in_progress = [r for r in rows if r.status == "in_progress"]
    in_progress.sort(key=lambda r: r.last_attempt_at, reverse=True)
    if in_progress:
        continue_slug = in_progress[0].slug
    else:
        unstarted = [r for r in rows if r.status == "not_started"]
        continue_slug = unstarted[0].slug if unstarted else None

    return DashboardOut(
        display_name=user.display_name,
        role=user.role,
        solved=sum(1 for r in rows if r.status == "solved"),
        total_exercises=len(rows),
        total_attempts=len(submissions),
        concepts=concepts,
        continue_slug=continue_slug,
        exercises=rows,
    )
