"""Add incentive application preparation/readiness cases.

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incentive_application_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("external_reference", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("readiness_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("prepared_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scheme_id"], ["schemes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "scheme_id", name="uq_incentive_case_project_scheme"),
    )
    op.create_index(
        "ix_incentive_application_cases_project_id",
        "incentive_application_cases",
        ["project_id"],
    )
    op.create_index(
        "ix_incentive_application_cases_scheme_id",
        "incentive_application_cases",
        ["scheme_id"],
    )
    op.create_index(
        "ix_incentive_application_cases_status",
        "incentive_application_cases",
        ["status"],
    )

    op.create_table(
        "incentive_application_documents",
        sa.Column("incentive_application_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incentive_application_case_id"],
            ["incentive_application_cases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("incentive_application_case_id", "document_id"),
    )
    op.create_index(
        "ix_incentive_application_documents_document_id",
        "incentive_application_documents",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incentive_application_documents_document_id",
        table_name="incentive_application_documents",
    )
    op.drop_table("incentive_application_documents")
    op.drop_index("ix_incentive_application_cases_status", table_name="incentive_application_cases")
    op.drop_index("ix_incentive_application_cases_scheme_id", table_name="incentive_application_cases")
    op.drop_index("ix_incentive_application_cases_project_id", table_name="incentive_application_cases")
    op.drop_table("incentive_application_cases")
