# ============================================================================
# LIMPIEZA A2C SEGURA - 2026-02-16
# ============================================================================
# OBJETIVO: Limpiar checkpoints A2C PROTEGIENDO SAC y PPO
# VALIDACION: Verifica en cada paso que SAC/PPO no se tocan
# ============================================================================

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  LIMPIEZA A2C SEGURA - PROTEGIENDO SAC & PPO                  ║" -ForegroundColor Cyan
Write-Host "║  Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Constantes de rutas
$A2C_DIR = "checkpoints/A2C"
$SAC_DIR = "checkpoints/SAC"
$PPO_DIR = "checkpoints/PPO"

# Función para validar directorio
function Validate-Directory {
    param([string]$Path, [string]$Name)
    if (Test-Path $Path) {
        $count = (Get-ChildItem $Path -Recurse | Measure-Object).Count
        Write-Host "  ✓ $Name : EXISTS ($count items)" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  ✗ $Name : NOT FOUND" -ForegroundColor Yellow
        return $false
    }
}

# Función para contar checkpoints
function Count-Checkpoints {
    param([string]$Path)
    if (Test-Path $Path) {
        $zips = Get-ChildItem $Path -Filter "*.zip" -ErrorAction SilentlyContinue
        return $zips.Count
    }
    return 0
}

# ============================================================================
# PASO 1: VALIDACION PRE-LIMPIEZA
# ============================================================================
Write-Host "PASO 1: VALIDACION PRE-LIMPIEZA" -ForegroundColor Cyan
Write-Host "-" * 64

Write-Host ""
Write-Host "Estado ANTES de limpieza:" -ForegroundColor Yellow
$sac_exists = Validate-Directory $SAC_DIR "SAC"
$ppo_exists = Validate-Directory $PPO_DIR "PPO"
$a2c_exists = Validate-Directory $A2C_DIR "A2C"
Write-Host ""

# Guardar recuento de SAC y PPO
$sac_count = Count-Checkpoints $SAC_DIR
$ppo_count = Count-Checkpoints $PPO_DIR
$a2c_count = Count-Checkpoints $A2C_DIR

Write-Host "Checkpoints .zip:" -ForegroundColor Yellow
Write-Host "  SAC: $sac_count checkpoints" -ForegroundColor Green
Write-Host "  PPO: $ppo_count checkpoints" -ForegroundColor Green
Write-Host "  A2C: $a2c_count checkpoints" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# PASO 2: BACKUP DE SAC Y PPO (OPCIONAL)
# ============================================================================
Write-Host "PASO 2: LISTAR CONTENIDOS A PROTEGER" -ForegroundColor Cyan
Write-Host "-" * 64
Write-Host ""

if ($sac_exists) {
    Write-Host "SAC PROTEGIDO (no sera tocado):" -ForegroundColor Green
    Get-ChildItem $SAC_DIR -Filter "*.zip" -ErrorAction SilentlyContinue | ForEach-Object {
        $size = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  ✓ $($_.Name) | $size MB" -ForegroundColor Green
    }
} else {
    Write-Host "  (No hay checkpoints SAC para proteger)" -ForegroundColor Gray
}

Write-Host ""

if ($ppo_exists) {
    Write-Host "PPO PROTEGIDO (no sera tocado):" -ForegroundColor Green
    Get-ChildItem $PPO_DIR -Filter "*.zip" -ErrorAction SilentlyContinue | ForEach-Object {
        $size = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  ✓ $($_.Name) | $size MB" -ForegroundColor Green
    }
} else {
    Write-Host "  (No hay checkpoints PPO para proteger)" -ForegroundColor Gray
}

Write-Host ""

# ============================================================================
# PASO 3: LIMPIAR A2C
# ============================================================================
Write-Host "PASO 3: LIMPIAR CHECKPOINTS A2C" -ForegroundColor Cyan
Write-Host "-" * 64
Write-Host ""

if ($a2c_exists -and $a2c_count -gt 0) {
    Write-Host "Eliminando $a2c_count checkpoints de A2C..." -ForegroundColor Yellow
    
    try {
        Get-ChildItem $A2C_DIR -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "  ✓ A2C directory cleaned successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ Error limpiando A2C: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  (No hay checkpoints A2C, directorio limpio)" -ForegroundColor Gray
}

Write-Host ""

# ============================================================================
# PASO 4: VALIDACION POST-LIMPIEZA
# ============================================================================
Write-Host "PASO 4: VALIDACION POST-LIMPIEZA" -ForegroundColor Cyan
Write-Host "-" * 64
Write-Host ""

Write-Host "Estado DESPUES de limpieza:" -ForegroundColor Yellow

# Verificar SAC nuevamente
$sac_count_after = Count-Checkpoints $SAC_DIR
if ($sac_count_after -eq $sac_count) {
    Write-Host "  ✓ SAC PROTEGIDO: $sac_count checkpoints (sin cambios)" -ForegroundColor Green
} else {
    Write-Host "  ✗ SAC MODIFICADO: ANTES=$sac_count AHORA=$sac_count_after" -ForegroundColor Red
    exit 1
}

# Verificar PPO nuevamente
$ppo_count_after = Count-Checkpoints $PPO_DIR
if ($ppo_count_after -eq $ppo_count) {
    Write-Host "  ✓ PPO PROTEGIDO: $ppo_count checkpoints (sin cambios)" -ForegroundColor Green
} else {
    Write-Host "  ✗ PPO MODIFICADO: ANTES=$ppo_count AHORA=$ppo_count_after" -ForegroundColor Red
    exit 1
}

# Verificar A2C limpiado
$a2c_count_after = Count-Checkpoints $A2C_DIR
if ($a2c_count_after -eq 0) {
    Write-Host "  ✓ A2C LIMPIADO: 0 checkpoints" -ForegroundColor Green
} else {
    Write-Host "  ✗ A2C NO LIMPADO: Aun tiene $a2c_count_after checkpoints" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================================================
# RESUMEN FINAL
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  LIMPIEZA COMPLETADA CON EXITO                                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ✓ SAC:  $sac_count checkpoints PROTEGIDOS" -ForegroundColor Green
Write-Host "  ✓ PPO:  $ppo_count checkpoints PROTEGIDOS" -ForegroundColor Green
Write-Host "  ✓ A2C:  LIMPIOS Y LISTOS PARA ENTRENAR" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""
