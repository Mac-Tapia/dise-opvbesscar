# PowerShell Script - Lanzar entrenamiento PPO
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  LANZANDO ENTRENAMIENTO PPO v5.7" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

cd D:\diseñopvbesscar

# Verificar datos
Write-Host "1. Verificando datos OE2..." -ForegroundColor Yellow
python verify_data.py
Write-Host ""

# Limpiar log anterior
if (Test-Path "entrenamiento_ppo.log") {
    Remove-Item "entrenamiento_ppo.log" -Force -ErrorAction SilentlyContinue
}

# Lanzar entrenamiento en background
Write-Host "2. Lanzando entrenamiento..." -ForegroundColor Yellow
$process = Start-Process -FilePath "python" -ArgumentList "launch_training.py" `
    -RedirectStandardOutput "entrenamiento_ppo.log" `
    -RedirectStandardError "entrenamiento_ppo_error.log" `
    -PassThru -NoNewWindow

Write-Host "OK Proceso iniciado con PID: $($process.Id)" -ForegroundColor Green
Write-Host ""

# Monitoreo
Write-Host "3. MONITOREO (cada 30 segundos):" -ForegroundColor Yellow
Write-Host "========================================================================" -ForegroundColor Cyan

$count = 0
while (!$process.HasExited) {
    $count++
    $time = Get-Date -Format "HH:mm:ss"
    
    if (Test-Path "entrenamiento_ppo.log") {
        $lines = @(Get-Content "entrenamiento_ppo.log" -ErrorAction SilentlyContinue)
        $lineCount = $lines.Count
        Write-Host "[$time] Check #$count - Lines: $lineCount" -ForegroundColor Cyan
        
        # Mostrar ultimas lineas
        if ($lineCount -gt 0) {
            $last2 = $lines | Select-Object -Last 2
            foreach ($line in $last2) {
                if ($line) {
                    Write-Host "  $line" -ForegroundColor Gray
                }
            }
        }
    } else {
        Write-Host "[$time] Check #$count - Esperando log..." -ForegroundColor Gray
    }
    
    Write-Host ""
    Start-Sleep -Seconds 30
}

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "OK ENTRENAMIENTO FINALIZADO" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Archivos: outputs/ppo_training/" -ForegroundColor Green
Write-Host "Checkpoint: checkpoints/PPO/latest.zip" -ForegroundColor Green
Write-Host ""
