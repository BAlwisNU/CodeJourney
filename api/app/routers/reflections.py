"""The learning journal.

    What did you try? Where did you get stuck? How did you fix it?

HARD RULE, and it is structural rather than a matter of policy: nothing in this
module ever calls an LLM, and no other service reads these fields.

A student writing about "personal growth and challenges" may disclose real
distress. The proposal promises the system makes no psychological judgements.
Keeping the AI's eyes on code only is what makes that promise real instead of
aspirational. There is deliberately no sentiment analysis, no summarisation, no
keyword flagging, and no "wellbeing" heuristic anywhere in this file -- adding
one would be the first step toward breaking the guarantee, and it would need to
go back through ethics before it could be considered.

See docs/architecture.md, "Reflections never touch an LLM".
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import Exercise, Reflection
from ..schemas import ReflectionIn, ReflectionOut

router = APIRouter(prefix="/reflections", tags=["reflections"])

DbSession = Annotated[Session, Depends(get_db)]

MAX_FIELD_CHARS = 5000


def _check_length(body: ReflectionIn) -> None:
    for label, value in (
        ("what you tried", body.what_i_tried),
        ("where you got stuck", body.where_i_got_stuck),
        ("how you fixed it", body.how_i_fixed_it),
    ):
        if len(value) > MAX_FIELD_CHARS:
            raise HTTPException(
                status_code=422,
                detail=f"That's a lot of writing about {label} — please keep it "
                f"under {MAX_FIELD_CHARS} characters.",
            )


@router.get("", response_model=list[ReflectionOut])
def list_reflections(
    user: CurrentUser, db: DbSession, exercise_id: str | None = None
) -> list[Reflection]:
    """This student's own journal entries. Never anyone else's."""
    query = select(Reflection).where(Reflection.user_id == user.id)
    if exercise_id:
        query = query.where(Reflection.exercise_id == exercise_id)
    return list(db.scalars(query.order_by(Reflection.updated_at.desc())))


@router.post("", response_model=ReflectionOut, status_code=201)
def save_reflection(
    body: ReflectionIn, user: CurrentUser, db: DbSession
) -> Reflection:
    """Create or update the entry for an exercise.

    Upsert rather than append: a journal that spawns a new entry every time you
    fix a typo becomes unreadable, and the point is one honest account per
    exercise that you can return to and revise.
    """
    _check_length(body)

    if body.exercise_id is not None:
        if db.get(Exercise, body.exercise_id) is None:
            raise HTTPException(status_code=404, detail="Exercise not found")

        existing = db.scalar(
            select(Reflection).where(
                Reflection.user_id == user.id,
                Reflection.exercise_id == body.exercise_id,
            )
        )
        if existing is not None:
            existing.what_i_tried = body.what_i_tried
            existing.where_i_got_stuck = body.where_i_got_stuck
            existing.how_i_fixed_it = body.how_i_fixed_it
            db.commit()
            db.refresh(existing)
            return existing

    reflection = Reflection(
        user_id=user.id,
        exercise_id=body.exercise_id,
        what_i_tried=body.what_i_tried,
        where_i_got_stuck=body.where_i_got_stuck,
        how_i_fixed_it=body.how_i_fixed_it,
    )
    db.add(reflection)
    db.commit()
    db.refresh(reflection)
    return reflection


@router.delete("/{reflection_id}", status_code=204)
def delete_reflection(reflection_id: str, user: CurrentUser, db: DbSession) -> None:
    """Delete your own entry.

    Unconditional, and no soft-delete. Someone who wrote something personal and
    changed their mind must be able to take it back for real -- a "deleted" flag
    on a row that still holds the text is not deletion, and promising otherwise
    would be a lie to both the participant and the ethics committee.
    """
    reflection = db.get(Reflection, reflection_id)
    # Same 404 whether it's missing or someone else's: don't confirm the
    # existence of other people's journal entries.
    if reflection is None or reflection.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(reflection)
    db.commit()
