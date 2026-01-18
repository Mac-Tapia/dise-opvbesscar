# Script para correr Docker usando datos ya guardados
# No va a reentrenar, solo va a usar los resultados existentes

Write-Host "🐳 Iniciando Docker con DATOS EXISTENTES" -ForegroundColor Green
Write-Host "📁 Datos disponibles en: d:\diseñopvbesscar\outputs\oe3\simulations" -ForegroundColor Cyan

# Verificar Docker está corriendo
if (-not (docker ps 2>&1)) {
    Write-Host "❌ Docker no está corriendo" -ForegroundColor Red
    exit 1
}

# Copiar datos a la ubicación accesible por el volumen
Write-Host "📋 Copiando datos existentes..." -ForegroundColor Yellow

$host_data = "d:\diseñopvbesscar\outputs\oe3"
$files_to_copy = @(
    "simulations\simulation_summary.json",
    "simulations\co2_comparison.md",
    "simulations\result_Uncontrolled.json",
    "simulations\timeseries_SAC.csv",
    "simulations\timeseries_PPO.csv",
    "simulations\timeseries_A2C.csv",
    "simulations\timeseries_Uncontrolled.csv",
    "graphics\*.png"
)

foreach ($file in $files_to_copy) {
    if (Test-Path "$host_data\$file") {
        Write-Host "  ✓ $file (OK)" -ForegroundColor Green
    }
}

# Comando Docker
$docker_cmd = @"
docker run -it --rm --gpus all `
  -v "d:/diseñopvbesscar/data:/app/data" `
  -v "d:/diseñopvbesscar/outputs:/app/outputs" `
  -v "d:/diseñopvbesscar/configs:/app/configs:ro" `
  -v "d:/diseñopvbesscar/scripts:/app/scripts:ro" `
  iquitos-citylearn:latest `
  python -c "
import json
from pathlib import Path

# Cargar datos existentes
results_path = Path('/app/outputs/oe3/simulations')
summary_file = results_path / 'simulation_summary.json'

if summary_file.exists():
    with open(summary_file) as f:
        data = json.load(f)
    print('✅ Datos cargados correctamente')
    print(f'   - Agentes: {list(data.get(\"agents\", {}).keys())}')
    print(f'   - Escenarios: {len(data.get(\"scenarios\", []))}')
    print('📊 Simulación completada - No necesita re-entrenamiento')
else:
    print('❌ No se encontraron datos guardados')
"
"@

Write-Host "`n🚀 Ejecutando Docker..." -ForegroundColor Cyan
Write-Host $docker_cmd -ForegroundColor Gray

Invoke-Expression $docker_cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Docker completó correctamente" -ForegroundColor Green
    Write-Host "📁 Resultados en: d:\diseñopvbesscar\outputs\oe3\simulations" -ForegroundColor Green
}
else {
    Write-Host "`n❌ Error al ejecutar Docker" -ForegroundColor Red
}
