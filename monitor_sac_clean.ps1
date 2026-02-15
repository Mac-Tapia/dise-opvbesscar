#!/usr/bin/env powershell
# -*- coding: utf-8 -*-
<#
Monitor SAC Training in Real-Time (Clean - No Special Characters)
#>

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  MONITOR SAC TRAINING - TIEMPO REAL (LIMPIO)" -ForegroundColor Cyan  
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$log_file = "entrenamiento_sac_limpio.log"
$refresh_interval = 3  # segundos

# Monitor loop
Write-Host "[MONITOR] Presiona Ctrl+C para detener" -ForegroundColor Yellow
Write-Host ""

$last_lines = 0
while ($true) {
    if (Test-Path $log_file) {
        $current_lines = @(Get-Content $log_file).Count
        
        # Show last 30 lines
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] -- ULTIMAS 30 LINEAS DEL LOG --" -ForegroundColor Gray
        Write-Host ""
        
        $content = Get-Content $log_file
        if ($content -is [string]) {
            $content = @($content)
        }
        
        $start = [Math]::Max(0, $content.Count - 30)
        for ($i = $start; $i -lt $content.Count; $i++) {
            $line = $content[$i]
            
            # Colorize by content
            if ($line -match 'OK|OK]' -or $line.Contains('[OK]')) {
                Write-Host $line -ForegroundColor Green
            } elseif ($line -match 'ERROR|ERROR]' -or $line.Contains('[ERROR]')) {
                Write-Host $line -ForegroundColor Red
            } elseif ($line -match 'WARNING|WARNING]' -or $line.Contains('[WARNING]')) {
                Write-Host $line -ForegroundColor Yellow
            } elseif ($line -match 'Episode|Step|Checkpoint' -or $line.Contains('Episode')) {
                Write-Host $line -ForegroundColor Cyan
            } else {
                Write-Host $line -ForegroundColor White
            }
        }
        
        Write-Host ""
        Write-Host "Total lines: $($content.Count) | Updated at $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
        Write-Host ""
        Write-Host "========================================================================" -ForegroundColor Gray
    } else {
        Write-Host "Esperando archivo de log: $log_file" -ForegroundColor Yellow
    }
    
    # Wait before refresh
    Start-Sleep -Seconds $refresh_interval
    Clear-Host
}
