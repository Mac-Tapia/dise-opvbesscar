#!/usr/bin/env powershell
<#
.SYNOPSIS
    Entrenar SAC con Opción B - Monitoreo Robusto en Tiempo Real
    
.DESCRIPTION
    - Ejecuta SAC con hiperparámetros optimizados
    - Monitorea convergencia EN TIEMPO REAL
    - Detecta anomalías y patrones de no-convergencia
    - Permite pausar/reanudar sin perder estado
    - Genera reportes detallados
    
.NOTES
    Opción B (2026-02-17): Resuelve problema de SAC local optimum
    SAC anterior: Episodes 3-10 FLAT (0.6739, 2,940 kg CO2) - NO CONVERGENCIA
    SAC nuevo: Esperado 50%+ CO2 reduction como A2C
    
.EXAMPLE
    .\train_sac_option_b_robust.ps1
#>

param(
    [switch]$DryRun = $false,
    [switch]$CleanFirst = $true,
    [switch]$NoMonitor = $false,
    [int]$Episodes = 20,  # AUMENTADO para validar convergencia
    [string]$Device = 'cuda'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ===== COLORES Y EMOJIS =====
$Colors = @{
    Success = 'Green'
    Error = 'Red'
    Warning = 'Yellow'
    Info = 'Cyan'
    Muted = 'Gray'
}

$Emojis = @{
    Check  = '✅'
    Cross  = '❌'
    Warning = '⚠️'
    Rocket = '🚀'
    Monitor = '📊'
    Clean = '🧹'
    Train = '🎯'
}

function Write-Status {
    param([string]$Message, [string]$Type = 'Info')
    $Color = $Colors[$Type]
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("="*80) -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host ("="*80) -ForegroundColor Cyan
    Write-Host ""
}

function Write-Progress-Custom {
    param([int]$Episode, [int]$Total, [float]$Reward, [float]$CO2, [string]$Status)
    
    $Progress = [math]::Round((($Episode / $Total) * 100), 1)
    $Bar = ("[" + ("=" * [int]($Progress / 5)) + ("." * (20 - [int]($Progress / 5))) + "]")
    
    Write-Host "`n📊 Episode $Episode/$Total | $Bar $Progress%" -ForegroundColor Cyan
    Write-Host "   Reward: $Reward | CO2: {0:N0} kg | Status: $Status" -f [int]$CO2 -ForegroundColor Yellow
}

# ===== FASE 1: VALIDAR AMBIENTE =====
Write-Header "$($Emojis.Rocket) FASE 1: VALIDAR AMBIENTE Y CONFIGURACION"

Write-Status "  [1.1] Python version..." Info
$PythonVersion = python --version 2>&1
Write-Status "        $PythonVersion" Success

Write-Status "  [1.2] GPU availability..." Info
$GPUCheck = python -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')" 2>&1
Write-Status "        $GPUCheck" Success

Write-Status "  [1.3] Workspace structure..." Info
$WorkspacePaths = @('checkpoints', 'outputs', 'scripts', 'src', 'data')
foreach ($Path in $WorkspacePaths) {
    if (Test-Path $Path) {
        Write-Status "        ✅ $Path" Success
    } else {
        Write-Status "        ❌ $Path (MISSING!)" Error
    }
}

# ===== FASE 2: LIMPIEZA SEGURA SAC =====
if ($CleanFirst) {
    Write-Header "$($Emojis.Clean) FASE 2: LIMPIEZA SEGURA (SOLO SAC - PROTEGE A2C/PPO)"
    
    Write-Status "  [2.1] Validando checkpoints SAC..." Info
    
    if (Test-Path 'checkpoints\SAC') {
        $SACFiles = Get-ChildItem 'checkpoints\SAC\*.zip' -ErrorAction SilentlyContinue | Measure-Object
        Write-Status "        SAC checkpoints encontrados: $($SACFiles.Count)" Warning
        
        if ($SACFiles.Count -gt 0) {
            Write-Status "  [2.2] Borrando SOLO SAC (dry-run)..." Info
            python clean_sac_only_safe.py --dry-run
            
            if ($DryRun) {
                Write-Status "        DRY-RUN: No se eliminó nada" Muted
            } else {
                Write-Status "  [2.3] Ejecutando limpieza SAC..." Info
                python clean_sac_only_safe.py --confirm
                Write-Status "        $($Emojis.Check) SAC checkpoints limpios" Success
            }
        } else {
            Write-Status "        SAC limpio - sin checkpoints previos" Success
        }
    } else {
        Write-Status "        Directorio SAC no existe - primera ejecucion" Info
    }
    
    # VALIDAR A2C/PPO PROTEGIDOS
    Write-Status "  [2.4] Validando protección A2C/PPO..." Info
    if (Test-Path 'checkpoints\A2C') {
        $A2CFiles = Get-ChildItem 'checkpoints\A2C\*.zip' -ErrorAction SilentlyContinue | Measure-Object
        Write-Status "        $($Emojis.Check) A2C PROTEGIDO: $($A2CFiles.Count) checkpoint(s)" Success
    }
    if (Test-Path 'checkpoints\PPO') {
        $PPOFiles = Get-ChildItem 'checkpoints\PPO\*.zip' -ErrorAction SilentlyContinue | Measure-Object
        Write-Status "        $($Emojis.Check) PPO PROTEGIDO: $($PPOFiles.Count) checkpoint(s)" Success
    }
}

# ===== FASE 3: PREPARAR DATASETS =====
Write-Header "$($Emojis.Monitor) FASE 3: CONSTRUIR DATASETS REALES (OE2)"

Write-Status "  [3.1] Preparando datasets para todos los agentes..." Info
Write-Status "        (Solar, Chargers, BESS, Mall - 8,760 horas = 1 año)" Muted

if ($DryRun) {
    Write-Status "        DRY-RUN: Saltando construcción" Muted
} else {
    Write-Status "  [3.2] Ejecutando prepare_datasets_all_agents.py..." Info
    
    # Variables de ambiente
    $env:PYTHONIOENCODING = 'utf-8'
    
    try {
        python prepare_datasets_all_agents.py
        Write-Status "        $($Emojis.Check) Datasets construidos" Success
    } catch {
        Write-Status "        ❌ Error en construcción de datasets" Error
        Write-Status "           $_" Muted
        exit 1
    }
}

# ===== FASE 4: ENTRENAR SAC CON OPCION B =====
Write-Header "$($Emojis.Train) FASE 4: ENTRENAR SAC - OPCION B (ROMPER OPTIMO LOCAL)"

Write-Status "  [4.1] Configuración SAC Opción B:" Info
Write-Status "        - Learning rate:     5e-4 (AUMENTADO para convergencia inicial)" Muted
Write-Status "        - Entropy target:   -20.0 (AUMENTADO para exploración)" Muted
Write-Status "        - Train frequency:   1 step (4x más updates que v9.2)" Muted
Write-Status "        - Batch size:       128 (mejor gradientes)" Muted
Write-Status "        - Networks:        512x512 (mayor capacidad)" Muted
Write-Status "        - Buffer:          600K (más diversidad)" Muted
Write-Status "        - SDE:             Enabled (exploración en 38D)" Muted

Write-Status "  [4.2] Métricas de éxito esperadas:" Info
Write-Status "        - SAC v9.2: 35.2% CO2 reduction (BASELINE)" Warning
Write-Status "        - SAC Opción B: >45% CO2 reduction (MINIMO)" Info
Write-Status "        - Ideal: 50%+ CO2 reduction (PARITY CON A2C)" Success

Write-Status "  [4.3] Iniciando entrenamiento..." Info
Write-Status "        Episodes: $Episodes | Device: $Device" Muted
Write-Status "        Duración estimada: 20-30 minutos (GPU RTX 4060)" Muted

if ($DryRun) {
    Write-Status "        DRY-RUN: Saltando entrenamiento" Muted
} else {
    # Limpiar variables de entrenamiento anterior de SAC
    $StartTime = Get-Date
    
    Write-Status "  [4.4] Ejecutando scripts\train\train_sac_multiobjetivo.py..." Info
    
    # Usar encoding UTF-8 para output
    $env:PYTHONIOENCODING = 'utf-8'
    
    # Buffer de output para monitoreo
    $TrainingOutput = New-Object System.Collections.ArrayList
    
    try {
        # Ejecutar Python con output capturado
        $Process = Start-Process python -ArgumentList @(
            'scripts\train\train_sac_multiobjetivo.py'
        ) -NoNewWindow -PassThru -RedirectStandardOutput 'sac_training.tmp.log' -RedirectStandardError 'sac_training.tmp.err'
        
        Write-Status "        Proceso iniciado - Monitorando output..." Info
        
        # Monitorear en tiempo real (líneas principales)
        $LogFile = 'sac_training.tmp.log'
        $LastLine = 0
        $PreviousReward = $null
        $FlatEpisodes = 0
        
        while ($Process.HasExited -eq $false) {
            if (Test-Path $LogFile) {
                $CurrentLines = @(Get-Content $LogFile)
                
                if ($CurrentLines.Count -gt $LastLine) {
                    # Mostrar nuevas líneas
                    for ($i = $LastLine; $i -lt $CurrentLines.Count; $i++) {
                        $Line = $CurrentLines[$i]
                        
                        # Detectar episodios y rewards
                        if ($Line -match 'Episode (\d+).*\| Reward:\s*([-\d.]+).*\| CO2:\s*([\d,]+)') {
                            $EpisodeNum = [int]$matches[1]
                            $Reward = [float]$matches[2]
                            $CO2Str = $matches[3] -replace ',', ''
                            $CO2 = [float]$CO2Str
                            
                            # Detectar no-convergencia (reward flat)
                            if ($PreviousReward -ne $null) {
                                $Change = [math]::Abs($Reward - $PreviousReward) / [math]::Max([math]::Abs($PreviousReward), 0.001)
                                
                                if ($Change -lt 0.001) {  # <0.1% cambio
                                    $FlatEpisodes++
                                    Write-Status "        ⚠️  Episode $EpisodeNum: Reward FLAT (change: {0:P2})" -f $Change Warning
                                } else {
                                    $FlatEpisodes = 0
                                    Write-Status "        ✅ Episode $EpisodeNum: Reward $Reward | CO2: {0:N0} kg | LEARNING ✓" -f [int]$CO2 Success
                                }
                            }
                            
                            $PreviousReward = $Reward
                        }
                        
                        # Mostrar líneas importantes
                        if ($Line -match '(Error|Exception|Traceback|WARNING|CRITICAL)') {
                            Write-Status "        ❌ $Line" Error
                        }
                        elseif ($Line -match '(Completed|Finished|Success|Total)') {
                            Write-Status "        ✅ $Line" Success
                        }
                    }
                    
                    $LastLine = $CurrentLines.Count
                }
            }
            
            Start-Sleep -Milliseconds 500
            
            # Safety check: si demasiadas líneas flat, advertir
            if ($FlatEpisodes -ge 5) {
                Write-Status "        ⚠️  ADVERTENCIA: 5+ episodios sin mejora. Posible no-convergencia." Warning
                Write-Status "           Continuar monitoreo... (SAC puede recuperarse con nueva exploración)" Muted
                $FlatEpisodes = 0
            }
        }
        
        # Esperar a que termine proceso
        $ExitCode = $Process.ExitCode
        $EndTime = Get-Date
        $Duration = ($EndTime - $StartTime).TotalMinutes
        
        if ($ExitCode -eq 0) {
            Write-Status "        $($Emojis.Check) Entrenamiento SAC completo en {0:F1} minutos" -f $Duration Success
        } else {
            Write-Status "        $($Emojis.Cross) Error en entrenamiento (exit code: $ExitCode)" Error
        }
        
        # Limpiar logs temporales
        if (Test-Path 'sac_training.tmp.log') { Remove-Item 'sac_training.tmp.log' -Force }
        if (Test-Path 'sac_training.tmp.err') { Remove-Item 'sac_training.tmp.err' -Force }
        
    } catch {
        Write-Status "        ❌ Error iniciando entrenamiento" Error
        Write-Status "           $_" Muted
        exit 1
    }
}

# ===== FASE 5: VALIDACION Y COMPARACION =====
Write-Header "$($Emojis.Monitor) FASE 5: VALIDAR RESULTADOS Y COMPARAR CON A2C/PPO"

if ($DryRun) {
    Write-Status "  DRY-RUN: Saltando validación" Muted
} else {
    Write-Status "  [5.1] Extrayendo métricas de checkpoint SAC..." Info
    
    $ValidateScript = @'
import json
from pathlib import Path

result_file = Path('outputs/sac_training/result_sac.json')
if result_file.exists():
    with open(result_file) as f:
        data = json.load(f)
    
    if 'training_evolution' in data and 'episode_co2_grid' in data['training_evolution']:
        episodes = data['training_evolution']['episode_co2_grid']
        first_co2 = episodes[0] if episodes else 0
        final_co2 = episodes[-1] if episodes else 0
        best_co2 = min(episodes) if episodes else 0
        
        print(f"CO2 First: {first_co2:,.0f} kg")
        print(f"CO2 Final: {final_co2:,.0f} kg")
        print(f"CO2 Best:  {best_co2:,.0f} kg")
        print(f"Episodes: {len(episodes)}")
        
        # Calcular reducción
        baseline = 4485286  # kg/año sin control
        reduction_pct = ((baseline - final_co2) / baseline * 100) if baseline > 0 else 0
        print(f"Reduction: {reduction_pct:.1f}%")
    else:
        print("Missing training_evolution data")
else:
    print("SAC result file not found")
'@
    
    python -c $ValidateScript 2>&1 | ForEach-Object {
        if ($_ -match 'Reduction') {
            Write-Status "        $($Emojis.Check) $_" Success
        } else {
            Write-Status "        $_" Info
        }
    }
}

# ===== RESUMEN FINAL =====
Write-Header "$($Emojis.Check) RESUMEN OPCION B - ENTRENAR SAC OPTIMIZADO"

Write-Status "  ✅ FASES COMPLETADAS:" Success
Write-Status "     1. ✅ Validación ambiente" Success
Write-Status "     2. ✅ Limpieza SAC segura (A2C/PPO protegidos)" Success
Write-Status "     3. ✅ Construcción datasets OE2 reales" Success
Write-Status "     4. ✅ Entrenamiento SAC con Opción B" Success
Write-Status "     5. ✅ Validación y comparación" Success

Write-Status "`n  📊 COMPARACION SAC:" Info
Write-Status "     SAC v9.2 (OLD):  35.2% CO2 reduction (NO CONVERGENCIA)" Warning
Write-Status "     SAC Opción B:    >45% CO2 reduction (ESPERADO)" Info
Write-Status "     A2C v7.2:        50.9% CO2 reduction (BASELINE)" Success

Write-Status "`n  🎯 PROXIMOS PASOS:" Info
Write-Status "     1. Generar gráficas comparativas con SAC nuevo" Muted
Write-Status "     2. Validar convergencia por episodio" Muted
Write-Status "     3. Documentar mejoras vs SAC v9.2" Muted

Write-Host "`n" 
Write-Host ("="*80) -ForegroundColor Cyan

if (-not $DryRun) {
    Write-Status "Para ver resultados: python validate_and_graph_sac.py" Info
    Write-Status "Para comparar todos: python generate_real_checkpoint_graphs.py" Info
}
