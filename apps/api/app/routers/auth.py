import random
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser, create_access_token, hash_password, verify_password
from ..db import get_db
from ..models import LearnerProfile, User
from ..services import demo
from ..schemas import (
    ConsentUpdate,
    DemoRequest,
    LearnerProfileIn,
    LearnerProfileOut,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: DbSession) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        # Counterbalancing is assigned once, here, and never recomputed.
        # Recomputing it later -- or assigning it at first exercise -- would let
        # dropout correlate with condition order and quietly bias the study.
        counterbalance_group=random.choice(["A", "B"]),
        # Stamped only on an explicit opt-in. Everyone gets the full platform
        # either way; consent governs analysis, not access.
        consented_at=_now() if body.consent_to_research else None,
    )
    db.add(user)
    db.commit()
    return TokenResponse(access_token=create_access_token(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email))
    # Same error for unknown email and wrong password: don't leak which emails
    # are enrolled in the study.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return TokenResponse(access_token=create_access_token(user))


#: Demo accounts are created by anyone who clicks a button on a public page, so
#: the endpoint is a free "make me a row" for whoever finds it. This is a floor,
#: not a security control -- it stops an accidental loop or a bored visitor, not
#: a determined one. Real rate limiting belongs at the edge, and /auth/login
#: needs it more (see the README's note on what is still missing).
_DEMO_LIMIT_PER_HOUR = 30
_demo_hits: list[datetime] = []


@router.post("/demo", response_model=TokenResponse, status_code=201)
def start_demo(body: DemoRequest, db: DbSession) -> TokenResponse:
    """Mint a throwaway account for the landing page's two demo buttons.

    A fresh one per click rather than a shared login, so two visitors can never
    see or undo each other's work. It is never study data: see services/demo.py
    for the three rules these accounts keep.
    """
    now = _now()
    _demo_hits[:] = [t for t in _demo_hits if now - t < timedelta(hours=1)]
    if len(_demo_hits) >= _DEMO_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "The demo is busy just now — try again shortly, or create a "
                "free account and keep what you make."
            ),
        )
    _demo_hits.append(now)

    user = demo.create_demo_user(db, with_progress=body.with_progress)
    return TokenResponse(access_token=create_access_token(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    # is_demo is derived from the address rather than stored, so it cannot drift
    # out of step with what the account actually is.
    return UserOut.model_validate(user, from_attributes=True).model_copy(
        update={"is_demo": demo.is_demo_email(user.email)}
    )


# --- the second step of signing up ------------------------------------------


def _profile_out(profile: LearnerProfile | None) -> LearnerProfileOut:
    if profile is None:
        return LearnerProfileOut(goals="", project_ideas="", completed=False)
    return LearnerProfileOut(
        goals=profile.goals,
        project_ideas=profile.project_ideas,
        completed=True,
    )


@router.get("/me/profile", response_model=LearnerProfileOut)
def get_profile(user: CurrentUser, db: DbSession) -> LearnerProfileOut:
    """The learner's own goals and project ideas, for their account page.

    Note what is missing: how much programming they said they had done. That is
    collected to pitch the tutor correctly, and is never read back -- see
    schemas.LearnerProfileOut. `completed` is what tells the web app whether a
    new account still needs the welcome step.
    """
    return _profile_out(db.get(LearnerProfile, user.id))


@router.patch("/me/profile", response_model=LearnerProfileOut)
def set_profile(
    body: LearnerProfileIn, user: CurrentUser, db: DbSession
) -> LearnerProfileOut:
    """Save the welcome step, or a later edit of part of it.

    PATCH, and only the fields actually sent are touched. The account page can
    edit goals and project ideas but cannot read the experience answer back, so
    a whole-row replace there would wipe it -- see LearnerProfileIn.

    Skipping is a legitimate answer. An empty submission still creates the row,
    which is what makes `completed` mean "we asked" rather than "they wrote
    something" -- otherwise anyone who skipped would be asked again on every
    single visit.
    """
    profile = db.get(LearnerProfile, user.id)
    if profile is None:
        profile = LearnerProfile(user_id=user.id)
        db.add(profile)

    if body.goals is not None:
        profile.goals = body.goals.strip()
    if body.experience is not None:
        profile.experience = body.experience
    if body.experience_note is not None:
        profile.experience_note = body.experience_note.strip()
    if body.project_ideas is not None:
        profile.project_ideas = body.project_ideas.strip()

    db.commit()
    db.refresh(profile)
    return _profile_out(profile)


@router.patch("/me/consent", response_model=UserOut)
def update_consent(body: ConsentUpdate, user: CurrentUser, db: DbSession) -> User:
    """Grant or withdraw study consent at any time.

    Withdrawal is a single toggle on the account page, deliberately. A right to
    withdraw that requires emailing a researcher is a right on paper only, and
    it is the participant protection an ethics committee will look for first.

    Withdrawing does NOT delete their work -- they keep their exercises, drafts
    and journal, and can carry on using the platform. It removes them from the
    analysis. That separation is the whole point: leaving the study should never
    cost someone the thing they came for.
    """
    now = _now()
    if body.consent_to_research:
        user.consented_at = now
        user.consent_withdrawn_at = None
    else:
        # Only record a withdrawal if there was consent to withdraw, so the
        # audit trail doesn't fill with no-ops from people who never opted in.
        if user.consented_at is not None:
            user.consent_withdrawn_at = now
        user.consented_at = None

    db.commit()
    db.refresh(user)
    return user
