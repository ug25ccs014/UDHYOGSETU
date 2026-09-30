"""Reconcile the schema with the current SQLAlchemy models (spec drift).

After 0001 was released, the models gained several tables and columns that
were never reflected in a migration:

    * government_applications          (spec §19 - live gov status tracking)
    * ai_event_logs                    (spec §34 - AI observability)
    * knowledge_documents.date | effective_date | effective_to |
      supersedes_document_id | version | is_latest | superseded_by_document_id
    * knowledge_chunks.text + custom_metadata (0001 created `content` instead)

A production database may already have some of these (e.g. because the app
startup runs Base.metadata.create_all, which creates missing tables but never
alters existing tables). This migration is therefore fully idempotent: every
DDL is guarded by an existence check, so it is safe to run on either a fresh
database (created purely by 0001) or an existing deployment.

Existing data is never destroyed. Where 0001 named a chunk column `content`,
the rows are copied into the new `text` column and `content` is only dropped
when it is empty (i.e. a freshly created table).
"""

import logging

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

# ---------------------------------------------------------------------------
# Idempotency helpers
# ---------------------------------------------------------------------------


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _column_exists(inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def _index_exists(inspector, table: str, index_name: str) -> bool:
    return any(i["name"] == index_name for i in inspector.get_indexes(table))


def _column_nullable(inspector, table: str, column: str) -> bool:
    for c in inspector.get_columns(table):
        if c["name"] == column:
            return bool(c.get("nullable", True))
    return True


def _ensure_column(inspector, table: str, column) -> object:
    """Add a column only if it does not already exist; return a fresh inspector."""
    if not _column_exists(inspector, table, column.name):
        op.add_column(table, column)
        log.info("Added %s.%s", table, column.name)
    return _inspector()


def _ensure_index(inspector, table: str, column: str, index_name: str) -> object:
    """Create an index only if it does not already exist; return a fresh inspector."""
    if not _index_exists(inspector, table, index_name):
        op.create_index(index_name, table, [column])
        log.info("Created index %s", index_name)
    return _inspector()


def upgrade() -> None:
    inspector = _inspector()

    # ------------------------------------------------------------------
    # 1. government_applications (spec §19)
    # ------------------------------------------------------------------
    if not _table_exists(inspector, "government_applications"):
        op.create_table(
            "government_applications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "approval_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("approvals.id"),
                nullable=True,
            ),
            sa.Column(
                "project_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("projects.id"),
                nullable=False,
            ),
            sa.Column("system", sa.String(100), nullable=False),
            sa.Column("government_application_id", sa.String(100), nullable=False),
            sa.Column("last_synced_status", sa.String(50), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(), nullable=True),
            sa.Column("raw_response", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        log.info("Created table government_applications")

    inspector = _ensure_index(
        inspector, "government_applications", "approval_id",
        "ix_government_applications_approval_id",
    )
    inspector = _ensure_index(
        inspector, "government_applications", "project_id",
        "ix_government_applications_project_id",
    )

    # ------------------------------------------------------------------
    # 2. ai_event_logs (spec §34) - the DB column is literally named
    #    "metadata" to match the model's reserved-name override.
    # ------------------------------------------------------------------
    if not _table_exists(inspector, "ai_event_logs"):
        op.create_table(
            "ai_event_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("request_type", sa.String(50), nullable=False),
            sa.Column("model", sa.String(100), nullable=True),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("token_count", sa.Integer(), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=False),
            sa.Column("error_kind", sa.String(100), nullable=True),
            sa.Column("metadata", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        log.info("Created table ai_event_logs")

    inspector = _ensure_index(
        inspector, "ai_event_logs", "user_id", "ix_ai_event_logs_user_id",
    )
    inspector = _ensure_index(
        inspector, "ai_event_logs", "project_id", "ix_ai_event_logs_project_id",
    )

    # ------------------------------------------------------------------
    # 3. knowledge_documents - add versioning / metadata columns
    # ------------------------------------------------------------------
    for name in ("date", "effective_date", "effective_to"):
        inspector = _ensure_column(
            inspector, "knowledge_documents", sa.Column(name, sa.DateTime(), nullable=True)
        )
    inspector = _ensure_column(
        inspector, "knowledge_documents", sa.Column("version", sa.String(50), nullable=True)
    )
    inspector = _ensure_column(
        inspector, "knowledge_documents", sa.Column("is_latest", sa.Boolean(), nullable=True)
    )
    for name in ("supersedes_document_id", "superseded_by_document_id"):
        inspector = _ensure_column(
            inspector, "knowledge_documents",
            sa.Column(name, postgresql.UUID(as_uuid=True), nullable=True),
        )

    # ------------------------------------------------------------------
    # 4. knowledge_chunks - ensure text + custom_metadata exist and are
    #    nullable (models declare them nullable). Migrate 0001's `content`
    #    column into `text`, copying any rows, dropping `content` only when
    #    it is empty.
    # ------------------------------------------------------------------
    if not _column_exists(inspector, "knowledge_chunks", "text"):
        if _column_exists(inspector, "knowledge_chunks", "content"):
            op.add_column("knowledge_chunks", sa.Column("text", sa.Text(), nullable=True))
            op.execute("UPDATE knowledge_chunks SET text = content")
            has_content = (
                op.get_bind()
                .execute(
                    sa.text(
                        "SELECT 1 FROM knowledge_chunks "
                        "WHERE content IS NOT NULL AND content <> '' LIMIT 1"
                    )
                )
                .first()
                is not None
            )
            if not has_content:
                op.drop_column("knowledge_chunks", "content")
                log.info("knowledge_chunks: migrated content -> text (content was empty)")
            else:
                log.info("knowledge_chunks: kept non-empty content; added text beside it")
        else:
            op.add_column("knowledge_chunks", sa.Column("text", sa.Text(), nullable=True))
            log.info("knowledge_chunks: added text (no content column present)")
        inspector = _inspector()

    inspector = _ensure_column(
        inspector, "knowledge_chunks",
        sa.Column("custom_metadata", postgresql.JSONB(), nullable=True),
    )

    # Relax NOT NULL on document_id / chunk_index so a database produced purely
    # by 0001 matches the nullable model columns (idempotent).
    for col in ("document_id", "chunk_index"):
        if not _column_nullable(inspector, "knowledge_chunks", col):
            existing_type = (
                postgresql.UUID(as_uuid=True) if col == "document_id" else sa.Integer()
            )
            op.alter_column(
                "knowledge_chunks", col,
                existing_type=existing_type,
                nullable=True,
            )
            inspector = _inspector()


def downgrade() -> None:
    inspector = _inspector()

    # Drop the two tables added by this migration.
    if _table_exists(inspector, "ai_event_logs"):
        op.drop_table("ai_event_logs")
    if _table_exists(inspector, "government_applications"):
        op.drop_table("government_applications")

    # knowledge_documents: drop the versioning / metadata columns added above.
    inspector = _inspector()
    for name in ("superseded_by_document_id", "supersedes_document_id",
                 "is_latest", "version", "effective_to", "effective_date",
                 "date"):
        if _column_exists(inspector, "knowledge_documents", name):
            op.drop_column("knowledge_documents", name)
            inspector = _inspector()

    # knowledge_chunks: drop custom_metadata and text. If `text` never existed
    # before (created from 0001's empty `content`), restore `content` for the
    # round-trip; if `text` was pre-existing real data this is only a best-effort
    # structural downgrade and is guarded to avoid an erroneous duplicate column.
    inspector = _inspector()
    if _column_exists(inspector, "knowledge_chunks", "custom_metadata"):
        op.drop_column("knowledge_chunks", "custom_metadata")
        inspector = _inspector()
    if _column_exists(inspector, "knowledge_chunks", "text"):
        if not _column_exists(inspector, "knowledge_chunks", "content"):
            op.add_column("knowledge_chunks", sa.Column("content", sa.Text(), nullable=True))
        op.drop_column("knowledge_chunks", "text")
