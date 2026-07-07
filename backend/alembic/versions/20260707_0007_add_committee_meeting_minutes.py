"""add committee meeting minutes

Revision ID: 20260707_0007
Revises: 20260702_0006
Create Date: 2026-07-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260707_0007"
down_revision: str | None = "20260702_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "committee_meetings",
        sa.Column("committee_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("meeting_time_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("chair_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("agenda_summary", sa.Text(), nullable=True),
        sa.Column("discussion_summary", sa.Text(), nullable=True),
        sa.Column("decisions_summary", sa.Text(), nullable=True),
        sa.Column("action_items_summary", sa.Text(), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["committee_id"], ["committees.id"]),
        sa.ForeignKeyConstraint(["chair_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["finalized_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_committee_meetings_committee_id",
        "committee_meetings",
        ["committee_id"],
    )
    op.create_index(
        "ix_committee_meetings_meeting_date",
        "committee_meetings",
        ["meeting_date"],
    )
    op.create_index(
        "ix_committee_meetings_status",
        "committee_meetings",
        ["status"],
    )

    op.create_table(
        "committee_meeting_attendees",
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("attendee_name", sa.String(length=255), nullable=True),
        sa.Column("attendee_email", sa.String(length=320), nullable=True),
        sa.Column("role_label", sa.String(length=100), nullable=True),
        sa.Column("attendance_status", sa.String(length=8), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["meeting_id"], ["committee_meetings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_committee_meeting_attendees_meeting_id",
        "committee_meeting_attendees",
        ["meeting_id"],
    )

    op.create_table(
        "committee_meeting_risk_items",
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("risk_record_id", sa.Uuid(), nullable=False),
        sa.Column("agenda_item_number", sa.Integer(), nullable=True),
        sa.Column("discussion_summary", sa.Text(), nullable=True),
        sa.Column("decision_summary", sa.Text(), nullable=True),
        sa.Column("action_items", sa.Text(), nullable=True),
        sa.Column("linked_risk_decision_id", sa.Uuid(), nullable=True),
        sa.Column("follow_up_required", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("follow_up_notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["meeting_id"], ["committee_meetings.id"]),
        sa.ForeignKeyConstraint(["risk_record_id"], ["risk_records.id"]),
        sa.ForeignKeyConstraint(["linked_risk_decision_id"], ["risk_decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_committee_meeting_risk_items_meeting_id",
        "committee_meeting_risk_items",
        ["meeting_id"],
    )
    op.create_index(
        "ix_committee_meeting_risk_items_risk_record_id",
        "committee_meeting_risk_items",
        ["risk_record_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_committee_meeting_risk_items_risk_record_id",
        table_name="committee_meeting_risk_items",
    )
    op.drop_index(
        "ix_committee_meeting_risk_items_meeting_id",
        table_name="committee_meeting_risk_items",
    )
    op.drop_table("committee_meeting_risk_items")
    op.drop_index(
        "ix_committee_meeting_attendees_meeting_id",
        table_name="committee_meeting_attendees",
    )
    op.drop_table("committee_meeting_attendees")
    op.drop_index("ix_committee_meetings_status", table_name="committee_meetings")
    op.drop_index("ix_committee_meetings_meeting_date", table_name="committee_meetings")
    op.drop_index("ix_committee_meetings_committee_id", table_name="committee_meetings")
    op.drop_table("committee_meetings")
