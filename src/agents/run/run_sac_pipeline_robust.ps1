#Requires -Version 5.1
<#
================================================================================
SAC FULL PIPELINE - ROBUSTO CON VALIDACIÓN Y ERROR HANDLING
================================================================================
Descripción:
  - Dataset Construction (OE2 → CityLearn)
  - SAC Training (5 episodios = 43,800 timesteps)
  - Post-Training Analysis
  - Python 3.11 validación obligatoria

Uso:
  .\run_sac_pipeline_robust.ps1 -Episodes 5

Requirement:
  - Python 3.11 exactamente
  - Virtual environment .venv activado
  - Proyecto en d:\diseñopvbesscar

================================================================================
#>

param(
    [int]$Episodes = 5,
    [bool]$VerboseLogging = $true,
    [bool]$SkipDataset = $false
)

# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

$ProjectRoot = "d:\diseñopvbesscar"
$ConfigFile = "configs/default.yaml"
$LogDir = "logs/sac_pipeline"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = "$LogDir/pipeline_${Timestamp}.log"
$ErrorLogFile = "$LogDir/pipeline_errors_${Timestamp}.log"

# Colores
$ColorSuccess = "Green"
$ColorError = "Red"
$ColorWarning = "Yellow"
$ColorInfo = "Cyan"
$ColorDebug = "Gray"

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = $ColorInfo
    )

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"

    # Salida a consola
    Write-Host $LogMessage -ForegroundColor $Color

    # Salida a archivo
    Add-Content -Path $LogFile -Value $LogMessage -Force -ErrorAction SilentlyContinue
}

function Write-Success {
    param([string]$Message)
    Write-Log -Message $Message -Level "SUCCESS" -Color $ColorSuccess
}

function Write-Error-Log {
    param([string]$Message)
    Write-Log -Message $Message -Level "ERROR" -Color $ColorError
    Add-Content -Path $ErrorLogFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" -Force -ErrorAction SilentlyContinue
}

function Write-Warning-Log {
    param([string]$Message)
    Write-Log -Message $Message -Level "WARNING" -Color $ColorWarning
}

function Write-Debug-Log {
    param([string]$Message)
    if ($VerboseLogging) {
        Write-Log -Message $Message -Level "DEBUG" -Color $ColorDebug
    }
}

function Test-PythonVersion {
    Write-Log -Message "Validando Python 3.11..." -Level "CHECK"

    try {
        $PythonVersion = python --version 2>&1
        Write-Debug-Log -Message "Python detectado: $PythonVersion"

        if ($PythonVersion -match "3\.11") {
            Write-Success -Message "✓ Python 3.11 detectado: $PythonVersion"
            return $true
        } else {
            Write-Error-Log -Message "✗ Python incorrecto: $PythonVersion (requiere 3.11)"
            return $false
        }
    } catch {
        Write-Error-Log -Message "✗ Python no encontrado en PATH"
        return $false
    }
}

function Activate-VirtualEnv {
    Write-Log -Message "Activando virtual environment..." -Level "SETUP"

    $VenvPath = "$ProjectRoot\.venv\Scripts\Activate.ps1"
    if (-not (Test-Path $VenvPath)) {
        Write-Error-Log -Message "✗ Virtual env no encontrado en: $VenvPath"
        return $false
    }

    try {
        & $VenvPath
        Write-Success -Message "✓ Virtual environment activado"
        Write-Debug-Log -Message "Verificando pip..."
        pip --version | Out-Null
        Write-Success -Message "✓ pip disponible"
        return $true
    } catch {
        Write-Error-Log -Message "✗ Error activando virtual env: $_"
        return $false
    }
}

function Test-ProjectStructure {
    Write-Log -Message "Validando estructura del proyecto..." -Level "CHECK"

    $RequiredFiles = @(
        "configs/default.yaml",
        "src/iquitos_citylearn/oe3/simulate.py",
        "src/iquitos_citylearn/oe3/agents/sac.py"
    )

    $AllExist = $true
    foreach ($File in $RequiredFiles) {
        $FullPath = Join-Path $ProjectRoot $File
        if (Test-Path $FullPath) {
            Write-Debug-Log -Message "✓ Encontrado: $File"
        } else {
            Write-Warning-Log -Message "✗ NO encontrado: $File"
            $AllExist = $false
        }
    }

    if ($AllExist) {
        Write-Success -Message "✓ Estructura del proyecto OK"
    } else {
        Write-Error-Log -Message "✗ Archivos faltantes en proyecto"
    }

    return $AllExist
}

function Build-Dataset {
    Write-Log -Message "════════════════════════════════════════" -Level "STAGE"
    Write-Log -Message "STAGE 1: CONSTRUCCIÓN DE DATASET" -Level "STAGE" -Color $ColorInfo
    Write-Log -Message "════════════════════════════════════════" -Level "STAGE"

    if ($SkipDataset) {
        Write-Warning-Log -Message "⊘ Dataset building skipped (SkipDataset=$SkipDataset)"
        return $true
    }

    Write-Log -Message "Ejecutando: python -m scripts.run_oe3_build_dataset --config $ConfigFile" -Level "EXEC"

    try {
        $Output = & python -m scripts.run_oe3_build_dataset --config $ConfigFile 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Success -Message "✓ Dataset building completado exitosamente"
            Write-Debug-Log -Message "Dataset output: $Output"
            return $true
        } else {
            Write-Error-Log -Message "✗ Dataset building falló (exit code $LASTEXITCODE)"
            Write-Error-Log -Message "Output: $Output"
            return $false
        }
    } catch {
        Write-Error-Log -Message "✗ Excepción en dataset building: $_"
        return $false
    }
}

function Train-SAC {
    Write-Log -Message "════════════════════════════════════════" -Level "STAGE"
    Write-Log -Message "STAGE 2: ENTRENAMIENTO SAC" -Level "STAGE" -Color $ColorInfo
    Write-Log -Message "════════════════════════════════════════" -Level "STAGE"
    Write-Log -Message "Episodios: $Episodes" -Level "CONFIG"
    Write-Log -Message "Total timesteps: $($Episodes * 8760)" -Level "CONFIG"

    $Cmd = "python -m scripts.run_oe3_simulate --config $ConfigFile --agent sac --sac-episodes $Episodes"
    Write-Log -Message "Ejecutando: $Cmd" -Level "EXEC"

    try {
        # Capturar output con stream de tiempo real
        $StartTime = Get-Date
        $Output = & python -m scripts.run_oe3_simulate --config $ConfigFile --agent sac --sac-episodes $Episodes 2>&1
        $EndTime = Get-Date
        $Duration = $EndTime - $StartTime

        if ($LASTEXITCODE -eq 0) {
            Write-Success -Message "✓ SAC training completado en $($Duration.TotalMinutes | [math]::Round(2)) minutos"
            Write-Debug-Log -Message "Training output (últimas 20 líneas):"
            $Output | Select-Object -Last 20 | ForEach-Object { Write-Debug-Log -Message $_}
            return $true
        } else {
            Write-Error-Log -Message "✗ SAC training falló (exit code $LASTEXITCODE)"
            Write-Error-Log -Message "Training output (últimas 30 líneas):"
            $Output | Select-Object -Last 30 | ForEach-Object { Write-Error-Log -Message $_}
            return $false
        }
    } catch {
        Write-Error-Log -Message "✗ Excepción en SAC training: $_"
        return $false
    }
}

function Analyze-Results {
    Write-Log -Message "════════════════════════════════════════" -Level "STAGE"
    Write-Log -Message "STAGE 3: ANÁLISIS POST-ENTRENAMIENTO" -Level "STAGE" -Color $ColorInfo
    Write-Log -Message "════════════════════════════════════════" -Level "STAGE"

    Write-Log -Message "Ejecutando: python -m scripts.run_oe3_co2_table --config $ConfigFile" -Level "EXEC"

    try {
        $Output = & python -m scripts.run_oe3_co2_table --config $ConfigFile 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Success -Message "✓ Análisis completado exitosamente"
            Write-Debug-Log -Message "Analysis output: $Output"
            return $true
        } else {
            Write-Warning-Log -Message "⚠ Análisis retornó código no-cero (no es crítico)"
            Write-Debug-Log -Message "Analysis output: $Output"
            return $true  # No es crítico
        }
    } catch {
        Write-Warning-Log -Message "⚠ Excepción en análisis (no es crítico): $_"
        return $true  # No es crítico
    }
}

function Show-Results {
    Write-Log -Message "════════════════════════════════════════" -Level "RESULTS"
    Write-Log -Message "RESULTADOS DEL PIPELINE" -Level "RESULTS" -Color $ColorSuccess
    Write-Log -Message "════════════════════════════════════════" -Level "RESULTS"

    $OutputDir = Join-Path $ProjectRoot "outputs/oe3_simulations/sac"
    $CheckpointDir = Join-Path $ProjectRoot "checkpoints/sac"

    Write-Log -Message "📁 Salida:" -Level "RESULTS"
    Write-Log -Message "   Directorio: $OutputDir" -Level "RESULTS"

    if (Test-Path $OutputDir) {
        $Files = Get-ChildItem $OutputDir -File
        foreach ($File in $Files) {
            $SizeMB = [math]::Round($File.Length / 1MB, 2)
            Write-Log -Message "   - $($File.Name) ($SizeMB MB)" -Level "RESULTS"
        }
    }

    Write-Log -Message "📁 Checkpoints:" -Level "RESULTS"
    Write-Log -Message "   Directorio: $CheckpointDir" -Level "RESULTS"

    if (Test-Path $CheckpointDir) {
        $Checkpoints = Get-ChildItem $CheckpointDir -File -Filter "*.zip"
        foreach ($CP in $Checkpoints) {
            $SizeMB = [math]::Round($CP.Length / 1MB, 2)
            Write-Log -Message "   - $($CP.Name) ($SizeMB MB)" -Level "RESULTS"
        }
    }

    Write-Log -Message "📋 Logs:" -Level "RESULTS"
    Write-Log -Message "   - $LogFile" -Level "RESULTS"
    Write-Log -Message "   - $ErrorLogFile" -Level "RESULTS"
}

# ============================================================================
# MAIN PIPELINE EXECUTION
# ============================================================================

function Main {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $ColorInfo
    Write-Host "║        SAC FULL PIPELINE - Python 3.11 Robusto            ║" -ForegroundColor $ColorInfo
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $ColorInfo
    Write-Host ""

    # Crear directorio de logs
    New-Item -ItemType Directory -Path $LogDir -Force -ErrorAction SilentlyContinue | Out-Null

    Write-Success -Message "Log principal: $LogFile"
    Write-Success -Message "Log de errores: $ErrorLogFile"
    Write-Log -Message "" -Level ""

    # VALIDACIÓN PREVIA
    Write-Log -Message "┌─ VALIDACIONES PREVIAS ─────────────────────────────────┐" -Level "SECTION"

    if (-not (Test-PythonVersion)) {
        Write-Error-Log -Message "PIPELINE ABORTADO: Python 3.11 no disponible"
        exit 1
    }

    Set-Location $ProjectRoot
    Write-Log -Message "✓ Working directory: $ProjectRoot" -Level "CHECK"

    if (-not (Test-ProjectStructure)) {
        Write-Error-Log -Message "PIPELINE ABORTADO: Estructura del proyecto incompleta"
        exit 1
    }

    if (-not (Activate-VirtualEnv)) {
        Write-Error-Log -Message "PIPELINE ABORTADO: No se pudo activar virtual environment"
        exit 1
    }

    Write-Log -Message "└────────────────────────────────────────────────────────┘" -Level "SECTION"
    Write-Log -Message "" -Level ""

    # EXECUTION STAGES
    $StartTime = Get-Date
    $Success = $true

    # Stage 1: Dataset
    if (-not (Build-Dataset)) {
        Write-Error-Log -Message "PIPELINE ABORTADO EN STAGE 1: Dataset construction failed"
        $Success = $false
    }

    Write-Log -Message "" -Level ""

    # Stage 2: SAC Training (CRITICAL)
    if ($Success -and -not (Train-SAC)) {
        Write-Error-Log -Message "PIPELINE ABORTADO EN STAGE 2: SAC training failed"
        $Success = $false
    }

    Write-Log -Message "" -Level ""

    # Stage 3: Analysis (NON-CRITICAL)
    if ($Success) {
        Analyze-Results | Out-Null
    }

    # RESULTADOS FINALES
    Write-Log -Message "" -Level ""
    $EndTime = Get-Date
    $TotalDuration = $EndTime - $StartTime

    if ($Success) {
        Write-Log -Message "╔════════════════════════════════════════════════════════════╗" -Level "SUCCESS" -Color $ColorSuccess
        Write-Log -Message "║          PIPELINE COMPLETADO EXITOSAMENTE ✓              ║" -Level "SUCCESS" -Color $ColorSuccess
        Write-Log -Message "╚════════════════════════════════════════════════════════════╝" -Level "SUCCESS" -Color $ColorSuccess

        Show-Results

        Write-Log -Message "" -Level ""
        Write-Log -Message "⏱️  Duración total: $($TotalDuration.TotalMinutes | [math]::Round(2)) minutos" -Level "SUCCESS" -Color $ColorSuccess

        exit 0
    } else {
        Write-Log -Message "╔════════════════════════════════════════════════════════════╗" -Level "ERROR" -Color $ColorError
        Write-Log -Message "║          PIPELINE FALLÓ - Revisar logs arriba            ║" -Level "ERROR" -Color $ColorError
        Write-Log -Message "╚════════════════════════════════════════════════════════════╝" -Level "ERROR" -Color $ColorError

        Write-Log -Message "" -Level ""
        Write-Log -Message "📋 Detalles en: $ErrorLogFile" -Level "ERROR" -Color $ColorError

        exit 1
    }
}

# ============================================================================
# EXECUTION
# ============================================================================

Main
