import argparse
import uuid

from app.core.database import SessionLocal
from app.services.bootstrap_service import (
    BootstrapBusinessRuleError,
    bootstrap_governance_admin,
)
from app.services.default_risk_matrix_seed_service import (
    DefaultRiskMatrixSeedError,
    seed_default_risk_matrix,
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "seed-default-risk-matrix":
        return _seed_default_risk_matrix(args)
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


if __name__ == "__main__":
    raise SystemExit(main())
