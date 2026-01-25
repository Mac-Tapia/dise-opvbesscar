#!/usr/bin/env powershell
# Script para limpiar Python 3.13 y asegurar Python 3.11

Write-Host "🔧 CONFIGURACIÓN ENTORNO - PYTHON 3.11 SOLO" -ForegroundColor Cyan
Write-Host ""

# 1. Detectar instalaciones de Python
Write-Host "1. Buscando instalaciones de Python..." -ForegroundColor Yellow

$python_paths = @()

# Buscar en Program Files
$pf = "C:\Program Files\Python*", "C:\Program Files (x86)\Python*"
foreach ($p in $pf) {
    Get-ChildItem $p -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $python_paths += $_
    }
}

Write-Host "   Instalaciones encontradas:"
$python_paths | ForEach-Object {
    $version_file = "$_\python.exe"
    if (Test-Path $version_file) {
        $version = & $version_file --version 2>&1
        Write-Host "   • $_ ($version)" -ForegroundColor White
    }
}

# 2. Verificar PATH
Write-Host ""
Write-Host "2. Verificando PATH:" -ForegroundColor Yellow
$env:PATH -split ";" | Where-Object { $_ -match "python" } -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "   • $_" -ForegroundColor White
}

# 3. Verificar venv del proyecto
Write-Host ""
Write-Host "3. Verificando venv del proyecto:" -ForegroundColor Yellow
$venv_python = "D:\diseñopvbesscar\.venv\Scripts\python.exe"
if (Test-Path $venv_python) {
    $version = & $venv_python --version 2>&1
    Write-Host "   ✅ Venv encontrado: $version" -ForegroundColor Green
}
else {
    Write-Host "   ❌ Venv NO encontrado" -ForegroundColor Red
}

# 4. Instrucciones para limpiar
Write-Host ""
Write-Host "4. Para eliminar Python 3.13:" -ForegroundColor Yellow
Write-Host "   Opción A - Desinstalar desde Windows:" -ForegroundColor White
Write-Host "     • Configuración > Aplicaciones > Aplicaciones instaladas" -ForegroundColor Cyan
Write-Host "     • Buscar 'Python 3.13'" -ForegroundColor Cyan
Write-Host "     • Desinstalar" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Opción B - Línea de comandos (admin):" -ForegroundColor White
Write-Host "     • wmic product where name='Python 3.13*' call uninstall" -ForegroundColor Cyan
Write-Host ""

# 5. Recrear venv si es necesario
Write-Host "5. Para recrear venv con Python 3.11:" -ForegroundColor Yellow
Write-Host "   Pasos:" -ForegroundColor White
Write-Host "   1. python -m venv d:\diseñopvbesscar\.venv --upgrade-deps" -ForegroundColor Cyan
Write-Host "   2. .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   3. pip install -r requirements.txt" -ForegroundColor Cyan
Write-Host ""

Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "⚠️  IMPORTANTE: El proyecto requiere PYTHON 3.11" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
