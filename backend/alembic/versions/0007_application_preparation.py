"""Add saved application preparation overrides."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_preparations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "approval_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approvals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("overrides", postgresql.JSONB(), nullable=True),
        sa.Column("prepared_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("prepared_source_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("prepared_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_application_preparations_approval_id",
        "application_preparations",
        ["approval_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_preparations_approval_id",
        table_name="application_preparations",
    )
    op.drop_table("application_preparations")
