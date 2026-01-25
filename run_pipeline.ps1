# Script PowerShell para ejecutar pipeline completo

# Activar ambiente virtual
Write-Host "Activando ambiente virtual..." -ForegroundColor Cyan
& "d:\diseñopvbesscar\.venv\Scripts\Activate.ps1"

# Verificar Python
Write-Host "Verificando Python..." -ForegroundColor Cyan
python --version

# Establecer encoding UTF-8
$env:PYTHONIOENCODING = 'utf-8'

# Cambiar a directorio del proyecto
Set-Location d:\diseñopvbesscar

Write-Host "`n" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "INICIANDO PIPELINE COMPLETO" -ForegroundColor Green
Write-Host "1. Construir Dataset" -ForegroundColor Green
Write-Host "2. Calcular Baseline" -ForegroundColor Green
Write-Host "3. Entrenar 3 Agentes (SAC, PPO, A2C)" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "`n"

# Ejecutar pipeline
Write-Host "Ejecutando: python -m scripts.run_oe3_simulate --config configs/default.yaml" -ForegroundColor Yellow
python -m scripts.run_oe3_simulate --config configs/default.yaml

Write-Host "`n================================" -ForegroundColor Green
Write-Host "PIPELINE COMPLETADO" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
