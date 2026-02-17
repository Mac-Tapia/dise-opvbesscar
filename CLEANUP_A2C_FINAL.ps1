Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "LIMPIEZA A2C SEGURA - PROTEGIENDO SAC & PPO" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$A2C_DIR = "checkpoints/A2C"
$SAC_DIR = "checkpoints/SAC"
$PPO_DIR = "checkpoints/PPO"

function Count-Checkpoints {
    param([string]$Path)
    if (Test-Path $Path) {
        $zips = Get-ChildItem $Path -Filter "*.zip" -ErrorAction SilentlyContinue
        return $zips.Count
    }
    return 0
}

Write-Host "VALIDACION PRE-LIMPIEZA:" -ForegroundColor Yellow
$sac_count_before = Count-Checkpoints $SAC_DIR
$ppo_count_before = Count-Checkpoints $PPO_DIR
$a2c_count_before = Count-Checkpoints $A2C_DIR

Write-Host "  SAC: $sac_count_before checkpoints" -ForegroundColor Green
Write-Host "  PPO: $ppo_count_before checkpoints" -ForegroundColor Green
Write-Host "  A2C: $a2c_count_before checkpoints" -ForegroundColor Cyan
Write-Host ""

Write-Host "LISTAR CONTENIDOS PROTEGIDOS:" -ForegroundColor Yellow
if (Test-Path $SAC_DIR) {
    Write-Host "  SAC (PROTEGIDO):" -ForegroundColor Green
    Get-ChildItem $SAC_DIR -Filter "*.zip" -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "    - $($_.Name)" -ForegroundColor Green
    }
}
if (Test-Path $PPO_DIR) {
    Write-Host "  PPO (PROTEGIDO):" -ForegroundColor Green
    Get-ChildItem $PPO_DIR -Filter "*.zip" -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "    - $($_.Name)" -ForegroundColor Green
    }
}
Write-Host ""

Write-Host "LIMPIAR A2C:" -ForegroundColor Cyan
if ((Test-Path $A2C_DIR) -and ($a2c_count_before -gt 0)) {
    Write-Host "  Eliminando $a2c_count_before checkpoints de A2C..." -ForegroundColor Yellow
    Get-ChildItem $A2C_DIR -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
    Write-Host "  A2C limpiado!" -ForegroundColor Green
} else {
    Write-Host "  A2C ya estaba limpio" -ForegroundColor Gray
}
Write-Host ""

Write-Host "VALIDACION POST-LIMPIEZA:" -ForegroundColor Yellow
$sac_count_after = Count-Checkpoints $SAC_DIR
$ppo_count_after = Count-Checkpoints $PPO_DIR
$a2c_count_after = Count-Checkpoints $A2C_DIR

if ($sac_count_after -eq $sac_count_before) {
    Write-Host "  SAC PROTEGIDO: $sac_count_before checkpoints (sin cambios)" -ForegroundColor Green
} else {
    Write-Host "  ERROR: SAC fue modificado!" -ForegroundColor Red
    exit 1
}

if ($ppo_count_after -eq $ppo_count_before) {
    Write-Host "  PPO PROTEGIDO: $ppo_count_before checkpoints (sin cambios)" -ForegroundColor Green
} else {
    Write-Host "  ERROR: PPO fue modificado!" -ForegroundColor Red
    exit 1
}

Write-Host "  A2C LIMPIO: $a2c_count_after checkpoints" -ForegroundColor Cyan
Write-Host ""

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "LIMPIEZA COMPLETADA CON EXITO" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  SAC: $sac_count_before checkpoints PROTEGIDOS" -ForegroundColor Green
Write-Host "  PPO: $ppo_count_before checkpoints PROTEGIDOS" -ForegroundColor Green
Write-Host "  A2C: LIMPIO Y LISTO PARA ENTRENAR" -ForegroundColor Cyan
Write-Host ""
