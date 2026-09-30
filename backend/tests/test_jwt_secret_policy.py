"""Regression tests: production environment requires an explicit JWT secret.

Previously an empty ``JWT_SECRET_KEY`` silently fell back to a per-process
random secret, so tokens became invalid on every restart and every replica in
a multi-instance deployment issued its own keys. In the production environment
an explicit secret is now mandatory (fail-fast at startup).
"""

import pytest
from pydantic import ValidationError


def test_production_requires_explicit_jwt_secret():
    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY="")


def test_development_allows_auto_generated_secret():
    from app.core.config import Settings

    settings = Settings(ENVIRONMENT="development", JWT_SECRET_KEY="")
    assert len(settings.JWT_SECRET_KEY) == 64
    assert settings.AUTO_GENERATED_SECRET is True