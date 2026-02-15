#!/usr/bin/env pwsh
# Lanzar entrenamiento SAC

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "LANZANDO ENTRENAMIENTO SAC - DATOS OE2 REALES"
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Validar datos
Write-Host "VALIDANDO DATOS..." -ForegroundColor Yellow
python validate_datasets.py

Write-Host ""
Write-Host "INICIANDO ENTRENAMIENTO SAC..." -ForegroundColor Green
Write-Host "Configuración:"
Write-Host "  - Episodios: 10"
Write-Host "  - Timesteps: 87,600 (10 x 8,760)"
Write-Host "  - Learning Rate: 1e-4"
Write-Host "  - Buffer Size: 1,000,000"
Write-Host "  - Batch Size: 256"
Write-Host ""

# Lanzar entrenamiento
python scripts/train/train_sac_multiobjetivo.py
