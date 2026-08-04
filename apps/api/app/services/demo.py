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


def demo_kind(email: str) -> str | None:
    """Which button minted this account: "lesson", "account", or None.

    Encoded in the address rather than a new column, so it needs no migration
    and is legible straight from the database. The two behave differently on
    purpose: the lesson demo is a focused look at one exercise and has no
    dashboard to go back to, while the account demo exists precisely to wander
    around one.
    """
    if not is_demo_email(email):
        return None
    local = email.split("@", 1)[0]
    if local.startswith("demo-lesson-"):
        return "lesson"
    if local.startswith("demo-account-"):
        return "account"
    # Minted before the two were distinguished. Treated as the permissive one:
    # leaving an old demo stranded is worse than showing it a dashboard.
    return "account"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_demo_user(db: Session, *, with_progress: bool) -> User:
    """Mint a fresh throwaway account, optionally with work already in it."""
    kind = "account" if with_progress else "lesson"
    user = User(
        email=f"demo-{kind}-{uuid.uuid4().hex[:12]}@{DEMO_DOMAIN}",
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


#: A believable fortnight of work.
#:
#: Three outcomes, because the dashboard has three states and a demo that only
#: ever shows one of them demonstrates a third of the product:
#:
#:   solved   passed in the end -- some first try, some after a fight
#:   stuck    attempted, not passed. This is what "in progress" looks like, and
#:            it is the state the hint ladder exists for.
#:   opened   started and walked away without submitting. Counts as in progress
#:            too (see routers/progress.py) and is what half-finished really
#:            looks like in practice.
#:
#: Everything not listed is left untouched and shows as not started, which is
#: most of the 69 -- as it should be for someone a fortnight in.
_STORY: list[tuple[str, int, int, str]] = [
    # (slug, attempts, highest hint used, outcome)
    ("lists-make", 1, 0, "solved"),
    ("lists-index", 2, 1, "solved"),
    ("lists-slice", 1, 0, "solved"),
    ("loops-for", 3, 2, "solved"),
    ("loops-range", 2, 0, "solved"),
    ("str-index", 4, 3, "solved"),
    # Still going: submitted, not passing yet.
    ("lists-loop", 2, 1, "stuck"),
    ("loops-accum", 3, 3, "stuck"),
    # Opened and left. No submissions at all.
    ("dicts-make", 0, 0, "opened"),
    ("str-case", 0, 0, "opened"),
]


def _seed_progress(db: Session, user: User) -> None:
    """Give the account a history worth looking at.

    Deliberately uneven. A demo where everything passed first time shows none
    of what this product is actually for -- the hint ladder, the retries, the
    half-finished exercise you come back to.
    """
    started = _now() - timedelta(days=14)

    for index, (slug, attempts, hints, outcome) in enumerate(_STORY):
        exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
        if exercise is None:
            # The content set is edited often; a demo must not 500 because one
            # slug was renamed.
            continue

        # Spread across the fortnight so "pick up where you left off" has an
        # order to work with, and the most recent thing is something unfinished.
        day = index + (index // 3)
        session = ExerciseSession(
            user_id=user.id,
            exercise_id=exercise.id,
            started_at=started + timedelta(days=day),
            last_activity_at=started + timedelta(days=day, minutes=18),
        )
        db.add(session)
        db.flush()

        for attempt in range(1, attempts + 1):
            # Only a "solved" run ends in a pass; a "stuck" one never does.
            passed = outcome == "solved" and attempt == attempts
            total = 4
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
                        "summary": {
                            "passed": total if passed else min(attempt, total - 1),
                            "total": total,
                        },
                    },
                    passed=passed,
                    # Hints climb with the struggle rather than arriving at once.
                    max_hint_level=min(hints, attempt),
                    seconds_since_exercise_start=150 * attempt + index * 20,
                    attempt_number=attempt,
                    created_at=started + timedelta(days=day, minutes=5 * attempt),
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
    "demo_kind",
    "is_demo_email",
    "purge_expired",
    "ThemeVariant",
]
