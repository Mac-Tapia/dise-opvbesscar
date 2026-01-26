$logFile = "training_output.log"
Write-Host "Monitoreando inicio de SAC..." -ForegroundColor Cyan
Write-Host "Revisando cada 60 segundos..." -ForegroundColor Gray
Write-Host ""

$sacFound = $false
while (-not $sacFound) {
    if (Test-Path $logFile) {
        $content = Get-Content $logFile
        $sacLines = $content | Select-String "SAC.*reward_avg"
        
        if ($sacLines.Count -gt 0) {
            $sacFound = $true
            Write-Host ""
            Write-Host "=== SAC INICIADO ===" -ForegroundColor Green
            Write-Host "Hora: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Primeras 10 lineas con reward_avg:" -ForegroundColor Cyan
            Write-Host ""
            
            $sacLines | Select-Object -First 10 | ForEach-Object {
                Write-Host $_.Line -ForegroundColor White
            }
            
            Write-Host ""
            Write-Host "=== VALIDACION ===" -ForegroundColor Magenta
            $rewards = @()
            $sacLines | Select-Object -First 10 | ForEach-Object {
                if ($_.Line -match "reward_avg=([0-9.]+)") { 
                    $rewards += $matches[1] 
                }
            }
            $uniqueRewards = $rewards | Select-Object -Unique
            
            Write-Host "Valores unicos de reward_avg: $($uniqueRewards -join ', ')" -ForegroundColor Yellow
            
            if ($uniqueRewards.Count -gt 1) {
                Write-Host "OK SLIDING WINDOW FUNCIONANDO - reward_avg varia!" -ForegroundColor Green
            } else {
                Write-Host "PROBLEMA - reward_avg sigue fijo en $($uniqueRewards[0])" -ForegroundColor Red
            }
            
            Write-Host ""
            Write-Host "Presiona Ctrl+C para salir..." -ForegroundColor Gray
            Start-Sleep 10
            break
        }
    }
    
    if (Test-Path $logFile) {
        $lastLine = Get-Content $logFile -Tail 1
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $lastLine" -ForegroundColor DarkGray
    }
    
    Start-Sleep 60
}
