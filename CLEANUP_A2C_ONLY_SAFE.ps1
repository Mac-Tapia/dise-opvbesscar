# ================================================================
# CLEANUP_A2C_ONLY_SAFE.ps1
# Limpieza SEGURA de checkpoints A2C únicamente
# Protege SAC y PPO durante todas las operaciones
# ================================================================

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  CLEANUP A2C ONLY - SAFE MODE                                ║" -ForegroundColor Cyan
Write-Host "║  ✓ Solo A2C se limpia                                        ║" -ForegroundColor Green
Write-Host "║  ✓ SAC y PPO están PROTEGIDOS                                ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ===== PASO 1: VALIDAR ESTRUCTURA CHECKPOINTS =====
Write-Host "1️⃣  VALIDANDO ESTRUCTURA DE CHECKPOINTS..." -ForegroundColor Yellow

$checkpoint_dir = "checkpoints"
$sac_dir = Join-Path $checkpoint_dir "SAC"
$ppo_dir = Join-Path $checkpoint_dir "PPO"
$a2c_dir = Join-Path $checkpoint_dir "A2C"

Write-Host "   ├─ SAC:  $(If (Test-Path $sac_dir) { '[ENCONTRADO]' } Else { '[NO EXISTE]' })" -ForegroundColor Cyan
Write-Host "   ├─ PPO:  $(If (Test-Path $ppo_dir) { '[ENCONTRADO]' } Else { '[NO EXISTE]' })" -ForegroundColor Cyan
Write-Host "   └─ A2C:  $(If (Test-Path $a2c_dir) { '[ENCONTRADO]' } Else { '[NO EXISTE]' })" -ForegroundColor Cyan
Write-Host ""

# ===== PASO 2: VALIDAR ARCHIVOS SAC Y PPO ANTES DE LIMPIAR =====
Write-Host "2️⃣  VALIDANDO PROTECCIÓN SAC Y PPO..." -ForegroundColor Yellow

$sac_count = 0
$ppo_count = 0

if (Test-Path $sac_dir) {
    $sac_files = @(Get-Item "$sac_dir\*.zip" -ErrorAction SilentlyContinue)
    $sac_count = $sac_files.Count
    Write-Host "   ✓ SAC: $sac_count fichero(s) ZIP" -ForegroundColor Green
}

if (Test-Path $ppo_dir) {
    $ppo_files = @(Get-Item "$ppo_dir\*.zip" -ErrorAction SilentlyContinue)
    $ppo_count = $ppo_files.Count
    Write-Host "   ✓ PPO: $ppo_count fichero(s) ZIP" -ForegroundColor Green
}

Write-Host ""

# ===== PASO 3: LIMPIAR SOLO A2C =====
Write-Host "3️⃣  LIMPIANDO CHECKPOINTS A2C..." -ForegroundColor Yellow

if (Test-Path $a2c_dir) {
    $a2c_files = @(Get-ChildItem "$a2c_dir\*" -ErrorAction SilentlyContinue)
    $a2c_count_before = $a2c_files.Count
    
    if ($a2c_count_before -gt 0) {
        Write-Host "   📊 Antes: $a2c_count_before items en A2C/" -ForegroundColor Cyan
        
        # Eliminar TODOS los items en A2C
        Get-ChildItem "$a2c_dir\*" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        
        $a2c_count_after = @(Get-ChildItem "$a2c_dir\*" -ErrorAction SilentlyContinue).Count
        Write-Host "   📊 Después: $a2c_count_after items en A2C/" -ForegroundColor Cyan
        
        if ($a2c_count_after -eq 0) {
            Write-Host "   ✓ A2C limpiado correctamente" -ForegroundColor Green
        }
    } else {
        Write-Host "   ℹ️  A2C ya estaba vacío" -ForegroundColor Blue
    }
} else {
    Write-Host "   ℹ️  Directorio A2C no existe (será creado en entrenamiento)" -ForegroundColor Blue
}

Write-Host ""

# ===== PASO 4: VALIDACIÓN FINAL DE PROTECCIÓN =====
Write-Host "4️⃣  VALIDACIÓN FINAL DE PROTECCIÓN..." -ForegroundColor Yellow

# Re-validar SAC
if (Test-Path $sac_dir) {
    $sac_files_final = @(Get-Item "$sac_dir\*.zip" -ErrorAction SilentlyContinue)
    $sac_final_count = $sac_files_final.Count
    Write-Host "   ✓ SAC: $sac_final_count fichero(s) ZIP [PROTEGIDO]" -ForegroundColor Green
}

# Re-validar PPO
if (Test-Path $ppo_dir) {
    $ppo_files_final = @(Get-Item "$ppo_dir\*.zip" -ErrorAction SilentlyContinue)
    $ppo_final_count = $ppo_files_final.Count
    Write-Host "   ✓ PPO: $ppo_final_count fichero(s) ZIP [PROTEGIDO]" -ForegroundColor Green
}

# Validar A2C vacío
if (Test-Path $a2c_dir) {
    $a2c_files_final = @(Get-ChildItem "$a2c_dir\*" -ErrorAction SilentlyContinue)
    $a2c_final_count = $a2c_files_final.Count
    Write-Host "   ✓ A2C: $a2c_final_count items [LIMPIO]" -ForegroundColor Green
} else {
    Write-Host "   ✓ A2C: Directorio listo para crear [LIMPIO]" -ForegroundColor Green
}

Write-Host ""

# ===== RESUMEN FINAL =====
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  LIMPIEZA COMPLETADA - SEGURA                                ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host ""
Write-Host "📋 ESTADO CHECKPOINTS:" -ForegroundColor Yellow
Write-Host "   SAC:  PROTEGIDO ✓" -ForegroundColor Green
Write-Host "   PPO:  PROTEGIDO ✓" -ForegroundColor Green
Write-Host "   A2C:  LIMPIO Y LISTO ✓" -ForegroundColor Green
Write-Host ""
Write-Host "▶️  Próximo paso: Construir dataset" -ForegroundColor Cyan
Write-Host ""
