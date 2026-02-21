#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

# Cargar los datos del BESS
bess_data = pd.read_csv('data/interim/oe2/bess/bess_ano_2024.csv')

# Verificar las primeras 7 días
first_7_days = bess_data.iloc[:168]

print('=== VERIFICACION: PRIMEROS 7 DIAS (HORAS 0-167) ===\n')
print(f'Columnas disponibles: {list(bess_data.columns)}')
print(f'\nHoras analizadas: {len(first_7_days)}')
print(f'Rango bess_action_kwh: {first_7_days["bess_action_kwh"].min():.1f} - {first_7_days["bess_action_kwh"].max():.1f} kW\n')

# Patrón esperado: Horas 0-8=0, 9-15=400, ...
print('Análisis HORARIO (valores esperados por FASE):')
for h in [0, 6, 9, 15, 17, 22]:
    val = first_7_days.loc[h, 'bess_action_kwh'] if h < len(first_7_days) else -999
    expected = {0: 0, 6: 0, 9: 400, 15: 400, 17: 0, 22: 0}.get(h, '?')
    print(f'  Hora {h:2d}: {val:6.1f} kW (esperado ~{expected})')

# Verificar que se están usando datos reales en _plot_integral_curves
print('\n=== VERIFICACION: DATOS PARA _plot_integral_curves ===')
print(f'pv_to_bess_kwh (CARGA): min={first_7_days["pv_to_bess_kwh"].min():.1f}, max={first_7_days["pv_to_bess_kwh"].max():.1f}')
print(f'bess_to_ev_kwh (DESC.): min={first_7_days["bess_to_ev_kwh"].min():.1f}, max={first_7_days["bess_to_ev_kwh"].max():.1f}')
print(f'bess_to_mall_kwh (DESC.): min={first_7_days["bess_to_mall_kwh"].min():.1f}, max={first_7_days["bess_to_mall_kwh"].max():.1f}')

# Descarga total
total_discharge = first_7_days['bess_to_ev_kwh'] + first_7_days['bess_to_mall_kwh']
print(f'Descarga total: min={total_discharge.min():.1f}, max={total_discharge.max():.1f}')

# Verificar valores con threshold 0.1 (como en el código corregido)
charge_above_threshold = (first_7_days['pv_to_bess_kwh'] > 0.1).sum()
discharge_above_threshold = (total_discharge > 0.1).sum()
print(f'\nValores significativos (> 0.1 kW):')
print(f'  Horas con CARGA: {charge_above_threshold}')
print(f'  Horas con DESCARGA: {discharge_above_threshold}')

# Resumen de patrón de 6 fases
print('\n=== PATRÓN ESPERADO DE 6 FASES - VALIDACION ===')
print('FASE 6 (00-06): Reposo\n  bess_action ~0:')
fase6_vals = first_7_days.loc[0:6, 'bess_action_kwh'].values
print(f'  Valores: {fase6_vals}')

print('\nFASE 1 (09-15): Carga PV→BESS\n  bess_action ~400:')
fase1_vals = first_7_days.loc[9:15, 'bess_action_kwh'].values
print(f'  Valor medio: {np.mean(fase1_vals):.1f} kW')

print('\nFASE 3-5 (17-22): Descarga BESS→MALL\n  pv_to_bess ~0, bess_to_mall > 0:')
fase3_5_data = first_7_days.loc[17:22, ['pv_to_bess_kwh', 'bess_to_mall_kwh']]
print(f'  pv_to_bess media: {fase3_5_data["pv_to_bess_kwh"].mean():.1f} kW')
print(f'  bess_to_mall media: {fase3_5_data["bess_to_mall_kwh"].mean():.1f} kW')

print('\n✓ Verificación completa')
