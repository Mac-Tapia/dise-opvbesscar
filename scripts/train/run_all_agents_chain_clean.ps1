param(
    [int]$Timesteps = 438000,
    [switch]$RebuildSchema
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

$RunId = Get-Date -Format "yyyyMMdd_HHmmss"
$RunRoot = Join-Path $Root "outputs\training_chain\$RunId"
$LogRoot = Join-Path $RunRoot "logs"
$ArchiveRoot = Join-Path $RunRoot "archive_previous"
New-Item -ItemType Directory -Force -Path $LogRoot, $ArchiveRoot | Out-Null

$MasterLog = Join-Path $RunRoot "chain_master.log"
function Write-ChainLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath $MasterLog -Append
}

Write-ChainLog "RunId=$RunId"
Write-ChainLog "Root=$Root"
Write-ChainLog "Timesteps=$Timesteps"

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}
Write-ChainLog "Python=$Python"

$RootFull = [System.IO.Path]::GetFullPath($Root)
function Assert-InWorkspace {
    param([string]$Path)
    $full = [System.IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($RootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside workspace: $full"
    }
    return $full
}

Write-ChainLog "Stopping active training processes, if any."
$trainPattern = "train_(sac|ppo|a2c)_citylearn\.py"
$active = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine -match $trainPattern -and
    $_.CommandLine -like "*d:\diseñopvbesscar*"
}
foreach ($proc in $active) {
    Write-ChainLog ("Stopping PID {0}: {1}" -f $proc.ProcessId, $proc.CommandLine)
    Stop-Process -Id $proc.ProcessId -Force
}
if (-not $active) {
    Write-ChainLog "No active SAC/PPO/A2C training process found."
}

$cleanTargets = @(
    "checkpoints\SAC_CityLearn",
    "checkpoints\PPO_CityLearn",
    "checkpoints\A2C_CityLearn",
    "outputs\sac_training",
    "outputs\ppo_training",
    "outputs\a2c_training",
    "logs\tensorboard\sac_citylearn",
    "logs\tensorboard\ppo_citylearn",
    "logs\tensorboard\a2c_citylearn"
)

Write-ChainLog "Archiving previous checkpoints/results."
foreach ($rel in $cleanTargets) {
    $target = Join-Path $Root $rel
    Assert-InWorkspace $target | Out-Null
    if (Test-Path -LiteralPath $target) {
        $archiveName = $rel -replace "[\\/]", "__"
        $archivePath = Join-Path $ArchiveRoot $archiveName
        Assert-InWorkspace $archivePath | Out-Null
        Move-Item -LiteralPath $target -Destination $archivePath -Force
        Write-ChainLog "Archived $rel -> $archiveName"
    }
    New-Item -ItemType Directory -Force -Path $target | Out-Null
}

$agents = @(
    @{ Name = "SAC"; Script = "scripts\train\train_sac_citylearn.py"; Log = "sac.log" },
    @{ Name = "PPO"; Script = "scripts\train\train_ppo_citylearn.py"; Log = "ppo.log" },
    @{ Name = "A2C"; Script = "scripts\train\train_a2c_citylearn.py"; Log = "a2c.log" }
)

foreach ($agent in $agents) {
    $script = Join-Path $Root $agent.Script
    Assert-InWorkspace $script | Out-Null
    $agentLog = Join-Path $LogRoot $agent.Log
    $args = @($script, "--timesteps", "$Timesteps")
    if ($RebuildSchema -and $agent.Name -eq "SAC") {
        $args += "--rebuild-schema"
    }

    Write-ChainLog ("Starting {0}: {1} {2}" -f $agent.Name, $Python, ($args -join " "))
    & $Python @args 2>&1 | Tee-Object -FilePath $agentLog
    $exitCode = $LASTEXITCODE
    Write-ChainLog ("Finished {0} with exit code {1}. Log: {2}" -f $agent.Name, $exitCode, $agentLog)
    if ($exitCode -ne 0) {
        Write-ChainLog "Aborting chain because $($agent.Name) failed."
        exit $exitCode
    }
}

Write-ChainLog "Training chain completed successfully."
