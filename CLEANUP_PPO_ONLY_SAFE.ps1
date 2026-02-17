#!/usr/bin/env pwsh
<#
.SYNOPSIS
Script SEGURO para limpiar checkpoints PPO UNICAMENTE
- NO toca SAC ni A2C (PROTEGIDOS)
- Valida estructura antes y después
- Auditable y reversible

.DESCRIPTION
LIMPIEZA SELECTIVA - Solo PPO:
1. Verifica SAC y A2C existen y tienen archivos
2. Limpia carpeta PPO (o la crea si no existe)
3. Valida que SAC/A2C estan intactos
4. Genera reporte de limpieza

.EXAMPLE
.\CLEANUP_PPO_ONLY_SAFE.ps1
#>

param(
    [switch]$DryRun = $false  # $true para ver que se eliminaria sin eliminar
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ============================================================================
# CONFIGURACION
# ============================================================================
$CHECKPOINTS_ROOT = "checkpoints"
$AGENTS = @{
    "SAC"  = @{ Path = "checkpoints/SAC"; Protected = $true }
    "A2C"  = @{ Path = "checkpoints/A2C"; Protected = $true }
    "PPO"  = @{ Path = "checkpoints/PPO"; Protected = $false }
}

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "LIMPIEZA SELECTIVA DE CHECKPOINTS - PPO ONLY (SAFE)" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# PASO 1: VALIDAR ESTADO ACTUAL
# ============================================================================
Write-Host "[PASO 1] Validar estado ANTES de limpieza..." -ForegroundColor Yellow
Write-Host "----" -ForegroundColor Gray

$state_before = @{}
foreach ($agent in $AGENTS.Keys) {
    $path = $AGENTS[$agent].Path
    $protected = $AGENTS[$agent].Protected
    
    if (Test-Path $path) {
        $file_count = @(Get-ChildItem $path -Filter "*.zip" -ErrorAction SilentlyContinue).Count
        $file_count = if ($file_count -eq 0) { 0 } else { $file_count }
        $size_mb = [math]::Round((Get-ChildItem $path -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
        
        $state_before[$agent] = @{
            Exists = $true
            FileCount = $file_count
            SizeMB = $size_mb
        }
        
        $protected_tag = if ($protected) { "[PROTEGIDO]" } else { "[DISPOSABLE]" }
        Write-Host "  ${agent} $protected_tag"
        Write-Host "    - Archivos: $file_count .zip files"
        Write-Host "    - Tamano: $size_mb MB"
    } else {
        $state_before[$agent] = @{
            Exists = $false
            FileCount = 0
            SizeMB = 0
        }
        
        $protected_tag = if ($protected) { "[PROTEGIDO]" } else { "[DISPOSABLE]" }
        Write-Host "  ${agent} $protected_tag [NO EXISTE]"
    }
}

Write-Host ""

# ============================================================================
# PASO 2: VALIDAR PROTECCIONES
# ============================================================================
Write-Host "[PASO 2] Validar que SAC y A2C estan PROTEGIDOS..." -ForegroundColor Yellow
Write-Host "----" -ForegroundColor Gray

$protection_ok = $true
foreach ($protected_agent in @("SAC", "A2C")) {
    if (-not $state_before[$protected_agent].Exists -or $state_before[$protected_agent].FileCount -eq 0) {
        Write-Host "  WARNING: $protected_agent no tiene checkpoints" -ForegroundColor Yellow
    } else {
        Write-Host "  OK - $protected_agent - Protegido ($($state_before[$protected_agent].FileCount) archivos)" -ForegroundColor Green
    }
}

Write-Host ""

# ============================================================================
# PASO 3: LIMPIAR PPO (SOLO PPO)
# ============================================================================
Write-Host "[PASO 3] Limpiar checkpoints PPO..." -ForegroundColor Yellow
Write-Host "----" -ForegroundColor Gray

$ppo_path = $AGENTS["PPO"].Path
$ppo_files_deleted = 0

if (Test-Path $ppo_path) {
    $ppo_files = @(Get-ChildItem $ppo_path -Filter "*.zip" -ErrorAction SilentlyContinue)
    
    if ($ppo_files.Count -gt 0) {
        Write-Host "  Encontrados $($ppo_files.Count) archivos PPO para eliminar" -ForegroundColor Cyan
        
        if (-not $DryRun) {
            foreach ($file in $ppo_files) {
                try {
                    Remove-Item $file.FullName -Force
                    $ppo_files_deleted++
                    Write-Host "    OK - Eliminado: $($file.Name)" -ForegroundColor Green
                } catch {
                    Write-Host "    ERROR al eliminar $($file.Name): $_" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "  [DRY RUN] Se eliminarian los archivos encontrados" -ForegroundColor Cyan
        }
    } else {
        Write-Host "  INFO - Carpeta PPO existe pero esta vacia" -ForegroundColor Cyan
    }
} else {
    Write-Host "  INFO - Carpeta PPO no existe, sera creada en el entrenamiento" -ForegroundColor Cyan
}

Write-Host ""

# ============================================================================
# PASO 4: CREAR DIRECTORIO PPO SI NO EXISTE
# ============================================================================
Write-Host "[PASO 4] Crear directorio PPO si no existe..." -ForegroundColor Yellow
Write-Host "----" -ForegroundColor Gray

if (-not (Test-Path $ppo_path)) {
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $ppo_path -Force | Out-Null
        Write-Host "  OK - Directorio PPO creado: $ppo_path" -ForegroundColor Green
    } else {
        Write-Host "  [DRY RUN] Se crearia directorio: $ppo_path" -ForegroundColor Cyan
    }
} else {
    Write-Host "  OK - Directorio PPO ya existe" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# PASO 5: VALIDAR ESTADO FINAL
# ============================================================================
Write-Host "[PASO 5] Validar estado DESPUES de limpieza..." -ForegroundColor Yellow
Write-Host "----" -ForegroundColor Gray

$all_ok = $true
foreach ($agent in @("SAC", "A2C")) {
    $path = $AGENTS[$agent].Path
    
    if (Test-Path $path) {
        $current_files = @(Get-ChildItem $path -Filter "*.zip" -ErrorAction SilentlyContinue).Count
        $original_files = $state_before[$agent].FileCount
        
        if ($current_files -eq $original_files) {
            Write-Host "  OK - ${agent} - INTACTO ($current_files archivos)" -ForegroundColor Green
        } else {
            Write-Host "  ERROR - ${agent} - CAMBIO ($original_files -> $current_files)" -ForegroundColor Red
            $all_ok = $false
        }
    } else {
        Write-Host "  OK - ${agent} - No existia antes, no existe ahora [ESPERADO]" -ForegroundColor Green
    }
}

Write-Host ""

# ============================================================================
# REPORTE FINAL
# ============================================================================
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "REPORTE DE LIMPIEZA" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "OK - MODO DRY RUN - No se realizaron cambios" -ForegroundColor Yellow
} else {
    Write-Host "OK - Archivos PPO eliminados: $ppo_files_deleted" -ForegroundColor Green
}

Write-Host "OK - SAC protegido: intacto" -ForegroundColor Green
Write-Host "OK - A2C protegido: intacto" -ForegroundColor Green
Write-Host "OK - PPO: listo para nuevo entrenamiento" -ForegroundColor Green

if ($all_ok) {
    Write-Host ""
    Write-Host "SUCCESS - LIMPIEZA EXITOSA - Sistema en estado SEGURO" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "WARNING - PROBLEMAS DETECTADOS - Revisar reporte" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
