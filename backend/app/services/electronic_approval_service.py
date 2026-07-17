import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.committee import Committee
from app.models.electronic_approval import ElectronicApproval
from app.models.enums import (
    ElectronicApprovalStatus,
    ElectronicApprovalTargetType,
)
from app.models.risk import RiskDecision, RiskRecord
from app.schemas.electronic_approval import (
    DEFAULT_ACKNOWLEDGEMENT_TEXT,
    DEFAULT_MEANING_OF_SIGNATURE,
    ElectronicApprovalCreate,
)
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    can_read_risk_record,
    is_active_committee_member,
    is_active_fixed_governance_member,
    validate_active_user,
)

ELECTRONIC_APPROVAL_ENTITY_TYPE = "ElectronicApproval"


class ElectronicApprovalBusinessRuleError(ValueError):
    pass


class ElectronicApprovalNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class ApprovalTargetContext:
    risk_record_id: uuid.UUID | None
    risk_decision_id: uuid.UUID | None
    committee_id: uuid.UUID | None
    authority_level: object | None
    metadata_json: dict[str, Any]


def _to_hash_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        normalized = (
            value.astimezone(timezone.utc).replace(tzinfo=None)
            if value.tzinfo is not None
            else value
        )
        return normalized.isoformat()
    if hasattr(value, "value"):
        return getattr(value, "value")
    return value


def compute_approval_hash(approval: ElectronicApproval) -> str:
    payload = {
        "target_type": _to_hash_value(approval.target_type),
        "target_id": _to_hash_value(approval.target_id),
        "risk_record_id": _to_hash_value(approval.risk_record_id),
        "risk_decision_id": _to_hash_value(approval.risk_decision_id),
        "committee_id": _to_hash_value(approval.committee_id),
        "authority_level": _to_hash_value(approval.authority_level),
        "approved_by_user_id": _to_hash_value(approval.approved_by_user_id),
        "approved_at": _to_hash_value(approval.approved_at),
        "approval_statement": approval.approval_statement,
        "acknowledgement_text": approval.acknowledgement_text,
        "meaning_of_signature": approval.meaning_of_signature,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _approval_snapshot(approval: ElectronicApproval) -> dict[str, object]:
    return {
        "id": approval.id,
        "target_type": approval.target_type,
        "target_id": approval.target_id,
        "risk_record_id": approval.risk_record_id,
        "risk_decision_id": approval.risk_decision_id,
        "committee_id": approval.committee_id,
        "authority_level": approval.authority_level,
        "approved_by_user_id": approval.approved_by_user_id,
        "approved_at": approval.approved_at,
        "approval_statement": approval.approval_statement,
        "acknowledgement_text": approval.acknowledgement_text,
        "meaning_of_signature": approval.meaning_of_signature,
        "status": approval.status,
        "approval_hash": approval.approval_hash,
        "metadata_json": approval.metadata_json,
    }


def _validate_statement(value: str) -> str:
    statement = value.strip()
    if not statement:
        raise ElectronicApprovalBusinessRuleError(
            "Approval statement must not be blank"
        )
    return statement


def _active_user_or_error(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    context: str,
):
    try:
        return validate_active_user(db, user_id=user_id, context=context)
    except RiskAccessBusinessRuleError as exc:
        raise ElectronicApprovalBusinessRuleError(str(exc)) from exc


def _get_active_risk(db: Session, risk_record_id: uuid.UUID) -> RiskRecord:
    risk = db.get(RiskRecord, risk_record_id)
    if risk is None:
        raise ElectronicApprovalBusinessRuleError("Risk record does not exist")
    if not risk.is_active:
        raise ElectronicApprovalBusinessRuleError(
            "Inactive risk records cannot be approved"
        )
    return risk


def _get_committee(db: Session, committee_id: uuid.UUID | None) -> Committee | None:
    if committee_id is None:
        return None
    committee = db.get(Committee, committee_id)
    if committee is None:
        raise ElectronicApprovalBusinessRuleError("Committee does not exist")
    if not committee.is_active:
        raise ElectronicApprovalBusinessRuleError("Committee is inactive")
    return committee


def _resolve_risk_record_target(
    db: Session,
    *,
    target_id: uuid.UUID,
    approved_by_user_id: uuid.UUID,
) -> ApprovalTargetContext:
    risk = _get_active_risk(db, target_id)
    if not can_read_risk_record(db, risk_record=risk, user_id=approved_by_user_id):
        raise ElectronicApprovalBusinessRuleError(
            "User is not authorized to approve this risk record"
        )
    committee = _get_committee(db, risk.board_of_origin_id)
    return ApprovalTargetContext(
        risk_record_id=risk.id,
        risk_decision_id=None,
        committee_id=committee.id if committee is not None else None,
        authority_level=committee.authority_level if committee is not None else None,
        metadata_json={
            "target_kind": "RiskRecord",
            "risk_id": risk.risk_id,
            "not_a_cryptographic_digital_signature": True,
        },
    )


def _can_approve_decision(
    db: Session,
    *,
    decision: RiskDecision,
    user_id: uuid.UUID,
) -> bool:
    if decision.decided_by_user_id == user_id:
        return True
    if is_active_committee_member(
        db,
        committee_id=decision.committee_id,
        user_id=user_id,
    ):
        return True
    return is_active_fixed_governance_member(db, user_id=user_id)


def _resolve_risk_decision_target(
    db: Session,
    *,
    target_id: uuid.UUID,
    approved_by_user_id: uuid.UUID,
) -> ApprovalTargetContext:
    decision = db.get(RiskDecision, target_id)
    if decision is None:
        raise ElectronicApprovalBusinessRuleError("Risk decision does not exist")
    risk = _get_active_risk(db, decision.risk_record_id)
    if not can_read_risk_record(db, risk_record=risk, user_id=approved_by_user_id):
        raise ElectronicApprovalBusinessRuleError(
            "User is not authorized to approve this risk decision"
        )
    if not _can_approve_decision(db, decision=decision, user_id=approved_by_user_id):
        raise ElectronicApprovalBusinessRuleError(
            "User is not authorized by the decision Authority Level or committee"
        )
    committee = _get_committee(db, decision.committee_id)
    return ApprovalTargetContext(
        risk_record_id=decision.risk_record_id,
        risk_decision_id=decision.id,
        committee_id=decision.committee_id,
        authority_level=committee.authority_level if committee is not None else None,
        metadata_json={
            "target_kind": "RiskDecision",
            "decision_type": decision.decision_type.value,
            "not_a_cryptographic_digital_signature": True,
        },
    )


def _resolve_target(
    db: Session,
    *,
    data: ElectronicApprovalCreate,
    approved_by_user_id: uuid.UUID,
) -> ApprovalTargetContext:
    if data.target_type == ElectronicApprovalTargetType.RISK_RECORD:
        return _resolve_risk_record_target(
            db,
            target_id=data.target_id,
            approved_by_user_id=approved_by_user_id,
        )
    if data.target_type == ElectronicApprovalTargetType.RISK_DECISION:
        return _resolve_risk_decision_target(
            db,
            target_id=data.target_id,
            approved_by_user_id=approved_by_user_id,
        )
    if data.target_type == ElectronicApprovalTargetType.GENERATED_REPORT:
        raise ElectronicApprovalBusinessRuleError(
            "Generated report approvals are not yet supported."
        )
    if data.target_type == ElectronicApprovalTargetType.COMMITTEE_MEETING:
        raise ElectronicApprovalBusinessRuleError(
            "Committee meeting approvals are not yet supported."
        )
    raise ElectronicApprovalBusinessRuleError(
        f"Unsupported approval target: {data.target_type}"
    )


def _validate_no_duplicate_approval(
    db: Session,
    *,
    target_type: ElectronicApprovalTargetType,
    target_id: uuid.UUID,
    approved_by_user_id: uuid.UUID,
) -> None:
    existing = db.scalar(
        select(ElectronicApproval.id).where(
            ElectronicApproval.target_type == target_type,
            ElectronicApproval.target_id == target_id,
            ElectronicApproval.approved_by_user_id == approved_by_user_id,
            ElectronicApproval.status == ElectronicApprovalStatus.APPROVED,
        )
    )
    if existing is not None:
        raise ElectronicApprovalBusinessRuleError(
            "User has already approved this target."
        )


def _can_read_approval(
    db: Session,
    *,
    approval: ElectronicApproval,
    user_id: uuid.UUID,
) -> bool:
    if approval.risk_record_id is None:
        return is_active_fixed_governance_member(db, user_id=user_id)
    risk = db.get(RiskRecord, approval.risk_record_id)
    if risk is None:
        return is_active_fixed_governance_member(db, user_id=user_id)
    return can_read_risk_record(db, risk_record=risk, user_id=user_id)


def create_electronic_approval(
    db: Session,
    *,
    data: ElectronicApprovalCreate,
    approved_by_user_id: uuid.UUID | None,
) -> ElectronicApproval:
    user = _active_user_or_error(
        db,
        user_id=approved_by_user_id,
        context="Electronic Approval",
    )
    approval_statement = _validate_statement(data.approval_statement)
    _validate_no_duplicate_approval(
        db,
        target_type=data.target_type,
        target_id=data.target_id,
        approved_by_user_id=user.id,
    )
    target_context = _resolve_target(
        db,
        data=data,
        approved_by_user_id=user.id,
    )

    approval = ElectronicApproval(
        target_type=data.target_type,
        target_id=data.target_id,
        risk_record_id=target_context.risk_record_id,
        risk_decision_id=target_context.risk_decision_id,
        committee_id=target_context.committee_id,
        authority_level=target_context.authority_level,
        approved_by_user_id=user.id,
        approved_at=datetime.now(timezone.utc),
        approval_statement=approval_statement,
        acknowledgement_text=(
            data.acknowledgement_text.strip()
            if data.acknowledgement_text and data.acknowledgement_text.strip()
            else DEFAULT_ACKNOWLEDGEMENT_TEXT
        ),
        meaning_of_signature=DEFAULT_MEANING_OF_SIGNATURE,
        status=ElectronicApprovalStatus.APPROVED,
        approval_hash="pending",
        metadata_json=target_context.metadata_json,
    )
    approval.approval_hash = compute_approval_hash(approval)
    db.add(approval)
    db.flush()

    audit_service.log_electronic_approval(
        db,
        entity_type=ELECTRONIC_APPROVAL_ENTITY_TYPE,
        entity_id=approval.id,
        approved_by_user_id=user.id,
        approval_metadata=_approval_snapshot(approval),
        reason="Electronic Approval / Signature Concept MVP",
    )
    return approval


def list_electronic_approvals(
    db: Session,
    *,
    target_type: ElectronicApprovalTargetType | None = None,
    target_id: uuid.UUID | None = None,
    risk_record_id: uuid.UUID | None = None,
    approved_by_user_id: uuid.UUID | None = None,
    requested_by_user_id: uuid.UUID | None,
) -> list[ElectronicApproval]:
    user = _active_user_or_error(
        db,
        user_id=requested_by_user_id,
        context="Electronic Approval access",
    )
    statement = select(ElectronicApproval).order_by(
        ElectronicApproval.approved_at.desc()
    )
    if target_type is not None:
        statement = statement.where(ElectronicApproval.target_type == target_type)
    if target_id is not None:
        statement = statement.where(ElectronicApproval.target_id == target_id)
    if risk_record_id is not None:
        statement = statement.where(ElectronicApproval.risk_record_id == risk_record_id)
    if approved_by_user_id is not None:
        statement = statement.where(
            ElectronicApproval.approved_by_user_id == approved_by_user_id
        )
    return [
        approval
        for approval in db.scalars(statement).all()
        if _can_read_approval(db, approval=approval, user_id=user.id)
    ]


def get_electronic_approval(
    db: Session,
    *,
    approval_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> ElectronicApproval | None:
    user = _active_user_or_error(
        db,
        user_id=requested_by_user_id,
        context="Electronic Approval access",
    )
    approval = db.get(ElectronicApproval, approval_id)
    if approval is None:
        return None
    if not _can_read_approval(db, approval=approval, user_id=user.id):
        raise ElectronicApprovalBusinessRuleError(
            "User is not authorized to read this electronic approval"
        )
    return approval
