# PowerShell Script para lanzar y monitorear entrenamiento PPO
# Iquitos EV Charging Optimization

Write-Host "" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  🚀 LANZANDO ENTRENAMIENTO PPO v5.7 - IQUITOS EV CHARGING OPTIMIZATION" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "" -ForegroundColor Cyan

# Verificar que estamos en el directorio correcto
$projectPath = "D:\diseñopvbesscar"
if (!(Test-Path $projectPath)) {
    Write-Host "❌ Error: No se encontró el directorio del proyecto en $projectPath" -ForegroundColor Red
    exit 1
}
cd $projectPath

# Verificar que Python está disponible
$pythonPath = python -c "import sys; print(sys.executable)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: Python no está disponible en el entorno virtual" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python: $pythonPath" -ForegroundColor Green

# Limpiar log anterior si existe
if (Test-Path "entrenamiento_ppo.log") {
    Remove-Item "entrenamiento_ppo.log" -Force
}

Write-Host "✓ Log file: entrenamiento_ppo.log" -ForegroundColor Green
Write-Host "" -ForegroundColor Cyan

# Lanzar entrenamiento en background redirigiéndolo al log
Write-Host "⏳ Lanzando entrenamiento..." -ForegroundColor Yellow
$process = Start-Process -FilePath "python" -ArgumentList "launch_training.py" `
    -RedirectStandardOutput "entrenamiento_ppo.log" `
    -RedirectStandardError "entrenamiento_ppo_error.log" `
    -PassThru `
    -NoNewWindow

Write-Host "✅ Entrenamiento iniciado con PID: $($process.Id)" -ForegroundColor Green
Write-Host "" -ForegroundColor Cyan

# Esperar a que el archivo log se cree
Start-Sleep -Seconds 2

# Monitoreo continuo
Write-Host "📊 MONITOREO DEL ENTRENAMIENTO:" -ForegroundColor Cyan
Write-Host "────────────────────────────────────────────────────────────────────────────────────" -ForegroundColor Cyan

$monitoringActive = $true
$iteration = 0
$lastLineCount = 0

while ($monitoringActive) {
    # Incrementar contador
    $iteration++
    
    # Mostrar timestamp
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] Check #$iteration" -ForegroundColor Cyan -NoNewline
    
    # Verificar si el archivo de log existe
    if (Test-Path "entrenamiento_ppo.log") {
        $logContent = Get-Content "entrenamiento_ppo.log" -ErrorAction SilentlyContinue
        if ($logContent) {
            # Contar líneas
            if ($logContent -is [array]) {
                $currentLineCount = $logContent.Count
            } else {
                $currentLineCount = 1
            }
            
            # Si hay nuevas líneas, mostrar últimas 3
            if ($currentLineCount -gt $lastLineCount) {
                Write-Host " (+$($currentLineCount - $lastLineCount) líneas)" -ForegroundColor Green
                
                # Mostrar últimas líneas
                $lastLines = $logContent | Select-Object -Last 3
                foreach ($line in $lastLines) {
                    if ($line) {
                        # Colorear según contenido
                        if ($line -match "EPISODIO|Episode") {
                            Write-Host "  ▶ $line" -ForegroundColor Yellow
                        } elseif ($line -match "ERROR|Error|❌") {
                            Write-Host "  ✗ $line" -ForegroundColor Red
                        } elseif ($line -match "✓|✅|Completado") {
                            Write-Host "  ✓ $line" -ForegroundColor Green
                        } else {
                            Write-Host "  • $line" -ForegroundColor White
                        }
                    }
                }
                $lastLineCount = $currentLineCount
            } else {
                Write-Host " (sin cambios)" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host " (esperando log...)" -ForegroundColor Gray
    }
    
    # Verificar si el proceso sigue vivo
    if (!$process.HasExited) {
        # Continuar monitoring cada 30 segundos
        Start-Sleep -Seconds 30
    } else {
        Write-Host "" -ForegroundColor Cyan
        Write-Host "────────────────────────────────────────────────────────────────────────────────────" -ForegroundColor Cyan
        Write-Host "✅ ENTRENAMIENTO COMPLETADO" -ForegroundColor Green
        Write-Host "Exit Code: $($process.ExitCode)" -ForegroundColor Green
        
        # Mostrar últimas líneas del log
        Write-Host "" -ForegroundColor Cyan
        if (Test-Path "entrenamiento_ppo.log") {
            Write-Host "📋 RESULTADOS FINALES:" -ForegroundColor Cyan
            Write-Host "────────────────────────────────────────────────────────────────────────────────────" -ForegroundColor Cyan
            $finalLines = Get-Content "entrenamiento_ppo.log" -Tail 20
            foreach ($line in $finalLines) {
                if ($line -match "RESULTADO|resultado|Reward|CO2|ERROR") {
                    Write-Host "$line" -ForegroundColor White
                }
            }
        }
        
        $monitoringActive = $false
    }
}

Write-Host "" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Archivos generados en: outputs\ppo_training\" -ForegroundColor Green
Write-Host "Checkpoint guardado en: checkpoints\PPO\" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "" -ForegroundColor Cyan
