"""The digital portfolio.

What the student made, and how they got there. The proposal's framing matters
here: a portfolio that showed only final answers would be a grade transcript.
This shows the solved code *and* how many attempts it took *and* what they wrote
about getting stuck -- evidence of progress rather than evidence of correctness.

The reflection is included because it is the student's own work and this is their
own portfolio. It still never goes to an LLM and is still excluded from research
data; being visible to its author is not the same as being processed.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import Exercise, Reflection, RunMode, Submission
from ..schemas import PortfolioEntry, PortfolioOut, ReflectionOut

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=PortfolioOut)
def portfolio(user: CurrentUser, db: DbSession) -> PortfolioOut:
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

    reflections = {
        r.exercise_id: r
        for r in db.scalars(select(Reflection).where(Reflection.user_id == user.id))
    }

    by_exercise: dict[str, list[Submission]] = {}
    for submission in submissions:
        by_exercise.setdefault(submission.exercise_id, []).append(submission)

    entries: list[PortfolioEntry] = []
    concepts: set[str] = set()

    for exercise_id, attempts in by_exercise.items():
        exercise = db.get(Exercise, exercise_id)
        if exercise is None:
            continue

        solved = next((s for s in attempts if s.passed), None)
        reflection = reflections.get(exercise_id)
        if solved is not None:
            concepts.add(exercise.concept.value)

        entries.append(
            PortfolioEntry(
                exercise_id=exercise.id,
                slug=exercise.slug,
                title=exercise.title,
                theme=exercise.theme,
                concept=exercise.concept,
                solved_at=solved.created_at if solved else None,
                attempts=len(attempts),
                # The code that passed. Unsolved exercises show their attempt
                # count but no code -- a portfolio of half-finished attempts
                # would be discouraging to look at, and the point of this page
                # is to show someone how far they've come.
                code=solved.code if solved else None,
                reflection=(
                    ReflectionOut.model_validate(reflection) if reflection else None
                ),
            )
        )

    # Solved first, then most-attempted -- the hardest wins lead the page.
    entries.sort(key=lambda e: (e.solved_at is None, -e.attempts))

    return PortfolioOut(
        display_name=user.display_name,
        solved=sum(1 for e in entries if e.solved_at is not None),
        total_attempts=len(submissions),
        concepts_touched=sorted(concepts),
        entries=entries,
    )
