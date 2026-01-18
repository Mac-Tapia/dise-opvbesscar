# Multi-stage build for Iquitos CityLearn OE2→OE3 Pipeline
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files and requirements
COPY requirements*.txt ./
COPY . .

# Create wheels for dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip wheel . --no-cache-dir --wheel-dir /wheels

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install project and dependencies
COPY . .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install --no-cache /wheels/* && \
    pip install -e .

# Set Python to unbuffered mode
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=4

# Create data directories
RUN mkdir -p /app/data/interim/oe2/{solar,chargers,bess} \
    && mkdir -p /app/outputs/oe3/{checkpoints,results}

# Verify Python version and dependencies
RUN python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'; print('✓ Python', sys.version)"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import torch; print('OK')" || exit 1

# Default: Run OE2 then OE3 pipeline
CMD ["python", "-m", "scripts.run_pipeline", "--config", "configs/default.yaml"]
