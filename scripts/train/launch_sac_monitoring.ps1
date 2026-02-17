param([switch]$Wait = $false)

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$WORKSPACE_ROOT = Get-Location
$PYTHON_SCRIPT = "scripts/train/train_sac_multiobjetivo.py"
$LOG_FILE = "sac_training.log"
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd_HHmmss"

Clear-Host

Write-Host "=========================================================================="
Write-Host "SAC TRAINING WITH LIVE MONITORING v7.3 (2026-02-16)" -ForegroundColor Green
Write-Host "=========================================================================="
Write-Host ""
Write-Host "Workspace: $WORKSPACE_ROOT"
Write-Host "Script: $PYTHON_SCRIPT"
Write-Host "Log: $LOG_FILE"
Write-Host "Time: $TIMESTAMP"
Write-Host ""

if (-not (Test-Path $WORKSPACE_ROOT)) {
    Write-Host "ERROR: Workspace not found" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $PYTHON_SCRIPT)) {
    Write-Host "ERROR: Script not found: $PYTHON_SCRIPT" -ForegroundColor Red
    exit 1
}

Write-Host "[PREP] Rotating previous log..."
$logPath = Join-Path $WORKSPACE_ROOT $LOG_FILE
if (Test-Path $logPath) {
    $backupLog = "$logPath.backup_$TIMESTAMP"
    Move-Item $logPath $backupLog -Force
    Write-Host "[OK] Log rotated: $backupLog"
}

Write-Host ""
Write-Host "[INIT] Starting SAC training in background..."
Write-Host ""

Push-Location $WORKSPACE_ROOT

$process = Start-Process `
    -FilePath python `
    -ArgumentList $PYTHON_SCRIPT `
    -WorkingDirectory $WORKSPACE_ROOT `
    -PassThru `
    -NoNewWindow

$processId = $process.Id
Write-Host "[OK] Process started (PID: $processId)" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop monitoring (training continues in background)" -ForegroundColor Cyan
Write-Host ""

$lastLogSize = 0
$checkInterval = 2
$errorCount = 0

try 
{
    while ($true) 
    {
        if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) 
        {
            Write-Host ""
            Write-Host "[DONE] Process finished" -ForegroundColor Yellow
            break
        }
        
        if (Test-Path $logPath) 
        {
            $currentSize = (Get-Item $logPath).Length
            if ($currentSize -gt $lastLogSize) 
            {
                $newContent = Get-Content $logPath -Tail 3 -ErrorAction SilentlyContinue
                if ($newContent) 
                {
                    foreach ($line in $newContent) 
                    {
                        if ($line -match "ERROR") 
                        {
                            Write-Host "  [ERROR] $line" -ForegroundColor Red
                            $errorCount++
                        } 
                        elseif ($line -match "WARNING") 
                        {
                            Write-Host "  [WARN] $line" -ForegroundColor Yellow
                        } 
                        else 
                        {
                            Write-Host "  $line" -ForegroundColor White
                        }
                    }
                }
                $lastLogSize = $currentSize
            }
        }
        
        Start-Sleep -Seconds $checkInterval
    }
    
    Write-Host ""
    Write-Host "Waiting for process to complete..."
    $process.WaitForExit()
    $exitCode = $process.ExitCode
    
    Write-Host ""
    Write-Host "=========================================================================="
    if ($exitCode -eq 0) 
    {
        Write-Host "SUCCESS: SAC training completed" -ForegroundColor Green
    } 
    else 
    {
        Write-Host "ERROR: Training failed with code $exitCode" -ForegroundColor Red
    }
    Write-Host "=========================================================================="
    
    Write-Host ""
    Write-Host "Results:"
    Write-Host "  PID: $processId"
    Write-Host "  Code: $exitCode"
    Write-Host "  Log: $logPath"
    Write-Host "  Checkpoints: checkpoints/SAC/"
    Write-Host ""
    
    exit $exitCode
}
catch 
{
    Write-Host ""
    Write-Host "Monitoring paused by user" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Training continues in background:"
    Write-Host "  Monitor: Get-Content '$LOG_FILE' -Tail 20 -Wait"
    Write-Host "  Stop: Stop-Process -Id $processId"
    Write-Host ""
}
finally 
{
    Pop-Location
}
