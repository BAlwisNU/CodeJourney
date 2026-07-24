import random
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser, create_access_token, hash_password, verify_password
from ..db import get_db
from ..models import User
from ..schemas import (
    ConsentUpdate,
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


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


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
