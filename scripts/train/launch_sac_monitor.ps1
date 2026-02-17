# SAC Training Monitor with Real-time Analytics
# Monitorea Actor Loss, Q-values, rewards en tiempo real

param(
    [string]$LogFile = "sac_training.log",
    [int]$CheckInterval = 2,
    [switch]$FollowMode = $true
)

$ErrorActionPreference = "Continue"
$WarningPreference = "Continue"

# Colors
$ColorGood = "Green"
$ColorWarn = "Yellow"
$ColorBad = "Red"
$ColorInfo = "Cyan"

Write-Host ""
Write-Host "="*80 -ForegroundColor $ColorInfo
Write-Host "SAC TRAINING MONITOR - REAL-TIME ANALYTICS" -ForegroundColor $ColorInfo
Write-Host "="*80 -ForegroundColor $ColorInfo
Write-Host ""
Write-Host "Starting SAC training with v9.0 (grid-centric, minimal reward)..." -ForegroundColor $ColorInfo
Write-Host ""

# Initiate training in background
$job = Start-Process python -ArgumentList "scripts/train/train_sac_multiobjetivo.py" -NoNewWindow -PassThru

Write-Host "Training process started (PID: $($job.Id))" -ForegroundColor $ColorGood
Write-Host ""

# Monitor function
$lastLines = @()
$actorLossHistory = @()
$qValuesHistory = @()
$stepCount = 0

function Parse-LogLine {
    param([string]$line)
    
    $metrics = @{}
    
    # Extract Actor Loss
    if ($line -match "Actor Loss:\s*(-?[\d.]+)") {
        $metrics['ActorLoss'] = [double]$matches[1]
    }
    
    # Extract Q-values
    if ($line -match "\| Q=([\d.]+)") {
        $metrics['QValue'] = [double]$matches[1]
    }
    
    # Extract Timestep
    if ($line -match "\[STEP\s*([\d,]+)\]") {
        $metrics['Step'] = [int]$matches[1].Replace(",", "")
    }
    
    # Extract Critic Loss
    if ($line -match "Critic Loss.*?:\s*(-?[\d.]+)") {
        $metrics['CriticLoss'] = [double]$matches[1]
    }
    
    return $metrics
}

# Main loop
$monitorActive = $true
$lastModTime = (Get-Item $LogFile -ErrorAction SilentlyContinue).LastWriteTime

while ($monitorActive -and (Get-Process -Id $job.Id -ErrorAction SilentlyContinue)) {
    try {
        if (Test-Path $LogFile) {
            $currentModTime = (Get-Item $LogFile).LastWriteTime
            
            if ($currentModTime -ne $lastModTime) {
                $newLines = Get-Content $LogFile | Select-Object -Last 50
                
                foreach ($line in $newLines) {
                    $parsed = Parse-LogLine $line
                    
                    # Display key metrics
                    if ($parsed['ActorLoss']) {
                        $actorLossHistory += $parsed['ActorLoss']
                        $qValuesHistory += $parsed['QValue']
                        
                        # Color-code based on healthy ranges
                        if ($parsed['ActorLoss'] -gt -50 -and $parsed['ActorLoss'] -lt -5) {
                            $lossColor = $ColorGood
                            $status = "[OK]"
                        } elseif ($parsed['ActorLoss'] -ge -100 -and $parsed['ActorLoss'] -le -50) {
                            $lossColor = $ColorWarn
                            $status = "[MONITOR]"
                        } else {
                            $lossColor = $ColorBad
                            $status = "[ALERT]"
                        }
                        
                        # Q-values health check
                        if ($parsed['QValue'] -lt 50) {
                            $qColor = $ColorGood
                        } elseif ($parsed['QValue'] -lt 100) {
                            $qColor = $ColorWarn
                        } else {
                            $qColor = $ColorBad
                        }
                        
                        $step = $parsed['Step']
                        Write-Host "  [$status] Step $step | Actor Loss: " -NoNewline
                        Write-Host "$($parsed['ActorLoss'])" -ForegroundColor $lossColor -NoNewline
                        Write-Host " | Q-Value: " -NoNewline
                        Write-Host "$($parsed['QValue'])" -ForegroundColor $qColor
                    }
                }
                
                $lastModTime = $currentModTime
            }
        }
        
        Start-Sleep -Seconds $CheckInterval
    }
    catch {
        # Continue monitoring even on errors
    }
}

Write-Host ""
Write-Host "="*80 -ForegroundColor $ColorInfo
Write-Host "Training process completed" -ForegroundColor $ColorGood
Write-Host "="*80 -ForegroundColor $ColorInfo
Write-Host ""

# Summary
if ($actorLossHistory.Count -gt 0) {
    Write-Host "Summary Statistics:" -ForegroundColor $ColorInfo
    Write-Host "  Actor Loss avg:  $([Math]::Round(($actorLossHistory | Measure-Object -Average).Average, 2))" -ForegroundColor $ColorInfo
    Write-Host "  Q-Values avg:    $([Math]::Round(($qValuesHistory | Measure-Object -Average).Average, 2))" -ForegroundColor $ColorInfo
    Write-Host "  Total steps:     $stepCount" -ForegroundColor $ColorInfo
}

Write-Host ""
