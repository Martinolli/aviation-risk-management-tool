from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationSummaryRead
from app.services.notification_service import (
    NotificationBusinessRuleError,
    get_my_notifications,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/my", response_model=NotificationSummaryRead)
def get_my_notifications_endpoint(
    include_info: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return get_my_notifications(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
            include_info=include_info,
            limit=limit,
        )
    except NotificationBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
