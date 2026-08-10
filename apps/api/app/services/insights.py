"""Turning a roster into the three things a teacher actually needs.

    who is stuck        -> student_rows()
    what is hard        -> exercise_difficulty() / concept_difficulty()
    what is going wrong -> common_errors()

Every function takes an explicit set of student ids and never works out for
itself who the teacher may see. Scoping lives in services/teaching.py; this
module is arithmetic over whatever roster it is handed. Keeping the two apart
means a scoping bug cannot hide inside an aggregation, and the aggregations can
be tested against a fixed roster.

**Definitions are stated, not implied.** A dashboard that says "difficult"
without saying what it measured is asking a teacher to trust a number they
cannot check, so each metric below names its rule in one sentence and the UI
repeats it. Two in particular:

  struggled   a student who attempted an exercise and either never solved it,
              or needed a level-3 hint or deeper to get there.
  needs help  a student sitting at the bottom of the hint ladder on something
              they still have not solved -- the platform has nothing left to
              give them, which is exactly when a person should step in.

Only graded submits count. Pressing Run in your own browser is not attempting
an exercise, and counting it would make every number here drift away from the
progress the student sees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Concept,
    Exercise,
    ExerciseSession,
    HelpRequest,
    HelpStatus,
    RunMode,
    Submission,
)

#: The rung at which the automatic ladder has run out. Matches L4 in
#: services/hints.py -- if that ceiling moves, this must move with it.
LADDER_EXHAUSTED = 4

#: Needing this deep a hint to solve something still counts as having struggled
#: with it. L3 is where the hint stops pointing and starts explaining.
STRUGGLED_AT_HINT = 3


@dataclass
class StudentStat:
    user_id: str
    display_name: str
    solved: int
    attempts: int
    max_hint_level: int
    last_active_at: datetime | None
    needs_help: bool
    #: Title of an exercise they have exhausted the ladder on and not solved.
    #: The single most useful cell on the row: it turns "Priya needs help" into
    #: "Priya needs help with slicing".
    stuck_on: str | None
    open_questions: int


@dataclass
class DifficultyStat:
    key: str
    label: str
    attempted: int
    solved: int
    struggled: int
    #: Mean graded attempts among students who eventually solved it. None when
    #: nobody has, because a mean over an empty set is not zero.
    avg_attempts_to_solve: float | None
    avg_hint_level: float
    #: Most frequent Python error type on this exercise, if any.
    top_error: str | None = None

    @property
    def struggle_rate(self) -> float:
        return self.struggled / self.attempted if self.attempted else 0.0


@dataclass
class _Work:
    """One student's graded attempts at one exercise, in time order."""

    rows: list[Submission] = field(default_factory=list)

    @property
    def solved(self) -> bool:
        return any(row.passed for row in self.rows)

    @property
    def max_hint(self) -> int:
        return max((row.max_hint_level for row in self.rows), default=0)

    @property
    def attempts_to_solve(self) -> int | None:
        """Graded attempts up to and including the first pass."""
        for index, row in enumerate(self.rows, start=1):
            if row.passed:
                return index
        return None

    @property
    def struggled(self) -> bool:
        return not self.solved or self.max_hint >= STRUGGLED_AT_HINT


def taught_exercises(db: Session) -> list[Exercise]:
    """The shared curriculum only.

    AI-generated practice is excluded deliberately. Those exercises exist for
    one student, so folding them into class difficulty would compare a lesson
    thirty people took against one built for a single person that afternoon --
    and would put a student's private branch in front of their teacher as though
    it were coursework.
    """
    return list(
        db.scalars(
            select(Exercise)
            .where(Exercise.created_by_user_id.is_(None))
            .order_by(Exercise.order_index, Exercise.title)
        )
    )


def _graded(student_ids: set[str], db: Session) -> list[Submission]:
    if not student_ids:
        return []
    return list(
        db.scalars(
            select(Submission)
            .where(
                Submission.user_id.in_(student_ids),
                Submission.run_mode == RunMode.SUBMIT,
            )
            .order_by(Submission.created_at)
        )
    )


def _index(submissions: list[Submission]) -> dict[tuple[str, str], _Work]:
    work: dict[tuple[str, str], _Work] = {}
    for row in submissions:
        work.setdefault((row.user_id, row.exercise_id), _Work()).rows.append(row)
    return work


# ---------------------------------------------------------------------------
# Who is stuck
# ---------------------------------------------------------------------------


def student_rows(students, db: Session) -> list[StudentStat]:
    """One row per student, most in need of attention first.

    Sorted by need rather than alphabetically, because an alphabetical list
    makes the teacher do triage the data can already do. Within "needs help",
    fewest solved first.
    """
    ids = {student.id for student in students}
    submissions = _graded(ids, db)
    work = _index(submissions)
    titles = {ex.id: ex.title for ex in db.scalars(select(Exercise))}

    # Latest activity per student, from sessions as well as submissions, so
    # someone who opened a lesson and read it does not read as absent.
    last_seen: dict[str, datetime] = {}
    for row in submissions:
        current = last_seen.get(row.user_id)
        if current is None or row.created_at > current:
            last_seen[row.user_id] = row.created_at
    if ids:
        for session in db.scalars(
            select(ExerciseSession).where(ExerciseSession.user_id.in_(ids))
        ):
            current = last_seen.get(session.user_id)
            if current is None or session.last_activity_at > current:
                last_seen[session.user_id] = session.last_activity_at

    open_counts: dict[str, int] = {}
    if ids:
        for request in db.scalars(
            select(HelpRequest).where(
                HelpRequest.student_id.in_(ids),
                HelpRequest.status == HelpStatus.OPEN,
            )
        ):
            open_counts[request.student_id] = open_counts.get(request.student_id, 0) + 1

    rows: list[StudentStat] = []
    for student in students:
        mine = {
            exercise_id: entry
            for (user_id, exercise_id), entry in work.items()
            if user_id == student.id
        }
        solved = sum(1 for entry in mine.values() if entry.solved)
        attempts = sum(len(entry.rows) for entry in mine.values())
        deepest = max((entry.max_hint for entry in mine.values()), default=0)

        stuck_on = None
        for exercise_id, entry in mine.items():
            if not entry.solved and entry.max_hint >= LADDER_EXHAUSTED:
                stuck_on = titles.get(exercise_id)
                break

        rows.append(
            StudentStat(
                user_id=student.id,
                display_name=student.display_name,
                solved=solved,
                attempts=attempts,
                max_hint_level=deepest,
                last_active_at=last_seen.get(student.id),
                needs_help=stuck_on is not None,
                stuck_on=stuck_on,
                open_questions=open_counts.get(student.id, 0),
            )
        )

    rows.sort(key=lambda r: (not (r.needs_help or r.open_questions), r.solved))
    return rows


# ---------------------------------------------------------------------------
# What is hard
# ---------------------------------------------------------------------------


def _error_types(submissions: list[Submission]) -> dict[str, dict[str, int]]:
    """Error-type counts per exercise, from the load error or the first failing
    test -- the same extraction the programme-wide view uses."""
    out: dict[str, dict[str, int]] = {}
    for row in submissions:
        results = row.test_results or {}
        error = results.get("error")
        if not error:
            error = next(
                (t.get("error") for t in results.get("tests", []) if t.get("error")),
                None,
            )
        if error and error.get("type"):
            bucket = out.setdefault(row.exercise_id, {})
            bucket[error["type"]] = bucket.get(error["type"], 0) + 1
    return out


def exercise_difficulty(student_ids: set[str], db: Session) -> list[DifficultyStat]:
    """Per-exercise difficulty across the roster, hardest first.

    Ranked by the **number** of students who struggled rather than the rate.
    That is deliberate: a rate puts an exercise one student bounced off once at
    the top of the list, above one that half the class is stuck on. The rate is
    still returned and shown next to it, because a count without a denominator
    is its own kind of lie.
    """
    submissions = _graded(student_ids, db)
    work = _index(submissions)
    errors = _error_types(submissions)
    exercises = {ex.id: ex for ex in taught_exercises(db)}

    by_exercise: dict[str, list[_Work]] = {}
    for (_, exercise_id), entry in work.items():
        if exercise_id in exercises:
            by_exercise.setdefault(exercise_id, []).append(entry)

    stats: list[DifficultyStat] = []
    for exercise_id, entries in by_exercise.items():
        exercise = exercises[exercise_id]
        solved = [e for e in entries if e.solved]
        to_solve = [e.attempts_to_solve for e in solved if e.attempts_to_solve]
        counts = errors.get(exercise_id, {})
        stats.append(
            DifficultyStat(
                key=exercise.slug,
                label=exercise.title,
                attempted=len(entries),
                solved=len(solved),
                struggled=sum(1 for e in entries if e.struggled),
                avg_attempts_to_solve=(sum(to_solve) / len(to_solve)) if to_solve else None,
                avg_hint_level=sum(e.max_hint for e in entries) / len(entries),
                top_error=max(counts, key=counts.get) if counts else None,
            )
        )

    stats.sort(key=lambda s: (-s.struggled, -s.struggle_rate))
    return stats


def concept_difficulty(student_ids: set[str], db: Session) -> list[DifficultyStat]:
    """The same measure rolled up to the six concepts.

    What a teacher plans a lesson from. An exercise being hard might be that
    exercise; a concept being hard is something to reteach.
    """
    submissions = _graded(student_ids, db)
    work = _index(submissions)
    concepts = {ex.id: ex.concept for ex in taught_exercises(db)}

    buckets: dict[str, list[_Work]] = {}
    for (_, exercise_id), entry in work.items():
        concept = concepts.get(exercise_id)
        if concept is not None:
            buckets.setdefault(concept.value, []).append(entry)

    labels = {
        Concept.LISTS.value: "Lists",
        Concept.LOOPS.value: "Loops",
        Concept.DICTS.value: "Dictionaries",
        Concept.STRINGS.value: "Text",
        Concept.FUNCTIONS.value: "Functions",
        Concept.FILE_IO.value: "Files",
    }

    stats: list[DifficultyStat] = []
    for key, entries in buckets.items():
        solved = [e for e in entries if e.solved]
        to_solve = [e.attempts_to_solve for e in solved if e.attempts_to_solve]
        stats.append(
            DifficultyStat(
                key=key,
                label=labels.get(key, key),
                attempted=len(entries),
                solved=len(solved),
                struggled=sum(1 for e in entries if e.struggled),
                avg_attempts_to_solve=(sum(to_solve) / len(to_solve)) if to_solve else None,
                avg_hint_level=sum(e.max_hint for e in entries) / len(entries),
            )
        )

    stats.sort(key=lambda s: (-s.struggle_rate, -s.struggled))
    return stats


def common_errors(student_ids: set[str], db: Session, limit: int = 8) -> list[tuple[str, int]]:
    """What the class is getting wrong, by Python error type.

    Feeds two decisions: what to reteach, and which error translations are
    earning their keep.
    """
    counts: dict[str, int] = {}
    for bucket in _error_types(_graded(student_ids, db)).values():
        for name, count in bucket.items():
            counts[name] = counts.get(name, 0) + count
    return sorted(counts.items(), key=lambda kv: -kv[1])[:limit]
