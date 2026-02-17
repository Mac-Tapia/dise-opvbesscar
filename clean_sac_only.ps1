#!/usr/bin/env powershell
# LIMPIEZA SAC SEGURA - SOLO SAC, PROTEGE A2C/PPO

Write-Host "`n" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host "LIMPIEZA SAC OPCION B - SEGURA Y VALIDADA" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host ""

# Colores
$Success = 'Green'
$Error = 'Red'
$Warning = 'Yellow'
$Info = 'Cyan'

# === FASE 1: VALIDAR ===
Write-Host "[1] Validando checkpoints..." -ForegroundColor $Info

$a2c_count = 0
$ppo_count = 0
$sac_count = 0

if (Test-Path 'checkpoints\A2C') {
    $a2c_files = @(Get-ChildItem 'checkpoints\A2C\*.zip' -ErrorAction SilentlyContinue)
    $a2c_count = $a2c_files.Count
}

if (Test-Path 'checkpoints\PPO') {
    $ppo_files = @(Get-ChildItem 'checkpoints\PPO\*.zip' -ErrorAction SilentlyContinue)
    $ppo_count = $ppo_files.Count
}

if (Test-Path 'checkpoints\SAC') {
    $sac_files = @(Get-ChildItem 'checkpoints\SAC\*.zip' -ErrorAction SilentlyContinue)
    $sac_count = $sac_files.Count
}

Write-Host "    [OK] A2C PROTEGIDO: $a2c_count checkpoint(s)" -ForegroundColor $Success
Write-Host "    [OK] PPO PROTEGIDO: $ppo_count checkpoint(s)" -ForegroundColor $Success
Write-Host "    [CLEAN] SAC PARA LIMPIAR: $sac_count checkpoint(s)" -ForegroundColor $Warning

# === FASE 2: LIMPIAR ===
Write-Host "`n[2] Limpiando SOLO SAC..." -ForegroundColor $Info

if ($sac_count -gt 0) {
    Remove-Item 'checkpoints\SAC\*.zip' -Force -ErrorAction SilentlyContinue
    Write-Host "    [OK] Checkpoints SAC eliminados" -ForegroundColor $Success
}

# Limpiar outputs SAC 
if (Test-Path 'outputs\sac_training') {
    Remove-Item 'outputs\sac_training\*.json' -Force -ErrorAction SilentlyContinue
    Remove-Item 'outputs\sac_training\*.csv' -Force -ErrorAction SilentlyContinue
    Write-Host "    [OK] Output files SAC eliminados" -ForegroundColor $Success
}

# === FASE 3: VALIDAR DESPUES ===
Write-Host "`n[3] Validando despues de limpieza..." -ForegroundColor $Info

$a2c_after = 0
$ppo_after = 0
$sac_after = 0

if (Test-Path 'checkpoints\A2C') {
    $a2c_after = @(Get-ChildItem 'checkpoints\A2C\*.zip' -ErrorAction SilentlyContinue).Count
}

if (Test-Path 'checkpoints\PPO') {
    $ppo_after = @(Get-ChildItem 'checkpoints\PPO\*.zip' -ErrorAction SilentlyContinue).Count
}

if (Test-Path 'checkpoints\SAC') {
    $sac_after = @(Get-ChildItem 'checkpoints\SAC\*.zip' -ErrorAction SilentlyContinue).Count
}

Write-Host "    A2C: $a2c_count -> $a2c_after (PROTEGIDO)" -ForegroundColor $Success
Write-Host "    PPO: $ppo_count -> $ppo_after (PROTEGIDO)" -ForegroundColor $Success
Write-Host "    SAC: $sac_count -> $sac_after (LIMPIO)" -ForegroundColor $Success

# === RESUMEN ===
Write-Host "`n" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host "[DONE] LIMPIEZA COMPLETADA" -ForegroundColor $Success
Write-Host ("="*70) -ForegroundColor Cyan
Write-Host ""

# Espacio liberado
if ($sac_count -gt 0) {
    Write-Host "  Eliminados: $sac_count checkpoint(s) SAC" -ForegroundColor $Warning
    Write-Host "  Protegido: $a2c_after A2C + $ppo_after PPO (intactos)" -ForegroundColor $Success
} else {
    Write-Host "  No habia checkpoints SAC para limpiar" -ForegroundColor $Info
}

Write-Host "`n"
