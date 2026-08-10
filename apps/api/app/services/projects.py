"""Projects, and the lessons underneath them.

The product is organised around things people want to build. This module owns
the two halves of that: turning what someone said at signup into projects they
can actually work on, and resolving a project's concepts into the specific
exercises that teach them.

Nothing here invents content. A project's lessons are the exercises that
already exist for its concepts, in the order the curriculum already teaches
them -- so a project is a route through the library rather than a parallel one.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    STARTER_PROJECTS,
    Concept,
    Exercise,
    LearnerProject,
    OnboardingPlan,
    ProjectCourseLesson,
    SkippedExercise,
    ThemeVariant,
)


def _clean_topics(raw: object) -> list[str]:
    """Concept keys we actually have exercises for, de-duplicated, in order.

    The plan's topics come from a model. Anything it invented is dropped here
    rather than surfacing later as a project whose lesson list has a hole in
    it -- and dropping the topic is better than dropping the project, because
    the rest of it is still a real thing to build.
    """
    known = {c.value for c in Concept}
    out: list[str] = []
    for topic in raw if isinstance(raw, list) else []:
        key = str(topic).strip().lower()
        if key in known and key not in out:
            out.append(key)
    return out


def ensure_projects(user_id: str, db: Session) -> list[LearnerProject]:
    """This learner's projects, creating them the first time they are needed.

    Materialised on read rather than written at signup, for two reasons: the
    welcome chat is skippable, so plenty of accounts would never get any; and
    every account that predates this feature would be stranded with an empty
    dashboard until it did the chat again.

    Someone with a plan gets what they asked for. Everyone else -- skippers,
    demo accounts, accounts made before any of this existed -- gets the starter
    set, so nobody lands on a page with nothing on it.
    """
    existing = list(
        db.scalars(
            select(LearnerProject)
            .where(LearnerProject.user_id == user_id)
            .order_by(LearnerProject.order_index, LearnerProject.created_at)
        )
    )
    if existing:
        return existing

    plan = db.get(OnboardingPlan, user_id)
    seeds: list[dict] = []
    if plan and plan.projects:
        for entry in plan.projects:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title", "")).strip()
            topics = _clean_topics(entry.get("topics"))
            # A project with no title is not a project, and one with no usable
            # topics has no lessons to show under it.
            if title and topics:
                seeds.append(
                    {"title": title[:200], "blurb": str(entry.get("blurb", ""))[:600], "topics": topics}
                )
    if not seeds:
        seeds = [dict(p) for p in STARTER_PROJECTS]

    made = [
        LearnerProject(
            user_id=user_id,
            title=seed["title"],
            blurb=seed["blurb"],
            topics=seed["topics"],
            order_index=i,
        )
        for i, seed in enumerate(seeds)
    ]
    db.add_all(made)
    db.commit()
    for project in made:
        db.refresh(project)
    return made


def course_for(project_id: str, db: Session) -> list[str]:
    """Exercise ids of the course written for this project, in teaching order."""
    return list(
        db.scalars(
            select(ProjectCourseLesson.exercise_id)
            .where(ProjectCourseLesson.project_id == project_id)
            .order_by(ProjectCourseLesson.order_index)
        )
    )


def lessons_for(
    project: LearnerProject,
    exercises: list[Exercise],
    course: list[str] | None = None,
) -> list[Exercise]:
    """The exercises that teach this project's concepts, in teaching order.

    Grouped by concept and concatenated in the project's own topic order, so
    the list reads as "first you need lists, then dictionaries" rather than as
    the library's global ordering interleaved.

    Only the study's control twin is left out, and only where its themed
    partner is also present -- the pair teaches the same concept in different
    framing, so listing both would put one lesson on the checklist twice.

    Not "every generic exercise": 62 of the 69 in the library are the plain
    teaching lessons and carry that variant. Filtering on the variant alone
    removed the whole curriculum and left three lessons for a three-topic
    project. The discriminator is a shared pair_id, of which there is exactly
    one in the seeded library.
    """
    # A written course replaces the library route rather than adding to it.
    # The whole point of one is that it teaches these concepts *in this
    # project* -- paces and distances rather than quests -- so showing both
    # would offer the same six ideas twice and bury the bespoke set under the
    # generic one.
    if course:
        by_id = {ex.id: ex for ex in exercises}
        found = [by_id[eid] for eid in course if eid in by_id]
        if found:
            return found

    wanted = _clean_topics(project.topics)
    shared: dict[str, int] = {}
    for exercise in exercises:
        if exercise.pair_id:
            shared[exercise.pair_id] = shared.get(exercise.pair_id, 0) + 1

    by_concept: dict[str, list[Exercise]] = {key: [] for key in wanted}
    for exercise in exercises:
        if (
            exercise.variant == ThemeVariant.GENERIC
            and exercise.pair_id
            and shared.get(exercise.pair_id, 0) > 1
        ):
            continue
        key = exercise.concept.value if hasattr(exercise.concept, "value") else str(exercise.concept)
        if key in by_concept:
            by_concept[key].append(exercise)
    return [ex for key in wanted for ex in by_concept[key]]


def skipped_ids(user_id: str, db: Session) -> set[str]:
    """Exercises the learner has said they already know."""
    return set(
        db.scalars(
            select(SkippedExercise.exercise_id).where(
                SkippedExercise.user_id == user_id
            )
        )
    )


def mark_skipped(user_id: str, exercise_id: str, db: Session, known: bool) -> None:
    """Say -- or unsay -- that a lesson is already known.

    Reversible on purpose. "I know this" is a judgement made before reading it,
    and someone who turns out to be wrong should be able to put it back without
    hunting for how.
    """
    row = db.get(SkippedExercise, (user_id, exercise_id))
    if known and row is None:
        db.add(SkippedExercise(user_id=user_id, exercise_id=exercise_id))
    elif not known and row is not None:
        db.delete(row)
    db.commit()


def mark_built(project: LearnerProject, db: Session, built: bool) -> None:
    """Finishing the build is a separate act from finishing the lessons."""
    project.built_at = datetime.now(timezone.utc) if built else None
    db.commit()
    db.refresh(project)
