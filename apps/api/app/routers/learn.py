"""The Plan stage: lessons, quizzes, and Parsons problems.

Sits between choosing a project (Connect) and writing code (Create). A novice
dropped straight into an empty editor has to invent the structure and the syntax
at the same time; this stage separates those.

Answer keys never leave the server. `correct_index` is stripped from every quiz
response, and the Parsons solution order is only ever compared server-side. A
student who opens devtools should find no answers there -- otherwise the warm-up
becomes a memory test.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import (
    Exercise,
    Lesson,
    LessonProgress,
    ParsonsAttempt,
    ParsonsProblem,
    QuizQuestion,
)
from ..schemas import (
    LessonOut,
    ParsonsCheckRequest,
    ParsonsCheckResponse,
    ParsonsOut,
    QuizGradeRequest,
    QuizGradeResponse,
    QuizQuestionOut,
    QuizResult,
)

router = APIRouter(prefix="/learn", tags=["learn"])

DbSession = Annotated[Session, Depends(get_db)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _shuffled_lines(problem: ParsonsProblem, seed: str) -> list[str]:
    """Present the lines out of order, deterministically per (problem, user).

    Deterministic so the puzzle doesn't rearrange itself under someone who
    refreshes mid-thought -- which reads as a bug and loses their reasoning.
    Seeded by user so two students don't compare identical screens.
    """
    items = list(problem.lines) + list(problem.distractors or [])
    # A tiny stable hash. Not security, just a repeatable shuffle without
    # importing random and worrying about global state.
    def key(item: str) -> int:
        h = 0
        for char in f"{seed}:{item}":
            h = (h * 31 + ord(char)) & 0xFFFFFFFF
        return h

    return sorted(items, key=key)


@router.get("/lessons/{concept}", response_model=LessonOut | None)
def lesson_for_concept(
    concept: str, user: CurrentUser, db: DbSession
) -> LessonOut | None:
    """The lesson for a concept, with its quiz -- answers stripped.

    Null when no lesson has been written yet. The Plan stage degrades to
    "straight to the editor" rather than blocking, so unwritten content never
    stops someone working.
    """
    lesson = db.scalar(
        select(Lesson).where(Lesson.concept == concept).order_by(Lesson.order_index)
    )
    if lesson is None:
        return None

    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson.id
        )
    )

    questions = sorted(lesson.questions, key=lambda q: q.order_index)
    return LessonOut(
        id=lesson.id,
        slug=lesson.slug,
        title=lesson.title,
        concept=lesson.concept,
        body_md=lesson.body_md,
        # No correct_index, no explanation. Both arrive only after answering.
        questions=[
            QuizQuestionOut(id=q.id, prompt=q.prompt, options=q.options)
            for q in questions
        ],
        completed=progress is not None and progress.completed_at is not None,
    )


@router.post("/lessons/{lesson_id}/quiz", response_model=QuizGradeResponse)
def grade_quiz(
    lesson_id: str, body: QuizGradeRequest, user: CurrentUser, db: DbSession
) -> QuizGradeResponse:
    """Grade the quiz and hand back explanations.

    Explanations come back for right answers too. Someone who guessed correctly
    has learned nothing yet, and telling them why it's right is the cheapest
    teaching moment in the whole flow.

    The quiz is not a gate. You can get everything wrong and still go and write
    the code -- this is a warm-up, not an exam.
    """
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    questions = {q.id: q for q in lesson.questions}
    results: list[QuizResult] = []

    for answer in body.answers:
        question = questions.get(answer.question_id)
        if question is None:
            continue
        correct = answer.chosen_index == question.correct_index
        results.append(
            QuizResult(
                question_id=question.id,
                correct=correct,
                correct_index=question.correct_index,
                explanation=question.explanation,
            )
        )

    correct_count = sum(1 for r in results if r.correct)

    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson.id
        )
    )
    if progress is None:
        progress = LessonProgress(user_id=user.id, lesson_id=lesson.id)
        db.add(progress)

    progress.quiz_correct = correct_count
    progress.quiz_total = len(results)
    # Completed means "worked through it", not "scored well". Gating progress on
    # a quiz score would turn a warm-up into an exam and punish the students who
    # most need the practice.
    progress.completed_at = _now()

    db.commit()

    return QuizGradeResponse(
        correct=correct_count, total=len(results), results=results
    )


@router.get("/parsons/{slug}", response_model=ParsonsOut | None)
def parsons_for_exercise(
    slug: str, user: CurrentUser, db: DbSession
) -> ParsonsOut | None:
    """The Parsons warm-up for an exercise, lines shuffled, answer withheld."""
    exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    problem = db.scalar(
        select(ParsonsProblem).where(ParsonsProblem.exercise_id == exercise.id)
    )
    if problem is None:
        return None

    return ParsonsOut(
        id=problem.id,
        prompt=problem.prompt,
        shuffled_lines=_shuffled_lines(problem, seed=user.id),
    )


@router.post("/parsons/{problem_id}/check", response_model=ParsonsCheckResponse)
def check_parsons(
    problem_id: str, body: ParsonsCheckRequest, user: CurrentUser, db: DbSession
) -> ParsonsCheckResponse:
    """Check an ordering.

    Returns how many lines from the start are right, not which ones are wrong.
    That's deliberate: "the first three are correct" tells you where to think
    without handing over the arrangement, which is the same restraint the hint
    ladder shows.
    """
    problem = db.get(ParsonsProblem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    expected = list(problem.lines)
    correct = body.ordering == expected

    prefix = 0
    for got, want in zip(body.ordering, expected):
        if got != want:
            break
        prefix += 1

    db.add(
        ParsonsAttempt(user_id=user.id, problem_id=problem.id, correct=correct)
    )
    db.commit()

    return ParsonsCheckResponse(
        correct=correct,
        correct_prefix=prefix,
        total_lines=len(expected),
    )
