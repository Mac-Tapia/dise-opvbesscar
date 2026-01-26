#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Relanza el pipeline completo de entrenamiento OE3 para PVBESSCAR Iquitos

.DESCRIPTION
    Script automatizado para ejecutar:
    1. Dataset builder (128 chargers + solar + demand)
    2. Baseline simulation (referencia sin RL)
    3. SAC training (5 episodios)
    4. PPO training (5 episodios)
    5. A2C training (5 episodios)

.PARAMETER SkipDataset
    Saltar construcción de dataset (usar dataset existente)

.PARAMETER SkipBaseline
    Saltar simulación baseline

.PARAMETER OnlyDataset
    Solo construir dataset, no entrenar agentes

.EXAMPLE
    .\RELANZAR_PIPELINE.ps1
    # Relanza pipeline completo desde cero

.EXAMPLE
    .\RELANZAR_PIPELINE.ps1 -SkipDataset
    # Usa dataset existente y entrena agentes

.EXAMPLE
    .\RELANZAR_PIPELINE.ps1 -OnlyDataset
    # Solo reconstruye dataset

.NOTES
    Duración estimada: 8-12 horas (con GPU CUDA)
    Log file: training_pipeline_YYYYMMDD_HHmmss.log
    Requisitos: Python 3.11, CUDA 11.8+ (opcional)
#>

param(
    [switch]$SkipDataset,
    [switch]$SkipBaseline,
    [switch]$OnlyDataset,
    [switch]$NoGPU
)

# Configuración
$ProjectRoot = "d:\diseñopvbesscar"
$PythonExe = "C:\Users\Lenovo Legion\AppData\Local\Programs\Python\Python311\python.exe"
$ConfigFile = "configs/default.yaml"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = "training_pipeline_$Timestamp.log"

Write-Host "`n" -ForegroundColor White
Write-Host "╔════════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                  PIPELINE OE3 - PVBESSCAR IQUITOS                             ║" -ForegroundColor Cyan
Write-Host "║                                                                                ║" -ForegroundColor Cyan
Write-Host "║  Dataset: 128 chargers | 8.04 MWh/año solar | 12.4 GWh/año demanda           ║" -ForegroundColor Cyan
Write-Host "║  Agents: SAC → PPO → A2C (en serie, checkpoints acumulables)                 ║" -ForegroundColor Cyan
Write-Host "║                                                                                ║" -ForegroundColor Cyan
Write-Host "║  Duración estimada: 8-12 horas (GPU CUDA)                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Cambiar al directorio del proyecto
cd $ProjectRoot

# Configurar variables de entorno
$env:PYTHONIOENCODING = 'utf-8'
if (-not $NoGPU) {
    $env:CUDA_VISIBLE_DEVICES = '0'
    Write-Host "✓ GPU CUDA habilitada (CUDA_VISIBLE_DEVICES=0)" -ForegroundColor Green
} else {
    Write-Host "⚠ GPU CUDA deshabilitada (modo CPU)" -ForegroundColor Yellow
}

# Verificar Python
Write-Host "`n📋 VERIFICACIÓN PREVIA:" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Host "✗ Python 3.11 no encontrado en: $PythonExe" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python 3.11 encontrado" -ForegroundColor Green

# Verificar dataset existente
$DatasetCheck = Test-Path "data/processed/citylearn/iquitos_ev_mall/schema.json"
if ($DatasetCheck) {
    Write-Host "✓ Dataset existente encontrado" -ForegroundColor Green
} else {
    Write-Host "⚠ Dataset no encontrado (será construido)" -ForegroundColor Yellow
    $SkipDataset = $false
}

# Limpiar checkpoints si no es skip
if (-not $SkipDataset) {
    Write-Host "`n🗑️  Limpiando checkpoints viejos..." -ForegroundColor Yellow
    Remove-Item -Path "checkpoints\SAC", "checkpoints\PPO", "checkpoints\A2C" `
        -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Checkpoints limpios" -ForegroundColor Green
}

# ============================================================================
# FASE 1: DATASET BUILDER
# ============================================================================

if (-not $SkipDataset) {
    Write-Host "`n" -ForegroundColor White
    Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "FASE 1: DATASET BUILDER (3-5 minutos)" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

    Write-Host "📦 Construyendo dataset:" -ForegroundColor Yellow
    Write-Host "   • Solar: 8.04 MWh/año (1,932.5 kWh/año/kWp × 4,162 kWp)" -ForegroundColor Cyan
    Write-Host "   • Demanda: 12,368,025 kWh/año (mall real)" -ForegroundColor Cyan
    Write-Host "   • BESS: 4,520 kWh @ 2,712 kW" -ForegroundColor Cyan
    Write-Host "   • Chargers: 128 (112 motos + 16 mototaxis)" -ForegroundColor Cyan
    Write-Host ""

    & $PythonExe -m scripts.run_oe3_build_dataset --config $ConfigFile 2>&1 | Tee-Object -FilePath $LogFile -Append

    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Dataset builder falló" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Dataset construido exitosamente" -ForegroundColor Green
}

# ============================================================================
# FASE 2: BASELINE (OPCIONAL)
# ============================================================================

if (-not $SkipBaseline -and -not $OnlyDataset) {
    Write-Host "`n" -ForegroundColor White
    Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "FASE 2: BASELINE SIMULATION (10-15 minutos)" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

    Write-Host "📊 Calculando referencia sin control RL..." -ForegroundColor Yellow

    & $PythonExe -m scripts.run_uncontrolled_baseline --config $ConfigFile 2>&1 | Tee-Object -FilePath $LogFile -Append

    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Baseline falló (continuando con agentes)" -ForegroundColor Yellow
    } else {
        Write-Host "✓ Baseline completado" -ForegroundColor Green
    }
}

# ============================================================================
# SI SOLO DATASET, TERMINAR AQUÍ
# ============================================================================

if ($OnlyDataset) {
    Write-Host "`n✓ Dataset construido exitosamente" -ForegroundColor Green
    Write-Host "Log guardado en: $LogFile" -ForegroundColor Cyan
    exit 0
}

# ============================================================================
# FASE 3-5: ENTRENAMIENTO RL (SAC → PPO → A2C)
# ============================================================================

Write-Host "`n" -ForegroundColor White
Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "FASES 3-5: ENTRENAMIENTO RL (6-9 horas)" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "🤖 Configuración de agentes:" -ForegroundColor Yellow
Write-Host "   SAC:  batch=128, lr=3e-4, 5 episodios" -ForegroundColor Cyan
Write-Host "   PPO:  batch=128, lr=1e-4, 5 episodios" -ForegroundColor Cyan
Write-Host "   A2C:  lr=5e-4,   n_steps=2048, 5 episodios" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Modo: Checkpoints acumulables (reset_num_timesteps=False)" -ForegroundColor Yellow
Write-Host "💾 Log: $LogFile" -ForegroundColor Yellow
Write-Host ""

& $PythonExe -m scripts.run_oe3_simulate --config $ConfigFile 2>&1 | Tee-Object -FilePath $LogFile -Append

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Pipeline completado exitosamente" -ForegroundColor Green
} else {
    Write-Host "`n✗ Pipeline terminó con errores" -ForegroundColor Red
    exit 1
}

# ============================================================================
# RESUMEN FINAL
# ============================================================================

Write-Host "`n" -ForegroundColor White
Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "PIPELINE COMPLETADO" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "📂 Archivos generados:" -ForegroundColor Green
Write-Host "   ✓ outputs/oe3_simulations/simulation_summary.json" -ForegroundColor Cyan
Write-Host "   ✓ checkpoints/SAC/latest.zip" -ForegroundColor Cyan
Write-Host "   ✓ checkpoints/PPO/latest.zip" -ForegroundColor Cyan
Write-Host "   ✓ checkpoints/A2C/latest.zip" -ForegroundColor Cyan
Write-Host "   ✓ training_pipeline_$Timestamp.log" -ForegroundColor Cyan
Write-Host ""

Write-Host "📊 Próximos pasos:" -ForegroundColor Yellow
Write-Host "   1. Revisar resultados en: outputs/oe3_simulations/" -ForegroundColor Cyan
Write-Host "   2. Comparar agentes (SAC vs PPO vs A2C vs Baseline)" -ForegroundColor Cyan
Write-Host "   3. Usar checkpoints para predicciones/deployment" -ForegroundColor Cyan
Write-Host ""

Write-Host "📝 Log completo disponible en: $LogFile" -ForegroundColor Cyan
Write-Host ""
