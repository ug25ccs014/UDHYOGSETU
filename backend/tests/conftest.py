"""Shared pytest configuration for the UDYOGSETU backend.

The test suite runs against a throwaway SQLite database (file-backed) instead
of the PostgreSQL instance used in development/production. Environment
variables are configured here before any application module is imported so the
application's settings/engine are created against SQLite.
"""

import asyncio
import os
import tempfile
import warnings

# ---------------------------------------------------------------------------
# 1. Point the app at SQLite BEFORE importing any application module.
# ---------------------------------------------------------------------------
_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "udyogsetu_test.db")
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH.replace(os.sep, '/')}"
os.environ["ALLOWED_HOSTS"] = '["*"]'
# Rate limiting uses the local Redis; disable it for the test suite so the
# shared limiter cannot 429 across many tests that register users.
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Long fixed key to avoid the PyJWT InsecureKeyLengthWarning in test output.
os.environ["JWT_SECRET_KEY"] = "test-secret-" + "x" * 32

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated",
)

# ---------------------------------------------------------------------------
# 2. Allow PostgreSQL-only column types to render on SQLite.
# ---------------------------------------------------------------------------
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.compiler import compiles


@compiles(postgresql.UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(postgresql.JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# ---------------------------------------------------------------------------
# 3. Rebuild the engine/session machinery against a file-backed SQLite DB.
#    NullPool gives every checkout its own connection, which is safe across
#    the different event loops used by pytest-asyncio and TestClient.
# ---------------------------------------------------------------------------
def _bootstrap_test_db() -> None:
    from sqlalchemy.pool import NullPool

    import app.models  # noqa: F401 - registers tables on Base.metadata
    from app import main
    from app.core import database

    test_engine = database.build_engine(
        f"sqlite+aiosqlite:///{_TEST_DB_PATH.replace(os.sep, '/')}",
        poolclass=NullPool,
    )

    database.engine = test_engine
    database.AsyncSessionLocal = database.async_sessionmaker(
        test_engine,
        class_=database.AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    main.engine = test_engine

    async def _create_schema():
        async with test_engine.begin() as conn:
            await conn.run_sync(database.Base.metadata.create_all)

    asyncio.run(_create_schema())


_bootstrap_test_db()

# ---------------------------------------------------------------------------
# 4. Fixtures.
# ---------------------------------------------------------------------------
import pytest


@pytest.fixture(autouse=True)
def _clean_db():
    """Reset the test database before every test for full isolation.

    The file-backed SQLite DB is shared by TestClient (``test_api.py``) and the
    async session fixture (``test_services.py``), so tables are dropped and
    recreated ahead of each test.
    """
    from app.core.database import Base, engine

    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())
    yield


@pytest.fixture
async def db_session():
    """Provide an async database session backed by the test SQLite DB."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session