import uuid
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.committee import Committee
from app.models.enums import AuthorityLevel, CommitteeType

COMMITTEE_ENTITY_TYPE = "Committee"


class DefaultCommitteeDefinition(TypedDict):
    name: str
    description: str
    authority_level: AuthorityLevel
    committee_type: CommitteeType
    is_fixed: bool


DEFAULT_GOVERNANCE_COMMITTEES: list[DefaultCommitteeDefinition] = [
    {
        "name": "Flight Test Safety Committee - Operation",
        "description": "Operational board for flight test safety governance.",
        "authority_level": AuthorityLevel.LOW,
        "committee_type": CommitteeType.OPERATIONAL_BOARD,
        "is_fixed": False,
    },
    {
        "name": "Aircraft Safety Committee - Engineering Board",
        "description": "Operational board for aircraft engineering safety governance.",
        "authority_level": AuthorityLevel.LOW,
        "committee_type": CommitteeType.OPERATIONAL_BOARD,
        "is_fixed": False,
    },
    {
        "name": (
            "Industrial Safety Committee - Quality, Manufacturing, Production, "
            "Supply Chain, OHSE"
        ),
        "description": "Operational board for industrial safety governance.",
        "authority_level": AuthorityLevel.LOW,
        "committee_type": CommitteeType.OPERATIONAL_BOARD,
        "is_fixed": False,
    },
    {
        "name": "Risk Management Committee",
        "description": "Fixed middle-authority risk management governance committee.",
        "authority_level": AuthorityLevel.MIDDLE,
        "committee_type": CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        "is_fixed": True,
    },
    {
        "name": "Executive Safety Management Committee",
        "description": "Fixed high-authority executive safety governance committee.",
        "authority_level": AuthorityLevel.HIGH,
        "committee_type": CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE,
        "is_fixed": True,
    },
]


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


def get_default_committee_names() -> list[str]:
    return [committee["name"] for committee in DEFAULT_GOVERNANCE_COMMITTEES]


def seed_default_committees(
    db: Session,
    *,
    changed_by_user_id: uuid.UUID | None = None,
) -> list[Committee]:
    committees: list[Committee] = []

    for definition in DEFAULT_GOVERNANCE_COMMITTEES:
        existing_committee = db.scalar(
            select(Committee).where(Committee.name == definition["name"])
        )
        if existing_committee is not None:
            committees.append(existing_committee)
            continue

        committee = Committee(
            name=definition["name"],
            description=definition["description"],
            authority_level=definition["authority_level"],
            committee_type=definition["committee_type"],
            is_fixed=definition["is_fixed"],
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
        committees.append(committee)

    return committees
