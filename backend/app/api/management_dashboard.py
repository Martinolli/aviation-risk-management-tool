from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.management_dashboard import ManagementDashboardRead
from app.services.management_dashboard_service import (
    ManagementDashboardBusinessRuleError,
    get_management_dashboard,
)

router = APIRouter(prefix="/management-dashboard", tags=["management-dashboard"])


@router.get("", response_model=ManagementDashboardRead)
def get_management_dashboard_endpoint(
    limit: int = 10,
    high_risk_levels: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return get_management_dashboard(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
            high_risk_levels=high_risk_levels,
            limit=limit,
        )
    except ManagementDashboardBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
