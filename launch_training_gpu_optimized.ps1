# GPU-Optimized Training Launcher for RTX 4060
# Includes real-time GPU monitoring and memory tracking
# Date: 2026-01-27

param(
    [switch]$Monitor = $false,      # Enable real-time GPU monitoring
    [switch]$NoGPU = $false,        # Force CPU-only mode (debugging)
    [string]$ConfigPath = "configs/default.yaml"
)

Write-Host "`n" -ForegroundColor White
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "GPU-OPTIMIZED TRAINING LAUNCHER FOR RTX 4060" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

# Function to display GPU status
function Show-GPUStatus {
    Write-Host "`n[GPU STATUS]" -ForegroundColor Yellow
    $nvidia_output = & nvidia-smi --query-gpu=index, name, memory.used, memory.total, utilization.gpu, temperature.gpu `
        --format=csv, noheader, nounits 2>$null

    if ($LASTEXITCODE -eq 0) {
        foreach ($line in $nvidia_output) {
            $parts = $line -split ','
            $gpu_idx = $parts[0].Trim()
            $gpu_name = $parts[1].Trim()
            $mem_used = [int]$parts[2]
            $mem_total = [int]$parts[3]
            $util_gpu = [int]$parts[4]
            $temp = [int]$parts[5]

            $mem_percent = [math]::Round(($mem_used / $mem_total) * 100, 1)

            Write-Host "  GPU $gpu_idx : $gpu_name" -ForegroundColor Cyan
            Write-Host "    Memory: $mem_used / $mem_total MB ($mem_percent %)" -ForegroundColor White
            Write-Host "    GPU Util: $util_gpu %" -ForegroundColor White
            Write-Host "    Temperature: $temp C" -ForegroundColor White
        }
    }
    else {
        Write-Host "  WARNING: nvidia-smi not found. GPU monitoring disabled." -ForegroundColor Red
    }
}

# Function to check prerequisites
function Check-Prerequisites {
    Write-Host "`n[PREREQUISITES CHECK]" -ForegroundColor Yellow

    # Check Python version
    $python_version = & python --version 2>&1
    Write-Host "  Python: $python_version" -ForegroundColor Green

    # Check PyTorch
    $pytorch_check = & python -c "import torch; print(f'PyTorch {torch.version.__version__} (CUDA {torch.version.cuda})'); print(f'GPU Available: {torch.cuda.is_available()}'); print(f'GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')" 2>&1
    Write-Host "  PyTorch:`n$($pytorch_check | ForEach-Object {"    $_"})" -ForegroundColor Green

    # Check config file
    if (Test-Path $ConfigPath) {
        Write-Host "  Config: $ConfigPath [OK]" -ForegroundColor Green
    }
    else {
        Write-Host "  Config: $ConfigPath [NOT FOUND]" -ForegroundColor Red
        exit 1
    }
}

# Function to start GPU monitoring in background
function Start-GPUMonitoring {
    Write-Host "`n[GPU MONITORING]" -ForegroundColor Yellow
    Write-Host "  GPU monitoring started. Updating every 5 seconds." -ForegroundColor Green

    # Create a job to monitor GPU
    $monitor_script = {
        while ($true) {
            $nvidia_output = & nvidia-smi --query-gpu=index, memory.used, memory.total, utilization.gpu, temperature.gpu `
                --format=csv, noheader, nounits --loop-ms=5000 2>$null

            if ($LASTEXITCODE -eq 0) {
                foreach ($line in $nvidia_output) {
                    $parts = $line -split ','
                    $mem_used = [int]$parts[1]
                    $mem_total = [int]$parts[2]
                    $util_gpu = [int]$parts[3]
                    $temp = [int]$parts[4]

                    $mem_percent = [math]::Round(($mem_used / $mem_total) * 100, 1)

                    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] GPU: $util_gpu% | Memory: $mem_percent% ($mem_used/$mem_total MB) | Temp: $temp C" `
                        -ForegroundColor Cyan
                }
            }
            Start-Sleep -Seconds 5
        }
    }

    Start-Job -ScriptBlock $monitor_script -Name "GPUMonitoring" | Out-Null
    Write-Host "  Job ID: $(Get-Job -Name GPUMonitoring | Select-Object -ExpandProperty Id)" -ForegroundColor Green
}

# Main execution
function Start-Training {
    Write-Host "`n[TRAINING CONFIGURATION]" -ForegroundColor Yellow
    Write-Host "  Config file: $ConfigPath" -ForegroundColor Green

    if ($NoGPU) {
        Write-Host "  Mode: CPU-only (GPU disabled)" -ForegroundColor Yellow
        $env:CUDA_VISIBLE_DEVICES = "-1"
    }
    else {
        Write-Host "  Mode: GPU-accelerated" -ForegroundColor Green
        Remove-Item env:CUDA_VISIBLE_DEVICES -ErrorAction SilentlyContinue
    }

    # Set UTF-8 encoding for logging
    $env:PYTHONIOENCODING = "utf-8"

    # Set environment variables for optimization
    $env:OMP_NUM_THREADS = "8"
    $env:MKL_NUM_THREADS = "8"

    Write-Host "`n[LAUNCHING TRAINING]" -ForegroundColor Cyan
    Write-Host "  Command: py -3.11 -m scripts.launch_gpu_optimized_training" -ForegroundColor White
    Write-Host "  Expected duration: ~10.7 hours (SAC 5.25h + PPO 3.28h + A2C 2.19h)" -ForegroundColor White
    Write-Host "  Output file: training_gpu_optimized.log" -ForegroundColor White

    # Show initial GPU status
    Show-GPUStatus

    # Start GPU monitoring if requested
    if ($Monitor) {
        Start-GPUMonitoring
    }

    # Launch training
    Write-Host "`n" -ForegroundColor White
    py -3.11 -m scripts.launch_gpu_optimized_training --config $ConfigPath 2>&1 | Tee-Object -FilePath training_gpu_optimized.log

    # Show final GPU status
    Write-Host "`n" -ForegroundColor White
    Show-GPUStatus

    # Stop GPU monitoring if running
    if (Get-Job -Name "GPUMonitoring" -ErrorAction SilentlyContinue) {
        Stop-Job -Name "GPUMonitoring"
        Remove-Job -Name "GPUMonitoring"
        Write-Host "`n[GPU MONITORING] Stopped" -ForegroundColor Yellow
    }
}

# Run all functions
Check-Prerequisites
Show-GPUStatus
Start-Training

Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "TRAINING COMPLETED" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "`nResults location: outputs/oe3_simulations/" -ForegroundColor Green
Write-Host "Log file: training_gpu_optimized.log" -ForegroundColor Green
