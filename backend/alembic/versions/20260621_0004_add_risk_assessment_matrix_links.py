"""add risk assessment matrix links

Revision ID: 20260621_0004
Revises: 20260621_0003
Create Date: 2026-06-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260621_0004"
down_revision: str | None = "20260621_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("risk_assessments", sa.Column("severity_level_id", sa.Uuid(), nullable=True))
    op.add_column("risk_assessments", sa.Column("likelihood_level_id", sa.Uuid(), nullable=True))
    op.add_column("risk_assessments", sa.Column("calculated_risk_level_id", sa.Uuid(), nullable=True))
    op.add_column("risk_assessments", sa.Column("matrix_cell_id", sa.Uuid(), nullable=True))
    op.add_column("risk_assessments", sa.Column("calculated_score", sa.Integer(), nullable=True))
    op.add_column("risk_assessments", sa.Column("is_tolerable", sa.Boolean(), nullable=True))
    op.add_column("risk_assessments", sa.Column("requires_mitigation", sa.Boolean(), nullable=True))
    op.add_column("risk_assessments", sa.Column("requires_escalation", sa.Boolean(), nullable=True))
    op.create_foreign_key("fk_risk_assessments_severity_level", "risk_assessments", "risk_severity_levels", ["severity_level_id"], ["id"])
    op.create_foreign_key("fk_risk_assessments_likelihood_level", "risk_assessments", "risk_likelihood_levels", ["likelihood_level_id"], ["id"])
    op.create_foreign_key("fk_risk_assessments_calculated_risk_level", "risk_assessments", "risk_levels", ["calculated_risk_level_id"], ["id"])
    op.create_foreign_key("fk_risk_assessments_matrix_cell", "risk_assessments", "risk_matrix_cells", ["matrix_cell_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_risk_assessments_matrix_cell", "risk_assessments", type_="foreignkey")
    op.drop_constraint("fk_risk_assessments_calculated_risk_level", "risk_assessments", type_="foreignkey")
    op.drop_constraint("fk_risk_assessments_likelihood_level", "risk_assessments", type_="foreignkey")
    op.drop_constraint("fk_risk_assessments_severity_level", "risk_assessments", type_="foreignkey")
    op.drop_column("risk_assessments", "requires_escalation")
    op.drop_column("risk_assessments", "requires_mitigation")
    op.drop_column("risk_assessments", "is_tolerable")
    op.drop_column("risk_assessments", "calculated_score")
    op.drop_column("risk_assessments", "matrix_cell_id")
    op.drop_column("risk_assessments", "calculated_risk_level_id")
    op.drop_column("risk_assessments", "likelihood_level_id")
    op.drop_column("risk_assessments", "severity_level_id")
