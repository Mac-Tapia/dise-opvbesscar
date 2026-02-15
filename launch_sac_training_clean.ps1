#!/usr/bin/env powershell
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
Lanzar entrenamiento SAC con datos reales OE2
.DESCRIPTION
Ejecuta train_sac_multiobjetivo.py en background y monitorea archivos de output
#>

Write-Host "=================================================================================" -ForegroundColor Cyan
Write-Host "ENTRENAR SAC - DATOS REALES OE2 (MULTIOBJETIVO)" -ForegroundColor Cyan
Write-Host "=================================================================================" -ForegroundColor Cyan
Write-Host ""

# Validar que los datos estén listos
$test_files = @(
    "data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv",
    "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
    "data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv",
    "data/oe2/bess/bess_ano_2024.csv"
)

$all_ready = $true
foreach ($file in $test_files) {
    if (Test-Path $file) {
        Write-Host "[OK] $file" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] $file no encontrado" -ForegroundColor Red
        $all_ready = $false
    }
}

if (-not $all_ready) {
    Write-Host ""
    Write-Host "[ERROR] Faltan archivos de datos" -ForegroundColor Red
    Write-Host "Ejecutar primero: python scripts/train/prepare_data_ppo.py" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Inicializando entrenamiento SAC..." -ForegroundColor Yellow
Write-Host ""

# Crear directorio de outputs
if (-not (Test-Path "outputs/sac_training")) {
    New-Item -Path "outputs/sac_training" -ItemType Directory -Force | Out-Null
}

# Configurar encoding UTF-8
$env:PYTHONIOENCODING = 'utf-8'

# Lanzar entrenamiento en background
$job = Start-Job -ScriptBlock {
    Set-Location D:\diseñopvbesscar
    $env:PYTHONIOENCODING = 'utf-8'
    python scripts/train/train_sac_multiobjetivo.py 2>&1 | Tee-Object -FilePath entrenamiento_sac_clean.log
}

$job_id = $job.Id
Write-Host "[OK] SAC entrenamiento iniciado (Job $job_id)" -ForegroundColor Green
Write-Host ""
Write-Host "Monitoreo en vivo:" -ForegroundColor Cyan
Write-Host "  - Log completo:   tail entrenamiento_sac_clean.log" -ForegroundColor White
Write-Host "  - Últimas 20 l..: Get-Content entrenamiento_sac_clean.log -Tail 20 -Wait" -ForegroundColor White
Write-Host "  - Estado job:    Get-Job | ForEach {   $_.Name }" -ForegroundColor White
Write-Host ""

# Monitoreo continuo de output directory
Write-Host "Esperando archivos de output..." -ForegroundColor Yellow
$timeout = 0
$max_wait = 60

while (-not (Test-Path "outputs/sac_training/result_sac.json") -and $timeout -lt $max_wait) {
    Start-Sleep -Seconds 5
    $timeout += 5
    
    # Mostrar estado del job
    $job_status = Get-Job -Id $job_id -ErrorAction SilentlyContinue
    if ($job_status.State -eq "Completed") {
        Write-Host "[OK] Job completado" -ForegroundColor Green
        break
    } elseif ($job_status.State -eq "Failed") {
        Write-Host "[ERROR] Job falló" -ForegroundColor Red
        break
    }
}

Write-Host ""
Write-Host "Esperando a que el job se complete..." -ForegroundColor Yellow

# Esperar exactamente a que el job termine
while ((Get-Job -Id $job_id -ErrorAction SilentlyContinue).State -eq "Running") {
    Start-Sleep -Seconds 2
}

Write-Host "[OK] Entrenamiento SAC completado" -ForegroundColor Green
Write-Host ""

# Mostrar resumen final
if (Test-Path "entrenamiento_sac_clean.log") {
    Write-Host "ÚLTIMAS LÍNEAS DEL LOG:" -ForegroundColor Cyan
    Get-Content entrenamiento_sac_clean.log -Tail 40
}

Write-Host ""
Write-Host "Archivos de salida:" -ForegroundColor Cyan
if (Test-Path "outputs/sac_training/result_sac.json") {
    Write-Host "[OK] outputs/sac_training/result_sac.json" -ForegroundColor Green
}
if (Test-Path "outputs/sac_training/timeseries_sac.csv") {
    Write-Host "[OK] outputs/sac_training/timeseries_sac.csv" -ForegroundColor Green
}
if (Test-Path "outputs/sac_training/trace_sac.csv") {
    Write-Host "[OK] outputs/sac_training/trace_sac.csv" -ForegroundColor Green
}

Write-Host ""
Write-Host "=================================================================================" -ForegroundColor Green
Write-Host "ENTRENAMIENTO COMPLETADO" -ForegroundColor Green
Write-Host "=================================================================================" -ForegroundColor Green
