import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate
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
def create_role_endpoint(data: RoleCreate, db: Session = Depends(get_db)):
    try:
        return _commit_and_refresh(
            db,
            create_role(db, data=data, changed_by_user_id=None),
        )
    except RoleBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.patch("/{role_id}", response_model=RoleRead)
def update_role_endpoint(
    role_id: uuid.UUID,
    data: RoleUpdate,
    db: Session = Depends(get_db),
):
    try:
        return _commit_and_refresh(
            db,
            update_role(
                db,
                role_id=role_id,
                data=data,
                changed_by_user_id=None,
            ),
        )
    except RoleNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except RoleBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
