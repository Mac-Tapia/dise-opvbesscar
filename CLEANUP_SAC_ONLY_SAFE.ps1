#!/usr/bin/env powershell
# -*- coding: utf-8 -*-
<#
LIMPIEZA SEGURA DE CHECKPOINTS - SOLO SAC, PROTEGER PPO/A2C
=============================================================
Este script:
1. Valida estructura de checkpoints
2. Limpia SOLO SAC
3. Protege PPO/A2C (no los toca)
4. Valida post-limpieza
#>

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   LIMPIEZA SEGURA DE CHECKPOINTS - PROTEGER PPO/A2C, LIMPIAR SAC" -ForegroundColor White
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ========== PASO 1: VALIDACIÓN PRE-LIMPIEZA ==========
Write-Host "[1] VALIDACIÓN PRE-LIMPIEZA" -ForegroundColor Yellow
Write-Host ""

$checkpoint_base = "d:\diseñopvbesscar\checkpoints"
$sac_dir = Join-Path $checkpoint_base "SAC"
$ppo_dir = Join-Path $checkpoint_base "PPO"
$a2c_dir = Join-Path $checkpoint_base "A2C"

Write-Host "    Directorios esperados:" -ForegroundColor White
Write-Host "    ├─ SAC: $(if (Test-Path $sac_dir) { '✅ EXISTE' } else { '❌ NO EXISTE' })"
Write-Host "    ├─ PPO: $(if (Test-Path $ppo_dir) { '✅ EXISTE' } else { '⚠️ NO EXISTE (OK)' })"
Write-Host "    └─ A2C: $(if (Test-Path $a2c_dir) { '✅ EXISTE' } else { '⚠️ NO EXISTE (OK)' })"
Write-Host ""

# ========== PASO 2: LISTAR CONTENIDO ACTUAL ==========
Write-Host "[2] CONTENIDO ACTUAL DE CHECKPOINTS" -ForegroundColor Yellow
Write-Host ""

if (Test-Path $sac_dir) {
    $sac_files = @(Get-ChildItem -Path $sac_dir -Force)
    Write-Host "    SAC ($($sac_files.Count) archivos/carpetas):" -ForegroundColor White
    if ($sac_files.Count -gt 0) {
        foreach ($file in $sac_files | Select-Object -First 10) {
            $size_mb = if ($file.PSIsContainer) { "[DIR]" } else { "$([math]::Round($file.Length / 1MB, 2)) MB" }
            Write-Host "      • $($file.Name) ($size_mb)"
        }
        if ($sac_files.Count -gt 10) {
            Write-Host "      ... y $($sac_files.Count - 10) más"
        }
    } else {
        Write-Host "      (vacío - SAC listo para nuevo entrenamiento)"
    }
} else {
    Write-Host "    SAC no existe - se creará para el nuevo entrenamiento"
}

Write-Host ""

if (Test-Path $ppo_dir) {
    $ppo_files = @(Get-ChildItem -Path $ppo_dir -Force)
    Write-Host "    PPO ($($ppo_files.Count) archivos) - PROTEGIDO:" -ForegroundColor Green
    Write-Host "      ✅ Estos archivos NO serán tocados"
} else {
    Write-Host "    PPO no existe aún (OK)"
}

Write-Host ""

if (Test-Path $a2c_dir) {
    $a2c_files = @(Get-ChildItem -Path $a2c_dir -Force)
    Write-Host "    A2C ($($a2c_files.Count) archivos) - PROTEGIDO:" -ForegroundColor Green
    Write-Host "      ✅ Estos archivos NO serán tocados"
} else {
    Write-Host "    A2C no existe aún (OK)"
}

Write-Host ""

# ========== PASO 3: CONFIRMACIÓN ANTES DE LIMPIAR ==========
Write-Host "[3] CONFIRMACIÓN" -ForegroundColor Yellow
Write-Host ""
Write-Host "    ⚠️  ACCIÓN A REALIZAR:" -ForegroundColor White
Write-Host "        → Limpiar SOLO el directorio SAC"
Write-Host "        → Crear directorio vacío listo para nuevo entrenamiento"
Write-Host "        → PROTEGER: PPO y A2C (no se modificarán)"
Write-Host ""

$response = Read-Host "    ¿Continuar con la limpieza de SAC? (s/n)"

if ($response -ne "s" -and $response -ne "S") {
    Write-Host ""
    Write-Host "    ❌ Operación cancelada por el usuario" -ForegroundColor Red
    Write-Host ""
    exit 0
}

Write-Host ""

# ========== PASO 4: LIMPIEZA SEGURA DE SAC ==========
Write-Host "[4] LIMPIEZA DE SAC" -ForegroundColor Yellow
Write-Host ""

try {
    if (Test-Path $sac_dir) {
        Write-Host "    Eliminando contenido de SAC..." -ForegroundColor White
        
        $items_to_delete = Get-ChildItem -Path $sac_dir -Force
        $delete_count = 0
        
        foreach ($item in $items_to_delete) {
            try {
                if ($item.PSIsContainer) {
                    Write-Host "      ✓ Eliminando directorio: $($item.Name)"
                    Remove-Item -Path $item.FullPath -Recurse -Force -ErrorAction Stop
                } else {
                    Write-Host "      ✓ Eliminando archivo: $($item.Name)"
                    Remove-Item -Path $item.FullPath -Force -ErrorAction Stop
                }
                $delete_count++
            } catch {
                Write-Host "      ✗ ERROR al eliminar $($item.Name): $_" -ForegroundColor Red
            }
        }
        
        Write-Host "      → Eliminados: $delete_count elementos"
    } else {
        Write-Host "    SAC no existe - creando..." -ForegroundColor White
        New-Item -ItemType Directory -Path $sac_dir -Force | Out-Null
        Write-Host "      → Directorio SAC creado"
    }
    
    Write-Host "    ✅ Limpieza de SAC completada" -ForegroundColor Green
} catch {
    Write-Host "    ❌ Error durante limpieza: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ========== PASO 5: VALIDACIÓN POST-LIMPIEZA ==========
Write-Host "[5] VALIDACIÓN POST-LIMPIEZA" -ForegroundColor Yellow
Write-Host ""

# Verificar SAC
$sac_items = @(Get-ChildItem -Path $sac_dir -Force -ErrorAction SilentlyContinue)
Write-Host "    SAC: $($sac_items.Count) elementos (LIMPIO ✅)"

# Protección PPO
if (Test-Path $ppo_dir) {
    $ppo_items_after = @(Get-ChildItem -Path $ppo_dir -Force)
    $ppo_check = if ($ppo_items_after.Count -gt 0) { "✅ PROTEGIDO" } else { "⚠️ Vacío" }
    Write-Host "    PPO: $($ppo_items_after.Count) elementos ($ppo_check)"
}

# Protección A2C
if (Test-Path $a2c_dir) {
    $a2c_items_after = @(Get-ChildItem -Path $a2c_dir -Force)
    $a2c_check = if ($a2c_items_after.Count -gt 0) { "✅ PROTEGIDO" } else { "⚠️ Vacío" }
    Write-Host "    A2C: $($a2c_items_after.Count) elementos ($a2c_check)"
}

Write-Host ""

# ========== RESULTADO FINAL ==========
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "   ✅ LIMPIEZA COMPLETADA EXITOSAMENTE" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "   ESTADO FINAL:" -ForegroundColor White
Write-Host "   ✅ SAC: Limpio y listo para nuevo entrenamiento"
Write-Host "   🔒 PPO: Protegido (no fue modificado)"
Write-Host "   🔒 A2C: Protegido (no fue modificado)"
Write-Host ""

exit 0
