import logging
from functools import lru_cache
from inspect import Parameter, signature
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

_SSLMODE_VALUES = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}

# Fallback allow-list of asyncpg.connect() keywords, only used if asyncpg is
# unexpectedly unavailable (it is a hard runtime dependency). The primary
# source of truth is introspecting the installed asyncpg at runtime.
_ASYNCPG_CONNECT_ARGS_FALLBACK = {
    "dsn", "host", "port", "user", "password", "passfile", "service",
    "servicefile", "database", "loop", "timeout", "statement_cache_size",
    "max_cached_statement_lifetime", "max_cacheable_statement_size",
    "command_timeout", "ssl", "direct_tls", "connection_class", "record_class",
    "server_settings", "target_session_attrs", "krbsrvname", "gsslib",
}


@lru_cache(maxsize=1)
def _asyncpg_connect_arg_names() -> frozenset:
    """Keyword arguments accepted by the installed ``asyncpg.connect()``.

    Kept dynamic so the normalization tracks the driver actually installed,
    instead of a hardcoded assumption about its supported parameters.
    """
    try:
        import asyncpg

        return frozenset(
            name
            for name, param in signature(asyncpg.connect).parameters.items()
            if param.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)
        )
    except ImportError as exc:  # pragma: no cover - asyncpg is required; belt & braces
        logger.warning("asyncpg unavailable (%s); using static param allow-list", exc)
        return frozenset(_ASYNCPG_CONNECT_ARGS_FALLBACK)


def normalize_database_url(url: str | None) -> str:
    """Make a provider-generated PostgreSQL ``DATABASE_URL`` usable by asyncpg.

    Hosted providers (Neon, Render, Railway, ...) hand out URLs flavoured for
    libpq, whose query parameters are forwarded verbatim to
    ``asyncpg.connect()`` by SQLAlchemy's async dialect. asyncpg rejects any
    keyword it does not know, e.g.::

        TypeError: connect() got an unexpected keyword argument 'sslmode'
        TypeError: connect() got an unexpected keyword argument 'channel_binding'

    This normalizes once, up front:

    * ``postgresql://``/``postgres://`` -> ``postgresql+asyncpg://``
      (driver-less URLs would otherwise fall back to the uninstalled psycopg2
      sync dialect).
    * ``sslmode=<value>`` -> ``ssl=<value>`` -- asyncpg's ``ssl`` parameter
      accepts the same vocabulary (disable/allow/prefer/require/verify-ca/
      verify-full), so TLS requirements are preserved, never silently dropped.
    * ``channel_binding`` is removed: asyncpg implements no channel-binding
      negotiation, so no value can be honored. This does not weaken TLS --
      connection encryption is governed by ``sslmode``/``ssl``, which is kept
      and enforced. asyncpg simply performs (non-channel-bound) SCRAM-SHA-256,
      which Neon supports.
    * Any other query parameter whose name is not accepted by the installed
      ``asyncpg.connect()`` is removed too, with a warning, so providers can
      add more libpq-only options without breaking the connection. Valid
      asyncpg parameters (``timeout``, ``target_session_attrs``, ``options``,
      ...) are preserved along with credentials, host, port, database, password
      and explicit ``ssl``.

    Non-PostgreSQL URLs (e.g. SQLite tests) are returned unchanged.
    """
    if not url:
        return url or ""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("postgres", "postgresql", "postgresql+asyncpg"):
        return url

    accepted = _asyncpg_connect_arg_names()
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    has_explicit_ssl = any(key.lower() == "ssl" for key, _ in pairs)

    normalized: list[tuple[str, str]] = []
    dropped: list[str] = []
    for key, value in pairs:
        lower = key.lower()
        if lower == "sslmode":
            if value and value.lower() in _SSLMODE_VALUES and not has_explicit_ssl:
                normalized.append(("ssl", value))
            else:
                dropped.append(key)
        elif lower in accepted:
            normalized.append((key, value))
        else:
            dropped.append(key)

    if dropped:
        logger.warning(
            "Dropped URL query parameter(s) asyncpg cannot honor: %s "
            "(connection 'ssl' setting retained)", ", ".join(dropped),
        )

    return urlunparse(
        parsed._replace(
            scheme="postgresql+asyncpg",
            query=urlencode(normalized),
        )
    )


def _engine_kwargs(url: str) -> dict:
    """Return create_async_engine kwargs appropriate for the database URL.

    PostgreSQL (asyncpg) gets a real connection pool. SQLite test databases use
    a NullPool and reject PostgreSQL-only pool arguments (pool_size and
    max_overflow raise TypeError against SQLiteDialect_aiosqlite), so those
    arguments are only applied for PostgreSQL URLs.
    """
    kwargs: dict = {
        "echo": settings.DEBUG,
        "future": True,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    if url.startswith("postgresql"):
        kwargs.update(pool_size=20, max_overflow=10)
    return kwargs


def build_engine(url: str | None = None, **overrides):
    """Build an async engine for ``url`` (default: settings.DATABASE_URL).

    ``overrides`` are merged last so callers (e.g. the test bootstrap) can
    override behavior without re-implementing dialect awareness.
    """
    url = url or settings.DATABASE_URL
    kwargs = {**_engine_kwargs(url), **overrides}
    return create_async_engine(normalize_database_url(url), **kwargs)


engine = build_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
