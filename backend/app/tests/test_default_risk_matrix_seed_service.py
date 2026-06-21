import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.risk_matrix import RiskLevel, RiskMatrixCell, RiskSeverityLevel
from app.models.user import User
from app.services.default_risk_matrix_seed_service import (
    DefaultRiskMatrixSeedError,
    seed_default_risk_matrix,
)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    Base.metadata.drop_all(engine)


def test_seed_creates_complete_default_matrix_and_audit_records(db_session: Session) -> None:
    result = seed_default_risk_matrix(db_session)
    cells = {cell.label: cell for cell in result["matrix_cells"]}

    assert result["created_severity_count"] == 5
    assert result["created_likelihood_count"] == 5
    assert result["created_risk_level_count"] == 4
    assert result["created_cell_count"] == 25
    assert result["total_cells"] == 25
    assert (cells["S1-L1"].risk_level.code, cells["S1-L1"].score) == ("LOW", 1)
    assert (cells["S1-L5"].risk_level.code, cells["S1-L5"].score) == ("MEDIUM", 5)
    assert (cells["S2-L4"].risk_level.code, cells["S2-L4"].score) == ("HIGH", 8)
    assert (cells["S3-L5"].risk_level.code, cells["S3-L5"].score) == ("EXTREME", 15)
    assert (cells["S5-L5"].risk_level.code, cells["S5-L5"].score) == ("EXTREME", 25)
    assert db_session.scalar(select(func.count()).select_from(AuditLog)) >= 39


def test_seed_is_idempotent_without_overwriting_active_records(db_session: Session) -> None:
    seed_default_risk_matrix(db_session)
    severity = db_session.scalar(select(RiskSeverityLevel).where(RiskSeverityLevel.code == "S3"))
    assert severity is not None
    severity.name = "Custom Major"
    db_session.flush()

    result = seed_default_risk_matrix(db_session)

    assert result["created_cell_count"] == 0
    assert result["updated_severity_count"] == 0
    assert severity.name == "Custom Major"
    assert db_session.scalar(select(func.count()).select_from(RiskMatrixCell)) == 25


def test_overwrite_updates_active_defaults_but_not_inactive_records(db_session: Session) -> None:
    seed_default_risk_matrix(db_session)
    severity = db_session.scalar(select(RiskSeverityLevel).where(RiskSeverityLevel.code == "S3"))
    assert severity is not None
    severity.name = "Custom Major"
    db_session.flush()

    result = seed_default_risk_matrix(db_session, overwrite_existing=True)

    assert result["updated_severity_count"] == 1
    assert severity.name == "Major"
    severity.is_active = False
    db_session.flush()
    with pytest.raises(DefaultRiskMatrixSeedError, match="Inactive default RiskSeverityLevel code exists: S3"):
        seed_default_risk_matrix(db_session)


def test_seed_overwrite_repairs_default_matrix_cell(db_session: Session) -> None:
    result = seed_default_risk_matrix(db_session)
    cell = result["matrix_cells"][0]
    level = db_session.scalar(select(RiskLevel).where(RiskLevel.code == "EXTREME"))
    assert level is not None
    cell.risk_level_id = level.id
    cell.score = 99
    cell.label = "custom"
    db_session.flush()

    result = seed_default_risk_matrix(db_session, overwrite_existing=True)

    assert result["updated_cell_count"] == 1
    assert cell.score == 1
    assert cell.label == "S1-L1"
    assert cell.risk_level.code == "LOW"


def test_seed_does_not_modify_extra_custom_records_and_attributes_audit(
    db_session: Session,
) -> None:
    actor = User(email="seed-actor@example.com", display_name="Seed Actor", is_active=True)
    custom_severity = RiskSeverityLevel(
        code="CUSTOM",
        name="Custom Severity",
        numeric_value=99,
        is_active=True,
    )
    db_session.add_all([actor, custom_severity])
    db_session.flush()

    seed_default_risk_matrix(
        db_session,
        changed_by_user_id=actor.id,
        overwrite_existing=True,
    )

    assert custom_severity.name == "Custom Severity"
    assert custom_severity.numeric_value == 99
    assert db_session.scalar(
        select(AuditLog).where(AuditLog.changed_by_user_id == actor.id)
    ) is not None
