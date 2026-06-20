import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate

ROLE_ENTITY_TYPE = "Role"


class RoleNotFoundError(ValueError):
    pass


class RoleBusinessRuleError(ValueError):
    pass


def _role_snapshot(role: Role) -> dict[str, object]:
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_active": role.is_active,
    }


def create_role(
    db: Session,
    *,
    data: RoleCreate,
    changed_by_user_id: uuid.UUID | None = None,
) -> Role:
    if not data.name.strip():
        raise RoleBusinessRuleError("name must not be empty")

    existing_role = db.scalar(
        select(Role).where(func.lower(Role.name) == data.name.strip().lower())
    )
    if existing_role is not None:
        raise RoleBusinessRuleError("A role with this name already exists")

    role = Role(
        name=data.name.strip(),
        description=data.description,
        is_active=True,
    )
    db.add(role)
    db.flush()
    audit_service.log_entity_created(
        db,
        entity_type=ROLE_ENTITY_TYPE,
        entity_id=role.id,
        created_by_user_id=changed_by_user_id,
        new_value=_role_snapshot(role),
    )
    return role


def get_role(db: Session, *, role_id: uuid.UUID) -> Role | None:
    return db.get(Role, role_id)


def list_roles(db: Session) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.name)).all())


def update_role(
    db: Session,
    *,
    role_id: uuid.UUID,
    data: RoleUpdate,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> Role:
    role = get_role(db, role_id=role_id)
    if role is None:
        raise RoleNotFoundError("Role not found")

    for field_name, new_value in data.model_dump(exclude_unset=True).items():
        old_value = getattr(role, field_name)
        if old_value == new_value:
            continue
        setattr(role, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=ROLE_ENTITY_TYPE,
            entity_id=role.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )

    db.add(role)
    db.flush()
    return role
