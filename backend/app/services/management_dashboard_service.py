import uuid
from collections import Counter
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import (
    AuthorityLevel,
    RiskActionStatus,
    RiskLifecycleStatus,
    RiskMonitoringStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAssessment, RiskRecord
from app.schemas.management_dashboard import (
    ManagementDashboardAttentionItem,
    ManagementDashboardGroup,
    ManagementDashboardKpi,
    ManagementDashboardRead,
    ManagementDashboardRiskSummary,
)
from app.services.decision_queue_service import (
    DecisionQueueBusinessRuleError,
    get_my_decision_queue,
)
from app.services.notification_service import (
    NotificationBusinessRuleError,
    get_my_notifications,
)
from app.services.risk_action_service import (
    RiskActionBusinessRuleError,
    get_my_risk_actions,
)
from app.services.risk_monitoring_service import (
    RiskMonitoringReviewBusinessRuleError,
    get_my_monitoring_reviews,
)
from app.services.risk_service import (
    RiskRecordBusinessRuleError,
    get_risk_submission_readiness,
    list_authorized_risk_records,
)


class ManagementDashboardBusinessRuleError(ValueError):
    pass


DEFAULT_HIGH_RISK_LEVELS = {"HIGH", "EXTREME", "CRITICAL", "INTOLERABLE"}
ESCALATED_WORKFLOW_STATUSES = {
    RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
    RiskWorkflowStatus.UNDER_RISK_MANAGEMENT_COMMITTEE_REVIEW,
    RiskWorkflowStatus.ESCALATED_TO_EXECUTIVE_COMMITTEE,
    RiskWorkflowStatus.UNDER_EXECUTIVE_COMMITTEE_REVIEW,
}
MIDDLE_WORKFLOW_STATUSES = {
    RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
    RiskWorkflowStatus.UNDER_RISK_MANAGEMENT_COMMITTEE_REVIEW,
}
HIGH_WORKFLOW_STATUSES = {
    RiskWorkflowStatus.ESCALATED_TO_EXECUTIVE_COMMITTEE,
    RiskWorkflowStatus.UNDER_EXECUTIVE_COMMITTEE_REVIEW,
}
LOW_WORKFLOW_STATUSES = {
    RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
    RiskWorkflowStatus.UNDER_OPERATIONAL_BOARD_REVIEW,
}


def _is_open_risk(risk: RiskRecord) -> bool:
    return (
        risk.is_active
        and risk.lifecycle_status != RiskLifecycleStatus.CLOSED
        and risk.workflow_status != RiskWorkflowStatus.CLOSED
    )


def _latest_assessments(
    db: Session,
    *,
    risk_ids: set[uuid.UUID],
) -> dict[uuid.UUID, RiskAssessment]:
    if not risk_ids:
        return {}
    assessments = list(
        db.scalars(
            select(RiskAssessment)
            .where(RiskAssessment.risk_record_id.in_(risk_ids))
            .order_by(
                RiskAssessment.risk_record_id.asc(),
                RiskAssessment.assessed_at.desc(),
                RiskAssessment.created_at.desc(),
            )
        ).all()
    )
    latest: dict[uuid.UUID, RiskAssessment] = {}
    for assessment in assessments:
        latest.setdefault(assessment.risk_record_id, assessment)
    return latest


def _risk_summary(
    risk: RiskRecord,
    *,
    latest_assessment: RiskAssessment | None,
) -> ManagementDashboardRiskSummary:
    board = risk.board_of_origin
    return ManagementDashboardRiskSummary(
        risk_record_id=risk.id,
        risk_id=risk.risk_id,
        problem_description=risk.problem_description,
        domain=risk.domain.value,
        workflow_status=risk.workflow_status.value,
        lifecycle_status=risk.lifecycle_status.value,
        latest_risk_level=latest_assessment.risk_level if latest_assessment else None,
        board_of_origin_id=risk.board_of_origin_id,
        board_of_origin_name=board.name if board is not None else None,
        owner_user_id=risk.owner_user_id,
        updated_at=risk.updated_at,
    )


def _risk_level_key(value: str | None) -> str:
    return value.strip().upper() if value and value.strip() else "NOT_ASSESSED"


def _risk_level_label(value: str | None) -> str:
    return value.strip() if value and value.strip() else "Not assessed"


def _high_risk_level_set(high_risk_levels: list[str] | None) -> set[str]:
    levels = high_risk_levels or list(DEFAULT_HIGH_RISK_LEVELS)
    return {level.strip().upper() for level in levels if level.strip()}


def _is_high_exposure(
    latest_assessment: RiskAssessment | None,
    *,
    high_risk_levels: set[str],
) -> bool:
    if latest_assessment is None:
        return False
    return latest_assessment.risk_level.strip().upper() in high_risk_levels


def _group_counter(counter: Counter[str], labels: dict[str, str] | None = None) -> list[ManagementDashboardGroup]:
    labels = labels or {}
    return [
        ManagementDashboardGroup(
            key=key,
            label=labels.get(key, key),
            count=count,
        )
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _authority_level_for_risk(risk: RiskRecord) -> str:
    if risk.workflow_status in HIGH_WORKFLOW_STATUSES:
        return AuthorityLevel.HIGH.value
    if risk.workflow_status in MIDDLE_WORKFLOW_STATUSES:
        return AuthorityLevel.MIDDLE.value
    if risk.workflow_status in LOW_WORKFLOW_STATUSES:
        return AuthorityLevel.LOW.value
    if risk.board_of_origin is not None and risk.board_of_origin.authority_level is not None:
        return risk.board_of_origin.authority_level.value
    return "NOT_ASSIGNED"


def _risk_timestamp(risk: RiskRecord) -> float:
    value = risk.updated_at or risk.created_at
    if value is None:
        return 0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _assessment_timestamp(assessment: RiskAssessment | None) -> float:
    if assessment is None:
        return 0
    value = assessment.assessed_at or assessment.created_at
    if value is None:
        return 0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _risk_level_priority(level: str | None) -> int:
    if level is None:
        return 99
    priority = {
        "INTOLERABLE": 0,
        "EXTREME": 1,
        "CRITICAL": 2,
        "HIGH": 3,
    }
    return priority.get(level.strip().upper(), 50)


def _unique_risks_by_urgency(risks: list[RiskRecord]) -> list[RiskRecord]:
    seen: set[uuid.UUID] = set()
    unique: list[RiskRecord] = []
    for risk in risks:
        if risk.id in seen:
            continue
        seen.add(risk.id)
        unique.append(risk)
    return sorted(unique, key=lambda risk: -_risk_timestamp(risk))


def _top_attention_items(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID,
) -> list[ManagementDashboardAttentionItem]:
    notifications = get_my_notifications(
        db,
        requested_by_user_id=requested_by_user_id,
        include_info=False,
        limit=10,
    )
    return [
        ManagementDashboardAttentionItem(
            category=notification.category.value,
            severity=notification.severity.value,
            title=notification.title,
            message=notification.message,
            target_type=notification.target_type,
            target_id=notification.target_id,
            risk_record_id=notification.risk_record_id,
            risk_id=notification.risk_id,
            action_url=notification.action_url,
            due_date=notification.due_date,
        )
        for notification in notifications.items
    ]


def _count_draft_package_backlog(db: Session, *, risks: list[RiskRecord]) -> int:
    return sum(
        1
        for risk in risks
        if risk.workflow_status == RiskWorkflowStatus.DRAFT
        and not get_risk_submission_readiness(db, risk_record=risk)["is_ready"]
    )


def get_management_dashboard(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
    high_risk_levels: list[str] | None = None,
    limit: int = 10,
) -> ManagementDashboardRead:
    try:
        readable_risks = list_authorized_risk_records(
            db,
            requested_by_user_id=requested_by_user_id,
            include_archived=False,
        )
        requested_user_id = requested_by_user_id
        if requested_user_id is None:
            raise ManagementDashboardBusinessRuleError(
                "Management Dashboard access requires an authenticated active user"
            )
        actions = get_my_risk_actions(
            db,
            requested_by_user_id=requested_user_id,
            include_completed=False,
            include_cancelled=False,
        )
        monitoring_reviews = get_my_monitoring_reviews(
            db,
            requested_by_user_id=requested_user_id,
            include_closed=False,
        )
        decision_queue = get_my_decision_queue(
            db,
            requested_by_user_id=requested_user_id,
        )
        attention_items = _top_attention_items(
            db,
            requested_by_user_id=requested_user_id,
        )
    except (
        RiskRecordBusinessRuleError,
        RiskActionBusinessRuleError,
        RiskMonitoringReviewBusinessRuleError,
        DecisionQueueBusinessRuleError,
        NotificationBusinessRuleError,
    ) as exc:
        raise ManagementDashboardBusinessRuleError(str(exc)) from exc

    open_risks = [risk for risk in readable_risks if _is_open_risk(risk)]
    readable_risk_by_id = {risk.id: risk for risk in readable_risks}
    open_risk_ids = {risk.id for risk in open_risks}
    latest = _latest_assessments(db, risk_ids={risk.id for risk in readable_risks})
    high_levels = _high_risk_level_set(high_risk_levels)
    limited = max(limit, 0)

    high_exposure_risks = [
        risk
        for risk in open_risks
        if _is_high_exposure(latest.get(risk.id), high_risk_levels=high_levels)
    ]
    high_exposure_risks.sort(
        key=lambda risk: (
            _risk_level_priority(latest[risk.id].risk_level),
            -_assessment_timestamp(latest.get(risk.id)),
            -_risk_timestamp(risk),
        )
    )

    overdue_actions = [
        action
        for action in actions
        if action.risk_record_id in open_risk_ids
        and action.status in {RiskActionStatus.OPEN, RiskActionStatus.IN_PROGRESS}
        and action.due_date is not None
        and action.due_date < date.today()
    ]
    overdue_action_risks = _unique_risks_by_urgency(
        [
            action.risk_record
            for action in overdue_actions
            if action.risk_record is not None
        ]
    )

    monitoring_concerns = [
        review
        for review in monitoring_reviews
        if review.risk_record_id in open_risk_ids
        and review.is_active
        and review.status in {RiskMonitoringStatus.DUE, RiskMonitoringStatus.OVERDUE}
    ]
    monitoring_concern_risks = _unique_risks_by_urgency(
        [
            review.risk_record
            for review in monitoring_concerns
            if review.risk_record is not None
        ]
    )

    committee_backlog_map: dict[uuid.UUID, RiskRecord] = {}
    for item in decision_queue.queue_items:
        risk = readable_risk_by_id.get(item.risk_record.id)
        if risk is not None and risk.id in open_risk_ids:
            committee_backlog_map.setdefault(risk.id, risk)
    committee_backlog_risks = sorted(
        committee_backlog_map.values(),
        key=lambda risk: -_risk_timestamp(risk),
    )

    assessed_distribution = Counter(
        _risk_level_key(latest.get(risk.id).risk_level if latest.get(risk.id) else None)
        for risk in open_risks
    )
    risk_level_labels = {
        _risk_level_key(latest.get(risk.id).risk_level if latest.get(risk.id) else None): _risk_level_label(
            latest.get(risk.id).risk_level if latest.get(risk.id) else None
        )
        for risk in open_risks
    }
    domain_counter = Counter(risk.domain.value for risk in open_risks)
    workflow_counter = Counter(risk.workflow_status.value for risk in open_risks)
    authority_counter = Counter(_authority_level_for_risk(risk) for risk in open_risks)
    authority_labels = {
        AuthorityLevel.LOW.value: "LOW",
        AuthorityLevel.MIDDLE.value: "MIDDLE",
        AuthorityLevel.HIGH.value: "HIGH",
        "NOT_ASSIGNED": "Not assigned",
    }

    summary_for = lambda risk: _risk_summary(  # noqa: E731
        risk,
        latest_assessment=latest.get(risk.id),
    )

    kpis = [
        ManagementDashboardKpi(
            key="total_open_risks",
            label="Total open risks",
            value=len(open_risks),
            detail="Readable risks not closed",
        ),
        ManagementDashboardKpi(
            key="high_risk_exposure",
            label="High Risk Exposure",
            value=len(high_exposure_risks),
            detail="Latest assessment in configured high risk levels",
            severity="CRITICAL" if high_exposure_risks else None,
        ),
        ManagementDashboardKpi(
            key="escalated_risks",
            label="Escalated risks",
            value=sum(risk.workflow_status in ESCALATED_WORKFLOW_STATUSES for risk in open_risks),
            detail="RMC or executive workflow statuses",
            severity="WARNING",
        ),
        ManagementDashboardKpi(
            key="accepted_monitoring",
            label="Accepted / monitoring",
            value=sum(
                risk.workflow_status == RiskWorkflowStatus.ACCEPTED
                or risk.lifecycle_status == RiskLifecycleStatus.MONITORING
                for risk in open_risks
            ),
            detail="Accepted risks or lifecycle monitoring",
        ),
        ManagementDashboardKpi(
            key="overdue_actions",
            label="Overdue Actions",
            value=len(overdue_actions),
            detail="Open or in-progress controls past due",
            severity="CRITICAL" if overdue_actions else None,
        ),
        ManagementDashboardKpi(
            key="monitoring_concerns",
            label="Monitoring Concerns",
            value=len(monitoring_concerns),
            detail="Due or overdue active monitoring reviews",
            severity="WARNING" if monitoring_concerns else None,
        ),
        ManagementDashboardKpi(
            key="committee_backlog",
            label="Committee Backlog",
            value=len(committee_backlog_risks),
            detail="Risks awaiting committee review",
            severity="WARNING" if committee_backlog_risks else None,
        ),
        ManagementDashboardKpi(
            key="draft_package_backlog",
            label="Draft package backlog",
            value=_count_draft_package_backlog(db, risks=open_risks),
            detail="Draft risks missing package readiness or initial assessment",
        ),
    ]

    return ManagementDashboardRead(
        generated_at=datetime.now(timezone.utc),
        kpis=kpis,
        risk_level_distribution=_group_counter(assessed_distribution, risk_level_labels),
        domain_hotspots=_group_counter(domain_counter)[:8],
        workflow_backlog=_group_counter(workflow_counter),
        authority_level_backlog=_group_counter(authority_counter, authority_labels),
        top_attention_items=attention_items,
        high_exposure_risks=[summary_for(risk) for risk in high_exposure_risks[:limited]],
        overdue_action_risks=[
            summary_for(risk) for risk in overdue_action_risks[:limited]
        ],
        monitoring_concern_risks=[
            summary_for(risk) for risk in monitoring_concern_risks[:limited]
        ],
        committee_backlog_risks=[
            summary_for(risk) for risk in committee_backlog_risks[:limited]
        ],
    )
