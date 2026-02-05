#!/bin/bash
# ================================================================================
# SAC FULL PIPELINE (Dataset Building + Training)
# Purpose: Execute complete pipeline from dataset construction to SAC training
# Runtime: Continuous execution with error handling
# Python: 3.11 ONLY
# ================================================================================

set -e  # Exit on error

# Configuration
PROJECT_ROOT="d:/diseñopvbesscar"
EPISODES=${1:-5}
CONFIG_PATH="${2:-configs/default.yaml}"
LOG_DIR="$PROJECT_ROOT/logs/sac_pipeline"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/sac_pipeline_$TIMESTAMP.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log() {
    local level=$1
    shift
    local message="$@"
    local ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$ts] [$level] $message" | tee -a "$LOG_FILE"
}

header() {
    echo -e "${CYAN}========== $1 ==========${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓ $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}✗ ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠ WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

# Initialize
mkdir -p "$LOG_DIR"
echo "Pipeline execution started at $(date)" > "$LOG_FILE"

# Check Python 3.11
header "Checking Python 3.11"
if ! command -v python &> /dev/null; then
    error "Python not found in PATH"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1)
success "Python version: $PYTHON_VERSION"

if [[ ! $PYTHON_VERSION =~ "3.11" ]]; then
    warning "Expected Python 3.11, got: $PYTHON_VERSION"
fi

# Check virtual environment
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    error "Virtual environment not found at $PROJECT_ROOT/.venv"
    exit 1
fi

success "Virtual environment found"

# Activate virtual environment
cd "$PROJECT_ROOT"
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

# Stage 1: Build Dataset
header "STAGE 1: BUILDING DATASET"
log "INFO" "Executing: python -m scripts.run_oe3_build_dataset --config $CONFIG_PATH"

if python -m scripts.run_oe3_build_dataset --config "$CONFIG_PATH" 2>&1 | tee -a "$LOG_FILE"; then
    success "Dataset building completed"
else
    error "Dataset building failed"
    exit 1
fi

# Stage 2: Train SAC
header "STAGE 2: SAC TRAINING ($EPISODES episodes)"
log "INFO" "Training configuration:"
log "INFO" "  Episodes: $EPISODES"
log "INFO" "  Config: $CONFIG_PATH"
log "INFO" "  Timesteps (estimated): $((EPISODES * 8760))"

log "INFO" "Executing: python -m scripts.run_oe3_simulate --config $CONFIG_PATH --agent sac --sac-episodes $EPISODES"

if python -m scripts.run_oe3_simulate \
    --config "$CONFIG_PATH" \
    --agent sac \
    --sac-episodes "$EPISODES" 2>&1 | tee -a "$LOG_FILE"; then
    success "SAC training completed"
else
    error "SAC training failed"
    exit 1
fi

# Stage 3: Post-training analysis
header "STAGE 3: POST-TRAINING ANALYSIS"
log "INFO" "Generating comparison table..."

if python -m scripts.run_oe3_co2_table --config "$CONFIG_PATH" 2>&1 | tee -a "$LOG_FILE"; then
    success "Post-training analysis completed"
else
    warning "Post-training analysis had issues (non-critical)"
fi

# Display results
header "PIPELINE SUMMARY"
success "Full log saved to: $LOG_FILE"
success "Checkpoints available in: checkpoints/sac/"
success "Results available in: outputs/oe3_simulations/sac/"

echo -e "\n${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║               PIPELINE COMPLETED SUCCESSFULLY ✓                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

log "SUCCESS" "Pipeline execution completed successfully"
exit 0
