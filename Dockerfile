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
COPY requirements.txt requirements-citylearn-v2.txt ./

# Create wheels for dependencies (excluir paquete local iquitos-citylearn)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    grep -vE '^(iquitos-citylearn|#|\s*$)' requirements.txt > /tmp/req_filtered.txt && \
    pip wheel -r /tmp/req_filtered.txt --no-cache-dir --wheel-dir /wheels && \
    pip wheel --no-deps --no-cache-dir --wheel-dir /wheels \
        "citylearn>=2.0.0,<3.0" "jsonschema>=4.0.0,<5.0"

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
    PYTHONPATH=/app/src:/app:$PYTHONPATH

# Create data and training directories
RUN mkdir -p /app/data/interim/oe2/{solar,chargers,bess} \
    && mkdir -p /app/outputs/oe3/{checkpoints,results,analyses} \
    && mkdir -p /app/outputs/sac_training \
    && mkdir -p /app/checkpoints/SAC_CityLearn \
    && mkdir -p /app/checkpoints/PPO_CityLearn \
    && mkdir -p /app/checkpoints/A2C_CityLearn \
    && mkdir -p /app/logs/training/sac_citylearn \
    && mkdir -p /app/logs/tensorboard/sac_citylearn \
    && mkdir -p /app/configs

# Verify Python version and key dependencies
RUN python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'; import stable_baselines3; import gymnasium; import numpy; import pandas; print('✓ All dependencies verified')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import stable_baselines3; print('healthy')" || exit 1

# Use tini as init to handle signals properly
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default: ejecutar entrypoint (soporte MODE=sac para entrenamiento SAC)
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "--", "/docker-entrypoint.sh"]
CMD ["pipeline"]
