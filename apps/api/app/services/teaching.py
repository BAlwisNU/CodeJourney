"""Classes, membership, and who a teacher is allowed to see.

This module owns one question and answers it in one place: **which students is
this teacher entitled to look at?** Every teacher-facing endpoint routes through
`roster_ids` rather than selecting students directly, so there is a single
function to audit and a single function to change.

That matters more here than it would in most apps. Instructors may read student
journals, so a scoping bug is not a cosmetic leak -- it is one teacher reading
another cohort's private writing about struggling. The rule is deliberately
boring: a teacher sees exactly the students who joined a class that teacher
owns, and nobody else.

Nothing here is analytics. Turning a roster into progress, difficulty and
struggle signals is services/insights.py -- kept apart so membership rules stay
readable and so the analytics can be tested against a fixed roster.
"""

from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    JOIN_CODE_ALPHABET,
    JOIN_CODE_LENGTH,
    Classroom,
    ClassroomMember,
    Role,
    User,
)

#: How many times to draw a fresh code before giving up. At 30^6 (~729 million)
#: a collision is already vanishingly unlikely; the retry exists so that the
#: unlikely case is a second draw rather than a 500 in front of a teacher who is
#: standing at the front of a room.
_CODE_ATTEMPTS = 12


class TeachingError(Exception):
    """Something a teacher or student did that has a sentence-long explanation.

    Raised with text meant to be shown, so routers can turn it straight into a
    4xx detail rather than inventing wording at the edge.
    """


def _draw_code() -> str:
    return "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(JOIN_CODE_LENGTH))


def generate_join_code(db: Session) -> str:
    """A code no live class is already using.

    `secrets` rather than `random`: a guessable code is a way into a class
    roster, and the cost of the stronger generator is nil at this frequency.
    """
    for _ in range(_CODE_ATTEMPTS):
        code = _draw_code()
        if db.scalar(select(Classroom.id).where(Classroom.join_code == code)) is None:
            return code
    raise TeachingError("Couldn't allocate a class code just now. Try again.")


# ---------------------------------------------------------------------------
# Teacher side
# ---------------------------------------------------------------------------


#: A chosen code has to be typeable on a phone and readable off a whiteboard,
#: and long enough not to be stumbled into by someone guessing.
MIN_CHOSEN_CODE = 4
MAX_CHOSEN_CODE = 12


def normalise_code(raw: str) -> str:
    """Clean up a code a teacher typed, or say why it cannot be used.

    Forgiving about how it was entered -- case, spaces and dashes all go --
    because the same code gets written on a board, said out loud and pasted
    into a chat, and none of those agree on formatting.

    Letters and digits only. Note what is NOT enforced: the confusable
    characters the generator avoids. A random code has no meaning to fall back
    on, so an O that might be a zero is a genuine trap; "YEAR10" is remembered
    as a word, and refusing it because it contains a 1 would be pedantry at the
    expense of the thing that makes a chosen code worth having.
    """
    cleaned = "".join(
        ch for ch in raw.strip().upper() if ch.isalnum()
    )
    if not cleaned:
        raise TeachingError("A class code needs some letters or numbers in it.")
    if len(cleaned) < MIN_CHOSEN_CODE:
        raise TeachingError(
            f"That code is too short — {MIN_CHOSEN_CODE} characters at least, "
            "so nobody lands in your class by accident."
        )
    if len(cleaned) > MAX_CHOSEN_CODE:
        raise TeachingError(
            f"That code is too long — {MAX_CHOSEN_CODE} characters at most, "
            "or it won't get typed correctly."
        )
    return cleaned


def _claim_code(code: str, db: Session, *, allow: str | None = None) -> str:
    """Take a chosen code, or explain that somebody already has it.

    `allow` is the classroom already holding it, so re-saving a class without
    changing its code is not a clash with itself.
    """
    taken = db.scalar(select(Classroom).where(Classroom.join_code == code))
    if taken is not None and taken.id != allow:
        raise TeachingError(
            "Another class is already using that code. Try a different one."
        )
    return code


def create_classroom(
    teacher: User, name: str, db: Session, code: str | None = None
) -> Classroom:
    """Make a class, with a code the teacher chose or one drawn for them.

    Choosing is worth supporting because the code is spoken: "join YEAR10" is
    a sentence a room can act on, where "join Q69NEK" gets misheard twice and
    typed wrong three times.
    """
    cleaned = name.strip()
    if not cleaned:
        raise TeachingError("A class needs a name.")
    join_code = (
        _claim_code(normalise_code(code), db) if code and code.strip() else generate_join_code(db)
    )
    classroom = Classroom(
        teacher_id=teacher.id,
        name=cleaned[:120],
        join_code=join_code,
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return classroom


def set_join_code(classroom: Classroom, code: str, db: Session) -> Classroom:
    """Change an existing class's code.

    Students already in the class stay in it -- membership is a row, not a
    password. What changes is only what a new student would type, which is why
    this is also the way to shut out a code that has escaped into the wrong
    group chat.
    """
    classroom.join_code = _claim_code(normalise_code(code), db, allow=classroom.id)
    db.commit()
    db.refresh(classroom)
    return classroom


def classrooms_for(teacher_id: str, db: Session, *, include_archived: bool = False):
    """This teacher's classes, newest last so codes stay where they were."""
    query = select(Classroom).where(Classroom.teacher_id == teacher_id)
    if not include_archived:
        query = query.where(Classroom.archived_at.is_(None))
    return list(db.scalars(query.order_by(Classroom.created_at)))


def own_classroom(classroom_id: str, teacher_id: str, db: Session) -> Classroom:
    """Fetch a class, or refuse.

    404 rather than 403 for someone else's class: whether a given class exists
    is not this caller's business either, and a 403 confirms the id is real.
    """
    classroom = db.get(Classroom, classroom_id)
    if classroom is None or classroom.teacher_id != teacher_id:
        raise TeachingError("Class not found")
    return classroom


def roster_ids(
    teacher_id: str, db: Session, classroom_id: str | None = None
) -> set[str]:
    """The user ids this teacher may look at.

    The single scoping decision in the teacher-facing API. Pass `classroom_id`
    to narrow to one class; omit it for every student across all of this
    teacher's classes.

    Returns a set rather than a list because a student in two of the same
    teacher's classes is one student, and counting them twice would overstate
    every number on the dashboard.
    """
    query = (
        select(ClassroomMember.user_id)
        .join(Classroom, Classroom.id == ClassroomMember.classroom_id)
        .where(Classroom.teacher_id == teacher_id)
    )
    if classroom_id is not None:
        query = query.where(Classroom.id == classroom_id)
    return set(db.scalars(query))


def roster(teacher_id: str, db: Session, classroom_id: str | None = None) -> list[User]:
    """The students themselves, alphabetically.

    Ordering is by name here and re-sorted by need in the dashboard. Two
    different jobs: this one has to be stable so a roster does not reshuffle
    under a teacher's cursor.
    """
    ids = roster_ids(teacher_id, db, classroom_id)
    if not ids:
        return []
    return list(
        db.scalars(
            select(User).where(User.id.in_(ids)).order_by(func.lower(User.display_name))
        )
    )


def member_counts(teacher_id: str, db: Session) -> dict[str, int]:
    """How many students are in each of this teacher's classes."""
    rows = db.execute(
        select(ClassroomMember.classroom_id, func.count(ClassroomMember.user_id))
        .join(Classroom, Classroom.id == ClassroomMember.classroom_id)
        .where(Classroom.teacher_id == teacher_id)
        .group_by(ClassroomMember.classroom_id)
    )
    return {classroom_id: count for classroom_id, count in rows}


def remove_member(classroom_id: str, user_id: str, teacher_id: str, db: Session) -> None:
    """Take a student off a roster.

    Removes the membership only. Their work, submissions and progress are
    theirs and survive -- leaving a class must never cost someone the thing they
    came for, which is the same rule consent withdrawal follows.
    """
    own_classroom(classroom_id, teacher_id, db)
    row = db.get(ClassroomMember, (classroom_id, user_id))
    if row is not None:
        db.delete(row)
        db.commit()


# ---------------------------------------------------------------------------
# Student side
# ---------------------------------------------------------------------------


def join_by_code(student: User, code: str, db: Session) -> Classroom:
    """Put a student in a class from a code they typed.

    Whitespace and case are forgiving because the code arrives by whiteboard,
    verbally, or over a chat message, and none of those preserve either.
    """
    cleaned = code.strip().upper().replace(" ", "").replace("-", "")
    if not cleaned:
        raise TeachingError("Enter the code your teacher gave you.")

    classroom = db.scalar(select(Classroom).where(Classroom.join_code == cleaned))
    if classroom is None:
        raise TeachingError("No class has that code. Check it and try again.")
    if classroom.archived_at is not None:
        raise TeachingError("That class has been closed.")
    if classroom.teacher_id == student.id:
        raise TeachingError("That's your own class — you're already teaching it.")

    existing = db.get(ClassroomMember, (classroom.id, student.id))
    if existing is None:
        db.add(ClassroomMember(classroom_id=classroom.id, user_id=student.id))
        db.commit()
    return classroom


def classrooms_of(student_id: str, db: Session) -> list[Classroom]:
    """The classes a student has joined, with the archived ones left out."""
    return list(
        db.scalars(
            select(Classroom)
            .join(ClassroomMember, ClassroomMember.classroom_id == Classroom.id)
            .where(
                ClassroomMember.user_id == student_id,
                Classroom.archived_at.is_(None),
            )
            .order_by(Classroom.created_at)
        )
    )


def teacher_names(student_id: str, db: Session) -> list[str]:
    """Who this student can address a question to, for the ask box."""
    return list(
        db.scalars(
            select(User.display_name)
            .join(Classroom, Classroom.teacher_id == User.id)
            .join(ClassroomMember, ClassroomMember.classroom_id == Classroom.id)
            .where(
                ClassroomMember.user_id == student_id,
                Classroom.archived_at.is_(None),
                User.role == Role.INSTRUCTOR,
            )
            .distinct()
        )
    )
