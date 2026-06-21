import argparse

from app.core.database import SessionLocal
from app.services.bootstrap_service import (
    BootstrapBusinessRuleError,
    bootstrap_governance_admin,
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command != "bootstrap-admin":
        return 2

    db = SessionLocal()
    try:
        result = bootstrap_governance_admin(
            db,
            admin_email=args.email,
            admin_display_name=args.display_name,
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


if __name__ == "__main__":
    raise SystemExit(main())
