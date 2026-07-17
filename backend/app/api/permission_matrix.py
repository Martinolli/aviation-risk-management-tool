from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_optional_current_user
from app.models.user import User
from app.schemas.permission_matrix import PermissionMatrixRead
from app.services.permission_matrix_service import get_permission_matrix

router = APIRouter(prefix="/permission-matrix", tags=["permission-matrix"])


@router.get("", response_model=PermissionMatrixRead)
def get_permission_matrix_endpoint(
    current_user: User | None = Depends(get_optional_current_user),
):
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return get_permission_matrix()
