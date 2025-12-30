[CmdletBinding()]
param(
    [string]$Config = "configs/default.yaml",
    [switch]$SkipDataset,
    [switch]$SkipCo2Table,
    [switch]$SkipUncontrolled
)

$ErrorActionPreference = "Stop"

# Ubica la raiz del repo (carpeta scripts -> raiz)
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $repoRoot

try {
    # Activa la venv si existe (Python 3.11 requerido por scripts/_common.py)
    $venvActivate = Join-Path $repoRoot ".venv/Scripts/Activate.ps1"
    if (Test-Path $venvActivate) {
        Write-Host "Activando entorno virtual: $venvActivate"
        . $venvActivate
    } else {
        Write-Warning "No se encontro .venv; usa un Python 3.11 del sistema antes de ejecutar este script."
    }

    $venvPython = Join-Path $repoRoot ".venv/Scripts/python.exe"
    $python = if (Test-Path $venvPython) { $venvPython } else { "python" }

    $pyVer = & $python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
    if ($pyVer -ne "3.11") {
        Write-Warning "Python 3.11 requerido; version detectada: $pyVer"
    }

    function Invoke-Step {
        param(
            [string]$Title,
            [string[]]$CommandArgs
        )
        Write-Host "`n==> $Title"
        & $python @CommandArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Fallo en: $Title"
        }
    }

    if (-not $SkipDataset.IsPresent) {
        Invoke-Step -Title "Construyendo dataset CityLearn (OE3)" -CommandArgs @("-m", "scripts.run_oe3_build_dataset", "--config", $Config)
    } else {
        Write-Host "Saltando generacion de dataset (--SkipDataset activado)."
    }

    $simArgs = @("-m", "scripts.run_oe3_simulate", "--config", $Config)
    if ($SkipUncontrolled.IsPresent) {
        $simArgs += "--skip-uncontrolled"
    }
    Invoke-Step -Title "Entrenando y evaluando agentes OE3 (SAC/PPO/A2C)" -CommandArgs $simArgs

    if (-not $SkipCo2Table.IsPresent) {
        Invoke-Step -Title "Generando tablas CO2" -CommandArgs @("-m", "scripts.run_oe3_co2_table", "--config", $Config)
    } else {
        Write-Host "Saltando tablas CO2 (--SkipCo2Table activado)."
    }

    # Grafica comparativa de entrenamiento (SAC/PPO/A2C)
    Invoke-Step -Title "Graficando entrenamiento (comparativo episodios)" -CommandArgs @("-m", "scripts.plot_oe3_training", "--config", $Config)

    Write-Host "`nListo. Artefactos clave:"
    Write-Host "- Entrenamiento: $($repoRoot.Path)/analyses/oe3/training"
    Write-Host "- Simulaciones: $($repoRoot.Path)/outputs/oe3/simulations"
} finally {
    Pop-Location
}
