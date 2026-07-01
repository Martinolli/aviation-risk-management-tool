"""add risk evidence

Revision ID: 20260701_0005
Revises: 20260621_0004
Create Date: 2026-07-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260701_0005"
down_revision: str | None = "20260621_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_evidence",
        sa.Column("risk_record_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["archived_by_user_id"],
            ["users.id"],
            name="fk_risk_evidence_archived_by_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["risk_record_id"],
            ["risk_records.id"],
            name="fk_risk_evidence_risk_record_id",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name="fk_risk_evidence_uploaded_by_user_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_risk_evidence_risk_record_id",
        "risk_evidence",
        ["risk_record_id"],
    )
    op.create_index(
        "ix_risk_evidence_uploaded_by_user_id",
        "risk_evidence",
        ["uploaded_by_user_id"],
    )
    op.create_index(
        "ix_risk_evidence_is_active", "risk_evidence", ["is_active"]
    )


def downgrade() -> None:
    op.drop_index("ix_risk_evidence_is_active", table_name="risk_evidence")
    op.drop_index(
        "ix_risk_evidence_uploaded_by_user_id", table_name="risk_evidence"
    )
    op.drop_index(
        "ix_risk_evidence_risk_record_id", table_name="risk_evidence"
    )
    op.drop_table("risk_evidence")
