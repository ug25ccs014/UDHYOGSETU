"""Add the Explore Government Services catalog table.

Matches the SQLAlchemy ``GovernmentService`` model exactly (as ``create_all``
on startup would produce it): native PostgreSQL enum for ``status`` and
UUID/JSONB-equivalent column types.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

service_status_enum = postgresql.ENUM(
    "ACTIVE", "INACTIVE", name="servicestatus", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    service_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "government_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("authority", sa.String(length=255), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("service_type", sa.String(length=50), nullable=True),
        sa.Column("application_mode", sa.String(length=20), nullable=True),
        sa.Column(
            "status",
            service_status_enum,
            nullable=True,
        ),
        sa.Column("official_reference", sa.String(length=255), nullable=True),
        sa.Column("external_portal_url", sa.String(length=500), nullable=True),
        sa.Column("applicable_documents", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("fees", sa.String(length=255), nullable=True),
        sa.Column("eligibility_summary", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=True),
        sa.Column("sla_days", sa.Integer(), nullable=True),
        sa.Column("renewal_period_days", sa.Integer(), nullable=True),
        sa.Column(
            "approval_rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approval_rules.id"),
            nullable=True,
        ),
        sa.Column("gateway_system", sa.String(length=50), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_government_services_slug", "government_services", ["slug"], unique=True)
    op.create_index("ix_government_services_category", "government_services", ["category"])
    op.create_index("ix_government_services_approval_rule_id", "government_services", ["approval_rule_id"])


def downgrade() -> None:
    op.drop_index("ix_government_services_approval_rule_id", table_name="government_services")
    op.drop_index("ix_government_services_category", table_name="government_services")
    op.drop_index("ix_government_services_slug", table_name="government_services")
    op.drop_table("government_services")

    bind = op.get_bind()
    service_status_enum.drop(bind, checkfirst=True)