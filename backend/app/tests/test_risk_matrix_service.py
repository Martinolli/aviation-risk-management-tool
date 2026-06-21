import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel, CommitteeType
from app.models.risk_matrix import RiskSeverityLevel
from app.models.user import User
from app.schemas.risk_matrix import (
    RiskLevelCreate, RiskLikelihoodLevelCreate,
    RiskMatrixCellCreate, RiskMatrixCellUpdate, RiskSeverityLevelCreate,
)
from app.services.admin_authorization_service import AdminAuthorizationBusinessRuleError
from app.services.risk_matrix_service import (
    RiskMatrixBusinessRuleError,
    archive_severity_level,
    create_likelihood_level,
    create_matrix_cell,
    create_risk_level,
    create_severity_level,
    list_severity_levels,
    update_matrix_cell,
)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    Base.metadata.drop_all(engine)


def _user(db: Session) -> User:
    user = User(email=f"matrix-{uuid.uuid4()}@example.com", display_name="Matrix User", is_active=True)
    db.add(user)
    db.flush()
    return user


def _admin(db: Session) -> User:
    user = _user(db)
    committee = Committee(name=f"Governance {uuid.uuid4()}", authority_level=AuthorityLevel.MIDDLE, committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE, is_fixed=True, is_active=True)
    db.add(committee)
    db.flush()
    db.add(CommitteeMember(committee_id=committee.id, user_id=user.id, is_active=True))
    db.flush()
    return user


def _severity_data() -> RiskSeverityLevelCreate:
    return RiskSeverityLevelCreate(code=" s3 ", name=" Major ", numeric_value=3)


def test_reference_levels_are_admin_only_normalized_and_audited(db_session: Session) -> None:
    admin = _admin(db_session)
    severity = create_severity_level(db_session, data=_severity_data(), changed_by_user_id=admin.id)

    assert severity.code == "S3"
    assert severity.name == "Major"
    assert db_session.scalar(select(AuditLog).where(AuditLog.entity_id == severity.id)) is not None
    with pytest.raises(RiskMatrixBusinessRuleError):
        create_severity_level(db_session, data=RiskSeverityLevelCreate(code="S3", name="Duplicate", numeric_value=1), changed_by_user_id=admin.id)
    with pytest.raises(AdminAuthorizationBusinessRuleError):
        create_severity_level(db_session, data=RiskSeverityLevelCreate(code="S4", name="Hazardous", numeric_value=4), changed_by_user_id=_user(db_session).id)


@pytest.mark.parametrize("code,name,value", [("   ", "Major", 3), ("S3", "  ", 3)])
def test_reference_validation_rejects_blank_code_or_name(db_session: Session, code: str, name: str, value: int) -> None:
    admin = _admin(db_session)
    with pytest.raises(RiskMatrixBusinessRuleError):
        create_severity_level(db_session, data=RiskSeverityLevelCreate.model_construct(code=code, name=name, numeric_value=value), changed_by_user_id=admin.id)


def test_reference_validation_rejects_non_positive_numeric_value(db_session: Session) -> None:
    admin = _admin(db_session)
    with pytest.raises(RiskMatrixBusinessRuleError, match="positive"):
        create_severity_level(
            db_session,
            data=RiskSeverityLevelCreate.model_construct(code="S0", name="Invalid", numeric_value=0),
            changed_by_user_id=admin.id,
        )


def test_archive_filters_and_audits_reference_levels(db_session: Session) -> None:
    admin = _admin(db_session)
    severity = create_severity_level(db_session, data=_severity_data(), changed_by_user_id=admin.id)
    archive_severity_level(db_session, severity_level_id=severity.id, changed_by_user_id=admin.id, reason="Retired")

    assert severity.is_active is False
    assert severity.archived_at is not None
    assert severity.archived_by_user_id == admin.id
    assert list_severity_levels(db_session) == []
    assert list_severity_levels(db_session, include_inactive=True) == [severity]
    with pytest.raises(RiskMatrixBusinessRuleError, match="already archived"):
        archive_severity_level(db_session, severity_level_id=severity.id, changed_by_user_id=admin.id)


def test_matrix_cells_validate_references_auto_score_update_and_archive(db_session: Session) -> None:
    admin = _admin(db_session)
    severity = create_severity_level(db_session, data=_severity_data(), changed_by_user_id=admin.id)
    likelihood = create_likelihood_level(db_session, data=RiskLikelihoodLevelCreate(code="l2", name="Remote", numeric_value=2), changed_by_user_id=admin.id)
    low = create_risk_level(db_session, data=RiskLevelCreate(code="low", name="Low", numeric_value=1), changed_by_user_id=admin.id)
    high = create_risk_level(db_session, data=RiskLevelCreate(code="high", name="High", numeric_value=3), changed_by_user_id=admin.id)
    cell = create_matrix_cell(db_session, data=RiskMatrixCellCreate(severity_level_id=severity.id, likelihood_level_id=likelihood.id, risk_level_id=low.id), changed_by_user_id=admin.id)

    assert cell.score == 6
    with pytest.raises(RiskMatrixBusinessRuleError, match="already exists"):
        create_matrix_cell(db_session, data=RiskMatrixCellCreate(severity_level_id=severity.id, likelihood_level_id=likelihood.id, risk_level_id=low.id), changed_by_user_id=admin.id)
    update_matrix_cell(db_session, matrix_cell_id=cell.id, data=RiskMatrixCellUpdate(risk_level_id=high.id), changed_by_user_id=admin.id)
    assert cell.risk_level_id == high.id
