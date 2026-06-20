import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuditAction, AuthorityLevel
from app.models.report import GeneratedReport
from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord
from app.models.user import User

MAX_AUDIT_LOG_LIMIT = 500


class AuditQueryBusinessRuleError(ValueError):
    pass


def _validate_audit_reader(
    db: Session,
    *,
    user_id: uuid.UUID | None,
) -> User:
    if user_id is None:
        raise AuditQueryBusinessRuleError(
            "Audit log access requires an authenticated active user"
        )
    user = db.get(User, user_id)
    if user is None:
        raise AuditQueryBusinessRuleError("Audit log user does not exist")
    if not user.is_active:
        raise AuditQueryBusinessRuleError("Audit log user is inactive")
    return user


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


def _can_read_risk_record_scope(
    db: Session,
    *,
    risk_record_id: uuid.UUID | None,
    user_id: uuid.UUID,
) -> bool:
    if risk_record_id is None:
        return _is_active_fixed_governance_member(db, user_id=user_id)

    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        return _is_active_fixed_governance_member(db, user_id=user_id)
    if user_id in {risk_record.owner_user_id, risk_record.created_by_user_id}:
        return True
    return _is_active_committee_member(
        db,
        committee_id=risk_record.board_of_origin_id,
        user_id=user_id,
    ) or _is_active_fixed_governance_member(db, user_id=user_id)


def _can_read_audit_log(
    db: Session,
    *,
    audit_log: AuditLog,
    user_id: uuid.UUID,
) -> bool:
    if audit_log.entity_type == "RiskRecord":
        return _can_read_risk_record_scope(
            db,
            risk_record_id=audit_log.entity_id,
            user_id=user_id,
        )

    if audit_log.entity_type == "RiskAssessment":
        assessment = db.get(RiskAssessment, audit_log.entity_id)
        if assessment is None:
            return _is_active_fixed_governance_member(db, user_id=user_id)
        return (
            user_id == assessment.assessed_by_user_id
            or _can_read_risk_record_scope(
                db,
                risk_record_id=assessment.risk_record_id,
                user_id=user_id,
            )
        )

    if audit_log.entity_type == "RiskAction":
        action = db.get(RiskAction, audit_log.entity_id)
        if action is None:
            return _is_active_fixed_governance_member(db, user_id=user_id)
        return (
            user_id == action.action_owner_user_id
            or _can_read_risk_record_scope(
                db,
                risk_record_id=action.risk_record_id,
                user_id=user_id,
            )
        )

    if audit_log.entity_type == "RiskDecision":
        decision = db.get(RiskDecision, audit_log.entity_id)
        if decision is None:
            return _is_active_fixed_governance_member(db, user_id=user_id)
        return (
            user_id == decision.decided_by_user_id
            or _is_active_committee_member(
                db,
                committee_id=decision.committee_id,
                user_id=user_id,
            )
            or _can_read_risk_record_scope(
                db,
                risk_record_id=decision.risk_record_id,
                user_id=user_id,
            )
        )

    if audit_log.entity_type == "GeneratedReport":
        report = db.get(GeneratedReport, audit_log.entity_id)
        if report is None or report.risk_record_id is None:
            return _is_active_fixed_governance_member(db, user_id=user_id)
        return (
            user_id == report.generated_by_user_id
            or _can_read_risk_record_scope(
                db,
                risk_record_id=report.risk_record_id,
                user_id=user_id,
            )
        )

    if audit_log.entity_type == "User" and audit_log.entity_id == user_id:
        return True
    if audit_log.entity_type == "CommitteeMember":
        member = db.get(CommitteeMember, audit_log.entity_id)
        if member is not None and member.user_id == user_id:
            return True

    return _is_active_fixed_governance_member(db, user_id=user_id)


def get_audit_log(
    db: Session,
    *,
    audit_log_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> AuditLog | None:
    _validate_audit_reader(db, user_id=requested_by_user_id)
    audit_log = db.get(AuditLog, audit_log_id)
    if audit_log is None:
        return None
    if not _can_read_audit_log(
        db,
        audit_log=audit_log,
        user_id=requested_by_user_id,
    ):
        raise AuditQueryBusinessRuleError("User is not authorized to read this audit log")
    return audit_log


def list_audit_logs(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: AuditAction | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    _validate_audit_reader(db, user_id=requested_by_user_id)
    if limit < 1:
        raise AuditQueryBusinessRuleError("limit must be at least 1")
    if offset < 0:
        raise AuditQueryBusinessRuleError("offset must be at least 0")

    effective_limit = min(limit, MAX_AUDIT_LOG_LIMIT)
    statement = select(AuditLog).order_by(AuditLog.changed_at.desc())

    if entity_type is not None:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(AuditLog.entity_id == entity_id)
    if action is not None:
        statement = statement.where(AuditLog.action == action)
    if changed_by_user_id is not None:
        statement = statement.where(AuditLog.changed_by_user_id == changed_by_user_id)

    statement = statement.limit(effective_limit).offset(offset)
    return [
        audit_log
        for audit_log in db.scalars(statement).all()
        if _can_read_audit_log(
            db,
            audit_log=audit_log,
            user_id=requested_by_user_id,
        )
    ]
