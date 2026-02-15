#!/usr/bin/env powershell
# Monitor simplificado PPO - Mostrar ultimas lineas cada 10 segundos

$LogFile = "entrenamiento_ppo.log"

Write-Host ""
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "  MONITOR - ENTRENAMIENTO PPO" -ForegroundColor Cyan  
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

$lastPosition = 0

while ($true) {
    if (Test-Path $LogFile) {
        $tail = Get-Content $LogFile -Tail 12 -ErrorAction SilentlyContinue
        
        Clear-Host
        Write-Host ""
        Write-Host "===================================" -ForegroundColor Cyan
        Write-Host "  MUESTREO: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor White
        Write-Host "===================================" -ForegroundColor Cyan
        Write-Host ""
        
        foreach ($line in $tail) {
            if ($line -match "Steps:|Ep:" -or $line -match "Progreso:") {
                Write-Host $line -ForegroundColor Yellow
            } elseif ($line -match "COMPLETADO|Reward Total" -or $line -match "Reduccion") {
                Write-Host $line -ForegroundColor Green
            } elseif ($line -match "CO2_grid:|CO2_evitado:" -or $line -match "Energia|BESS|Motos|Taxis") {
                Write-Host $line -ForegroundColor Cyan
            } elseif ($line -match "WARNING" -or $line -match "ERROR") {
                Write-Host $line -ForegroundColor Red
            } elseif ($line -match "KL:|Entropy:|Clip|Policy|Value|Expl") {
                Write-Host $line -ForegroundColor White
            } else {
                Write-Host $line
            }
        }
        
        Write-Host ""
        Write-Host "(Presiona CTRL+C para salir | Archivo: $LogFile)" -ForegroundColor Gray
    } else {
        Write-Host "Esperando archivo de log: $LogFile..." -ForegroundColor Gray
    }
    
    Start-Sleep -Seconds 10
}
