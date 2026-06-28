import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.committee import Committee, CommitteeMember
from app.models.enums import (
    AuditAction,
    AuthorityLevel,
    RiskActionStatus,
    RiskAssessmentType,
    RiskDecisionType,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord
from app.models.user import User
from app.schemas.risk_decision import RiskDecisionCreate

RISK_DECISION_ENTITY_TYPE = "RiskDecision"
RISK_RECORD_ENTITY_TYPE = "RiskRecord"


class RiskDecisionNotFoundError(ValueError):
    pass


class RiskDecisionBusinessRuleError(ValueError):
    pass


def _risk_decision_snapshot(decision: RiskDecision) -> dict[str, object]:
    return {
        "id": decision.id,
        "risk_record_id": decision.risk_record_id,
        "committee_id": decision.committee_id,
        "decision_type": decision.decision_type,
        "decision_text": decision.decision_text,
        "decided_by_user_id": decision.decided_by_user_id,
        "decided_at": decision.decided_at,
    }


def _validate_decision_text(decision_text: str) -> None:
    if not decision_text.strip():
        raise RiskDecisionBusinessRuleError("decision_text must not be empty")


def _get_decidable_risk_record(db: Session, risk_record_id: uuid.UUID) -> RiskRecord:
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        raise RiskDecisionBusinessRuleError("Risk record does not exist")
    if not risk_record.is_active:
        raise RiskDecisionBusinessRuleError(
            "Inactive risk records cannot receive decisions"
        )
    if risk_record.workflow_status == RiskWorkflowStatus.CLOSED:
        raise RiskDecisionBusinessRuleError("Closed risk records cannot receive decisions")
    return risk_record


def _get_active_committee(db: Session, committee_id: uuid.UUID) -> Committee:
    committee = db.get(Committee, committee_id)
    if committee is None:
        raise RiskDecisionBusinessRuleError("Decision committee does not exist")
    if not committee.is_active:
        raise RiskDecisionBusinessRuleError("Decision committee is inactive")
    return committee


def _validate_decision_authority(
    db: Session,
    *,
    committee: Committee,
    decided_by_user_id: uuid.UUID | None,
) -> None:
    if decided_by_user_id is None:
        raise RiskDecisionBusinessRuleError(
            "Decision requires an authenticated active user"
        )

    user = db.get(User, decided_by_user_id)
    if user is None:
        raise RiskDecisionBusinessRuleError("Decision user does not exist")
    if not user.is_active:
        raise RiskDecisionBusinessRuleError("Decision user is inactive")
    if not committee.is_active:
        raise RiskDecisionBusinessRuleError("Decision committee is inactive")

    membership = db.scalar(
        select(CommitteeMember.id).where(
            CommitteeMember.committee_id == committee.id,
            CommitteeMember.user_id == decided_by_user_id,
            CommitteeMember.is_active.is_(True),
        )
    )
    if membership is None:
        raise RiskDecisionBusinessRuleError(
            "Decision user is not an active member of the committee"
        )


def _validate_committee_risk_scope(
    *,
    risk_record: RiskRecord,
    committee: Committee,
) -> None:
    if committee.authority_level == AuthorityLevel.LOW:
        if risk_record.board_of_origin_id != committee.id:
            raise RiskDecisionBusinessRuleError(
                "LOW decision committee must be the risk Board of Origin"
            )
        return

    if not committee.is_fixed:
        raise RiskDecisionBusinessRuleError(
            "MIDDLE/HIGH decisions require a fixed governance committee"
        )

    required_status = {
        AuthorityLevel.MIDDLE: (
            RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE
        ),
        AuthorityLevel.HIGH: RiskWorkflowStatus.ESCALATED_TO_EXECUTIVE_COMMITTEE,
    }[committee.authority_level]
    if risk_record.workflow_status != required_status:
        raise RiskDecisionBusinessRuleError(
            f"{committee.authority_level.value} committee cannot decide a risk "
            f"in {risk_record.workflow_status.value} status"
        )


def _get_residual_assessment_for_risk(
    db: Session,
    risk_record_id: uuid.UUID,
) -> RiskAssessment | None:
    statement = (
        select(RiskAssessment)
        .where(
            RiskAssessment.risk_record_id == risk_record_id,
            RiskAssessment.assessment_type == RiskAssessmentType.RESIDUAL,
        )
        .order_by(RiskAssessment.assessed_at.desc(), RiskAssessment.created_at.desc())
    )
    return db.scalars(statement).first()


def _has_open_mitigation_actions(db: Session, risk_record_id: uuid.UUID) -> bool:
    actions = db.scalars(
        select(RiskAction).where(RiskAction.risk_record_id == risk_record_id)
    ).all()

    for action in actions:
        if action.completed_at is not None:
            continue
        if action.status in {RiskActionStatus.COMPLETED, RiskActionStatus.CANCELLED}:
            continue
        if action.status in {RiskActionStatus.OPEN, RiskActionStatus.IN_PROGRESS}:
            return True

    return False


def _validate_residual_acceptance_authority(
    db: Session,
    risk_record: RiskRecord,
    committee: Committee,
) -> None:
    if committee.authority_level != AuthorityLevel.LOW:
        return

    residual_assessment = _get_residual_assessment_for_risk(db, risk_record.id)
    if residual_assessment is None:
        raise RiskDecisionBusinessRuleError(
            "LOW authority committee requires a residual assessment before accepting residual risk"
        )
    if residual_assessment.is_tolerable is not True:
        raise RiskDecisionBusinessRuleError(
            "LOW authority committee cannot accept non-tolerable residual risk"
        )
    if residual_assessment.requires_escalation is True:
        raise RiskDecisionBusinessRuleError(
            "LOW authority committee cannot accept residual risk that requires escalation"
        )


def _validate_closure_authority(
    db: Session,
    risk_record: RiskRecord,
    committee: Committee,
) -> None:
    if committee.authority_level != AuthorityLevel.LOW:
        return

    residual_assessment = _get_residual_assessment_for_risk(db, risk_record.id)
    if residual_assessment is None:
        raise RiskDecisionBusinessRuleError(
            "LOW authority committee requires a residual assessment before closing a risk"
        )
    if residual_assessment.is_tolerable is not True:
        raise RiskDecisionBusinessRuleError(
            "LOW authority committee cannot close a risk with non-tolerable residual risk"
        )
    if residual_assessment.requires_escalation is True:
        raise RiskDecisionBusinessRuleError(
            "LOW authority committee cannot close a risk that requires escalation"
        )
    if _has_open_mitigation_actions(db, risk_record.id):
        raise RiskDecisionBusinessRuleError(
            "LOW authority committee cannot close a risk with open mitigation actions"
        )


def _validate_decision_business_context(
    db: Session,
    risk_record: RiskRecord,
    committee: Committee,
    decision_type: RiskDecisionType,
) -> None:
    if decision_type == RiskDecisionType.ACCEPT_RESIDUAL_RISK:
        _validate_residual_acceptance_authority(db, risk_record, committee)
    if decision_type == RiskDecisionType.CLOSE:
        _validate_closure_authority(db, risk_record, committee)


def _decision_effect(
    committee: Committee,
    decision_type: RiskDecisionType,
) -> tuple[RiskWorkflowStatus, RiskLifecycleStatus | None, AuditAction]:
    if decision_type == RiskDecisionType.APPROVE:
        if committee.authority_level == AuthorityLevel.LOW:
            return (
                RiskWorkflowStatus.APPROVED_AT_OPERATIONAL_BOARD,
                None,
                AuditAction.APPROVE,
            )
        if committee.authority_level == AuthorityLevel.MIDDLE:
            return (
                RiskWorkflowStatus.APPROVED_AT_RISK_MANAGEMENT_COMMITTEE,
                None,
                AuditAction.APPROVE,
            )
        return (RiskWorkflowStatus.ACCEPTED, None, AuditAction.APPROVE)

    if decision_type == RiskDecisionType.REJECT:
        return (RiskWorkflowStatus.REJECTED, None, AuditAction.REJECT)

    if decision_type == RiskDecisionType.ESCALATE:
        if committee.authority_level == AuthorityLevel.LOW:
            return (
                RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
                None,
                AuditAction.ESCALATE,
            )
        if committee.authority_level == AuthorityLevel.MIDDLE:
            return (
                RiskWorkflowStatus.ESCALATED_TO_EXECUTIVE_COMMITTEE,
                None,
                AuditAction.ESCALATE,
            )
        raise RiskDecisionBusinessRuleError("HIGH authority committee cannot escalate")

    if decision_type == RiskDecisionType.RETURN_FOR_REVISION:
        return (
            RiskWorkflowStatus.RETURNED_FOR_REVISION,
            None,
            AuditAction.RETURN_FOR_REVISION,
        )

    if decision_type == RiskDecisionType.ACCEPT_RESIDUAL_RISK:
        return (RiskWorkflowStatus.ACCEPTED, None, AuditAction.APPROVE)

    if decision_type == RiskDecisionType.CLOSE:
        # AuditAction has no CLOSE value yet, so CLOSE decisions use APPROVE temporarily.
        return (
            RiskWorkflowStatus.CLOSED,
            RiskLifecycleStatus.CLOSED,
            AuditAction.APPROVE,
        )

    raise RiskDecisionBusinessRuleError(f"Unsupported decision type: {decision_type}")


def _apply_decision_to_risk_record(
    db: Session,
    risk_record: RiskRecord,
    committee: Committee,
    decision_type: RiskDecisionType,
    decided_by_user_id: uuid.UUID | None,
) -> None:
    new_workflow_status, new_lifecycle_status, audit_action = _decision_effect(
        committee,
        decision_type,
    )
    old_value = {
        "workflow_status": risk_record.workflow_status,
        "lifecycle_status": risk_record.lifecycle_status,
    }

    risk_record.workflow_status = new_workflow_status
    if new_lifecycle_status is not None:
        risk_record.lifecycle_status = new_lifecycle_status

    new_value = {
        "workflow_status": risk_record.workflow_status,
        "lifecycle_status": risk_record.lifecycle_status,
    }

    audit_service.log_workflow_action(
        db,
        entity_type=RISK_RECORD_ENTITY_TYPE,
        entity_id=risk_record.id,
        action=audit_action,
        changed_by_user_id=decided_by_user_id,
        old_value=old_value,
        new_value=new_value,
        reason=f"Decision: {decision_type.value}",
    )
    db.add(risk_record)
    db.flush()


def create_risk_decision(
    db: Session,
    *,
    data: RiskDecisionCreate,
    decided_by_user_id: uuid.UUID | None = None,
) -> RiskDecision:
    _validate_decision_text(data.decision_text)
    risk_record = _get_decidable_risk_record(db, data.risk_record_id)
    committee = _get_active_committee(db, data.committee_id)
    _validate_decision_business_context(db, risk_record, committee, data.decision_type)
    _validate_decision_authority(
        db,
        committee=committee,
        decided_by_user_id=decided_by_user_id,
    )
    _validate_committee_risk_scope(risk_record=risk_record, committee=committee)
    _decision_effect(committee, data.decision_type)

    decision = RiskDecision(
        risk_record_id=data.risk_record_id,
        committee_id=data.committee_id,
        decision_type=data.decision_type,
        decision_text=data.decision_text,
        decided_by_user_id=decided_by_user_id,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(decision)
    db.flush()

    audit_service.log_entity_created(
        db,
        entity_type=RISK_DECISION_ENTITY_TYPE,
        entity_id=decision.id,
        created_by_user_id=decided_by_user_id,
        new_value=_risk_decision_snapshot(decision),
    )
    _apply_decision_to_risk_record(
        db,
        risk_record,
        committee,
        data.decision_type,
        decided_by_user_id,
    )
    return decision


def get_risk_decision(
    db: Session,
    *,
    risk_decision_id: uuid.UUID,
) -> RiskDecision | None:
    return db.get(RiskDecision, risk_decision_id)


def list_risk_decisions(
    db: Session,
    *,
    risk_record_id: uuid.UUID | None = None,
    committee_id: uuid.UUID | None = None,
) -> list[RiskDecision]:
    statement = select(RiskDecision).order_by(RiskDecision.decided_at.desc())
    if risk_record_id is not None:
        statement = statement.where(RiskDecision.risk_record_id == risk_record_id)
    if committee_id is not None:
        statement = statement.where(RiskDecision.committee_id == committee_id)

    return list(db.scalars(statement).all())
