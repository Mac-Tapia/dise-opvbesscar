#!/usr/bin/env pwsh
# launch_chain_fresh.ps1 -- Entrena SAC -> PPO -> A2C en cadena desde cero
# Lanzar desde: d:\diseñopvbesscar\
# Uso: pwsh -File scripts\train\launch_chain_fresh.ps1

$ErrorActionPreference = "Stop"
$ROOT = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $ROOT

$PYTHON = "$ROOT\.venv\Scripts\python.exe"
$LOG_DIR = "$ROOT\outputs\training_chain"
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$LOG_DIR\chain_$timestamp.log"

function Write-Log {
    param([string]$msg)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Write-Log "============================================================"
Write-Log "CADENA DE ENTRENAMIENTO: SAC -> PPO -> A2C (desde cero)"
Write-Log "============================================================"
Write-Log "Python: $PYTHON"
Write-Log "Log: $logFile"
Write-Log ""

# ─── 1. SAC ───────────────────────────────────────────────────────────────
Write-Log ">>> INICIANDO SAC (50 episodios = 438,000 steps)"
$t0 = Get-Date
& $PYTHON scripts\train\train_sac_citylearn.py 2>&1 | Tee-Object -Append -FilePath $logFile
$sacExit = $LASTEXITCODE
$elapsed = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
Write-Log "<<< SAC finalizado. Exit=$sacExit | Tiempo: ${elapsed} min"
Write-Log ""

if ($sacExit -ne 0) {
    Write-Log "[ERROR] SAC terminó con error ($sacExit). Abortando cadena."
    Read-Host "Presiona ENTER para cerrar"
    exit $sacExit
}

# ─── 2. PPO ───────────────────────────────────────────────────────────────
Write-Log ">>> INICIANDO PPO (50 episodios = 438,000 steps)"
$t0 = Get-Date
& $PYTHON scripts\train\train_ppo_citylearn.py 2>&1 | Tee-Object -Append -FilePath $logFile
$ppoExit = $LASTEXITCODE
$elapsed = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
Write-Log "<<< PPO finalizado. Exit=$ppoExit | Tiempo: ${elapsed} min"
Write-Log ""

if ($ppoExit -ne 0) {
    Write-Log "[ERROR] PPO terminó con error ($ppoExit). Abortando cadena."
    Read-Host "Presiona ENTER para cerrar"
    exit $ppoExit
}

# ─── 3. A2C ───────────────────────────────────────────────────────────────
Write-Log ">>> INICIANDO A2C (50 episodios = 438,000 steps)"
$t0 = Get-Date
& $PYTHON scripts\train\train_a2c_citylearn.py 2>&1 | Tee-Object -Append -FilePath $logFile
$a2cExit = $LASTEXITCODE
$elapsed = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
Write-Log "<<< A2C finalizado. Exit=$a2cExit | Tiempo: ${elapsed} min"
Write-Log ""

# ─── RESUMEN ──────────────────────────────────────────────────────────────
Write-Log "============================================================"
Write-Log "CADENA COMPLETADA: SAC=$sacExit | PPO=$ppoExit | A2C=$a2cExit"
Write-Log "Log completo: $logFile"
Write-Log "============================================================"
Read-Host "Presiona ENTER para cerrar"
