#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Lanzador RÁPIDO de entrenamiento serial
    
.DESCRIPTION
    Ejecuta automáticamente:
    1. Verifica entorno
    2. Lanza train_agents_serial_auto.py
    3. Monitorea progreso
    
.EXAMPLE
    .\launch_training.ps1
#>

Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "LANZADOR DE ENTRENAMIENTO SERIAL" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

# Verificar venv
if (-not $env:VIRTUAL_ENV) {
    Write-Host "`n⚠ Virtual environment NO ACTIVO" -ForegroundColor Yellow
    Write-Host "Activando: .venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    & ".venv\Scripts\Activate.ps1"
}

Write-Host "`n✓ Environment: $env:VIRTUAL_ENV" -ForegroundColor Green

# Quick verification
Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "VERIFICACIÓN RÁPIDA" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

$py_ver = & python --version 2>&1
Write-Host "✓ $py_ver" -ForegroundColor Green

$cuda = & python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')" 2>&1
Write-Host "✓ $cuda" -ForegroundColor Green

# Launch training
Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "INICIANDO ENTRENAMIENTO SERIAL" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

Write-Host "`n⏱️  Tiempo estimado: 4-7 horas" -ForegroundColor Yellow
Write-Host "💾 Espacio requerido: ~20 GB" -ForegroundColor Yellow
Write-Host "🖥️  Mantener terminal abierta durante entrenamiento" -ForegroundColor Yellow

Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan

$cmd = "python train_agents_serial_auto.py"
Write-Host "Ejecutando: $cmd`n" -ForegroundColor Cyan

& python train_agents_serial_auto.py

$exit_code = $LASTEXITCODE

# Show results location
Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
if ($exit_code -eq 0) {
    Write-Host "✓ ENTRENAMIENTO COMPLETADO" -ForegroundColor Green
}
else {
    Write-Host "⚠ ENTRENAMIENTO CON ERRORES" -ForegroundColor Yellow
}
Write-Host ("=" * 70) -ForegroundColor Cyan

Write-Host "`nResultados en:" -ForegroundColor Cyan
Write-Host "  📊 outputs/oe3/simulations/simulation_summary.json" -ForegroundColor Green
Write-Host "  📈 outputs/oe3/simulations/co2_comparison.md" -ForegroundColor Green
Write-Host "  💾 outputs/oe3/checkpoints/" -ForegroundColor Green

Write-Host "`nVer resultados:" -ForegroundColor Cyan
Write-Host "  cat outputs/oe3/simulations/simulation_summary.json | python -m json.tool" -ForegroundColor Gray

Write-Host ""
exit $exit_code
