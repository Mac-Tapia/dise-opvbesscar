#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Lanzar entrenamiento serial de agentes RL con GPU máximo

.DESCRIPTION
    Ejecuta el pipeline OE3 en forma serial: SAC → PPO → A2C
    - Verifica GPU disponible
    - Configura variables de entorno
    - Monitorea checkpoints en tiempo real
    - Genera reporte de resultados

.EXAMPLE
    .\train_agents_serial.ps1

.NOTES
    Requiere: .venv\Scripts\activate activada
#>

# Stop on error
$ErrorActionPreference = "Stop"

Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "VERIFICACIÓN DE VENV" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

# Check if venv is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "`n✗ ERROR: Virtual environment no está activo" -ForegroundColor Red
    Write-Host "Ejecuta primero: .venv\Scripts\activate" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✓ Virtual environment activo: $env:VIRTUAL_ENV" -ForegroundColor Green

# Verify Python
$python_version = & python --version 2>&1
Write-Host "✓ Python: $python_version" -ForegroundColor Green

# Check CUDA/GPU
Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "VERIFICACIÓN DE GPU" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

$cuda_check = & python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPUs: {torch.cuda.device_count()}')" 2>&1
Write-Host $cuda_check -ForegroundColor Green

# Verify project files
Write-Host "`n✓ Verificando archivos del proyecto..." -ForegroundColor Green

$required_files = @(
    "configs/default.yaml",
    "data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json"
)

foreach ($file in $required_files) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ FALTA: $file" -ForegroundColor Red
        exit 1
    }
}

# Configure environment for maximum GPU performance
Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "CONFIGURACIÓN GPU MÁXIMO" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

$env:CUDA_LAUNCH_BLOCKING = "0"
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:OMP_NUM_THREADS = "8"
$env:CUBLAS_WORKSPACE_CONFIG = ":16:8"

Write-Host "`n✓ Variables configuradas:" -ForegroundColor Green
Write-Host "  - CUDA_LAUNCH_BLOCKING=0" -ForegroundColor Green
Write-Host "  - OMP_NUM_THREADS=8" -ForegroundColor Green
Write-Host "  - CUBLAS_WORKSPACE_CONFIG=:16:8" -ForegroundColor Green

# Launch training
Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "INICIANDO ENTRENAMIENTO SERIAL" -ForegroundColor Cyan
Write-Host "SAC (GPU) → PPO (CPU) → A2C (GPU)" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

$cmd = "python train_agents_serial_gpu.py"
Write-Host "`nComando: $cmd`n" -ForegroundColor Yellow

try {
    & python train_agents_serial_gpu.py
    $exit_code = $LASTEXITCODE
}
catch {
    Write-Host "`n✗ ERROR durante ejecución: $_" -ForegroundColor Red
    exit 1
}

# Check results
if ($exit_code -eq 0) {
    Write-Host "`n✓ ENTRENAMIENTO COMPLETADO" -ForegroundColor Green
    
    # Show summary
    $summary_file = "outputs/oe3/simulations/simulation_summary.json"
    if (Test-Path $summary_file) {
        Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
        Write-Host "RESULTADOS FINALES" -ForegroundColor Cyan
        Write-Host ("=" * 70) -ForegroundColor Cyan
        
        $summary = Get-Content $summary_file | ConvertFrom-Json
        Write-Host "`nMejor agente: $($summary.best_agent)" -ForegroundColor Green
        
        if ($summary.pv_bess_results) {
            Write-Host "`nCO2 (kg/año):" -ForegroundColor Cyan
            foreach ($agent in $summary.pv_bess_results.PSObject.Properties) {
                $co2 = $agent.Value.carbon_kg
                Write-Host "  $($agent.Name): $([math]::Round($co2, 0))" -ForegroundColor Green
            }
        }
    }
}
else {
    Write-Host "`n✗ ENTRENAMIENTO FALLÓ (código $exit_code)" -ForegroundColor Red
    exit $exit_code
}

exit 0
