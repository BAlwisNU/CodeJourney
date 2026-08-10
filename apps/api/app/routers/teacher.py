"""The teaching dashboard's HTTP surface.

Distinct from routers/instructor.py, and the split is by **question asked**
rather than by role:

    /instructor   programme-wide research analytics. Every student in the
                  database, divergence incidents, the whole error distribution.
                  Written for whoever is running the study.
    /teacher      "how is *my class* doing?" Scoped to the students who joined a
                  class this teacher owns, and shaped around the three things a
                  teacher does with the answer: check on people, decide what to
                  reteach, and reply to questions.

Both are instructor-gated; they are not redundant, because a class teacher
should not be reading another cohort's rows to find their own, and a researcher
should not have their population silently narrowed to one classroom.

Every endpoint here derives its population from services/teaching.roster_ids and
never selects students directly. Analytics live in services/insights.py. This
module is transport: validate, delegate, shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Instructor
from ..db import get_db
from ..models import Classroom, HelpRequest, HelpStatus, Reflection
from ..schemas import ReflectionOut
from ..services import insights, teaching

router = APIRouter(prefix="/teacher", tags=["teacher"])

DbSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------


class ClassroomOut(BaseModel):
    id: str
    name: str
    join_code: str
    students: int
    created_at: datetime


class NewClassroom(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    #: Optional. Left out, one is drawn -- a teacher who has no preference
    #: should not have to invent one to get a class.
    join_code: str = Field(default="", max_length=32)


class CodeIn(BaseModel):
    join_code: str = Field(min_length=1, max_length=32)


class StudentOut(BaseModel):
    user_id: str
    display_name: str
    solved: int
    total_exercises: int
    attempts: int
    max_hint_level: int
    last_active_at: datetime | None
    needs_help: bool
    stuck_on: str | None
    open_questions: int


class DifficultyOut(BaseModel):
    key: str
    label: str
    attempted: int
    solved: int
    struggled: int
    struggle_rate: float
    avg_attempts_to_solve: float | None
    avg_hint_level: float
    top_error: str | None = None


class ErrorOut(BaseModel):
    error_type: str
    count: int


class TeacherHome(BaseModel):
    """Everything the dashboard's landing view needs, in one request.

    One call rather than five, because five means five spinners resolving in an
    order nobody chose. At a class-sized roster the whole thing is one pass over
    a few hundred rows.
    """

    display_name: str
    classrooms: list[ClassroomOut]
    #: None until the teacher makes their first class. The dashboard opens on a
    #: setup card in that state rather than on a page of empty tables, which
    #: reads as broken rather than as new.
    has_class: bool
    students: list[StudentOut]
    total_students: int
    needs_help: int
    open_questions: int
    concepts: list[DifficultyOut]
    hardest: list[DifficultyOut]
    common_errors: list[ErrorOut]


def _difficulty(stat: insights.DifficultyStat) -> DifficultyOut:
    return DifficultyOut(
        key=stat.key,
        label=stat.label,
        attempted=stat.attempted,
        solved=stat.solved,
        struggled=stat.struggled,
        struggle_rate=stat.struggle_rate,
        avg_attempts_to_solve=stat.avg_attempts_to_solve,
        avg_hint_level=stat.avg_hint_level,
        top_error=stat.top_error,
    )


def _classroom(classroom: Classroom, counts: dict[str, int]) -> ClassroomOut:
    return ClassroomOut(
        id=classroom.id,
        name=classroom.name,
        join_code=classroom.join_code,
        students=counts.get(classroom.id, 0),
        created_at=classroom.created_at,
    )


# ---------------------------------------------------------------------------
# The dashboard
# ---------------------------------------------------------------------------


@router.get("", response_model=TeacherHome)
def home(
    instructor: Instructor, db: DbSession, classroom_id: str | None = None
) -> TeacherHome:
    classrooms = teaching.classrooms_for(instructor.id, db)
    counts = teaching.member_counts(instructor.id, db)

    if classroom_id is not None:
        try:
            teaching.own_classroom(classroom_id, instructor.id, db)
        except teaching.TeachingError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None

    students = teaching.roster(instructor.id, db, classroom_id)
    ids = {student.id for student in students}
    total_exercises = len(insights.taught_exercises(db))

    rows = insights.student_rows(students, db)
    open_questions = (
        len(
            list(
                db.scalars(
                    select(HelpRequest.id).where(
                        HelpRequest.student_id.in_(ids),
                        HelpRequest.status == HelpStatus.OPEN,
                    )
                )
            )
        )
        if ids
        else 0
    )

    return TeacherHome(
        display_name=instructor.display_name,
        classrooms=[_classroom(c, counts) for c in classrooms],
        has_class=bool(classrooms),
        students=[
            StudentOut(
                user_id=row.user_id,
                display_name=row.display_name,
                solved=row.solved,
                total_exercises=total_exercises,
                attempts=row.attempts,
                max_hint_level=row.max_hint_level,
                last_active_at=row.last_active_at,
                needs_help=row.needs_help,
                stuck_on=row.stuck_on,
                open_questions=row.open_questions,
            )
            for row in rows
        ],
        total_students=len(students),
        needs_help=sum(1 for row in rows if row.needs_help),
        open_questions=open_questions,
        concepts=[_difficulty(s) for s in insights.concept_difficulty(ids, db)],
        hardest=[_difficulty(s) for s in insights.exercise_difficulty(ids, db)[:8]],
        common_errors=[
            ErrorOut(error_type=name, count=count)
            for name, count in insights.common_errors(ids, db)
        ],
    )


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------


@router.get("/classes", response_model=list[ClassroomOut])
def list_classes(instructor: Instructor, db: DbSession) -> list[ClassroomOut]:
    counts = teaching.member_counts(instructor.id, db)
    return [
        _classroom(c, counts) for c in teaching.classrooms_for(instructor.id, db)
    ]


class SuggestedCode(BaseModel):
    join_code: str


@router.get("/classes/suggest-code", response_model=SuggestedCode)
def suggest_code(instructor: Instructor, db: DbSession) -> SuggestedCode:
    """A code no live class is using, for the "draw me one" button.

    Drawn on the server rather than in the browser so the answer is actually
    free -- a client-side random string is a guess that the save then rejects,
    which is a worse experience than not offering the button.

    It is a suggestion, not a reservation: nothing is held, and the same code
    could in principle be taken between this call and the save. At the number
    of teachers this serves, and against 30^6 possibilities, that race is not
    worth a lock -- and if it ever fires, the save says so plainly.
    """
    try:
        return SuggestedCode(join_code=teaching.generate_join_code(db))
    except teaching.TeachingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.post("/classes", response_model=ClassroomOut, status_code=201)
def create_class(
    body: NewClassroom, instructor: Instructor, db: DbSession
) -> ClassroomOut:
    try:
        classroom = teaching.create_classroom(
            instructor, body.name, db, body.join_code
        )
    except teaching.TeachingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _classroom(classroom, {})


@router.patch("/classes/{classroom_id}/code", response_model=ClassroomOut)
def set_class_code(
    classroom_id: str, body: CodeIn, instructor: Instructor, db: DbSession
) -> ClassroomOut:
    """Change a class's code to something the teacher picked.

    Also the way to retire a code that has escaped into the wrong group chat:
    students already in the class stay in it, and only what a new student
    would type changes.
    """
    try:
        classroom = teaching.own_classroom(classroom_id, instructor.id, db)
    except teaching.TeachingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    try:
        classroom = teaching.set_join_code(classroom, body.join_code, db)
    except teaching.TeachingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _classroom(classroom, teaching.member_counts(instructor.id, db))


@router.delete("/classes/{classroom_id}/students/{user_id}", status_code=204)
def remove_student(
    classroom_id: str, user_id: str, instructor: Instructor, db: DbSession
) -> None:
    """Take someone off a roster. Their work is untouched -- see the service."""
    try:
        teaching.remove_member(classroom_id, user_id, instructor.id, db)
    except teaching.TeachingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post("/classes/{classroom_id}/archive", response_model=ClassroomOut)
def archive_class(
    classroom_id: str, instructor: Instructor, db: DbSession
) -> ClassroomOut:
    """Close a finished class. Archived, never deleted -- the term's work stays."""
    try:
        classroom = teaching.own_classroom(classroom_id, instructor.id, db)
    except teaching.TeachingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    classroom.archived_at = datetime.now(classroom.created_at.tzinfo)
    db.commit()
    db.refresh(classroom)
    return _classroom(classroom, teaching.member_counts(instructor.id, db))


# ---------------------------------------------------------------------------
# One student
# ---------------------------------------------------------------------------


class StudentDetail(BaseModel):
    user_id: str
    display_name: str
    solved: int
    total_exercises: int
    attempts: int
    max_hint_level: int
    last_active_at: datetime | None
    stuck_on: str | None
    #: Where this one student struggled, hardest first. Same measure as the
    #: class view, so the two cannot tell different stories.
    hardest: list[DifficultyOut]


@router.get("/students/{user_id}", response_model=StudentDetail)
def student_detail(
    user_id: str, instructor: Instructor, db: DbSession
) -> StudentDetail:
    students = [
        s for s in teaching.roster(instructor.id, db) if s.id == user_id
    ]
    if not students:
        raise HTTPException(status_code=404, detail="Student not found")
    student = students[0]
    row = insights.student_rows([student], db)[0]
    return StudentDetail(
        user_id=student.id,
        display_name=student.display_name,
        solved=row.solved,
        total_exercises=len(insights.taught_exercises(db)),
        attempts=row.attempts,
        max_hint_level=row.max_hint_level,
        last_active_at=row.last_active_at,
        stuck_on=row.stuck_on,
        hardest=[
            _difficulty(s) for s in insights.exercise_difficulty({student.id}, db)[:6]
        ],
    )


@router.get("/students/{user_id}/reflections", response_model=list[ReflectionOut])
def student_reflections(
    user_id: str, instructor: Instructor, db: DbSession
) -> list[Reflection]:
    """A student's journal, if they are on this teacher's roster.

    The scoping is the difference from the equivalent endpoint on /instructor,
    and it is the reason this route exists twice. Journals are the most
    sensitive thing in the database; a class teacher reaching one belonging to a
    student who never joined their class is not a feature.

    What must never happen either way is a *machine* reading these. No
    summarisation, no sentiment scoring, no flagging. A human instructor reading
    a reflection is teaching; a model doing it is the psychological judgement
    the proposal promises not to make.
    """
    if user_id not in teaching.roster_ids(instructor.id, db):
        raise HTTPException(status_code=404, detail="Student not found")
    return list(
        db.scalars(
            select(Reflection)
            .where(Reflection.user_id == user_id)
            .order_by(Reflection.updated_at.desc())
        )
    )
