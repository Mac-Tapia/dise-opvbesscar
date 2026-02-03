# Comando rápido para verificar estado del entrenamiento SAC Clean Start

# OPCIÓN 1: Ver último checkpoint guardado
Write-Host "CHECKPOINTS GUARDADOS:" -ForegroundColor Yellow
$latest = Get-ChildItem D:\diseñopvbesscar\checkpoints\sac\sac_step_*.zip -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latest -and $latest.Name -match "step_(\d+)") {
    $step = [int]$matches[1]
    $mb = [math]::Round($latest.Length / 1MB, 1)
    Write-Host "   Último: paso $step ($mb MB) - $($latest.LastWriteTime)" -ForegroundColor Green
} else {
    Write-Host "   (Aguardando primer checkpoint...)" -ForegroundColor Yellow
}

# OPCIÓN 2: Ver si Python sigue corriendo
Write-Host ""
Write-Host "PROCESO:" -ForegroundColor Yellow
$proc = Get-Process python -ErrorAction SilentlyContinue | Select-Object -First 1
if ($proc) {
    $mem = [math]::Round($proc.WorkingSet / 1MB)
    Write-Host "   ✓ Python activo - Memory: $mem MB" -ForegroundColor Green
} else {
    Write-Host "   ⏳ Python no ejecutando" -ForegroundColor Yellow
}

# OPCIÓN 3: Ver archivos finales (cuando terminen)
Write-Host ""
Write-Host "RESULTADOS:" -ForegroundColor Yellow
$resultJSON = Get-ChildItem D:\diseñopvbesscar\outputs\oe3\simulations\result_SAC.json -ErrorAction SilentlyContinue
$resultCSV = Get-ChildItem D:\diseñopvbesscar\outputs\oe3\simulations\timeseries_SAC.csv -ErrorAction SilentlyContinue

if ($resultJSON) {
    Write-Host "   ✓ result_SAC.json" -ForegroundColor Green
} else {
    Write-Host "   [ ] result_SAC.json" -ForegroundColor Gray
}

if ($resultCSV) {
    Write-Host "   ✓ timeseries_SAC.csv" -ForegroundColor Green
} else {
    Write-Host "   [ ] timeseries_SAC.csv" -ForegroundColor Gray
}

Write-Host ""
