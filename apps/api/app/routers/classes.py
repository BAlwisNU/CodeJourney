"""Joining a class, from the student's side.

Separate from routers/teacher.py because that whole module is instructor-gated
and this is the one part of classes a student touches. Separate from
routers/help.py because being in a class and asking a question are different
things -- you join once and ask many times.

Joining is a code the student types, not an invitation they wait for. A teacher
reads six characters out in a room and everyone is in within a minute; collecting
thirty email addresses first is how a class tool goes unused in week one.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import ClassroomMember, Role, User
from ..services import teaching

router = APIRouter(prefix="/classes", tags=["classes"])

DbSession = Annotated[Session, Depends(get_db)]


class JoinIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class MyClass(BaseModel):
    id: str
    name: str
    teacher_name: str


@router.get("/mine", response_model=list[MyClass])
def my_classes(user: CurrentUser, db: DbSession) -> list[MyClass]:
    out: list[MyClass] = []
    for classroom in teaching.classrooms_of(user.id, db):
        teacher = db.get(User, classroom.teacher_id)
        out.append(
            MyClass(
                id=classroom.id,
                name=classroom.name,
                teacher_name=teacher.display_name if teacher else "Your teacher",
            )
        )
    return out


@router.post("/join", response_model=MyClass, status_code=201)
def join(body: JoinIn, user: CurrentUser, db: DbSession) -> MyClass:
    """Join with a code.

    Teachers are refused rather than silently enrolled: a teacher account in
    someone else's roster would appear in their class averages and their
    "needs help" count, which quietly corrupts every number on that dashboard.
    """
    if user.role is Role.INSTRUCTOR:
        raise HTTPException(
            status_code=409,
            detail="Teacher accounts can't join a class as a student.",
        )
    try:
        classroom = teaching.join_by_code(user, body.code, db)
    except teaching.TeachingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    teacher = db.get(User, classroom.teacher_id)
    return MyClass(
        id=classroom.id,
        name=classroom.name,
        teacher_name=teacher.display_name if teacher else "Your teacher",
    )


@router.delete("/{classroom_id}", status_code=204)
def leave(classroom_id: str, user: CurrentUser, db: DbSession) -> None:
    """Leave a class.

    Removes the membership and nothing else. Every submission, draft, project
    and reflection stays theirs -- the same rule consent withdrawal follows, for
    the same reason: leaving something should never cost you the work you did
    while you were in it.
    """
    row = db.get(ClassroomMember, (classroom_id, user.id))
    if row is not None:
        db.delete(row)
        db.commit()
