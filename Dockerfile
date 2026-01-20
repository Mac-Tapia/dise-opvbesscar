# Multi-stage build for PVBESSCAR RL Energy Management
# Stage 1: Builder - Download and build dependencies
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libopenblas-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements*.txt ./

# Create wheels for dependencies (with caching)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip wheel -r requirements.txt --no-cache-dir --wheel-dir /wheels

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim

LABEL maintainer="Energy Systems Lab" \
    version="1.0.0" \
    description="RL-based building energy management system"

WORKDIR /app

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas-dev \
    libgomp1 \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install pip and wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --no-index --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Copy project files
COPY . .

# Install project in editable mode
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=4 \
    PYTHONPATH=/app:$PYTHONPATH

# Create data directories
RUN mkdir -p /app/data/interim/oe2/{solar,chargers,bess} \
    && mkdir -p /app/outputs/oe3/{checkpoints,results,analyses} \
    && mkdir -p /app/configs

# Verify Python version and key dependencies
RUN python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'; import stable_baselines3; import gymnasium; import numpy; import pandas; print('✓ All dependencies verified')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import stable_baselines3; print('healthy')" || exit 1

# Use tini as init to handle signals properly
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default: Run pipeline
CMD ["python", "-m", "scripts.run_pipeline", "--config", "configs/default.yaml"]
