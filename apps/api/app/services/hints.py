"""The hint ladder.

    L0  run output + test results        free, immediate
    L1  translated error                 automatic on any exception
    L2  location        after 2 failures or 5 min idle
    L3  conceptual      after 4 failures
    L4  structural      after 6 failures
    L5  instructor flag
    --  the answer                       never

Thresholds are per-exercise overridable (Exercise.hint_thresholds). That is not
a nice-to-have: it makes escalation speed a manipulable variable, which turns
the platform into a research instrument rather than a fixed opinion about
pedagogy.

The ladder never goes down. Once a student has seen L3, they have seen it, and
the mastery penalty reflects that for the rest of the exercise -- otherwise a
student could peek, then reset, and the mastery score would be measuring
nothing.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Exercise, HintEvent, Submission

DEFAULT_THRESHOLDS = {
    "l2_after_failures": 2,
    "l3_after_failures": 4,
    "l4_after_failures": 6,
    "l2_after_idle_seconds": 300,
}

MAX_AUTOMATIC_LEVEL = 4  # L5 is a human being; the ladder cannot award it.


def thresholds_for(exercise: Exercise) -> dict:
    merged = dict(DEFAULT_THRESHOLDS)
    merged.update(exercise.hint_thresholds or {})
    return merged


def level_for(
    exercise: Exercise,
    consecutive_failures: int,
    idle_seconds: int,
    has_error: bool,
    current_max_level: int = 0,
) -> int:
    """Compute the hint level this attempt has earned.

    Returns the *highest* of what the failure count, the idle timer, and the
    already-revealed level justify -- never less than current_max_level, because
    the ladder is a ratchet.
    """
    t = thresholds_for(exercise)
    level = 0

    # L1 is automatic on any exception -- a raw traceback is never the whole of
    # what a novice gets.
    if has_error:
        level = 1

    if consecutive_failures >= t["l2_after_failures"]:
        level = max(level, 2)
    if idle_seconds >= t["l2_after_idle_seconds"]:
        level = max(level, 2)
    if consecutive_failures >= t["l3_after_failures"]:
        level = max(level, 3)
    if consecutive_failures >= t["l4_after_failures"]:
        level = max(level, 4)

    level = min(level, MAX_AUTOMATIC_LEVEL)
    return max(level, current_max_level)


def hint_text(exercise: Exercise, level: int) -> str | None:
    """Content for a level. L0/L1 are generated elsewhere, so they return None.

    L2-L4 are authored per exercise (content track, Weeks 2-4). An exercise
    missing its L3 text falls back to the nearest lower authored level rather
    than showing nothing -- a student stuck at L3 with no L3 written should not
    silently get less help than one at L2.
    """
    if level < 2:
        return None
    hints = exercise.hints or {}
    for candidate in range(level, 1, -1):
        text = hints.get(str(candidate))
        if text:
            return text
    return None


def consecutive_failures(db: Session, user_id: str, exercise_id: str) -> int:
    """Failures since the last pass on this exercise.

    Consecutive rather than total: a student who solved it, came back, and broke
    it again should not be handed L4 on their first new attempt.
    """
    rows = db.scalars(
        select(Submission)
        .where(
            Submission.user_id == user_id,
            Submission.exercise_id == exercise_id,
        )
        .order_by(Submission.created_at.desc())
    ).all()
    count = 0
    for row in rows:
        if row.passed:
            break
        count += 1
    return count


def current_max_hint_level(db: Session, user_id: str, exercise_id: str) -> int:
    """The highest hint level revealed so far -- the ratchet floor.

    Reads BOTH submissions and hint events, so a hint the student *pulled* on
    demand (a HintEvent with no matching submission) raises the floor exactly
    like one the ladder pushed. In the pure-push flow the two agree, so this is a
    no-op there; it only matters once requested hints exist.
    """
    sub_max = db.scalar(
        select(func.max(Submission.max_hint_level)).where(
            Submission.user_id == user_id,
            Submission.exercise_id == exercise_id,
        )
    )
    hint_max = db.scalar(
        select(func.max(HintEvent.level)).where(
            HintEvent.user_id == user_id,
            HintEvent.exercise_id == exercise_id,
        )
    )
    return max(sub_max or 0, hint_max or 0)


def next_requested_level(current_max_level: int) -> int:
    """The level a 'give me a hint' press should reveal next.

    The first pull lands on L2 -- the first authored nudge -- because L0/L1 are
    the automatic test output and translated error, which need no button. From
    there it climbs one rung per press, and never past L4: the answer is a
    separate, deliberate choice, not the top of the hint ladder.
    """
    return min(max(current_max_level, 1) + 1, MAX_AUTOMATIC_LEVEL)


def should_flag_instructor(
    exercise: Exercise, consecutive_failures: int, current_max_level: int
) -> bool:
    """L5. The ladder has run out and a human should look.

    Deliberately generous: flagging is cheap, and a student who has burned
    through every hint and is still failing is exactly the case the instructor
    dashboard exists to surface.
    """
    t = thresholds_for(exercise)
    return (
        current_max_level >= MAX_AUTOMATIC_LEVEL
        and consecutive_failures >= t["l4_after_failures"] + 2
    )
