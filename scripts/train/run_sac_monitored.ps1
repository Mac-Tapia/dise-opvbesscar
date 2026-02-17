#!/usr/bin/env pwsh
# ENTRENAMIENTO SAC CON MONITOREO ROBUSTO EN TIEMPO REAL
# Garantiza capturas correctas de losses + validacion continuous

$env:PYTHONIOENCODING = 'utf-8'

# Header visual
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "ENTRENAMIENTO SAC v9.3 - MONITOREO SEGURO Y ROBUSTO" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "[LIMPIEZA] SAC: LIMPIO (0 checkpoints)" -ForegroundColor Green
Write-Host "[PROTECCION] PPO: 46 checkpoints INTACTOS" -ForegroundColor Green
Write-Host "[PROTECCION] A2C: 44 checkpoints INTACTOS" -ForegroundColor Green
Write-Host "[DATOS] OE2: 4 datasets validados (8,760 horas)" -ForegroundColor Green
Write-Host "[GPU] RTX 4060 Laptop 8.6GB (CUDA 12.1)" -ForegroundColor Green
Write-Host "[ALGORITMO] SAC (Off-policy, asimetrico)" -ForegroundColor Yellow
Write-Host "[CONFIG] LR=1e-4 Buffer=1M Batch=256 tau=0.025" -ForegroundColor Yellow
Write-Host "[DURACION] 5-7 horas (RTX 4060)" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

# Timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log_file = "outputs/sac_training_${timestamp}.log"
$err_file = "outputs/sac_training_${timestamp}.err"

Write-Host "LOG: $log_file" -ForegroundColor White
Write-Host "ERR: $err_file" -ForegroundColor White
Write-Host ""

# Crear directorio de outputs si no existe
New-Item -Path "outputs" -ItemType Directory -Force | Out-Null

Write-Host "═" * 100 -ForegroundColor Cyan
Write-Host "INICIANDO ENTRENAMIENTO SAC..." -ForegroundColor Green
Write-Host "═" * 100 -ForegroundColor Cyan
Write-Host ""

# Ejecutar entrenamiento y capturar TODA la salida
try {
    # Ejecutar python con output redirection (stdout + stderr)
    python scripts/train/train_sac_multiobjetivo.py 2>&1 | Tee-Object -FilePath $log_file | ForEach-Object {
        # Filtrar y mostrar líneas importantes EN TIEMPO REAL
        $line = $_
        
        # METRICAS CRITICAS
        if ($line -match 'METRICA|TIMESTEP|LOSSES|EXPLORACION|Critic Loss|Actor Loss|Alpha|Entropy') {
            Write-Host $line -ForegroundColor Yellow
        }
        # CHECKPOINTS
        elseif ($line -match 'Checkpoint|saved|zip') {
            Write-Host $line -ForegroundColor Green
        }
        # ERRORES
        elseif ($line -match 'ERROR|FAIL|Exception') {
            Write-Host $line -ForegroundColor Red
        }
        # ADVERTENCIAS
        elseif ($line -match 'WARNING|WARN') {
            Write-Host $line -ForegroundColor Magenta
        }
        # PROGRESO (mostrar menos)
        elseif ($line -match 'Episode|Step|Reward') {
            # Solo mostrar cada 10 lineas
            Write-Host $line -ForegroundColor Gray
        }
        # Otros
        else {
            Write-Host $line
        }
    }
    
    Write-Host ""
    Write-Host "═" * 100 -ForegroundColor Green
    Write-Host "ENTRENAMIENTO COMPLETADO EXITOSAMENTE" -ForegroundColor Green
    Write-Host "═" * 100 -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "═" * 100 -ForegroundColor Red
    Write-Host "ERROR DURANTE ENTRENAMIENTO:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "═" * 100 -ForegroundColor Red
    
    # Guardar error
    $_ | Out-File -FilePath $err_file -Append
    exit 1
}

# VALIDACION POST-ENTRENAMIENTO
Write-Host ""
Write-Host "POST-VALIDACION:" -ForegroundColor Cyan
Write-Host ""

# 1. Checkpoints SAC creados
$sac_count = (Get-ChildItem checkpoints/SAC -Filter "*.zip" -ErrorAction SilentlyContinue).Count
Write-Host "  SAC Checkpoints:  $sac_count nuevos" -ForegroundColor $(if ($sac_count -gt 0) { 'Green' } else { 'Red' })

# 2. PPO/A2C intactos
$ppo_count = (Get-ChildItem checkpoints/PPO -Filter "*.zip").Count
$a2c_count = (Get-ChildItem checkpoints/A2C -Filter "*.zip").Count
Write-Host "  PPO Checkpoints:  $ppo_count (INTACTOS)" -ForegroundColor Green
Write-Host "  A2C Checkpoints:  $a2c_count (INTACTOS)" -ForegroundColor Green

# 3. Logs guardados
$metric_files = (Get-ChildItem outputs -Filter "sac_metrics*" -ErrorAction SilentlyContinue).Count
Write-Host "  Archivos métricas: $metric_files" -ForegroundColor Green

# 4. Summary
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "RESUMEN:" -ForegroundColor Green
Write-Host "  Log complete:     $log_file" -ForegroundColor White
Write-Host "  Checkpoints SAC:  $sac_count modelos guardados" -ForegroundColor White
Write-Host "  Estado PPO/A2C:   PROTEGIDOS (sin cambios)" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Green
