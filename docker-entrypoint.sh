#!/bin/bash
# Docker entrypoint script for OE2→OE3 Pipeline
set -e

echo "=========================================="
echo "Iquitos CityLearn Pipeline - Docker Entry"
echo "=========================================="

# Verify Python version
python_version=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python: $python_version"

# Verify CUDA (if GPU available)
python -c "import torch; device='cuda' if torch.cuda.is_available() else 'cpu'; print(f'✓ Device: {device} (CUDA: {torch.cuda.is_available()})')" || echo "⚠ CUDA not available"

# Create necessary directories
mkdir -p /app/data/interim/oe2/{solar,chargers,bess}
mkdir -p /app/outputs/oe3/{checkpoints,results}
echo "✓ Directories created"

# Parse arguments
CONFIG_FILE=${1:-"/app/configs/default.yaml"}
SKIP_OE2=${2:-false}

echo ""
echo "Configuration: $CONFIG_FILE"
echo "Skip OE2: $SKIP_OE2"
echo ""

# Execute pipeline
if [ "$SKIP_OE2" = "true" ]; then
    echo "⏭ Skipping OE2 stages (resuming OE3)..."
    python -m scripts.run_oe3_simulate --config "$CONFIG_FILE"
    python -m scripts.run_oe3_co2_table --config "$CONFIG_FILE"
else
    echo "▶ Starting full OE2→OE3 pipeline..."
    python -m scripts.run_pipeline --config "$CONFIG_FILE"
fi

echo ""
echo "=========================================="
echo "Pipeline execution completed!"
echo "Results available in: /app/outputs/oe3/"
echo "=========================================="
