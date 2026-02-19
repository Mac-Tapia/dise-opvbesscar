#!/usr/bin/env python
"""Extraer configuración específica de motos y mototaxis."""

import pandas as pd
import json
from pathlib import Path
from collections import Counter

print("=" * 80)
print("EXTRAYENDO CONFIGURACIÓN DE MOTOS Y MOTOTAXIS")
print("=" * 80)

# Cargar chargers
df_chargers = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')

# Encontrar todas las columnas vehicle_type
vehicle_type_cols = [c for c in df_chargers.columns if 'vehicle_type' in c.lower()]
print(f'\nColumnas de tipo de vehículo encontradas: {len(vehicle_type_cols)}')

# Contar cuántas son MOTO vs MOTOTAXI
vehicle_types = {}
for col in vehicle_type_cols:
    unique_vals = df_chargers[col].unique()
    for val in unique_vals:
        if val not in vehicle_types:
            vehicle_types[val] = []
        vehicle_types[val].append(col)

print(f'\nTipos de vehículos encontrados:')
for vtype, cols in vehicle_types.items():
    print(f'  {vtype}: {len(cols)} columnas/sockets')
    # Mostrar primeros 3
    for col in cols[:3]:
        print(f'    - {col}')

# Extraer información de cargadores del archivo (últimas columnas)
charger_cols = [c for c in df_chargers.columns if c.startswith('cargador_')]
print(f'\nColumnas de cargador encontradas: {len(charger_cols)}')

# Agrupar por cargador
chargers_info = {}
for col in charger_cols:
    # Formato: cargador_N_XXX
    parts = col.split('_')
    if len(parts) >= 2:
        charger_num = parts[1]
        if charger_num not in chargers_info:
            chargers_info[charger_num] = []
        chargers_info[charger_num].append(col)

print(f'\nCargadores identificados: {len(chargers_info)}')
for charger_num in sorted(chargers_info.keys(), key=lambda x: int(x)):
    cols = chargers_info[charger_num]
    has_motos = any('motos' in c for c in cols)
    has_mototaxis = any('mototaxis' in c for c in cols)
    print(f'  Cargador {charger_num}: {len(cols)} columnas | motos={has_motos}, mototaxis={has_mototaxis}')

# Contar sockets activos por tipo
print(f'\n' + '=' * 80)
print('CONTEO DE SOCKETS ACTIVOS POR TIPO')
print('=' * 80)

moto_count = 0
mototaxi_count = 0
unknown_count = 0

for col in vehicle_type_cols:
    vehicle_type = df_chargers[col].iloc[0]  # Tomar primer valor (deberían ser todos iguales)
    if 'MOTO' in vehicle_type.upper() and 'MOTOTAXI' not in vehicle_type.upper():
        moto_count += 1
    elif 'MOTOTAXI' in vehicle_type.upper():
        mototaxi_count += 1
    else:
        unknown_count += 1

total_sockets = moto_count + mototaxi_count + unknown_count
print(f'Total sockets: {total_sockets}')
print(f'  - Motos: {moto_count}')
print(f'  - Mototaxis: {mototaxi_count}')
print(f'  - Desconocido: {unknown_count}')

# Calcular información de chargers
print(f'\n' + '=' * 80)
print('INFORMACIÓN DE CARGADORES')
print('=' * 80)

n_chargers = len(set(int(n) for n in chargers_info.keys()))
print(f'Total cargadores: {n_chargers}')
sockets_per_charger = total_sockets / n_chargers if n_chargers > 0 else 0
print(f'Sockets por cargador: {sockets_per_charger:.1f}')

# Verificar datos de motos y mototaxis en las columnas del cargador
motos_in_chargers = sum(len([c for c in cols if 'motos' in c]) for cols in chargers_info.values())
mototaxis_in_chargers = sum(len([c for c in cols if 'mototaxis' in c]) for cols in chargers_info.values())

print(f'Métricas de motos en cargadores: {motos_in_chargers}')
print(f'Métricas de mototaxis en cargadores: {mototaxis_in_chargers}')

# BESS capacity
df_bess = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
bess_capacity = df_bess['soc_kwh'].max()
bess_avg_soc = df_bess['soc_percent'].mean()
bess_max_power = max(df_bess['bess_charge_kwh'].max(), df_bess['bess_discharge_kwh'].max())

print(f'\n' + '=' * 80)
print('CONFIGURACIÓN BESS')
print('=' * 80)
print(f'Capacidad máxima: {bess_capacity:.1f} kWh')
print(f'SOC promedio: {bess_avg_soc:.2f}%')
print(f'Potencia máxima (carga/descarga): {bess_max_power:.2f} kW')

# Solar
df_solar = pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
solar_total_energy = df_solar['energia_kwh'].sum()
solar_max_power = df_solar['potencia_kw'].max()

print(f'\n' + '=' * 80)
print('CONFIGURACIÓN SOLAR')
print('=' * 80)
print(f'Energía anual total: {solar_total_energy:,.0f} kWh')
print(f'Max potencia: {solar_max_power:.2f} kW')

# Mall
df_mall = pd.read_csv('data/oe2/demandamallkwh/demandamallhorakwh.csv')
mall_total = df_mall['mall_demand_kwh'].sum()
mall_avg = df_mall['mall_demand_kwh'].mean()
mall_max = df_mall['mall_demand_kwh'].max()

print(f'\n' + '=' * 80)
print('CONFIGURACIÓN MALL')
print('=' * 80)
print(f'Demanda anual total: {mall_total:,.0f} kWh')
print(f'Demanda promedio (horaria): {mall_avg:.2f} kW')
print(f'Demanda máxima: {mall_max:.2f} kW')

# Resumen para JSON
print(f'\n' + '=' * 80)
print('RESUMEN PARA dataset_config_v7.json')
print('=' * 80)

config_summary = {
    "system": {
        "pv_capacity_kwp": 4050.0,
        "bess_capacity_kwh": bess_capacity,
        "bess_max_power_kw": float(bess_max_power),
        "bess_avg_soc_percent": float(bess_avg_soc),
        "n_chargers": n_chargers,
        "n_sockets_total": total_sockets,
        "charger_power_kw": 7.4,
        "sockets_per_charger": float(sockets_per_charger)
    },
    "vehicles": {
        "motos": {
            "count": moto_count,
            "sockets": moto_count,
            "chargers_assigned": n_chargers // 2 if mototaxi_count > 0 else n_chargers
        },
        "mototaxis": {
            "count": mototaxi_count,
            "sockets": mototaxi_count,
            "chargers_assigned": n_chargers // 2 if mototaxi_count > 0 else 0
        }
    },
    "demand": {
        "mall_annual_kwh": float(mall_total),
        "mall_avg_hourly_kw": float(mall_avg),
        "mall_max_hourly_kw": float(mall_max),
        "ev_annual_kwh": 52_613_744.0  # Aproximado del dataset compilado
    },
    "solar": {
        "annual_kwh": float(solar_total_energy),
        "max_power_kw": float(solar_max_power)
    }
}

print(json.dumps(config_summary, indent=2))

# Guardar resumen a archivo
with open('data_structure_summary.json', 'w') as f:
    json.dump(config_summary, f, indent=2)
print(f'\n✓ Resumen guardado en: data_structure_summary.json')
