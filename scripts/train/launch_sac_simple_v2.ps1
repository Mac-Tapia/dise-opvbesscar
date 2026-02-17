# -*- coding: utf-8 -*-
# ENTRENADOR SAC CON MONITOREO BASICO - PowerShell v7.2 (2026-02-16)

Clear-Host
Write-Host "="*100 -ForegroundColor Cyan
Write-Host "ENTRENADOR SAC CON MONITOREO BASICO" -ForegroundColor Green
Write-Host "="*100 -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$WORKSPACE = "d:\diseñopvbesscar"
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd HHmmss"

# Validacion basica
Write-Host "[CHECK] Validaciones iniciales..." -ForegroundColor Yellow
if (-not (Test-Path "$WORKSPACE\checkpoints\SAC")) {
    New-Item -ItemType Directory -Path "$WORKSPACE\checkpoints\SAC" -Force | Out-Null
    Write-Host "  ✓ Directorio SAC creado"
}

# Verificar datasets
$datasets = @(
    'data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv',
    'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'data/oe2/bess/bess_ano_2024.csv',
    'data/oe2/demandamallkwh/demandamallhorakwh.csv'
)

foreach ($dataset in $datasets) {
    if (Test-Path "$WORKSPACE\$dataset") {
        Write-Host "  ✓ $(Split-Path -Leaf $dataset)"
    } else {
        Write-Host "  ✗ FALTA: $dataset" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[TRAIN] Iniciando SAC..." -ForegroundColor Yellow
Write-Host ""

# Cambiar a workspace
Push-Location $WORKSPACE

# Ejecutar entrenamiento
python scripts/train/train_sac_multiobjetivo.py

$exitCode = $LASTEXITCODE

Pop-Location

Write-Host ""
Write-Host "="*100 -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "✓ SAC TRAINING COMPLETADO" -ForegroundColor Green
} else {
    Write-Host "✗ SAC TRAINING FALLÓ (exit: $exitCode)" -ForegroundColor Red
}
Write-Host "="*100 -ForegroundColor Cyan
Write-Host ""

exit $exitCode
