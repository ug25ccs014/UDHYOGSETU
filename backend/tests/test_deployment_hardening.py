"""Security/deployment hardening tests.

Covers production defaults that protect the deployed deployment:
- CORS restricts origins to the configured allow-list (no wildcard).
- CORS preflight (OPTIONS) responds with the expected origin headers.
- The app refuses to start when DEBUG=false with a missing/forbidden
  JWT secret so production never silently falls back to a weak secret.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.database import normalize_database_url
from app.main import app

client = TestClient(app)


def test_cors_blocks_disallowed_origin():
    """Requests with a foreign Origin must NOT receive CORS grant headers."""
    resp = client.get(
        "/health",
        headers={"Origin": "https://evil.example.com"},
    )
    assert "access-control-allow-origin" not in resp.headers


def test_cors_allows_trusted_local_origin_preflight():
    """OPTIONS preflight from a configured origin returns the expected grant."""
    origin = "http://localhost:3000"
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == origin


def test_production_fails_fast_without_jwt_secret():
    """ENVIRONMENT=production with a missing JWT secret must fail validation."""
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY="")


def test_production_rejects_forbidden_weak_secret():
    """Weak/placeholder JWT secrets must not be accepted for production."""
    for weak in ("secret", "changeme", "test-secret", "default-secret"):
        with pytest.raises(ValidationError):
            Settings(ENVIRONMENT="production", JWT_SECRET_KEY=weak)


def test_normalize_database_url_handles_railway_format():
    """A driver-less postgresql:// URL (Railway) gains the asyncpg driver."""
    assert (
        normalize_database_url("postgresql://user:pw@host:5432/db")
        == "postgresql+asyncpg://user:pw@host:5432/db"
    )
    assert (
        normalize_database_url("postgres://user:pw@host:5432/db")
        == "postgresql+asyncpg://user:pw@host:5432/db"
    )


def test_normalize_database_url_preserves_explicit_drivers_and_others():
    """Explicit asyncpg URLs and non-PostgreSQL URLs are left unchanged."""
    assert (
        normalize_database_url("postgresql+asyncpg://u:p@h/db")
        == "postgresql+asyncpg://u:p@h/db"
    )
    assert (
        normalize_database_url("sqlite+aiosqlite:///tmp/test.db")
        == "sqlite+aiosqlite:///tmp/test.db"
    )


def test_normalize_database_url_translates_sslmode_to_asyncpg_ssl():
    """``sslmode=require`` (Neon) must become asyncpg's ``ssl=require``.

    asyncpg raises ``TypeError: connect() got an unexpected keyword argument
    'sslmode'`` when the libpq-style parameter is forwarded, so it is renamed
    to the asyncpg-native ``ssl`` key (same value vocabulary).
    """
    assert (
        normalize_database_url(
            "postgresql://user:pw@db.example.com:5432/db?sslmode=require"
        )
        == "postgresql+asyncpg://user:pw@db.example.com:5432/db?ssl=require"
    )
    assert (
        normalize_database_url(
            "postgres://user:pw@db.example.com:5432/db?sslmode=require"
        )
        == "postgresql+asyncpg://user:pw@db.example.com:5432/db?ssl=require"
    )


def test_normalize_database_url_sslmode_values_preserved():
    """Each libpq ``sslmode`` value is kept under the ``ssl`` key."""
    for mode in ("disable", "allow", "prefer", "verify-ca", "verify-full"):
        assert (
            normalize_database_url(f"postgresql://u:p@h/db?sslmode={mode}")
            == f"postgresql+asyncpg://u:p@h/db?ssl={mode}"
        )


def test_normalize_database_url_preserves_asyncpg_supported_params():
    """Valid asyncpg.connect() query parameters survive normalization."""
    normalized = normalize_database_url(
        "postgresql://u:p@h/db?sslmode=require&timeout=10&target_session_attrs=read-write"
    )
    assert "sslmode" not in normalized
    assert "ssl=require" in normalized
    assert "timeout=10" in normalized
    assert "target_session_attrs=read-write" in normalized


def test_normalize_database_url_explicit_ssl_wins_and_local_untouched():
    """An explicit ``ssl`` parameter wins; local URLs gain only the driver."""
    assert (
        normalize_database_url(
            "postgresql://u:p@h/db?sslmode=require&ssl=prefer"
        )
        == "postgresql+asyncpg://u:p@h/db?ssl=prefer"
    )
    assert (
        normalize_database_url("postgresql://udyogsetu:password@localhost:5432/udyogsetu")
        == "postgresql+asyncpg://udyogsetu:password@localhost:5432/udyogsetu"
    )


def test_normalize_neon_url_sslmode_and_channel_binding():
    """A provider-generated Neon URL with both params is fully normalized."""
    url = (
        "postgresql://username:s3cr3t@ep-cute-mouse-123456.us-east-2.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    assert normalize_database_url(url) == (
        "postgresql+asyncpg://username:s3cr3t@ep-cute-mouse-123456.us-east-2.aws.neon.tech/neondb"
        "?ssl=require"
    )


def test_normalize_channel_binding_variants_are_dropped():
    """channel_binding cannot be honored by asyncpg and is always removed."""
    for mode in ("require", "prefer", "disable"):
        assert (
            normalize_database_url(f"postgresql://u:p@h/db?channel_binding={mode}")
            == "postgresql+asyncpg://u:p@h/db"
        )


def test_normalize_drops_other_asyncpg_unsupported_params():
    """libpq-only params (application_name, connect_timeout) also break asyncpg and are dropped."""
    assert (
        normalize_database_url(
            "postgresql://u:p@h/db?channel_binding=require&application_name=app&connect_timeout=9"
        )
        == "postgresql+asyncpg://u:p@h/db"
    )


def test_normalize_preserves_credentials_verbatim():
    """Username and percent-encoded password survive exactly."""
    assert normalize_database_url(
        "postgresql://user:pa%40ss@ep-x.region.aws.neon.tech/db?sslmode=require&channel_binding=require"
    ) == (
        "postgresql+asyncpg://user:pa%40ss@ep-x.region.aws.neon.tech/db?ssl=require"
    )


def test_asyncpg_engine_receives_only_supported_keywords():
    """The kwargs SQLAlchemy forwards to asyncpg contain only supported keywords.

    Mirrors the original crash (``unexpected keyword argument``): after
    normalization the forwarded ``connect()`` kwargs must be a subset of the
    installed asyncpg's accepted parameters.
    """
    from inspect import Parameter, signature

    import asyncpg
    from sqlalchemy.ext.asyncio import create_async_engine

    url = normalize_database_url(
        "postgres://user:pw@ep-random-2.us-east-2.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    engine = create_async_engine(url)
    _, kwargs = engine.dialect.create_connect_args(engine.url)
    supported = {
        p.name
        for p in signature(asyncpg.connect).parameters.values()
        if p.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)
    }
    assert "sslmode" not in kwargs
    assert "channel_binding" not in kwargs
    assert set(kwargs) <= supported
    assert kwargs["ssl"] == "require"


def test_alembic_uses_app_url_normalization():
    """Alembic env.py drives migrations through the same normalize helper."""
    from pathlib import Path

    env_py = (Path(__file__).resolve().parent.parent / "alembic" / "env.py").read_text(
        encoding="utf-8"
    )
    assert "normalize_database_url" in env_py
    assert "normalize_database_url(settings.DATABASE_URL)" in env_py
