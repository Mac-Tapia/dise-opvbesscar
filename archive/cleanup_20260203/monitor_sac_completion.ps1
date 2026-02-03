# Monitor SAC Training Completion and File Generation
# Este script espera a que termine el entrenamiento SAC y verifica la generación de archivos

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MONITOR: SAC Training Completion" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$outputDir = "d:\diseñopvbesscar\outputs\oe3\simulations"
$checkpointDir = "d:\diseñopvbesscar\checkpoints\sac"
$maxWaitMinutes = 60
$checkInterval = 10
$startTime = Get-Date
$lastCheckpointTime = (Get-ChildItem $checkpointDir -Filter "sac_step_*.zip" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime

Write-Host "[INFO] Esperando a que termine entrenamiento SAC (máx $maxWaitMinutes minutos)..." -ForegroundColor Yellow
Write-Host "[INFO] Verificando cada $checkInterval segundos..." -ForegroundColor Yellow
Write-Host ""

$iteration = 0
$sacFilesFound = $false

while ($true) {
    $iteration++
    $elapsedMinutes = [math]::Round(((Get-Date) - $startTime).TotalSeconds / 60, 1)

    # Check if SAC result files exist
    $resultFile = Join-Path $outputDir "result_SAC.json"
    $timeseriesFile = Join-Path $outputDir "timeseries_SAC.csv"
    $traceFile = Join-Path $outputDir "trace_SAC.csv"

    $hasResultFile = Test-Path $resultFile
    $hasTimeseriesFile = Test-Path $timeseriesFile
    $hasTraceFile = Test-Path $traceFile

    # Check checkpoint progression
    $latestCheckpoint = Get-ChildItem $checkpointDir -Filter "sac_step_*.zip" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $latestCheckpointName = if ($latestCheckpoint) { $latestCheckpoint.Name } else { "None" }
    $latestCheckpointTime = if ($latestCheckpoint) { '{0:HH:mm:ss}' -f $latestCheckpoint.LastWriteTime } else { "N/A" }

    # Display status every 2 iterations
    if ($iteration % 2 -eq 1) {
        Write-Host "[$elapsedMinutes min] [$iteration check] Latest checkpoint: $latestCheckpointName ($latestCheckpointTime)" -ForegroundColor Cyan
        if ($hasResultFile -or $hasTimeseriesFile -or $hasTraceFile) {
            Write-Host "  ✅ result_SAC.json: $(if ($hasResultFile) { 'FOUND' } else { 'PENDING' })" -ForegroundColor Green
            Write-Host "  ✅ timeseries_SAC.csv: $(if ($hasTimeseriesFile) { 'FOUND' } else { 'PENDING' })" -ForegroundColor Green
            Write-Host "  ✅ trace_SAC.csv: $(if ($hasTraceFile) { 'FOUND' } else { 'PENDING' })" -ForegroundColor Green
        }
    }

    # Check if all files exist
    if ($hasResultFile -and $hasTimeseriesFile -and $hasTraceFile) {
        Write-Host ""
        Write-Host "✅✅✅ SUCCESS! All SAC result files generated! ✅✅✅" -ForegroundColor Green
        Write-Host ""
        Write-Host "  📊 result_SAC.json: $((Get-Item $resultFile).Length) bytes" -ForegroundColor Green
        Write-Host "  📊 timeseries_SAC.csv: $((Get-Item $timeseriesFile).Length) bytes" -ForegroundColor Green
        Write-Host "  📊 trace_SAC.csv: $((Get-Item $traceFile).Length) bytes" -ForegroundColor Green
        Write-Host ""
        Write-Host "Elapsed time: $elapsedMinutes minutes" -ForegroundColor Green
        break
    }

    # Check if timeout exceeded
    if ($elapsedMinutes -gt $maxWaitMinutes) {
        Write-Host ""
        Write-Host "❌ TIMEOUT: SAC training did not complete within $maxWaitMinutes minutes" -ForegroundColor Red
        Write-Host "Files status after $elapsedMinutes minutes:" -ForegroundColor Red
        Write-Host "  result_SAC.json: $(if ($hasResultFile) { 'FOUND' } else { 'NOT FOUND' })" -ForegroundColor Red
        Write-Host "  timeseries_SAC.csv: $(if ($hasTimeseriesFile) { 'FOUND' } else { 'NOT FOUND' })" -ForegroundColor Red
        Write-Host "  trace_SAC.csv: $(if ($hasTraceFile) { 'FOUND' } else { 'NOT FOUND' })" -ForegroundColor Red
        break
    }

    # Sleep before next check
    Start-Sleep -Seconds $checkInterval
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Monitor completed" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
