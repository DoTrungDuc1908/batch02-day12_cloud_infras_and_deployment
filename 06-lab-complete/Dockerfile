# ============================================================
# Production Dockerfile — Multi-stage, < 500 MB, non-root
# ============================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Non-root user
RUN groupadd -r agent && useradd -r -g agent -m -d /home/agent agent

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application
COPY app/ ./app/

RUN chown -R agent:agent /app /home/agent /opt/venv

USER agent

ENV PATH=/opt/venv/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

CMD ["python", "-m", "app.main"]
