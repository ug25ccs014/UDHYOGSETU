# UDYOGSETU backend for Hugging Face Spaces (Docker SDK).
#
# Hugging Face Spaces builds a Dockerfile found at the repository ROOT and
# expects the app to listen on port 7860. This mirrors
# infrastructure/docker/Dockerfile.backend (context = repo root) with Spaces
# port defaults. It is NOT used by docker-compose or CI, which reference the
# Dockerfiles under infrastructure/docker/ explicitly.

# Stage 1: build wheels
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: runtime
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    tesseract-ocr \
    libtesseract-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY data ./data

RUN mkdir -p /var/uploads

# Hugging Face Spaces serves the public proxy on port 7860.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]