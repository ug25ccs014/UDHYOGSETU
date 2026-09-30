"""Add entrepreneur business profiles and reusable document vault links."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("business_type", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("pan", sa.String(length=10), nullable=True),
        sa.Column("gstin", sa.String(length=15), nullable=True),
        sa.Column("udyam_number", sa.String(length=100), nullable=True),
        sa.Column("registered_address", sa.Text(), nullable=True),
        sa.Column("registered_state", sa.String(length=100), nullable=True),
        sa.Column("registered_district", sa.String(length=100), nullable=True),
        sa.Column("registered_city", sa.String(length=100), nullable=True),
        sa.Column("registered_pincode", sa.String(length=10), nullable=True),
        sa.Column("verification_status", postgresql.JSONB(), nullable=True),
        sa.Column("verification_details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=True, default=datetime.utcnow),
    )
    op.create_index(
        "ix_business_profiles_user_id",
        "business_profiles",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "business_profile_documents",
        sa.Column(
            "business_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_profiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("added_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )


def downgrade() -> None:
    op.drop_table("business_profile_documents")
    op.drop_index("ix_business_profiles_user_id", table_name="business_profiles")
    op.drop_table("business_profiles")
