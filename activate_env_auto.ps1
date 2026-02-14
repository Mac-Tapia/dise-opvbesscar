# Script de activacion automatica del ambiente virtual
# Ejecutar: . .\activate_env_auto.ps1

$venvPath = ".\.venv\Scripts\Activate.ps1"

if (Test-Path $venvPath) {
    & $venvPath
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✓ AMBIENTE VIRTUAL ACTIVADO (.venv)" -ForegroundColor Green
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Python: $(python --version)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Comandos disponibles:"-ForegroundColor Yellow
    Write-Host "  - python scripts/train/train_sac_multiobjetivo.py      SAC training" 
    Write-Host "  - python scripts/build/build_bess_dataset_simple.py    Build BESS"
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "ERROR: No se encontro .venv\Scripts\Activate.ps1" -ForegroundColor Red
    Write-Host "Ejecuta primero: python -m venv .venv" -ForegroundColor Yellow
}
