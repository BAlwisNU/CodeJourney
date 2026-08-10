"""Step three of signing up: a chat about what you'd like to build.

The conversation is saved turn by turn, so closing the tab halfway through
doesn't lose it. What the model concludes is saved separately in
`onboarding_plans` -- see the note on that model for why the learner's own words
and a machine's paraphrase of them are kept apart.

Nothing here is required. The whole step can be skipped, and if no
ANTHROPIC_API_KEY is set it is skipped automatically, because a signup flow must
not dead-end on a missing API key.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser
from ..db import get_db
from ..models import (
    LearnerIntake,
    ONBOARDING_EXPERIENCE,
    ONBOARDING_LEARN_STYLE,
    ONBOARDING_TIME,
    ONBOARDING_WORRIES,
    Concept,
    LearnerProfile,
    OnboardingMessage,
    OnboardingPlan,
)
from ..services import tutor

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

DbSession = Annotated[Session, Depends(get_db)]

#: Enough back-and-forth to arrive at a plan, and a ceiling so a long
#: conversation cannot grow the prompt without limit.
_MAX_TURNS = 40


class ChatMessage(BaseModel):
    role: str
    content: str


class ProjectIdea(BaseModel):
    title: str
    blurb: str
    topics: list[str] = Field(default_factory=list)


class PlanOut(BaseModel):
    interests: str = ""
    topics: list[str] = Field(default_factory=list)
    projects: list[ProjectIdea] = Field(default_factory=list)
    #: False until the model has recorded anything.
    recorded: bool = False


class WelcomeState(BaseModel):
    """Everything the chat page needs to render itself."""

    #: False when the tutor has no API key. The page then offers to skip rather
    #: than showing a chat box that cannot answer.
    available: bool
    greeting: str
    messages: list[ChatMessage]
    plan: PlanOut


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatOut(BaseModel):
    reply: str
    plan: PlanOut


def _plan_out(plan: OnboardingPlan | None) -> PlanOut:
    if plan is None:
        return PlanOut()
    return PlanOut(
        interests=plan.interests,
        topics=list(plan.topics or []),
        projects=[ProjectIdea(**p) for p in (plan.projects or [])],
        recorded=True,
    )


def _history(user_id: str, db: Session) -> list[OnboardingMessage]:
    return list(
        db.scalars(
            select(OnboardingMessage)
            .where(OnboardingMessage.user_id == user_id)
            .order_by(OnboardingMessage.created_at, OnboardingMessage.id)
        )
    )


def _brief(user_id: str, db: Session) -> tutor.LearnerBrief | None:
    """The step-two answers, so the chat doesn't ask what was just answered."""
    profile = db.get(LearnerProfile, user_id)
    if profile is None:
        return None
    intake = db.get(LearnerIntake, user_id)
    return tutor.LearnerBrief(
        goals=profile.goals,
        experience=ONBOARDING_EXPERIENCE.get(profile.experience, ""),
        experience_note=profile.experience_note,
        project_ideas=profile.project_ideas,
        # Labels, not keys -- the model should never be shown "maths".
        worries=tuple(
            ONBOARDING_WORRIES[key]
            for key in (intake.worries.split(",") if intake and intake.worries else [])
            if key in ONBOARDING_WORRIES
        ),
        time_available=ONBOARDING_TIME.get(intake.time_available, "") if intake else "",
        learn_style=ONBOARDING_LEARN_STYLE.get(intake.learn_style, "") if intake else "",
    )


@router.get("/welcome", response_model=WelcomeState)
def welcome_state(user: CurrentUser, db: DbSession) -> WelcomeState:
    return WelcomeState(
        available=tutor.enabled(),
        greeting=tutor.WELCOME_GREETING,
        messages=[
            ChatMessage(role=m.role, content=m.content) for m in _history(user.id, db)
        ],
        plan=_plan_out(db.get(OnboardingPlan, user.id)),
    )


@router.post("/welcome/chat", response_model=ChatOut)
def welcome_chat(body: ChatIn, user: CurrentUser, db: DbSession) -> ChatOut:
    if not tutor.enabled():
        raise HTTPException(
            status_code=503,
            detail="The welcome chat isn't set up on this server.",
        )

    history = _history(user.id, db)
    if len(history) >= _MAX_TURNS:
        raise HTTPException(
            status_code=409,
            detail=(
                "That's a good long chat — let's get you started. You can "
                "always talk more with the tutor inside a lesson."
            ),
        )

    said = body.message.strip()
    db.add(OnboardingMessage(user_id=user.id, role="user", content=said))
    db.flush()

    turns = [{"role": m.role, "content": m.content} for m in history]
    turns.append({"role": "user", "content": said})

    reply, recorded = tutor.welcome_chat(_brief(user.id, db), turns)

    db.add(OnboardingMessage(user_id=user.id, role="assistant", content=reply))

    plan = _record(user.id, recorded, db)
    db.commit()
    return ChatOut(reply=reply, plan=_plan_out(plan))


_CONCEPT_KEYS = {c.value for c in Concept}


def _record_profile(user_id: str, recorded: dict, db: Session) -> None:
    """Write the answers the signup form used to collect.

    Same two rows it always wrote -- LearnerProfile and LearnerIntake -- so
    everything downstream that reads them (the coach's LearnerBrief, the
    account page, exercise generation) works unchanged and cannot tell whether
    a form or a conversation produced them.

    Only fields the model actually reported are touched. A later turn that
    omits something must not blank what an earlier turn heard.
    """
    profile = db.get(LearnerProfile, user_id)
    if profile is None:
        profile = LearnerProfile(user_id=user_id)
        db.add(profile)

    goals = str(recorded.get("goals") or "").strip()
    if goals:
        profile.goals = goals[:2000]
    experience = str(recorded.get("experience") or "")
    if experience in ONBOARDING_EXPERIENCE:
        profile.experience = experience
    # `interests` is the model's summary of the person, which is the closest
    # thing the conversation produces to the form's "what would you build".
    ideas = str(recorded.get("interests") or "").strip()
    if ideas and not profile.project_ideas:
        profile.project_ideas = ideas[:2000]

    intake = db.get(LearnerIntake, user_id)
    if intake is None:
        intake = LearnerIntake(user_id=user_id)
        db.add(intake)

    learn_style = str(recorded.get("learn_style") or "")
    if learn_style in ONBOARDING_LEARN_STYLE:
        intake.learn_style = learn_style
    time_available = str(recorded.get("time_available") or "")
    if time_available in ONBOARDING_TIME:
        intake.time_available = time_available
    worries = [w for w in (recorded.get("worries") or []) if w in ONBOARDING_WORRIES]
    if worries:
        intake.worries = ",".join(worries)


def _record(user_id: str, recorded: dict | None, db: Session) -> OnboardingPlan | None:
    """Persist what the model concluded, filtered down to what is real.

    The tool schema constrains topics to the Concept enum, but a model can still
    return something outside it, and an unknown topic key renders as a dead link
    on the account page. Shared by both the blocking and streaming turns so the
    two cannot filter differently.
    """
    plan = db.get(OnboardingPlan, user_id)
    if recorded is None:
        return plan
    if plan is None:
        plan = OnboardingPlan(user_id=user_id)
        db.add(plan)

    # The conversation replaced the form, so what the form used to write is
    # written from here. Each field is set only when the model actually heard
    # it: a chat is not obliged to extract all six, and overwriting a real
    # answer from turn two with a blank on turn five would lose it.
    _record_profile(user_id, recorded, db)
    plan.interests = str(recorded.get("interests") or "").strip()
    plan.topics = [
        key for key in (recorded.get("topics") or []) if key in _CONCEPT_KEYS
    ]
    plan.projects = [
        {
            "title": str(item.get("title") or "").strip()[:120],
            "blurb": str(item.get("blurb") or "").strip()[:400],
            "topics": [
                key for key in (item.get("topics") or []) if key in _CONCEPT_KEYS
            ],
        }
        for item in (recorded.get("projects") or [])
        if item.get("title")
    ][:4]
    return plan


@router.post("/welcome/chat/stream")
def welcome_chat_stream(body: ChatIn, user: CurrentUser, db: DbSession):
    """One turn of the signup conversation, streamed.

    Newline-delimited JSON, matching /tutor/chat/stream -- see that endpoint for
    why not Server-Sent Events. Line shapes:

        {"type": "text", "value": "..."}
        {"type": "done", "reply": "...", "plan": {...}}
        {"type": "error", "message": "..."}

    Streaming matters more here than anywhere else in the product. This sits in
    the middle of signing up, and several seconds of nothing moving is the
    moment a new person decides the thing is broken and closes the tab.
    """
    if not tutor.enabled():
        raise HTTPException(
            status_code=503, detail="The welcome chat isn't set up on this server."
        )

    history = _history(user.id, db)
    if len(history) >= _MAX_TURNS:
        raise HTTPException(
            status_code=409,
            detail=(
                "That's a good long chat — let's get you started. You can "
                "always talk more with the tutor inside a lesson."
            ),
        )

    said = body.message.strip()
    turns = [{"role": m.role, "content": m.content} for m in history]
    turns.append({"role": "user", "content": said})
    brief = _brief(user.id, db)

    def emit():
        for kind, payload in tutor.welcome_chat_stream(brief, turns):
            if kind == "thinking":
                # A real signal, not a spinner: the model is reasoning before it
                # speaks, and saying so beats dots that look identical whether
                # it is thinking or the connection has died.
                yield json.dumps({"type": "thinking"}) + "\n"
            elif kind == "text":
                yield json.dumps({"type": "text", "value": payload}) + "\n"
            elif kind == "error":
                # Nothing is written. Their turn is not saved either, so the
                # retry is a clean retry rather than a duplicate.
                yield json.dumps({"type": "error", "message": payload}) + "\n"
            else:
                db.add(OnboardingMessage(user_id=user.id, role="user", content=said))
                db.add(
                    OnboardingMessage(
                        user_id=user.id, role="assistant", content=payload["reply"]
                    )
                )
                plan = _record(user.id, payload["plan"], db)
                db.commit()
                yield json.dumps(
                    {
                        "type": "done",
                        "reply": payload["reply"],
                        "plan": _plan_out(plan).model_dump(),
                    }
                ) + "\n"

    return StreamingResponse(emit(), media_type="application/x-ndjson")


@router.get("/plan", response_model=PlanOut)
def get_plan(user: CurrentUser, db: DbSession) -> PlanOut:
    """The plan, for the account page. Theirs to read whenever they like."""
    return _plan_out(db.get(OnboardingPlan, user.id))
