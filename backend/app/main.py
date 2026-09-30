import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.ratelimit import RateLimitMiddleware

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _seed_data() -> None:
    """Idempotently load approval rules, schemes, and regulation knowledge."""
    from app.services.data_loader import RuleLoadingService

    root = os.path.join(settings.DATA_DIRECTORY, "")
    paths = {
        "approval_rules": os.path.join(root, "approvals", "approval_rules.json"),
        "schemes": os.path.join(root, "schemes", "schemes.json"),
        "regulations": os.path.join(root, "regulations"),
        "explore_services": os.path.join(root, "services", "explore_services.json"),
    }

    async with AsyncSessionLocal() as session:
        loader = RuleLoadingService(session)
        if os.path.exists(paths["approval_rules"]):
            await loader.load_approval_rules(paths["approval_rules"])
            logger.info("Seeded approval rules from %s", paths["approval_rules"])
        if os.path.exists(paths["schemes"]):
            await loader.load_schemes(paths["schemes"])
            logger.info("Seeded schemes from %s", paths["schemes"])
        if os.path.isdir(paths["regulations"]):
            await loader.load_knowledge_documents(paths["regulations"])
            logger.info("Seeded regulation knowledge docs from %s", paths["regulations"])
        if os.path.exists(paths["explore_services"]):
            await loader.load_explore_services(paths["explore_services"])
            logger.info("Seeded explore services from %s", paths["explore_services"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting UDYOGSETU API v%s (%s)", settings.APP_VERSION, settings.ENVIRONMENT)
    if settings.AUTO_GENERATED_SECRET:
        logger.warning("JWT_SECRET_KEY is not set; tokens will be invalidated on restart. Set JWT_SECRET_KEY in your environment for stable sessions.")
    if settings.ENVIRONMENT == "production":
        # Production schema is controlled exclusively by Alembic. The deployment
        # pipeline runs `alembic upgrade head` as a pre-deploy step (Railway) or
        # in the container start command (Docker Compose). Never mutate the
        # schema from application metadata at startup in production.
        logger.info(
            "Production startup (%s): schema managed by Alembic; overhead from create_all suppressed",
            settings.ENVIRONMENT,
        )
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready (created via metadata in %s mode)", settings.ENVIRONMENT)
    try:
        await _seed_data()
    except Exception:
        logger.exception("Startup data seeding failed (continuing without seed)")
    from app.workers.background import get_task_manager
    get_task_manager().start()
    yield
    logger.info("Shutting down UDYOGSETU API")
    await engine.dispose()


app = FastAPI(
    title="UDYOGSETU API",
    description="Industrial approval, compliance, and government-support platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
    logger.info(
        "%s %s -> %s (%.1fms) [%s]",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "-")
    logger.exception("Unhandled exception on %s %s [request_id=%s]", request.method, request.url.path, request_id)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

from app.audit.middleware import audit_logging_middleware

app.middleware("http")(audit_logging_middleware)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: database unreachable")
        db_status = "error"
    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
