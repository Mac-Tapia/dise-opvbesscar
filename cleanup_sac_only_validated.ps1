#!/usr/bin/env pwsh
<#
.SYNOPSIS
    LIMPIEZA ULTRA-SEGURA: Elimina SOLO checkpoints SAC, PROTEGIENDO PPO y A2C
    
.DESCRIPTION
    Validación triple:
    1. Verifica que PPO y A2C existan y tengan archivos
    2. Lista archivos SAC que van a eliminarse
    3. Ejecuta eliminación SOLO si validación pasa
    4. Verifica post-limpieza que PPO/A2C siguen intactos
    
.NOTES
    Debe ejecutarse desde raíz del workspace
    Protección: No elimina si detecta anomalía
#>

# Configuración
$CHECKPOINT_DIR = "checkpoints"
$SAC_DIR = Join-Path $CHECKPOINT_DIR "SAC"
$PPO_DIR = Join-Path $CHECKPOINT_DIR "PPO"
$A2C_DIR = Join-Path $CHECKPOINT_DIR "A2C"

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  LIMPIEZA SEGURA: CHECKPOINTS SAC ONLY (Protegiendo PPO/A2C)  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ===== VALIDACION 1: Directorio de work =====
if (-not (Test-Path "scripts" -PathType Container)) {
    Write-Host "❌ ERROR: No está en raíz del workspace (falta carpeta 'scripts')" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Workspace validado" -ForegroundColor Green

# ===== VALIDACION 2: Checkpoints existen =====
if (-not (Test-Path $SAC_DIR)) {
    Write-Host "❌ ERROR: Directorio SAC no encontrado: $SAC_DIR" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $PPO_DIR)) {
    Write-Host "❌ ERROR: Directorio PPO no encontrado - PROTECCIÓN ACTIVADA" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $A2C_DIR)) {
    Write-Host "❌ ERROR: Directorio A2C no encontrado - PROTECCIÓN ACTIVADA" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Todos los directorios de agentes encontrados" -ForegroundColor Green

# ===== VALIDACION 3: Archivos en PPO y A2C (NO VACÍOS) =====
$ppo_count = (Get-ChildItem $PPO_DIR -Filter "*.zip" -ErrorAction SilentlyContinue).Count
$a2c_count = (Get-ChildItem $A2C_DIR -Filter "*.zip" -ErrorAction SilentlyContinue).Count

if ($ppo_count -eq 0) {
    Write-Host "❌ ERROR: PPO está VACÍO ($ppo_count archivos) - ANOMALÍA DETECTADA" -ForegroundColor Red
    exit 1
}
if ($a2c_count -eq 0) {
    Write-Host "❌ ERROR: A2C está VACÍO ($a2c_count archivos) - ANOMALÍA DETECTADA" -ForegroundColor Red
    exit 1
}
Write-Host "✓ PPO: $ppo_count checkpoints protegidos" -ForegroundColor Yellow
Write-Host "✓ A2C: $a2c_count checkpoints protegidos" -ForegroundColor Yellow

# ===== LISTAR ARCHIVOS SAC (PRE-LIMPIEZA) =====
Write-Host ""
Write-Host "Archivos SAC a ELIMINAR:" -ForegroundColor White
$sac_files = Get-ChildItem $SAC_DIR -Filter "*.zip" -ErrorAction SilentlyContinue
if ($sac_files.Count -eq 0) {
    Write-Host "  (directorio SAC ya está vacío)" -ForegroundColor Yellow
} else {
    $sac_files | ForEach-Object {
        Write-Host "  ✗ $($_.Name)" -ForegroundColor Red
    }
    Write-Host "  Total: $($sac_files.Count) archivos" -ForegroundColor Red
}

# ===== CONFIRMACIÓN INTERACTIVA =====
Write-Host ""
$confirm = Read-Host "¿Eliminar SOLO checkpoints SAC? (s/N, cualquier otra letra = cancelar)"
if ($confirm -ne "s") {
    Write-Host "❌ Operación cancelada por usuario" -ForegroundColor Yellow
    exit 0
}

# ===== LIMPIEZA: ELIMINAR SAC SOLO =====
Write-Host ""
Write-Host "Ejecutando limpieza SAC..." -ForegroundColor Cyan
try {
    $sac_files = Get-ChildItem $SAC_DIR -Filter "*.zip" -ErrorAction SilentlyContinue
    foreach ($file in $sac_files) {
        Remove-Item (Join-Path $SAC_DIR $file.Name) -Force -ErrorAction Stop
        Write-Host "  ✓ Eliminado: $($file.Name)" -ForegroundColor Green
    }
    Write-Host "✓ Limpieza SAC completada" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR durante eliminación: $_" -ForegroundColor Red
    exit 1
}

# ===== VALIDACION FINAL: Verificar integridad PPO/A2C =====
Write-Host ""
Write-Host "Validando integridad post-limpieza..." -ForegroundColor Cyan

$ppo_count_after = (Get-ChildItem $PPO_DIR -Filter "*.zip" -ErrorAction SilentlyContinue).Count
$a2c_count_after = (Get-ChildItem $A2C_DIR -Filter "*.zip" -ErrorAction SilentlyContinue).Count

if ($ppo_count_after -ne $ppo_count) {
    Write-Host "❌ CRÍTICO: PPO fue modificado! (antes: $ppo_count, ahora: $ppo_count_after)" -ForegroundColor Red
    exit 1
}
if ($a2c_count_after -ne $a2c_count) {
    Write-Host "❌ CRÍTICO: A2C fue modificado! (antes: $a2c_count, ahora: $a2c_count_after)" -ForegroundColor Red
    exit 1
}

Write-Host "✓ PPO: $ppo_count_after checkpoints intactos" -ForegroundColor Green
Write-Host "✓ A2C: $a2c_count_after checkpoints intactos" -ForegroundColor Green

# ===== RESUMEN FINAL =====
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✓ LIMPIEZA COMPLETADA CON ÉXITO                             ║" -ForegroundColor Green
Write-Host "╠════════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  SAC:  LIMPIO (listo para reentrenamiento)                    ║" -ForegroundColor Green
Write-Host "║  PPO:  PROTEGIDO ($ppo_count_after checkpoints)               ║" -ForegroundColor Green
Write-Host "║  A2C:  PROTEGIDO ($a2c_count_after checkpoints)               ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
