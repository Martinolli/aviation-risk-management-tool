from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.enums import RiskDomain, RiskLifecycleStatus, RiskWorkflowStatus
from app.models.risk import RiskRecord
from app.services.risk_numbering_service import generate_next_risk_id, parse_risk_id


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        yield session

    Base.metadata.drop_all(engine)


def _create_risk_record(db_session: Session, *, risk_id: str | None) -> RiskRecord:
    risk_record = RiskRecord(
        risk_id=risk_id,
        problem_description="Risk numbering test record.",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.flush()
    return risk_record


def test_parse_risk_id_parses_valid_id() -> None:
    assert parse_risk_id("RISK-2026-0001") == (2026, 1)


@pytest.mark.parametrize(
    "risk_id",
    [
        "",
        "RISK-26-0001",
        "RISK-2026-001",
        "RISK-2026-ABC1",
        "OTHER-2026-0001",
    ],
)
def test_parse_risk_id_returns_none_for_invalid_id(risk_id: str) -> None:
    assert parse_risk_id(risk_id) is None


def test_generate_next_risk_id_returns_current_year_first_id_when_none_exist(
    db_session: Session,
) -> None:
    current_year = datetime.now(timezone.utc).year

    risk_id = generate_next_risk_id(db_session)

    assert risk_id == f"RISK-{current_year}-0001"


def test_generate_next_risk_id_with_year_returns_first_id_when_none_exist(
    db_session: Session,
) -> None:
    assert generate_next_risk_id(db_session, year=2026) == "RISK-2026-0001"


def test_generate_next_risk_id_returns_next_sequence_when_existing_id_exists(
    db_session: Session,
) -> None:
    _create_risk_record(db_session, risk_id="RISK-2026-0001")

    assert generate_next_risk_id(db_session, year=2026) == "RISK-2026-0002"


def test_generate_next_risk_id_ignores_invalid_risk_id_values(
    db_session: Session,
) -> None:
    _create_risk_record(db_session, risk_id="RISK-2026-0001")
    _create_risk_record(db_session, risk_id="RISK-2026-ABC1")
    _create_risk_record(db_session, risk_id="OTHER-2026-9999")

    assert generate_next_risk_id(db_session, year=2026) == "RISK-2026-0002"


def test_generate_next_risk_id_resets_sequence_for_new_year(
    db_session: Session,
) -> None:
    _create_risk_record(db_session, risk_id="RISK-2026-0007")

    assert generate_next_risk_id(db_session, year=2027) == "RISK-2027-0001"


def test_generate_next_risk_id_uses_highest_existing_sequence(
    db_session: Session,
) -> None:
    _create_risk_record(db_session, risk_id="RISK-2026-0002")
    _create_risk_record(db_session, risk_id="RISK-2026-0010")
    _create_risk_record(db_session, risk_id="RISK-2026-0005")

    assert generate_next_risk_id(db_session, year=2026) == "RISK-2026-0011"
