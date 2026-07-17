import uuid
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.electronic_approval import ElectronicApproval
from app.models.enums import (
    AuditAction,
    AuthorityLevel,
    CommitteeType,
    ElectronicApprovalTargetType,
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskDecision, RiskRecord
from app.models.user import User
from app.services.auth_service import create_access_token
from app.services.electronic_approval_service import compute_approval_hash


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, autoflush=False, autocommit=False)() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(db: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"electronic-approval-{uuid.uuid4()}@example.com",
        display_name="Electronic Approval User",
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"}


def _create_committee(
    db: Session,
    *,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    is_fixed: bool = False,
) -> Committee:
    committee_type = {
        AuthorityLevel.LOW: CommitteeType.OPERATIONAL_BOARD,
        AuthorityLevel.MIDDLE: CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        AuthorityLevel.HIGH: CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE,
    }[authority_level]
    committee = Committee(
        name=f"{authority_level.value} Electronic Approval {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=committee_type,
        is_fixed=is_fixed,
        is_active=True,
    )
    db.add(committee)
    db.flush()
    return committee


def _add_member(db: Session, *, committee: Committee, user: User) -> None:
    db.add(
        CommitteeMember(
            committee_id=committee.id,
            user_id=user.id,
            is_active=True,
        )
    )
    db.flush()


def _create_risk(
    db: Session,
    *,
    creator: User,
    board: Committee | None = None,
) -> RiskRecord:
    risk = RiskRecord(
        risk_id=f"RISK-EA-{uuid.uuid4().hex[:8]}",
        problem_description="Electronic approval test risk",
        domain=RiskDomain.FLIGHT_TEST,
        board_of_origin_id=board.id if board else None,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=creator.id,
        is_active=True,
    )
    db.add(risk)
    db.flush()
    return risk


def _create_decision(
    db: Session,
    *,
    risk: RiskRecord,
    committee: Committee,
    decided_by: User | None = None,
) -> RiskDecision:
    decision = RiskDecision(
        risk_record_id=risk.id,
        committee_id=committee.id,
        decision_type=RiskDecisionType.APPROVE,
        decision_text="Decision reviewed for electronic approval",
        decided_by_user_id=decided_by.id if decided_by else None,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(decision)
    db.flush()
    return decision


def _approve_risk(client: TestClient, user: User, risk: RiskRecord, statement: str = "Approved"):
    return client.post(
        "/electronic-approvals",
        headers=_headers(user),
        json={
            "target_type": "RISK_RECORD",
            "target_id": str(risk.id),
            "approval_statement": statement,
        },
    )


def test_authenticated_active_user_can_approve_readable_risk_record(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    db_session.commit()

    response = _approve_risk(client, user, risk, "I approve this risk record.")

    assert response.status_code == 201
    assert response.json()["target_type"] == "RISK_RECORD"
    assert response.json()["risk_record_id"] == str(risk.id)


def test_unauthenticated_user_cannot_create_approval(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    db_session.commit()

    response = client.post(
        "/electronic-approvals",
        json={
            "target_type": "RISK_RECORD",
            "target_id": str(risk.id),
            "approval_statement": "Approved",
        },
    )

    assert response.status_code == 401


def test_inactive_user_cannot_create_approval(
    client: TestClient,
    db_session: Session,
) -> None:
    inactive = _create_user(db_session, is_active=False)
    risk = _create_risk(db_session, creator=inactive)
    db_session.commit()

    response = _approve_risk(client, inactive, risk)

    assert response.status_code == 403


def test_approval_statement_cannot_be_blank(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    db_session.commit()

    response = _approve_risk(client, user, risk, "   ")

    assert response.status_code == 400
    assert "Approval statement" in response.json()["error"]["message"]


def test_approval_hash_is_created_and_stable(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    db_session.commit()

    body = _approve_risk(client, user, risk).json()
    approval = db_session.get(ElectronicApproval, uuid.UUID(body["id"]))

    assert body["approval_hash"]
    assert len(body["approval_hash"]) == 64
    assert approval is not None
    assert compute_approval_hash(approval) == body["approval_hash"]


def test_approval_read_returns_acknowledgement_and_meaning(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    db_session.commit()
    created = _approve_risk(client, user, risk).json()

    response = client.get(
        f"/electronic-approvals/{created['id']}",
        headers=_headers(user),
    )
    body = response.json()

    assert response.status_code == 200
    assert "controlled approval record" in body["acknowledgement_text"]
    assert "not a cryptographic digital signature" in body["acknowledgement_text"]
    assert "Authority Level" in body["meaning_of_signature"]


def test_approval_records_user_timestamp_and_authority_level(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    board = _create_committee(db_session, authority_level=AuthorityLevel.LOW)
    risk = _create_risk(db_session, creator=user, board=board)
    db_session.commit()

    body = _approve_risk(client, user, risk).json()

    assert body["approved_by_user_id"] == str(user.id)
    assert body["approved_at"]
    assert body["committee_id"] == str(board.id)
    assert body["authority_level"] == "LOW"


def test_user_cannot_approve_unreadable_risk_record(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    outsider = _create_user(db_session)
    risk = _create_risk(db_session, creator=creator)
    db_session.commit()

    response = _approve_risk(client, outsider, risk)

    assert response.status_code == 400
    assert "not authorized" in response.json()["error"]["message"]


def test_same_user_cannot_duplicate_approve_same_target(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    db_session.commit()

    first = _approve_risk(client, user, risk)
    duplicate = _approve_risk(client, user, risk)

    assert first.status_code == 201
    assert duplicate.status_code == 400
    assert "already approved" in duplicate.json()["error"]["message"]


def test_creator_can_list_approvals_for_readable_risk(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    db_session.commit()
    created = _approve_risk(client, user, risk).json()

    response = client.get(
        f"/electronic-approvals?risk_record_id={risk.id}",
        headers=_headers(user),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [created["id"]]


def test_unauthorized_user_cannot_list_approvals_for_unreadable_risk(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    outsider = _create_user(db_session)
    risk = _create_risk(db_session, creator=creator)
    db_session.commit()
    _approve_risk(client, creator, risk)

    response = client.get(
        f"/electronic-approvals?risk_record_id={risk.id}",
        headers=_headers(outsider),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_risk_decision_target_resolves_parent_context(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    decision_member = _create_user(db_session)
    committee = _create_committee(db_session, authority_level=AuthorityLevel.MIDDLE, is_fixed=True)
    _add_member(db_session, committee=committee, user=decision_member)
    risk = _create_risk(db_session, creator=creator)
    decision = _create_decision(
        db_session,
        risk=risk,
        committee=committee,
        decided_by=decision_member,
    )
    db_session.commit()

    response = client.post(
        "/electronic-approvals",
        headers=_headers(decision_member),
        json={
            "target_type": "RISK_DECISION",
            "target_id": str(decision.id),
            "approval_statement": "Decision reviewed and approved.",
        },
    )
    body = response.json()

    assert response.status_code == 201
    assert body["risk_record_id"] == str(risk.id)
    assert body["risk_decision_id"] == str(decision.id)
    assert body["committee_id"] == str(committee.id)
    assert body["authority_level"] == "MIDDLE"


def test_user_outside_decision_committee_cannot_approve_decision(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    decision_member = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee=committee, user=decision_member)
    risk = _create_risk(db_session, creator=creator, board=committee)
    decision = _create_decision(db_session, risk=risk, committee=committee)
    db_session.commit()

    response = client.post(
        "/electronic-approvals",
        headers=_headers(creator),
        json={
            "target_type": "RISK_DECISION",
            "target_id": str(decision.id),
            "approval_statement": "Decision approval attempt.",
        },
    )

    assert response.status_code == 400
    assert "Authority Level or committee" in response.json()["error"]["message"]


def test_committee_member_can_approve_decision_target(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    member = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee=committee, user=member)
    risk = _create_risk(db_session, creator=creator, board=committee)
    decision = _create_decision(db_session, risk=risk, committee=committee)
    db_session.commit()

    response = client.post(
        "/electronic-approvals",
        headers=_headers(member),
        json={
            "target_type": "RISK_DECISION",
            "target_id": str(decision.id),
            "approval_statement": "Committee decision approved.",
        },
    )

    assert response.status_code == 201


def test_electronic_approval_creation_writes_audit_log(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    db_session.commit()

    body = _approve_risk(client, user, risk).json()
    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(body["id"]),
            AuditLog.entity_type == "ElectronicApproval",
        )
    )

    assert audit_log is not None
    assert audit_log.action == AuditAction.ELECTRONIC_APPROVAL
    assert audit_log.changed_by_user_id == user.id


def test_electronic_approval_has_no_update_or_delete_endpoint(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    db_session.commit()
    approval_id = _approve_risk(client, user, risk).json()["id"]

    patch_response = client.patch(
        f"/electronic-approvals/{approval_id}",
        headers=_headers(user),
        json={"approval_statement": "Changed"},
    )
    delete_response = client.delete(
        f"/electronic-approvals/{approval_id}",
        headers=_headers(user),
    )

    assert patch_response.status_code == 405
    assert delete_response.status_code == 405


def test_list_filter_by_target_type_and_target_id_works(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    first = _create_risk(db_session, creator=user)
    second = _create_risk(db_session, creator=user)
    db_session.commit()
    target = _approve_risk(client, user, first).json()
    _approve_risk(client, user, second)

    response = client.get(
        f"/electronic-approvals?target_type=RISK_RECORD&target_id={first.id}",
        headers=_headers(user),
    )

    assert [item["id"] for item in response.json()] == [target["id"]]


def test_get_missing_approval_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    response = client.get(f"/electronic-approvals/{uuid.uuid4()}", headers=_headers(user))

    assert response.status_code == 404


def test_generated_report_target_returns_clear_mvp_unsupported_error(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    response = client.post(
        "/electronic-approvals",
        headers=_headers(user),
        json={
            "target_type": ElectronicApprovalTargetType.GENERATED_REPORT.value,
            "target_id": str(uuid.uuid4()),
            "approval_statement": "Approve generated report.",
        },
    )

    assert response.status_code == 400
    assert "Generated report approvals are not yet supported" in response.json()[
        "error"
    ]["message"]
