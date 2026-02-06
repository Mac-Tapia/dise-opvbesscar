# Script para eliminar TODOS los archivos excepto los 18 permitidos
$root = (Get-Location).Path

# Archivos que DEBEN MANTENERSE
$allowed = @(
    "train_sac_multiobjetivo.py",
    "train_ppo_multiobjetivo.py",
    "train_a2c_multiobjetivo.py",
    "requirements.txt",
    "requirements-training.txt",
    "requirements-citylearn-v2.txt",
    "Dockerfile",
    "Dockerfile.fastapi",
    "docker-compose.yml",
    "docker-compose.dev.yml",
    "docker-compose.fastapi.yml",
    "docker-compose.gpu.yml",
    "docker-entrypoint.sh",
    "pyproject.toml",
    "pyrightconfig.json",
    "py.typed",
    "setup.py",
    "gpu_cuda_config.json",
    "cleanup_root.ps1"
)

Write-Host "Directorio actual: $root"

# Obtener todos los archivos en la raiz
$all = @(Get-ChildItem -File -ErrorAction SilentlyContinue)

# Archivos a eliminar
$toDelete = @()
foreach ($file in $all) {
    if ($file.Name -notIn $allowed) {
        $toDelete += $file
    }
}

$count = $toDelete.Count

Write-Host ""
Write-Host "Total archivos: $($all.Count)"
Write-Host "A eliminar: $count"
Write-Host ""

# Eliminar
if ($count -gt 0) {
    foreach ($file in $toDelete) {
        Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
        Write-Host "Eliminado: $($file.Name)"
    }
    Write-Host ""
    Write-Host "COMPLETADO: $count archivos eliminados"
} else {
    Write-Host "Nada para eliminar"
}

# Verificar resultado final
$final = @(Get-ChildItem -File -ErrorAction SilentlyContinue)
Write-Host "Archivos finales: $($final.Count)"
