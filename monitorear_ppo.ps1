#!/usr/bin/env powershell
# Monitor simplificado - Mostrar ultimas lineas cada 10 segundos

$LogFile = "entrenamiento_ppo.log"

Write-Host ""
Write-Host "===================================" -ForegroundColor Green
Write-Host "  MONITOR DE ENTRENAMIENTO PPO" -ForegroundColor Green  
Write-Host "===================================" -ForegroundColor Green
Write-Host ""

while ($true) {
    if (Test-Path $LogFile) {
        $tail = Get-Content $LogFile -Tail 8 -ErrorAction SilentlyContinue
        
        Clear-Host
        Write-Host ""
        Write-Host "===================================" -ForegroundColor Green
        Write-Host "  MUESTREO: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
        Write-Host "===================================" -ForegroundColor Green
        Write-Host ""
        
        foreach ($line in $tail) {
            if ($line -match "Steps:") {
                Write-Host $line -ForegroundColor Yellow
            } elseif ($line -match "CO2") {
                Write-Host $line -ForegroundColor Green
            } elseif ($line -match "KL:|Entropy:|Policy|Value|Expl") {
                Write-Host $line -ForegroundColor Cyan
            } elseif ($line -match "WARNING") {
                Write-Host $line -ForegroundColor Red
            } else {
                Write-Host $line
            }
        }
        
        Write-Host ""
        Write-Host "(Presiona CTRL+C para salir)" -ForegroundColor Gray
    } else {
        Write-Host "Esperando archivo de log..." -ForegroundColor Yellow
    }
    
    Start-Sleep -Seconds 10
}
