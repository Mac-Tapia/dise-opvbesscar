#!/usr/bin/env powershell
# Script de limpieza segura A2C v7.1
# Valida protección de SAC y PPO

Write-Host '╔═══════════════════════════════════════════════════════════════╗' -ForegroundColor Cyan
Write-Host '║  LIMPIEZA A2C SEGURA - Protegiendo SAC y PPO               ║' -ForegroundColor Cyan
Write-Host '╚═══════════════════════════════════════════════════════════════╝' -ForegroundColor Cyan
Write-Host ''

# Validar que SAC y PPO existen ANTES
$sac_files_before = @(Get-ChildItem 'checkpoints/SAC/*.zip' -ErrorAction SilentlyContinue).Count
$ppo_files_before = @(Get-ChildItem 'checkpoints/PPO/*.zip' -ErrorAction SilentlyContinue).Count

Write-Host 'ANTES DE LIMPIAR:' -ForegroundColor Yellow
Write-Host "  SAC: $sac_files_before ficheros ZIP" -ForegroundColor Green
Write-Host "  PPO: $ppo_files_before ficheros ZIP" -ForegroundColor Green
Write-Host "  A2C: $((@(Get-ChildItem 'checkpoints/A2C/*.zip' -ErrorAction SilentlyContinue).Count)) ficheros ZIP" -ForegroundColor Yellow
Write-Host ''

# Limpiar SOLO A2C
if (Test-Path 'checkpoints/A2C') {
    Write-Host 'Limpiando A2C...' -ForegroundColor Yellow
    Get-ChildItem 'checkpoints/A2C' -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host '  ✓ A2C limpiado' -ForegroundColor Green
}

Write-Host ''

# Validar que SAC y PPO siguen intactos DESPUÉS
$sac_files_after = @(Get-ChildItem 'checkpoints/SAC/*.zip' -ErrorAction SilentlyContinue).Count
$ppo_files_after = @(Get-ChildItem 'checkpoints/PPO/*.zip' -ErrorAction SilentlyContinue).Count

Write-Host 'DESPUÉS DE LIMPIAR:' -ForegroundColor Yellow
Write-Host "  SAC: $sac_files_after ficheros ZIP" -ForegroundColor Green
Write-Host "  PPO: $ppo_files_after ficheros ZIP" -ForegroundColor Green
Write-Host "  A2C: $((@(Get-ChildItem 'checkpoints/A2C/*.zip' -ErrorAction SilentlyContinue).Count)) ficheros ZIP" -ForegroundColor Yellow
Write-Host ''

# Validación final
if ($sac_files_after -eq $sac_files_before -and $ppo_files_after -eq $ppo_files_before) {
    Write-Host '════════════════════════════════════════════════════════════════' -ForegroundColor Green
    Write-Host 'VALIDACION: SAC y PPO PROTEGIDOS ✓' -ForegroundColor Green
    Write-Host '════════════════════════════════════════════════════════════════' -ForegroundColor Green
    exit 0
} else {
    Write-Host '════════════════════════════════════════════════════════════════' -ForegroundColor Red
    Write-Host 'ERROR: SAC o PPO fueron modificados durante limpieza' -ForegroundColor Red
    Write-Host "  SAC: $sac_files_before → $sac_files_after" -ForegroundColor Red
    Write-Host "  PPO: $ppo_files_before → $ppo_files_after" -ForegroundColor Red
    Write-Host '════════════════════════════════════════════════════════════════' -ForegroundColor Red
    exit 1
}
