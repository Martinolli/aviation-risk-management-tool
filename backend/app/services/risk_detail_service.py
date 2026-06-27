import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    can_read_risk_record,
    validate_active_user,
)

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
    try:
        reader = validate_active_user(
            db,
            user_id=requested_by_user_id,
            context="Risk detail access",
        )
    except RiskAccessBusinessRuleError as exc:
        raise RiskDetailBusinessRuleError(str(exc)) from exc

    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        return None
    if not can_read_risk_record(db, risk_record=risk_record, user_id=reader.id):
        raise RiskDetailBusinessRuleError(
            "User is not authorized to read this risk detail"
        )
    return _build_risk_record_detail(db, risk_record_id=risk_record_id)
