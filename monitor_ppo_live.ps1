#!/usr/bin/env powershell
# Monitor de entrenamiento PPO en TIEMPO REAL

$LogFile = "entrenamiento_ppo.log"
$OutputFile = "monitor_ppo_progress.csv"
$lastPosition = 0

# Encabezado CSV
@"
timestamp,step,episode,progress_pct,co2_grid_kg,co2_evitado_kg,kl_divergence,clip_pct,entropy,policy_loss,value_loss,expl_var
"@ | Set-Content $OutputFile -Encoding UTF8

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  MONITOR - ENTRENAMIENTO PPO (TIEMPO REAL)" -ForegroundColor Green
Write-Host "  Archivo log: $LogFile" -ForegroundColor Cyan
Write-Host "  Monitor CSV: $OutputFile" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$startTime = Get-Date
$lastDisplay = Get-Date

# Monitorear en vivo
while ($true) {
    if (Test-Path $LogFile) {
        try {
            $lines = Get-Content $LogFile -ErrorAction SilentlyContinue
            $newLines = @()
            
            foreach ($line in $lines) {
                # Extraer líneas con progreso
                if ($line -match "Steps:\s+(\d+)\s+\|\s+Ep:\s+(\d+)\s+\|\s+Progreso:\s+([\d.]+)%\s+\|\s+CO2_grid:\s+([\d,]+)\s+kg\s+\|\s+CO2_evitado:\s+([\d,]+)\s+kg") {
                    $step = [int]$matches[1]
                    $episode = [int]$matches[2]
                    $progress = [double]$matches[3]
                    $co2_grid = $matches[4] -replace ",", "" | Int64
                    $co2_evitado = $matches[5] -replace ",", "" | Int64
                    
                    # Extraer PPO metrics (siguiente línea)
                    if ($lines -like "*KL: *") {
                        $metricLine = $lines | Where-Object { $_ -match "KL:" } | Select-Object -Last 1
                        if ($metricLine -match "KL:\s+([\d.]+)\s+\|\s+Clip%:\s+([\d.]+)%\s+\|\s+Entropy:\s+([\d.]+)") {
                            $kl = [double]$matches[1]
                            $clip = [double]$matches[2]
                            $entropy = [double]$matches[3]
                        }
                    }
                    
                    # Mostrar cada 5 segundos
                    if (((Get-Date) - $lastDisplay).TotalSeconds -ge 5) {
                        Clear-Host
                        Write-Host "================================================================" -ForegroundColor Cyan
                        Write-Host "  ENTRENAMIENTO PPO - MONITOREO EN VIVO" -ForegroundColor Green
                        Write-Host "================================================================" -ForegroundColor Cyan
                        Write-Host ""
                        
                        # Barra de progreso
                        $barLength = 50
                        $filledLength = [int]($progress / 100 * $barLength)
                        $bar = "█" * $filledLength + "░" * ($barLength - $filledLength)
                        Write-Host "  Progreso  [$bar] $progress%" -ForegroundColor Yellow
                        Write-Host ""
                        
                        # Métricas
                        Write-Host "  [METRICAS ENTRENAMIENTO]" -ForegroundColor Cyan
                        Write-Host "    Step        : $step de 87,600"
                        Write-Host "    Episodio    : $episode"
                        Write-Host "    KL Div      : $kl" -ForegroundColor White
                        Write-Host "    Clipping    : $clip%" -ForegroundColor White
                        Write-Host "    Entropy     : $entropy" -ForegroundColor White
                        Write-Host ""
                        
                        # CO2
                        Write-Host "  [IMPACTO CO2]" -ForegroundColor Cyan
                        Write-Host "    CO2 Grid    : ${co2_grid:N0} kg" -ForegroundColor Red
                        Write-Host "    CO2 Evitado : ${co2_evitado:N0} kg" -ForegroundColor Green
                        Write-Host ""
                        
                        # Tiempo
                        $elapsed = New-TimeSpan -Start $startTime -End (Get-Date)
                        $timePerStep = $elapsed.TotalSeconds / $step
                        $remainingSteps = 87600 - $step
                        $estimatedRemaining = New-TimeSpan -Seconds ($timePerStep * $remainingSteps)
                        
                        Write-Host "  [TIEMPO]" -ForegroundColor Cyan
                        Write-Host "    Tiempo transcurrido : $($elapsed.ToString('hh\:mm\:ss'))"
                        Write-Host "    Tiempo restante est. : $($estimatedRemaining.ToString('hh\:mm\:ss'))"
                        Write-Host "    Velocidad           : $([math]::Round($timePerStep, 3)) seg/step"
                        Write-Host ""
                        
                        Write-Host "================================================================" -ForegroundColor Cyan
                        Write-Host "  (Presiona CTRL+C para detener)" -ForegroundColor Gray
                        
                        $lastDisplay = Get-Date
                    }
                }
            }
            
        } catch {
            # Ignorar errores de lectura mientras el archivo está siendo escrito
        }
    }
    
    Start-Sleep -Milliseconds 500
}
