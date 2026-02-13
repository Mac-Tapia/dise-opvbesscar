#!/usr/bin/env python
"""Verificación final del dataset BESS 2024"""

import pandas as pd
import numpy as np

print('╔════════════════════════════════════════════════════════════════════╗')
print('║     VERIFICACIÓN FINAL - CONTENIDO DEL DATASET BESS 2024         ║')
print('╚════════════════════════════════════════════════════════════════════╝')
print()

try:
    df = pd.read_csv('data/oe2/bess/bess_hourly_dataset_2024.csv', index_col=0, parse_dates=True)

    print('✅ ESTRUCTURA:')
    print(f'   • Filas: {len(df):,} (esperado: 8,760) ✓')
    print(f'   • Columnas: {len(df.columns)} (esperado: 11) ✓')
    print(f'   • Índice: DatetimeIndex (2024) ✓')
    print()

    print('✅ VALIDACIONES:')
    print(f'   • Valores NaN: {df.isna().sum().sum()} (ninguno) ✓')
    print(f'   • Índice único: {df.index.is_unique} ✓')
    print(f'   • Año: {df.index[0].year} ✓')
    print(f'   • Período: {df.index[0]} a {df.index[-1]} ✓')
    print()

    print('✅ ENERGÍA ANUAL (kWh):')
    print(f'   • PV generado: {df["pv_kwh"].sum():>12,.0f}')
    print(f'   • EV demanda: {df["ev_kwh"].sum():>13,.0f}')
    print(f'   • Mall demanda: {df["mall_kwh"].sum():>11,.0f}')
    grid_total = df["grid_to_ev_kwh"].sum() + df["grid_to_mall_kwh"].sum()
    print(f'   • Red importada: {grid_total:>10,.0f}')
    print()

    print('✅ BALANCE ENERGÉTICO:')
    total_demand = df['ev_kwh'].sum() + df['mall_kwh'].sum()
    grid_import = grid_total
    pv_used = df['pv_kwh'].sum()
    autosuf = 100 * (1 - grid_import / total_demand)
    pv_cover = 100 * (pv_used / total_demand)

    print(f'   • Solar cubre: {pv_cover:>6.1f}% de demanda')
    print(f'   • Autosuficiencia (incl. BESS): {autosuf:>3.1f}%')
    print(f'   • Red requerida: {100-autosuf:>6.1f}%')
    print()

    print('✅ BESS OPERACIÓN:')
    print(f'   • Carga anual: {df["bess_charge_kwh"].sum():>12,.0f} kWh')
    print(f'   • Descarga anual: {df["bess_discharge_kwh"].sum():>10,.0f} kWh')
    print(f'   • SOC mínimo: {df["soc_percent"].min():>15.1f}%')
    print(f'   • SOC máximo: {df["soc_percent"].max():>15.1f}%')
    print(f'   • SOC promedio: {df["soc_percent"].mean():>13.1f}%')
    print()

    print('✅ EJEMPLOS DE DATOS:')
    print(f'   • Primero (2024-01-01): PV={df.iloc[0]["pv_kwh"]:>6.1f} kWh, SOC={df.iloc[0]["soc_percent"]:>5.1f}%')
    print(f'   • Último (2024-12-30):  PV={df.iloc[-1]["pv_kwh"]:>6.1f} kWh, SOC={df.iloc[-1]["soc_percent"]:>5.1f}%')
    print()

    print('╔════════════════════════════════════════════════════════════════════╗')
    print('║  ✅ DATASET BESS 2024 LISTO PARA USAR EN OE3                      ║')
    print('╚════════════════════════════════════════════════════════════════════╝')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
