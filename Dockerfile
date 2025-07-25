# WebUIFlasher Docker Image
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    udev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for all users
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    chmod +x /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY scripts/ ./scripts/
# NOTE: sources.yaml and sources_example.yaml are NOT copied - they must be mounted from outside
COPY img/ ./img/
COPY README.md ./
COPY docker-entrypoint.sh ./

# Create directories
RUN mkdir -p tmpfw

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Install Python dependencies
RUN uv sync --frozen

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint (using root for better device access)
ENTRYPOINT ["./docker-entrypoint.sh"]
