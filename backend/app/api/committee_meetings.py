import uuid

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.committee_meeting import CommitteeMeeting
from app.models.enums import CommitteeMeetingStatus
from app.models.user import User
from app.schemas.committee_meeting import (
    CommitteeMeetingAttendeeCreate,
    CommitteeMeetingAttendeeUpdate,
    CommitteeMeetingCancel,
    CommitteeMeetingCreate,
    CommitteeMeetingFinalize,
    CommitteeMeetingRead,
    CommitteeMeetingRiskItemCreate,
    CommitteeMeetingRiskItemUpdate,
    CommitteeMeetingUpdate,
)
from app.services.committee_meeting_service import (
    CommitteeMeetingBusinessRuleError,
    CommitteeMeetingNotFoundError,
    add_committee_meeting_attendee,
    add_committee_meeting_risk_item,
    cancel_committee_meeting,
    create_committee_meeting,
    finalize_committee_meeting,
    get_committee_meeting,
    list_committee_meetings,
    remove_committee_meeting_attendee,
    remove_committee_meeting_risk_item,
    update_committee_meeting,
    update_committee_meeting_attendee,
    update_committee_meeting_risk_item,
)

router = APIRouter(prefix="/committee-meetings", tags=["committee-meetings"])


def _commit_and_refresh(
    db: Session,
    meeting: CommitteeMeeting,
    requested_by_user_id: uuid.UUID | None,
) -> CommitteeMeeting:
    db.commit()
    refreshed = get_committee_meeting(
        db,
        meeting_id=meeting.id,
        requested_by_user_id=requested_by_user_id,
    )
    return refreshed or meeting


def _current_user_id(current_user: User | None) -> uuid.UUID | None:
    return get_optional_current_user_id(current_user)


@router.get("", response_model=list[CommitteeMeetingRead])
def list_committee_meetings_endpoint(
    committee_id: uuid.UUID | None = None,
    status: CommitteeMeetingStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return list_committee_meetings(
            db,
            requested_by_user_id=_current_user_id(current_user),
            committee_id=committee_id,
            status=status,
        )
    except CommitteeMeetingBusinessRuleError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=CommitteeMeetingRead,
    status_code=http_status.HTTP_201_CREATED,
)
def create_committee_meeting_endpoint(
    data: CommitteeMeetingCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = create_committee_meeting(
            db,
            data=data,
            created_by_user_id=_current_user_id(current_user),
        )
        db.commit()
        return get_committee_meeting(
            db,
            meeting_id=meeting.id,
            requested_by_user_id=_current_user_id(current_user),
        )
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{meeting_id}", response_model=CommitteeMeetingRead)
def get_committee_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = get_committee_meeting(
            db,
            meeting_id=meeting_id,
            requested_by_user_id=_current_user_id(current_user),
        )
        if meeting is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Committee Meeting Minutes not found",
            )
        return meeting
    except CommitteeMeetingBusinessRuleError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch("/{meeting_id}", response_model=CommitteeMeetingRead)
def update_committee_meeting_endpoint(
    meeting_id: uuid.UUID,
    data: CommitteeMeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = update_committee_meeting(
            db,
            meeting_id=meeting_id,
            data=data,
            changed_by_user_id=_current_user_id(current_user),
        )
        return _commit_and_refresh(db, meeting, _current_user_id(current_user))
    except CommitteeMeetingNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{meeting_id}/finalize", response_model=CommitteeMeetingRead)
def finalize_committee_meeting_endpoint(
    meeting_id: uuid.UUID,
    data: CommitteeMeetingFinalize,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = finalize_committee_meeting(
            db,
            meeting_id=meeting_id,
            data=data,
            finalized_by_user_id=_current_user_id(current_user),
        )
        return _commit_and_refresh(db, meeting, _current_user_id(current_user))
    except CommitteeMeetingNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{meeting_id}/cancel", response_model=CommitteeMeetingRead)
def cancel_committee_meeting_endpoint(
    meeting_id: uuid.UUID,
    data: CommitteeMeetingCancel,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = cancel_committee_meeting(
            db,
            meeting_id=meeting_id,
            data=data,
            cancelled_by_user_id=_current_user_id(current_user),
        )
        return _commit_and_refresh(db, meeting, _current_user_id(current_user))
    except CommitteeMeetingNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{meeting_id}/attendees", response_model=CommitteeMeetingRead)
def add_committee_meeting_attendee_endpoint(
    meeting_id: uuid.UUID,
    data: CommitteeMeetingAttendeeCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = add_committee_meeting_attendee(
            db,
            meeting_id=meeting_id,
            data=data,
            changed_by_user_id=_current_user_id(current_user),
        )
        return _commit_and_refresh(db, meeting, _current_user_id(current_user))
    except CommitteeMeetingNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
    "/{meeting_id}/attendees/{attendee_id}",
    response_model=CommitteeMeetingRead,
)
def update_committee_meeting_attendee_endpoint(
    meeting_id: uuid.UUID,
    attendee_id: uuid.UUID,
    data: CommitteeMeetingAttendeeUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = update_committee_meeting_attendee(
            db,
            meeting_id=meeting_id,
            attendee_id=attendee_id,
            data=data,
            changed_by_user_id=_current_user_id(current_user),
        )
        return _commit_and_refresh(db, meeting, _current_user_id(current_user))
    except CommitteeMeetingNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete(
    "/{meeting_id}/attendees/{attendee_id}",
    response_model=CommitteeMeetingRead,
)
def remove_committee_meeting_attendee_endpoint(
    meeting_id: uuid.UUID,
    attendee_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = remove_committee_meeting_attendee(
            db,
            meeting_id=meeting_id,
            attendee_id=attendee_id,
            changed_by_user_id=_current_user_id(current_user),
        )
        return _commit_and_refresh(db, meeting, _current_user_id(current_user))
    except CommitteeMeetingNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{meeting_id}/risk-items", response_model=CommitteeMeetingRead)
def add_committee_meeting_risk_item_endpoint(
    meeting_id: uuid.UUID,
    data: CommitteeMeetingRiskItemCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = add_committee_meeting_risk_item(
            db,
            meeting_id=meeting_id,
            data=data,
            changed_by_user_id=_current_user_id(current_user),
        )
        return _commit_and_refresh(db, meeting, _current_user_id(current_user))
    except CommitteeMeetingNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
    "/{meeting_id}/risk-items/{risk_item_id}",
    response_model=CommitteeMeetingRead,
)
def update_committee_meeting_risk_item_endpoint(
    meeting_id: uuid.UUID,
    risk_item_id: uuid.UUID,
    data: CommitteeMeetingRiskItemUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = update_committee_meeting_risk_item(
            db,
            meeting_id=meeting_id,
            risk_item_id=risk_item_id,
            data=data,
            changed_by_user_id=_current_user_id(current_user),
        )
        return _commit_and_refresh(db, meeting, _current_user_id(current_user))
    except CommitteeMeetingNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete(
    "/{meeting_id}/risk-items/{risk_item_id}",
    response_model=CommitteeMeetingRead,
)
def remove_committee_meeting_risk_item_endpoint(
    meeting_id: uuid.UUID,
    risk_item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        meeting = remove_committee_meeting_risk_item(
            db,
            meeting_id=meeting_id,
            risk_item_id=risk_item_id,
            changed_by_user_id=_current_user_id(current_user),
        )
        return _commit_and_refresh(db, meeting, _current_user_id(current_user))
    except CommitteeMeetingNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommitteeMeetingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
