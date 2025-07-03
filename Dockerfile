# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    XDG_CACHE_HOME=/app/.cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    libpq-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the application code
COPY . .

# Set script permissions before switching to non-root user
RUN chmod +x /app/docker-entrypoint.sh /app/reset-super-admin.sh

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser -m

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/.cache/docling/models /home/appuser /opt/docling-models && \
    chown -R appuser:appuser /app /home/appuser /opt/docling-models

# Switch to non-root user
USER appuser

# Pre-download Docling models to a permanent location
# Download models to /opt/docling-models which won't be affected by volume mounts
RUN mkdir -p /opt/docling-models/docling/models && \
    docling-tools models download --output-dir /opt/docling-models/docling/models && \
    echo "Models downloaded to /opt/docling-models/docling/models" && \
    find /opt/docling-models -type f | head -10 && \
    echo "Total model files: $(find /opt/docling-models -type f | wc -l)"

# Expose the port the app runs on
EXPOSE 35430

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:35430/health || exit 1

# Command to run the application
CMD ["/app/docker-entrypoint.sh"]
