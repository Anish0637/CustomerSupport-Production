# ── Stage 1: dependency resolver ─────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Use same WORKDIR as runtime so venv shebang paths are identical
WORKDIR /app

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy lockfile and project manifest first (layer-cache friendly)
COPY pyproject.toml uv.lock ./

# Install all deps into /app/.venv — no editable install yet
RUN uv sync --frozen --no-install-project

# Copy source and install the project itself
COPY . .
RUN uv sync --frozen

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app

# Non-root user for container security
RUN useradd --create-home --shell /bin/sh appuser

# Copy installed packages and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/frontend /app/frontend

# Put venv on PATH; add frontend/ to PYTHONPATH so `from config import settings` resolves
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/frontend"
ENV PYTHONUNBUFFERED=1

# Sane defaults — override at runtime via env vars or .env
ENV HOST=0.0.0.0
ENV PORT=8501
ENV DEBUG=false
ENV HTTPS_ONLY=false

EXPOSE 8501

USER appuser

# The frontend module lives at /app/frontend/frontend.py
CMD ["uvicorn", "frontend.frontend:app", "--host", "0.0.0.0", "--port", "8501", "--log-level", "info"]
