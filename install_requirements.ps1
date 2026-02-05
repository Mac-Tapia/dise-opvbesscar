# Script de instalación individual de requisitos
# Python 3.11 - Iquitos PV-BESS-CAR Project
# ==============================================================================

Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  INSTALACIÓN DE REQUISITOS - PYTHON 3.11                                  ║" -ForegroundColor Cyan
Write-Host "║  Proyecto: diseñopvbesscar                                                ║" -ForegroundColor Cyan
Write-Host "║  Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')                                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Verificar que el entorno virtual está activado
$venvCheck = python --version 2>&1
Write-Host "✓ Python detectado: $venvCheck" -ForegroundColor Green

# Crear log file
$logFile = "installation_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
Write-Host "📝 Registrando en: $logFile" -ForegroundColor Yellow
Write-Host ""

# Función para instalar paquete individual
function Install-Package {
    param(
        [string]$PackageName,
        [int]$Index,
        [int]$Total
    )

    Write-Host "[$Index/$Total] Instalando: $PackageName" -ForegroundColor Cyan

    # Ejecutar pip install
    $output = pip install $PackageName 2>&1
    $output | Out-File -FilePath $logFile -Append -Encoding UTF8

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $PackageName instalado correctamente" -ForegroundColor Green
    }
    else {
Write-Host ""

Install-Package "numpy==1.26.4" 1 3
Install-Package "pandas==2.3.3" 2 3
Install-Package "scipy==1.17.0" 3 3

# ============================================================================
# REINFORCEMENT LEARNING
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  REINFORCEMENT LEARNING                                                    ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

Install-Package "gymnasium==0.29.1" 1 2
Install-Package "Farama-Notifications==0.0.4" 2 2

# ============================================================================
# DEEP LEARNING & NUMERICAL COMPUTING
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  DEEP LEARNING & NUMERICAL COMPUTING                                       ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

Install-Package "torch==2.10.0" 1 2
Install-Package "torchvision==0.15.2" 2 2

# ============================================================================
# STABLE BASELINES 3 (después de torch)
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  STABLE BASELINES 3 (RL Framework)                                         ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

Install-Package "stable_baselines3==2.7.1" 1 1

# ============================================================================
# CONFIGURATION & UTILITIES
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  CONFIGURATION & UTILITIES                                                 ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

Install-Package "PyYAML==6.0.3" 1 4
Install-Package "python_dotenv==1.2.1" 2 4
Install-Package "pydantic==2.12.5" 3 4
Install-Package "pydantic_core==2.41.5" 4 4

# ============================================================================
# VISUALIZATION & ANALYSIS
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  VISUALIZATION & ANALYSIS                                                  ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

Install-Package "matplotlib==3.10.8" 1 7
Install-Package "seaborn==0.13.2" 2 7
Install-Package "pillow==12.1.0" 3 7
Install-Package "contourpy==1.3.3" 4 7
Install-Package "cycler==0.12.1" 5 7
Install-Package "fonttools==4.61.1" 6 7
Install-Package "kiwisolver==1.4.9" 7 7

# ============================================================================
# TESTING & LINTING
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  TESTING & LINTING                                                         ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

Install-Package "pytest==8.3.4" 1 2
Install-Package "black==24.10.0" 2 2

# ============================================================================
# SOLAR & CITYLEARN
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  SOLAR & CITYLEARN                                                         ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

Install-Package "pvlib==0.10.4" 1 2
Install-Package "requests==2.32.3" 2 2

# ============================================================================
# RESUMEN FINAL
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  RESUMEN DE INSTALACIÓN                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host ""
Write-Host "📋 Verificando instalación de todos los paquetes..." -ForegroundColor Yellow
$pipList = pip list 2>&1
$pipList | Out-File -FilePath $logFile -Append -Encoding UTF8
$pipList | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "✅ INSTALACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "📝 Log guardado en: $logFile" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Cyan
Write-Host "1. Verificar que todos los paquetes se instalaron correctamente"
Write-Host "2. Ejecutar: python -c 'import torch; print(torch.__version__)'"
Write-Host "3. Ejecutar: python -c 'import stable_baselines3; print(stable_baselines3.__version__)'"
Write-Host "4. Ejecutar: python run_solar_generation_hourly.py"
Write-Host ""
