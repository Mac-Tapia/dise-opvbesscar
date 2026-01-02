param(
    [string]$Config = "configs/default.yaml",
    [switch]$SkipDataset = $false,
    [switch]$SkipUncontrolled = $false
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$venvActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"

if (Test-Path $venvActivate) {
    Write-Host "Activando entorno virtual: $venvActivate"
    . $venvActivate
} else {
    Write-Warning "No se encontró el entorno virtual en $venvActivate. Continúo sin activarlo."
}

$python = "python"

if (-not $SkipDataset) {
    Write-Host "`n==> Construyendo dataset CityLearn (OE3)"
    & $python -m scripts.run_oe3_build_dataset --config $Config
}

$simulateArgs = @("--config", $Config)
if ($SkipDataset) { $simulateArgs += "--skip-dataset" }
if ($SkipUncontrolled) { $simulateArgs += "--skip-uncontrolled" }

Write-Host "`n==> Entrenando y evaluando agentes OE3 (SAC/PPO/A2C)"
& $python -m scripts.run_oe3_simulate @simulateArgs
