"""add electronic approvals

Revision ID: 20260717_0008
Revises: 20260707_0007
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260717_0008"
down_revision: str | None = "20260707_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "electronic_approvals",
        sa.Column("target_type", sa.String(length=17), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("risk_record_id", sa.Uuid(), nullable=True),
        sa.Column("risk_decision_id", sa.Uuid(), nullable=True),
        sa.Column("committee_id", sa.Uuid(), nullable=True),
        sa.Column("authority_level", sa.String(length=6), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approval_statement", sa.Text(), nullable=False),
        sa.Column("acknowledgement_text", sa.Text(), nullable=False),
        sa.Column("meaning_of_signature", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("approval_hash", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["committee_id"], ["committees.id"]),
        sa.ForeignKeyConstraint(["risk_decision_id"], ["risk_decisions.id"]),
        sa.ForeignKeyConstraint(["risk_record_id"], ["risk_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_electronic_approvals_target",
        "electronic_approvals",
        ["target_type", "target_id"],
    )
    op.create_index(
        "ix_electronic_approvals_risk_record_id",
        "electronic_approvals",
        ["risk_record_id"],
    )
    op.create_index(
        "ix_electronic_approvals_risk_decision_id",
        "electronic_approvals",
        ["risk_decision_id"],
    )
    op.create_index(
        "ix_electronic_approvals_approved_by_user_id",
        "electronic_approvals",
        ["approved_by_user_id"],
    )
    op.create_index(
        "ix_electronic_approvals_approved_at",
        "electronic_approvals",
        ["approved_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_electronic_approvals_approved_at", table_name="electronic_approvals")
    op.drop_index(
        "ix_electronic_approvals_approved_by_user_id",
        table_name="electronic_approvals",
    )
    op.drop_index(
        "ix_electronic_approvals_risk_decision_id",
        table_name="electronic_approvals",
    )
    op.drop_index(
        "ix_electronic_approvals_risk_record_id",
        table_name="electronic_approvals",
    )
    op.drop_index("ix_electronic_approvals_target", table_name="electronic_approvals")
    op.drop_table("electronic_approvals")
