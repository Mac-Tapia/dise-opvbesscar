# Script para ejecutar pipeline OE3 con GPU forzado
$env:PYTHONIOENCODING = 'utf-8'
$env:CUDA_VISIBLE_DEVICES = '0'  # Forzar GPU 0
$env:TF_CPP_MIN_LOG_LEVEL = '2'  # Reducir logs TensorFlow

# Usar Get-Location para evitar problemas de caracteres especiales
$workdir = Get-Location
Write-Host "Directorio: $workdir" -ForegroundColor Cyan

Write-Host "================================" -ForegroundColor Cyan
Write-Host "PIPELINE OE3 - ENTRENAMIENTO CON GPU" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuracion:" -ForegroundColor Yellow
Write-Host "  CUDA_VISIBLE_DEVICES: 0 (GPU RTX 4060)" -ForegroundColor Green
Write-Host "  Encoding: UTF-8" -ForegroundColor Green
Write-Host ""
Write-Host "Activando venv..." -ForegroundColor Cyan
& ".venv\Scripts\Activate.ps1"

Write-Host "Ejecutando pipeline..." -ForegroundColor Green
python -m scripts.run_oe3_simulate --config configs/default.yaml

Write-Host ""
Write-Host "Pipeline completado" -ForegroundColor Green
