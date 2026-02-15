#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
"""
Monitor en vivo para entrenamiento A2C
Actualiza cada 10 segundos
"""

$logFile = "entrenamiento_a2c.log"
$previousSize = 0
$episodePattern = "Episodio\s+(\d+)/10"
$stepPattern = "Step\s+(\d+,?\d*)/87,600"
$rewardPattern = "R_avg=\s*([-\d.]+)"
$co2Pattern = "CO2=\s*([\d,]+)"
$solarPattern = "Solar=\s*([\d,]+)"
$startTime = Get-Date

function Format-Size($bytes) {
    if ($bytes -ge 1MB) { return "{0:F1} MB" -f ($bytes / 1MB) }
    if ($bytes -ge 1KB) { return "{0:F0} KB" -f ($bytes / 1KB) }
    return "$bytes B"
}

function Get-Progress($line) {
    if ($line -match $stepPattern) {
        $step = [int]($matches[1] -replace ',', '')
        return [math]::Round(($step / 87600) * 100, 1)
    }
    return 0
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║            MONITOR EN VIVO - ENTRENAMIENTO A2C                  ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

while ($true) {
    if (Test-Path $logFile) {
        $fileSize = (Get-Item $logFile).Length
        $content = Get-Content $logFile -Tail 15 -ErrorAction SilentlyContinue
        
        if ($content) {
            Write-Host ""
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Log Size: $(Format-Size $fileSize)" -ForegroundColor Cyan
            Write-Host "─" * 70 -ForegroundColor DarkGray
            
            $lastLine = $content[-1]
            
            # Extraer progreso
            if ($lastLine -match "Step\s+([\d,]+)/87,600") {
                $step = [int]($matches[1] -replace ',', '')
                $progress = [math]::Round(($step / 87600) * 100, 1)
                
                # Proyectar velocidad
                $elapsed = ((Get-Date) - $startTime).TotalSeconds
                if ($elapsed -gt 0) {
                    $sps = [math]::Round($step / $elapsed, 0)
                    $remaining = 87600 - $step
                    $etaSeconds = $remaining / $sps
                    $eta = [timespan]::FromSeconds($etaSeconds)
                    
                    Write-Host "📊 Progreso: ${progress}% [$step/87,600 steps]" -ForegroundColor Yellow
                    Write-Host "   Velocidad: $sps timesteps/sec" -ForegroundColor Green
                    if ($eta.TotalSeconds -gt 0) {
                        Write-Host "   ETA: $($eta.Minutes)m $($eta.Seconds)s" -ForegroundColor Cyan
                    }
                }
            }
            
            # Mostrar últimas líneas del log
            Write-Host ""
            Write-Host "📋 Últimas 5 líneas del log:" -ForegroundColor White
            $content | Select-Object -Last 5 | ForEach-Object {
                Write-Host "   $_" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ⏳ Esperando log..." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Start-Sleep -Seconds 10
}
