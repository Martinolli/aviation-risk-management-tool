import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.risk import (
    RiskAction,
    RiskAssessment,
    RiskDecision,
    RiskEvidence,
    RiskRecord,
)
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    can_read_risk_record,
    validate_active_user,
)

RISK_RECORD_ENTITY_TYPE = "RiskRecord"
RISK_ASSESSMENT_ENTITY_TYPE = "RiskAssessment"
RISK_ACTION_ENTITY_TYPE = "RiskAction"
RISK_DECISION_ENTITY_TYPE = "RiskDecision"
RISK_EVIDENCE_ENTITY_TYPE = "RiskEvidence"
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


def _audit_summary(audit_logs: list[AuditLog]) -> dict[str, object]:
    return {
        "total_count": len(audit_logs),
        "create_count": sum(
            audit_log.action == AuditAction.CREATE for audit_log in audit_logs
        ),
        "update_count": sum(
            audit_log.action == AuditAction.UPDATE for audit_log in audit_logs
        ),
        "workflow_count": sum(
            audit_log.action in WORKFLOW_AUDIT_ACTIONS for audit_log in audit_logs
        ),
        "evidence_count": sum(
            audit_log.entity_type == RISK_EVIDENCE_ENTITY_TYPE
            for audit_log in audit_logs
        ),
        "latest_changed_at": audit_logs[-1].changed_at if audit_logs else None,
    }


def _related_audit_logs(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    assessments: list[RiskAssessment],
    actions: list[RiskAction],
    decisions: list[RiskDecision],
    evidence_items: list[RiskEvidence],
) -> list[AuditLog]:
    audit_scopes = [
        and_(
            AuditLog.entity_type == RISK_RECORD_ENTITY_TYPE,
            AuditLog.entity_id == risk_record_id,
        )
    ]
    related_entities = (
        (RISK_ASSESSMENT_ENTITY_TYPE, assessments),
        (RISK_ACTION_ENTITY_TYPE, actions),
        (RISK_DECISION_ENTITY_TYPE, decisions),
        (RISK_EVIDENCE_ENTITY_TYPE, evidence_items),
    )
    for entity_type, entities in related_entities:
        entity_ids = [entity.id for entity in entities]
        if entity_ids:
            audit_scopes.append(
                and_(
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id.in_(entity_ids),
                )
            )

    return list(
        db.scalars(
            select(AuditLog)
            .where(or_(*audit_scopes))
            .order_by(AuditLog.changed_at.asc(), AuditLog.created_at.asc())
        ).all()
    )


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
    evidence_items = list(
        db.scalars(
            select(RiskEvidence)
            .where(RiskEvidence.risk_record_id == risk_record_id)
            .order_by(
                RiskEvidence.uploaded_at.desc(),
                RiskEvidence.created_at.desc(),
            )
        )
    )
    audit_logs = _related_audit_logs(
        db,
        risk_record_id=risk_record_id,
        assessments=assessments,
        actions=actions,
        decisions=decisions,
        evidence_items=evidence_items,
    )

    return {
        "risk_record": risk_record,
        "assessments": assessments,
        "actions": actions,
        "decisions": decisions,
        "evidence_items": evidence_items,
        "audit_logs": audit_logs,
        "audit_summary": _audit_summary(audit_logs),
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
