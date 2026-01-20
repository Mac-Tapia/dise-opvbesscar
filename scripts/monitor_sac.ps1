#!/usr/bin/env powershell
# Monitor SAC Checkpoints - Muestra progreso en tiempo real

$interval = 5  # segundos

function Show-CheckpointProgress {
    $cpDir = "analyses/oe3/training/checkpoints/sac"
    $files = Get-ChildItem $cpDir -File -ErrorAction SilentlyContinue | 
    Sort-Object LastWriteTime | 
    Select-Object -Last 10
    
    Write-Host "`n=== SAC Checkpoints (Últimos 10) ===" -ForegroundColor Cyan
    Write-Host "Tiempo         | Archivo                    | Tamaño" -ForegroundColor Gray
    Write-Host "---------------------------------------------------" -ForegroundColor Gray
    
    foreach ($file in $files) {
        $time = $file.LastWriteTime.ToString("HH:mm:ss")
        $sizeKB = [math]::Round($file.Length / 1KB, 1)
        Write-Host "$time | $($file.Name.PadRight(26)) | $sizeKB KB" -ForegroundColor Yellow
    }
    
    $latestCheckpoint = $files | Select-Object -Last 1
    if ($latestCheckpoint) {
        Write-Host "`nÚltimo checkpoint: $($latestCheckpoint.Name) hace $(([datetime]::Now - $latestCheckpoint.LastWriteTime).TotalSeconds | [math]::Round) segundos" -ForegroundColor Green
    }
}

function Show-ProcessStatus {
    Write-Host "`n=== Proceso Python ===" -ForegroundColor Cyan
    $proc = Get-Process python -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -match "continue_sac" }
    
    if ($proc) {
        Write-Host "✅ EJECUTÁNDOSE (PID: $($proc.Id))" -ForegroundColor Green
        Write-Host "   Memoria: $([math]::Round($proc.WorkingSet / 1MB, 1)) MB"
        Write-Host "   Handles: $($proc.Handles)"
    }
    else {
        Write-Host "⏸️  DETENIDO" -ForegroundColor Red
    }
}

# Loop principal
try {
    while ($true) {
        Clear-Host
        Write-Host "SAC Training Monitor - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Magenta
        Write-Host "Intervalo de actualización: ${interval}s (Ctrl+C para salir)" -ForegroundColor Gray
        
        Show-CheckpointProgress
        Show-ProcessStatus
        
        Start-Sleep -Seconds $interval
    }
}
catch {
    Write-Host "`n✅ Monitor detenido" -ForegroundColor Green
}
