import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.security_service import hash_password

USER_ENTITY_TYPE = "User"


class UserNotFoundError(ValueError):
    pass


class UserBusinessRuleError(ValueError):
    pass


def _user_snapshot(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
    }


def _require_non_blank(value: str, field_name: str) -> None:
    if not value.strip():
        raise UserBusinessRuleError(f"{field_name} must not be empty")


def create_user(
    db: Session,
    *,
    data: UserCreate,
    changed_by_user_id: uuid.UUID | None = None,
) -> User:
    _require_non_blank(data.email, "email")
    _require_non_blank(data.display_name, "display_name")

    existing_user = db.scalar(
        select(User).where(func.lower(User.email) == data.email.strip().lower())
    )
    if existing_user is not None:
        raise UserBusinessRuleError("A user with this email already exists")

    user = User(
        email=data.email.strip(),
        display_name=data.display_name.strip(),
        password_hash=hash_password(data.password) if data.password is not None else None,
        is_active=True,
    )
    db.add(user)
    db.flush()
    audit_service.log_entity_created(
        db,
        entity_type=USER_ENTITY_TYPE,
        entity_id=user.id,
        created_by_user_id=changed_by_user_id,
        new_value=_user_snapshot(user),
    )
    return user


def get_user(db: Session, *, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def list_users(db: Session, *, include_inactive: bool = False) -> list[User]:
    statement = select(User).order_by(User.display_name)
    if not include_inactive:
        statement = statement.where(User.is_active.is_(True))
    return list(db.scalars(statement).all())


def update_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    data: UserUpdate,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> User:
    user = get_user(db, user_id=user_id)
    if user is None:
        raise UserNotFoundError("User not found")

    update_data = data.model_dump(exclude_unset=True)
    password = update_data.pop("password", None)
    if "display_name" in update_data:
        if update_data["display_name"] is None:
            raise UserBusinessRuleError("display_name must not be empty")
        _require_non_blank(update_data["display_name"], "display_name")
        update_data["display_name"] = update_data["display_name"].strip()

    for field_name, new_value in update_data.items():
        old_value = getattr(user, field_name)
        if old_value == new_value:
            continue
        setattr(user, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=USER_ENTITY_TYPE,
            entity_id=user.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )

    if password is not None:
        user.password_hash = hash_password(password)
        audit_service.log_change(
            db,
            entity_type=USER_ENTITY_TYPE,
            entity_id=user.id,
            field_name="password",
            old_value=None,
            new_value="***UPDATED***",
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )

    db.add(user)
    db.flush()
    return user
