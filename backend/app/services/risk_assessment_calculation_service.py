import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.risk import RiskAssessment
from app.models.risk_matrix import (
    RiskLevel,
    RiskLikelihoodLevel,
    RiskMatrixCell,
    RiskSeverityLevel,
)


class RiskAssessmentCalculationError(ValueError):
    pass


def calculate_risk_assessment_from_matrix(
    db: Session,
    *,
    severity_level_id: uuid.UUID,
    likelihood_level_id: uuid.UUID,
) -> dict[str, object]:
    severity = db.get(RiskSeverityLevel, severity_level_id)
    if severity is None or not severity.is_active:
        raise RiskAssessmentCalculationError(
            "Severity level is not active or does not exist"
        )
    likelihood = db.get(RiskLikelihoodLevel, likelihood_level_id)
    if likelihood is None or not likelihood.is_active:
        raise RiskAssessmentCalculationError(
            "Likelihood level is not active or does not exist"
        )
    matrix_cell = db.scalar(
        select(RiskMatrixCell).where(
            RiskMatrixCell.severity_level_id == severity_level_id,
            RiskMatrixCell.likelihood_level_id == likelihood_level_id,
            RiskMatrixCell.is_active.is_(True),
        )
    )
    if matrix_cell is None:
        raise RiskAssessmentCalculationError(
            "No active risk matrix cell found for severity and likelihood"
        )
    risk_level = db.get(RiskLevel, matrix_cell.risk_level_id)
    if risk_level is None or not risk_level.is_active:
        raise RiskAssessmentCalculationError(
            "Calculated risk level is not active or does not exist"
        )
    return {
        "severity_level_id": severity.id,
        "likelihood_level_id": likelihood.id,
        "calculated_risk_level_id": risk_level.id,
        "matrix_cell_id": matrix_cell.id,
        "calculated_score": (
            matrix_cell.score
            if matrix_cell.score is not None
            else severity.numeric_value * likelihood.numeric_value
        ),
        "is_tolerable": risk_level.is_tolerable,
        "requires_mitigation": risk_level.requires_mitigation,
        "requires_escalation": risk_level.requires_escalation,
        "calculated_risk_level_code": risk_level.code,
        "calculated_risk_level_name": risk_level.name,
        "severity_level_code": severity.code,
        "likelihood_level_code": likelihood.code,
    }


def clear_risk_assessment_matrix_calculation(assessment: RiskAssessment) -> None:
    assessment.severity_level_id = None
    assessment.likelihood_level_id = None
    assessment.calculated_risk_level_id = None
    assessment.matrix_cell_id = None
    assessment.calculated_score = None
    assessment.is_tolerable = None
    assessment.requires_mitigation = None
    assessment.requires_escalation = None
