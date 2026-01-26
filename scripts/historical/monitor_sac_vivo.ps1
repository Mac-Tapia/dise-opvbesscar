# Monitor de SAC Training en Tiempo Real (sin interrupciones)
# Script: monitor_sac_vivo.ps1
# Uso: .\monitor_sac_vivo.ps1

param(
    [int]$RefreshSeconds = 10
)

function Get-LatestCheckpoint {
    $checkpointDir = "analyses/oe3/training/checkpoints/sac"
    if (Test-Path $checkpointDir) {
        $latest = Get-ChildItem "$checkpointDir/*.zip" -ErrorAction SilentlyContinue | 
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latest) {
            $step = [regex]::Match($latest.Name, '_(\d+)').Groups[1].Value
            @{
                File   = $latest.Name
                Step   = [int]$step
                SizeMB = [math]::Round($latest.Length / 1MB, 2)
                Time   = $latest.LastWriteTime.ToString("HH:mm:ss")
            }
        }
    }
}

function Get-LatestMetrics {
    $logFile = "analyses/oe3/training/sac_training.log"
    if (Test-Path $logFile) {
        # Leer últimas 100 líneas
        $lines = @(Get-Content $logFile -Tail 100 -ErrorAction SilentlyContinue)
        
        # Buscar línea con "[SAC] paso" más reciente
        foreach ($line in $lines | Select-Object -Last 100) {
            if ($line -match '\[SAC\] paso (\d+) \| ep~(\d+) .*reward_avg=([0-9\.]+)') {
                return @{
                    Paso      = [int]$matches[1]
                    Episodio  = $matches[2]
                    RewardAvg = [double]$matches[3]
                    Timestamp = Get-Date -Format "HH:mm:ss"
                }
            }
        }
    }
}

function Get-BaselineData {
    $file = "analyses/oe3/simulations/uncontrolled_pv_bess.json"
    if (Test-Path $file) {
        try {
            $json = Get-Content $file | ConvertFrom-Json
            if ($json.uncontrolled) {
                return @{
                    CO2_kg  = $json.uncontrolled.total_co2_kg
                    GridKwh = $json.uncontrolled.grid_electricity_consumption_kWh
                    Reward  = $json.uncontrolled.reward
                }
            }
        }
        catch {}
    }
}

function Show-Monitor {
    # Limpiar pantalla
    Clear-Host
    
    # Encabezado
    Write-Host "╔" + ("═" * 78) + "╗" -ForegroundColor Cyan
    Write-Host "║" + (" " * 78) + "║" -ForegroundColor Cyan
    Write-Host "║" + "  📊 MONITOR SAC TRAINING - ENTRENAMIENTO EN VIVO".PadRight(78) + "║" -ForegroundColor Green
    Write-Host "║" + (" " * 78) + "║" -ForegroundColor Cyan
    Write-Host "╚" + ("═" * 78) + "╝" -ForegroundColor Cyan
    Write-Host ""
    
    # Checkpoint Status
    Write-Host "📁 CHECKPOINT ACTUAL" -ForegroundColor Yellow
    Write-Host ("─" * 80)
    $checkpoint = Get-LatestCheckpoint
    if ($checkpoint) {
        Write-Host "  Archivo:      $($checkpoint.File)" -ForegroundColor White
        Write-Host "  Paso:         $($checkpoint.Step.ToString('N0')) steps" -ForegroundColor Cyan
        Write-Host "  Tamaño:       $($checkpoint.SizeMB) MB" -ForegroundColor Cyan
        Write-Host "  Actualizado:  $($checkpoint.Time)" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠️  No checkpoints encontrados" -ForegroundColor Red
    }
    Write-Host ""
    
    # Training Metrics
    Write-Host "📈 MÉTRICAS DE ENTRENAMIENTO" -ForegroundColor Yellow
    Write-Host ("─" * 80)
    $metrics = Get-LatestMetrics
    if ($metrics) {
        Write-Host "  Paso Actual:      $($metrics.Paso.ToString('N0')) steps" -ForegroundColor White
        Write-Host "  Episodio:         $($metrics.Episodio) / 10" -ForegroundColor Cyan
        Write-Host "  Reward Promedio:  $($metrics.RewardAvg.ToString('F4'))" -ForegroundColor Green
        Write-Host "  Última Lectura:   $($metrics.Timestamp)" -ForegroundColor White
        
        # Progress bar
        $ep = [int]$metrics.Episodio
        $progress = [int]($ep * 4)  # 40 caracteres para 10 episodios
        $bar = ("█" * $progress) + ("░" * (40 - $progress))
        $percent = ($ep / 10) * 100
        Write-Host "  Progreso:         [$bar] $($percent.ToString('F0'))%" -ForegroundColor Cyan
    }
    else {
        Write-Host "  ⚠️  Esperando datos de entrenamiento..." -ForegroundColor Yellow
    }
    Write-Host ""
    
    # Baseline Comparison
    Write-Host "🎯 COMPARACIÓN SAC vs BASELINE" -ForegroundColor Yellow
    Write-Host ("─" * 80)
    $baseline = Get-BaselineData
    if ($baseline -and $metrics) {
        $reduction = (1 - ($metrics.RewardAvg / 100)) * 100
        Write-Host "  Baseline CO₂:       $($baseline.CO2_kg.ToString('F1')) kg" -ForegroundColor White
        Write-Host "  Baseline Grid:      $($baseline.GridKwh.ToString('F1')) kWh" -ForegroundColor White
        Write-Host "  Reward Baseline:    $($baseline.Reward.ToString('F1'))" -ForegroundColor White
        Write-Host "  Reward SAC Promedio: $($metrics.RewardAvg.ToString('F4'))" -ForegroundColor Green
        
        if ($metrics.RewardAvg -gt 40) {
            Write-Host "  ✅ Rendimiento:     EXCELENTE" -ForegroundColor Green
        }
        elseif ($metrics.RewardAvg -gt 30) {
            Write-Host "  ✓ Rendimiento:      BUENO" -ForegroundColor Yellow
        }
        else {
            Write-Host "  ⚠️  Rendimiento:     EN MEJORA" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "  ⚠️  Datos insuficientes para comparación" -ForegroundColor Yellow
    }
    Write-Host ""
    
    # Checkpoint History
    Write-Host "📜 ÚLTIMOS 5 CHECKPOINTS" -ForegroundColor Yellow
    Write-Host ("─" * 80)
    $checkpointDir = "analyses/oe3/training/checkpoints/sac"
    if (Test-Path $checkpointDir) {
        $count = 0
        Get-ChildItem "$checkpointDir/*.zip" -ErrorAction SilentlyContinue | 
        Sort-Object LastWriteTime -Descending | 
        Select-Object -First 5 | 
        ForEach-Object {
            $count++
            $step = [regex]::Match($_.Name, '_(\d+)').Groups[1].Value
            $time = $_.LastWriteTime.ToString("HH:mm:ss")
            $size = [math]::Round($_.Length / 1MB, 1)
            $status = if ($count -eq 1) { "🟢 Activo" } else { "  " }
            Write-Host "  $count. Step $step ($time) - ${size}MB $status" -ForegroundColor Cyan
        }
    }
    else {
        Write-Host "  ⚠️  Carpeta de checkpoints no encontrada" -ForegroundColor Red
    }
    Write-Host ""
    
    # Footer
    Write-Host ("─" * 80)
    Write-Host "🔄 Última actualización: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
    Write-Host "💡 El entrenamiento continúa en background. Este monitor NO interrumpe el proceso." -ForegroundColor Gray
    Write-Host "⏸️  Presiona Ctrl+C para salir (el entrenamiento continuará)" -ForegroundColor Magenta
    Write-Host "🔁 Próxima actualización en $RefreshSeconds segundos..." -ForegroundColor Gray
    Write-Host ""
}

# Main loop
try {
    while ($true) {
        Show-Monitor
        Start-Sleep -Seconds $RefreshSeconds
    }
}
catch [OperationCanceledException] {
    Write-Host "`n✅ Monitor detenido. El entrenamiento continúa en background." -ForegroundColor Green
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
