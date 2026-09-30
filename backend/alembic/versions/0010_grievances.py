"""Add grievance and escalation case management.

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grievances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("application_id", sa.String(length=100), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="OPEN"),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("assigned_officer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("response_target_at", sa.DateTime(), nullable=True),
        sa.Column("escalated_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_officer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, column in [
        ("ix_grievances_user_id", "user_id"),
        ("ix_grievances_project_id", "project_id"),
        ("ix_grievances_approval_id", "approval_id"),
        ("ix_grievances_application_id", "application_id"),
        ("ix_grievances_department", "department"),
        ("ix_grievances_priority", "priority"),
        ("ix_grievances_status", "status"),
        ("ix_grievances_assigned_officer_id", "assigned_officer_id"),
        ("ix_grievances_response_target_at", "response_target_at"),
    ]:
        op.create_index(name, "grievances", [column])

    op.create_table(
        "grievance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grievance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["grievance_id"], ["grievances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grievance_events_grievance_id", "grievance_events", ["grievance_id"])
    op.create_index("ix_grievance_events_actor_user_id", "grievance_events", ["actor_user_id"])
    op.create_index("ix_grievance_events_created_at", "grievance_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_grievance_events_created_at", table_name="grievance_events")
    op.drop_index("ix_grievance_events_actor_user_id", table_name="grievance_events")
    op.drop_index("ix_grievance_events_grievance_id", table_name="grievance_events")
    op.drop_table("grievance_events")
    for name, _column in reversed([
        ("ix_grievances_response_target_at", "response_target_at"),
        ("ix_grievances_assigned_officer_id", "assigned_officer_id"),
        ("ix_grievances_status", "status"),
        ("ix_grievances_priority", "priority"),
        ("ix_grievances_department", "department"),
        ("ix_grievances_application_id", "application_id"),
        ("ix_grievances_approval_id", "approval_id"),
        ("ix_grievances_project_id", "project_id"),
        ("ix_grievances_user_id", "user_id"),
    ]):
        op.drop_index(name, table_name="grievances")
    op.drop_table("grievances")
