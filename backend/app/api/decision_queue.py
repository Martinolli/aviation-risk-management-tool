from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.decision_queue import MyDecisionQueueRead
from app.services.decision_queue_service import (
    DecisionQueueBusinessRuleError,
    get_my_decision_queue,
)

router = APIRouter(prefix="/decision-queue", tags=["decision-queue"])


@router.get("/my", response_model=MyDecisionQueueRead)
def get_my_decision_queue_endpoint(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return get_my_decision_queue(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
        )
    except DecisionQueueBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
