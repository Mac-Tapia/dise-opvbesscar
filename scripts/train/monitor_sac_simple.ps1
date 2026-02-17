# Simple SAC Training Monitor - Watch Log in Real-Time
# Monitorea cambios en sac_training.log y muestra métricas clave

param(
    [string]$LogFile = "sac_training.log",
    [int]$TailLines = 10
)

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "SAC TRAINING MONITOR - REAL-TIME LOG VIEWER" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Checking log file: $LogFile" -ForegroundColor Yellow
Write-Host ""
Write-Host "Monitoring updates every 5 seconds. Press Ctrl+C to exit." -ForegroundColor Gray
Write-Host ""

$iteration = 0

while ($true) {
    $iteration++
    
    if (Test-Path $LogFile) {
        # Get last N lines
        $lines = Get-Content $LogFile -Tail $TailLines -ErrorAction SilentlyContinue
        
        if ($lines) {
            Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] [ITERATION $iteration] Last $TailLines log lines:" -ForegroundColor Cyan
            Write-Host ""
            
            # Display lines with color coding
            foreach ($line in $lines) {
                if ($line -match "Actor Loss.*(-[0-9.]+)") {
                    $loss = [double]$matches[1]
                    if ($loss -gt -50) {
                        $color = "Green"  # Good
                        $status = "[OK]"
                    } elseif ($loss -gt -100) {
                        $color = "Yellow" # Monitor
                        $status = "[!]"
                    } else {
                        $color = "Red"    # Alert
                        $status = "[X]"
                    }
                    Write-Host "  $status $line" -ForegroundColor $color
                } elseif ($line -match "EPISODIO|COMPLETADO|STEP|TIMESTEP") {
                    Write-Host "  [#] $line" -ForegroundColor Cyan
                } elseif ($line -match "OK|Progress") {
                    Write-Host "  [+] $line" -ForegroundColor Green
                } else {
                    Write-Host "     $line" -ForegroundColor Gray
                }
            }
        } else {
            Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] [WAITING] Log file exists but empty..." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] [PENDING] Log file not found. Training starting..." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "--------" -ForegroundColor Gray
    
    Start-Sleep -Seconds 5
}
