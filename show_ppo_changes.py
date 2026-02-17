#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparación: QUÉ SE GUARDABA vs QUÉ SE GUARDARÁ AHORA en PPO v7.4
"""
from __future__ import annotations

print('=' * 100)
print('PPO v7.4 - COMPARACIÓN DE COLUMNAS: ANTES vs DESPUÉS DE CAMBIOS')
print('=' * 100)
print()

# =========================================================================
# ANTES: v7.2 (CSV viejo generado antes de correcciones)
# =========================================================================
print('ANTES (v7.2) - Columnas en timeseries_ppo.csv:')
print('-' * 100)
before_timeseries = [
    'timestep', 'episode', 'hour', 'solar_generation_kwh', 'ev_charging_kwh',
    'grid_import_kwh', 'bess_power_kw', 'bess_soc', 'mall_demand_kw',
    'co2_avoided_total_kg', 'motos_charging', 'mototaxis_charging', 'reward',
    'r_co2', 'r_solar', 'r_vehicles', 'r_grid_stable', 'r_bess', 'r_priority',
    'ahorro_solar_soles', 'ahorro_bess_soles', 'costo_grid_soles', 'ahorro_combustible_usd',
    'ahorro_total_usd'
]

print(f'Total: {len(before_timeseries)} columnas')
for i, col in enumerate(before_timeseries, 1):
    print(f'  {i:2d}. {col}')

print()
print('ANTES (v7.2) - Columnas en trace_ppo.csv:')
print('-' * 100)
before_trace = [
    'timestep', 'episode', 'step_in_episode', 'hour', 'reward',
    'co2_grid_kg', 'co2_avoided_indirect_kg', 'co2_avoided_direct_kg',
    'solar_generation_kwh', 'ev_charging_kwh', 'grid_import_kwh',
    'bess_power_kw', 'motos_power_kw', 'mototaxis_power_kw',
    'motos_charging', 'mototaxis_charging'
]

print(f'Total: {len(before_trace)} columnas')
for i, col in enumerate(before_trace, 1):
    print(f'  {i:2d}. {col}')

print()
print()

# =========================================================================
# DESPUÉS: v7.4 (lo que se guardará con los cambios implementados)
# =========================================================================
print('DESPUÉS (v7.4) - Columnas en timeseries_ppo.csv:')
print('-' * 100)
after_timeseries = [
    'timestep', 'episode', 'hour', 'solar_generation_kwh', 'ev_charging_kwh',
    'grid_import_kwh', 'bess_power_kw', 'bess_soc', 'mall_demand_kw',
    # [FIX v7.4] NUEVAS: CO2
    'co2_grid_kg', 'co2_avoided_indirect_kg', 'co2_avoided_direct_kg', 'co2_avoided_total_kg',
    'motos_charging', 'mototaxis_charging', 'reward',
    'r_co2', 'r_solar', 'r_vehicles', 'r_grid_stable', 'r_bess', 'r_priority',
    'ahorro_solar_soles', 'ahorro_bess_soles', 'costo_grid_soles', 'ahorro_combustible_usd',
    'ahorro_total_usd',
    # [FIX v7.3] NUEVAS: Entropía/PPO
    'entropy', 'approx_kl', 'clip_fraction', 'policy_loss', 'value_loss', 'explained_variance'
]

print(f'Total: {len(after_timeseries)} columnas (+{len(after_timeseries) - len(before_timeseries)})')
for i, col in enumerate(after_timeseries, 1):
    if col not in before_timeseries:
        print(f'  {i:2d}. {col} ⭐ NUEVA')
    else:
        print(f'  {i:2d}. {col}')

print()
print('DESPUÉS (v7.4) - Columnas en trace_ppo.csv:')
print('-' * 100)
after_trace = [
    'timestep', 'episode', 'step_in_episode', 'hour', 'reward',
    'co2_grid_kg', 'co2_avoided_indirect_kg', 'co2_avoided_direct_kg',
    'solar_generation_kwh', 'ev_charging_kwh', 'grid_import_kwh',
    'bess_power_kw', 'motos_power_kw', 'mototaxis_power_kw',
    'motos_charging', 'mototaxis_charging',
    # [FIX v7.3] NUEVAS: Entropía/PPO
    'entropy', 'approx_kl', 'clip_fraction', 'policy_loss', 'value_loss', 'explained_variance'
]

print(f'Total: {len(after_trace)} columnas (+{len(after_trace) - len(before_trace)})')
for i, col in enumerate(after_trace, 1):
    if col not in before_trace:
        print(f'  {i:2d}. {col} ⭐ NUEVA')
    else:
        print(f'  {i:2d}. {col}')

print()
print()

# =========================================================================
# RESUMEN DE NUEVAS COLUMNAS
# =========================================================================
print('=' * 100)
print('RESUMEN DE CAMBIOS')
print('=' * 100)

new_cols_ts = set(after_timeseries) - set(before_timeseries)
new_cols_trace = set(after_trace) - set(before_trace)

print()
print('🆕 NUEVAS EN timeseries_ppo.csv:')
for col in sorted(new_cols_ts):
    print(f'  • {col}')

print()
print('🆕 NUEVAS EN trace_ppo.csv:')
for col in sorted(new_cols_trace):
    print(f'  • {col}')

print()
print()
print('=' * 100)
print('✅ IMPACTO DE CAMBIOS')
print('=' * 100)

print()
print('📊 timeseries_ppo.csv:')
print(f'  Antes: {len(before_timeseries)} columnas')
print(f'  Después: {len(after_timeseries)} columnas')
print(f'  Adiciones: +9 columnas')
print(f'    - 4 columnas CO2 (v7.4): co2_grid_kg, co2_avoided_indirect_kg, co2_avoided_direct_kg, co2_avoided_total_kg')
print(f'    - 6 columnas Entropía (v7.3): entropy, approx_kl, clip_fraction, policy_loss, value_loss, explained_variance')
print()

print('📊 trace_ppo.csv:')
print(f'  Antes: {len(before_trace)} columnas')
print(f'  Después: {len(after_trace)} columnas')
print(f'  Adiciones: +6 columnas')
print(f'    - 6 columnas Entropía (v7.3): entropy, approx_kl, clip_fraction, policy_loss, value_loss, explained_variance')
print()

print()
print('=' * 100)
print('🚀 PRÓXIMOS PASOS')
print('=' * 100)
print()
print('1. Ejecutar entrenamiento PPO (generará nuevos CSVs con las 9 columnas nuevas):')
print('   python scripts/train/train_ppo_multiobjetivo.py')
print()
print('2. Validar que se guardaron correctamente:')
print('   python verify_all_ppo_columns.py')
print()
print('3. Analizar nuevas columnas en Python:')
print('   import pandas as pd')
print('   df = pd.read_csv("outputs/ppo_training/timeseries_ppo.csv")')
print('   print(df[["entropy", "co2_grid_kg", "co2_avoided_indirect_kg"]].head())')
print()
