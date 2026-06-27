import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel, CommitteeType
from app.models.user import User
from app.services.security_service import verify_password
from app.services.test_access_seed_service import (
    TEST_ACCESS_PROFILES,
    TestAccessSeedError,
    seed_test_access_profiles,
)

AIRCRAFT_COMMITTEE = "Aircraft Safety Committee - Engineering Board"
INDUSTRIAL_COMMITTEE = (
    "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE"
)
FLIGHT_TEST_COMMITTEE = "Flight Test Safety Committee - Operation"
RISK_MANAGEMENT_COMMITTEE = "Risk Management Committee"


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("test access seed service must not commit transactions")


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, class_=NoCommitSession)() as session:
        yield session
    Base.metadata.drop_all(engine)


def _seed_required_committees(
    db: Session,
    *,
    omit: str | None = None,
    risk_management_authority_level: AuthorityLevel = AuthorityLevel.MIDDLE,
) -> None:
    definitions = [
        (AIRCRAFT_COMMITTEE, AuthorityLevel.LOW, CommitteeType.OPERATIONAL_BOARD, False),
        (INDUSTRIAL_COMMITTEE, AuthorityLevel.LOW, CommitteeType.OPERATIONAL_BOARD, False),
        (FLIGHT_TEST_COMMITTEE, AuthorityLevel.LOW, CommitteeType.OPERATIONAL_BOARD, False),
        (
            RISK_MANAGEMENT_COMMITTEE,
            risk_management_authority_level,
            CommitteeType.RISK_MANAGEMENT_COMMITTEE,
            True,
        ),
    ]
    for name, authority_level, committee_type, is_fixed in definitions:
        if name == omit:
            continue
        db.add(
            Committee(
                name=name,
                authority_level=authority_level,
                committee_type=committee_type,
                is_fixed=is_fixed,
                is_active=True,
            )
        )
    db.flush()


def test_seed_test_access_profiles_creates_expected_users_and_memberships(
    db_session: Session,
) -> None:
    password = "ChangeMe123!"
    _seed_required_committees(db_session)

    result = seed_test_access_profiles(db_session, password=password)

    assert result["created_users"] == 6
    assert result["created_memberships"] == 6
    assert db_session.scalar(select(func.count()).select_from(User)) == 6
    assert db_session.scalar(select(func.count()).select_from(CommitteeMember)) == 6

    for profile in TEST_ACCESS_PROFILES:
        user = db_session.scalar(
            select(User).where(
                func.lower(User.email) == str(profile["email"]).lower()
            )
        )
        assert user is not None
        assert user.display_name == profile["display_name"]
        assert user.is_active is True
        assert verify_password(password, user.password_hash)

    celso = db_session.scalar(select(User).where(User.email == "celso.cobra@calaero.ae"))
    assert celso is not None

    expected_role_labels = {
        "joao.bosco@calidus.ae": (
            RISK_MANAGEMENT_COMMITTEE,
            "Governance Administrator",
        ),
        "kevin.rooney@calidus.ae": (AIRCRAFT_COMMITTEE, "Committee Chairman"),
        "gulzar.hussain@calidus.ae": (INDUSTRIAL_COMMITTEE, "Committee Member"),
        "joao.desouza@calidus.ae": (FLIGHT_TEST_COMMITTEE, "Committee Chairman"),
        "andres.samper@calidus.ae": (RISK_MANAGEMENT_COMMITTEE, "Committee Member"),
        "celso.cobra@calaero.ae": (RISK_MANAGEMENT_COMMITTEE, "Committee Chairman"),
    }
    for email, (committee_name, role_label) in expected_role_labels.items():
        membership = db_session.scalar(
            select(CommitteeMember)
            .join(User, CommitteeMember.user_id == User.id)
            .join(Committee, CommitteeMember.committee_id == Committee.id)
            .where(
                User.email == email,
                Committee.name == committee_name,
                CommitteeMember.is_active.is_(True),
            )
        )
        assert membership is not None
        assert membership.role_label == role_label

    admin_summary = next(
        profile for profile in result["profiles"] if profile["email"] == "joao.bosco@calidus.ae"
    )
    assert admin_summary["membership_status"] == "created"
    assert admin_summary["is_system_admin"] is True
    assert result["admin_role_status"] == "profiled"


def test_seed_test_access_profiles_is_idempotent(db_session: Session) -> None:
    _seed_required_committees(db_session)

    seed_test_access_profiles(db_session, password="ChangeMe123!")
    second_result = seed_test_access_profiles(db_session, password="ChangeMe123!")

    assert second_result["created_users"] == 0
    assert second_result["updated_users"] == 0
    assert second_result["existing_users"] == 6
    assert second_result["created_memberships"] == 0
    assert second_result["updated_memberships"] == 0
    assert second_result["existing_memberships"] == 6
    assert db_session.scalar(select(func.count()).select_from(User)) == 6
    assert db_session.scalar(select(func.count()).select_from(CommitteeMember)) == 6


def test_seed_test_access_profiles_raises_clear_error_if_committee_is_missing(
    db_session: Session,
) -> None:
    _seed_required_committees(db_session, omit=AIRCRAFT_COMMITTEE)

    with pytest.raises(TestAccessSeedError, match=AIRCRAFT_COMMITTEE):
        seed_test_access_profiles(db_session, password="ChangeMe123!")


def test_seed_test_access_profiles_raises_clear_error_if_authority_level_mismatches(
    db_session: Session,
) -> None:
    _seed_required_committees(
        db_session,
        risk_management_authority_level=AuthorityLevel.LOW,
    )

    with pytest.raises(TestAccessSeedError, match="Authority Level mismatch"):
        seed_test_access_profiles(db_session, password="ChangeMe123!")
