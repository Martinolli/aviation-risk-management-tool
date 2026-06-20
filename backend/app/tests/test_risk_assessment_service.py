import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import (
    AuditAction,
    RiskAssessmentType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskRecord
from app.models.user import User
from app.schemas.risk_assessment import RiskAssessmentCreate, RiskAssessmentUpdate
from app.services.risk_assessment_service import (
    RiskAssessmentBusinessRuleError,
    create_risk_assessment,
    get_risk_assessment,
    list_risk_assessments,
    update_risk_assessment,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("risk assessment service must not commit transactions")


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, class_=NoCommitSession)

    with SessionLocal() as session:
        yield session

    Base.metadata.drop_all(engine)


def _create_risk_record(
    db_session: Session,
    *,
    is_active: bool = True,
    workflow_status: RiskWorkflowStatus = RiskWorkflowStatus.DRAFT,
) -> RiskRecord:
    risk_record = RiskRecord(
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=workflow_status,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=is_active,
    )
    db_session.add(risk_record)
    db_session.flush()
    return risk_record


def _assessment_data(
    risk_record_id: uuid.UUID,
    *,
    assessment_type: RiskAssessmentType = RiskAssessmentType.INITIAL,
    severity: str = "Major",
    likelihood: str = "Remote",
    risk_level: str = "Medium",
) -> RiskAssessmentCreate:
    return RiskAssessmentCreate(
        risk_record_id=risk_record_id,
        assessment_type=assessment_type,
        severity=severity,
        likelihood=likelihood,
        risk_level=risk_level,
        rationale="Initial assessment rationale",
    )


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Assessment User",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_create_initial_assessment_succeeds(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)

    assessment = create_risk_assessment(
        db_session,
        data=_assessment_data(risk_record.id),
        assessed_by_user_id=user.id,
    )

    assert assessment.id is not None
    assert assessment.assessment_type == RiskAssessmentType.INITIAL
    assert assessment.assessed_at.tzinfo is not None
    assert assessment.assessed_by_user_id == user.id


def test_create_residual_assessment_succeeds(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)

    assessment = create_risk_assessment(
        db_session,
        data=_assessment_data(
            risk_record.id,
            assessment_type=RiskAssessmentType.RESIDUAL,
        ),
        assessed_by_user_id=user.id,
    )

    assert assessment.assessment_type == RiskAssessmentType.RESIDUAL


def test_create_assessment_requires_active_actor(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    inactive_user = _create_user(db_session, is_active=False)

    with pytest.raises(RiskAssessmentBusinessRuleError, match="authenticated active user"):
        create_risk_assessment(db_session, data=_assessment_data(risk_record.id))
    with pytest.raises(RiskAssessmentBusinessRuleError, match="user does not exist"):
        create_risk_assessment(
            db_session,
            data=_assessment_data(risk_record.id),
            assessed_by_user_id=uuid.uuid4(),
        )
    with pytest.raises(RiskAssessmentBusinessRuleError, match="user is inactive"):
        create_risk_assessment(
            db_session,
            data=_assessment_data(risk_record.id),
            assessed_by_user_id=inactive_user.id,
        )


def test_update_assessment_requires_active_actor(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    creator = _create_user(db_session)
    inactive_user = _create_user(db_session, is_active=False)
    assessment = create_risk_assessment(
        db_session,
        data=_assessment_data(risk_record.id),
        assessed_by_user_id=creator.id,
    )

    with pytest.raises(RiskAssessmentBusinessRuleError, match="update requires"):
        update_risk_assessment(
            db_session,
            risk_assessment_id=assessment.id,
            data=RiskAssessmentUpdate(severity="Hazardous"),
        )
    with pytest.raises(RiskAssessmentBusinessRuleError, match="user does not exist"):
        update_risk_assessment(
            db_session,
            risk_assessment_id=assessment.id,
            data=RiskAssessmentUpdate(severity="Hazardous"),
            changed_by_user_id=uuid.uuid4(),
        )
    with pytest.raises(RiskAssessmentBusinessRuleError, match="user is inactive"):
        update_risk_assessment(
            db_session,
            risk_assessment_id=assessment.id,
            data=RiskAssessmentUpdate(severity="Hazardous"),
            changed_by_user_id=inactive_user.id,
        )


def test_create_assessment_for_unknown_risk_record_raises_business_rule_error(
    db_session: Session,
) -> None:
    with pytest.raises(RiskAssessmentBusinessRuleError):
        create_risk_assessment(
            db_session,
            data=_assessment_data(uuid.uuid4()),
        )


def test_create_assessment_for_inactive_risk_record_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session, is_active=False)

    with pytest.raises(RiskAssessmentBusinessRuleError):
        create_risk_assessment(
            db_session,
            data=_assessment_data(risk_record.id),
        )


def test_create_assessment_for_closed_risk_record_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(
        db_session,
        workflow_status=RiskWorkflowStatus.CLOSED,
    )

    with pytest.raises(RiskAssessmentBusinessRuleError):
        create_risk_assessment(
            db_session,
            data=_assessment_data(risk_record.id),
        )


def test_create_assessment_with_empty_severity_fails() -> None:
    with pytest.raises(ValidationError):
        RiskAssessmentCreate(
            risk_record_id=uuid.uuid4(),
            assessment_type=RiskAssessmentType.INITIAL,
            severity="",
            likelihood="Remote",
            risk_level="Medium",
        )


def test_create_assessment_with_blank_severity_fails_at_service_level(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)

    with pytest.raises(RiskAssessmentBusinessRuleError):
        create_risk_assessment(
            db_session,
            data=_assessment_data(risk_record.id, severity="   "),
            assessed_by_user_id=user.id,
        )


@pytest.mark.parametrize(
    "assessment_type",
    [RiskAssessmentType.INITIAL, RiskAssessmentType.RESIDUAL],
)
def test_create_duplicate_assessment_type_for_same_risk_raises_business_rule_error(
    db_session: Session,
    assessment_type: RiskAssessmentType,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)
    create_risk_assessment(
        db_session,
        data=_assessment_data(risk_record.id, assessment_type=assessment_type),
        assessed_by_user_id=user.id,
    )

    with pytest.raises(RiskAssessmentBusinessRuleError):
        create_risk_assessment(
            db_session,
            data=_assessment_data(risk_record.id, assessment_type=assessment_type),
            assessed_by_user_id=user.id,
        )


def test_create_assessment_writes_create_audit_log(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)

    assessment = create_risk_assessment(
        db_session,
        data=_assessment_data(risk_record.id),
        assessed_by_user_id=user.id,
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == assessment.id,
            AuditLog.entity_type == "RiskAssessment",
            AuditLog.action == AuditAction.CREATE,
        )
    )

    assert audit_log is not None
    assert audit_log.changed_by_user_id == user.id


def test_update_assessment_severity_succeeds_and_writes_update_audit_log(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)
    assessment = create_risk_assessment(
        db_session,
        data=_assessment_data(risk_record.id),
        assessed_by_user_id=user.id,
    )

    updated_assessment = update_risk_assessment(
        db_session,
        risk_assessment_id=assessment.id,
        data=RiskAssessmentUpdate(severity="Hazardous"),
        changed_by_user_id=user.id,
        reason="Reassessed consequence severity",
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == assessment.id,
            AuditLog.entity_type == "RiskAssessment",
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.field_name == "severity",
        )
    )

    assert updated_assessment.severity == "Hazardous"
    assert audit_log is not None
    assert audit_log.old_value == "Major"
    assert audit_log.new_value == "Hazardous"
    assert audit_log.changed_by_user_id == user.id


def test_update_assessment_with_empty_risk_level_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)
    assessment = create_risk_assessment(
        db_session,
        data=_assessment_data(risk_record.id),
        assessed_by_user_id=user.id,
    )

    with pytest.raises(RiskAssessmentBusinessRuleError):
        update_risk_assessment(
            db_session,
            risk_assessment_id=assessment.id,
            data=RiskAssessmentUpdate(risk_level="   "),
            changed_by_user_id=user.id,
        )


def test_list_risk_assessments_filtered_by_risk_record_id(
    db_session: Session,
) -> None:
    first_risk = _create_risk_record(db_session)
    second_risk = _create_risk_record(db_session)
    user = _create_user(db_session)
    first_assessment = create_risk_assessment(
        db_session,
        data=_assessment_data(first_risk.id),
        assessed_by_user_id=user.id,
    )
    second_assessment = create_risk_assessment(
        db_session,
        data=_assessment_data(second_risk.id),
        assessed_by_user_id=user.id,
    )

    assessments = list_risk_assessments(db_session, risk_record_id=first_risk.id)

    assert first_assessment in assessments
    assert second_assessment not in assessments


def test_get_unknown_assessment_returns_none(db_session: Session) -> None:
    assert get_risk_assessment(db_session, risk_assessment_id=uuid.uuid4()) is None
