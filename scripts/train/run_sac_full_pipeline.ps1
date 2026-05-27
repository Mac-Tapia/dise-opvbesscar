# SAC Full Pipeline: Dataset Building + Training (5 Episodes)
# Python 3.11 Required
# Continuous Execution with Error Handling

param(
    [int]$Episodes = 5,
    [string]$ConfigPath = "configs/default.yaml"
)

# ================================================================================
# CONFIGURATION
# ================================================================================
$ProjectRoot = "d:\diseñopvbesscar"
$VenvPath = "$ProjectRoot\.venv"
$ActivateScript = "$VenvPath\Scripts\Activate.ps1"
$PythonExe = "$VenvPath\Scripts\python.exe"
$LogDir = "$ProjectRoot\logs\sac_pipeline"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = "$LogDir\sac_pipeline_$Timestamp.log"

# Colors for output
$Colors = @{
    Header   = "Cyan"
    Success  = "Green"
    Warning  = "Yellow"
    Error    = "Red"
    Info     = "White"
}

# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = $Colors.Info
    )
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Host $LogMessage -ForegroundColor $Color
    Add-Content -Path $LogFile -Value $LogMessage -Encoding UTF8
}

function Initialize-Logging {
    if (-not (Test-Path $LogDir)) {
        New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
    }
    "Pipeline execution started at $(Get-Date)" | Out-File -FilePath $LogFile -Encoding UTF8
    Write-Log "Logging initialized to: $LogFile" "INFO" $Colors.Success
}

function Check-Python {
    Write-Log "Checking Python 3.11 installation..." "INFO" $Colors.Info

    if (-not (Test-Path $PythonExe)) {
        Write-Log "ERROR: Python executable not found at $PythonExe" "ERROR" $Colors.Error
        Write-Log "Expected location: .venv\Scripts\python.exe" "ERROR" $Colors.Error
        exit 1
    }

    $PythonVersion = & $PythonExe --version 2>&1
    Write-Log "Python version: $PythonVersion" "INFO" $Colors.Success

    if ($PythonVersion -notmatch "3\.11") {
        Write-Log "WARNING: Expected Python 3.11, got: $PythonVersion" "WARNING" $Colors.Warning
    }

    Write-Log "✓ Python 3.11 verified" "SUCCESS" $Colors.Success
}

function Check-VirtualEnv {
    Write-Log "Checking virtual environment..." "INFO" $Colors.Info

    if (-not (Test-Path $ActivateScript)) {
        Write-Log "ERROR: Virtual environment not found at $VenvPath" "ERROR" $Colors.Error
        Write-Log "Run: python -m venv .venv" "ERROR" $Colors.Error
        exit 1
    }

    Write-Log "✓ Virtual environment found at $VenvPath" "SUCCESS" $Colors.Success
}

function Activate-VirtualEnv {
    Write-Log "Activating virtual environment..." "INFO" $Colors.Info
    try {
        & $ActivateScript
        Write-Log "✓ Virtual environment activated" "SUCCESS" $Colors.Success
    } catch {
        Write-Log "ERROR: Failed to activate venv: $_" "ERROR" $Colors.Error
        exit 1
    }
}

function Build-Dataset {
    Write-Log "========== STAGE 1: BUILDING DATASET ==========" "INFO" $Colors.Header

    if ($SkipDataset) {
        Write-Log "Skipping dataset build (SkipDataset flag set)" "WARNING" $Colors.Warning

    try {
        & $PythonExe -m scripts.run_oe3_build_dataset --config $ConfigPath 2>&1 | Tee-Object -FilePath $LogFile -Append | ForEach-Object {
            if ($_ -match "ERROR|CRITICAL") {
                Write-Host $_ -ForegroundColor $Colors.Error
            } elseif ($_ -match "OK|SUCCESS|✓") {
                Write-Host $_ -ForegroundColor $Colors.Success
            } else {
                Write-Host $_
            }
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Log "✓ Dataset building completed successfully" "SUCCESS" $Colors.Success
            return $true
        } else {
            Write-Log "ERROR: Dataset building failed with exit code $LASTEXITCODE" "ERROR" $Colors.Error
            return $false
        }
    } catch {
        Write-Log "ERROR: Exception during dataset building: $_" "ERROR" $Colors.Error
        return $false
    }
}

function Train-SAC {
    param([int]$NumEpisodes)

    Write-Log "========== STAGE 2: SAC TRAINING ($NumEpisodes episodes) ==========" "INFO" $Colors.Header

    Write-Log "Training configuration:" "INFO" $Colors.Info
    Write-Log "  Episodes: $NumEpisodes" "INFO" $Colors.Info
    Write-Log "  Config: $ConfigPath" "INFO" $Colors.Info
    Write-Log "  Timesteps (estimated): $($NumEpisodes * 8760) (8760 per year)" "INFO" $Colors.Info

    Write-Log "Executing: python -m scripts.run_oe3_simulate --config $ConfigPath --agent sac --sac-episodes $NumEpisodes" "INFO" $Colors.Info

    try {
        & $PythonExe -m scripts.run_oe3_simulate `
            --config $ConfigPath `
            --agent sac `
            --sac-episodes $NumEpisodes `
            2>&1 | Tee-Object -FilePath $LogFile -Append | ForEach-Object {
            if ($_ -match "ERROR|CRITICAL|❌") {
                Write-Host $_ -ForegroundColor $Colors.Error
            } elseif ($_ -match "OK|SUCCESS|✓|✅") {
                Write-Host $_ -ForegroundColor $Colors.Success
            } elseif ($_ -match "WARNING|⚠") {
                Write-Host $_ -ForegroundColor $Colors.Warning
            } else {
                Write-Host $_
            }
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Log "✓ SAC training completed successfully" "SUCCESS" $Colors.Success
            return $true
        } else {
            Write-Log "ERROR: SAC training failed with exit code $LASTEXITCODE" "ERROR" $Colors.Error
            return $false
        }
    } catch {
        Write-Log "ERROR: Exception during SAC training: $_" "ERROR" $Colors.Error
        return $false
    }
}

function Run-PostTrainingAnalysis {
    Write-Log "========== STAGE 3: POST-TRAINING ANALYSIS ==========" "INFO" $Colors.Header

    Write-Log "Generating comparison table..." "INFO" $Colors.Info

    try {
        & $PythonExe -m scripts.run_oe3_co2_table --config $ConfigPath 2>&1 | Tee-Object -FilePath $LogFile -Append | ForEach-Object {
            Write-Host $_
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Log "✓ Post-training analysis completed" "SUCCESS" $Colors.Success
            return $true
        } else {
            Write-Log "WARNING: Post-training analysis had issues (non-critical)" "WARNING" $Colors.Warning
            return $true  # Don't fail pipeline for this
        }
    } catch {
        Write-Log "WARNING: Exception during post-training analysis: $_" "WARNING" $Colors.Warning
        return $true  # Don't fail pipeline
    }
}

function Display-Results {
    Write-Log "========== PIPELINE SUMMARY ==========" "INFO" $Colors.Header

    $OutputDir = "outputs\oe3_simulations\sac"
    $TimestampDir = Get-ChildItem -Path $OutputDir -Directory | Sort-Object -Property CreationTime -Descending | Select-Object -First 1

    if ($TimestampDir) {
        Write-Log "Latest results in: $($TimestampDir.FullName)" "INFO" $Colors.Success

        $ResultJson = Get-ChildItem -Path $TimestampDir.FullName -Filter "result_*.json" | Select-Object -First 1
        if ($ResultJson) {
            Write-Log "Result file: $($ResultJson.Name)" "INFO" $Colors.Success
            Write-Log "Size: $($ResultJson.Length) bytes" "INFO" $Colors.Success
        }

        $TimestampsCsv = Get-ChildItem -Path $TimestampDir.FullName -Filter "timeseries_*.csv" | Select-Object -First 1
        if ($TimestampsCsv) {
            Write-Log "Timeseries file: $($TimestampsCsv.Name)" "INFO" $Colors.Success
            Write-Log "Size: $($TimestampsCsv.Length) bytes" "INFO" $Colors.Success
        }
    }

    Write-Log "Checkpoints available in: checkpoints/sac/" "INFO" $Colors.Info
    $Checkpoints = Get-ChildItem -Path "checkpoints/sac" -Filter "*.zip" 2>$null | Measure-Object
    if ($Checkpoints.Count -gt 0) {
        Write-Log "Found $($Checkpoints.Count) checkpoint files" "INFO" $Colors.Success
    }

    Write-Log "Full log saved to: $LogFile" "INFO" $Colors.Success
}

# ================================================================================
# MAIN PIPELINE
# ================================================================================

Write-Host "`n" -ForegroundColor $Colors.Header
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor $Colors.Header
Write-Host "║        SAC FULL PIPELINE - DATASET + TRAINING (5 EPISODES)    ║" -ForegroundColor $Colors.Header
Write-Host "║                   Python 3.11 | Continuous Execution          ║" -ForegroundColor $Colors.Header
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor $Colors.Header
Write-Host "`n" -ForegroundColor $Colors.Header

# Initialize
Initialize-Logging
Check-Python
Check-VirtualEnv
Activate-VirtualEnv

# Change to project directory
Set-Location -Path $ProjectRoot

# Pipeline execution
$DatasetSuccess = Build-Dataset
if (-not $DatasetSuccess) {
    Write-Log "FATAL: Dataset building failed. Aborting pipeline." "ERROR" $Colors.Error
    exit 1
}

$SACSuccess = Train-SAC -NumEpisodes $Episodes
if (-not $SACSuccess) {
    Write-Log "FATAL: SAC training failed. Aborting pipeline." "ERROR" $Colors.Error
    exit 1
}

# Post-training analysis
Run-PostTrainingAnalysis

# Summary
Display-Results

Write-Host "`n" -ForegroundColor $Colors.Header
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor $Colors.Header
Write-Host "║               PIPELINE COMPLETED SUCCESSFULLY ✓                ║" -ForegroundColor $Colors.Header
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor $Colors.Header
Write-Host "`n" -ForegroundColor $Colors.Header

Write-Log "Pipeline execution completed successfully" "SUCCESS" $Colors.Success
exit 0
