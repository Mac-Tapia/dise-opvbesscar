#!/usr/bin/env powershell
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
Lanzar entrenamiento SAC con datos reales OE2 en PowerShell
Limpio: Sin emojis, sin caracteres especiales, solo ASCII

.DESCRIPTION
1. Verifica datos reales
2. Lanza entrenamiento SAC en background
3. Monitorea en tiempo real
4. Genera reportes

#>

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  ENTRENAMIENTO SAC - MULTIOBJETIVO REAL (CO2, SOLAR, COST, EV, GRID)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# ===== VERIFICAR DATOS REALES =====
Write-Host "[PASO 1] Validar datos reales OE2..." -ForegroundColor Yellow
Write-Host ""

$datasets = @{
    "Solar PV (PVGIS)" = "data/oe2/Generacionsolar/pv_generation_citylearn2024.csv"
    "Chargers EV (38 sockets)" = "data/oe2/chargers/chargers_ev_ano_2024_v3.csv"
    "BESS SOC" = "data/oe2/bess/bess_ano_2024.csv"
    "Mall Demand" = "data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv"
}

$all_ok = $true
foreach ($name in $datasets.Keys) {
    $path = $datasets[$name]
    if (Test-Path $path) {
        Write-Host "  [OK] $name" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] $name - NOT FOUND: $path" -ForegroundColor Red
        $all_ok = $false
    }
}

if (-not $all_ok) {
    Write-Host ""
    Write-Host "[ERROR] Faltan datos - Ejecutar: python scripts/train/prepare_data_ppo.py" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[OK] TODOS LOS DATOS REALES VALIDADOS" -ForegroundColor Green
Write-Host ""

# ===== LANZAR ENTRENAMIENTO SAC =====
Write-Host "[PASO 2] Lanzar entrenamiento SAC..." -ForegroundColor Yellow
Write-Host ""

$log_file = "entrenamiento_sac_limpio.log"
$start_time = Get-Date

Write-Host "  Log file: $log_file" -ForegroundColor Gray
Write-Host "  Timestamp: $start_time" -ForegroundColor Gray
Write-Host ""

# Lanzar Python con el archivo principal
python -c "
import sys
from pathlib import Path

# Fix path
project = Path('.')
sys.path.insert(0, str(project))
sys.path.insert(0, str(project / 'src'))

# Run training
from scripts.train.train_sac_multiobjetivo import main
try:
    main()
except KeyboardInterrupt:
    print('\n\n[DETENIDO] Entrenamiento interrumpido por usuario')
except Exception as e:
    print(f'\n\n[ERROR] {e}')
    import traceback
    traceback.print_exc()
" 2>&1 | Tee-Object -FilePath $log_file

# ===== REPORTE FINAL =====
$end_time = Get-Date
$duration = $end_time - $start_time

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  ENTRENAMIENTO SAC COMPLETADO" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Duracion total: $($duration.Hours)h $($duration.Minutes)m $($duration.Seconds)s" -ForegroundColor Green
Write-Host "Archivo log:   $log_file" -ForegroundColor Green
Write-Host "Checkpoints:   checkpoints/SAC/" -ForegroundColor Green
Write-Host "Outputs:       outputs/sac_training/" -ForegroundColor Green
Write-Host ""
Write-Host "Proximos pasos:" -ForegroundColor Yellow
Write-Host "  1. Revisar log: Get-Content $log_file -Tail 50" -ForegroundColor Gray
Write-Host "  2. Ver checkpoints: Get-ChildItem checkpoints/SAC/" -ForegroundColor Gray
Write-Host "  3. Ver outputs: Get-ChildItem outputs/sac_training/" -ForegroundColor Gray
Write-Host ""
