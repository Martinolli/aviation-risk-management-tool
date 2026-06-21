import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.models.base import Base
from app.models.user import User
from app.services.auth_service import (
    AuthenticationError,
    TokenError,
    authenticate_user,
    create_access_token,
    decode_access_token,
)
from app.services.security_service import hash_password


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    Base.metadata.drop_all(engine)


def _user(
    db: Session,
    *,
    email: str = "admin@example.com",
    password: str | None = "StrongPassword123!",
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        display_name="Auth User",
        password_hash=hash_password(password) if password else None,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def test_authenticate_user_accepts_valid_case_insensitive_credentials(
    db_session: Session,
) -> None:
    user = _user(db_session)

    assert authenticate_user(
        db_session,
        email=" ADMIN@EXAMPLE.COM ",
        password="StrongPassword123!",
    ) is user


@pytest.mark.parametrize(
    "email,password",
    [
        ("", "StrongPassword123!"),
        ("admin@example.com", ""),
        ("unknown@example.com", "StrongPassword123!"),
        ("admin@example.com", "WrongPassword123!"),
    ],
)
def test_authenticate_user_rejects_invalid_credentials(
    db_session: Session,
    email: str,
    password: str,
) -> None:
    _user(db_session)

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        authenticate_user(db_session, email=email, password=password)


def test_authenticate_user_rejects_inactive_and_passwordless_users(
    db_session: Session,
) -> None:
    inactive_user = _user(db_session, email="inactive@example.com", is_active=False)
    passwordless_user = _user(db_session, email="passwordless@example.com", password=None)

    with pytest.raises(AuthenticationError, match="User is inactive"):
        authenticate_user(
            db_session, email=inactive_user.email, password="StrongPassword123!"
        )
    with pytest.raises(AuthenticationError, match="does not have password"):
        authenticate_user(
            db_session, email=passwordless_user.email, password="StrongPassword123!"
        )


def test_access_token_round_trip_and_invalid_payloads() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id)
    now = datetime.now(timezone.utc)
    wrong_type_token = jwt.encode(
        {"sub": str(user_id), "type": "refresh", "iat": now, "exp": now + timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    invalid_subject_token = jwt.encode(
        {"sub": "not-a-uuid", "type": "access", "iat": now, "exp": now + timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    assert decode_access_token(token) == user_id
    for invalid_token in ("malformed", wrong_type_token, invalid_subject_token):
        with pytest.raises(TokenError, match="Invalid or expired access token"):
            decode_access_token(invalid_token)


def test_expired_access_token_is_rejected() -> None:
    token = create_access_token(
        user_id=uuid.uuid4(), expires_delta=timedelta(seconds=-1)
    )

    with pytest.raises(TokenError, match="Invalid or expired access token"):
        decode_access_token(token)
