from hashlib import sha256
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _user_from_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            raise JWTError()
        user_id = int(subject)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return _user_from_token(token, db)


def get_current_or_guest_user(
    authorization: Annotated[str | None, Header()] = None,
    guest_session: Annotated[str | None, Header(alias="X-Guest-Session")] = None,
    db: Session = Depends(get_db),
) -> User:
    if authorization and authorization.lower().startswith("bearer "):
        return _user_from_token(authorization.split(" ", 1)[1].strip(), db)

    if not guest_session or len(guest_session.strip()) < 16:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Guest session is required")

    digest = sha256(f"{settings.secret_key}:{guest_session.strip()}".encode("utf-8")).hexdigest()
    email = f"guest-{digest[:24]}@guest.local"
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        return user

    user = User(
        email=email,
        password_hash=f"guest:{digest}",
        display_name=f"游客 {digest[:12]}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
