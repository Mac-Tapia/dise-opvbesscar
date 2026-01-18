# docker-run.ps1
# PowerShell script to build and run Iquitos CityLearn Docker pipeline on Windows

param(
    [string]$Config = "configs/default.yaml",
    [string]$Action = "run",  # build | run | logs | stop | clean
    [switch]$GPU = $false,
    [switch]$SkipOE2 = $false,
    [switch]$Detach = $false,
    [string]$ImageTag = "iquitos-citylearn:latest"
)

$ErrorActionPreference = "Stop"

function Write-Header {
    param([string]$Message)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Check-Docker {
    try {
        docker --version | Out-Null
        Write-Host "✓ Docker is installed" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Docker is not installed or not in PATH" -ForegroundColor Red
        exit 1
    }
}

function Build-Image {
    Write-Header "Building Docker Image"
    
    $buildArgs = @(
        "-t", $ImageTag,
        "-f", "Dockerfile",
        "--build-arg", "BUILDKIT_INLINE_CACHE=1",
        "."
    )
    
    & docker build @buildArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Image built successfully" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Build failed" -ForegroundColor Red
        exit 1
    }
}

function Run-Pipeline {
    Write-Header "Running OE2→OE3 Pipeline"
    
    $runArgs = @(
        "--name", "iquitos-pipeline-$(Get-Random)",
        "--rm",
        "-v", "${PWD}/data:/app/data",
        "-v", "${PWD}/outputs:/app/outputs",
        "-v", "${PWD}/configs:/app/configs:ro"
    )
    
    # GPU support
    if ($GPU) {
        $runArgs += "--gpus", "all"
        Write-Host "✓ GPU support enabled" -ForegroundColor Yellow
    }
    
    # Detached mode
    if ($Detach) {
        $runArgs += "-d"
        Write-Host "✓ Running in detached mode" -ForegroundColor Yellow
    }
    else {
        $runArgs += "-it"
    }
    
    # Skip OE2 flag
    $cmdArgs = @($Config)
    if ($SkipOE2) {
        $cmdArgs += "true"
        Write-Host "✓ Skipping OE2 stages" -ForegroundColor Yellow
    }
    
    $runArgs += $ImageTag
    $runArgs += $cmdArgs
    
    Write-Host "Executing: docker run $($runArgs -join ' ')" -ForegroundColor Gray
    
    & docker run @runArgs
}

function Run-Compose {
    Write-Header "Starting Docker Compose Stack"
    
    $composeArgs = @()
    
    if ($GPU) {
        $composeArgs += "-f", "docker-compose.gpu.yml"
        Write-Host "✓ GPU compose file selected" -ForegroundColor Yellow
    }
    
    $composeArgs += "up"
    
    if ($Detach) {
        $composeArgs += "-d"
        Write-Host "✓ Running in background" -ForegroundColor Yellow
    }
    
    & docker-compose @composeArgs
}

function Show-Logs {
    Write-Header "Pipeline Logs"
    
    & docker logs -f (& docker ps --filter "name=iquitos-pipeline" --format "{{.ID}}")
}

function Stop-Pipeline {
    Write-Header "Stopping Pipeline"
    
    & docker-compose down
    Write-Host "✓ Pipeline stopped" -ForegroundColor Green
}

function Clean-Resources {
    Write-Header "Cleaning Docker Resources"
    
    Write-Host "Removing stopped containers..." -ForegroundColor Yellow
    & docker container prune -f
    
    Write-Host "Removing dangling images..." -ForegroundColor Yellow
    & docker image prune -f
    
    Write-Host "✓ Cleanup completed" -ForegroundColor Green
}

# Main execution
Check-Docker

switch ($Action) {
    "build" {
        Build-Image
    }
    "run" {
        Build-Image
        Run-Pipeline
    }
    "compose" {
        Build-Image
        Run-Compose
    }
    "logs" {
        Show-Logs
    }
    "stop" {
        Stop-Pipeline
    }
    "clean" {
        Clean-Resources
    }
    default {
        Write-Host "Usage: $($MyInvocation.MyCommand.Name) -Action [build|run|compose|logs|stop|clean] [-GPU] [-SkipOE2] [-Detach]" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor Cyan
        Write-Host "  # Full pipeline with GPU" -ForegroundColor Gray
        Write-Host "  .\docker-run.ps1 -Action run -GPU" -ForegroundColor White
        Write-Host ""
        Write-Host "  # Resume OE3 (skip OE2) in background" -ForegroundColor Gray
        Write-Host "  .\docker-run.ps1 -Action run -SkipOE2 -Detach" -ForegroundColor White
        Write-Host ""
        Write-Host "  # Docker Compose stack" -ForegroundColor Gray
        Write-Host "  .\docker-run.ps1 -Action compose -GPU" -ForegroundColor White
    }
}
