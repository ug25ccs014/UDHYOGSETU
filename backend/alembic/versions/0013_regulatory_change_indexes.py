"""Add indexes for regulatory change center queries.

Revision ID: 0013
Revises: 0012
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_knowledge_documents_supersedes_created_at",
        "knowledge_documents",
        ["supersedes_document_id", "created_at"],
    )
    op.create_index(
        "ix_knowledge_documents_latest_effective",
        "knowledge_documents",
        ["is_latest", "effective_date"],
    )
    op.create_index(
        "ix_knowledge_documents_department_sector",
        "knowledge_documents",
        ["department", "sector"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_documents_department_sector", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_latest_effective", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_supersedes_created_at", table_name="knowledge_documents")
