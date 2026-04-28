import pytest
from pydantic import ValidationError
from sqlalchemy.orm import configure_mappers

from app.models import (
    AuditAction,
    AuditLog,
    AuthorityLevel,
    Committee,
    CommitteeMember,
    CommitteeType,
    GeneratedReport,
    LLMAnalysis,
    RiskAction,
    RiskAssessment,
    RiskDecision,
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskRecord,
    RiskWorkflowStatus,
    Role,
    User,
)
from app.models.base import Base
from app.schemas import RiskRecordCreate


def test_all_models_import_and_register_tables() -> None:
    configure_mappers()

    expected_tables = {
        "users",
        "roles",
        "committees",
        "committee_members",
        "risk_records",
        "risk_assessments",
        "risk_actions",
        "risk_decisions",
        "audit_logs",
        "generated_reports",
        "llm_analyses",
    }

    assert expected_tables.issubset(Base.metadata.tables)
    assert User
    assert Role
    assert Committee
    assert CommitteeMember
    assert RiskRecord
    assert RiskAssessment
    assert RiskAction
    assert RiskDecision
    assert AuditLog
    assert GeneratedReport
    assert LLMAnalysis


def test_required_enums_exist() -> None:
    assert [level.value for level in AuthorityLevel] == ["LOW", "MIDDLE", "HIGH"]
    assert CommitteeType.OPERATIONAL_BOARD.value == "OPERATIONAL_BOARD"
    assert RiskWorkflowStatus.DRAFT.value == "DRAFT"
    assert RiskWorkflowStatus.CLOSED.value == "CLOSED"
    assert RiskLifecycleStatus.MONITORING.value == "MONITORING"
    assert RiskDomain.FLIGHT_TEST.value == "FLIGHT_TEST"
    assert RiskDomain.OTHER.value == "OTHER"
    assert RiskDecisionType.ACCEPT_RESIDUAL_RISK.value == "ACCEPT_RESIDUAL_RISK"
    assert AuditAction.LLM_ANALYSIS.value == "LLM_ANALYSIS"


def test_risk_record_create_requires_problem_description() -> None:
    with pytest.raises(ValidationError):
        RiskRecordCreate()

    schema = RiskRecordCreate(problem_description="Unstable test condition observed.")

    assert schema.problem_description == "Unstable test condition observed."
    assert schema.domain == RiskDomain.OTHER


def test_committee_can_represent_all_authority_levels() -> None:
    low = Committee(
        name="Operational Board",
        authority_level=AuthorityLevel.LOW,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=False,
    )
    middle = Committee(
        name="Risk Management Committee",
        authority_level=AuthorityLevel.MIDDLE,
        committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        is_fixed=True,
    )
    high = Committee(
        name="Executive Safety Management Committee",
        authority_level=AuthorityLevel.HIGH,
        committee_type=CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE,
        is_fixed=True,
    )

    assert {low.authority_level, middle.authority_level, high.authority_level} == {
        AuthorityLevel.LOW,
        AuthorityLevel.MIDDLE,
        AuthorityLevel.HIGH,
    }


def test_fixed_committee_flags_can_be_represented() -> None:
    configurable_board = Committee(
        name="Configurable Low Board",
        authority_level=AuthorityLevel.LOW,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=False,
    )
    protected_committee = Committee(
        name="Protected Governance Committee",
        authority_level=AuthorityLevel.HIGH,
        committee_type=CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE,
        is_fixed=True,
    )

    assert configurable_board.is_fixed is False
    assert protected_committee.is_fixed is True
