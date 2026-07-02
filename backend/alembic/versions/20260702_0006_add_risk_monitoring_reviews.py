"""add risk monitoring reviews

Revision ID: 20260702_0006
Revises: 20260701_0005
Create Date: 2026-07-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260702_0006"
down_revision: str | None = "20260701_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_monitoring_reviews",
        sa.Column("risk_record_id", sa.Uuid(), nullable=False),
        sa.Column("monitoring_owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("review_frequency", sa.String(length=100), nullable=True),
        sa.Column("next_review_date", sa.Date(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("effectiveness_review", sa.Text(), nullable=True),
        sa.Column("review_outcome", sa.String(length=22), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("closure_reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
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
        sa.ForeignKeyConstraint(["risk_record_id"], ["risk_records.id"]),
        sa.ForeignKeyConstraint(["monitoring_owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_risk_monitoring_reviews_risk_record_id",
        "risk_monitoring_reviews",
        ["risk_record_id"],
    )
    op.create_index(
        "ix_risk_monitoring_reviews_monitoring_owner_user_id",
        "risk_monitoring_reviews",
        ["monitoring_owner_user_id"],
    )
    op.create_index(
        "ix_risk_monitoring_reviews_next_review_date",
        "risk_monitoring_reviews",
        ["next_review_date"],
    )
    op.create_index(
        "ix_risk_monitoring_reviews_status",
        "risk_monitoring_reviews",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_risk_monitoring_reviews_status", table_name="risk_monitoring_reviews")
    op.drop_index(
        "ix_risk_monitoring_reviews_next_review_date",
        table_name="risk_monitoring_reviews",
    )
    op.drop_index(
        "ix_risk_monitoring_reviews_monitoring_owner_user_id",
        table_name="risk_monitoring_reviews",
    )
    op.drop_index(
        "ix_risk_monitoring_reviews_risk_record_id",
        table_name="risk_monitoring_reviews",
    )
    op.drop_table("risk_monitoring_reviews")
