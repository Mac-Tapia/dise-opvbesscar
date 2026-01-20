# Docker Quick Commands for PVBESSCAR - PowerShell

param(
    [string]$Command = "",
    [switch]$Clean = $false,
    [switch]$GPU = $false,
    [switch]$Dev = $false
)

function Show-Help {
    Write-Host ""
    Write-Host "PVBESSCAR Docker Commands" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\docker_quick.ps1 -Command [command] [options]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  build              Build CPU image"
    Write-Host "  build -GPU         Build GPU image"
    Write-Host "  build -Dev         Build dev image"
    Write-Host "  build -Clean       Build without cache"
    Write-Host ""
    Write-Host "  up                 Start CPU services"
    Write-Host "  up -GPU            Start GPU services"
    Write-Host "  up -Dev            Start dev services"
    Write-Host ""
    Write-Host "  down               Stop all services"
    Write-Host "  down -Clean        Stop and remove volumes"
    Write-Host ""
    Write-Host "  logs               View all logs"
    Write-Host "  logs -GPU          View GPU service logs"
    Write-Host ""
    Write-Host "  stats              Show resource usage"
    Write-Host "  health             Check container health"
    Write-Host "  clean              Clean Docker cache"
    Write-Host ""
}

function Invoke-DockerBuild {
    param(
        [string]$Tag = "pvbesscar:latest",
        [bool]$NoCache = $false
    )
    
    $args = @(
        "build",
        "--build-arg", "BUILDKIT_INLINE_CACHE=1",
        "-t", $Tag
    )
    
    if ($NoCache) {
        $args = @("build", "--no-cache", "-t", $Tag)
    }
    
    $args += "."
    
    Write-Host "`n📦 Building image: $Tag" -ForegroundColor Cyan
    & docker $args
}

function Invoke-DockerCompose {
    param(
        [string]$File = "docker-compose.yml",
        [string]$Action = "up",
        [switch]$Detach = $true
    )
    
    $args = @("-f", $File, $Action)
    
    if ($Detach -and $Action -eq "up") {
        $args += "-d"
    }
    
    Write-Host "`n🐳 Running: docker-compose $($args -join ' ')" -ForegroundColor Cyan
    & docker-compose $args
}

# Route commands
switch ($Command.ToLower()) {
    "build" {
        if ($GPU) {
            Invoke-DockerBuild -Tag "pvbesscar:latest-gpu" -NoCache $Clean
        }
        elseif ($Dev) {
            Invoke-DockerBuild -Tag "pvbesscar:dev" -NoCache $Clean
        }
        else {
            Invoke-DockerBuild -Tag "pvbesscar:latest" -NoCache $Clean
        }
    }
    
    "up" {
        if ($GPU) {
            Invoke-DockerCompose -File "docker-compose.gpu.yml" -Action "up"
        }
        elseif ($Dev) {
            Invoke-DockerCompose -File "docker-compose.dev.yml" -Action "up"
        }
        else {
            Invoke-DockerCompose -File "docker-compose.yml" -Action "up"
        }
        
        Start-Sleep -Seconds 2
        & docker ps
    }
    
    "down" {
        $file = if ($GPU) { "docker-compose.gpu.yml" } else { "docker-compose.yml" }
        $action = if ($Clean) { @("down", "-v") } else { @("down") }
        
        Write-Host "`n⏹️  Stopping services..." -ForegroundColor Cyan
        & docker-compose -f $file $action
    }
    
    "logs" {
        $file = if ($GPU) { "docker-compose.gpu.yml" } else { "docker-compose.yml" }
        
        Write-Host "`n📋 Showing logs..." -ForegroundColor Cyan
        & docker-compose -f $file logs -f --tail=100
    }
    
    "stats" {
        Write-Host "`n📊 Docker resource usage:" -ForegroundColor Cyan
        & docker stats
    }
    
    "health" {
        $container = if ($GPU) { "pvbesscar-pipeline-gpu" } else { "pvbesscar-pipeline" }
        
        Write-Host "`n✅ Checking health for: $container" -ForegroundColor Cyan
        & docker inspect --format='{{json .State.Health}}' $container | ConvertFrom-Json | Format-List
    }
    
    "clean" {
        Write-Host "`n🧹 Pruning Docker cache..." -ForegroundColor Cyan
        & docker builder prune --all -f
    }
    
    default {
        Show-Help
    }
}
