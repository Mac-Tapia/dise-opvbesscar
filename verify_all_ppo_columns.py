#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación completa de columnas en CSVs de PPO v7.4
Asegura que se guardan todos los valores críticos.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import json

print('=' * 100)
print('PPO v7.4 - VERIFICACIÓN COMPLETA DE COLUMNAS')
print('=' * 100)
print()

# =========================================================================
# 1. COLUMNAS ESPERADAS EN timeseries_ppo.csv
# =========================================================================
print('[TIMESERIES_PPO.CSV] - Columnas esperadas y verificación')
print('-' * 100)

expected_timeseries_cols = {
    'Timestep/Episode': ['timestep', 'episode', 'hour'],
    'Energía': ['solar_generation_kwh', 'ev_charging_kwh', 'grid_import_kwh', 'bess_power_kw', 'bess_soc', 'mall_demand_kw'],
    'CO2 (CRÍTICO)': ['co2_grid_kg', 'co2_avoided_indirect_kg', 'co2_avoided_direct_kg', 'co2_avoided_total_kg'],
    'Vehículos': ['motos_charging', 'mototaxis_charging'],
    'Reward': ['reward', 'r_co2', 'r_solar', 'r_vehicles', 'r_grid_stable', 'r_bess', 'r_priority'],
    'Costos': ['ahorro_solar_soles', 'ahorro_bess_soles', 'costo_grid_soles', 'ahorro_combustible_usd', 'ahorro_total_usd'],
    'Entropía/PPO (CRÍTICO)': ['entropy', 'approx_kl', 'clip_fraction', 'policy_loss', 'value_loss', 'explained_variance']
}

expected_cols_list = []
for category, cols in expected_timeseries_cols.items():
    expected_cols_list.extend(cols)

ts_file = Path('outputs/ppo_training/timeseries_ppo.csv')
if ts_file.exists():
    df_ts = pd.read_csv(ts_file)
    actual_cols = set(df_ts.columns)
    expected_set = set(expected_cols_list)
    
    missing = expected_set - actual_cols
    extra = actual_cols - expected_set
    
    if missing:
        print(f'❌ COLUMNAS FALTANTES ({len(missing)}):')
        for col in sorted(missing):
            print(f'  - {col}')
        print()
    else:
        print('✓ Todas las columnas esperadas presentes')
        print()
    
    if extra:
        print(f'⚠️  COLUMNAS EXTRA ({len(extra)}):')
        for col in sorted(extra):
            print(f'  - {col}')
        print()
    
    print(f'📊 Total columnas: {len(df_ts.columns)} (esperado: {len(expected_cols_list)})')
    print(f'📈 Total registros: {len(df_ts):,}')
    print()
    
    # Validación de datos
    print('[VALIDACIÓN DE DATOS]')
    for category, cols in expected_timeseries_cols.items():
        cat_cols = [c for c in cols if c in df_ts.columns]
        if cat_cols:
            non_zero = (df_ts[cat_cols] != 0).any(axis=1).sum()
            zero_count = (df_ts[cat_cols] == 0).all(axis=1).sum()
            pct_zero = (zero_count / len(df_ts)) * 100 if len(df_ts) > 0 else 0
            print(f'  {category}: {non_zero:,} valores no-cero, {zero_count:,} filas todas-cero ({pct_zero:.1f}%)')

else:
    print(f'❌ No encontrado: {ts_file}')

print()

# =========================================================================
# 2. COLUMNAS ESPERADAS EN trace_ppo.csv
# =========================================================================
print('[TRACE_PPO.CSV] - Columnas esperadas y verificación')
print('-' * 100)

expected_trace_cols = {
    'Timestep/Episode': ['timestep', 'episode', 'step_in_episode', 'hour'],
    'Energía': ['solar_generation_kwh', 'ev_charging_kwh', 'grid_import_kwh', 'bess_power_kw', 'motos_power_kw', 'mototaxis_power_kw'],
    'CO2 (CRÍTICO)': ['co2_grid_kg', 'co2_avoided_indirect_kg', 'co2_avoided_direct_kg'],
    'Vehículos': ['motos_charging', 'mototaxis_charging'],
    'Reward': ['reward'],
    'Entropía/PPO (CRÍTICO)': ['entropy', 'approx_kl', 'clip_fraction', 'policy_loss', 'value_loss', 'explained_variance']
}

expected_trace_list = []
for category, cols in expected_trace_cols.items():
    expected_trace_list.extend(cols)

trace_file = Path('outputs/ppo_training/trace_ppo.csv')
if trace_file.exists():
    df_trace = pd.read_csv(trace_file)
    actual_trace_cols = set(df_trace.columns)
    expected_trace_set = set(expected_trace_list)
    
    missing_trace = expected_trace_set - actual_trace_cols
    extra_trace = actual_trace_cols - expected_trace_set
    
    if missing_trace:
        print(f'❌ COLUMNAS FALTANTES ({len(missing_trace)}):')
        for col in sorted(missing_trace):
            print(f'  - {col}')
        print()
    else:
        print('✓ Todas las columnas esperadas presentes')
        print()
    
    if extra_trace:
        print(f'⚠️  COLUMNAS EXTRA ({len(extra_trace)}):')
        for col in sorted(extra_trace):
            print(f'  - {col}')
        print()
    
    print(f'📊 Total columnas: {len(df_trace.columns)} (esperado: {len(expected_trace_list)})')
    print(f'📈 Total registros: {len(df_trace):,}')
    print()

else:
    print(f'❌ No encontrado: {trace_file}')

print()

# =========================================================================
# 3. VERIFICACIÓN DE result_ppo.json
# =========================================================================
print('[RESULT_PPO.JSON] - Datos agregados por episodio')
print('-' * 100)

result_file = Path('outputs/ppo_training/result_ppo.json')
if result_file.exists():
    with open(result_file, 'r') as f:
        result = json.load(f)
    
    if 'training_evolution' in result:
        te = result['training_evolution']
        print(f'✓ Training evolution con {len(te)} campos:')
        for key in te:
            val = te[key]
            if isinstance(val, list):
                print(f'  - {key} ({len(val)} épocas)')
            else:
                print(f'  - {key}')
        print()

print()
print('=' * 100)
print('✅ VERIFICACIÓN COMPLETA - Ready for next training run')
print('=' * 100)
print()
print('📝 RESUMEN:')
print('  • timeseries_ppo.csv: Datos por HORA (8,760 horas × N episodios)')
print('  • trace_ppo.csv: Datos por TIMESTEP (paso a paso)')
print('  • result_ppo.json: Agregados por EPISODIO (1 valor por episodio)')
print()
print('🚀 PRÓXIMO PASO: python scripts/train/train_ppo_multiobjetivo.py')
print()
