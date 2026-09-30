"""Add compliance/renewal lifecycle tracking.

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "renewal_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_approval_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("approvals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="DRAFT"),
        sa.Column("external_reference", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("prepared_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("renewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_approval_id"),
    )
    op.create_index("ix_renewal_cases_project", "renewal_cases", ["project_id"])
    op.create_index("ix_renewal_cases_source_approval", "renewal_cases", ["source_approval_id"])
    op.create_index("ix_renewal_cases_status", "renewal_cases", ["status"])
    op.create_table(
        "renewal_case_documents",
        sa.Column("renewal_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("renewal_cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("renewal_case_documents")
    op.drop_index("ix_renewal_cases_status", table_name="renewal_cases")
    op.drop_index("ix_renewal_cases_source_approval", table_name="renewal_cases")
    op.drop_index("ix_renewal_cases_project", table_name="renewal_cases")
    op.drop_table("renewal_cases")
