"""Persist government query/response lifecycle.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("government_application_id", sa.String(length=100), nullable=True),
        sa.Column("system", sa.String(length=100), nullable=True),
        sa.Column("query_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="OPEN"),
        sa.Column("response_draft", sa.Text(), nullable=True),
        sa.Column("submitted_response", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_application_queries_approval_id", "application_queries", ["approval_id"])
    op.create_index("ix_application_queries_government_application_id", "application_queries", ["government_application_id"])
    op.create_index("ix_application_queries_query_fingerprint", "application_queries", ["query_fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_application_queries_query_fingerprint", table_name="application_queries")
    op.drop_index("ix_application_queries_government_application_id", table_name="application_queries")
    op.drop_index("ix_application_queries_approval_id", table_name="application_queries")
    op.drop_table("application_queries")
