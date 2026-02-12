# ===========================================================================
# PowerShell Optimization & Cleanup Script
# Soluciona problemas de atascamiento en VS Code
# ===========================================================================

Write-Host "`n🔧 Iniciando optimización de PowerShell..." -ForegroundColor Cyan

# 1. MATAR PROCESOS PYTHON RESIDUALES
Write-Host "`n📛 Limpiando procesos residuales..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Milliseconds 500

# 2. LIMPIAR ARCHIVOS TEMPORALES PYTHON
Write-Host "🧹 Limpiando archivos temporales..." -ForegroundColor Yellow
$pythonCache = @(
    "$env:USERPROFILE\.vscode\extensions\*",
    "$env:TEMP\*",
    "$env:APPDATA\Python\*cache*"
)

foreach ($path in $pythonCache) {
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue -Verbose:$false
        } catch {
            # Silently continue if removing fails
        }
    }
}

# 3. CONFIGURAR VARIABLES DE ENTORNO
Write-Host "⚙️  Configurando variables de entorno..." -ForegroundColor Yellow
$env:PYTHONUNBUFFERED = 1
$env:PYTHONDONTWRITEBYTECODE = 1
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONWARNINGS = "ignore"

# 4. ACTIVAR VIRTUAL ENVIRONMENT
Write-Host "🐍 Activando virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".venv\Scripts\Activate.ps1"
}

# 5. MOSTRAR ESTADO FINAL
Write-Host "`n✅ OPTIMIZACIÓN COMPLETADA:" -ForegroundColor Green
Write-Host "   ✓ Procesos Python limpiados" -ForegroundColor Gray
Write-Host "   ✓ Caché removido" -ForegroundColor Gray
Write-Host "   ✓ Variables de entorno configuradas" -ForegroundColor Gray
Write-Host "   ✓ Virtual environment activado" -ForegroundColor Gray
Write-Host "`n🟢 PowerShell listo para uso" -ForegroundColor Green
Write-Host "   Ubicación: $(Get-Location)" -ForegroundColor Gray
Write-Host "   Procesos Python: $(Get-Process python -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count)" -ForegroundColor Gray
