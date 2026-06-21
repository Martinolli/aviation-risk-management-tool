import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuditAction, AuthorityLevel
from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord
from app.models.user import User

RISK_RECORD_ENTITY_TYPE = "RiskRecord"
WORKFLOW_AUDIT_ACTIONS = {
    AuditAction.SUBMIT,
    AuditAction.APPROVE,
    AuditAction.REJECT,
    AuditAction.ESCALATE,
    AuditAction.RETURN_FOR_REVISION,
}


class RiskDetailNotFoundError(ValueError):
    pass


class RiskDetailBusinessRuleError(ValueError):
    pass


def _validate_risk_detail_reader(
    db: Session,
    *,
    user_id: uuid.UUID | None,
) -> User:
    if user_id is None:
        raise RiskDetailBusinessRuleError(
            "Risk detail access requires an authenticated active user"
        )
    user = db.get(User, user_id)
    if user is None:
        raise RiskDetailBusinessRuleError("Risk detail user does not exist")
    if not user.is_active:
        raise RiskDetailBusinessRuleError("Risk detail user is inactive")
    return user


def _is_active_committee_member(
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


def _is_active_fixed_governance_member(
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


def _validate_risk_detail_authority(
    db: Session,
    *,
    risk_record: RiskRecord,
    user_id: uuid.UUID,
) -> None:
    if user_id in {risk_record.owner_user_id, risk_record.created_by_user_id}:
        return
    if _is_active_committee_member(
        db,
        committee_id=risk_record.board_of_origin_id,
        user_id=user_id,
    ):
        return
    if db.scalar(
        select(RiskAssessment.id).where(
            RiskAssessment.risk_record_id == risk_record.id,
            RiskAssessment.assessed_by_user_id == user_id,
        )
    ) is not None:
        return
    if db.scalar(
        select(RiskAction.id).where(
            RiskAction.risk_record_id == risk_record.id,
            RiskAction.action_owner_user_id == user_id,
        )
    ) is not None:
        return
    if db.scalar(
        select(RiskDecision.id).where(
            RiskDecision.risk_record_id == risk_record.id,
            RiskDecision.decided_by_user_id == user_id,
        )
    ) is not None:
        return
    decision_committee_ids = db.scalars(
        select(RiskDecision.committee_id).where(
            RiskDecision.risk_record_id == risk_record.id
        )
    )
    if any(
        _is_active_committee_member(
            db,
            committee_id=committee_id,
            user_id=user_id,
        )
        for committee_id in decision_committee_ids
    ):
        return
    if _is_active_fixed_governance_member(db, user_id=user_id):
        return
    raise RiskDetailBusinessRuleError("User is not authorized to read this risk detail")


def _count_audit_logs(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    action: AuditAction | None = None,
    workflow_actions: bool = False,
) -> int:
    statement = (
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.entity_type == RISK_RECORD_ENTITY_TYPE,
            AuditLog.entity_id == risk_record_id,
        )
    )
    if action is not None:
        statement = statement.where(AuditLog.action == action)
    if workflow_actions:
        statement = statement.where(AuditLog.action.in_(WORKFLOW_AUDIT_ACTIONS))

    return db.scalar(statement) or 0


def _audit_summary(db: Session, *, risk_record_id: uuid.UUID) -> dict[str, object]:
    latest_changed_at = db.scalar(
        select(func.max(AuditLog.changed_at)).where(
            AuditLog.entity_type == RISK_RECORD_ENTITY_TYPE,
            AuditLog.entity_id == risk_record_id,
        )
    )

    return {
        "total_count": _count_audit_logs(db, risk_record_id=risk_record_id),
        "create_count": _count_audit_logs(
            db,
            risk_record_id=risk_record_id,
            action=AuditAction.CREATE,
        ),
        "update_count": _count_audit_logs(
            db,
            risk_record_id=risk_record_id,
            action=AuditAction.UPDATE,
        ),
        "workflow_count": _count_audit_logs(
            db,
            risk_record_id=risk_record_id,
            workflow_actions=True,
        ),
        "latest_changed_at": latest_changed_at,
    }


def _build_risk_record_detail(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
) -> dict[str, object] | None:
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        return None

    assessments = list(
        db.scalars(
            select(RiskAssessment)
            .where(RiskAssessment.risk_record_id == risk_record_id)
            .order_by(RiskAssessment.created_at.desc())
        )
    )
    actions = list(
        db.scalars(
            select(RiskAction)
            .where(RiskAction.risk_record_id == risk_record_id)
            .order_by(RiskAction.created_at.desc())
        )
    )
    decisions = list(
        db.scalars(
            select(RiskDecision)
            .where(RiskDecision.risk_record_id == risk_record_id)
            .order_by(RiskDecision.decided_at.desc())
        )
    )

    return {
        "risk_record": risk_record,
        "assessments": assessments,
        "actions": actions,
        "decisions": decisions,
        "audit_summary": _audit_summary(db, risk_record_id=risk_record_id),
    }


def get_risk_record_detail(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> dict[str, object] | None:
    _validate_risk_detail_reader(db, user_id=requested_by_user_id)
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        return None
    _validate_risk_detail_authority(
        db,
        risk_record=risk_record,
        user_id=requested_by_user_id,
    )
    return _build_risk_record_detail(db, risk_record_id=risk_record_id)
