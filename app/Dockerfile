# ----- Builder Stage -----
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy only what's needed for package installation
COPY pyproject.toml .
COPY src/ src/

# Install dependencies using uv
RUN uv pip install --no-cache-dir --system .

# Update apt for any additional packages
RUN apt-get update

# ----- Runtime Stage -----
FROM python:3.12-slim-bookworm

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser

# Set up directory structure
WORKDIR /app/src
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    LOG_DIR=/app/logs

# Create logs directory with proper permissions
RUN mkdir -p /app/logs && \
    chown appuser:appuser /app/logs

# Install vim for debugging and any system dependencies
RUN apt-get update && \
    apt-get install -y \
        vim \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies and application code from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ .

# Copy Alembic configuration to /app/
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic/

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Default command for production
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 