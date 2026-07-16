import argparse
import uuid

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.bootstrap_service import (
    BootstrapBusinessRuleError,
    bootstrap_governance_admin,
)
from app.services.default_risk_matrix_seed_service import (
    DefaultRiskMatrixSeedError,
    seed_default_risk_matrix,
)
from app.services.test_access_seed_service import (
    TestAccessSeedError,
    seed_test_access_profiles,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aviation Risk Management Tool CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    bootstrap_parser = subparsers.add_parser(
        "bootstrap-admin",
        help="Initialize default governance data and the first governance admin.",
    )
    bootstrap_parser.add_argument("--email", required=True)
    bootstrap_parser.add_argument("--display-name", required=True)
    bootstrap_parser.add_argument("--password")
    matrix_parser = subparsers.add_parser(
        "seed-default-risk-matrix",
        help="Seed the default aviation-style 5 x 5 risk matrix.",
    )
    matrix_parser.add_argument("--overwrite-existing", action="store_true")
    matrix_parser.add_argument("--changed-by-user-id", type=uuid.UUID)
    access_parser = subparsers.add_parser(
        "seed-test-access-profiles",
        help="Seed representative test committee users and memberships.",
    )
    access_parser.add_argument("--password", default="ChangeMe123!")
    access_parser.add_argument("--dry-run", action="store_true")
    subparsers.add_parser(
        "check-deployment-readiness",
        help="Validate Deployment Readiness production safety settings.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "seed-default-risk-matrix":
        return _seed_default_risk_matrix(args)
    if args.command == "seed-test-access-profiles":
        return _seed_test_access_profiles(args)
    if args.command == "check-deployment-readiness":
        return _check_deployment_readiness()
    if args.command != "bootstrap-admin":
        return 2

    db = SessionLocal()
    try:
        result = bootstrap_governance_admin(
            db,
            admin_email=args.email,
            admin_display_name=args.display_name,
            admin_password=args.password,
        )
        db.commit()
        user = result["user"]
        committee = result["committee"]
        membership = result["membership"]
        roles = result["roles"]
        summary = (
            user.email,
            str(user.id),
            committee.name,
            str(membership.id),
            ", ".join(role.name for role in roles),
        )
    except BootstrapBusinessRuleError as exc:
        db.rollback()
        print(f"Bootstrap failed: {exc}")
        return 1
    except Exception as exc:
        db.rollback()
        print(f"Bootstrap failed: {exc}")
        return 1
    finally:
        db.close()

    print("Bootstrap completed")
    print(f"Admin email: {summary[0]}")
    print(f"Admin user ID: {summary[1]}")
    print(f"Committee: {summary[2]}")
    print(f"Membership ID: {summary[3]}")
    print(f"Roles ensured: {summary[4]}")
    return 0


def _check_deployment_readiness() -> int:
    try:
        settings.validate_production_safety()
    except ValueError as exc:
        print(f"Deployment readiness check failed: {exc}")
        return 1
    print("Deployment readiness check passed.")
    return 0


def _seed_default_risk_matrix(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        result = seed_default_risk_matrix(
            db,
            changed_by_user_id=args.changed_by_user_id,
            overwrite_existing=args.overwrite_existing,
        )
        db.commit()
        summary = (
            result["created_severity_count"], result["updated_severity_count"],
            result["created_likelihood_count"], result["updated_likelihood_count"],
            result["created_risk_level_count"], result["updated_risk_level_count"],
            result["created_cell_count"], result["updated_cell_count"], result["total_cells"],
        )
    except DefaultRiskMatrixSeedError as exc:
        db.rollback()
        print(f"Default risk matrix seed failed: {exc}")
        return 1
    except Exception as exc:
        db.rollback()
        print(f"Default risk matrix seed failed: {exc}")
        return 1
    finally:
        db.close()

    print("Default risk matrix seed completed")
    print(f"Severity created: {summary[0]}, updated: {summary[1]}")
    print(f"Likelihood created: {summary[2]}, updated: {summary[3]}")
    print(f"Risk levels created: {summary[4]}, updated: {summary[5]}")
    print(f"Matrix cells created: {summary[6]}, updated: {summary[7]}")
    print(f"Total matrix cells: {summary[8]}")
    return 0


def _seed_test_access_profiles(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        result = seed_test_access_profiles(
            db,
            password=args.password,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    except TestAccessSeedError as exc:
        db.rollback()
        print(f"Test access profile seed failed: {exc}")
        return 1
    except Exception as exc:
        db.rollback()
        print(f"Test access profile seed failed: {exc}")
        return 1
    finally:
        db.close()

    print("Test access profile seed completed")
    print(
        "Users created: "
        f"{result['created_users']}, updated: {result['updated_users']}, "
        f"existing: {result['existing_users']}"
    )
    print(
        "Memberships created: "
        f"{result['created_memberships']}, updated: {result['updated_memberships']}, "
        f"existing: {result['existing_memberships']}"
    )
    for profile in result["profiles"]:
        committee = profile["committee"] or "not applicable"
        authority_level = profile["Authority Level"] or "not applicable"
        print(
            "- "
            f"{profile['email']} | {profile['display_name']} | "
            f"{committee} | Authority Level: {authority_level} | "
            f"membership: {profile['membership_status']}"
        )
    if args.dry_run:
        print("Dry run only; no database changes committed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
