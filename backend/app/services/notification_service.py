import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from app.models.enums import CommitteeMeetingStatus, RiskMonitoringStatus
from app.schemas.notification import (
    NotificationCategory,
    NotificationRead,
    NotificationSeverity,
    NotificationSummaryRead,
)
from app.services.committee_meeting_service import (
    CommitteeMeetingBusinessRuleError,
    list_committee_meetings,
)
from app.services.decision_queue_service import (
    DecisionQueueBusinessRuleError,
    get_my_decision_queue,
)
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    validate_active_user,
)
from app.services.risk_action_service import (
    RiskActionBusinessRuleError,
    get_my_risk_actions,
    get_risk_action_due_status,
    is_action_open_for_alerts,
)
from app.services.risk_monitoring_service import (
    RiskMonitoringReviewBusinessRuleError,
    get_my_monitoring_reviews,
)


class NotificationBusinessRuleError(ValueError):
    pass


def _build_summary(items: list[NotificationRead]) -> NotificationSummaryRead:
    return NotificationSummaryRead(
        total_count=len(items),
        critical_count=sum(
            1 for item in items if item.severity == NotificationSeverity.CRITICAL
        ),
        warning_count=sum(
            1 for item in items if item.severity == NotificationSeverity.WARNING
        ),
        info_count=sum(1 for item in items if item.severity == NotificationSeverity.INFO),
        action_count=sum(
            1 for item in items if item.category == NotificationCategory.ACTION
        ),
        monitoring_count=sum(
            1 for item in items if item.category == NotificationCategory.MONITORING
        ),
        decision_queue_count=sum(
            1 for item in items if item.category == NotificationCategory.DECISION_QUEUE
        ),
        meeting_count=sum(
            1 for item in items if item.category == NotificationCategory.MEETING
        ),
        items=items,
    )


def _created_timestamp(value: datetime | None) -> float:
    if value is None:
        return 0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _sort_notifications(items: list[NotificationRead]) -> list[NotificationRead]:
    severity_priority = {
        NotificationSeverity.CRITICAL: 0,
        NotificationSeverity.WARNING: 1,
        NotificationSeverity.INFO: 2,
    }
    category_priority = {
        NotificationCategory.ACTION: 0,
        NotificationCategory.MONITORING: 1,
        NotificationCategory.DECISION_QUEUE: 2,
        NotificationCategory.MEETING: 3,
    }
    return sorted(
        items,
        key=lambda item: (
            severity_priority[item.severity],
            item.due_date is None,
            item.due_date or date.max,
            -_created_timestamp(item.created_reference_at),
            category_priority[item.category],
            item.id,
        ),
    )


def _end_of_day(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.max)


def _action_notifications(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID,
) -> list[NotificationRead]:
    actions = get_my_risk_actions(
        db,
        requested_by_user_id=requested_by_user_id,
        include_completed=False,
        include_cancelled=False,
    )
    items: list[NotificationRead] = []
    for action in actions:
        if not is_action_open_for_alerts(action):
            continue
        due_status = get_risk_action_due_status(action)
        if due_status == "OVERDUE":
            severity = NotificationSeverity.CRITICAL
            title = "Overdue Action"
        elif due_status == "DUE_TODAY":
            severity = NotificationSeverity.WARNING
            title = "Action Due Today"
        elif due_status == "DUE_SOON":
            severity = NotificationSeverity.INFO
            title = "Action Due Soon"
        else:
            continue

        risk_record = action.risk_record
        items.append(
            NotificationRead(
                id=f"ACTION:{action.id}:{due_status}",
                category=NotificationCategory.ACTION,
                severity=severity,
                title=title,
                message=f"Risk action '{action.title}' is overdue."
                if due_status == "OVERDUE"
                else f"Risk action '{action.title}' needs attention.",
                target_type="RiskAction",
                target_id=action.id,
                risk_record_id=action.risk_record_id,
                risk_id=risk_record.risk_id if risk_record is not None else None,
                due_date=action.due_date,
                created_reference_at=action.created_at,
                action_url=f"/risks/{action.risk_record_id}",
            )
        )
    return items


def _monitoring_notifications(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID,
) -> list[NotificationRead]:
    reviews = get_my_monitoring_reviews(
        db,
        requested_by_user_id=requested_by_user_id,
        include_closed=False,
    )
    items: list[NotificationRead] = []
    for review in reviews:
        if not review.is_active:
            continue
        risk_record = review.risk_record
        risk_id = risk_record.risk_id if risk_record is not None else None
        if review.status == RiskMonitoringStatus.OVERDUE:
            severity = NotificationSeverity.CRITICAL
            title = "Monitoring Overdue"
            message = f"Monitoring review for risk {risk_id or review.risk_record_id} is overdue."
        elif review.status == RiskMonitoringStatus.DUE:
            severity = NotificationSeverity.WARNING
            title = "Monitoring Due"
            message = f"Monitoring review for risk {risk_id or review.risk_record_id} is due."
        else:
            continue

        items.append(
            NotificationRead(
                id=f"MONITORING:{review.id}:{review.status.value}",
                category=NotificationCategory.MONITORING,
                severity=severity,
                title=title,
                message=message,
                target_type="RiskMonitoringReview",
                target_id=review.id,
                risk_record_id=review.risk_record_id,
                risk_id=risk_id,
                due_date=review.next_review_date,
                created_reference_at=review.created_at,
                action_url=f"/risks/{review.risk_record_id}",
            )
        )
    return items


def _decision_queue_notifications(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID,
) -> list[NotificationRead]:
    decision_queue = get_my_decision_queue(
        db,
        requested_by_user_id=requested_by_user_id,
    )
    items: list[NotificationRead] = []
    for item in decision_queue.queue_items[:10]:
        risk = item.risk_record
        items.append(
            NotificationRead(
                id=f"DECISION_QUEUE:{item.committee_id}:{risk.id}",
                category=NotificationCategory.DECISION_QUEUE,
                severity=NotificationSeverity.WARNING,
                title="Committee Review Pending",
                message=f"Risk {risk.risk_id or risk.id} is awaiting committee review.",
                target_type="RiskRecord",
                target_id=risk.id,
                risk_record_id=risk.id,
                risk_id=risk.risk_id,
                committee_id=item.committee_id,
                committee_name=item.committee_name,
                created_reference_at=risk.updated_at or risk.created_at,
                action_url="/my-decisions",
            )
        )
    return items


def _meeting_notifications(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID,
) -> list[NotificationRead]:
    today = date.today()
    meetings = list_committee_meetings(
        db,
        requested_by_user_id=requested_by_user_id,
        status=CommitteeMeetingStatus.DRAFT,
    )
    items: list[NotificationRead] = []
    for meeting in meetings:
        if not meeting.is_active or meeting.meeting_date > today:
            continue
        severity = (
            NotificationSeverity.INFO
            if meeting.meeting_date == today
            else NotificationSeverity.WARNING
        )
        items.append(
            NotificationRead(
                id=f"MEETING:{meeting.id}:DRAFT",
                category=NotificationCategory.MEETING,
                severity=severity,
                title="Meeting Minutes Draft",
                message=f"Meeting minutes '{meeting.title}' are still in draft.",
                target_type="CommitteeMeeting",
                target_id=meeting.id,
                committee_id=meeting.committee_id,
                committee_name=meeting.committee_name,
                due_date=meeting.meeting_date,
                created_reference_at=_end_of_day(meeting.meeting_date)
                or meeting.created_at,
                action_url=f"/committee-meetings/{meeting.id}",
            )
        )
    return items


def get_my_notifications(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
    include_info: bool = True,
    limit: int = 50,
) -> NotificationSummaryRead:
    try:
        user = validate_active_user(
            db,
            user_id=requested_by_user_id,
            context="Notifications access",
        )
        items = [
            *_action_notifications(db, requested_by_user_id=user.id),
            *_monitoring_notifications(db, requested_by_user_id=user.id),
            *_decision_queue_notifications(db, requested_by_user_id=user.id),
            *_meeting_notifications(db, requested_by_user_id=user.id),
        ]
    except (
        RiskAccessBusinessRuleError,
        RiskActionBusinessRuleError,
        RiskMonitoringReviewBusinessRuleError,
        DecisionQueueBusinessRuleError,
        CommitteeMeetingBusinessRuleError,
    ) as exc:
        raise NotificationBusinessRuleError(str(exc)) from exc

    if not include_info:
        items = [item for item in items if item.severity != NotificationSeverity.INFO]

    limited_items = _sort_notifications(items)[: max(limit, 0)]
    return _build_summary(limited_items)
