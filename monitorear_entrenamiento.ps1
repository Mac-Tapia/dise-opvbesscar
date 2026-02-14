#!/usr/bin/env pwsh
<#
.SYNOPSIS
Monitor SAC training progress in real-time
.DESCRIPTION
Reads training log file and shows progress, metrics, and alerts for SAC training
#>

param(
    [int]$RefreshSeconds = 10,
    [string]$LogFile = "outputs/sac_training/live_training.log"
)

function Get-TrainingStats {
    param([string]$FilePath)
    
    if (!(Test-Path $FilePath)) {
        return $null
    }
    
    $content = Get-Content $FilePath -Raw
    $lines = $content -split "`n"
    
    # Get last 50 lines
    $recent_lines = $lines[-50..-1]
    
    return $recent_lines
}

function Show-Status {
    Clear-Host
    
    Write-Host "=======================================================================" -ForegroundColor Cyan
    Write-Host "SAC TRAINING MONITOR EN VIVO" -ForegroundColor Yellow
    Write-Host "=======================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    $stats = Get-TrainingStats $LogFile
    
    if ($null -eq $stats) {
        Write-Host "Esperando que inicie el entrenamiento..." -ForegroundColor Yellow
        return
    }
    
    Write-Host "ULTIMAS 50 LINEAS DEL LOG:" -ForegroundColor Cyan
    Write-Host "-----------------------------------------------------------------------"
    
    foreach ($line in $stats) {
        if ($line -match "error|Error|ERROR") {
            Write-Host $line -ForegroundColor Red
        }
        elseif ($line -match "warning|Warning|WARNING") {
            Write-Host $line -ForegroundColor Yellow
        }
        elseif ($line -match "OK|succes|load") {
            Write-Host $line -ForegroundColor Green
        }
        elseif ($line -match "Logging|timesteps|Q-value|Entropy|loss") {
            Write-Host $line -ForegroundColor Cyan
        }
        else {
            Write-Host $line -ForegroundColor White
        }
    }
    
    Write-Host ""
    Write-Host "=======================================================================" -ForegroundColor Cyan
    Write-Host "Proxima actualizacion en $RefreshSeconds segundos (Ctrl+C para salir)" -ForegroundColor Gray
    Write-Host "=======================================================================" -ForegroundColor Cyan
}

# Main loop
while ($true) {
    Show-Status
    Start-Sleep -Seconds $RefreshSeconds
}
