"""Authentication and role-based access.

Bearer tokens rather than session cookies. This is the concession the Expo
companion needs: a native client has no cookie jar and no same-site story, so a
cookie-based session would force a second auth path in Week 5. Tokens cost
nothing extra now and make the companion a ~4-day job instead of a rewrite.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Role, User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


"""Marker stored in `password_hash` for accounts that have no password.

Someone who signs up with "Continue with Google" never chooses one. The column
is NOT NULL and this project has no migration tool yet, so relaxing it would
break every existing database -- storing a value that cannot be a bcrypt hash
achieves the same thing with no schema change. Django's `set_unusable_password`
does exactly this, for the same reason.

The safety of it rests entirely on `verify_password` below refusing anything
that isn't a real bcrypt hash. A bcrypt hash always begins "$2"; this begins
"!", so no password can ever verify against it.
"""
UNUSABLE_PASSWORD = "!oauth-only-no-password-set"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    # Guard before passlib rather than after: handed a non-bcrypt string it
    # raises UnknownHashError, which would surface as a 500 on the login route
    # instead of the "invalid credentials" this is asking about. An
    # OAuth-only account must fail password login as a plain wrong password.
    if not hashed or not hashed.startswith("$"):
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        # Malformed or unknown hash. Treated as "does not match", never as an
        # error the caller has to handle.
        return False


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[ALGORITHM]
        )
    except jwt.PyJWTError:
        raise unauthorized from None

    user = db.get(User, payload.get("sub"))
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_instructor(user: CurrentUser) -> User:
    if user.role is not Role.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor role required",
        )
    return user


Instructor = Annotated[User, Depends(require_instructor)]
