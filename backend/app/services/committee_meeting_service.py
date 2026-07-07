import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import app.services.audit_service as audit_service
from app.models.committee import Committee
from app.models.committee_meeting import (
    CommitteeMeeting,
    CommitteeMeetingAttendee,
    CommitteeMeetingRiskItem,
)
from app.models.enums import CommitteeMeetingStatus
from app.models.risk import RiskDecision, RiskRecord
from app.models.user import User
from app.schemas.committee_meeting import (
    CommitteeMeetingAttendeeCreate,
    CommitteeMeetingAttendeeUpdate,
    CommitteeMeetingCancel,
    CommitteeMeetingCreate,
    CommitteeMeetingFinalize,
    CommitteeMeetingRiskItemCreate,
    CommitteeMeetingRiskItemUpdate,
    CommitteeMeetingUpdate,
)
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    can_read_risk_record,
    is_active_committee_member,
    validate_active_user,
)

COMMITTEE_MEETING_ENTITY_TYPE = "CommitteeMeeting"


class CommitteeMeetingNotFoundError(ValueError):
    pass


class CommitteeMeetingBusinessRuleError(ValueError):
    pass


def _load_meeting(db: Session, meeting_id: uuid.UUID) -> CommitteeMeeting | None:
    return db.scalar(
        select(CommitteeMeeting)
        .options(
            selectinload(CommitteeMeeting.committee),
            selectinload(CommitteeMeeting.attendees),
            selectinload(CommitteeMeeting.risk_items).selectinload(
                CommitteeMeetingRiskItem.risk_record
            ),
            selectinload(CommitteeMeeting.risk_items).selectinload(
                CommitteeMeetingRiskItem.linked_risk_decision
            ),
        )
        .where(CommitteeMeeting.id == meeting_id)
    )


def _validate_actor(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    context: str,
) -> User:
    try:
        return validate_active_user(db, user_id=user_id, context=context)
    except RiskAccessBusinessRuleError as exc:
        raise CommitteeMeetingBusinessRuleError(str(exc)) from exc


def _validate_active_committee(db: Session, committee_id: uuid.UUID) -> Committee:
    committee = db.get(Committee, committee_id)
    if committee is None:
        raise CommitteeMeetingBusinessRuleError("Committee does not exist")
    if not committee.is_active:
        raise CommitteeMeetingBusinessRuleError("Committee is inactive")
    return committee


def _validate_committee_member(
    db: Session,
    *,
    committee_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    if not is_active_committee_member(
        db,
        committee_id=committee_id,
        user_id=user_id,
    ):
        raise CommitteeMeetingBusinessRuleError(
            "User is not an active member of this committee"
        )


def _validate_meeting_access(
    db: Session,
    *,
    meeting: CommitteeMeeting,
    user_id: uuid.UUID,
) -> None:
    _validate_committee_member(db, committee_id=meeting.committee_id, user_id=user_id)


def _validate_draft(meeting: CommitteeMeeting) -> None:
    if meeting.status != CommitteeMeetingStatus.DRAFT:
        raise CommitteeMeetingBusinessRuleError(
            "Only DRAFT meeting minutes can be modified"
        )


def _validate_active_user_reference(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    field_name: str,
) -> None:
    if user_id is None:
        return
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise CommitteeMeetingBusinessRuleError(f"{field_name} must be an active user")


def _validate_readable_risk(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    user_id: uuid.UUID,
) -> RiskRecord:
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        raise CommitteeMeetingBusinessRuleError("Risk record does not exist")
    if not can_read_risk_record(db, risk_record=risk_record, user_id=user_id):
        raise CommitteeMeetingBusinessRuleError(
            "User is not authorized to read linked risk"
        )
    return risk_record


def _validate_linked_decision(
    db: Session,
    *,
    linked_risk_decision_id: uuid.UUID | None,
    risk_record_id: uuid.UUID,
    committee_id: uuid.UUID,
) -> None:
    if linked_risk_decision_id is None:
        return
    decision = db.get(RiskDecision, linked_risk_decision_id)
    if decision is None:
        raise CommitteeMeetingBusinessRuleError("Linked Decision Record does not exist")
    if decision.risk_record_id != risk_record_id:
        raise CommitteeMeetingBusinessRuleError(
            "Linked Decision Record must belong to the same risk"
        )
    if decision.committee_id != committee_id:
        raise CommitteeMeetingBusinessRuleError(
            "Linked Decision Record must belong to the same committee"
        )


def _validate_attendee_identity(
    *,
    user_id: uuid.UUID | None,
    attendee_name: str | None,
) -> None:
    if user_id is None and not (attendee_name or "").strip():
        raise CommitteeMeetingBusinessRuleError(
            "Either user_id or attendee_name must be provided"
        )


def _meeting_snapshot(meeting: CommitteeMeeting) -> dict[str, Any]:
    return {
        "id": meeting.id,
        "committee_id": meeting.committee_id,
        "title": meeting.title,
        "meeting_date": meeting.meeting_date,
        "status": meeting.status,
        "attendee_count": len(meeting.attendees),
        "risk_item_count": len(meeting.risk_items),
    }


def create_committee_meeting(
    db: Session,
    *,
    data: CommitteeMeetingCreate,
    created_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=created_by_user_id,
        context="Committee Meeting Minutes creation",
    )
    committee = _validate_active_committee(db, data.committee_id)
    _validate_committee_member(db, committee_id=committee.id, user_id=actor.id)
    if not data.title.strip():
        raise CommitteeMeetingBusinessRuleError("Meeting title cannot be empty")
    _validate_active_user_reference(
        db,
        user_id=data.chair_user_id,
        field_name="chair_user_id",
    )

    for attendee_data in data.attendees:
        _validate_active_user_reference(
            db,
            user_id=attendee_data.user_id,
            field_name="attendee user_id",
        )
    for risk_item_data in data.risk_items:
        _validate_readable_risk(
            db,
            risk_record_id=risk_item_data.risk_record_id,
            user_id=actor.id,
        )
        _validate_linked_decision(
            db,
            linked_risk_decision_id=risk_item_data.linked_risk_decision_id,
            risk_record_id=risk_item_data.risk_record_id,
            committee_id=committee.id,
        )

    meeting = CommitteeMeeting(
        committee_id=committee.id,
        title=data.title.strip(),
        meeting_date=data.meeting_date,
        meeting_time_utc=data.meeting_time_utc,
        location=data.location,
        chair_user_id=data.chair_user_id,
        created_by_user_id=actor.id,
        status=CommitteeMeetingStatus.DRAFT,
        agenda_summary=data.agenda_summary,
        discussion_summary=data.discussion_summary,
        decisions_summary=data.decisions_summary,
        action_items_summary=data.action_items_summary,
        attendees=[
            CommitteeMeetingAttendee(**attendee.model_dump())
            for attendee in data.attendees
        ],
        risk_items=[
            CommitteeMeetingRiskItem(**risk_item.model_dump())
            for risk_item in data.risk_items
        ],
    )
    db.add(meeting)
    db.flush()
    audit_service.log_entity_created(
        db,
        entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
        entity_id=meeting.id,
        created_by_user_id=actor.id,
        new_value=_meeting_snapshot(meeting),
    )
    db.refresh(meeting)
    return _load_meeting(db, meeting.id) or meeting


def get_committee_meeting(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting | None:
    actor = _validate_actor(
        db,
        user_id=requested_by_user_id,
        context="Committee Meeting Minutes read",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        return None
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    return meeting


def list_committee_meetings(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
    committee_id: uuid.UUID | None = None,
    status: CommitteeMeetingStatus | None = None,
) -> list[CommitteeMeeting]:
    actor = _validate_actor(
        db,
        user_id=requested_by_user_id,
        context="Committee Meeting Minutes list",
    )
    statement = (
        select(CommitteeMeeting)
        .join(Committee, CommitteeMeeting.committee_id == Committee.id)
        .where(Committee.is_active.is_(True))
        .options(
            selectinload(CommitteeMeeting.committee),
            selectinload(CommitteeMeeting.attendees),
            selectinload(CommitteeMeeting.risk_items).selectinload(
                CommitteeMeetingRiskItem.risk_record
            ),
        )
        .order_by(
            CommitteeMeeting.meeting_date.desc(),
            CommitteeMeeting.created_at.desc(),
        )
    )
    if committee_id is not None:
        statement = statement.where(CommitteeMeeting.committee_id == committee_id)
    if status is not None:
        statement = statement.where(CommitteeMeeting.status == status)
    meetings = list(db.scalars(statement).all())
    return [
        meeting
        for meeting in meetings
        if is_active_committee_member(
            db,
            committee_id=meeting.committee_id,
            user_id=actor.id,
        )
    ]


def update_committee_meeting(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    data: CommitteeMeetingUpdate,
    changed_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=changed_by_user_id,
        context="Committee Meeting Minutes update",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        raise CommitteeMeetingNotFoundError("Committee Meeting Minutes not found")
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    _validate_draft(meeting)
    update_data = data.model_dump(exclude_unset=True)
    if "title" in update_data and not (update_data["title"] or "").strip():
        raise CommitteeMeetingBusinessRuleError("Meeting title cannot be empty")
    if "chair_user_id" in update_data:
        _validate_active_user_reference(
            db,
            user_id=update_data["chair_user_id"],
            field_name="chair_user_id",
        )
    for field_name, new_value in update_data.items():
        if field_name == "title" and isinstance(new_value, str):
            new_value = new_value.strip()
        old_value = getattr(meeting, field_name)
        if old_value == new_value:
            continue
        setattr(meeting, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
            entity_id=meeting.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=actor.id,
        )
    db.add(meeting)
    db.flush()
    return _load_meeting(db, meeting.id) or meeting


def add_committee_meeting_attendee(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    data: CommitteeMeetingAttendeeCreate,
    changed_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=changed_by_user_id,
        context="Committee Meeting Minutes attendance update",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        raise CommitteeMeetingNotFoundError("Committee Meeting Minutes not found")
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    _validate_draft(meeting)
    _validate_active_user_reference(
        db,
        user_id=data.user_id,
        field_name="attendee user_id",
    )
    attendee = CommitteeMeetingAttendee(meeting_id=meeting.id, **data.model_dump())
    db.add(attendee)
    db.flush()
    audit_service.log_change(
        db,
        entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
        entity_id=meeting.id,
        field_name="Attendance",
        old_value=None,
        new_value=data.model_dump(),
        changed_by_user_id=actor.id,
    )
    return _load_meeting(db, meeting.id) or meeting


def update_committee_meeting_attendee(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    attendee_id: uuid.UUID,
    data: CommitteeMeetingAttendeeUpdate,
    changed_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=changed_by_user_id,
        context="Committee Meeting Minutes attendance update",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        raise CommitteeMeetingNotFoundError("Committee Meeting Minutes not found")
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    _validate_draft(meeting)
    attendee = next((item for item in meeting.attendees if item.id == attendee_id), None)
    if attendee is None:
        raise CommitteeMeetingNotFoundError("Attendance record not found")
    update_data = data.model_dump(exclude_unset=True)
    if "user_id" in update_data:
        _validate_active_user_reference(
            db,
            user_id=update_data["user_id"],
            field_name="attendee user_id",
        )
    next_user_id = update_data.get("user_id", attendee.user_id)
    next_name = update_data.get("attendee_name", attendee.attendee_name)
    _validate_attendee_identity(user_id=next_user_id, attendee_name=next_name)
    for field_name, new_value in update_data.items():
        old_value = getattr(attendee, field_name)
        if old_value == new_value:
            continue
        setattr(attendee, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
            entity_id=meeting.id,
            field_name=f"Attendance.{field_name}",
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=actor.id,
        )
    db.add(attendee)
    db.flush()
    return _load_meeting(db, meeting.id) or meeting


def remove_committee_meeting_attendee(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    attendee_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=changed_by_user_id,
        context="Committee Meeting Minutes attendance update",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        raise CommitteeMeetingNotFoundError("Committee Meeting Minutes not found")
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    _validate_draft(meeting)
    attendee = next((item for item in meeting.attendees if item.id == attendee_id), None)
    if attendee is None:
        raise CommitteeMeetingNotFoundError("Attendance record not found")
    audit_service.log_change(
        db,
        entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
        entity_id=meeting.id,
        field_name="Attendance",
        old_value={"id": attendee.id},
        new_value=None,
        changed_by_user_id=actor.id,
    )
    db.delete(attendee)
    db.flush()
    return _load_meeting(db, meeting.id) or meeting


def add_committee_meeting_risk_item(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    data: CommitteeMeetingRiskItemCreate,
    changed_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=changed_by_user_id,
        context="Committee Meeting Minutes risk item update",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        raise CommitteeMeetingNotFoundError("Committee Meeting Minutes not found")
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    _validate_draft(meeting)
    _validate_readable_risk(
        db,
        risk_record_id=data.risk_record_id,
        user_id=actor.id,
    )
    _validate_linked_decision(
        db,
        linked_risk_decision_id=data.linked_risk_decision_id,
        risk_record_id=data.risk_record_id,
        committee_id=meeting.committee_id,
    )
    risk_item = CommitteeMeetingRiskItem(meeting_id=meeting.id, **data.model_dump())
    db.add(risk_item)
    db.flush()
    audit_service.log_change(
        db,
        entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
        entity_id=meeting.id,
        field_name="Agenda Item",
        old_value=None,
        new_value=data.model_dump(),
        changed_by_user_id=actor.id,
    )
    return _load_meeting(db, meeting.id) or meeting


def update_committee_meeting_risk_item(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    risk_item_id: uuid.UUID,
    data: CommitteeMeetingRiskItemUpdate,
    changed_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=changed_by_user_id,
        context="Committee Meeting Minutes risk item update",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        raise CommitteeMeetingNotFoundError("Committee Meeting Minutes not found")
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    _validate_draft(meeting)
    risk_item = next(
        (item for item in meeting.risk_items if item.id == risk_item_id),
        None,
    )
    if risk_item is None:
        raise CommitteeMeetingNotFoundError("Agenda Item not found")
    update_data = data.model_dump(exclude_unset=True)
    next_decision_id = update_data.get(
        "linked_risk_decision_id",
        risk_item.linked_risk_decision_id,
    )
    _validate_linked_decision(
        db,
        linked_risk_decision_id=next_decision_id,
        risk_record_id=risk_item.risk_record_id,
        committee_id=meeting.committee_id,
    )
    for field_name, new_value in update_data.items():
        old_value = getattr(risk_item, field_name)
        if old_value == new_value:
            continue
        setattr(risk_item, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
            entity_id=meeting.id,
            field_name=f"Agenda Item.{field_name}",
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=actor.id,
        )
    db.add(risk_item)
    db.flush()
    return _load_meeting(db, meeting.id) or meeting


def remove_committee_meeting_risk_item(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    risk_item_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=changed_by_user_id,
        context="Committee Meeting Minutes risk item update",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        raise CommitteeMeetingNotFoundError("Committee Meeting Minutes not found")
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    _validate_draft(meeting)
    risk_item = next(
        (item for item in meeting.risk_items if item.id == risk_item_id),
        None,
    )
    if risk_item is None:
        raise CommitteeMeetingNotFoundError("Agenda Item not found")
    audit_service.log_change(
        db,
        entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
        entity_id=meeting.id,
        field_name="Agenda Item",
        old_value={"id": risk_item.id, "risk_record_id": risk_item.risk_record_id},
        new_value=None,
        changed_by_user_id=actor.id,
    )
    db.delete(risk_item)
    db.flush()
    return _load_meeting(db, meeting.id) or meeting


def finalize_committee_meeting(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    data: CommitteeMeetingFinalize,
    finalized_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=finalized_by_user_id,
        context="Committee Meeting Minutes finalization",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        raise CommitteeMeetingNotFoundError("Committee Meeting Minutes not found")
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    _validate_draft(meeting)
    if not meeting.attendees:
        raise CommitteeMeetingBusinessRuleError(
            "Meeting Minutes cannot be finalized without Attendance"
        )

    old_status = meeting.status
    meeting.status = CommitteeMeetingStatus.FINALIZED
    meeting.finalized_at = datetime.now(timezone.utc)
    meeting.finalized_by_user_id = actor.id
    if data.finalization_notes:
        existing = meeting.action_items_summary or ""
        separator = "\n\n" if existing else ""
        meeting.action_items_summary = (
            f"{existing}{separator}Finalization notes: {data.finalization_notes}"
        )
    audit_service.log_change(
        db,
        entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
        entity_id=meeting.id,
        field_name="status",
        old_value=old_status,
        new_value=meeting.status,
        changed_by_user_id=actor.id,
    )
    db.add(meeting)
    db.flush()
    return _load_meeting(db, meeting.id) or meeting


def cancel_committee_meeting(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    data: CommitteeMeetingCancel,
    cancelled_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    actor = _validate_actor(
        db,
        user_id=cancelled_by_user_id,
        context="Committee Meeting Minutes cancellation",
    )
    meeting = _load_meeting(db, meeting_id)
    if meeting is None:
        raise CommitteeMeetingNotFoundError("Committee Meeting Minutes not found")
    _validate_meeting_access(db, meeting=meeting, user_id=actor.id)
    if meeting.status == CommitteeMeetingStatus.FINALIZED:
        raise CommitteeMeetingBusinessRuleError(
            "FINALIZED meeting minutes cannot be cancelled"
        )
    if meeting.status == CommitteeMeetingStatus.CANCELLED:
        raise CommitteeMeetingBusinessRuleError(
            "Committee Meeting Minutes are already CANCELLED"
        )
    old_status = meeting.status
    meeting.status = CommitteeMeetingStatus.CANCELLED
    meeting.cancellation_reason = data.cancellation_reason
    audit_service.log_change(
        db,
        entity_type=COMMITTEE_MEETING_ENTITY_TYPE,
        entity_id=meeting.id,
        field_name="status",
        old_value=old_status,
        new_value=meeting.status,
        changed_by_user_id=actor.id,
        reason=data.cancellation_reason,
    )
    db.add(meeting)
    db.flush()
    return _load_meeting(db, meeting.id) or meeting
