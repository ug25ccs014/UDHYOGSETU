"""Initial migration - create all tables."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, default="ENTREPRENEUR"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    # NOTE: users.email is declared unique=True, index=True above, which already
    # creates the unique index ix_users_email; an explicit create_index here
    # would raise DuplicateTableError on a fresh database.

    # Projects
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("business_type", sa.String(100)),
        sa.Column("industry", sa.String(100)),
        sa.Column("sector", sa.String(100)),
        sa.Column("project_stage", sa.String(100)),
        sa.Column("investment_amount", sa.Float()),
        sa.Column("location_state", sa.String(100)),
        sa.Column("location_district", sa.String(100)),
        sa.Column("location_city", sa.String(100)),
        sa.Column("location_industrial_area", sa.String(255)),
        sa.Column("location_midc_estate", sa.String(255)),
        sa.Column("land_type", sa.String(100)),
        sa.Column("employees", sa.Integer()),
        sa.Column("production_type", sa.String(100)),
        sa.Column("hazardous_materials", sa.Boolean(), default=False),
        sa.Column("has_boiler", sa.Boolean(), default=False),
        sa.Column("electricity_load", sa.Float()),
        sa.Column("water_consumption", sa.Float()),
        sa.Column("pollution_potential", sa.String(50)),
        sa.Column("building_type", sa.String(100)),
        sa.Column("is_new", sa.Boolean(), default=True),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    # NOTE: projects.user_id is declared index=True above, which already creates
    # ix_projects_user_id; an explicit create_index here would be a duplicate.

    # Approvals
    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("sector", sa.String(100)),
        sa.Column("is_mandatory", sa.Boolean(), default=False),
        sa.Column("risk_level", sa.String(50), default="MEDIUM"),
        sa.Column("estimated_processing_days", sa.Integer()),
        sa.Column("renewal_period_days", sa.Integer()),
        sa.Column("status", sa.String(50), default="NOT_STARTED"),
        sa.Column("application_id", sa.String(100)),
        sa.Column("submitted_at", sa.DateTime()),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("source", sa.String(255)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    # NOTE: approvals.project_id is declared index=True above, which already
    # creates ix_approvals_project_id; an explicit create_index here would be
    # a duplicate.

    # Documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer()),
        sa.Column("status", sa.String(50), default="UPLOADED"),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("extracted_fields", postgresql.JSONB(), default={}),
        sa.Column("custom_metadata", postgresql.JSONB(), default={}),
        sa.Column("validation_errors", postgresql.JSON(), default=[]),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # Compliance Items
    op.create_table(
        "compliance_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("requirement", sa.String(255), nullable=False),
        sa.Column("frequency", sa.String(50)),
        sa.Column("due_date", sa.DateTime()),
        sa.Column("status", sa.String(50), default="ON_TRACK"),
        sa.Column("last_completed", sa.DateTime()),
        sa.Column("next_due", sa.DateTime()),
        sa.Column("document_required", sa.Boolean(), default=False),
        sa.Column("source", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # Approval Rules
    op.create_table(
        "approval_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("sector", sa.String(100)),
        sa.Column("location", sa.String(100)),
        sa.Column("conditions", postgresql.JSONB(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), default=False),
        sa.Column("required_documents", postgresql.JSON(), default=[]),
        sa.Column("dependencies", postgresql.JSON(), default=[]),
        sa.Column("estimated_processing_days", sa.Integer()),
        sa.Column("renewal_period_days", sa.Integer()),
        sa.Column("risk_level", sa.String(50), default="MEDIUM"),
        sa.Column("source", sa.String(255)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # Schemes
    op.create_table(
        "schemes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("sector", sa.String(100)),
        sa.Column("location", sa.String(100)),
        sa.Column("min_investment", sa.Float()),
        sa.Column("max_investment", sa.Float()),
        sa.Column("eligible_entity", sa.String(100)),
        sa.Column("employee_requirement", sa.Integer()),
        sa.Column("benefits", postgresql.JSON(), default=[]),
        sa.Column("application_period", sa.String(255)),
        sa.Column("required_documents", postgresql.JSON(), default=[]),
        sa.Column("source", sa.String(255)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # Knowledge Documents (RAG)
    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("department", sa.String(100)),
        sa.Column("document_type", sa.String(100)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("jurisdiction", sa.String(100)),
        sa.Column("sector", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # Knowledge Chunks
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_documents.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("embedding", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("details", postgresql.JSONB(), default={}),
        sa.Column("ip_address", sa.String(50)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )

    # Notifications
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("category", sa.String(50), default="general"),
        sa.Column("severity", sa.String(20), default="info"),
        sa.Column("is_read", sa.Boolean(), default=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("reference_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("read_at", sa.DateTime()),
    )

    # Approval Documents association table
    op.create_table(
        "approval_documents",
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("approvals.id"), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("approval_documents")
    op.drop_table("notifications")
    op.drop_table("audit_logs")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("schemes")
    op.drop_table("approval_rules")
    op.drop_table("compliance_items")
    op.drop_table("documents")
    op.drop_table("approvals")
    op.drop_table("projects")
    op.drop_table("users")