import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel
from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord
from app.models.user import User


class RiskAccessBusinessRuleError(ValueError):
    pass


def validate_active_user(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    context: str,
) -> User:
    if user_id is None:
        raise RiskAccessBusinessRuleError(
            f"{context} requires an authenticated active user"
        )
    user = db.get(User, user_id)
    if user is None:
        raise RiskAccessBusinessRuleError(f"{context} user does not exist")
    if not user.is_active:
        raise RiskAccessBusinessRuleError(f"{context} user is inactive")
    return user


def is_active_committee_member(
    db: Session,
    *,
    committee_id: uuid.UUID | None,
    user_id: uuid.UUID,
) -> bool:
    if committee_id is None:
        return False
    return db.scalar(
        select(CommitteeMember.id)
        .join(Committee, CommitteeMember.committee_id == Committee.id)
        .where(
            CommitteeMember.committee_id == committee_id,
            CommitteeMember.user_id == user_id,
            CommitteeMember.is_active.is_(True),
            Committee.is_active.is_(True),
        )
    ) is not None


def is_active_fixed_governance_member(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> bool:
    return db.scalar(
        select(CommitteeMember.id)
        .join(Committee, CommitteeMember.committee_id == Committee.id)
        .where(
            CommitteeMember.user_id == user_id,
            CommitteeMember.is_active.is_(True),
            Committee.is_active.is_(True),
            Committee.is_fixed.is_(True),
            Committee.authority_level.in_([AuthorityLevel.MIDDLE, AuthorityLevel.HIGH]),
        )
    ) is not None


def can_read_risk_record(
    db: Session,
    *,
    risk_record: RiskRecord,
    user_id: uuid.UUID,
) -> bool:
    if user_id in {risk_record.owner_user_id, risk_record.created_by_user_id}:
        return True
    if is_active_committee_member(
        db,
        committee_id=risk_record.board_of_origin_id,
        user_id=user_id,
    ):
        return True
    if db.scalar(
        select(RiskAssessment.id).where(
            RiskAssessment.risk_record_id == risk_record.id,
            RiskAssessment.assessed_by_user_id == user_id,
        )
    ) is not None:
        return True
    if db.scalar(
        select(RiskAction.id).where(
            RiskAction.risk_record_id == risk_record.id,
            RiskAction.action_owner_user_id == user_id,
        )
    ) is not None:
        return True
    if db.scalar(
        select(RiskDecision.id).where(
            RiskDecision.risk_record_id == risk_record.id,
            RiskDecision.decided_by_user_id == user_id,
        )
    ) is not None:
        return True

    decision_committee_ids = db.scalars(
        select(RiskDecision.committee_id).where(
            RiskDecision.risk_record_id == risk_record.id
        )
    )
    if any(
        is_active_committee_member(
            db,
            committee_id=committee_id,
            user_id=user_id,
        )
        for committee_id in decision_committee_ids
    ):
        return True

    return is_active_fixed_governance_member(db, user_id=user_id)


def filter_readable_risk_records(
    db: Session,
    *,
    risk_records: list[RiskRecord],
    user_id: uuid.UUID,
) -> list[RiskRecord]:
    return [
        risk_record
        for risk_record in risk_records
        if can_read_risk_record(db, risk_record=risk_record, user_id=user_id)
    ]
