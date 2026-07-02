import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.risk import RiskMonitoringReview
from app.models.user import User
from app.schemas.risk_monitoring import (
    RiskMonitoringReviewClose,
    RiskMonitoringReviewComplete,
    RiskMonitoringReviewCreate,
    RiskMonitoringReviewRead,
    RiskMonitoringReviewUpdate,
)
from app.services.risk_monitoring_service import (
    RiskMonitoringReviewBusinessRuleError,
    RiskMonitoringReviewNotFoundError,
    close_risk_monitoring_review,
    complete_risk_monitoring_review,
    create_risk_monitoring_review,
    get_my_monitoring_reviews,
    list_risk_monitoring_reviews,
    update_risk_monitoring_review,
)

router = APIRouter(prefix="/risk-monitoring", tags=["risk-monitoring"])


def _commit_and_refresh(
    db: Session, monitoring_review: RiskMonitoringReview
) -> RiskMonitoringReview:
    db.commit()
    db.refresh(monitoring_review)
    return monitoring_review


def _not_found(exc: RiskMonitoringReviewNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _business_rule(exc: RiskMonitoringReviewBusinessRuleError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/my", response_model=list[RiskMonitoringReviewRead])
def get_my_monitoring_reviews_endpoint(
    include_closed: bool = False,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return get_my_monitoring_reviews(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
            include_closed=include_closed,
        )
    except RiskMonitoringReviewBusinessRuleError as exc:
        raise _business_rule(exc) from exc


@router.get(
    "/risk/{risk_record_id}", response_model=list[RiskMonitoringReviewRead]
)
def list_risk_monitoring_reviews_endpoint(
    risk_record_id: uuid.UUID,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return list_risk_monitoring_reviews(
            db,
            risk_record_id=risk_record_id,
            requested_by_user_id=get_optional_current_user_id(current_user),
            include_inactive=include_inactive,
        )
    except RiskMonitoringReviewNotFoundError as exc:
        raise _not_found(exc) from exc
    except RiskMonitoringReviewBusinessRuleError as exc:
        raise _business_rule(exc) from exc


@router.post(
    "",
    response_model=RiskMonitoringReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def create_risk_monitoring_review_endpoint(
    data: RiskMonitoringReviewCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        review = create_risk_monitoring_review(
            db,
            data=data,
            created_by_user_id=get_optional_current_user_id(current_user),
        )
        return _commit_and_refresh(db, review)
    except RiskMonitoringReviewNotFoundError as exc:
        db.rollback()
        raise _not_found(exc) from exc
    except RiskMonitoringReviewBusinessRuleError as exc:
        db.rollback()
        raise _business_rule(exc) from exc


@router.patch("/{monitoring_review_id}", response_model=RiskMonitoringReviewRead)
def update_risk_monitoring_review_endpoint(
    monitoring_review_id: uuid.UUID,
    data: RiskMonitoringReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        review = update_risk_monitoring_review(
            db,
            monitoring_review_id=monitoring_review_id,
            data=data,
            changed_by_user_id=get_optional_current_user_id(current_user),
        )
        return _commit_and_refresh(db, review)
    except RiskMonitoringReviewNotFoundError as exc:
        db.rollback()
        raise _not_found(exc) from exc
    except RiskMonitoringReviewBusinessRuleError as exc:
        db.rollback()
        raise _business_rule(exc) from exc


@router.post(
    "/{monitoring_review_id}/complete", response_model=RiskMonitoringReviewRead
)
def complete_risk_monitoring_review_endpoint(
    monitoring_review_id: uuid.UUID,
    data: RiskMonitoringReviewComplete,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        review = complete_risk_monitoring_review(
            db,
            monitoring_review_id=monitoring_review_id,
            data=data,
            reviewed_by_user_id=get_optional_current_user_id(current_user),
        )
        return _commit_and_refresh(db, review)
    except RiskMonitoringReviewNotFoundError as exc:
        db.rollback()
        raise _not_found(exc) from exc
    except RiskMonitoringReviewBusinessRuleError as exc:
        db.rollback()
        raise _business_rule(exc) from exc


@router.post(
    "/{monitoring_review_id}/close", response_model=RiskMonitoringReviewRead
)
def close_risk_monitoring_review_endpoint(
    monitoring_review_id: uuid.UUID,
    data: RiskMonitoringReviewClose,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        review = close_risk_monitoring_review(
            db,
            monitoring_review_id=monitoring_review_id,
            data=data,
            closed_by_user_id=get_optional_current_user_id(current_user),
        )
        return _commit_and_refresh(db, review)
    except RiskMonitoringReviewNotFoundError as exc:
        db.rollback()
        raise _not_found(exc) from exc
    except RiskMonitoringReviewBusinessRuleError as exc:
        db.rollback()
        raise _business_rule(exc) from exc
