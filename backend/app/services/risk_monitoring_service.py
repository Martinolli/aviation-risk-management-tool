import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

import app.services.audit_service as audit_service
from app.models.enums import (
    RiskLifecycleStatus,
    RiskMonitoringReviewOutcome,
    RiskMonitoringStatus,
)
from app.models.risk import RiskMonitoringReview, RiskRecord
from app.models.user import User
from app.schemas.risk_monitoring import (
    RiskMonitoringReviewClose,
    RiskMonitoringReviewComplete,
    RiskMonitoringReviewCreate,
    RiskMonitoringReviewUpdate,
)
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    can_read_risk_record,
    validate_active_user,
)

RISK_MONITORING_ENTITY_TYPE = "RiskMonitoringReview"
RISK_RECORD_ENTITY_TYPE = "RiskRecord"


class RiskMonitoringReviewNotFoundError(ValueError):
    pass


class RiskMonitoringReviewBusinessRuleError(ValueError):
    pass


def _validate_actor(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    context: str,
) -> User:
    try:
        return validate_active_user(db, user_id=user_id, context=context)
    except RiskAccessBusinessRuleError as exc:
        raise RiskMonitoringReviewBusinessRuleError(str(exc)) from exc


def _get_risk_record(db: Session, risk_record_id: uuid.UUID) -> RiskRecord:
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        raise RiskMonitoringReviewNotFoundError("Risk record not found")
    return risk_record


def _get_monitoring_review(
    db: Session, monitoring_review_id: uuid.UUID
) -> RiskMonitoringReview:
    monitoring_review = db.get(RiskMonitoringReview, monitoring_review_id)
    if monitoring_review is None:
        raise RiskMonitoringReviewNotFoundError("Monitoring review not found")
    return monitoring_review


def _authorize(
    db: Session,
    *,
    risk_record: RiskRecord,
    user_id: uuid.UUID,
    operation: str,
) -> None:
    if not can_read_risk_record(db, risk_record=risk_record, user_id=user_id):
        raise RiskMonitoringReviewBusinessRuleError(
            f"User is not authorized to {operation} monitoring for this risk"
        )


def _status_for_review_date(next_review_date: date | None) -> RiskMonitoringStatus:
    if next_review_date is None or next_review_date > date.today():
        return RiskMonitoringStatus.ACTIVE
    if next_review_date == date.today():
        return RiskMonitoringStatus.DUE
    return RiskMonitoringStatus.OVERDUE


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _audit_changed_fields(
    db: Session,
    *,
    monitoring_review: RiskMonitoringReview,
    old_values: dict[str, Any],
    changed_by_user_id: uuid.UUID,
) -> None:
    for field_name, old_value in old_values.items():
        new_value = getattr(monitoring_review, field_name)
        if old_value != new_value:
            audit_service.log_change(
                db,
                entity_type=RISK_MONITORING_ENTITY_TYPE,
                entity_id=monitoring_review.id,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                changed_by_user_id=changed_by_user_id,
            )


def list_risk_monitoring_reviews(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
    include_inactive: bool = False,
) -> list[RiskMonitoringReview]:
    reader = _validate_actor(
        db,
        user_id=requested_by_user_id,
        context="Monitoring list access",
    )
    risk_record = _get_risk_record(db, risk_record_id)
    _authorize(
        db,
        risk_record=risk_record,
        user_id=reader.id,
        operation="list",
    )

    active_statuses = (
        RiskMonitoringStatus.ACTIVE,
        RiskMonitoringStatus.DUE,
        RiskMonitoringStatus.OVERDUE,
    )
    statement = select(RiskMonitoringReview).where(
        RiskMonitoringReview.risk_record_id == risk_record.id
    )
    if not include_inactive:
        statement = statement.where(RiskMonitoringReview.is_active.is_(True))
    statement = statement.order_by(
        case((RiskMonitoringReview.status.in_(active_statuses), 0), else_=1),
        case((RiskMonitoringReview.next_review_date.is_(None), 1), else_=0),
        RiskMonitoringReview.next_review_date.asc(),
        RiskMonitoringReview.created_at.desc(),
    )
    return list(db.scalars(statement).all())


def get_my_monitoring_reviews(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
    include_closed: bool = False,
) -> list[RiskMonitoringReview]:
    reader = _validate_actor(
        db,
        user_id=requested_by_user_id,
        context="My Monitoring access",
    )
    statement = (
        select(RiskMonitoringReview)
        .options(selectinload(RiskMonitoringReview.risk_record))
        .where(RiskMonitoringReview.is_active.is_(True))
        .order_by(RiskMonitoringReview.created_at.desc())
    )
    if not include_closed:
        statement = statement.where(
            RiskMonitoringReview.status.not_in(
                (RiskMonitoringStatus.CLOSED, RiskMonitoringStatus.CANCELLED)
            )
        )

    readable_reviews = [
        review
        for review in db.scalars(statement).all()
        if can_read_risk_record(
            db,
            risk_record=review.risk_record,
            user_id=reader.id,
        )
    ]
    status_priority = {
        RiskMonitoringStatus.OVERDUE: 0,
        RiskMonitoringStatus.DUE: 1,
        RiskMonitoringStatus.ACTIVE: 2,
        RiskMonitoringStatus.CLOSED: 3,
        RiskMonitoringStatus.CANCELLED: 4,
    }
    return sorted(
        readable_reviews,
        key=lambda review: (
            status_priority[review.status],
            review.next_review_date is None,
            review.next_review_date or date.max,
        ),
    )


def create_risk_monitoring_review(
    db: Session,
    *,
    data: RiskMonitoringReviewCreate,
    created_by_user_id: uuid.UUID | None,
) -> RiskMonitoringReview:
    creator = _validate_actor(
        db,
        user_id=created_by_user_id,
        context="Monitoring creation",
    )
    risk_record = _get_risk_record(db, data.risk_record_id)
    _authorize(
        db,
        risk_record=risk_record,
        user_id=creator.id,
        operation="create",
    )
    if not risk_record.is_active:
        raise RiskMonitoringReviewBusinessRuleError(
            "Monitoring cannot be created for an inactive risk record"
        )

    monitoring_review = RiskMonitoringReview(
        risk_record_id=risk_record.id,
        monitoring_owner_user_id=data.monitoring_owner_user_id,
        review_frequency=_normalize_text(data.review_frequency),
        next_review_date=data.next_review_date,
        status=_status_for_review_date(data.next_review_date),
        review_notes=_normalize_text(data.review_notes),
        effectiveness_review=_normalize_text(data.effectiveness_review),
        created_by_user_id=creator.id,
        is_active=True,
    )
    db.add(monitoring_review)
    db.flush()
    audit_service.log_entity_created(
        db,
        entity_type=RISK_MONITORING_ENTITY_TYPE,
        entity_id=monitoring_review.id,
        created_by_user_id=creator.id,
        new_value={
            "risk_record_id": risk_record.id,
            "monitoring_owner_user_id": monitoring_review.monitoring_owner_user_id,
            "review_frequency": monitoring_review.review_frequency,
            "next_review_date": monitoring_review.next_review_date,
            "status": monitoring_review.status,
            "review_notes": monitoring_review.review_notes,
            "effectiveness_review": monitoring_review.effectiveness_review,
        },
    )

    if risk_record.lifecycle_status != RiskLifecycleStatus.CLOSED:
        old_status = risk_record.lifecycle_status
        if old_status != RiskLifecycleStatus.MONITORING:
            risk_record.lifecycle_status = RiskLifecycleStatus.MONITORING
            db.flush()
            audit_service.log_change(
                db,
                entity_type=RISK_RECORD_ENTITY_TYPE,
                entity_id=risk_record.id,
                field_name="lifecycle_status",
                old_value=old_status,
                new_value=RiskLifecycleStatus.MONITORING,
                changed_by_user_id=creator.id,
                reason="Monitoring review cycle created",
            )

    return monitoring_review


def update_risk_monitoring_review(
    db: Session,
    *,
    monitoring_review_id: uuid.UUID,
    data: RiskMonitoringReviewUpdate,
    changed_by_user_id: uuid.UUID | None,
) -> RiskMonitoringReview:
    actor = _validate_actor(
        db,
        user_id=changed_by_user_id,
        context="Monitoring update",
    )
    monitoring_review = _get_monitoring_review(db, monitoring_review_id)
    risk_record = _get_risk_record(db, monitoring_review.risk_record_id)
    _authorize(
        db,
        risk_record=risk_record,
        user_id=actor.id,
        operation="update",
    )

    updates = data.model_dump(exclude_unset=True)
    editable_fields = {
        "monitoring_owner_user_id",
        "review_frequency",
        "next_review_date",
        "status",
        "review_notes",
        "effectiveness_review",
        "review_outcome",
    }
    old_values = {
        field_name: getattr(monitoring_review, field_name)
        for field_name in editable_fields
    }
    for field_name, value in updates.items():
        if field_name in {"review_frequency", "review_notes", "effectiveness_review"}:
            value = _normalize_text(value)
        setattr(monitoring_review, field_name, value)
    if (
        "status" not in updates
        and monitoring_review.status
        not in {RiskMonitoringStatus.CLOSED, RiskMonitoringStatus.CANCELLED}
    ):
        monitoring_review.status = _status_for_review_date(
            monitoring_review.next_review_date
        )

    db.flush()
    _audit_changed_fields(
        db,
        monitoring_review=monitoring_review,
        old_values=old_values,
        changed_by_user_id=actor.id,
    )
    return monitoring_review


def complete_risk_monitoring_review(
    db: Session,
    *,
    monitoring_review_id: uuid.UUID,
    data: RiskMonitoringReviewComplete,
    reviewed_by_user_id: uuid.UUID | None,
) -> RiskMonitoringReview:
    reviewer = _validate_actor(
        db,
        user_id=reviewed_by_user_id,
        context="Effectiveness review completion",
    )
    monitoring_review = _get_monitoring_review(db, monitoring_review_id)
    risk_record = _get_risk_record(db, monitoring_review.risk_record_id)
    _authorize(
        db,
        risk_record=risk_record,
        user_id=reviewer.id,
        operation="complete",
    )
    if monitoring_review.status in {
        RiskMonitoringStatus.CLOSED,
        RiskMonitoringStatus.CANCELLED,
    }:
        raise RiskMonitoringReviewBusinessRuleError(
            "Closed or cancelled monitoring cannot be completed"
        )

    tracked_fields = (
        "effectiveness_review",
        "review_outcome",
        "review_notes",
        "last_reviewed_at",
        "reviewed_by_user_id",
        "next_review_date",
        "status",
        "closed_at",
        "closed_by_user_id",
    )
    old_values = {
        field_name: getattr(monitoring_review, field_name)
        for field_name in tracked_fields
    }
    now = datetime.now(timezone.utc)
    monitoring_review.effectiveness_review = _normalize_text(
        data.effectiveness_review
    )
    if monitoring_review.effectiveness_review is None:
        raise RiskMonitoringReviewBusinessRuleError(
            "Effectiveness Review is required"
        )
    monitoring_review.review_outcome = data.review_outcome
    if "review_notes" in data.model_fields_set:
        monitoring_review.review_notes = _normalize_text(data.review_notes)
    monitoring_review.last_reviewed_at = now
    monitoring_review.reviewed_by_user_id = reviewer.id
    monitoring_review.next_review_date = data.next_review_date

    if data.review_outcome == RiskMonitoringReviewOutcome.CLOSE_MONITORING:
        monitoring_review.status = RiskMonitoringStatus.CLOSED
        monitoring_review.closed_at = now
        monitoring_review.closed_by_user_id = reviewer.id
    else:
        monitoring_review.status = _status_for_review_date(data.next_review_date)

    db.flush()
    _audit_changed_fields(
        db,
        monitoring_review=monitoring_review,
        old_values=old_values,
        changed_by_user_id=reviewer.id,
    )
    return monitoring_review


def close_risk_monitoring_review(
    db: Session,
    *,
    monitoring_review_id: uuid.UUID,
    data: RiskMonitoringReviewClose,
    closed_by_user_id: uuid.UUID | None,
) -> RiskMonitoringReview:
    actor = _validate_actor(
        db,
        user_id=closed_by_user_id,
        context="Monitoring closure",
    )
    monitoring_review = _get_monitoring_review(db, monitoring_review_id)
    risk_record = _get_risk_record(db, monitoring_review.risk_record_id)
    _authorize(
        db,
        risk_record=risk_record,
        user_id=actor.id,
        operation="close",
    )
    if monitoring_review.status == RiskMonitoringStatus.CLOSED:
        raise RiskMonitoringReviewBusinessRuleError("Monitoring is already closed")

    tracked_fields = ("status", "closed_at", "closed_by_user_id", "closure_reason")
    old_values = {
        field_name: getattr(monitoring_review, field_name)
        for field_name in tracked_fields
    }
    monitoring_review.status = RiskMonitoringStatus.CLOSED
    monitoring_review.closed_at = datetime.now(timezone.utc)
    monitoring_review.closed_by_user_id = actor.id
    monitoring_review.closure_reason = _normalize_text(data.closure_reason)
    db.flush()
    _audit_changed_fields(
        db,
        monitoring_review=monitoring_review,
        old_values=old_values,
        changed_by_user_id=actor.id,
    )
    return monitoring_review
