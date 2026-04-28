"""create model baseline

Revision ID: 20260428_0001
Revises:
Create Date: 2026-04-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260428_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), nullable=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False)


authority_level = _enum("authoritylevel", "LOW", "MIDDLE", "HIGH")
committee_type = _enum(
    "committeetype",
    "OPERATIONAL_BOARD",
    "RISK_MANAGEMENT_COMMITTEE",
    "EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE",
)
risk_domain = _enum(
    "riskdomain",
    "FLIGHT_TEST",
    "ENGINEERING",
    "MANUFACTURING",
    "QUALITY",
    "PRODUCTION",
    "SUPPLY_CHAIN",
    "OHSE",
    "CONTINUED_AIRWORTHINESS",
    "MAINTENANCE",
    "SUPPLIER_INTERFACE",
    "ORGANIZATIONAL",
    "OTHER",
)
risk_workflow_status = _enum(
    "riskworkflowstatus",
    "DRAFT",
    "SUBMITTED_TO_OPERATIONAL_BOARD",
    "UNDER_OPERATIONAL_BOARD_REVIEW",
    "APPROVED_AT_OPERATIONAL_BOARD",
    "ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE",
    "UNDER_RISK_MANAGEMENT_COMMITTEE_REVIEW",
    "APPROVED_AT_RISK_MANAGEMENT_COMMITTEE",
    "ESCALATED_TO_EXECUTIVE_COMMITTEE",
    "UNDER_EXECUTIVE_COMMITTEE_REVIEW",
    "ACCEPTED",
    "REJECTED",
    "RETURNED_FOR_REVISION",
    "CLOSED",
)
risk_lifecycle_status = _enum(
    "risklifecyclestatus",
    "OPEN",
    "UNDER_ANALYSIS",
    "PENDING_MITIGATION",
    "MITIGATION_IN_PROGRESS",
    "PENDING_RESIDUAL_RISK_REVIEW",
    "PENDING_ACCEPTANCE",
    "MONITORING",
    "CLOSED",
)
risk_assessment_type = _enum("riskassessmenttype", "INITIAL", "RESIDUAL")
risk_action_status = _enum(
    "riskactionstatus", "OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"
)
risk_decision_type = _enum(
    "riskdecisiontype",
    "APPROVE",
    "REJECT",
    "ESCALATE",
    "RETURN_FOR_REVISION",
    "ACCEPT_RESIDUAL_RISK",
    "CLOSE",
)
audit_action = _enum(
    "auditaction",
    "CREATE",
    "UPDATE",
    "ARCHIVE",
    "RESTORE",
    "SUBMIT",
    "APPROVE",
    "REJECT",
    "ESCALATE",
    "RETURN_FOR_REVISION",
    "GENERATE_REPORT",
    "LLM_ANALYSIS",
)


def upgrade() -> None:
    op.create_table(
        "users",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "roles",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    op.create_table(
        "committees",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("authority_level", authority_level, nullable=False),
        sa.Column("committee_type", committee_type, nullable=False),
        sa.Column("is_fixed", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "risk_records",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("risk_id", sa.String(length=50), nullable=True),
        sa.Column("problem_description", sa.Text(), nullable=False),
        sa.Column("source_trigger", sa.String(length=255), nullable=True),
        sa.Column("domain", risk_domain, nullable=False),
        sa.Column("board_of_origin_id", sa.Uuid(), nullable=True),
        sa.Column("system_scope", sa.Text(), nullable=True),
        sa.Column("central_event", sa.Text(), nullable=True),
        sa.Column("hazard_statement", sa.Text(), nullable=True),
        sa.Column("causes", sa.JSON(), nullable=True),
        sa.Column("consequences", sa.JSON(), nullable=True),
        sa.Column("existing_controls", sa.JSON(), nullable=True),
        sa.Column("workflow_status", risk_workflow_status, nullable=False),
        sa.Column("lifecycle_status", risk_lifecycle_status, nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["board_of_origin_id"], ["committees.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_records_risk_id"), "risk_records", ["risk_id"], unique=True)

    op.create_table(
        "committee_members",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("committee_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_label", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["committee_id"], ["committees.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "risk_assessments",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("risk_record_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_type", risk_assessment_type, nullable=False),
        sa.Column("severity", sa.String(length=100), nullable=False),
        sa.Column("likelihood", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.String(length=100), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("assessed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assessed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["risk_record_id"], ["risk_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "risk_actions",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("risk_record_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("action_owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", risk_action_status, nullable=False),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["action_owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["risk_record_id"], ["risk_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "risk_decisions",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("risk_record_id", sa.Uuid(), nullable=False),
        sa.Column("committee_id", sa.Uuid(), nullable=False),
        sa.Column("decision_type", risk_decision_type, nullable=False),
        sa.Column("decision_text", sa.Text(), nullable=False),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["committee_id"], ["committees.id"]),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["risk_record_id"], ["risk_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("field_name", sa.String(length=255), nullable=True),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "generated_reports",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("report_type", sa.String(length=100), nullable=False),
        sa.Column("risk_record_id", sa.Uuid(), nullable=True),
        sa.Column("committee_id", sa.Uuid(), nullable=True),
        sa.Column("generated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=True),
        sa.Column("template_version", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["committee_id"], ["committees.id"]),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["risk_record_id"], ["risk_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "llm_analyses",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("risk_record_id", sa.Uuid(), nullable=False),
        sa.Column("input_problem_description", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_accepted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["risk_record_id"], ["risk_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("llm_analyses")
    op.drop_table("generated_reports")
    op.drop_table("audit_logs")
    op.drop_table("risk_decisions")
    op.drop_table("risk_actions")
    op.drop_table("risk_assessments")
    op.drop_table("committee_members")
    op.drop_index(op.f("ix_risk_records_risk_id"), table_name="risk_records")
    op.drop_table("risk_records")
    op.drop_table("committees")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
