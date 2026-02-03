#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick test de baselines duales CON/SIN solar

.DESCRIPTION
    Ejecuta ambos baselines y valida la funcionalidad

.EXAMPLE
    .\test_dual_baselines.ps1
#>

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "TEST: Dual Baselines (CON/SIN Solar)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
$PythonCmd = & { python --version 2>&1; $? }
if (-not $PythonCmd) {
    Write-Host "❌ ERROR: Python no está disponible" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Python encontrado" -ForegroundColor Green
python --version

Write-Host ""
Write-Host "PASO 1: Ejecutar baselines duales..." -ForegroundColor Yellow
Write-Host "   (Duración: ~20 segundos)" -ForegroundColor Gray
Write-Host ""

# Run dual baselines
python -m scripts.run_dual_baselines --config configs/default.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ ERROR ejecutando baselines" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "PASO 2: Validar resultados..." -ForegroundColor Yellow
Write-Host "   (Duración: ~5 segundos)" -ForegroundColor Gray
Write-Host ""

# Run validation
python scripts/test_dual_baselines.py
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ ERROR en validación" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "✅ TEST COMPLETADO EXITOSAMENTE" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

Write-Host "ARCHIVOS GENERADOS:" -ForegroundColor Cyan
Write-Host "  • outputs/baselines/with_solar/" -ForegroundColor Gray
Write-Host "  • outputs/baselines/without_solar/" -ForegroundColor Gray
Write-Host "  • outputs/baselines/baseline_comparison.csv" -ForegroundColor Gray
Write-Host "  • outputs/baselines/baseline_comparison.json" -ForegroundColor Gray
Write-Host ""

Write-Host "PRÓXIMOS PASOS:" -ForegroundColor Cyan
Write-Host "  1. Ver comparación:" -ForegroundColor Gray
Write-Host "     cat outputs/baselines/baseline_comparison.csv" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Entrenar RL agents:" -ForegroundColor Gray
Write-Host "     python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Comparar resultados:" -ForegroundColor Gray
Write-Host "     python -m scripts.run_oe3_co2_table --config configs/default.yaml" -ForegroundColor Gray
Write-Host ""
