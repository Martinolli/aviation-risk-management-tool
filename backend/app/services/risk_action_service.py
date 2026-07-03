import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import app.services.audit_service as audit_service
from app.models.enums import RiskActionStatus, RiskWorkflowStatus
from app.models.risk import RiskAction, RiskRecord
from app.models.user import User
from app.schemas.risk_action import (
    RiskActionCreate,
    RiskActionUpdate,
)
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    can_read_risk_record,
    validate_active_user,
)

RISK_ACTION_ENTITY_TYPE = "RiskAction"


class RiskActionNotFoundError(ValueError):
    pass


class RiskActionBusinessRuleError(ValueError):
    pass


def get_risk_action_due_status(
    action: RiskAction,
    *,
    today: date | None = None,
) -> str:
    if action.status == RiskActionStatus.COMPLETED:
        return "COMPLETED"
    if action.status == RiskActionStatus.CANCELLED:
        return "CANCELLED"
    if action.due_date is None:
        return "NO_DUE_DATE"

    current_date = today or date.today()
    if action.due_date < current_date:
        return "OVERDUE"
    if action.due_date == current_date:
        return "DUE_TODAY"
    if action.due_date <= current_date + timedelta(days=7):
        return "DUE_SOON"
    return "OPEN"


def is_action_open_for_alerts(action: RiskAction) -> bool:
    return action.status not in {
        RiskActionStatus.COMPLETED,
        RiskActionStatus.CANCELLED,
    }


def _validate_reader(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    context: str,
) -> User:
    try:
        return validate_active_user(db, user_id=user_id, context=context)
    except RiskAccessBusinessRuleError as exc:
        raise RiskActionBusinessRuleError(str(exc)) from exc


def _authorize_risk_read(
    db: Session,
    *,
    risk_record: RiskRecord,
    user_id: uuid.UUID,
    operation: str,
) -> None:
    if not can_read_risk_record(db, risk_record=risk_record, user_id=user_id):
        raise RiskActionBusinessRuleError(
            f"User is not authorized to {operation} Risk Actions for this risk"
        )


def _filter_action_statuses(
    actions: list[RiskAction],
    *,
    include_completed: bool,
    include_cancelled: bool,
) -> list[RiskAction]:
    return [
        action
        for action in actions
        if (include_completed or action.status != RiskActionStatus.COMPLETED)
        and (include_cancelled or action.status != RiskActionStatus.CANCELLED)
    ]


def _sort_risk_actions_by_urgency(actions: list[RiskAction]) -> list[RiskAction]:
    due_status_priority = {
        "OVERDUE": 0,
        "DUE_TODAY": 1,
        "DUE_SOON": 2,
        "OPEN": 3,
        "NO_DUE_DATE": 4,
        "COMPLETED": 5,
        "CANCELLED": 6,
    }
    return sorted(
        actions,
        key=lambda action: (
            due_status_priority[get_risk_action_due_status(action)],
            action.due_date is None,
            action.due_date or date.max,
            -(action.created_at.timestamp() if action.created_at else 0),
        ),
    )


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


def _validate_action_owner_user(
    db: Session,
    *,
    owner_user_id: uuid.UUID | None,
) -> None:
    if owner_user_id is None:
        return

    owner = db.get(User, owner_user_id)
    if owner is None:
        raise RiskActionBusinessRuleError("Risk action owner does not exist")
    if not owner.is_active:
        raise RiskActionBusinessRuleError("Risk action owner is inactive")


def _validate_action_actor(
    db: Session,
    *,
    action: RiskAction,
    actor_user_id: uuid.UUID | None,
    operation: str,
) -> None:
    if actor_user_id is None:
        raise RiskActionBusinessRuleError(
            "Risk action update requires an authenticated active user"
        )

    actor = db.get(User, actor_user_id)
    if actor is None:
        raise RiskActionBusinessRuleError("Risk action user does not exist")
    if not actor.is_active:
        raise RiskActionBusinessRuleError("Risk action user is inactive")
    if (
        action.action_owner_user_id is not None
        and action.action_owner_user_id != actor_user_id
    ):
        if operation == "complete":
            raise RiskActionBusinessRuleError(
                "Only the assigned action owner can complete this action"
            )
        raise RiskActionBusinessRuleError(
            "Only the assigned action owner can update this action"
        )


def create_risk_action(
    db: Session,
    *,
    data: RiskActionCreate,
    created_by_user_id: uuid.UUID | None = None,
) -> RiskAction:
    _get_actionable_risk_record(db, data.risk_record_id)
    _validate_title(data.title)
    _validate_action_owner_user(db, owner_user_id=data.action_owner_user_id)

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


def list_authorized_risk_actions(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
    risk_record_id: uuid.UUID | None = None,
    include_completed: bool = True,
    include_cancelled: bool = True,
) -> list[RiskAction]:
    reader = _validate_reader(
        db,
        user_id=requested_by_user_id,
        context="Risk Actions list access",
    )

    statement = select(RiskAction).options(selectinload(RiskAction.risk_record))
    if risk_record_id is not None:
        risk_record = db.get(RiskRecord, risk_record_id)
        if risk_record is None:
            raise RiskActionNotFoundError("Risk record not found")
        _authorize_risk_read(
            db,
            risk_record=risk_record,
            user_id=reader.id,
            operation="list",
        )
        statement = statement.where(RiskAction.risk_record_id == risk_record.id)

    actions = list(db.scalars(statement).all())
    if risk_record_id is None:
        actions = [
            action
            for action in actions
            if can_read_risk_record(
                db,
                risk_record=action.risk_record,
                user_id=reader.id,
            )
        ]

    return _sort_risk_actions_by_urgency(
        _filter_action_statuses(
            actions,
            include_completed=include_completed,
            include_cancelled=include_cancelled,
        )
    )


def get_authorized_risk_action(
    db: Session,
    *,
    risk_action_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> RiskAction | None:
    reader = _validate_reader(
        db,
        user_id=requested_by_user_id,
        context="Risk Action access",
    )
    action = db.scalar(
        select(RiskAction)
        .options(selectinload(RiskAction.risk_record))
        .where(RiskAction.id == risk_action_id)
    )
    if action is None:
        return None
    _authorize_risk_read(
        db,
        risk_record=action.risk_record,
        user_id=reader.id,
        operation="read",
    )
    return action


def get_my_risk_actions(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
    include_completed: bool = False,
    include_cancelled: bool = False,
) -> list[RiskAction]:
    reader = _validate_reader(
        db,
        user_id=requested_by_user_id,
        context="My Actions access",
    )
    actions = list(
        db.scalars(
            select(RiskAction).options(selectinload(RiskAction.risk_record))
        ).all()
    )
    readable_actions = [
        action
        for action in actions
        if can_read_risk_record(
            db,
            risk_record=action.risk_record,
            user_id=reader.id,
        )
    ]
    return _sort_risk_actions_by_urgency(
        _filter_action_statuses(
            readable_actions,
            include_completed=include_completed,
            include_cancelled=include_cancelled,
        )
    )


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

    _validate_action_actor(
        db,
        action=action,
        actor_user_id=changed_by_user_id,
        operation="update",
    )
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

    _validate_action_actor(
        db,
        action=action,
        actor_user_id=changed_by_user_id,
        operation="complete",
    )
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
