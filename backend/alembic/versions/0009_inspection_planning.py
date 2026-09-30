"""Add inspection visit planning and common-visit coordination.

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inspection_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_officer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="SCHEDULED"),
        sa.Column("location", sa.String(length=1000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("checklist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("coordination_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assigned_officer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inspection_visits_project_id", "inspection_visits", ["project_id"])
    op.create_index("ix_inspection_visits_assigned_officer_id", "inspection_visits", ["assigned_officer_id"])
    op.create_index("ix_inspection_visits_scheduled_start", "inspection_visits", ["scheduled_start"])
    op.create_index("ix_inspection_visits_status", "inspection_visits", ["status"])

    op.create_table(
        "inspection_visit_approvals",
        sa.Column("inspection_visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inspection_visit_id"], ["inspection_visits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("inspection_visit_id", "approval_id"),
    )
    op.create_index("ix_inspection_visit_approvals_approval_id", "inspection_visit_approvals", ["approval_id"])


def downgrade() -> None:
    op.drop_index("ix_inspection_visit_approvals_approval_id", table_name="inspection_visit_approvals")
    op.drop_table("inspection_visit_approvals")
    op.drop_index("ix_inspection_visits_status", table_name="inspection_visits")
    op.drop_index("ix_inspection_visits_scheduled_start", table_name="inspection_visits")
    op.drop_index("ix_inspection_visits_assigned_officer_id", table_name="inspection_visits")
    op.drop_index("ix_inspection_visits_project_id", table_name="inspection_visits")
    op.drop_table("inspection_visits")
