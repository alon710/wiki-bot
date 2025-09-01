# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Create non-root user
RUN adduser --disabled-password --gecos '' --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Export dependencies to requirements.txt using uv
RUN uv export --format requirements-txt --no-hashes --output-file requirements.txt

# Install dependencies using uv pip
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Change ownership to app user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "main.py"]