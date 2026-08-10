"""The student dashboard's data.

Computed server-side rather than by rolling up `/submissions` in the browser, for
two reasons: the Expo companion (Week 5) needs the same numbers and shouldn't
reimplement them, and a client-side rollup would need every submission row just
to render a progress bar.

WHAT THIS ENDPOINT DELIBERATELY DOES NOT RETURN, and why it matters:

    time-on-task        omitted
    hint depth          omitted

Both are dependent variables in the Week 7 study. Showing a participant their own
time-on-task, or how deep into the hint ladder they went, changes the behaviour
being measured -- someone who can see "you used hint 4" is under quiet pressure to
avoid hints next time, and someone watching a timer works differently than someone
who isn't. That is measurement reactivity, and it would contaminate exactly the
variables the study exists to measure.

Completion is different: a student obviously knows which exercises they've solved,
so surfacing it adds no distortion. It is shown.

Instructors get these numbers for their students in the Week 6 dashboard, where
reactivity isn't a concern because the instructor isn't the participant.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import (
    Exercise,
    ExerciseSession,
    LearnerProject,
    OnboardingPlan,
    RunMode,
    Submission,
    ThemeVariant,
)
from ..schemas import (
    BranchOut,
    ConceptProgress,
    DashboardOut,
    ExerciseProgress,
    Recommendation,
)

router = APIRouter(prefix="/progress", tags=["progress"])

DbSession = Annotated[Session, Depends(get_db)]


#: How many to offer. Four is a strip; ten is a syllabus, which is the thing
#: the dashboard was reorganised to stop being.
_RECOMMEND = 4

_CONCEPT_NAME = {
    "lists": "lists",
    "loops": "loops",
    "dicts": "dictionaries",
    "strings": "text",
    "functions": "functions",
    "file_io": "files",
}


def _recommend(
    user_id: str,
    exercises: list[Exercise],
    rows: list[ExerciseProgress],
    continue_slug: str | None,
    db: Session,
) -> list[Recommendation]:
    """A few lessons worth doing next. Never empty for a signed-in account.

    A brand-new account used to reach a dashboard whose two strips -- recent
    lessons and practice built for you -- were both empty, because it had no
    history and had accepted no offers. So the page ended after the project
    cards, on the first visit, which is the one visit that has to land.

    Three sources, best first, and each says why it is recommending something:

      1. **The topics they asked for.** The signup conversation records which
         concepts serve what they want to build; those lessons come first.
      2. **What their projects need**, for someone who skipped the chat or
         whose plan named no topics.
      3. **The beginning of the curriculum**, which is the right answer for
         anyone the first two cannot speak for and is never nothing.

    Deliberately not "mastery-ranked": there is no mastery score in this
    system (the table has no writer), and dressing curriculum order up as
    personalisation would be a claim the platform cannot back.
    """
    done = {row.id for row in rows if row.status == "solved"}

    # Curriculum order is not teaching order at the front of the list. The six
    # exercises at order_index 1-6 are the study set -- one themed exercise per
    # concept, the within-subjects instrument -- and the taught ladder starts
    # at 101 with "Making a list". Trusting order_index alone recommended "How
    # long is this boss fight?" to someone who had never written a line.
    #
    # It takes both conditions, and each was found by watching the wrong thing
    # come out first:
    #
    #   themed variant       the five remaining study exercises, which are one
    #                        per concept and not a beginner's first anything
    #   shared pair_id       the control twin of the sixth, which is generic
    #                        and still sorts to the front (order_index 2)
    #
    # What is left is the 61-lesson taught ladder, starting at "Making a list".
    shared: dict[str, int] = {}
    for exercise in exercises:
        if exercise.pair_id:
            shared[exercise.pair_id] = shared.get(exercise.pair_id, 0) + 1
    teaching = [
        ex
        for ex in exercises
        if ex.variant is ThemeVariant.GENERIC
        and not (ex.pair_id and shared.get(ex.pair_id, 0) > 1)
    ]
    ladder = teaching or exercises

    def offer(exercise: Exercise, reason: str) -> Recommendation:
        return Recommendation(
            slug=exercise.slug,
            title=exercise.title,
            concept=exercise.concept.value,
            reason=reason,
        )

    # Never re-offer the one the resume card is already offering, and never
    # something they have finished.
    def eligible(exercise: Exercise) -> bool:
        return exercise.id not in done and exercise.slug != continue_slug

    picked: list[Recommendation] = []
    seen: set[str] = set()

    def take(exercise: Exercise, reason: str) -> None:
        if exercise.id in seen or not eligible(exercise):
            return
        seen.add(exercise.id)
        picked.append(offer(exercise, reason))

    plan = db.get(OnboardingPlan, user_id)
    wanted = [t for t in (plan.topics if plan else []) or []]
    for topic in wanted:
        for exercise in ladder:
            if len(picked) >= _RECOMMEND:
                break
            if exercise.concept.value == topic:
                take(exercise, f"You said you wanted {_CONCEPT_NAME.get(topic, topic)}")

    if len(picked) < _RECOMMEND:
        project_topics: list[str] = []
        for project in db.scalars(
            select(LearnerProject).where(LearnerProject.user_id == user_id)
        ):
            for topic in project.topics or []:
                if topic not in project_topics:
                    project_topics.append(topic)
        for topic in project_topics:
            for exercise in ladder:
                if len(picked) >= _RECOMMEND:
                    break
                if exercise.concept.value == topic:
                    take(exercise, "Your projects need this")

    # The floor: the start of the taught sequence, which is the right answer
    # for anyone the two better sources cannot speak for.
    for exercise in ladder:
        if len(picked) >= _RECOMMEND:
            break
        take(exercise, "A good place to start")

    return picked[:_RECOMMEND]


@router.get("", response_model=DashboardOut)
def dashboard(user: CurrentUser, db: DbSession) -> DashboardOut:
    # The taught curriculum (created_by is null) plus this student's own AI-built
    # branches. Another student's branches are theirs alone -- excluded here so a
    # generated lesson never clutters anyone else's dashboard.
    exercises = list(
        db.scalars(
            select(Exercise)
            .where(
                (Exercise.created_by_user_id.is_(None))
                | (Exercise.created_by_user_id == user.id)
            )
            .order_by(Exercise.order_index, Exercise.title)
        )
    )

    # Only graded attempts count toward progress. Runs are logged as behaviour
    # (they're most of the learning signal) but a student hasn't "done" an
    # exercise by pressing Run in their own browser.
    submissions = list(
        db.scalars(
            select(Submission)
            .where(
                Submission.user_id == user.id,
                Submission.run_mode == RunMode.SUBMIT,
            )
            .order_by(Submission.created_at)
        )
    )

    # Roll up in Python rather than with window functions. At ~30 exercises and a
    # few hundred submissions per student this is trivially fast, and it stays
    # readable for a team of three who are also writing exercises this week.
    by_exercise: dict[str, list[Submission]] = {}
    for submission in submissions:
        by_exercise.setdefault(submission.exercise_id, []).append(submission)

    # "In progress" starts the moment a lesson is OPENED, not just submitted.
    # Opening the editor creates an ExerciseSession, so a student who dips into a
    # lesson and leaves before finishing should see "in progress" -- which is
    # what they asked for. Tracking the latest activity per exercise also gives
    # a better "carry on where you left off" than submission time alone, since it
    # counts opening the lesson as activity.
    opened_at: dict[str, object] = {}
    for sess in db.scalars(
        select(ExerciseSession).where(ExerciseSession.user_id == user.id)
    ):
        prev = opened_at.get(sess.exercise_id)
        if prev is None or sess.last_activity_at > prev:  # type: ignore[operator]
            opened_at[sess.exercise_id] = sess.last_activity_at

    rows: list[ExerciseProgress] = []
    for exercise in exercises:
        attempts = by_exercise.get(exercise.id, [])
        solved = next((s for s in attempts if s.passed), None)
        opened = exercise.id in opened_at
        if solved is not None:
            status = "solved"
        elif attempts or opened:
            # Submitted-but-not-passed, or merely opened and left: both are work
            # in progress from the student's point of view.
            status = "in_progress"
        else:
            status = "not_started"

        rows.append(
            ExerciseProgress(
                id=exercise.id,
                slug=exercise.slug,
                title=exercise.title,
                concept=exercise.concept,
                theme=exercise.theme,
                variant=exercise.variant,
                status=status,
                attempts=len(attempts),
                last_attempt_at=attempts[-1].created_at if attempts else None,
            )
        )

    # Per-concept progress. Not mastery -- mastery is the weighted, hint-penalised
    # score in services/mastery.py and lands in Week 6. Calling this "mastery"
    # before that exists would be a claim the system can't back up.
    concept_totals: dict[str, list[int]] = {}
    for row in rows:
        counts = concept_totals.setdefault(row.concept.value, [0, 0])
        counts[1] += 1
        if row.status == "solved":
            counts[0] += 1

    concepts = [
        ConceptProgress(concept=name, solved=solved, total=total)
        for name, (solved, total) in sorted(concept_totals.items())
    ]

    # Where to send them next: the unsolved exercise they touched most recently,
    # otherwise the first one they haven't started. Picking up where you left off
    # beats making someone re-find their place in a list.
    #
    # Recency = latest activity, which for a session-only "in progress" exercise
    # comes from the session, and otherwise from the last submission. Some rows
    # have no submission timestamp, so `last_attempt_at` alone can't sort them.
    def recency(row: ExerciseProgress):
        return opened_at.get(row.id) or row.last_attempt_at

    in_progress = [r for r in rows if r.status == "in_progress" and recency(r)]
    in_progress.sort(key=recency, reverse=True)  # type: ignore[arg-type]
    if in_progress:
        continue_slug = in_progress[0].slug
    else:
        unstarted = [r for r in rows if r.status == "not_started"]
        continue_slug = unstarted[0].slug if unstarted else None

    # The student's AI-built branches, each tagged with the lesson it hangs off
    # so the dashboard can draw it below its parent. Status is already computed
    # per exercise in `rows`; branches reuse it rather than recomputing.
    slug_by_id = {ex.id: ex.slug for ex in exercises}
    status_by_id = {row.id: row.status for row in rows}
    branches = [
        BranchOut(
            parent_slug=slug_by_id[ex.parent_exercise_id],
            slug=ex.slug,
            title=ex.title,
            status=status_by_id[ex.id],
        )
        for ex in exercises
        if ex.created_by_user_id == user.id
        and ex.parent_exercise_id
        and ex.parent_exercise_id in slug_by_id
    ]

    return DashboardOut(
        recommended=_recommend(user.id, exercises, rows, continue_slug, db),
        display_name=user.display_name,
        role=user.role,
        solved=sum(1 for r in rows if r.status == "solved"),
        total_exercises=len(rows),
        total_attempts=len(submissions),
        concepts=concepts,
        continue_slug=continue_slug,
        exercises=rows,
        branches=branches,
    )
