# SAC Full Pipeline - Simple Version
# Python 3.11 Required

param(
    [int]$Episodes = 5
)

$ProjectRoot = "d:\diseñopvbesscar"
$Config = "configs/default.yaml"

Set-Location $ProjectRoot

Write-Host "`n=== SAC FULL PIPELINE ===" -ForegroundColor Cyan
Write-Host "Episode: $Episodes" -ForegroundColor Green
Write-Host "Config: $Config`n" -ForegroundColor Green

# Activate venv
Write-Host "[1/3] Activating Python 3.11 venv..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Stage 1: Build Dataset
Write-Host "`n[2/3] Building dataset from OE2 artifacts..." -ForegroundColor Cyan
python -m scripts.run_oe3_build_dataset --config $Config
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Dataset build failed!" -ForegroundColor Red
    exit 1
}

# Stage 2: Train SAC
Write-Host "`n[3/3] Training SAC ($Episodes episodes)..." -ForegroundColor Cyan
python -m scripts.run_oe3_simulate --config $Config --agent sac --sac-episodes $Episodes
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: SAC training failed!" -ForegroundColor Red
    exit 1
}

# Done
Write-Host "`n=== PIPELINE COMPLETED ===" -ForegroundColor Green
Write-Host "Results: outputs/oe3_simulations/sac/" -ForegroundColor Green
Write-Host "Checkpoints: checkpoints/sac/" -ForegroundColor Green
Write-Host "`n"
