import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.services.security_service import verify_password


class AuthenticationError(ValueError):
    pass


class TokenError(ValueError):
    pass


def authenticate_user(
    db: Session,
    *,
    email: str,
    password: str,
) -> User:
    normalized_email = email.strip().lower()
    if not normalized_email or not password or not password.strip():
        raise AuthenticationError("Invalid email or password")

    user = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    if user is None:
        raise AuthenticationError("Invalid email or password")
    if not user.is_active:
        raise AuthenticationError("User is inactive")
    if not user.password_hash or not user.password_hash.strip():
        raise AuthenticationError("User does not have password authentication configured")
    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")
    return user


def create_access_token(
    *,
    user_id: uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at, "iat": now, "type": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
        if payload.get("type") != "access":
            raise TokenError("Invalid or expired access token")
        subject = payload.get("sub")
        if not subject:
            raise TokenError("Invalid or expired access token")
        return uuid.UUID(subject)
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        raise TokenError("Invalid or expired access token") from exc
