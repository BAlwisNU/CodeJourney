"""What the learner is building, and the lessons under each thing.

The dashboard's primary view. It answers "what am I making, and what is left
to learn before I can make it?" -- which is the question the platform is for,
and one the topic-ordered curriculum could not answer at all.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import (
    Concept,
    Exercise,
    LearnerProject,
    RunMode,
    Submission,
)
from ..services import projects as svc

router = APIRouter(prefix="/projects", tags=["projects"])

DbSession = Annotated[Session, Depends(get_db)]


class LessonOut(BaseModel):
    slug: str
    title: str
    concept: str
    #: solved | in_progress | not_started | known
    status: str


class ProjectOut(BaseModel):
    id: str
    title: str
    blurb: str
    topics: list[str]
    built: bool
    lessons: list[LessonOut]
    #: Counted here rather than in the browser so the card and the page behind
    #: it can never disagree about how far along something is.
    done: int
    total: int
    #: The lesson to open next: the first that is neither solved nor known.
    next_slug: str | None


class ProjectsOut(BaseModel):
    projects: list[ProjectOut]


class NewProject(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    blurb: str = Field(default="", max_length=600)
    topics: list[str] = Field(default_factory=list)


class KnownIn(BaseModel):
    known: bool = True


class BuiltIn(BaseModel):
    built: bool = True


def _status_map(user_id: str, db: Session) -> dict[str, str]:
    """Per-exercise status, from graded submissions only.

    Runs are logged as behaviour but pressing Run in your own browser is not
    doing the exercise -- the same rule the dashboard uses, applied here so the
    two views of progress cannot drift apart.
    """
    rows = list(
        db.scalars(
            select(Submission)
            .where(Submission.user_id == user_id, Submission.run_mode == RunMode.SUBMIT)
            .order_by(Submission.created_at)
        )
    )
    out: dict[str, str] = {}
    for row in rows:
        if out.get(row.exercise_id) == "solved":
            continue
        out[row.exercise_id] = "solved" if row.passed else "in_progress"
    return out


def _shape(
    project: LearnerProject,
    exercises: list[Exercise],
    status: dict[str, str],
    skipped: set[str],
) -> ProjectOut:
    lessons: list[LessonOut] = []
    done = 0
    next_slug: str | None = None
    for exercise in svc.lessons_for(project, exercises):
        if exercise.id in skipped:
            state = "known"
        else:
            state = status.get(exercise.id, "not_started")
        # "Known" counts as cleared for the purpose of what is left to do, but
        # it is a different word on the card: the learner said it, we did not
        # watch them do it.
        if state in ("solved", "known"):
            done += 1
        elif next_slug is None:
            next_slug = exercise.slug
        lessons.append(
            LessonOut(
                slug=exercise.slug,
                title=exercise.title,
                concept=exercise.concept.value,
                status=state,
            )
        )
    return ProjectOut(
        id=project.id,
        title=project.title,
        blurb=project.blurb,
        topics=list(project.topics or []),
        built=project.built_at is not None,
        lessons=lessons,
        done=done,
        total=len(lessons),
        next_slug=next_slug,
    )


def _library(user_id: str, db: Session) -> list[Exercise]:
    """The taught curriculum plus this learner's own generated practice."""
    return list(
        db.scalars(
            select(Exercise)
            .where(
                (Exercise.created_by_user_id.is_(None))
                | (Exercise.created_by_user_id == user_id)
            )
            .order_by(Exercise.order_index, Exercise.title)
        )
    )


@router.get("", response_model=ProjectsOut)
def list_projects(user: CurrentUser, db: DbSession) -> ProjectsOut:
    rows = svc.ensure_projects(user.id, db)
    exercises = _library(user.id, db)
    status = _status_map(user.id, db)
    skipped = svc.skipped_ids(user.id, db)
    return ProjectsOut(
        projects=[_shape(p, exercises, status, skipped) for p in rows]
    )


@router.post("", response_model=ProjectOut, status_code=201)
def add_project(body: NewProject, user: CurrentUser, db: DbSession) -> ProjectOut:
    """Start something new.

    Topics are filtered to ones that exist rather than rejected: a project
    whose concepts are half recognised is still worth having, and refusing the
    whole thing over one bad key would lose the title someone just typed.
    """
    known = {c.value for c in Concept}
    topics = [t for t in body.topics if t in known]
    if not topics:
        raise HTTPException(
            status_code=422,
            detail="A project needs at least one topic that has lessons behind it.",
        )
    svc.ensure_projects(user.id, db)
    highest = db.scalar(
        select(LearnerProject.order_index)
        .where(LearnerProject.user_id == user.id)
        .order_by(LearnerProject.order_index.desc())
    )
    project = LearnerProject(
        user_id=user.id,
        title=body.title.strip(),
        blurb=body.blurb.strip(),
        topics=topics,
        order_index=(highest or 0) + 1,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _shape(
        project, _library(user.id, db), _status_map(user.id, db), svc.skipped_ids(user.id, db)
    )


def _own(project_id: str, user_id: str, db: Session) -> LearnerProject:
    project = db.get(LearnerProject, project_id)
    if project is None or project.user_id != user_id:
        # Not 403: whether someone else's project exists is not this caller's
        # business either.
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}/built", response_model=ProjectOut)
def set_built(
    project_id: str, body: BuiltIn, user: CurrentUser, db: DbSession
) -> ProjectOut:
    project = _own(project_id, user.id, db)
    svc.mark_built(project, db, body.built)
    return _shape(
        project, _library(user.id, db), _status_map(user.id, db), svc.skipped_ids(user.id, db)
    )


@router.put("/lessons/{slug}/known", status_code=204)
def set_known(slug: str, body: KnownIn, user: CurrentUser, db: DbSession) -> None:
    """Mark a lesson as already known, or take that back."""
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    svc.mark_skipped(user.id, exercise.id, db, body.known)


@router.get("/for-lesson/{slug}", response_model=ProjectsOut)
def projects_for_lesson(slug: str, user: CurrentUser, db: DbSession) -> ProjectsOut:
    """Which of the learner's projects need this lesson.

    What the lesson page uses to say why it is asking you to learn this. A
    lesson with no answer here is not an error -- it means the learner reached
    it some other way, and the page simply says nothing.
    """
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    concept = exercise.concept.value
    rows = [
        p for p in svc.ensure_projects(user.id, db) if concept in (p.topics or [])
    ]
    exercises = _library(user.id, db)
    status = _status_map(user.id, db)
    skipped = svc.skipped_ids(user.id, db)
    return ProjectsOut(projects=[_shape(p, exercises, status, skipped) for p in rows])
