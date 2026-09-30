import secrets
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "UDYOGSETU"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://udyogsetu:password@localhost:5432/udyogsetu"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    AUTO_GENERATED_SECRET: bool = False

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
    ]
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    # Optional regex (full match) for origins that change per deployment, e.g. Vercel
    # preview URLs:  https://udhyogsetu[a-z0-9-]*\.vercel\.app
    CORS_ORIGIN_REGEX: str = ""

    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_LLM_PROVIDER: str = "gemini"

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_PROVIDER: str = "mock"

    UPLOAD_DIRECTORY: str = "/tmp/udyogsetu/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    DATA_DIRECTORY: str = "./data"

    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_ENABLED: bool = True

    # Government integrations are prototype-only until an authorized adapter is configured.
    GOVERNMENT_INTEGRATION_PROVIDER: str = "prototype"
    GOVERNMENT_PROTOTYPE_SCENARIO: str = "si_demo"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        cls._jwt_was_empty = not v
        if not v:
            environment = (info.data.get("ENVIRONMENT") or "development").lower()
            if environment == "production":
                raise ValueError(
                    "JWT_SECRET_KEY is required in production. Generate one with "
                    "`python -c \"import secrets; print(secrets.token_hex(32))\"` "
                    "and set it in your environment."
                )
            v = secrets.token_hex(32)
        environment = (info.data.get("ENVIRONMENT") or "development").lower()
        weak = {s.strip().lower() for s in (
            "secret", "changeme", "development-secret",
            "test-secret", "default-secret", "password", "123456",
        )}
        if environment == "production" and (
            v.strip().lower() in weak or len(v) < 32
        ):
            raise ValueError(
                "JWT_SECRET_KEY in production must be a strong secret "
                "(at least 32 characters and not a placeholder). Generate one "
                "with `python -c \"import secrets; print(secrets.token_hex(32))\"`."
            )
        return v

    @model_validator(mode="after")
    def _mark_auto_generated_secret(self) -> "Settings":
        self.AUTO_GENERATED_SECRET = bool(getattr(type(self), "_jwt_was_empty", False))
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
