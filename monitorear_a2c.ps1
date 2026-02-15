#!/usr/bin/env powershell
# Monitor simplificado A2C - Mostrar ultimas lineas cada 10 segundos

$LogFile = "entrenamiento_a2c.log"

Write-Host ""
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "  MONITOR - ENTRENAMIENTO A2C" -ForegroundColor Cyan  
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

$lastPosition = 0

while ($true) {
    if (Test-Path $LogFile) {
        $tail = Get-Content $LogFile -Tail 10 -ErrorAction SilentlyContinue
        
        Clear-Host
        Write-Host ""
        Write-Host "===================================" -ForegroundColor Cyan
        Write-Host "  MUESTREO: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor White
        Write-Host "===================================" -ForegroundColor Cyan
        Write-Host ""
        
        foreach ($line in $tail) {
            if ($line -match "Step\s+[\d,]+") {
                Write-Host $line -ForegroundColor Yellow
            } elseif ($line -match "Entropy:|Loss:|Expl\.Var") {
                Write-Host $line -ForegroundColor Green
            } elseif ($line -match "WARNING" -or $line -match "ERROR") {
                Write-Host $line -ForegroundColor Red
            } elseif ($line -match "OK |Cargado" -or $line -match "Agent" -or $line -match "Device") {
                Write-Host $line -ForegroundColor Yellow
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
