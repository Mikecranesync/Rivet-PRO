# YCB - YouTube Channel Builder
# Docker container for 24/7 VPS deployment

FROM python:3.11-slim

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV YCB_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash ycb
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY ycb/ ./ycb/

# Create output directories
RUN mkdir -p /app/ycb_output /app/logs && \
    chown -R ycb:ycb /app

# Switch to non-root user
USER ycb

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from ycb.config import settings; print('OK')" || exit 1

# Default command - run daemon
CMD ["python", "-m", "ycb", "daemon"]
