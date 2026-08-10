"""Questions students ask their teacher.

The only channel in the platform where the **student** sets the agenda. The
hint ladder escalates on failure counts, the L5 flag fires when someone has
exhausted it, and the AI tutor talks when spoken to -- all three decide for
themselves what is worth surfacing. This is a person deciding, in their own
words, that they want a human.

Two endpoints per side, and the asymmetry is the design:

    students   POST /help          ask
               GET  /help/mine     see what they asked and what came back
               POST /help/{id}/close   "I worked it out"

    teachers   GET   /help/inbox   every open question from their own roster
               POST  /help/{id}/answer

**This is not the journal, and the separation is structural.** A reflection is
written for the student and no service outside routers/reflections.py reads its
body; a help request is addressed to a teacher and is meant to be read. They
live in different tables behind different endpoints so that neither can quietly
become the other -- and so that "the teacher can read what students write" stays
true of exactly one of them.

Nothing here is ever sent to a model. A question addressed to a person is
answered by that person.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser, Instructor
from ..db import get_db
from ..models import Classroom, Exercise, HelpRequest, HelpStatus, User
from ..services import teaching

router = APIRouter(prefix="/help", tags=["help"])

DbSession = Annotated[Session, Depends(get_db)]


class AskIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    #: The lesson they were on. Slug rather than id, because that is what the
    #: page already knows about itself.
    exercise_slug: str | None = None


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)


class HelpOut(BaseModel):
    id: str
    body: str
    status: str
    answer: str
    created_at: datetime
    answered_at: datetime | None
    #: Present on the teacher's inbox, absent on the student's own list -- they
    #: know who they are.
    student_name: str | None = None
    student_id: str | None = None
    #: Title of the lesson it was asked from, when it was asked from one.
    exercise_title: str | None = None
    exercise_slug: str | None = None
    classroom_name: str | None = None
    answered_by: str | None = None


class AskState(BaseModel):
    """What the student's ask box needs to draw itself."""

    #: False when they have not joined a class. The box then explains how to,
    #: rather than taking a question nobody is listening for.
    can_ask: bool
    teachers: list[str]
    requests: list[HelpOut]


def _shape(
    request: HelpRequest,
    db: Session,
    *,
    with_student: bool = False,
) -> HelpOut:
    exercise = (
        db.get(Exercise, request.exercise_id) if request.exercise_id else None
    )
    classroom = (
        db.get(Classroom, request.classroom_id) if request.classroom_id else None
    )
    answered_by = (
        db.get(User, request.answered_by_id) if request.answered_by_id else None
    )
    student = db.get(User, request.student_id) if with_student else None
    return HelpOut(
        id=request.id,
        body=request.body,
        status=request.status.value,
        answer=request.answer,
        created_at=request.created_at,
        answered_at=request.answered_at,
        student_name=student.display_name if student else None,
        student_id=student.id if student else None,
        exercise_title=exercise.title if exercise else None,
        exercise_slug=exercise.slug if exercise else None,
        classroom_name=classroom.name if classroom else None,
        answered_by=answered_by.display_name if answered_by else None,
    )


# ---------------------------------------------------------------------------
# Student side
# ---------------------------------------------------------------------------


@router.get("/mine", response_model=AskState)
def my_requests(user: CurrentUser, db: DbSession) -> AskState:
    rows = list(
        db.scalars(
            select(HelpRequest)
            .where(HelpRequest.student_id == user.id)
            .order_by(HelpRequest.created_at.desc())
        )
    )
    teachers = teaching.teacher_names(user.id, db)
    return AskState(
        can_ask=bool(teachers),
        teachers=teachers,
        requests=[_shape(row, db) for row in rows],
    )


@router.post("", response_model=HelpOut, status_code=201)
def ask(body: AskIn, user: CurrentUser, db: DbSession) -> HelpOut:
    """Raise a question.

    Attached to the first class the student is in. Most students are in one;
    someone in two gets their question routed to the class they joined first,
    which is a guess, but a wrong guess here costs a teacher reading a question
    meant for a colleague, not a lost message.
    """
    classrooms = teaching.classrooms_of(user.id, db)
    if not classrooms:
        raise HTTPException(
            status_code=409,
            detail=(
                "You're not in a class yet, so there's no teacher to send this "
                "to. Ask them for their class code and join from your account "
                "page."
            ),
        )

    exercise = None
    if body.exercise_slug:
        exercise = db.scalar(
            select(Exercise).where(Exercise.slug == body.exercise_slug)
        )

    request = HelpRequest(
        student_id=user.id,
        classroom_id=classrooms[0].id,
        exercise_id=exercise.id if exercise else None,
        body=body.body.strip(),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return _shape(request, db)


@router.post("/{request_id}/close", response_model=HelpOut)
def close(request_id: str, user: CurrentUser, db: DbSession) -> HelpOut:
    """"I worked it out." Closing is the student's to do, never the teacher's.

    A teacher marking their own answer as resolved would measure whether they
    replied, not whether it helped.
    """
    request = db.get(HelpRequest, request_id)
    if request is None or request.student_id != user.id:
        raise HTTPException(status_code=404, detail="Question not found")
    request.status = HelpStatus.CLOSED
    db.commit()
    db.refresh(request)
    return _shape(request, db)


# ---------------------------------------------------------------------------
# Teacher side
# ---------------------------------------------------------------------------


@router.get("/inbox", response_model=list[HelpOut])
def inbox(
    instructor: Instructor,
    db: DbSession,
    classroom_id: str | None = None,
    include_closed: bool = False,
) -> list[HelpOut]:
    """Questions from this teacher's own students, oldest first.

    Oldest first on purpose: a queue sorted newest-first quietly buries the
    person who has been waiting longest, which is the opposite of what a queue
    is for.
    """
    ids = teaching.roster_ids(instructor.id, db, classroom_id)
    if not ids:
        return []
    query = select(HelpRequest).where(HelpRequest.student_id.in_(ids))
    if not include_closed:
        query = query.where(HelpRequest.status != HelpStatus.CLOSED)
    rows = db.scalars(query.order_by(HelpRequest.created_at))
    return [_shape(row, db, with_student=True) for row in rows]


@router.post("/{request_id}/answer", response_model=HelpOut)
def answer(
    request_id: str, body: AnswerIn, instructor: Instructor, db: DbSession
) -> HelpOut:
    """Reply to a question, if the student is on this teacher's roster."""
    request = db.get(HelpRequest, request_id)
    if request is None or request.student_id not in teaching.roster_ids(
        instructor.id, db
    ):
        raise HTTPException(status_code=404, detail="Question not found")

    request.answer = body.answer.strip()
    request.answered_by_id = instructor.id
    request.answered_at = datetime.now(timezone.utc)
    request.status = HelpStatus.ANSWERED
    db.commit()
    db.refresh(request)
    return _shape(request, db, with_student=True)
