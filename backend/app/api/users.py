import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.admin_authorization_service import (
    AdminAuthorizationBusinessRuleError,
    validate_admin_actor,
)
from app.services.user_service import (
    UserBusinessRuleError,
    UserNotFoundError,
    create_user,
    get_user,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["users"])


def _commit_and_refresh(db: Session, user: User) -> User:
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead])
def list_users_endpoint(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    return list_users(db, include_inactive=include_inactive)


@router.get("/{user_id}", response_model=UserRead)
def get_user_endpoint(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        validate_admin_actor(
            db, user_id=get_optional_current_user_id(current_user)
        )
        return _commit_and_refresh(
            db,
            create_user(
                db,
                data=data,
                changed_by_user_id=get_optional_current_user_id(current_user),
            ),
        )
    except (AdminAuthorizationBusinessRuleError, UserBusinessRuleError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.patch("/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        validate_admin_actor(
            db, user_id=get_optional_current_user_id(current_user)
        )
        return _commit_and_refresh(
            db,
            update_user(
                db,
                user_id=user_id,
                data=data,
                changed_by_user_id=get_optional_current_user_id(current_user),
            ),
        )
    except UserNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (AdminAuthorizationBusinessRuleError, UserBusinessRuleError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
