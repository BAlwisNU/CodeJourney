"""What the learner is building, and the lessons under each thing.

The dashboard's primary view. It answers "what am I making, and what is left
to learn before I can make it?" -- which is the question the platform is for,
and one the topic-ordered curriculum could not answer at all.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import (
    Concept,
    Exercise,
    LearnerProject,
    ProjectCourseLesson,
    RunMode,
    Submission,
)
from ..routers.tutor import _learner_brief
from ..services import projects as svc
from ..services import tutor

logger = logging.getLogger(__name__)

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
    #: True when these lessons were written for this project rather than
    #: taken from the shared library.
    has_course: bool = False


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
    course: list[str] | None = None,
) -> ProjectOut:
    lessons: list[LessonOut] = []
    done = 0
    next_slug: str | None = None
    for exercise in svc.lessons_for(project, exercises, course):
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
        has_course=bool(course),
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
        projects=[
            _shape(p, exercises, status, skipped, svc.course_for(p.id, db))
            for p in rows
        ]
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
        project,
        _library(user.id, db),
        _status_map(user.id, db),
        svc.skipped_ids(user.id, db),
        svc.course_for(project.id, db),
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
        project,
        _library(user.id, db),
        _status_map(user.id, db),
        svc.skipped_ids(user.id, db),
        svc.course_for(project.id, db),
    )


@router.put("/lessons/{slug}/known", status_code=204)
def set_known(slug: str, body: KnownIn, user: CurrentUser, db: DbSession) -> None:
    """Mark a lesson as already known, or take that back."""
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    svc.mark_skipped(user.id, exercise.id, db, body.known)


@router.post("/{project_id}/course/stream")
def build_course(project_id: str, user: CurrentUser, db: DbSession):
    """Write a course of lessons for this project, streamed as each one lands.

    The library teaches lists and loops in the abstract. This teaches them in
    the learner's own project: a running tracker gets exercises about paces and
    distances, a group-chat bot gets exercises about messages and names, and
    every function is one they could paste into the thing they are building.

    Streamed, and not for polish. Each lesson is a model call plus a real
    harness run to prove the answer passes, which is ten to twenty seconds; a
    course of six is therefore minutes, and a request that returns nothing for
    two minutes looks broken however fast it eventually is. Lessons are
    committed one at a time as they pass, so a learner who closes the tab
    half way keeps the three that were finished rather than losing all six.

    Line shapes:
        {"type": "planned", "lessons": [{title, concept}, ...]}
        {"type": "lesson",  "slug": ..., "title": ..., "index": n, "of": m}
        {"type": "skipped", "title": ..., "reason": ...}
        {"type": "done",    "built": n}
        {"type": "error",   "message": ...}
    """
    project = _own(project_id, user.id, db)

    # State before capability, deliberately. Both can be true at once, and
    # "this already has a course" is the answer that tells the caller
    # something they can act on -- where "lesson writing is switched off"
    # sends them to find an administrator for a request that would have been
    # refused anyway.
    existing = db.scalar(
        select(func.count(ProjectCourseLesson.exercise_id)).where(
            ProjectCourseLesson.project_id == project.id
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="This project already has a course. Delete it to rebuild.",
        )

    if not tutor.enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "Lesson writing isn't switched on for this server — an "
                "instructor needs to add an API key."
            ),
        )

    learner = _learner_brief(user.id, db)
    setting = f"{project.title}. {project.blurb}".strip()

    def emit():
        try:
            plan = tutor.plan_course(
                project.title, project.blurb, list(project.topics or []), learner
            )
        except Exception as exc:  # noqa: BLE001 -- external call; never 500 mid-stream
            logger.exception("course planning failed")
            yield json.dumps(
                {
                    "type": "error",
                    "message": "I couldn't sketch a course for that just now. Try again in a moment.",
                }
            ) + "\n"
            return

        yield json.dumps(
            {
                "type": "planned",
                "lessons": [
                    {"title": step["title"], "concept": step["concept"]} for step in plan
                ],
            }
        ) + "\n"

        built = 0
        for index, step in enumerate(plan):
            try:
                spec = tutor.generate_exercise(
                    step["concept"],
                    step["focus"],
                    step["title"],
                    created_by_user_id=user.id,
                    learner=learner,
                    setting=setting,
                )
            except Exception:  # noqa: BLE001 -- one bad lesson must not end the course
                logger.exception("course lesson generation failed")
                yield json.dumps(
                    {
                        "type": "skipped",
                        "title": step["title"],
                        "reason": "couldn't be written this time",
                    }
                ) + "\n"
                continue

            exercise = Exercise(**spec)
            db.add(exercise)
            db.flush()
            db.add(
                ProjectCourseLesson(
                    project_id=project.id,
                    exercise_id=exercise.id,
                    order_index=index,
                )
            )
            # Committed per lesson, so closing the tab keeps what is finished.
            db.commit()
            built += 1
            yield json.dumps(
                {
                    "type": "lesson",
                    "slug": exercise.slug,
                    "title": exercise.title,
                    "index": index + 1,
                    "of": len(plan),
                }
            ) + "\n"

        yield json.dumps({"type": "done", "built": built}) + "\n"

    return StreamingResponse(emit(), media_type="application/x-ndjson")


@router.delete("/{project_id}/course", status_code=204)
def delete_course(project_id: str, user: CurrentUser, db: DbSession) -> None:
    """Throw the course away so it can be written again.

    Deletes the generated exercises themselves, not just the links: they exist
    only for this project, and leaving them behind would put orphaned lessons
    on the learner's dashboard with nothing pointing at them.
    """
    project = _own(project_id, user.id, db)
    rows = list(
        db.scalars(
            select(ProjectCourseLesson).where(
                ProjectCourseLesson.project_id == project.id
            )
        )
    )
    for row in rows:
        exercise = db.get(Exercise, row.exercise_id)
        db.delete(row)
        # Only ever this learner's own generated lesson -- never the taught
        # curriculum, which has no author.
        if exercise is not None and exercise.created_by_user_id == user.id:
            db.delete(exercise)
    db.commit()


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
    return ProjectsOut(
        projects=[
            _shape(p, exercises, status, skipped, svc.course_for(p.id, db))
            for p in rows
        ]
    )
