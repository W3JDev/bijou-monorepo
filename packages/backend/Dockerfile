# Multi-stage build for smaller image size
# Reduces from 2.9GB to ~500MB by removing unnecessary packages

FROM python:3.11-slim as base

# Install only essential system dependencies
# ffmpeg + libopus: Required for voice note processing (OGG/Opus → MP3 conversion)
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    ffmpeg \
    libopus0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.optimized.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# CRITICAL: Verify entrypoint exists at build time.
# If this fails, it means src/core/bijou.py was excluded from the build context
# (wrong working directory or missing --config fly.production.toml during fly deploy).
# NEVER deploy without: fly deploy --app bijou-production --config fly.production.toml
RUN test -f src/core/bijou.py || (echo "FATAL: src/core/bijou.py missing from build context. Deploy from w3j-bijou-enterprise/ with: fly deploy --app bijou-production --config fly.production.toml" && exit 1)

# Create necessary directories
RUN mkdir -p /data/logs /data/tenants /data/credentials

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the server
CMD ["python", "-u", "src/core/bijou.py"]
