#!/usr/bin/env pwsh
# Monitoreo en tiempo real del entrenamiento SAC

$log_file = "entrenamiento_sac.log"
$last_lines_count = 0

Write-Host ""
Write-Host "═════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "MONITOREO EN TIEMPO REAL - ENTRENAMIENTO SAC"
Write-Host "═════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Actualizando cada 3 segundos... Presiona Ctrl+C para salir" -ForegroundColor Yellow
Write-Host ""

$start_time = Get-Date
$step_count = 0
$last_q_value = $null

try {
    while ($true) {
        # Esperar 3 segundos
        Start-Sleep -Seconds 3
        
        if (Test-Path $log_file) {
            try {
                $all_lines = @(Get-Content -Path $log_file -ErrorAction SilentlyContinue)
            }
            catch {
                continue
            }
            
            $current_count = $all_lines.Count
            
            if ($current_count -gt $last_lines_count) {
                # Mostrar nuevas líneas relevantes
                $new_lines = $all_lines | Select-Object -Last ($current_count - $last_lines_count)
                
                foreach ($line in $new_lines) {
                    # Líneas importantes a monitorear
                    if ($line -match "STEP \d+|Entropy|Alpha|LOSSES|Q-VALUES|ACTION|TRAINING|✅|❌|⚠") {
                        if ($line -match "STEP (\d+)") {
                            $step_count = [int]$matches[1]
                        }
                        
                        Write-Host $line -ForegroundColor Gray
                    }
                    elseif ($line -match "Inicio:|Entrenamiento|Checkpoint|GPU|Device") {
                        Write-Host $line -ForegroundColor Green
                    }
                    elseif ($line -match "ERROR|Error|error") {
                        Write-Host $line -ForegroundColor Red
                    }
                }
                
                $last_lines_count = $current_count
            }
            
            # Estado actual
            $elapsed = (Get-Date) - $start_time
            $status = "Entrenando... Steps: {0:D6} | Tiempo: {1:D2}h {2:D2}m {3:D2}s" -f $step_count, $elapsed.Hours, $elapsed.Minutes, $elapsed.Seconds
            Write-Host "`r$status" -ForegroundColor Cyan -NoNewline
        }
    }
}
catch [System.Management.Automation.PipelineStoppedException] {
    Write-Host ""
    Write-Host ""
    Write-Host "Monitor detenido por usuario" -ForegroundColor Yellow
}
catch {
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "═════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "MOSTRAR ÚLTIMAS LÍNEAS DEL LOG:"
Write-Host "═════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $log_file) {
    Get-Content -Path $log_file -Tail 20
}

Write-Host ""
