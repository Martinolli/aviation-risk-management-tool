from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_optional_current_user
from app.models.user import User
from app.schemas.data_retention_policy import DataRetentionPolicyRead
from app.services.data_retention_policy_service import get_data_retention_policy

router = APIRouter(
    prefix="/data-retention-policy",
    tags=["data-retention-policy"],
)


@router.get("", response_model=DataRetentionPolicyRead)
def get_data_retention_policy_endpoint(
    current_user: User | None = Depends(get_optional_current_user),
):
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return get_data_retention_policy()
