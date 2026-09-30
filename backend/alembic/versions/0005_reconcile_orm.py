"""Reconcile legacy databases with the current ORM model state.

The current migration chain (``0001``-``0004``) already produces the exact
schema the ORM models declare: ``0001`` creates all ``index=True`` foreign-key
indexes and never created ``approvals.custom_metadata``. Some deployments were
originally initialised with ``Base.metadata.create_all()`` from an older model
revision and then stamped on to Alembic, leaving two kinds of drift:

* a stale ``approvals.custom_metadata`` column (removed from the model),
* missing FK indexes on ``approvals``/``projects``/``documents``/
  ``notifications``/``compliance_items``.

This migration is therefore defensive: every operation is guarded by an
inspector check so it is a no-op on a freshly migrated database and repairs a
legacy one. After applying, ``alembic check`` reports no drift on either.
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_FK_INDEXES = [
    ("approvals", "ix_approvals_project_id", "project_id"),
    ("projects", "ix_projects_user_id", "user_id"),
    ("documents", "ix_documents_project_id", "project_id"),
    ("notifications", "ix_notifications_user_id", "user_id"),
    ("compliance_items", "ix_compliance_items_project_id", "project_id"),
]


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in inspector.get_columns(table))


def _has_index(table: str, index: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    names = {i["name"] for i in inspector.get_indexes(table)}
    return index in names


def upgrade() -> None:
    if _has_column("approvals", "custom_metadata"):
        op.drop_column("approvals", "custom_metadata")

    for table, index, column in _FK_INDEXES:
        if not _has_index(table, index):
            op.create_index(index, table, [column])


def downgrade() -> None:
    for table, index, _column in reversed(_FK_INDEXES):
        if _has_index(table, index):
            op.drop_index(index, table_name=table)

    if not _has_column("approvals", "custom_metadata"):
        op.add_column(
            "approvals",
            sa.Column(
                "custom_metadata",
                sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )