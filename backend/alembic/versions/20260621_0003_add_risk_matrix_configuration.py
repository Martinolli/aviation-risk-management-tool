"""add risk matrix configuration

Revision ID: 20260621_0003
Revises: 20260621_0002
Create Date: 2026-06-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260621_0003"
down_revision: str | None = "20260621_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _reference_table(name: str, include_risk_fields: bool = False) -> None:
    columns = [
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("numeric_value", sa.Integer(), nullable=False),
    ]
    if include_risk_fields:
        columns.extend([
            sa.Column("color", sa.String(length=50), nullable=True),
            sa.Column("is_tolerable", sa.Boolean(), nullable=False),
            sa.Column("requires_mitigation", sa.Boolean(), nullable=False),
            sa.Column("requires_escalation", sa.Boolean(), nullable=False),
        ])
    columns.extend([
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("code"),
    ])
    op.create_table(name, *columns)
    op.create_index(op.f(f"ix_{name}_code"), name, ["code"], unique=True)


def upgrade() -> None:
    _reference_table("risk_severity_levels")
    _reference_table("risk_likelihood_levels")
    _reference_table("risk_levels", include_risk_fields=True)
    op.create_table(
        "risk_matrix_cells",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("severity_level_id", sa.Uuid(), nullable=False),
        sa.Column("likelihood_level_id", sa.Uuid(), nullable=False),
        sa.Column("risk_level_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["severity_level_id"], ["risk_severity_levels.id"]),
        sa.ForeignKeyConstraint(["likelihood_level_id"], ["risk_likelihood_levels.id"]),
        sa.ForeignKeyConstraint(["risk_level_id"], ["risk_levels.id"]),
        sa.ForeignKeyConstraint(["archived_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("severity_level_id", "likelihood_level_id"),
    )


def downgrade() -> None:
    op.drop_table("risk_matrix_cells")
    op.drop_index(op.f("ix_risk_levels_code"), table_name="risk_levels")
    op.drop_table("risk_levels")
    op.drop_index(op.f("ix_risk_likelihood_levels_code"), table_name="risk_likelihood_levels")
    op.drop_table("risk_likelihood_levels")
    op.drop_index(op.f("ix_risk_severity_levels_code"), table_name="risk_severity_levels")
    op.drop_table("risk_severity_levels")
