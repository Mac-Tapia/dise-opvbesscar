#!/usr/bin/env powershell
# Monitor de Entrenamiento SAC - Clean Start
# Muestra en tiempo real qué checkpoints se están guardando

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    MONITOR DE ENTRENAMIENTO SAC - CLEAN START (Paso 0)        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$sacDir = "D:\diseñopvbesscar\checkpoints\sac"
$outputDir = "D:\diseñopvbesscar\outputs\oe3\simulations"
$logFile = "D:\diseñopvbesscar\training_clean_start_20260203.log"
$lastCheckpointCount = 0
$startTime = Get-Date
$expectedSteps = 26280  # 3 episodios * 8760 pasos

while ($true) {
    Clear-Host

    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║    MONITOR DE ENTRENAMIENTO SAC - CLEAN START                  ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""

    # Tiempo transcurrido
    $elapsed = (Get-Date) - $startTime
    Write-Host "[TIEMPO] $($elapsed.Hours)h $($elapsed.Minutes)m $($elapsed.Seconds)s transcurridos" -ForegroundColor Yellow
    Write-Host ""

    # Checkpoints guardados
    Write-Host "[CHECKPOINTS GUARDADOS]:" -ForegroundColor Yellow
    $checkpoints = Get-ChildItem "$sacDir\sac_step_*.zip" -ErrorAction SilentlyContinue | Sort-Object {
        if ($_.Name -match "step_(\d+)") { [int]$matches[1] } else { 0 }
    }

    if ($checkpoints) {
        if ($checkpoints -is [array]) {
            $checkpointCount = $checkpoints.Count
        } else {
            $checkpointCount = 1
        }

        if ($checkpointCount -ne $lastCheckpointCount) {
            Write-Host "   [CHECK] Nuevos checkpoints guardados: $checkpointCount" -ForegroundColor Green
        Write-Host "   Últimos 5 checkpoints:" -ForegroundColor Cyan
        $checkpoints | Select-Object -Last 5 | ForEach-Object {
            if ($_.Name -match "step_(\d+)") {
                $step = [int]$matches[1]
                $mb = [math]::Round($_.Length / 1MB, 2)
                $time = $_.LastWriteTime.ToString('HH:mm:ss')
                $percent = [math]::Round(($step / $expectedSteps) * 100, 1)
                Write-Host "      [paso $($step.ToString().PadLeft(5))] $($mb.ToString().PadLeft(6)) MB - $time ($percent%)" -ForegroundColor Green
            }
        }
    } else {
        Write-Host "   (Esperando primer checkpoint en ~100 segundos...)" -ForegroundColor Cyan
    }

    # Archivos finales
    Write-Host ""
    Write-Host "[ARCHIVOS DE RESULTADO]:" -ForegroundColor Yellow
    $resultFiles = Get-ChildItem "$outputDir\*SAC*" -ErrorAction SilentlyContinue

    if ($resultFiles) {
        Write-Host "   ✓ Archivos generados (entrenamiento completado):" -ForegroundColor Green
        $resultFiles | ForEach-Object {
            $kb = [math]::Round($_.Length / 1KB, 1)
            Write-Host "      $_  ($kb KB)" -ForegroundColor Green
        }

        # Salir si está completo
        if ((Get-ChildItem "$outputDir\result_SAC.json" -ErrorAction SilentlyContinue) -and
            (Get-ChildItem "$outputDir\timeseries_SAC.csv" -ErrorAction SilentlyContinue)) {
            Write-Host ""
            Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
            Write-Host "        ✓ ENTRENAMIENTO COMPLETADO EXITOSAMENTE" -ForegroundColor Green
            Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
            Write-Host ""
            break
        }
    } else {
        Write-Host "   (Esperando generación de resultados...)" -ForegroundColor Cyan
    }

    # Proceso Python
    Write-Host ""
    Write-Host "[PROCESO]:" -ForegroundColor Yellow
    $pythonProcs = Get-Process python -ErrorAction SilentlyContinue
    if ($pythonProcs) {
        $pythonProcs | ForEach-Object {
            $mem = [math]::Round($_.WorkingSet / 1MB)
            Write-Host "   ✓ Python activo (PID: $($_.Id), Memory: $mem MB)"
        }
    } else {
        Write-Host "   ⚠ Python NO está ejecutando (puede haber terminado o iniciando)" -ForegroundColor Yellow
    }

    # Actualización
    Write-Host ""
    Write-Host "Actualizando en 5 segundos..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
}
