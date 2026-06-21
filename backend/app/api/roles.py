import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate
from app.services.admin_authorization_service import (
    AdminAuthorizationBusinessRuleError,
    validate_admin_actor,
)
from app.services.role_service import (
    RoleBusinessRuleError,
    RoleNotFoundError,
    create_role,
    get_role,
    list_roles,
    update_role,
)

router = APIRouter(prefix="/roles", tags=["roles"])


def _commit_and_refresh(db: Session, role: Role) -> Role:
    db.commit()
    db.refresh(role)
    return role


@router.get("", response_model=list[RoleRead])
def list_roles_endpoint(db: Session = Depends(get_db)):
    return list_roles(db)


@router.get("/{role_id}", response_model=RoleRead)
def get_role_endpoint(role_id: uuid.UUID, db: Session = Depends(get_db)):
    role = get_role(db, role_id=role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role_endpoint(
    data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        validate_admin_actor(
            db, user_id=get_optional_current_user_id(current_user)
        )
        return _commit_and_refresh(
            db,
            create_role(
                db,
                data=data,
                changed_by_user_id=get_optional_current_user_id(current_user),
            ),
        )
    except (AdminAuthorizationBusinessRuleError, RoleBusinessRuleError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.patch("/{role_id}", response_model=RoleRead)
def update_role_endpoint(
    role_id: uuid.UUID,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        validate_admin_actor(
            db, user_id=get_optional_current_user_id(current_user)
        )
        return _commit_and_refresh(
            db,
            update_role(
                db,
                role_id=role_id,
                data=data,
                changed_by_user_id=get_optional_current_user_id(current_user),
            ),
        )
    except RoleNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (AdminAuthorizationBusinessRuleError, RoleBusinessRuleError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
