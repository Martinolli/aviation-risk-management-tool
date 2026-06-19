import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.committee import Committee
from app.models.enums import AuditAction, RiskLifecycleStatus, RiskWorkflowStatus
from app.models.risk import RiskRecord
from app.schemas.risk import RiskRecordCreate, RiskRecordUpdate

RISK_RECORD_ENTITY_TYPE = "RiskRecord"


class RiskRecordNotFoundError(ValueError):
    pass


class RiskRecordBusinessRuleError(ValueError):
    pass


def _risk_record_snapshot(risk_record: RiskRecord) -> dict[str, object]:
    return {
        "id": risk_record.id,
        "risk_id": risk_record.risk_id,
        "problem_description": risk_record.problem_description,
        "source_trigger": risk_record.source_trigger,
        "domain": risk_record.domain,
        "board_of_origin_id": risk_record.board_of_origin_id,
        "system_scope": risk_record.system_scope,
        "central_event": risk_record.central_event,
        "hazard_statement": risk_record.hazard_statement,
        "causes": risk_record.causes,
        "consequences": risk_record.consequences,
        "existing_controls": risk_record.existing_controls,
        "workflow_status": risk_record.workflow_status,
        "lifecycle_status": risk_record.lifecycle_status,
        "created_by_user_id": risk_record.created_by_user_id,
        "owner_user_id": risk_record.owner_user_id,
        "is_active": risk_record.is_active,
        "archived_at": risk_record.archived_at,
        "archive_reason": risk_record.archive_reason,
    }


def _validate_problem_description(problem_description: str) -> None:
    if not problem_description.strip():
        raise RiskRecordBusinessRuleError("Problem description is required")


def _validate_board_of_origin(db: Session, board_of_origin_id: uuid.UUID | None) -> None:
    if board_of_origin_id is None:
        return

    committee = db.get(Committee, board_of_origin_id)
    if committee is None:
        raise RiskRecordBusinessRuleError("Board of origin does not exist")
    if not committee.is_active:
        raise RiskRecordBusinessRuleError("Board of origin is inactive")


def create_risk_record(
    db: Session,
    *,
    data: RiskRecordCreate,
    created_by_user_id: uuid.UUID | None = None,
) -> RiskRecord:
    _validate_problem_description(data.problem_description)
    _validate_board_of_origin(db, data.board_of_origin_id)

    risk_record = RiskRecord(
        problem_description=data.problem_description,
        source_trigger=data.source_trigger,
        domain=data.domain,
        board_of_origin_id=data.board_of_origin_id,
        system_scope=data.system_scope,
        central_event=data.central_event,
        hazard_statement=data.hazard_statement,
        causes=data.causes,
        consequences=data.consequences,
        existing_controls=data.existing_controls,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=created_by_user_id,
        owner_user_id=data.owner_user_id,
        is_active=True,
    )
    db.add(risk_record)
    db.flush()

    audit_service.log_entity_created(
        db,
        entity_type=RISK_RECORD_ENTITY_TYPE,
        entity_id=risk_record.id,
        created_by_user_id=created_by_user_id,
        new_value=_risk_record_snapshot(risk_record),
    )
    return risk_record


def get_risk_record(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
) -> RiskRecord | None:
    return db.get(RiskRecord, risk_record_id)


def list_risk_records(
    db: Session,
    *,
    include_archived: bool = False,
) -> list[RiskRecord]:
    statement = select(RiskRecord).order_by(RiskRecord.created_at.desc())
    if not include_archived:
        statement = statement.where(RiskRecord.is_active.is_(True))

    return list(db.scalars(statement).all())


def update_risk_record(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    data: RiskRecordUpdate,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> RiskRecord:
    risk_record = get_risk_record(db, risk_record_id=risk_record_id)
    if risk_record is None:
        raise RiskRecordNotFoundError("Risk record not found")
    if not risk_record.is_active:
        raise RiskRecordBusinessRuleError("Archived or inactive risks cannot be updated")
    if risk_record.workflow_status == RiskWorkflowStatus.CLOSED:
        raise RiskRecordBusinessRuleError("Closed risks cannot be updated")

    update_data = data.model_dump(exclude_unset=True)
    if "problem_description" in update_data:
        raise RiskRecordBusinessRuleError(
            "Problem description cannot be updated through this service"
        )
    _validate_board_of_origin(db, update_data.get("board_of_origin_id"))

    for field_name, new_value in update_data.items():
        old_value = getattr(risk_record, field_name)
        if old_value == new_value:
            continue

        setattr(risk_record, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=RISK_RECORD_ENTITY_TYPE,
            entity_id=risk_record.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )

    db.add(risk_record)
    db.flush()
    return risk_record


def submit_risk_record(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> RiskRecord:
    risk_record = get_risk_record(db, risk_record_id=risk_record_id)
    if risk_record is None:
        raise RiskRecordNotFoundError("Risk record not found")
    if not risk_record.is_active:
        raise RiskRecordBusinessRuleError("Archived or inactive risks cannot be submitted")
    if risk_record.workflow_status != RiskWorkflowStatus.DRAFT:
        raise RiskRecordBusinessRuleError("Only DRAFT risks can be submitted")

    old_status = risk_record.workflow_status
    risk_record.workflow_status = RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD

    audit_service.log_workflow_action(
        db,
        entity_type=RISK_RECORD_ENTITY_TYPE,
        entity_id=risk_record.id,
        action=AuditAction.SUBMIT,
        changed_by_user_id=changed_by_user_id,
        old_value={"workflow_status": old_status},
        new_value={"workflow_status": risk_record.workflow_status},
        reason=reason,
    )
    db.add(risk_record)
    db.flush()
    return risk_record
