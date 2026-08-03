"""Throwaway accounts for "try it without signing up".

Two buttons on the landing page land here: one drops you straight into a
lesson, one hands you an account that already has a few days of work in it so
the dashboard, the portfolio and the hint history have something to show.

Three rules this module exists to keep.

**A demo account is never study data.** `consented_at` stays None, which is what
excludes a user from analysis everywhere else, and the address is stamped with
`DEMO_DOMAIN` so a demo row is identifiable at a glance in the database and in
any query someone writes later. A stranger clicking a button on a marketing page
has not consented to anything, and their fake submissions must never reach the
Week 8 numbers.

**A demo account is obviously a demo, to its user.** `is_demo` rides on
/auth/me so the app can say so. Letting someone spend twenty minutes on work
that quietly evaporates is the kind of thing that makes people distrust a
product.

**A demo account owns nothing shared.** Each click mints a fresh one rather than
handing out a common login, so two visitors can never see each other's work or
undo each other's progress.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import UNUSABLE_PASSWORD
from ..models import (
    Exercise,
    ExerciseSession,
    Role,
    RunMode,
    Submission,
    ThemeVariant,
    User,
)

#: Stamped into every demo address, so a demo row is identifiable at a glance
#: in the database and in any query someone writes later.
#:
#: `.example` is reserved by RFC 2606: it can never be registered, so these
#: addresses can never route mail to a real person. `.invalid` and `.test` are
#: reserved too and would read better, but pydantic's EmailStr rejects them as
#: special-use names -- `.example` is the one that is both unregistrable and
#: valid, which is why it wins over a nicer-looking fake.
DEMO_DOMAIN = "demo.codejourney.example"


def is_demo_email(email: str) -> bool:
    return email.endswith(f"@{DEMO_DOMAIN}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_demo_user(db: Session, *, with_progress: bool) -> User:
    """Mint a fresh throwaway account, optionally with work already in it."""
    user = User(
        email=f"demo-{uuid.uuid4().hex[:12]}@{DEMO_DOMAIN}",
        # No password exists for these, and none can be set. See UNUSABLE_PASSWORD.
        password_hash=UNUSABLE_PASSWORD,
        display_name="Guest",
        role=Role.STUDENT,
        # Assigned like any other account so the app behaves identically -- the
        # study simply never looks at this row.
        counterbalance_group=random.choice(["A", "B"]),
        # Not consented, and there is no path from here to consenting: the
        # account page's toggle exists, but nothing in the analysis includes a
        # demo address anyway.
        consented_at=None,
    )
    db.add(user)
    db.flush()

    if with_progress:
        _seed_progress(db, user)

    db.commit()
    db.refresh(user)
    return user


#: What a plausible few days of work looks like. Kept small: the point is a
#: dashboard that isn't empty, not a simulation of a whole course.
_STORY = [
    # (slug, attempts before passing, hints used)
    ("lists-make", 1, 0),
    ("lists-index", 2, 1),
    ("loops-for", 3, 2),
]


def _seed_progress(db: Session, user: User) -> None:
    """Give the account a believable history.

    Deliberately imperfect: one exercise solved first try, one after a couple of
    goes, one that needed hints. A demo where everything passed immediately
    shows none of what the product is actually for.
    """
    started = _now() - timedelta(days=3)

    for index, (slug, attempts, hints) in enumerate(_STORY):
        exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
        if exercise is None:
            # The content set is edited often; a demo must not 500 because one
            # slug was renamed.
            continue

        session = ExerciseSession(
            user_id=user.id,
            exercise_id=exercise.id,
            started_at=started + timedelta(days=index),
            last_activity_at=started + timedelta(days=index, minutes=12),
        )
        db.add(session)
        db.flush()

        for attempt in range(1, attempts + 1):
            passed = attempt == attempts
            total = 4
            passing = total if passed else max(0, total - 2)
            db.add(
                Submission(
                    user_id=user.id,
                    exercise_id=exercise.id,
                    session_id=session.id,
                    code=f"# {slug}\n# attempt {attempt}\n",
                    run_mode=RunMode.SUBMIT,
                    theme_variant=exercise.variant,
                    test_results={
                        "passed": passed,
                        "summary": {"passed": passing, "total": total},
                    },
                    passed=passed,
                    max_hint_level=hints if not passed else hints,
                    seconds_since_exercise_start=120 * attempt + index * 30,
                    attempt_number=attempt,
                    created_at=started
                    + timedelta(days=index, minutes=4 * attempt),
                )
            )


def purge_expired(db: Session, *, older_than_days: int = 7) -> int:
    """Delete demo accounts and everything they own. Returns how many went.

    These are created by anyone who clicks a button on a public page, so without
    this the table grows forever with rows nobody will ever log into again.
    Called on startup rather than on a schedule -- there is no scheduler here,
    and "whenever the server restarts" is often enough for junk with no reader.
    """
    cutoff = _now() - timedelta(days=older_than_days)
    stale = list(
        db.scalars(
            select(User).where(
                User.email.like(f"%@{DEMO_DOMAIN}"), User.created_at < cutoff
            )
        )
    )
    for user in stale:
        # Submissions and sessions have plain foreign keys rather than cascades,
        # so they are removed explicitly; SQLite would not enforce it anyway.
        for model in (Submission, ExerciseSession):
            for row in db.scalars(select(model).where(model.user_id == user.id)):
                db.delete(row)
        db.delete(user)
    if stale:
        db.commit()
    return len(stale)


__all__ = [
    "DEMO_DOMAIN",
    "create_demo_user",
    "is_demo_email",
    "purge_expired",
    "ThemeVariant",
]
