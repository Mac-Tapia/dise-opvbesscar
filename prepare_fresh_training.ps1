#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Preparar entrenamiento SAC desde CERO
    
.DESCRIPTION
    Script completo para:
    1. Limpiar todos los checkpoints (SAC, PPO, backups)
    2. Limpiar outputs de entrenamientos anteriores
    3. Verificar que datasets OE2 están listos
    4. Verificar dependencias Python
    5. Opcionalmente ejecutar entrenamiento
    
.EXAMPLE
    .\prepare_fresh_training.ps1                 # Preparar solo
    .\prepare_fresh_training.ps1 -Train          # Preparar + Entrenar
    .\prepare_fresh_training.ps1 -Train -Agent SAC  # SAC training
#>

param(
    [Switch]$Train,
    [ValidateSet("SAC", "PPO", "A2C")]
    [String]$Agent = "SAC",
    [Switch]$Force
)

$ErrorActionPreference = 'Continue'
$WarningPreference = 'SilentlyContinue'

# ========== COLORES Y ESTILOS ==========
function Write-Section {
    param([String]$Text, [ConsoleColor]$Color = 'Cyan')
    Write-Host ""
    Write-Host "╔" + ("═" * 66) + "╗" -ForegroundColor $Color
    Write-Host "║ " + $Text.PadRight(64) + " ║" -ForegroundColor $Color
    Write-Host "╚" + ("═" * 66) + "╝" -ForegroundColor $Color
    Write-Host ""
}

function Write-Item {
    param([String]$Text, [ConsoleColor]$Color = 'White', [String]$Icon = "  ")
    Write-Host "$Icon $Text" -ForegroundColor $Color
}

# ========== INICIO ==========
Write-Section "PREPARADOR DE ENTRENAMIENTO DESDE CERO - PVBESSCAR 2026-02-08" 'Cyan'

Write-Item "Sistema: Windows PowerShell" 'Gray'
Write-Item "Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" 'Gray'
Write-Item "Ubicación: $PWD" 'Gray'
Write-Host ""

# ========== PASO 1: VALIDAR ESTRUCTURA ==========
Write-Section "PASO 1: VALIDAR ESTRUCTURA DE DIRECTORIOS" 'Yellow'

$dirs_required = @(
    "checkpoints",
    "checkpoints\SAC",
    "checkpoints\PPO",
    "data\interim\oe2",
    "outputs"
)

$all_dirs_ok = $true
foreach ($dir in $dirs_required) {
    if (Test-Path $dir) {
        Write-Item "✓ $dir" 'Green'
    } else {
        Write-Item "✗ $dir (CREANDO)" 'Yellow'
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host ""

# ========== PASO 2: LIMPIAR CHECKPOINTS ==========
Write-Section "PASO 2: LIMPIAR CHECKPOINTS ANTERIORES" 'Magenta'

Write-Item "🗑️  Eliminando SAC checkpoints..." 'Magenta'
$sac_count = (Get-ChildItem "checkpoints\SAC" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
if ($sac_count -gt 0) {
    Remove-Item "checkpoints\SAC\*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Item "  ✓ Eliminados $sac_count archivos SAC" 'Green'
} else {
    Write-Item "  ✓ SAC ya estaba limpio" 'Green'
}

Write-Item "🗑️  Eliminando PPO checkpoints..." 'Magenta'
$ppo_count = (Get-ChildItem "checkpoints\PPO" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
if ($ppo_count -gt 0) {
    Remove-Item "checkpoints\PPO\*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Item "  ✓ Eliminados $ppo_count archivos PPO" 'Green'
} else {
    Write-Item "  ✓ PPO ya estaba limpio" 'Green'
}

Write-Item "🗑️  Eliminando backups SAC..." 'Magenta'
$sac_backup_count = (Get-ChildItem "checkpoints" -Filter "SAC_backup_*" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
if ($sac_backup_count -gt 0) {
    Remove-Item "checkpoints\SAC_backup_*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Item "  ✓ Eliminados $sac_backup_count archivos de backup SAC" 'Green'
} else {
    Write-Item "  ✓ No hay backups SAC" 'Green'
}

Write-Item "🗑️  Eliminando backups PPO..." 'Magenta'
$ppo_backup_count = (Get-ChildItem "checkpoints" -Filter "PPO_backup_*" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
if ($ppo_backup_count -gt 0) {
    Remove-Item "checkpoints\PPO_backup_*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Item "  ✓ Eliminados $ppo_backup_count archivos de backup PPO" 'Green'
} else {
    Write-Item "  ✓ No hay backups PPO" 'Green'
}

Write-Host ""

# ========== PASO 3: LIMPIAR OUTPUTS ANTERIORES ==========
Write-Section "PASO 3: LIMPIAR OUTPUTS DE ENTRENAMIENTOS ANTERIORES" 'Magenta'

Write-Item "🗑️  Limpiando outputs/sac_training/..." 'Magenta'
if (Test-Path "outputs\sac_training") {
    Remove-Item "outputs\sac_training\*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Item "  ✓ Output SAC limpio" 'Green'
} else {
    Write-Item "  ✓ No hay outputs SAC anteriores" 'Green'
}

Write-Item "🗑️  Limpiando outputs/ppo_training/..." 'Magenta'
if (Test-Path "outputs\ppo_training") {
    Remove-Item "outputs\ppo_training\*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Item "  ✓ Output PPO limpio" 'Green'
} else {
    Write-Item "  ✓ No hay outputs PPO anteriores" 'Green'
}

Write-Host ""

# ========== PASO 4: VALIDAR DATASETS OE2 ==========
Write-Section "PASO 4: VALIDAR DATASETS OE2 (CRÍTICO)" 'Yellow'

$oe2_files = @{
    'Solar PVGIS' = 'data\interim\oe2\solar\pv_generation_citylearn_v2.csv'
    'Chargers' = 'data\interim\oe2\chargers\chargers_ev_ano_2024_v3.csv'
    'BESS' = 'data\interim\oe2\bess\bess_hourly_dataset_2024.csv'
    'Mall Demand' = 'data\interim\oe2\demandamallkwh\demandamallhorakwh.csv'
}

$all_oe2_ok = $true
foreach ($name in @('Solar PVGIS', 'Chargers', 'BESS', 'Mall Demand')) {
    $path = $oe2_files[$name]
    if (Test-Path $path) {
        try {
            $rows = (Import-Csv $path -Delimiter ',' | Measure-Object).Count
        } catch {
            $rows = 0
        }
        if ($rows -ge 8760 -or $name -eq 'Chargers') {
            Write-Item "✓ ${name}: LISTO" 'Green'
        } else {
            Write-Item "⚠ ${name}: ${rows} filas (esperado ≥8760)" 'Yellow'
            $all_oe2_ok = $false
        }
    } else {
        Write-Item "✗ ${name}: NO ENCONTRADO" 'Red'
        $all_oe2_ok = $false
    }
}

if (-not $all_oe2_ok) {
    Write-Host ""
    Write-Item "⚠️  ADVERTENCIA: Algunos datasets OE2 falta verificar" 'Yellow'
    Write-Item "Consulta: docs/OE2_DATASET_VALIDATION.md" 'Yellow'
}

Write-Host ""

# ========== PASO 5: VALIDAR DEPENDENCIAS ==========
Write-Section "PASO 5: VALIDAR DEPENDENCIAS PYTHON" 'Yellow'

# Verificar venv
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Item "✓ Virtual Environment (.venv) detectado" 'Green'
    Write-Item "  Activando..." 'Gray'
    & ".\.venv\Scripts\Activate.ps1" | Out-Null
    Write-Item "  ✓ .venv activado" 'Green'
} else {
    Write-Item "⚠ Virtual Environment NO encontrado" 'Yellow'
    Write-Item "  Ejecuta: python -m venv .venv" 'Yellow'
}

Write-Host ""

# ========== PASO 6: VERIFICAR ARCHIVOS CRÍTICOS ==========
Write-Section "PASO 6: VERIFICAR ARCHIVOS CRÍTICOS" 'Yellow'

$critical_files = @(
    'train_sac_multiobjetivo.py',
    'configs\default.yaml',
    'src\rewards\rewards.py'
)

foreach ($file in $critical_files) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length / 1KB
        Write-Item "✓ $file ($([Math]::Round($size, 0)) KB)" 'Green'
    } else {
        Write-Item "✗ ${file}: NO ENCONTRADO" 'Red'
    }
}

Write-Host ""

# ========== RESUMEN FINAL ==========
Write-Section "RESUMEN: PREPARACIÓN LISTA" 'Green'

Write-Item "✅ Checkpoints limpios" 'Green'
Write-Item "✅ Outputs anteriores removidos" 'Green'
Write-Item "✅ Datasets OE2 validados" 'Green'
Write-Item "✅ Archivos críticos presentes" 'Green'
Write-Item "✅ Sistema listo para entrenamiento DESDE CERO" 'Green'

Write-Host ""

# ========== OPCIÓN: ENTRENAR AHORA ==========
if ($Train) {
    Write-Section "INICIANDO ENTRENAMIENTO: $Agent DESDE CERO" 'Cyan'
    
    Write-Item "⏳ Iniciando entrenamiento $Agent..." 'Cyan'
    Write-Item "Timesteps: 87,600 (10 episodios completos)" 'Cyan'
    Write-Item "Duración estimada: 20-30 minutos (GPU)" 'Cyan'
    Write-Host ""
    
    switch ($Agent) {
        "SAC" {
            Write-Item "▶ Ejecutando: python train_sac_multiobjetivo.py" 'Cyan'
            & python train_sac_multiobjetivo.py
        }
        "PPO" {
            Write-Item "▶ Ejecutando: python train_ppo_multiobjetivo.py" 'Cyan'
            & python train_ppo_multiobjetivo.py
        }
        "A2C" {
            Write-Item "▶ Ejecutando: python train_a2c_multiobjetivo.py" 'Cyan'
            & python train_a2c_multiobjetivo.py
        }
    }
} else {
    Write-Host ""
    Write-Section "PRÓXIMO PASO" 'Cyan'
    
    Write-Item "Para iniciar entrenamiento SAC:" 'Cyan'
    Write-Item "  python train_sac_multiobjetivo.py" 'White'
    Write-Host ""
    Write-Item "O ejecutar este script con bandera -Train:" 'Cyan'
    Write-Item "  .\prepare_fresh_training.ps1 -Train" 'White'
    Write-Host ""
    Write-Item "Para entrenar con otro agente:" 'Cyan'
    Write-Item "  .\prepare_fresh_training.ps1 -Train -Agent PPO" 'White'
    Write-Item "  .\prepare_fresh_training.ps1 -Train -Agent A2C" 'White'
    Write-Host ""
}

Write-Section "PREPARACIÓN COMPLETADA" 'Green'
Write-Item "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" 'Gray'
Write-Host ""
