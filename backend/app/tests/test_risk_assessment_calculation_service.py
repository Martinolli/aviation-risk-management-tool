import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.risk import RiskAssessment
from app.models.risk_matrix import RiskLevel, RiskLikelihoodLevel, RiskMatrixCell, RiskSeverityLevel
from app.services.risk_assessment_calculation_service import (
    RiskAssessmentCalculationError,
    calculate_risk_assessment_from_matrix,
    clear_risk_assessment_matrix_calculation,
)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    Base.metadata.drop_all(engine)


def _matrix(db: Session, *, score: int | None = 7) -> tuple[RiskSeverityLevel, RiskLikelihoodLevel, RiskLevel, RiskMatrixCell]:
    severity = RiskSeverityLevel(code=f"S-{uuid.uuid4()}", name="Major", numeric_value=3, is_active=True)
    likelihood = RiskLikelihoodLevel(code=f"L-{uuid.uuid4()}", name="Remote", numeric_value=2, is_active=True)
    level = RiskLevel(code=f"H-{uuid.uuid4()}", name="High", numeric_value=3, is_active=True, is_tolerable=False, requires_mitigation=True, requires_escalation=True)
    db.add_all([severity, likelihood, level])
    db.flush()
    cell = RiskMatrixCell(severity_level_id=severity.id, likelihood_level_id=likelihood.id, risk_level_id=level.id, score=score, is_active=True)
    db.add(cell)
    db.flush()
    return severity, likelihood, level, cell


def test_calculates_active_matrix_cell_and_fallback_score(db_session: Session) -> None:
    severity, likelihood, level, cell = _matrix(db_session, score=None)

    result = calculate_risk_assessment_from_matrix(db_session, severity_level_id=severity.id, likelihood_level_id=likelihood.id)

    assert result["matrix_cell_id"] == cell.id
    assert result["calculated_risk_level_id"] == level.id
    assert result["calculated_score"] == 6
    assert result["requires_escalation"] is True


@pytest.mark.parametrize("inactive_target", ["severity", "likelihood", "cell", "level"])
def test_calculation_rejects_inactive_references(db_session: Session, inactive_target: str) -> None:
    severity, likelihood, level, cell = _matrix(db_session)
    {"severity": severity, "likelihood": likelihood, "cell": cell, "level": level}[inactive_target].is_active = False

    with pytest.raises(RiskAssessmentCalculationError):
        calculate_risk_assessment_from_matrix(db_session, severity_level_id=severity.id, likelihood_level_id=likelihood.id)


def test_clear_matrix_calculation_clears_all_fields() -> None:
    assessment = RiskAssessment(
        risk_record_id=uuid.uuid4(), assessment_type="INITIAL", severity="S3", likelihood="L2", risk_level="HIGH", assessed_at=datetime.now(),
        severity_level_id=uuid.uuid4(), likelihood_level_id=uuid.uuid4(), calculated_risk_level_id=uuid.uuid4(), matrix_cell_id=uuid.uuid4(), calculated_score=6, is_tolerable=False, requires_mitigation=True, requires_escalation=True,
    )

    clear_risk_assessment_matrix_calculation(assessment)

    assert assessment.severity_level_id is None
    assert assessment.likelihood_level_id is None
    assert assessment.calculated_risk_level_id is None
    assert assessment.matrix_cell_id is None
    assert assessment.calculated_score is None
    assert assessment.is_tolerable is None
    assert assessment.requires_mitigation is None
    assert assessment.requires_escalation is None
