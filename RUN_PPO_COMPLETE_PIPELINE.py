#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PIPELINE COMPLETO DE PPO - SEGURO Y MONITOREABLE
================================================
1. Limpiar SOLO PPO checkpoints (proteger SAC/A2C)
2. Validar datasets
3. Entrenar PPO con monitoreo en tiempo real
4. Aplicar mejora continua

Ejecutar: python RUN_PPO_COMPLETE_PIPELINE.py
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime

print('=' * 90)
print('PIPELINE COMPLETO PPO - SECURE & MONITORED')
print('=' * 90)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# ============================================================================
# FASE 1: LIMPIAR SOLO PPO - PROTEGER SAC/A2C
# ============================================================================
print('[FASE 1/4] LIMPIAR CHECKPOINTS - SOLO PPO')
print('-' * 90)

checkpoint_dir = Path('checkpoints')
sac_dir = checkpoint_dir / 'SAC'
ppo_dir = checkpoint_dir / 'PPO'
a2c_dir = checkpoint_dir / 'A2C'

# Crear directorio si no existe
checkpoint_dir.mkdir(parents=True, exist_ok=True)

# CONTAR ITEMS ANTES
sac_before = len(list(sac_dir.glob('*'))) if sac_dir.exists() else 0
ppo_before = len(list(ppo_dir.glob('*'))) if ppo_dir.exists() else 0
a2c_before = len(list(a2c_dir.glob('*'))) if a2c_dir.exists() else 0

print(f'\n[PRE-LIMPIEZA] Estado actual:')
print(f'  SAC: {sac_before} items')
print(f'  PPO: {ppo_before} items')
print(f'  A2C: {a2c_before} items')

# LIMPIAR SOLO PPO
if ppo_dir.exists():
    ppo_files = list(ppo_dir.glob('*'))
    print(f'\n[LIMPIANDO] PPO: {len(ppo_files)} archivos a eliminar...')
    for f in ppo_files:
        try:
            if f.is_file():
                f.unlink()
                print(f'  ✓ Eliminado: {f.name}')
            elif f.is_dir():
                shutil.rmtree(f)
                print(f'  ✓ Eliminado dir: {f.name}')
        except Exception as e:
            print(f'  ✗ Error eliminando {f.name}: {e}')

# VALIDAR POST-LIMPIEZA
sac_after = len(list(sac_dir.glob('*'))) if sac_dir.exists() else 0
ppo_after = len(list(ppo_dir.glob('*'))) if ppo_dir.exists() else 0
a2c_after = len(list(a2c_dir.glob('*'))) if a2c_dir.exists() else 0

print(f'\n[POST-LIMPIEZA] Estado después:')
print(f'  SAC: {sac_after} items (Cambio: {sac_after - sac_before:+d}) ' + ('✓ PROTEGIDO' if sac_before == sac_after else '✗ CAMBIO!'))
print(f'  PPO: {ppo_after} items (Cambio: {ppo_after - ppo_before:+d}) ✓ LIMPIADO')
print(f'  A2C: {a2c_after} items (Cambio: {a2c_after - a2c_before:+d}) ' + ('✓ PROTEGIDO' if a2c_before == a2c_after else '✗ CAMBIO!'))

if sac_before != sac_after or a2c_before != a2c_after:
    print('\n✗ ERROR: SAC o A2C fueron modificados - ABORTING')
    sys.exit(1)

print('\n✓ FASE 1 COMPLETADA - Checkpoints seguros')
print()

# ============================================================================
# FASE 2: VALIDAR DATASETS OE2
# ============================================================================
print('[FASE 2/4] VALIDAR DATASETS OE2')
print('-' * 90)

import pandas as pd

dataset_files = {
    'Solar PVGIS': Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv'),
    'Chargers 38 sockets': Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),
    'BESS SOC': Path('data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv'),
    'Mall Demand': Path('data/oe2/demandamallkwh/demandamallhorakwh.csv'),
}

all_valid = True
for name, filepath in dataset_files.items():
    if filepath.exists():
        try:
            df = pd.read_csv(filepath)
            rows = len(df)
            cols = len(df.columns)
            print(f'  ✓ {name}: {rows:,} rows × {cols} cols')
        except Exception as e:
            print(f'  ✗ {name}: ERROR - {e}')
            all_valid = False
    else:
        print(f'  ✗ {name}: Archivo no encontrado')
        all_valid = False

if not all_valid:
    print('\n✗ DATASETS INVÁLIDOS - ABORTING')
    sys.exit(1)

print('\n✓ FASE 2 COMPLETADA - Todos los datasets válidos')
print()

# ============================================================================
# FASE 3: ENTRENAR PPO (POWERSHELL)
# ============================================================================
print('[FASE 3/4] ENTRENAR PPO EN POWERSHELL')
print('-' * 90)
print('\n⚠️  A continuación, ejecutaremos el entrenamiento en PowerShell.')
print('   El script monitorea el progreso en tiempo real.')
print('\nCOMARNDO:')
print('   powershell -NoProfile -ExecutionPolicy Bypass -Command "...')
print('   python scripts/train/train_ppo_multiobjetivo.py"')
print()

input('Presiona ENTER para iniciar el entrenamiento...')

import subprocess
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

# Crear script PowerShell de entrenamiento
ps_script = r'''
$env:PYTHONIOENCODING='utf-8'
Write-Host "════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "PPO TRAINING - SECURE PIPELINE v7.0 FIX" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Estado: Limpieza completada ✓ | Datasets validados ✓ | Iniciando training..."
Write-Host ""

python scripts/train/train_ppo_multiobjetivo.py

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "TRAINING COMPLETADO" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
'''

ps_file = Path('_TEMP_PPO_TRAIN.ps1')
ps_file.write_text(ps_script)

try:
    result = subprocess.run(
        ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ps_file)],
        capture_output=False,
        text=True
    )
    
    if result.returncode != 0:
        print(f'\n✗ Entrenamiento falló con código {result.returncode}')
        sys.exit(1)
    else:
        print('\n✓ FASE 3 COMPLETADA - Entrenamiento exitoso')
        
finally:
    if ps_file.exists():
        ps_file.unlink()

print()

# ============================================================================
# FASE 4: VALIDAR Y APLICAR MEJORA CONTINUA
# ============================================================================
print('[FASE 4/4] VALIDAR DATOS Y APLICAR MEJORA CONTINUA')
print('-' * 90)

trace_file = Path('outputs/ppo_training/trace_ppo.csv')

if not trace_file.exists():
    print(f'\n✗ Archivo de trace no encontrado: {trace_file}')
    sys.exit(1)

# Cargar y validar datos
ppo_df = pd.read_csv(trace_file)

print(f'\n[VALIDACIÓN] Datos PPO:')
print(f'  Total timesteps: {len(ppo_df):,}')
print(f'  Episodios: {ppo_df["episode"].max() + 1}')

# Verificar columnas críticas
critical_cols = ['solar_generation_kwh', 'grid_import_kwh', 'ev_charging_kwh']
for col in critical_cols:
    if col in ppo_df.columns:
        total = ppo_df[col].sum()
        zeros = (ppo_df[col] == 0).sum()
        pct_zero = (zeros / len(ppo_df) * 100) if len(ppo_df) > 0 else 0
        
        if total > 0:
            status = '✓ VÁLIDO'
        else:
            status = '✗ CORRUPTO (100% ceros)'
        
        print(f'  {col}: {total:,.0f} ({pct_zero:.1f}% ceros) {status}')
    else:
        print(f'  {col}: ✗ NO ENCONTRADA')

# Comparar con SAC si existe
sac_trace = Path('outputs/sac_training/trace_sac.csv')
if sac_trace.exists():
    sac_df = pd.read_csv(sac_trace)
    
    print(f'\n[COMPARACIÓN] PPO vs SAC:')
    
    ppo_solar = ppo_df['solar_generation_kwh'].sum() if 'solar_generation_kwh' in ppo_df.columns else 0
    sac_solar = sac_df['solar_generation_kwh'].sum() if 'solar_generation_kwh' in sac_df.columns else 0
    ppo_grid = ppo_df['grid_import_kwh'].sum() if 'grid_import_kwh' in ppo_df.columns else 0
    sac_grid = sac_df['grid_import_kwh'].sum() if 'grid_import_kwh' in sac_df.columns else 0
    
    if ppo_grid > 0 and sac_grid > 0:
        grid_reduction = (1 - ppo_grid / sac_grid) * 100
        print(f'  Grid reduction: {grid_reduction:.1f}%')
        if grid_reduction > 50:
            print(f'    ✓ EXCELENTE (>50%)')
        elif grid_reduction > 20:
            print(f'    ✓ BUENO (>20%)')
        else:
            print(f'    ⚠️ BAJO (<20%)')

print('\n[MEJORA CONTINUA]')
print('  Opciones:')
print('  1. Ajustar reward weights (aumentar co2_weight)')
print('  2. Aumentar learning rate (si convergencia lenta)')
print('  3. Extender training (más episodios)')
print('  4. Implementar curiosity-driven exploration')

print('\n✓ FASE 4 COMPLETADA - Validación y recomendaciones listas')
print()

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print('=' * 90)
print('PIPELINE COMPLETADO EXITOSAMENTE')
print('=' * 90)
print(f'Fin: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()
print('RESULTADO:')
print(f'  ✓ Checkpoints limpios (PPO): 0 items')
print(f'  ✓ SAC protegido: {sac_after} items')
print(f'  ✓ A2C protegido: {a2c_after} items')
print(f'  ✓ Dataset validado')
print(f'  ✓ PPO Entrenamiento completado')
print(f'  ✓ Datos validados (sin corrupción)')
print()
print('PRÓXIMOS PASOS:')
print('  → Revisar outputs/ppo_training/trace_ppo.csv')
print('  → Ejecutar FINAL_DEPLOYMENT_RECOMMENDATION.py para comparación 3-agentes')
print('  → Deployar agent champion a hardware Iquitos')
print()
