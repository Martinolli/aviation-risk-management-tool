import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.enums import RiskWorkflowStatus
from app.models.risk import RiskAssessment, RiskRecord
from app.models.user import User
from app.schemas.risk_assessment import RiskAssessmentCreate, RiskAssessmentUpdate

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
    }


def _validate_required_text(field_name: str, value: str) -> None:
    if not value.strip():
        raise RiskAssessmentBusinessRuleError(f"{field_name} must not be empty")


def _validate_assessment_text_fields(data: dict[str, object]) -> None:
    for field_name in ("severity", "likelihood", "risk_level"):
        value = data.get(field_name)
        if isinstance(value, str):
            _validate_required_text(field_name, value)


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
        severity=data.severity,
        likelihood=data.likelihood,
        risk_level=data.risk_level,
        rationale=data.rationale,
        assessed_by_user_id=assessed_by_user_id,
        assessed_at=datetime.now(timezone.utc),
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

    db.add(assessment)
    db.flush()
    return assessment
