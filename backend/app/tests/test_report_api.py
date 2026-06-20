import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path

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
from app.models.enums import (
    AuditAction,
    AuthorityLevel,
    CommitteeType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.report import GeneratedReport
from app.models.risk import RiskRecord
from app.models.user import User


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
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


def _create_risk_record(
    db_session: Session,
    *,
    risk_id: str = "RISK-2026-0001",
    creator: User | None = None,
    owner: User | None = None,
    board_of_origin_id: uuid.UUID | None = None,
) -> RiskRecord:
    creator = creator or _create_user(db_session)
    risk_record = RiskRecord(
        risk_id=risk_id,
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=creator.id,
        owner_user_id=owner.id if owner is not None else None,
        board_of_origin_id=board_of_origin_id,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.commit()
    db_session.refresh(risk_record)
    return risk_record


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Report User",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_committee(
    db_session: Session,
    *,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    is_active: bool = True,
    is_fixed: bool = False,
) -> Committee:
    committee_type = {
        AuthorityLevel.LOW: CommitteeType.OPERATIONAL_BOARD,
        AuthorityLevel.MIDDLE: CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        AuthorityLevel.HIGH: CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE,
    }[authority_level]
    committee = Committee(
        name=f"{authority_level.value} Committee {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=committee_type,
        is_active=is_active,
        is_fixed=is_fixed,
    )
    db_session.add(committee)
    db_session.commit()
    db_session.refresh(committee)
    return committee


def _create_membership(
    db_session: Session,
    *,
    committee: Committee,
    user: User,
    is_active: bool = True,
) -> CommitteeMember:
    membership = CommitteeMember(
        committee_id=committee.id,
        user_id=user.id,
        is_active=is_active,
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)
    return membership


def _post_report(
    client: TestClient,
    risk_record_id: uuid.UUID,
    output_dir: Path,
    headers: dict[str, str] | None = None,
):
    return client.post(
        f"/reports/risk-dossiers/{risk_record_id}",
        json={"output_dir": str(output_dir)},
        headers=headers,
    )


def test_post_risk_dossier_report_returns_201(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(risk_record.created_by_user_id)},
    )

    assert response.status_code == 201


def test_post_risk_dossier_report_creates_report_metadata(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(risk_record.created_by_user_id)},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["risk_record_id"] == str(risk_record.id)
    assert body["report_type"] == "RISK_DOSSIER_DOCX"
    assert body["file_path"]


def test_post_risk_dossier_report_creates_physical_docx_file(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(risk_record.created_by_user_id)},
    )

    assert response.status_code == 201
    assert Path(response.json()["file_path"]).is_file()


def test_post_unknown_risk_returns_http_400(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = _post_report(client, uuid.uuid4(), tmp_path)

    assert response.status_code == 400


def test_post_report_requires_active_user(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)
    inactive_user = _create_user(db_session, is_active=False)

    assert _post_report(client, risk_record.id, tmp_path).status_code == 400
    assert _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(uuid.uuid4())},
    ).status_code == 401
    assert _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(inactive_user.id)},
    ).status_code == 403


def test_post_report_authorizes_related_users_and_rejects_unrelated_user(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    creator = _create_user(db_session)
    owner = _create_user(db_session)
    board_member = _create_user(db_session)
    middle_member = _create_user(db_session)
    high_member = _create_user(db_session)
    unrelated_user = _create_user(db_session)
    board = _create_committee(db_session)
    middle_committee = _create_committee(
        db_session,
        authority_level=AuthorityLevel.MIDDLE,
        is_fixed=True,
    )
    high_committee = _create_committee(
        db_session,
        authority_level=AuthorityLevel.HIGH,
        is_fixed=True,
    )
    _create_membership(db_session, committee=board, user=board_member)
    _create_membership(db_session, committee=middle_committee, user=middle_member)
    _create_membership(db_session, committee=high_committee, user=high_member)
    risk_record = _create_risk_record(
        db_session,
        creator=creator,
        owner=owner,
        board_of_origin_id=board.id,
    )

    responses = [
        _post_report(
            client,
            risk_record.id,
            tmp_path,
            headers={"X-User-Id": str(user.id)},
        )
        for user in (creator, owner, board_member, middle_member, high_member)
    ]
    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == risk_record.id,
            AuditLog.action == AuditAction.GENERATE_REPORT,
        )
    )

    assert [response.status_code for response in responses] == [201] * 5
    assert [response.json()["generated_by_user_id"] for response in responses] == [
        str(creator.id),
        str(owner.id),
        str(board_member.id),
        str(middle_member.id),
        str(high_member.id),
    ]
    assert Path(responses[0].json()["file_path"]).is_file()
    assert audit_log is not None
    assert audit_log.changed_by_user_id in {
        creator.id,
        owner.id,
        board_member.id,
        middle_member.id,
        high_member.id,
    }
    assert _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(unrelated_user.id)},
    ).status_code == 400


def test_get_reports_returns_list(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)
    _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(risk_record.created_by_user_id)},
    )

    response = client.get("/reports")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_reports_filters_by_risk_record_id(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    first_risk = _create_risk_record(db_session, risk_id="RISK-2026-0001")
    second_risk = _create_risk_record(db_session, risk_id="RISK-2026-0002")
    first_response = _post_report(
        client,
        first_risk.id,
        tmp_path,
        headers={"X-User-Id": str(first_risk.created_by_user_id)},
    )
    _post_report(
        client,
        second_risk.id,
        tmp_path,
        headers={"X-User-Id": str(second_risk.created_by_user_id)},
    )

    response = client.get(f"/reports?risk_record_id={first_risk.id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == first_response.json()["id"]


def test_get_reports_filters_by_report_type(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)
    report_response = _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(risk_record.created_by_user_id)},
    )

    response = client.get("/reports?report_type=RISK_DOSSIER_DOCX")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == report_response.json()["id"]


def test_get_report_returns_report(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)
    report_response = _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(risk_record.created_by_user_id)},
    )

    response = client.get(f"/reports/{report_response.json()['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == report_response.json()["id"]


def test_download_report_returns_docx_file(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)
    report_response = _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(risk_record.created_by_user_id)},
    )

    response = client.get(
        f"/reports/{report_response.json()['id']}/download",
        headers={"X-User-Id": str(risk_record.created_by_user_id)},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert (
        f'filename="{Path(report_response.json()["file_path"]).name}"'
        in response.headers["content-disposition"]
    )
    assert response.content


def test_download_report_requires_active_user(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    creator = _create_user(db_session)
    inactive_user = _create_user(db_session, is_active=False)
    risk_record = _create_risk_record(db_session, creator=creator)
    report_response = _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(creator.id)},
    )
    report_id = report_response.json()["id"]

    assert client.get(f"/reports/{report_id}/download").status_code == 400
    assert client.get(
        f"/reports/{report_id}/download",
        headers={"X-User-Id": str(uuid.uuid4())},
    ).status_code == 401
    assert client.get(
        f"/reports/{report_id}/download",
        headers={"X-User-Id": str(inactive_user.id)},
    ).status_code == 403


def test_download_report_authorizes_related_users_and_rejects_unrelated(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    creator = _create_user(db_session)
    owner = _create_user(db_session)
    board_member = _create_user(db_session)
    middle_member = _create_user(db_session)
    high_member = _create_user(db_session)
    unrelated_user = _create_user(db_session)
    board = _create_committee(db_session)
    middle_committee = _create_committee(
        db_session,
        authority_level=AuthorityLevel.MIDDLE,
        is_fixed=True,
    )
    high_committee = _create_committee(
        db_session,
        authority_level=AuthorityLevel.HIGH,
        is_fixed=True,
    )
    _create_membership(db_session, committee=board, user=board_member)
    _create_membership(db_session, committee=middle_committee, user=middle_member)
    _create_membership(db_session, committee=high_committee, user=high_member)
    risk_record = _create_risk_record(
        db_session,
        creator=creator,
        owner=owner,
        board_of_origin_id=board.id,
    )
    report_response = _post_report(
        client,
        risk_record.id,
        tmp_path,
        headers={"X-User-Id": str(creator.id)},
    )
    report_id = report_response.json()["id"]

    responses = [
        client.get(
            f"/reports/{report_id}/download",
            headers={"X-User-Id": str(user.id)},
        )
        for user in (creator, owner, board_member, middle_member, high_member)
    ]

    assert [response.status_code for response in responses] == [200] * 5
    assert all(response.content for response in responses)
    assert client.get(
        f"/reports/{report_id}/download",
        headers={"X-User-Id": str(unrelated_user.id)},
    ).status_code == 400


def test_download_unknown_report_returns_http_404(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    response = client.get(
        f"/reports/{uuid.uuid4()}/download",
        headers={"X-User-Id": str(user.id)},
    )

    assert response.status_code == 404


def test_download_report_with_missing_file_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    risk_record = _create_risk_record(db_session, creator=creator)
    generated_report = GeneratedReport(
        report_type="RISK_DOSSIER_DOCX",
        risk_record_id=risk_record.id,
        file_path="missing.docx",
        generated_at=datetime.now(timezone.utc),
        template_version="1.0",
    )
    db_session.add(generated_report)
    db_session.commit()
    db_session.refresh(generated_report)

    response = client.get(
        f"/reports/{generated_report.id}/download",
        headers={"X-User-Id": str(creator.id)},
    )

    assert response.status_code == 400


def test_get_unknown_report_returns_http_404(client: TestClient) -> None:
    response = client.get(f"/reports/{uuid.uuid4()}")

    assert response.status_code == 404
