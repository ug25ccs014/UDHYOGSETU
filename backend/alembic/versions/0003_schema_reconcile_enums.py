"""Reconcile enum columns and nullability with the current SQLAlchemy models.

After 0002 the migration-produced schema still diverged from the models:

    * users.role, approvals.status, documents.status, compliance_items.status
      were created as VARCHAR(length=50) but the models declare native
      PostgreSQL ENUM types (UserRole, ApprovalStatus, DocumentStatus,
      ComplianceStatus).
    * knowledge_chunks.text was created nullable but the model declares
      nullable=False.

This migration converts those columns to native ENUM types and tightens the
NOT NULL constraint, matching exactly what Base.metadata (create_all) would
produce.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


user_role_enum = postgresql.ENUM(
    "ENTREPRENEUR", "OFFICER", "ADMIN", name="userrole",
)
approval_status_enum = postgresql.ENUM(
    "NOT_STARTED", "DRAFT", "SUBMITTED", "UNDER_REVIEW", "QUERY_RAISED",
    "INSPECTION", "APPROVED", "REJECTED", "EXPIRED", "CANCELED",
    name="approvalstatus",
)
document_status_enum = postgresql.ENUM(
    "UPLOADED", "PROCESSING", "VERIFIED", "WARNING", "REJECTED", "EXPIRED",
    "MISSING", name="documentstatus",
)
compliance_status_enum = postgresql.ENUM(
    "ON_TRACK", "AT_RISK", "OVERDUE", name="compliancestatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    # Create the native PostgreSQL enum types before the columns reference them.
    for enum in (user_role_enum, approval_status_enum, document_status_enum, compliance_status_enum):
        enum.create(bind, checkfirst=True)

    op.alter_column(
        "users", "role",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.Enum("ENTREPRENEUR", "OFFICER", "ADMIN", name="userrole"),
        existing_nullable=False,
        postgresql_using="role::userrole",
    )
    op.alter_column(
        "approvals", "status",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.Enum(
            "NOT_STARTED", "DRAFT", "SUBMITTED", "UNDER_REVIEW", "QUERY_RAISED",
            "INSPECTION", "APPROVED", "REJECTED", "EXPIRED", "CANCELED",
            name="approvalstatus",
        ),
        existing_nullable=True,
        postgresql_using="status::approvalstatus",
    )
    op.alter_column(
        "documents", "status",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.Enum(
            "UPLOADED", "PROCESSING", "VERIFIED", "WARNING", "REJECTED",
            "EXPIRED", "MISSING", name="documentstatus",
        ),
        existing_nullable=True,
        postgresql_using="status::documentstatus",
    )
    op.alter_column(
        "compliance_items", "status",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.Enum("ON_TRACK", "AT_RISK", "OVERDUE", name="compliancestatus"),
        existing_nullable=True,
        postgresql_using="status::compliancestatus",
    )
    op.alter_column(
        "knowledge_chunks", "text",
        existing_type=sa.TEXT(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "knowledge_chunks", "text",
        existing_type=sa.TEXT(),
        nullable=True,
    )
    op.alter_column(
        "compliance_items", "status",
        existing_type=compliance_status_enum,
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )
    op.alter_column(
        "documents", "status",
        existing_type=document_status_enum,
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )
    op.alter_column(
        "approvals", "status",
        existing_type=approval_status_enum,
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )
    op.alter_column(
        "users", "role",
        existing_type=user_role_enum,
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )
    # Drop the enum types now that no column references them.
    bind = op.get_bind()
    for enum in (compliance_status_enum, document_status_enum, approval_status_enum, user_role_enum):
        enum.drop(bind, checkfirst=True)
