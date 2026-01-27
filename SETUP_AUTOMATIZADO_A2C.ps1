# =========================================================================
# AUTOMATIZADOR COMPLETO - EJECUTA ESTO DESPUES DE INSTALAR PYTHON 3.11
# =========================================================================
#
# ANTES DE EJECUTAR ESTE SCRIPT:
#   1. Descarga Python 3.11: https://www.python.org/downloads/
#   2. Instala con MARCA: "Add python.exe to PATH"
#   3. Cierra y reabre PowerShell COMPLETAMENTE
#   4. Verifica: python3.11 --version (debe mostrar Python 3.11.x)
#   5. LUEGO ejecuta este script:
#      .\SETUP_AUTOMATIZADO_A2C.ps1
#
# =========================================================================

Write-Host "`n" -ForegroundColor White
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "SETUP AUTOMATIZADO - PYTHON 3.11 -> A2C LISTO" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "`n" -ForegroundColor White

# PASO 1: Verificar Python 3.11
Write-Host "[1/4] Verificando Python 3.11..." -ForegroundColor Yellow
$python311_check = & python3.11 --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python 3.11 NO ENCONTRADO en PATH" -ForegroundColor Red
    Write-Host "Debes instalar Python 3.11 primero desde:" -ForegroundColor Red
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "`nPasos:" -ForegroundColor Red
    Write-Host "  1. Descarga Python 3.11" -ForegroundColor White
    Write-Host "  2. Instala con MARCA 'Add python.exe to PATH'" -ForegroundColor White
    Write-Host "  3. Cierra y reabre PowerShell" -ForegroundColor White
    Write-Host "  4. Verifica: python3.11 --version" -ForegroundColor White
    Write-Host "  5. Ejecuta de nuevo este script" -ForegroundColor White
    Write-Host "`n" -ForegroundColor White
    exit 1
}
Write-Host "OK: $python311_check" -ForegroundColor Green

# PASO 2: Crear venv
Write-Host "`n[2/4] Creando venv con Python 3.11..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "OK: .venv ya existe" -ForegroundColor Green
}
else {
    & python3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: No se pudo crear venv" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK: venv creado" -ForegroundColor Green
}

# PASO 3: Activar venv e instalar dependencias
Write-Host "`n[3/4] Activando venv e instalando dependencias..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: No se pudo activar venv" -ForegroundColor Red
    exit 1
}
Write-Host "OK: venv activado" -ForegroundColor Green

Write-Host "OK: Instalando dependencias (5 minutos)..." -ForegroundColor Green
& pip install --upgrade pip setuptools wheel 2>&1 | Out-Null
& pip install -r requirements-training.txt 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: No se pudieron instalar dependencias" -ForegroundColor Red
    exit 1
}
Write-Host "OK: Dependencias instaladas" -ForegroundColor Green

# PASO 4: Verificacion final
Write-Host "`n[4/4] Verificacion final..." -ForegroundColor Yellow
$py_version = & python --version 2>&1
Write-Host "OK: $py_version" -ForegroundColor Green

# EXITO
Write-Host "`n" -ForegroundColor White
Write-Host "=========================================================================" -ForegroundColor Green
Write-Host "OK: LISTO PARA ENTRENAR A2C" -ForegroundColor Green
Write-Host "=========================================================================" -ForegroundColor Green
Write-Host "`nEjecutar A2C con:" -ForegroundColor Cyan
Write-Host "  python -m scripts.run_a2c_only --config configs/default.yaml" -ForegroundColor White
Write-Host "`n" -ForegroundColor White
