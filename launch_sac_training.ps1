#!/usr/bin/env pwsh
<#
.SYNOPSIS
Lanza el entrenamiento SAC con datos OE2 reales y monitorea en tiempo real.

.DESCRIPTION
1. Valida que los datos estén listos
2. Lanza el entrenamiento SAC en background
3. Monitorea el progreso cada 5 segundos
4. Valida uso de todas las columnas de datos

.NOTES
Autor: Sistema Automático
Fecha: 2026-02-14
Versión: v5.3
#>

$ErrorActionPreference = "Continue"
$WarningPreference = "SilentlyContinue"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         LANZAMIENTO DE ENTRENAMIENTO SAC - CON DATOS OE2 REALES               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. VALIDAR DATOS
Write-Host "PASO 1: Validando datos OE2..." -ForegroundColor Yellow
$validation_output = python validate_datasets.py 2>&1
if ($validation_output -match "✅ VALIDACION EXITOSA") {
    Write-Host "  ✅ Todos los datos están listos" -ForegroundColor Green
} else {
    Write-Host "  ❌ Error en validación de datos" -ForegroundColor Red
    Write-Host $validation_output
    exit 1
}
Write-Host ""

# 2. LANZAR ENTRENAMIENTO SAC EN BACKGROUND
Write-Host "PASO 2: Lanzando entrenamiento SAC..." -ForegroundColor Yellow
Write-Host "  • Configuración: 10 episodios × 8,760 timesteps = 87,600 steps" -ForegroundColor Cyan
Write-Host "  • Parámetros SAC: LR=1e-4, Buffer=1M, Batch=256, τ=0.005" -ForegroundColor Cyan
Write-Host "  • Reward: Multiobjetivo (CO2, Solar, EV, Grid)" -ForegroundColor Cyan
Write-Host "  • GPU: $(python -c 'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\")' 2>/dev/null || echo 'check manually')" -ForegroundColor Cyan
Write-Host ""

$training_log = "entrenamiento_sac.log"
$start_time = Get-Date

# Lanzar entrenamiento
Write-Host "  Iniciando... (logs → $training_log)" -ForegroundColor Green
$process = Start-Process -FilePath python `
    -ArgumentList "scripts/train/train_sac_multiobjetivo.py" `
    -NoNewWindow `
    -PassThru `
    -RedirectStandardOutput $training_log `
    -RedirectStandardError ($training_log + ".err")

Write-Host "  ✓ PID: $($process.Id)" -ForegroundColor Green
Write-Host ""

# 3. MONITOREAR EN TIEMPO REAL
Write-Host "PASO 3: Monitoreando entrenamiento (actualizar cada 5 segundos)..." -ForegroundColor Yellow
Write-Host "  Presiona Ctrl+C para pausar monitor (entrenamiento continúa en background)" -ForegroundColor Cyan
Write-Host ""

$last_lines = 0
$last_size = 0
$first_lines = $true

try {
    while ($process.HasExited -eq $false) {
        Start-Sleep -Seconds 5
        
        # Leer últimas líneas del log
        if (Test-Path $training_log) {
            $current_size = (Get-Item $training_log).Length
            
            # Si el archivo creció, mostrar nuevas líneas
            if ($current_size -gt $last_size -or $first_lines) {
                $lines = @()
                try {
                    $lines = Get-Content $training_log -Tail 3 -ErrorAction SilentlyContinue
                } catch {
                    # Archivo en uso, esperar
                    Start-Sleep -Milliseconds 100
                    try {
                        $lines = Get-Content $training_log -Tail 3 -ErrorAction SilentlyContinue
                    } catch {}
                }
                
                if ($lines.Count -gt 0) {
                    # Mostrar líneas relevantes
                    foreach ($line in $lines) {
                        if ($line -match "STEP|EVAL|CO2|Entropy|Alpha|LOSSES|TRAINING") {
                            Write-Host "    $line" -ForegroundColor Gray
                        }
                    }
                }
                
                $last_size = $current_size
                $first_lines = $false
            }
        }
        
        # Mostrar progreso
        $elapsed = (Get-Date) - $start_time
        Write-Host "    [$(Get-Date -Format 'HH:mm:ss')] Entrenando... $('{0:D2}h {1:D2}m {2:D2}s' -f $elapsed.Hours, $elapsed.Minutes, $elapsed.Seconds)" -ForegroundColor Cyan -NoNewline
        Write-Host "`r" -NoNewline
    }
}
catch [System.OperationCanceledException] {
    Write-Host ""
    Write-Host "  ⚠ Monitor pausado por usuario (entrenamiento continúa en background)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host ""

# 4. VERIFICAR RESULTADO
Write-Host "PASO 4: Verificando resultado del entrenamiento..." -ForegroundColor Yellow

if ($process.HasExited) {
    $exitCode = $process.ExitCode
    $elapsed = (Get-Date) - $start_time
    
    if ($exitCode -eq 0) {
        Write-Host "  ✅ Entrenamiento completado exitosamente" -ForegroundColor Green
        Write-Host "  ✓ Tiempo total: $('{0:D2}h {1:D2}m {2:D2}s' -f $elapsed.Hours, $elapsed.Minutes, $elapsed.Seconds)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Entrenamiento completado con código: $exitCode" -ForegroundColor Yellow
    }
}

Write-Host ""

# 5. MOSTRAR UBICACIÓN DE ARCHIVOS
Write-Host "PASO 5: Archivos de salida generados..." -ForegroundColor Yellow
Write-Host ""

$output_dirs = @(
    "checkpoints/SAC",
    "outputs/sac_training"
)

foreach ($dir in $output_dirs) {
    if (Test-Path $dir) {
        $files = Get-ChildItem -Path $dir -File -Recurse | Measure-Object
        if ($files.Count -gt 0) {
            Write-Host "  ✓ $dir/" -ForegroundColor Green
            Get-ChildItem -Path $dir -File -Recurse | ForEach-Object {
                Write-Host "     - $($_.Name)" -ForegroundColor Gray
            }
        }
    }
}

Write-Host ""
Write-Host "✅ ENTRENAMIENTO SAC COMPLETADO" -ForegroundColor Green
Write-Host ""
Write-Host "PRÓXIMOS PASOS:" -ForegroundColor Yellow
Write-Host "  1. Revisar logs: Get-Content entrenamiento_sac.log -Tail 50" -ForegroundColor Cyan
Write-Host "  2. Análisis: python -c \"import pandas as pd; df=pd.read_csv('outputs/sac_training/sac_training_metrics.csv'); print(df.tail())\"" -ForegroundColor Cyan
Write-Host "  3. Gráficas: Revisar archivos .png en outputs/sac_training/" -ForegroundColor Cyan
Write-Host ""
