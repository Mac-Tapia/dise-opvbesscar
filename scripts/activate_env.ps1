# ============================================================================
# ACTIVAR AMBIENTE .venv AUTOMÁTICAMENTE
# ============================================================================
# Uso: & scripts/activate_env.ps1

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPath = Join-Path $ProjectRoot ".venv"

if (-not (Test-Path $VenvPath)) {
    Write-Host "❌ AMBIENTE NO ENCONTRADO: $VenvPath" -ForegroundColor Red
    Write-Host "Por favor crea el ambiente con: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Activar .venv
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
    Write-Host "❌ SCRIPT DE ACTIVACIÓN NO ENCONTRADO: $ActivateScript" -ForegroundColor Red
    exit 1
}

# Ejecutar activación
& $ActivateScript

# Verificar que estamos en .venv
$PyExe = (python -c "import sys; print(sys.executable)")
if ($PyExe -notlike "*$VenvPath*") {
    Write-Host "❌ ERROR: No se activó correctamente .venv" -ForegroundColor Red
    Write-Host "   Python ejecutable: $PyExe" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ AMBIENTE ACTIVADO: .venv" -ForegroundColor Green
Write-Host "   Python: $PyExe" -ForegroundColor Gray
Write-Host "   Versi​ón: $(python --version)" -ForegroundColor Gray
