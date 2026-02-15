# PowerShell Script - Lanzar y monitorear entrenamiento PPO
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  LANZANDO ENTRENAMIENTO PPO v5.7 - IQUITOS EV CHARGING" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

cd D:\diseñopvbesscar

# Verificar datos
Write-Host "1️⃣ Verificando datos OE2..." -ForegroundColor Yellow
python verify_data.py
Write-Host ""

# Limpiar log anterior
if (Test-Path "entrenamiento_ppo.log") {
    Remove-Item "entrenamiento_ppo.log" -Force -ErrorAction SilentlyContinue
}

# Lanzar entrenamiento
Write-Host "2️⃣ Lanzando entrenamiento en background..." -ForegroundColor Yellow
$process = Start-Process -FilePath "python" -ArgumentList "launch_training.py" `
    -RedirectStandardOutput "entrenamiento_ppo.log" `
    -RedirectStandardError "entrenamiento_ppo_error.log" `
    -PassThru -NoNewWindow

Write-Host "✅ Proceso iniciado con PID: $($process.Id)" -ForegroundColor Green
Write-Host ""

# Monitoreo
Write-Host "3️⃣ MONITOREO DEL ENTRENAMIENTO (cada 30 segundos):" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────────────────────────" -ForegroundColor Cyan

$count = 0
while (!$process.HasExited) {
    $count++
    $time = Get-Date -Format "HH:mm:ss"
    Write-Host "[$time] Check #$count" -ForegroundColor Cyan -NoNewline
    
    if (Test-Path "entrenamiento_ppo.log") {
        $lines = @(Get-Content "entrenamiento_ppo.log" -ErrorAction SilentlyContinue)
        Write-Host " - Total lines: $($lines.Count)" -ForegroundColor Cyan
        
        # Mostrar últimas líneas
        if ($lines.Count -gt 0) {
            $last3 = $lines | Select-Object -Last 3
            foreach ($line in $last3) {
                Write-Host "  $line" -ForegroundColor White
            }
        }
    } else {
        Write-Host " - Esperando log..." -ForegroundColor Gray
    }
    
    Write-Host ""
    Start-Sleep -Seconds 30
}

Write-Host "────────────────────────────────────────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host "✅ ENTRENAMIENTO FINALIZADO" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Mostrar resumen final
if (Test-Path "entrenamiento_ppo.log") {
    Write-Host "📋 ÚLTIMAS LÍNEAS DEL LOG:" -ForegroundColor Cyan
    Get-Content "entrenamiento_ppo.log" -Tail 30 | Select-String "(EPISODIO|Steps:|CO2|Error|Traceback)" -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "✓ Archivos generados en: outputs\ppo_training" -ForegroundColor Green
Write-Host "✓ Checkpoint en: checkpoints\PPO\latest.zip" -ForegroundColor Green
Write-Host ""
