import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel, RiskWorkflowStatus
from app.models.risk import RiskRecord
from app.schemas.decision_queue import (
    MyDecisionQueueCommitteeRead,
    MyDecisionQueueItemRead,
    MyDecisionQueueRead,
)
from app.schemas.risk import RiskRecordRead
from app.services.risk_access_service import validate_active_user

AIRCRAFT_COMMITTEE = "Aircraft Safety Committee - Engineering Board"
FLIGHT_TEST_COMMITTEE = "Flight Test Safety Committee - Operation"
INDUSTRIAL_COMMITTEE = (
    "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE"
)

LOW_QUEUE_STATUSES = {
    RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
    RiskWorkflowStatus.UNDER_OPERATIONAL_BOARD_REVIEW,
}
MIDDLE_QUEUE_STATUSES = {
    RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
    RiskWorkflowStatus.UNDER_RISK_MANAGEMENT_COMMITTEE_REVIEW,
}
HIGH_QUEUE_STATUSES = {
    RiskWorkflowStatus.ESCALATED_TO_EXECUTIVE_COMMITTEE,
    RiskWorkflowStatus.UNDER_EXECUTIVE_COMMITTEE_REVIEW,
}

LOW_COMMITTEE_SCOPES: dict[str, list[str]] = {
    AIRCRAFT_COMMITTEE: ["ENGINEERING", "CONTINUED_AIRWORTHINESS"],
    FLIGHT_TEST_COMMITTEE: ["FLIGHT_TEST"],
    INDUSTRIAL_COMMITTEE: [
        "QUALITY",
        "MANUFACTURING",
        "PRODUCTION",
        "SUPPLY_CHAIN",
        "OHSE",
        "MAINTENANCE",
        "SUPPLIER_INTERFACE",
    ],
}


class DecisionQueueBusinessRuleError(ValueError):
    pass


def _queue_scope(committee: Committee) -> str | list[str]:
    if committee.authority_level == AuthorityLevel.LOW:
        return LOW_COMMITTEE_SCOPES.get(committee.name, "Board of Origin risks")
    if committee.authority_level == AuthorityLevel.MIDDLE:
        return "Escalated RMC risks"
    return "Escalated executive risks"


def _queue_reason(authority_level: AuthorityLevel) -> str:
    if authority_level == AuthorityLevel.LOW:
        return "Risk is awaiting Board of Origin decision"
    if authority_level == AuthorityLevel.MIDDLE:
        return "Risk is escalated to Risk Management Committee"
    return "Risk is escalated to Executive Safety Management Committee"


def _queue_risks_for_committee(
    db: Session,
    *,
    committee: Committee,
) -> list[RiskRecord]:
    statement = select(RiskRecord).where(RiskRecord.is_active.is_(True))

    if committee.authority_level == AuthorityLevel.LOW:
        statement = statement.where(
            RiskRecord.board_of_origin_id == committee.id,
            RiskRecord.workflow_status.in_(LOW_QUEUE_STATUSES),
        )
    elif committee.authority_level == AuthorityLevel.MIDDLE:
        if not committee.is_fixed:
            return []
        statement = statement.where(RiskRecord.workflow_status.in_(MIDDLE_QUEUE_STATUSES))
    elif committee.authority_level == AuthorityLevel.HIGH:
        if not committee.is_fixed:
            return []
        statement = statement.where(RiskRecord.workflow_status.in_(HIGH_QUEUE_STATUSES))
    else:
        return []

    return list(db.scalars(statement).all())


def get_decision_queue_for_committee(
    db: Session,
    *,
    committee_id: uuid.UUID,
) -> list[RiskRecord]:
    committee = db.get(Committee, committee_id)
    if committee is None:
        raise DecisionQueueBusinessRuleError("Committee does not exist")
    if not committee.is_active:
        raise DecisionQueueBusinessRuleError("Committee is inactive")
    return _queue_risks_for_committee(db, committee=committee)


def get_decision_queue_scope(committee: Committee) -> str | list[str]:
    return _queue_scope(committee)


def _risk_timestamp(risk_record: RiskRecordRead, field: str) -> float:
    value: datetime | None = getattr(risk_record, field, None)
    if value is None:
        return 0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def get_my_decision_queue(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
) -> MyDecisionQueueRead:
    try:
        user = validate_active_user(
            db,
            user_id=requested_by_user_id,
            context="My decision queue access",
        )
    except ValueError as exc:
        raise DecisionQueueBusinessRuleError(str(exc)) from exc

    memberships = db.execute(
        select(CommitteeMember, Committee)
        .join(Committee, CommitteeMember.committee_id == Committee.id)
        .where(
            CommitteeMember.user_id == user.id,
            CommitteeMember.is_active.is_(True),
            Committee.is_active.is_(True),
            Committee.authority_level.in_(
                [AuthorityLevel.LOW, AuthorityLevel.MIDDLE, AuthorityLevel.HIGH]
            ),
        )
        .order_by(Committee.authority_level.asc(), Committee.name.asc())
    ).all()

    committees: list[MyDecisionQueueCommitteeRead] = []
    queue_items: list[MyDecisionQueueItemRead] = []
    seen_committees: set[uuid.UUID] = set()
    seen_items: set[tuple[uuid.UUID, uuid.UUID]] = set()

    for membership, committee in memberships:
        if (
            committee.authority_level in {AuthorityLevel.MIDDLE, AuthorityLevel.HIGH}
            and not committee.is_fixed
        ):
            continue
        if committee.id in seen_committees:
            continue
        seen_committees.add(committee.id)
        committees.append(
            MyDecisionQueueCommitteeRead(
                committee_id=committee.id,
                committee_name=committee.name,
                authority_level=committee.authority_level,
                committee_type=committee.committee_type,
                role_label=membership.role_label,
                queue_scope=_queue_scope(committee),
                is_active=True,
            )
        )

        for risk_record in _queue_risks_for_committee(db, committee=committee):
            item_key = (committee.id, risk_record.id)
            if item_key in seen_items:
                continue
            seen_items.add(item_key)
            queue_items.append(
                MyDecisionQueueItemRead(
                    risk_record=risk_record,
                    committee_id=committee.id,
                    committee_name=committee.name,
                    authority_level=committee.authority_level,
                    role_label=membership.role_label,
                    queue_reason=_queue_reason(committee.authority_level),
                )
            )

    queue_items.sort(
        key=lambda item: (
            -_risk_timestamp(item.risk_record, "updated_at"),
            item.risk_record.risk_id or "",
            -_risk_timestamp(item.risk_record, "created_at"),
        )
    )
    return MyDecisionQueueRead(
        user_id=user.id,
        committees=committees,
        queue_items=queue_items,
    )
