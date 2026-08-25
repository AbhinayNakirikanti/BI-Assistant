# BI Assistant — Docker Image
# ─────────────────────────────────────────────
# Build:   docker build -t bi-assistant .
# Run:     docker run -p 8501:8501 --env-file .env bi-assistant
# Compose: docker compose up
# ─────────────────────────────────────────────

FROM python:3.12-slim

# Metadata
LABEL maintainer="MirAI School of Technology"
LABEL description="AI-powered Business Intelligence Platform"
LABEL version="2.0.0"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Working directory
WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY --chown=appuser:appuser . .

# Remove sensitive files from image
RUN rm -f .env

# Switch to non-root user
USER appuser

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start Streamlit
ENTRYPOINT ["python", "-m", "streamlit", "run", "app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]
