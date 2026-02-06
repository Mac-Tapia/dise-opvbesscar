# ============================================================================
# EJECUTAR ENTRENAMIENTO DENTRO DE .venv AUTOMÁTICAMENTE
# ============================================================================
# Uso:
#   .\scripts\run_training.ps1 sac              # Entrena SAC
#   .\scripts\run_training.ps1 ppo              # Entrena PPO
#   .\scripts\run_training.ps1 a2c              # Entrena A2C
#   .\scripts\run_training.ps1 test             # Test ambiente

param(
    [string]$Agent = "sac",
    [switch]$GPU = $false
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPath = Join-Path $ProjectRoot ".venv"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

# Validar que .venv existe
if (-not (Test-Path $ActivateScript)) {
    Write-Host "❌ ERROR: .venv no encontrado" -ForegroundColor Red
    Write-Host "   Crea el ambiente con: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Activar ambiente
Write-Host "🔄 Activando .venv..." -ForegroundColor Cyan
& $ActivateScript

# Validar que se activó correctamente
$PyExe = (python -c "import sys; print(sys.executable)")
if ($PyExe -notlike "*$VenvPath*") {
    Write-Host "❌ ERROR: No se pudo activar .venv correctamente" -ForegroundColor Red
    Write-Host "   Python: $PyExe" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ AMBIENTE ACTIVADO: $VenvPath" -ForegroundColor Green
Write-Host ""

# Ejecutar según el agente
switch ($Agent.ToLower()) {
    "sac" {
        Write-Host "🚀 ENTRENANDO SAC..." -ForegroundColor Yellow
        Write-Host "   Duración esperada: 5-7 horas en GPU (RTX 4060)" -ForegroundColor Gray
        Write-Host "   Duración esperada: 20-30 horas en CPU" -ForegroundColor Gray
        Write-Host ""
        Set-Location $ProjectRoot
        python train_sac_multiobjetivo.py
    }
    "ppo" {
        Write-Host "🚀 ENTRENANDO PPO..." -ForegroundColor Yellow
        Write-Host "   Duración esperada: 4-6 horas en GPU" -ForegroundColor Gray
        Set-Location $ProjectRoot
        python train_ppo_multiobjetivo.py
    }
    "a2c" {
        Write-Host "🚀 ENTRENANDO A2C..." -ForegroundColor Yellow
        Write-Host "   Duración esperada: 3-5 horas en GPU" -ForegroundColor Gray
        Set-Location $ProjectRoot
        python train_a2c_multiobjetivo.py
    }
    "test" {
        Write-Host "🧪 VERIFICANDO AMBIENTE..." -ForegroundColor Cyan
        Write-Host ""
        python -c @'
from src.utils.environment_validator import validate_venv_active, get_venv_info
validate_venv_active()
info = get_venv_info()
print("✅ AMBIENTE OK:")
for k, v in info.items():
    print(f"   {k}: {v}")
'@
    }
    "install" {
        Write-Host "📦 INSTALANDO DEPENDENCIAS EN .venv..." -ForegroundColor Cyan
        Write-Host ""
        Set-Location $ProjectRoot
        pip install -e . -q 2>$null
        pip install -r requirements.txt -q 2>$null
        Write-Host "✅ Dependencias instaladas" -ForegroundColor Green
    }
    default {
        Write-Host "❌ Agente desconocido: $Agent" -ForegroundColor Red
        Write-Host ""
        Write-Host "Uso:" -ForegroundColor Yellow
        Write-Host "  .\scripts\run_training.ps1 sac     # Entrena SAC" -ForegroundColor Gray
        Write-Host "  .\scripts\run_training.ps1 ppo     # Entrena PPO" -ForegroundColor Gray
        Write-Host "  .\scripts\run_training.ps1 a2c     # Entrena A2C" -ForegroundColor Gray
        Write-Host "  .\scripts\run_training.ps1 test    # Verifica ambiente" -ForegroundColor Gray
        Write-Host "  .\scripts\run_training.ps1 install # Instala dependencias" -ForegroundColor Gray
        exit 1
    }
}

Write-Host ""
Write-Host "✅ COMPLETADO" -ForegroundColor Green
