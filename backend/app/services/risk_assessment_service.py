import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.enums import RiskWorkflowStatus
from app.models.risk import RiskAssessment, RiskRecord
from app.models.user import User
from app.schemas.risk_assessment import RiskAssessmentCreate, RiskAssessmentUpdate
from app.services.risk_assessment_calculation_service import (
    RiskAssessmentCalculationError,
    calculate_risk_assessment_from_matrix,
    clear_risk_assessment_matrix_calculation,
)

RISK_ASSESSMENT_ENTITY_TYPE = "RiskAssessment"


class RiskAssessmentNotFoundError(ValueError):
    pass


class RiskAssessmentBusinessRuleError(ValueError):
    pass


def _risk_assessment_snapshot(assessment: RiskAssessment) -> dict[str, object]:
    return {
        "id": assessment.id,
        "risk_record_id": assessment.risk_record_id,
        "assessment_type": assessment.assessment_type,
        "severity": assessment.severity,
        "likelihood": assessment.likelihood,
        "risk_level": assessment.risk_level,
        "rationale": assessment.rationale,
        "assessed_by_user_id": assessment.assessed_by_user_id,
        "assessed_at": assessment.assessed_at,
        "severity_level_id": assessment.severity_level_id,
        "likelihood_level_id": assessment.likelihood_level_id,
        "calculated_risk_level_id": assessment.calculated_risk_level_id,
        "matrix_cell_id": assessment.matrix_cell_id,
        "calculated_score": assessment.calculated_score,
        "is_tolerable": assessment.is_tolerable,
        "requires_mitigation": assessment.requires_mitigation,
        "requires_escalation": assessment.requires_escalation,
    }


def _validate_required_text(field_name: str, value: str) -> None:
    if not value.strip():
        raise RiskAssessmentBusinessRuleError(f"{field_name} must not be empty")


def _validate_assessment_text_fields(data: dict[str, object]) -> None:
    for field_name in ("severity", "likelihood", "risk_level"):
        if field_name not in data:
            continue
        value = data[field_name]
        if not isinstance(value, str):
            raise RiskAssessmentBusinessRuleError(f"{field_name} must not be empty")
        _validate_required_text(field_name, value)


def _apply_calculation(
    db: Session,
    *,
    assessment: RiskAssessment,
    severity_level_id: uuid.UUID,
    likelihood_level_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
    audit_changes: bool = False,
) -> None:
    try:
        calculation = calculate_risk_assessment_from_matrix(
            db,
            severity_level_id=severity_level_id,
            likelihood_level_id=likelihood_level_id,
        )
    except RiskAssessmentCalculationError as exc:
        raise RiskAssessmentBusinessRuleError(str(exc)) from exc
    values = {
        "severity_level_id": calculation["severity_level_id"],
        "likelihood_level_id": calculation["likelihood_level_id"],
        "calculated_risk_level_id": calculation["calculated_risk_level_id"],
        "matrix_cell_id": calculation["matrix_cell_id"],
        "calculated_score": calculation["calculated_score"],
        "is_tolerable": calculation["is_tolerable"],
        "requires_mitigation": calculation["requires_mitigation"],
        "requires_escalation": calculation["requires_escalation"],
        "severity": calculation["severity_level_code"],
        "likelihood": calculation["likelihood_level_code"],
        "risk_level": calculation["calculated_risk_level_code"],
    }
    for field_name, new_value in values.items():
        old_value = getattr(assessment, field_name)
        if old_value == new_value:
            continue
        setattr(assessment, field_name, new_value)
        if audit_changes:
            audit_service.log_change(
                db,
                entity_type=RISK_ASSESSMENT_ENTITY_TYPE,
                entity_id=assessment.id,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                changed_by_user_id=changed_by_user_id,
                reason=reason,
            )


def _clear_calculation_with_audit(
    db: Session,
    *,
    assessment: RiskAssessment,
    changed_by_user_id: uuid.UUID | None,
    reason: str | None,
) -> None:
    fields = (
        "severity_level_id", "likelihood_level_id", "calculated_risk_level_id",
        "matrix_cell_id", "calculated_score", "is_tolerable",
        "requires_mitigation", "requires_escalation",
    )
    old_values = {field_name: getattr(assessment, field_name) for field_name in fields}
    clear_risk_assessment_matrix_calculation(assessment)
    for field_name, old_value in old_values.items():
        if old_value is None:
            continue
        audit_service.log_change(
            db,
            entity_type=RISK_ASSESSMENT_ENTITY_TYPE,
            entity_id=assessment.id,
            field_name=field_name,
            old_value=old_value,
            new_value=None,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )


def _get_assessable_risk_record(db: Session, risk_record_id: uuid.UUID) -> RiskRecord:
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        raise RiskAssessmentBusinessRuleError("Risk record does not exist")
    if not risk_record.is_active:
        raise RiskAssessmentBusinessRuleError("Inactive risk records cannot be assessed")
    if risk_record.workflow_status == RiskWorkflowStatus.CLOSED:
        raise RiskAssessmentBusinessRuleError("Closed risk records cannot be assessed")
    return risk_record


def _validate_assessment_actor(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    operation: str,
) -> None:
    if user_id is None:
        if operation == "update":
            raise RiskAssessmentBusinessRuleError(
                "Risk assessment update requires an authenticated active user"
            )
        raise RiskAssessmentBusinessRuleError(
            "Risk assessment requires an authenticated active user"
        )

    user = db.get(User, user_id)
    if user is None:
        raise RiskAssessmentBusinessRuleError("Risk assessment user does not exist")
    if not user.is_active:
        raise RiskAssessmentBusinessRuleError("Risk assessment user is inactive")


def create_risk_assessment(
    db: Session,
    *,
    data: RiskAssessmentCreate,
    assessed_by_user_id: uuid.UUID | None = None,
) -> RiskAssessment:
    _get_assessable_risk_record(db, data.risk_record_id)
    _validate_assessment_actor(
        db,
        user_id=assessed_by_user_id,
        operation="create",
    )
    matrix_ids_provided = (
        data.severity_level_id is not None,
        data.likelihood_level_id is not None,
    )
    if any(matrix_ids_provided) and not all(matrix_ids_provided):
        raise RiskAssessmentBusinessRuleError(
            "Both severity_level_id and likelihood_level_id are required for matrix calculation"
        )
    if not any(matrix_ids_provided):
        _validate_assessment_text_fields(data.model_dump())

    existing_assessment = db.scalar(
        select(RiskAssessment).where(
            RiskAssessment.risk_record_id == data.risk_record_id,
            RiskAssessment.assessment_type == data.assessment_type,
        )
    )
    if existing_assessment is not None:
        raise RiskAssessmentBusinessRuleError(
            f"{data.assessment_type.value} assessment already exists for this risk"
        )

    assessment = RiskAssessment(
        risk_record_id=data.risk_record_id,
        assessment_type=data.assessment_type,
        severity=data.severity or "",
        likelihood=data.likelihood or "",
        risk_level=data.risk_level or "",
        rationale=data.rationale,
        assessed_by_user_id=assessed_by_user_id,
        assessed_at=datetime.now(timezone.utc),
    )
    if all(matrix_ids_provided):
        _apply_calculation(
            db,
            assessment=assessment,
            severity_level_id=data.severity_level_id,
            likelihood_level_id=data.likelihood_level_id,
        )
    db.add(assessment)
    db.flush()

    audit_service.log_entity_created(
        db,
        entity_type=RISK_ASSESSMENT_ENTITY_TYPE,
        entity_id=assessment.id,
        created_by_user_id=assessed_by_user_id,
        new_value=_risk_assessment_snapshot(assessment),
    )
    return assessment


def get_risk_assessment(
    db: Session,
    *,
    risk_assessment_id: uuid.UUID,
) -> RiskAssessment | None:
    return db.get(RiskAssessment, risk_assessment_id)


def list_risk_assessments(
    db: Session,
    *,
    risk_record_id: uuid.UUID | None = None,
) -> list[RiskAssessment]:
    statement = select(RiskAssessment).order_by(RiskAssessment.created_at.desc())
    if risk_record_id is not None:
        statement = statement.where(RiskAssessment.risk_record_id == risk_record_id)

    return list(db.scalars(statement).all())


def update_risk_assessment(
    db: Session,
    *,
    risk_assessment_id: uuid.UUID,
    data: RiskAssessmentUpdate,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> RiskAssessment:
    assessment = get_risk_assessment(db, risk_assessment_id=risk_assessment_id)
    if assessment is None:
        raise RiskAssessmentNotFoundError("Risk assessment not found")

    _validate_assessment_actor(
        db,
        user_id=changed_by_user_id,
        operation="update",
    )
    _get_assessable_risk_record(db, assessment.risk_record_id)
    update_data = data.model_dump(exclude_unset=True)
    clear_matrix_calculation = update_data.pop("clear_matrix_calculation", False)
    supplied_severity_level_id = update_data.pop("severity_level_id", None)
    supplied_likelihood_level_id = update_data.pop("likelihood_level_id", None)
    _validate_assessment_text_fields(update_data)

    for field_name, new_value in update_data.items():
        old_value = getattr(assessment, field_name)
        if old_value == new_value:
            continue

        setattr(assessment, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=RISK_ASSESSMENT_ENTITY_TYPE,
            entity_id=assessment.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )

    if clear_matrix_calculation:
        _clear_calculation_with_audit(
            db,
            assessment=assessment,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )
    elif "severity_level_id" in data.model_fields_set or "likelihood_level_id" in data.model_fields_set:
        severity_level_id = (
            supplied_severity_level_id
            if "severity_level_id" in data.model_fields_set
            else assessment.severity_level_id
        )
        likelihood_level_id = (
            supplied_likelihood_level_id
            if "likelihood_level_id" in data.model_fields_set
            else assessment.likelihood_level_id
        )
        if severity_level_id is None or likelihood_level_id is None:
            raise RiskAssessmentBusinessRuleError(
                "Both severity_level_id and likelihood_level_id are required for matrix calculation"
            )
        _apply_calculation(
            db,
            assessment=assessment,
            severity_level_id=severity_level_id,
            likelihood_level_id=likelihood_level_id,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
            audit_changes=True,
        )

    db.add(assessment)
    db.flush()
    return assessment
