import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.enums import RiskActionStatus, RiskWorkflowStatus
from app.models.risk import RiskAction, RiskRecord
from app.schemas.risk_action import (
    RiskActionCreate,
    RiskActionUpdate,
)

RISK_ACTION_ENTITY_TYPE = "RiskAction"


class RiskActionNotFoundError(ValueError):
    pass


class RiskActionBusinessRuleError(ValueError):
    pass


def _risk_action_snapshot(action: RiskAction) -> dict[str, object]:
    return {
        "id": action.id,
        "risk_record_id": action.risk_record_id,
        "title": action.title,
        "description": action.description,
        "action_owner_user_id": action.action_owner_user_id,
        "due_date": action.due_date,
        "status": action.status,
        "completion_notes": action.completion_notes,
        "completed_at": action.completed_at,
    }


def _validate_title(title: str) -> None:
    if not title.strip():
        raise RiskActionBusinessRuleError("title must not be empty")


def _get_actionable_risk_record(db: Session, risk_record_id: uuid.UUID) -> RiskRecord:
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        raise RiskActionBusinessRuleError("Risk record does not exist")
    if not risk_record.is_active:
        raise RiskActionBusinessRuleError("Inactive risk records cannot have actions")
    if risk_record.workflow_status == RiskWorkflowStatus.CLOSED:
        raise RiskActionBusinessRuleError("Closed risk records cannot have actions")
    return risk_record


def create_risk_action(
    db: Session,
    *,
    data: RiskActionCreate,
    created_by_user_id: uuid.UUID | None = None,
) -> RiskAction:
    _get_actionable_risk_record(db, data.risk_record_id)
    _validate_title(data.title)

    action = RiskAction(
        risk_record_id=data.risk_record_id,
        title=data.title,
        description=data.description,
        action_owner_user_id=data.action_owner_user_id,
        due_date=data.due_date,
        status=RiskActionStatus.OPEN,
        completed_at=None,
    )
    db.add(action)
    db.flush()

    audit_service.log_entity_created(
        db,
        entity_type=RISK_ACTION_ENTITY_TYPE,
        entity_id=action.id,
        created_by_user_id=created_by_user_id,
        new_value=_risk_action_snapshot(action),
    )
    return action


def get_risk_action(
    db: Session,
    *,
    risk_action_id: uuid.UUID,
) -> RiskAction | None:
    return db.get(RiskAction, risk_action_id)


def list_risk_actions(
    db: Session,
    *,
    risk_record_id: uuid.UUID | None = None,
) -> list[RiskAction]:
    statement = select(RiskAction).order_by(RiskAction.created_at.desc())
    if risk_record_id is not None:
        statement = statement.where(RiskAction.risk_record_id == risk_record_id)

    return list(db.scalars(statement).all())


def update_risk_action(
    db: Session,
    *,
    risk_action_id: uuid.UUID,
    data: RiskActionUpdate,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> RiskAction:
    action = get_risk_action(db, risk_action_id=risk_action_id)
    if action is None:
        raise RiskActionNotFoundError("Risk action not found")

    _get_actionable_risk_record(db, action.risk_record_id)
    if action.status == RiskActionStatus.COMPLETED:
        raise RiskActionBusinessRuleError("Completed actions cannot be updated")

    update_data = data.model_dump(exclude_unset=True)
    if "title" in update_data and update_data["title"] is not None:
        _validate_title(update_data["title"])
    if update_data.get("status") == RiskActionStatus.COMPLETED:
        raise RiskActionBusinessRuleError(
            "Use complete_risk_action to complete actions"
        )

    for field_name, new_value in update_data.items():
        old_value = getattr(action, field_name)
        if old_value == new_value:
            continue

        setattr(action, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=RISK_ACTION_ENTITY_TYPE,
            entity_id=action.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )

    db.add(action)
    db.flush()
    return action


def complete_risk_action(
    db: Session,
    *,
    risk_action_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None = None,
    completion_notes: str | None = None,
) -> RiskAction:
    action = get_risk_action(db, risk_action_id=risk_action_id)
    if action is None:
        raise RiskActionNotFoundError("Risk action not found")

    _get_actionable_risk_record(db, action.risk_record_id)
    if action.status == RiskActionStatus.COMPLETED:
        raise RiskActionBusinessRuleError("Risk action is already completed")

    changed_fields = {
        "status": RiskActionStatus.COMPLETED,
        "completed_at": datetime.now(timezone.utc),
        "completion_notes": completion_notes,
    }

    for field_name, new_value in changed_fields.items():
        old_value = getattr(action, field_name)
        if old_value == new_value:
            continue

        setattr(action, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=RISK_ACTION_ENTITY_TYPE,
            entity_id=action.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
        )

    db.add(action)
    db.flush()
    return action
