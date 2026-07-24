"""Autosaved work-in-progress code.

Server-side rather than localStorage, for two reasons. A participant who opens
the site on their phone should see what they wrote on their laptop -- that is the
whole point of the Week 5 companion. And localStorage is silently destroyed by
private browsing, clearing site data, and some managed-device policies, which
means the failure mode is "my work vanished" with no explanation.

Drafts are NOT research data. See the note on models.Draft.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import Draft, Exercise
from ..schemas import DraftIn, DraftOut

router = APIRouter(prefix="/exercises", tags=["drafts"])

DbSession = Annotated[Session, Depends(get_db)]

# Generous, but not unbounded. A novice exercise solution is a few hundred bytes;
# anything near this is a paste accident or someone probing, and an unbounded
# text column written on every keystroke-debounce is an easy way to fill a disk.
MAX_DRAFT_BYTES = 100_000


def _exercise_or_404(db: Session, slug: str) -> Exercise:
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise


@router.get("/{slug}/draft", response_model=DraftOut | None)
def get_draft(slug: str, user: CurrentUser, db: DbSession) -> Draft | None:
    """The saved draft, or null if they've never typed here.

    Null is a normal answer, not an error -- the editor falls back to the
    exercise's starter code.
    """
    exercise = _exercise_or_404(db, slug)
    return db.scalar(
        select(Draft).where(
            Draft.user_id == user.id, Draft.exercise_id == exercise.id
        )
    )


@router.put("/{slug}/draft", response_model=DraftOut)
def save_draft(
    slug: str, body: DraftIn, user: CurrentUser, db: DbSession
) -> Draft:
    """Upsert the draft. Called on a debounce as the student types.

    PUT rather than POST because it's idempotent overwrite-in-place: there is at
    most one draft per (user, exercise), enforced by a unique constraint.
    """
    if len(body.code.encode("utf-8")) > MAX_DRAFT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="That's a very large file — we can't autosave anything this big.",
        )

    exercise = _exercise_or_404(db, slug)
    draft = db.scalar(
        select(Draft).where(
            Draft.user_id == user.id, Draft.exercise_id == exercise.id
        )
    )
    if draft is None:
        draft = Draft(user_id=user.id, exercise_id=exercise.id, code=body.code)
        db.add(draft)
    else:
        draft.code = body.code

    db.commit()
    db.refresh(draft)
    return draft


@router.delete("/{slug}/draft", status_code=204)
def reset_draft(slug: str, user: CurrentUser, db: DbSession) -> None:
    """Throw the draft away and go back to the starter code.

    Being able to reset matters more for a novice than for an experienced
    programmer: when you've tangled the code beyond recognition and don't yet
    know how to untangle it, a clean slate is sometimes the only way forward.
    """
    exercise = _exercise_or_404(db, slug)
    draft = db.scalar(
        select(Draft).where(
            Draft.user_id == user.id, Draft.exercise_id == exercise.id
        )
    )
    if draft is not None:
        db.delete(draft)
        db.commit()
