# Verificar y forzar Python 3.11
# ===============================

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "VERIFICAR PYTHON 3.11 EXACTAMENTE" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$python_version = python --version 2>&1
Write-Host "Versión actual: $python_version" -ForegroundColor Yellow

# Extraer versión
$version_match = $python_version -match "(\d+)\.(\d+)"
if ($version_match) {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]

    if ($major -eq 3 -and $minor -eq 11) {
        Write-Host "✓ Python 3.11 CORRECTO" -ForegroundColor Green
        Write-Host ""
        Write-Host "Puedes ejecutar: python -m scripts.run_a2c_only --config configs/default.yaml" -ForegroundColor Green
    }
    else {
        Write-Host "❌ ERROR: Tienes Python $major.$minor pero se requiere Python 3.11 EXACTAMENTE" -ForegroundColor Red
        Write-Host ""
        Write-Host "Opciones para solucionar:" -ForegroundColor Yellow
        Write-Host "1. Descargar Python 3.11 desde: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "2. Desinstalar Python 3.12, 3.13, etc desde 'Agregar o quitar programas'" -ForegroundColor Yellow
        Write-Host "3. Instalar Python 3.11 EXACTAMENTE" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "O usar venv con Python 3.11:" -ForegroundColor Yellow
        Write-Host "  python3.11 -m venv .venv" -ForegroundColor Yellow
        Write-Host "  .venv\Scripts\activate" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
}
else {
    Write-Host "❌ No se pudo detectar versión de Python" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Iniciando A2C Training..." -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

python -m scripts.run_a2c_only --config configs/default.yaml
