#!/usr/bin/env pwsh
<#
.DESCRIPTION
Setup e instalación forzando Python 3.11
#>

param(
    [switch]$NoVenv = $false,
    [switch]$SkipInstall = $false
)

Write-Host "`n" + "="*80
Write-Host "🔧 SETUP A2C - PYTHON 3.11 REQUERIDO" -ForegroundColor Green
Write-Host "="*80 + "`n"

# 1. Detectar Python 3.11
Write-Host "[1/4] Buscando Python 3.11..." -ForegroundColor Cyan

$python311 = $null

# Buscar en PATH
$python311 = & {
    try {
        $v = python3.11 --version 2>&1
        if ($v -match "3.11") {
            return "python3.11"
        }
    }
    catch {}

    try {
        $v = py -3.11 --version 2>&1
        if ($v -match "3.11") {
            return "py -3.11"
        }
    }
    catch {}

    return $null
}

if (!$python311) {
    Write-Host "❌ Python 3.11 no encontrado" -ForegroundColor Red
    Write-Host "`n⚠️  Instala Python 3.11 desde:"
    Write-Host "   https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "   O usa: choco install python311" -ForegroundColor Yellow
    Write-Host "="*80 + "`n"
    exit 1
}

Write-Host "✓ Python 3.11 encontrado: $python311" -ForegroundColor Green

# 2. Crear venv si no existe
if ($NoVenv) {
    Write-Host "[2/4] Saltando venv (--NoVenv)" -ForegroundColor Yellow
}
else {
    Write-Host "[2/4] Verificando/creando virtual environment..." -ForegroundColor Cyan

    if (!(Test-Path ".venv")) {
        Write-Host "   Creando venv con Python 3.11..."
        & $python311 -m venv .venv
        Write-Host "   ✓ venv creado" -ForegroundColor Green
    }
    else {
        Write-Host "   ✓ venv existe" -ForegroundColor Green
    }

    # Activar venv
    Write-Host "   Activando venv..."
    & ".\.venv\Scripts\Activate.ps1"
    Write-Host "   ✓ venv activo" -ForegroundColor Green
}

# 3. Instalar paquetes
if ($SkipInstall) {
    Write-Host "[3/4] Saltando instalación (--SkipInstall)" -ForegroundColor Yellow
}
else {
    Write-Host "[3/4] Instalando paquetes requeridos..." -ForegroundColor Cyan

    & python -m pip install --upgrade pip setuptools wheel
    & python -m pip install -r requirements-training.txt

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Paquetes instalados" -ForegroundColor Green
    }
    else {
        Write-Host "   ❌ Error instalando paquetes" -ForegroundColor Red
        exit 1
    }
}

# 4. Verificar
Write-Host "[4/4] Verificando setup..." -ForegroundColor Cyan

$pythonVersion = & python --version
Write-Host "   Python: $pythonVersion" -ForegroundColor Green

try {
    $_ = & python -c "import gymnasium, numpy, pandas, stable_baselines3, torch; print('OK')"
    Write-Host "   Paquetes: OK" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ Error importando paquetes" -ForegroundColor Red
    exit 1
}

# Final
Write-Host "`n" + "="*80
Write-Host "✅ SETUP COMPLETADO" -ForegroundColor Green
Write-Host "="*80
Write-Host "`nAhora puedes ejecutar:`n" -ForegroundColor White
Write-Host "   python train_a2c_local_data_only.py" -ForegroundColor Yellow
Write-Host "`n" + "="*80 + "`n"
