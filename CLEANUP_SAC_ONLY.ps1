# -*- coding: utf-8 -*-
# LIMPIEZA SEGURA DE CHECKPOINTS - SOLO SAC, PROTEGER PPO/A2C

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   LIMPIEZA SEGURA DE CHECKPOINTS - PROTEGER PPO/A2C, LIMPIAR SAC" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# PASO 1: VALIDACION PRE-LIMPIEZA
Write-Host "[1] VALIDACION PRE-LIMPIEZA" -ForegroundColor Yellow
Write-Host ""

$checkpoint_base = "d:\diseñopvbesscar\checkpoints"
$sac_dir = Join-Path $checkpoint_base "SAC"
$ppo_dir = Join-Path $checkpoint_base "PPO"
$a2c_dir = Join-Path $checkpoint_base "A2C"

Write-Host "    Directorios esperados:" -ForegroundColor White
Write-Host "    - SAC: $(if (Test-Path $sac_dir) { 'OK' } else { 'NO EXISTE' })"
Write-Host "    - PPO: $(if (Test-Path $ppo_dir) { 'OK' } else { 'NO EXISTE' })"
Write-Host "    - A2C: $(if (Test-Path $a2c_dir) { 'OK' } else { 'NO EXISTE' })"
Write-Host ""

# PASO 2: LISTAR CONTENIDO ACTUAL
Write-Host "[2] CONTENIDO ACTUAL" -ForegroundColor Yellow
Write-Host ""

if (Test-Path $sac_dir) {
    $sac_files = @(Get-ChildItem -Path $sac_dir -Force)
    Write-Host "    SAC: $($sac_files.Count) elementos"
    if ($sac_files.Count -gt 0) {
        foreach ($file in $sac_files | Select-Object -First 5) {
            Write-Host "      - $($file.Name)"
        }
        if ($sac_files.Count -gt 5) {
            Write-Host "      ... y $($sac_files.Count - 5) mas"
        }
    }
} else {
    Write-Host "    SAC no existe - se creara"
}

Write-Host ""

if (Test-Path $ppo_dir) {
    $ppo_files = @(Get-ChildItem -Path $ppo_dir -Force)
    Write-Host "    PPO: $($ppo_files.Count) elementos [PROTEGIDO]" -ForegroundColor Green
}

if (Test-Path $a2c_dir) {
    $a2c_files = @(Get-ChildItem -Path $a2c_dir -Force)
    Write-Host "    A2C: $($a2c_files.Count) elementos [PROTEGIDO]" -ForegroundColor Green
}

Write-Host ""

# PASO 3: CONFIRMACION
Write-Host "[3] CONFIRMACION" -ForegroundColor Yellow
Write-Host ""
Write-Host "    ACCIONES A REALIZAR:"
Write-Host "    - Limpiar SOLO directorio SAC"
Write-Host "    - PROTEGER PPO (no modificar)"
Write-Host "    - PROTEGER A2C (no modificar)"
Write-Host ""

$response = Read-Host "    Continuar con limpieza de SAC? (s/n)"

if ($response -ne "s") {
    Write-Host ""
    Write-Host "    CANCELADO" -ForegroundColor Red
    exit 0
}

Write-Host ""

# PASO 4: LIMPIEZA SAC
Write-Host "[4] LIMPIEZA DE SAC" -ForegroundColor Yellow
Write-Host ""

try {
    if (Test-Path $sac_dir) {
        $items = Get-ChildItem -Path $sac_dir -Force -ErrorAction SilentlyContinue
        $count = 0
        
        foreach ($item in $items) {
            try {
                if ($item.PSIsContainer) {
                    Remove-Item -Path $item.FullPath -Recurse -Force
                    Write-Host "    - Eliminado dir: $($item.Name)"
                } else {
                    Remove-Item -Path $item.FullPath -Force
                    Write-Host "    - Eliminado archivo: $($item.Name)"
                }
                $count++
            } catch {
                Write-Host "    ERROR eliminar $($item.Name): $_" -ForegroundColor Red
            }
        }
        
        Write-Host ""
        Write-Host "    Total eliminados: $count" -ForegroundColor Green
    } else {
        Write-Host "    SAC no existe - creando..." -ForegroundColor White
        New-Item -ItemType Directory -Path $sac_dir -Force | Out-Null
    }
    
} catch {
    Write-Host "    ERROR: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# PASO 5: VALIDACION POST-LIMPIEZA
Write-Host "[5] VALIDACION POST-LIMPIEZA" -ForegroundColor Yellow
Write-Host ""

$sac_after = @(Get-ChildItem -Path $sac_dir -Force -ErrorAction SilentlyContinue)
Write-Host "    SAC limpio: $($sac_after.Count) elementos" -ForegroundColor Green

if (Test-Path $ppo_dir) {
    $ppo_after = @(Get-ChildItem -Path $ppo_dir -Force)
    Write-Host "    PPO protegido: $($ppo_after.Count) elementos intactos" -ForegroundColor Green
}

if (Test-Path $a2c_dir) {
    $a2c_after = @(Get-ChildItem -Path $a2c_dir -Force)
    Write-Host "    A2C protegido: $($a2c_after.Count) elementos intactos" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "   OK - LIMPIEZA COMPLETADA EXITOSAMENTE" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""

exit 0
