# Script: Instalar Python 3.11 y configurar venv para A2C
# Uso: .\INSTALAR_PYTHON_311.ps1

Write-Host "=================================================================================" -ForegroundColor Cyan
Write-Host "INSTALACION PYTHON 3.11 EXACTAMENTE" -ForegroundColor Cyan
Write-Host "=================================================================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Verificar si Python 3.11 esta disponible
Write-Host "[1/5] Verificando Python 3.11..." -ForegroundColor Yellow
$python311_exists = $false
try {
    $version = & python3.11 --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Python 3.11 ya esta instalado: $version" -ForegroundColor Green
        $python311_exists = $true
    }
}
catch {
    Write-Host "x Python 3.11 NO encontrado en PATH" -ForegroundColor Red
}

if (-not $python311_exists) {
    Write-Host ""
    Write-Host "=================================================================================" -ForegroundColor Red
    Write-Host "NECESITAS INSTALAR PYTHON 3.11 MANUALMENTE" -ForegroundColor Red
    Write-Host "=================================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Pasos:" -ForegroundColor Yellow
    Write-Host "1. Abre https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "2. Descarga Python 3.11 (la version mas reciente 3.11.x)" -ForegroundColor White
    Write-Host "3. Ejecuta el instalador" -ForegroundColor White
    Write-Host "4. IMPORTANTE: Marca la opcion 'Add Python 3.11 to PATH'" -ForegroundColor Red
    Write-Host "5. Instala en: C:\Python311" -ForegroundColor White
    Write-Host ""
    Write-Host "Despues de instalar, cierra y reabre PowerShell, luego ejecuta:" -ForegroundColor Cyan
    Write-Host "  .\INSTALAR_PYTHON_311.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Paso 2: Desinstalar versiones no compatibles (opcional, solo informativo)
Write-Host ""
Write-Host "[2/5] Versiones encontradas en PATH:" -ForegroundColor Yellow
$python_version = & python --version 2>&1
Write-Host "  Default python: $python_version" -ForegroundColor White

# Paso 3: Crear venv con Python 3.11
Write-Host ""
Write-Host "[3/5] Creando venv con Python 3.11..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "OK .venv ya existe, usando existente" -ForegroundColor Green
}
else {
    & python3.11 -m venv .venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK venv creado exitosamente" -ForegroundColor Green
    }
    else {
        Write-Host "x Error creando venv" -ForegroundColor Red
        exit 1
    }
}

# Paso 4: Activar venv
Write-Host ""
Write-Host "[4/5] Activando venv..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK venv activado" -ForegroundColor Green
}
else {
    Write-Host "x Error activando venv" -ForegroundColor Red
    exit 1
}

# Paso 5: Instalar dependencias
Write-Host ""
Write-Host "[5/5] Instalando dependencias (esto tarda ~5-10 minutos)..." -ForegroundColor Yellow
& pip install --upgrade pip setuptools wheel
& pip install -r requirements-training.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=================================================================================" -ForegroundColor Green
    Write-Host "OK CONFIGURACION COMPLETADA EXITOSAMENTE" -ForegroundColor Green
    Write-Host "=================================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Proximo paso - Ejecuta A2C con:" -ForegroundColor Cyan
    Write-Host "  python -m scripts.run_a2c_only --config configs/default.yaml" -ForegroundColor White
    Write-Host ""
}
else {
    Write-Host "x Error instalando dependencias" -ForegroundColor Red
    exit 1
}
