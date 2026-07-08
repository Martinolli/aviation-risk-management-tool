import uuid
from datetime import date

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.committee import Committee
from app.models.enums import (
    AuditAction,
    AuthorityLevel,
    CommitteeType,
    RiskAssessmentType,
    RiskActionStatus,
    RiskLifecycleStatus,
    RiskMonitoringStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskAssessment, RiskMonitoringReview, RiskRecord
from app.models.user import User
from app.schemas.risk import RiskRecordCreate, RiskRecordUpdate
from app.schemas.risk_search import RiskRecordListFilters
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    filter_readable_risk_records,
    validate_active_user,
)
from app.services.risk_numbering_service import generate_next_risk_id

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
    if (
        committee.authority_level != AuthorityLevel.LOW
        or committee.committee_type != CommitteeType.OPERATIONAL_BOARD
    ):
        raise RiskRecordBusinessRuleError(
            "Board of origin must be an active LOW operational board"
        )


def _validate_risk_actor(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    operation: str,
) -> User:
    if user_id is None:
        messages = {
            "create": "Risk record creation requires an authenticated active user",
            "update": "Risk record update requires an authenticated active user",
            "submit": "Risk record submission requires an authenticated active user",
        }
        raise RiskRecordBusinessRuleError(messages[operation])

    user = db.get(User, user_id)
    if user is None:
        raise RiskRecordBusinessRuleError("Risk record user does not exist")
    if not user.is_active:
        raise RiskRecordBusinessRuleError("Risk record user is inactive")
    return user


def _validate_risk_owner(
    db: Session,
    *,
    owner_user_id: uuid.UUID | None,
) -> None:
    if owner_user_id is None:
        return

    owner = db.get(User, owner_user_id)
    if owner is None:
        raise RiskRecordBusinessRuleError("Risk record owner does not exist")
    if not owner.is_active:
        raise RiskRecordBusinessRuleError("Risk record owner is inactive")


def _validate_risk_record_actor_authority(
    *,
    risk_record: RiskRecord,
    actor_user_id: uuid.UUID,
    operation: str,
) -> None:
    if (
        risk_record.owner_user_id is not None
        and risk_record.owner_user_id != actor_user_id
    ):
        if operation == "submit":
            raise RiskRecordBusinessRuleError(
                "Only the assigned risk owner can submit this risk record"
            )
        raise RiskRecordBusinessRuleError(
            "Only the assigned risk owner can update this risk record"
        )
    if (
        risk_record.owner_user_id is None
        and risk_record.created_by_user_id is not None
        and risk_record.created_by_user_id != actor_user_id
    ):
        if operation == "submit":
            raise RiskRecordBusinessRuleError(
                "Only the risk creator can submit this risk record"
            )
        raise RiskRecordBusinessRuleError(
            "Only the risk creator can update this risk record"
        )


def create_risk_record(
    db: Session,
    *,
    data: RiskRecordCreate,
    created_by_user_id: uuid.UUID | None = None,
) -> RiskRecord:
    _validate_problem_description(data.problem_description)
    _validate_board_of_origin(db, data.board_of_origin_id)
    _validate_risk_actor(db, user_id=created_by_user_id, operation="create")
    _validate_risk_owner(db, owner_user_id=data.owner_user_id)

    risk_record = RiskRecord(
        risk_id=generate_next_risk_id(db),
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


def _apply_risk_record_filters(statement, filters: RiskRecordListFilters):
    if filters.search:
        search_pattern = f"%{filters.search}%"
        statement = statement.where(
            or_(
                RiskRecord.risk_id.ilike(search_pattern),
                RiskRecord.problem_description.ilike(search_pattern),
                RiskRecord.source_trigger.ilike(search_pattern),
                RiskRecord.system_scope.ilike(search_pattern),
                RiskRecord.central_event.ilike(search_pattern),
                RiskRecord.hazard_statement.ilike(search_pattern),
            )
        )
    if filters.risk_id:
        statement = statement.where(RiskRecord.risk_id.ilike(f"%{filters.risk_id}%"))
    if filters.domain is not None:
        statement = statement.where(RiskRecord.domain == filters.domain)
    if filters.board_of_origin_id is not None:
        statement = statement.where(
            RiskRecord.board_of_origin_id == filters.board_of_origin_id
        )
    if filters.workflow_status is not None:
        statement = statement.where(RiskRecord.workflow_status == filters.workflow_status)
    if filters.lifecycle_status is not None:
        statement = statement.where(
            RiskRecord.lifecycle_status == filters.lifecycle_status
        )
    if filters.owner_user_id is not None:
        statement = statement.where(RiskRecord.owner_user_id == filters.owner_user_id)
    if filters.created_by_user_id is not None:
        statement = statement.where(
            RiskRecord.created_by_user_id == filters.created_by_user_id
        )
    if filters.latest_risk_level:
        latest_assessment_times = (
            select(
                RiskAssessment.risk_record_id,
                func.max(RiskAssessment.assessed_at).label("latest_assessed_at"),
            )
            .group_by(RiskAssessment.risk_record_id)
            .subquery()
        )
        latest_matching_risk_ids = (
            select(RiskAssessment.risk_record_id)
            .join(
                latest_assessment_times,
                (RiskAssessment.risk_record_id == latest_assessment_times.c.risk_record_id)
                & (
                    RiskAssessment.assessed_at
                    == latest_assessment_times.c.latest_assessed_at
                ),
            )
            .where(func.lower(RiskAssessment.risk_level) == filters.latest_risk_level.lower())
        )
        statement = statement.where(RiskRecord.id.in_(latest_matching_risk_ids))
    if filters.has_overdue_actions is not None:
        overdue_open_action_exists = exists().where(
            RiskAction.risk_record_id == RiskRecord.id,
            RiskAction.status.in_(
                [RiskActionStatus.OPEN, RiskActionStatus.IN_PROGRESS]
            ),
            RiskAction.due_date < date.today(),
        )
        statement = statement.where(
            overdue_open_action_exists
            if filters.has_overdue_actions
            else ~overdue_open_action_exists
        )
    if filters.has_due_or_overdue_monitoring is not None:
        due_or_overdue_monitoring_exists = exists().where(
            RiskMonitoringReview.risk_record_id == RiskRecord.id,
            RiskMonitoringReview.is_active.is_(True),
            RiskMonitoringReview.status.in_(
                [RiskMonitoringStatus.DUE, RiskMonitoringStatus.OVERDUE]
            ),
        )
        statement = statement.where(
            due_or_overdue_monitoring_exists
            if filters.has_due_or_overdue_monitoring
            else ~due_or_overdue_monitoring_exists
        )

    return statement


def _apply_risk_record_sorting(statement, filters: RiskRecordListFilters | None):
    sort_by = filters.sort_by if filters is not None else "updated_at"
    sort_direction = filters.sort_direction if filters is not None else "desc"
    sort_column = {
        "risk_id": RiskRecord.risk_id,
        "created_at": RiskRecord.created_at,
        "updated_at": RiskRecord.updated_at,
        "domain": RiskRecord.domain,
        "workflow_status": RiskRecord.workflow_status,
        "lifecycle_status": RiskRecord.lifecycle_status,
    }[sort_by]
    order_expression = (
        sort_column.asc() if sort_direction == "asc" else sort_column.desc()
    )
    return statement.order_by(order_expression, RiskRecord.created_at.desc())


def list_risk_records(
    db: Session,
    *,
    include_archived: bool = False,
    filters: RiskRecordListFilters | None = None,
) -> list[RiskRecord]:
    effective_include_archived = include_archived or (
        filters.include_archived if filters is not None else False
    )
    statement = select(RiskRecord)
    if not effective_include_archived:
        statement = statement.where(RiskRecord.is_active.is_(True))
    if filters is not None:
        statement = _apply_risk_record_filters(statement, filters)
    statement = _apply_risk_record_sorting(statement, filters)

    return list(db.scalars(statement).all())


def list_authorized_risk_records(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
    include_archived: bool = False,
    filters: RiskRecordListFilters | None = None,
) -> list[RiskRecord]:
    try:
        reader = validate_active_user(
            db,
            user_id=requested_by_user_id,
            context="Risk list access",
        )
    except RiskAccessBusinessRuleError as exc:
        raise RiskRecordBusinessRuleError(str(exc)) from exc

    risk_records = list_risk_records(
        db,
        include_archived=include_archived,
        filters=filters,
    )
    return filter_readable_risk_records(
        db,
        risk_records=risk_records,
        user_id=reader.id,
    )


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
    _validate_risk_actor(db, user_id=changed_by_user_id, operation="update")
    _validate_risk_record_actor_authority(
        risk_record=risk_record,
        actor_user_id=changed_by_user_id,
        operation="update",
    )
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


def _has_recorded_text(value: str | None) -> bool:
    return bool(value and value.strip())


def get_risk_submission_readiness(
    db: Session,
    *,
    risk_record: RiskRecord,
) -> dict[str, object]:
    initial_assessment_exists = db.scalar(
        select(RiskAssessment.id).where(
            RiskAssessment.risk_record_id == risk_record.id,
            RiskAssessment.assessment_type == RiskAssessmentType.INITIAL,
        )
    ) is not None
    checks = {
        "board_of_origin": risk_record.board_of_origin_id is not None,
        "system_scope": _has_recorded_text(risk_record.system_scope),
        "central_event": _has_recorded_text(risk_record.central_event),
        "hazard_statement": _has_recorded_text(risk_record.hazard_statement),
        "initial_assessment": initial_assessment_exists,
    }
    labels = {
        "board_of_origin": "Board of Origin / Originating Committee",
        "system_scope": "System Scope",
        "central_event": "Central Event",
        "hazard_statement": "Hazard Statement",
        "initial_assessment": "Initial Risk Assessment",
    }
    missing_items = [label for key, label in labels.items() if not checks[key]]
    return {
        "is_ready": not missing_items,
        "missing_items": missing_items,
        "checks": checks,
    }


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
    _validate_risk_actor(db, user_id=changed_by_user_id, operation="submit")
    _validate_risk_record_actor_authority(
        risk_record=risk_record,
        actor_user_id=changed_by_user_id,
        operation="submit",
    )
    if not risk_record.is_active:
        raise RiskRecordBusinessRuleError("Archived or inactive risks cannot be submitted")
    if risk_record.workflow_status != RiskWorkflowStatus.DRAFT:
        raise RiskRecordBusinessRuleError("Only DRAFT risks can be submitted")
    readiness = get_risk_submission_readiness(db, risk_record=risk_record)
    if not readiness["is_ready"]:
        missing_items = ", ".join(readiness["missing_items"])
        raise RiskRecordBusinessRuleError(
            "Risk cannot be submitted until the risk package and initial assessment "
            f"are complete. Missing: {missing_items}."
        )

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
