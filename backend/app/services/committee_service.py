import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.committee import Committee
from app.models.enums import AuthorityLevel, CommitteeType
from app.schemas.committee import CommitteeCreate, CommitteeUpdate

COMMITTEE_ENTITY_TYPE = "Committee"


class CommitteeNotFoundError(ValueError):
    pass


class CommitteeBusinessRuleError(ValueError):
    pass


def _committee_snapshot(committee: Committee) -> dict[str, object]:
    return {
        "id": committee.id,
        "name": committee.name,
        "description": committee.description,
        "authority_level": committee.authority_level,
        "committee_type": committee.committee_type,
        "is_fixed": committee.is_fixed,
        "is_active": committee.is_active,
        "archived_at": committee.archived_at,
        "archive_reason": committee.archive_reason,
    }


def create_committee(
    db: Session,
    *,
    data: CommitteeCreate,
    changed_by_user_id: uuid.UUID | None = None,
) -> Committee:
    if data.authority_level != AuthorityLevel.LOW:
        raise CommitteeBusinessRuleError("Only LOW authority committees can be created")
    if data.committee_type != CommitteeType.OPERATIONAL_BOARD:
        raise CommitteeBusinessRuleError(
            "Only OPERATIONAL_BOARD committees can be created"
        )

    committee = Committee(
        name=data.name,
        description=data.description,
        authority_level=data.authority_level,
        committee_type=data.committee_type,
        is_fixed=False,
        is_active=True,
    )
    db.add(committee)
    db.flush()

    audit_service.log_entity_created(
        db,
        entity_type=COMMITTEE_ENTITY_TYPE,
        entity_id=committee.id,
        created_by_user_id=changed_by_user_id,
        new_value=_committee_snapshot(committee),
    )
    return committee


def get_committee(
    db: Session,
    *,
    committee_id: uuid.UUID,
) -> Committee | None:
    return db.get(Committee, committee_id)


def update_committee(
    db: Session,
    *,
    committee_id: uuid.UUID,
    data: CommitteeUpdate,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> Committee:
    committee = get_committee(db, committee_id=committee_id)
    if committee is None:
        raise CommitteeNotFoundError("Committee not found")

    update_data = data.model_dump(exclude_unset=True)
    if (
        committee.is_fixed
        and "name" in update_data
        and update_data["name"] != committee.name
    ):
        raise CommitteeBusinessRuleError("Fixed committee name cannot be changed")

    for field_name, new_value in update_data.items():
        old_value = getattr(committee, field_name)
        if old_value == new_value:
            continue

        setattr(committee, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=COMMITTEE_ENTITY_TYPE,
            entity_id=committee.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )

    db.add(committee)
    db.flush()
    return committee


def archive_committee(
    db: Session,
    *,
    committee_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None = None,
    archive_reason: str,
) -> Committee:
    committee = get_committee(db, committee_id=committee_id)
    if committee is None:
        raise CommitteeNotFoundError("Committee not found")
    if committee.is_fixed:
        raise CommitteeBusinessRuleError("Fixed committees cannot be archived")
    if committee.authority_level != AuthorityLevel.LOW:
        raise CommitteeBusinessRuleError("Only LOW committees can be archived")

    old_value = _committee_snapshot(committee)
    committee.is_active = False
    committee.archived_at = datetime.now(timezone.utc)
    committee.archived_by_user_id = changed_by_user_id
    committee.archive_reason = archive_reason
    new_value = _committee_snapshot(committee)

    audit_service.log_archive_action(
        db,
        entity_type=COMMITTEE_ENTITY_TYPE,
        entity_id=committee.id,
        changed_by_user_id=changed_by_user_id,
        old_value=old_value,
        new_value=new_value,
        reason=archive_reason,
    )
    db.add(committee)
    db.flush()
    return committee


def list_committees(
    db: Session,
    *,
    include_archived: bool = False,
) -> list[Committee]:
    statement = select(Committee).order_by(Committee.name)
    if not include_archived:
        statement = statement.where(Committee.is_active.is_(True))

    return list(db.scalars(statement).all())
