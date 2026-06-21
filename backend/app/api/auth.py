from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import (
    AuthenticationError,
    authenticate_user,
    create_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login_endpoint(data: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, email=data.email, password=data.password)
    except AuthenticationError as exc:
        status_code = (
            status.HTTP_403_FORBIDDEN
            if str(exc) == "User is inactive"
            else status.HTTP_401_UNAUTHORIZED
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return TokenResponse(
        access_token=create_access_token(user_id=user.id),
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=user,
    )
