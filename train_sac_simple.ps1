#!/usr/bin/env pwsh
# ENTRENAMIENTO SAC - SIMPLE Y ROBUSTO SIN CARACTERES PROBLEMATICOS

$env:PYTHONIOENCODING = 'utf-8'

# Header
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SAC TRAINING v9.3" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Status: SAC clean, PPO/A2C protected" -ForegroundColor Green
Write-Host "GPU: RTX 4060 8.6GB CUDA 12.1" -ForegroundColor Green
Write-Host "Data: OE2 real 8,760 hours validated" -ForegroundColor Green
Write-Host "Estimated: 5-7 hours" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Paths
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log_file = "outputs/sac_training_${timestamp}.log"
$metrics_file = "outputs/sac_metrics_${timestamp}.csv"

Write-Host "Log file: $log_file" -ForegroundColor White
Write-Host "Starting training..." -ForegroundColor Green
Write-Host ""

# Ensure outputs dir exists
New-Item -Path "outputs" -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null

# Run training
try {
    python scripts/train/train_sac_multiobjetivo.py 2>&1 | Tee-Object -FilePath $log_file
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "TRAINING COMPLETED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Training failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Post-validation
Write-Host ""
Write-Host "Validating results..." -ForegroundColor Cyan

$sac_count = (Get-ChildItem checkpoints/SAC -Filter "*.zip" -ErrorAction SilentlyContinue).Count
$ppo_count = (Get-ChildItem checkpoints/PPO -Filter "*.zip" -ErrorAction SilentlyContinue).Count
$a2c_count = (Get-ChildItem checkpoints/A2C -Filter "*.zip" -ErrorAction SilentlyContinue).Count

Write-Host "SAC checkpoints: $sac_count (NEW)" -ForegroundColor Green
Write-Host "PPO checkpoints: $ppo_count (PROTECTED)" -ForegroundColor Green
Write-Host "A2C checkpoints: $a2c_count (PROTECTED)" -ForegroundColor Green

Write-Host ""
Write-Host "Log saved to: $log_file" -ForegroundColor White
Write-Host "Done." -ForegroundColor Green
