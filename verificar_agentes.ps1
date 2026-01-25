# ===============================================
# VERIFICAR AGENTES ANTES DE ENTRENAR
# ===============================================
# Autor: Proyecto Iquitos PV BESS EV
# Fecha: 2026-01-24
# ===============================================

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " VERIFICACION DE AGENTES - CONFIGURACIONES DE ENTRENAMIENTO" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Activar entorno virtual
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[OK] Activando entorno virtual..." -ForegroundColor Green
    & .venv\Scripts\Activate.ps1
}
else {
    Write-Host "[ERROR] No se encontro entorno virtual en .venv" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Ejecutar verificacion
Write-Host ""
Write-Host "[OK] Ejecutando verificacion..." -ForegroundColor Green
python scripts\verificar_agentes.py

# Pausar para ver resultado
Write-Host ""
Read-Host "Presiona Enter para salir"
