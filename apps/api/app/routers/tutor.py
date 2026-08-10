"""The reflection tutor's HTTP surface.

Two endpoints, both authenticated:

  POST /tutor/chat     one turn of the friendly-teacher conversation.
  POST /tutor/lesson   build a verified practice exercise the student asked for.

The context the tutor is given is assembled HERE, from the exercise and the
student's own submissions -- never from their private journal, and never from
anything the browser sends beyond the visible conversation. See
services/tutor.py for the boundary and routers/reflections.py for the rule it
keeps intact.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import (
    LearnerIntake,
    ONBOARDING_EXPERIENCE,
    ONBOARDING_LEARN_STYLE,
    ONBOARDING_TIME,
    ONBOARDING_WORRIES,
    Exercise,
    LearnerProfile,
    OnboardingPlan,
    RunMode,
    Submission,
    TutorChatMessage,
)
from ..schemas import (
    GeneratedLessonResponse,
    GenerateLessonRequest,
    LessonProposal,
    TutorChatRequest,
    TutorChatResponse,
    TutorMessage,
)
from ..services import tutor

# How many past turns to feed the model. The whole conversation is persisted, but
# only the recent tail is sent each turn -- enough for continuity, bounded so a
# long chat doesn't grow the context (and the cost) without limit.
_HISTORY_WINDOW = 30

router = APIRouter(prefix="/tutor", tags=["tutor"])

DbSession = Annotated[Session, Depends(get_db)]

_OFF_MESSAGE = (
    "Your reflection tutor isn't switched on yet — an instructor needs to add an "
    "API key. When it's on, I'll talk you through how this exercise went and can "
    "build you extra practice. For now, jotting a note in your journal is a great "
    "way to lock in what you learned."
)


def _learner_brief(user_id: str, db: Session) -> tutor.LearnerBrief | None:
    """What this learner said about themselves at signup, for the tutor.

    None when they skipped the step or never had one, which the tutor treats as
    "say nothing about it" rather than "they told us nothing".

    The stored experience key is swapped for its human label here: the model
    should read "Comfortable in another language, new to Python", not
    "other_language".

    Also carries what the welcome conversation concluded, so an exercise built
    for this person months later can still be set in something they said they
    cared about at signup.
    """
    profile = db.get(LearnerProfile, user_id)
    if profile is None:
        return None
    plan = db.get(OnboardingPlan, user_id)
    intake = db.get(LearnerIntake, user_id)
    return tutor.LearnerBrief(
        goals=profile.goals,
        experience=ONBOARDING_EXPERIENCE.get(profile.experience, ""),
        experience_note=profile.experience_note,
        project_ideas=profile.project_ideas,
        interests=plan.interests if plan else "",
        suggested_projects=tuple(
            str(p.get("title", "")) for p in (plan.projects or []) if p.get("title")
        )
        if plan
        else (),
        # Labels, not keys. The model should be told "That I'm not a maths
        # person", never "maths".
        worries=tuple(
            ONBOARDING_WORRIES[key]
            for key in (intake.worries.split(",") if intake and intake.worries else [])
            if key in ONBOARDING_WORRIES
        ),
        time_available=ONBOARDING_TIME.get(intake.time_available, "") if intake else "",
        learn_style=ONBOARDING_LEARN_STYLE.get(intake.learn_style, "") if intake else "",
    )


def _build_context(user_id: str, exercise: Exercise, db: Session) -> tutor.TutorContext:
    """What the tutor is allowed to know -- from the student's OWN attempts only."""
    attempts = (
        db.scalar(
            select(func.count(Submission.id)).where(
                Submission.user_id == user_id,
                Submission.exercise_id == exercise.id,
                Submission.run_mode == RunMode.SUBMIT,
            )
        )
        or 0
    )
    solved = bool(
        db.scalar(
            select(Submission.id).where(
                Submission.user_id == user_id,
                Submission.exercise_id == exercise.id,
                Submission.run_mode == RunMode.SUBMIT,
                Submission.passed.is_(True),
            )
        )
    )
    # Their most recent work on this exercise. Run or Submit, whichever is
    # newest.
    latest = db.scalar(
        select(Submission)
        .where(
            Submission.user_id == user_id,
            Submission.exercise_id == exercise.id,
        )
        .order_by(Submission.created_at.desc())
    )
    last_summary = None
    if latest is not None:
        summary = (latest.test_results or {}).get("summary") or {}
        if summary:
            last_summary = (
                f"{summary.get('passed', 0)} of {summary.get('total', 0)} "
                "checks passing"
            )

    return tutor.TutorContext(
        learner=_learner_brief(user_id, db),
        title=exercise.title,
        concept=exercise.concept.value,
        prompt_md=exercise.prompt_md,
        entrypoint=exercise.entrypoint,
        latest_code=latest.code if latest is not None else None,
        solved=solved,
        attempts=attempts,
        last_summary=last_summary,
    )


def _saved_messages(user_id: str, exercise_id: str, db: Session) -> list[TutorChatMessage]:
    return list(
        db.scalars(
            select(TutorChatMessage)
            .where(
                TutorChatMessage.user_id == user_id,
                TutorChatMessage.exercise_id == exercise_id,
            )
            .order_by(TutorChatMessage.created_at, TutorChatMessage.id)
        )
    )


@router.get("/history", response_model=list[TutorMessage])
def history(exercise_id: str, user: CurrentUser, db: DbSession) -> list[TutorMessage]:
    """This student's saved conversation for one lesson, oldest first.

    Loaded when the Reflect page opens so the chat is exactly as they left it."""
    rows = _saved_messages(user.id, exercise_id, db)
    return [TutorMessage(role=row.role, content=row.content) for row in rows]


@router.post("/chat", response_model=TutorChatResponse)
def chat(
    body: TutorChatRequest, user: CurrentUser, db: DbSession
) -> TutorChatResponse:
    exercise = db.get(Exercise, body.exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if not tutor.enabled():
        # A complete UI on a switched-off tutor: friendly, honest, no 500. Nothing
        # is persisted -- there's no real conversation to save.
        return TutorChatResponse(reply=_OFF_MESSAGE, proposal=None, configured=False)

    # The prior conversation is the server's, reloaded from the DB each turn, so
    # the chat survives navigating away and back and the browser can't rewrite it.
    saved = _saved_messages(user.id, exercise.id, db)
    history = [{"role": m.role, "content": m.content} for m in saved[-_HISTORY_WINDOW:]]
    history.append({"role": "user", "content": body.message})

    context = _build_context(user.id, exercise, db)
    reply, proposal_data = tutor.chat(context, history)

    # Persist exactly what was shown -- the user's turn and the reply -- so a
    # return visit renders the conversation as it was left.
    db.add(
        TutorChatMessage(
            user_id=user.id, exercise_id=exercise.id, role="user", content=body.message
        )
    )
    db.add(
        TutorChatMessage(
            user_id=user.id, exercise_id=exercise.id, role="assistant", content=reply
        )
    )
    db.commit()

    proposal = LessonProposal(**proposal_data) if proposal_data else None
    return TutorChatResponse(reply=reply, proposal=proposal, configured=True)


@router.post("/chat/stream")
def chat_stream(body: TutorChatRequest, user: CurrentUser, db: DbSession):
    """The same turn as /tutor/chat, delivered as it is written.

    Newline-delimited JSON rather than Server-Sent Events, for one concrete
    reason: SSE in the browser means `EventSource`, which cannot set an
    `Authorization` header, and this API is bearer-token only (see auth.py on
    why there are no cookies). NDJSON over a plain POST works with `fetch`,
    carries the header, and needs no framing beyond a line break.

    Three line shapes, and every stream ends with exactly one of the last two:

        {"type": "text",  "value": "..."}    a fragment of the reply
        {"type": "done",  "reply": "...", "proposal": {...} | null}
        {"type": "error", "message": "..."}

    The turn is persisted here, on `done`, and not before -- the same rows the
    blocking endpoint writes. A stream the student navigated away from mid-reply
    therefore saves nothing, which is the right outcome: they never read it.
    """
    exercise = db.get(Exercise, body.exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if not tutor.enabled():
        def off():
            yield json.dumps({"type": "text", "value": _OFF_MESSAGE}) + "\n"
            yield json.dumps(
                {"type": "done", "reply": _OFF_MESSAGE, "proposal": None,
                 "configured": False}
            ) + "\n"

        return StreamingResponse(off(), media_type="application/x-ndjson")

    saved = _saved_messages(user.id, exercise.id, db)
    history = [{"role": m.role, "content": m.content} for m in saved[-_HISTORY_WINDOW:]]
    history.append({"role": "user", "content": body.message})
    context = _build_context(user.id, exercise, db)

    def emit():
        for kind, payload in tutor.chat_stream(context, history):
            if kind == "thinking":
                # A real signal, not a spinner: the model is reasoning before it
                # speaks, and saying so beats dots that look identical whether
                # it is thinking or the connection has died.
                yield json.dumps({"type": "thinking"}) + "\n"
            elif kind == "text":
                yield json.dumps({"type": "text", "value": payload}) + "\n"
            elif kind == "error":
                # Persist nothing. The student saw a apology, not an answer, and
                # replaying it as tutor speech on their next visit would be a
                # lie about what was said.
                yield json.dumps({"type": "error", "message": payload}) + "\n"
            else:
                db.add(
                    TutorChatMessage(
                        user_id=user.id,
                        exercise_id=exercise.id,
                        role="user",
                        content=body.message,
                    )
                )
                db.add(
                    TutorChatMessage(
                        user_id=user.id,
                        exercise_id=exercise.id,
                        role="assistant",
                        content=payload["reply"],
                    )
                )
                db.commit()
                yield json.dumps(
                    {
                        "type": "done",
                        "reply": payload["reply"],
                        "proposal": payload["proposal"],
                        "configured": True,
                    }
                ) + "\n"

    return StreamingResponse(emit(), media_type="application/x-ndjson")


@router.post("/lesson", response_model=GeneratedLessonResponse, status_code=201)
def generate_lesson(
    body: GenerateLessonRequest, user: CurrentUser, db: DbSession
) -> GeneratedLessonResponse:
    """Build, verify, and store a practice exercise the student accepted.

    The exercise is proven solvable through the real harness inside
    `generate_exercise` before it is committed, so a student who opens it can
    always finish it. If a sound one can't be produced, the student gets a gentle
    apology rather than a broken lesson.
    """
    if not tutor.enabled():
        raise HTTPException(status_code=503, detail=_OFF_MESSAGE)

    # The branch hangs off the lesson the student was on. Verify it exists and is
    # theirs to branch from (the curriculum, or their own earlier branch).
    parent = db.get(Exercise, body.parent_exercise_id)
    if parent is None or (
        parent.created_by_user_id is not None
        and parent.created_by_user_id != user.id
    ):
        raise HTTPException(status_code=404, detail="Parent lesson not found")

    try:
        spec = tutor.generate_exercise(
            body.concept.value,
            body.focus,
            body.title,
            created_by_user_id=user.id,
            parent_exercise_id=parent.id,
            # So a generated exercise can be set in something they said they
            # cared about. This is the project's central bet -- concrete,
            # engaging framing -- applied to the one exercise built for them
            # alone.
            learner=_learner_brief(user.id, db),
        )
    except tutor.GenerationError:
        raise HTTPException(
            status_code=502,
            detail=(
                "I couldn't put together a good exercise just now — that's on me, "
                "not you. Give it another go in a moment."
            ),
        ) from None

    exercise = Exercise(**spec)
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return GeneratedLessonResponse(slug=exercise.slug, title=exercise.title)
