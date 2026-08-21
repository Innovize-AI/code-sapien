# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
ENV POETRY_VERSION=1.7.1
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev, create virtualenv in /app/.venv)
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-dev --no-interaction --no-ansi

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

# Set environment variables
ENV ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1

# Cloud Run uses port 8080 by default
EXPOSE 8080

# Build path to ensure modules are found
ENV PYTHONPATH=/app

# Run migrations and start application
CMD sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8080"
