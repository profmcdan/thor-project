# Stage 1: Build virtualenv using uv
FROM python:3.13-slim AS builder

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency configuration files
COPY pyproject.toml uv.lock ./

# Sync project dependencies using uv cache
RUN --mount=type=cache,target=/root/.cache/uv \
    /bin/uv sync --frozen --no-install-project --no-dev

# Stage 2: Minimal, secure runtime
FROM python:3.13-slim AS runtime

# Install runtime requirements (libpq5 for PostgreSQL integration, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create a non-privileged user and group for security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copy built virtual environment from builder stage
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Update PATH to prioritize virtualenv binaries
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code and execution scripts
COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup docker-entrypoint.sh /app/docker-entrypoint.sh

# Set working directory to django application root containing manage.py
WORKDIR /app/app

# Environment settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to security-hardened user
USER appuser

# Expose Gunicorn port
EXPOSE 8000

# Set entrypoint and default target execution command
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["web"]
