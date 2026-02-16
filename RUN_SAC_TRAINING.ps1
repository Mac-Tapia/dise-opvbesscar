#!/usr/bin/env pwsh
<#
.SYNOPSIS
    SAC Training Setup & Launch Script
    Automatiza: validación, verificación, ejecución de training

.DESCRIPTION
    Este script hacer:
    1. Validar ambiente Python
    2. Verificar datos
    3. Ejecutar entrenamiento SAC
    4. Monitorear progreso

.USAGE
    .\RUN_SAC_TRAINING.ps1
    .\RUN_SAC_TRAINING.ps1 -SkipValidation
    .\RUN_SAC_TRAINING.ps1 -MonitorOnly
#>

param(
    [switch]$SkipValidation = $false,
    [switch]$SkipTraining = $false,
    [switch]$MonitorOnly = $false,
    [switch]$CleanCheckpoints = $false
)

# Colors
$SUCCESS = "Green"
$ERROR_ = "Red"
$WARN = "Yellow"
$INFO = "Cyan"

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor $INFO
    Write-Host $Message -ForegroundColor $INFO
    Write-Host ("=" * 80) -ForegroundColor $INFO
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $SUCCESS
}

function Write-Error_ {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $ERROR_
}

function Write-Warning_ {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $WARN
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor $INFO
}

# ============================================================================
# MAIN SCRIPT BEGINS
# ============================================================================

Write-Header "SAC TRAINING SETUP & LAUNCHER"

$workspace = Get-Location
Write-Info "Workspace: $workspace"

# ============================================================================
# STEP 1: VALIDATION
# ============================================================================

if (-not $SkipValidation -and -not $MonitorOnly) {
    Write-Header "STEP 1: VALIDATING ENVIRONMENT"
    
    Write-Info "Running VALIDAR_SAC_TRAINING.py..."
    python VALIDAR_SAC_TRAINING.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error_ "Validation failed. Fix issues before continuing."
        Write-Info "See PLAN_ACCION_SAC_TRAINING.md for troubleshooting"
        exit 1
    }
    
    Write-Success "Validation complete - environment is ready"
}

# ============================================================================
# STEP 2: CLEANUP CHECKPOINTS (OPTIONAL)
# ============================================================================

if ($CleanCheckpoints) {
    Write-Header "STEP 2: CLEANING OLD CHECKPOINTS"
    
    $checkpoint_dir = Join-Path $workspace "checkpoints/SAC"
    
    if (Test-Path $checkpoint_dir) {
        Write-Warning_ "Deleting existing checkpoints in $checkpoint_dir"
        Remove-Item "$checkpoint_dir/*" -Force -ErrorAction SilentlyContinue
        Write-Success "Checkpoints deleted - will train from scratch"
    } else {
        Write-Info "No existing checkpoints found"
    }
} else {
    Write-Info "Keeping existing checkpoints (will continue training)"
    Write-Info "To start fresh, run: .\RUN_SAC_TRAINING.ps1 -CleanCheckpoints"
}

# ============================================================================
# STEP 3: VERIFY TENSORBOARD READY
# ============================================================================

if (-not $SkipTraining -and -not $MonitorOnly) {
    Write-Header "STEP 3: TENSORBOARD INFORMATION"
    
    Write-Info "TensorBoard will be available at:"
    Write-Info "  http://localhost:6006"
    Write-Info ""
    Write-Info "To launch TensorBoard in another terminal:"
    Write-Info "  tensorboard --logdir=runs/ --port=6006"
    Write-Info ""
    Write-Info "Monitor these metrics:"
    Write-Info "  - rollout/ep_reward_mean (should NOT be flat at 0.0)"
    Write-Info "  - train/actor_loss (should decrease/stabilize)"
    Write-Info "  - train/critic_loss (should stabilize at 0.05-0.5)"
}

# ============================================================================
# STEP 4: LAUNCH TRAINING
# ============================================================================

if (-not $SkipTraining -and -not $MonitorOnly) {
    Write-Header "STEP 4: LAUNCHING SAC TRAINING"
    
    Write-Info "Starting training..."
    Write-Info "Expected duration: 5-7 hours on RTX 4060 GPU"
    Write-Info "Press Ctrl+C to stop (checkpoints are auto-saved)"
    Write-Info ""
    
    $start_time = Get-Date
    Write-Info "Training started at: $start_time"
    
    # Run training
    python scripts/train/train_sac_multiobjetivo.py
    
    $exit_code = $LASTEXITCODE
    $end_time = Get-Date
    $duration = New-TimeSpan -Start $start_time -End $end_time
    
    if ($exit_code -eq 0) {
        Write-Success "Training completed successfully!"
        Write-Info "Total duration: $($duration.Hours)h $($duration.Minutes)m"
    } else {
        Write-Error_ "Training failed with exit code: $exit_code"
        Write-Info "Check output above for error details"
        exit $exit_code
    }
}

# ============================================================================
# STEP 5: LAUNCH TENSORBOARD (OPTIONAL)
# ============================================================================

if (-not $MonitorOnly) {
    Write-Header "STEP 5: POST-TRAINING INSTRUCTIONS"
    
    Write-Info "Training complete! Next steps:"
    Write-Info ""
    Write-Info "1. View results in TensorBoard:"
    Write-Info "   tensorboard --logdir=runs/ --port=6006"
    Write-Info "   Then open: http://localhost:6006"
    Write-Info ""
    Write-Info "2. Check saved checkpoints:"
    Write-Info "   ls checkpoints/SAC/"
    Write-Info ""
    Write-Info "3. Save changes to repository:"
    Write-Info "   git add -A"
    Write-Info "   git commit -m 'Fix: Complete SAC training pipeline'"
    Write-Info "   git push"
    Write-Info ""
    Write-Info "4. Read the analysis documents:"
    Write-Info "   - DIAGNOSTICO_SAC_EPISODE_RETURN_CERO.md"
    Write-Info "   - RESULTADO_ENTRENAMIENTO_SAC.txt"
    
} elseif ($MonitorOnly) {
    Write-Header "STEP 5: LAUNCHING TENSORBOARD MONITOR"
    
    Write-Info "Launching TensorBoard in browser..."
    
    # Start TensorBoard
    Write-Info "Command: tensorboard --logdir=runs/ --port=6006"
    
    # Try to open in browser
    $tensorboard_url = "http://localhost:6006"
    try {
        Start-Process $tensorboard_url
        Write-Success "TensorBoard opened at $tensorboard_url"
    } catch {
        Write-Warning_ "Could not auto-open browser. Visit manually: $tensorboard_url"
    }
    
    # Start TensorBoard process
    tensorboard --logdir=runs/ --port=6006
}

# ============================================================================
# FINISHED
# ============================================================================

Write-Header "PROCESS COMPLETE"
Write-Success "SAC training pipeline is ready or completed"
Write-Info "For more details, see: RESUMEN_FINAL_SAC_TRAINING.md"

exit 0
