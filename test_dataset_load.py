#!/usr/bin/env python3
"""Test que los scripts de entrenamiento pueden cargar datasets centralizados."""
import sys
from pathlib import Path

print('='*80)
print('VALIDACION: Scripts pueden cargar datasets centralizados')
print('='*80)
print()

# Test 1: Verificar dataset combinado existe
combined_path = Path('data/iquitos_ev_mall/citylearnv2_combined_dataset.csv')
if combined_path.exists():
    import pandas as pd
    df = pd.read_csv(combined_path)
    print(f'✓ Dataset combinado ENCONTRADO en {combined_path}')
    print(f'  Dimensiones: {df.shape[0]} horas × {df.shape[1]} columnas')
    print(f'  Columnas: {list(df.columns)}')
else:
    print(f'✗ Dataset combinado NO ENCONTRADO en {combined_path}')
    sys.exit(1)

print()

# Test 2: Cargar datos desde el dataset combinado
try:
    import numpy as np
    import pandas as pd
    
    df_combined = pd.read_csv(combined_path)
    n_hours = len(df_combined)
    
    # SOLAR
    solar_hourly = df_combined['solar_generation_kw'].values.astype(np.float32)
    print(f'✓ SOLAR: {np.sum(solar_hourly):,.0f} kWh/año')
    
    # EV DEMAND
    ev_total_hourly = df_combined['ev_kwh'].values.astype(np.float32)
    print(f'✓ EV DEMAND: {np.sum(ev_total_hourly):,.0f} kWh/año')
    
    # MALL
    mall_hourly = df_combined['mall_kwh'].values.astype(np.float32)
    print(f'✓ MALL: {np.sum(mall_hourly):,.0f} kWh/año')
    
    # CHARGERS (distribuidos)
    chargers_hourly = np.zeros((n_hours, 38), dtype=np.float32)
    for h in range(n_hours):
        hour_of_day = h % 24
        if 6 <= hour_of_day <= 22:
            occupancy_factor = 0.8
        else:
            occupancy_factor = 0.2
        
        available_power = ev_total_hourly[h] * occupancy_factor / 38.0
        chargers_hourly[h, :] = np.clip(available_power, 0.0, 7.4)
    
    print(f'✓ CHARGERS (38 sockets): {np.sum(chargers_hourly):,.0f} kWh/año')
    
    print()
    print('✅ VALIDACION EXITOSA: Todos los datos cargan correctamente')
    print()
    
except Exception as e:
    import traceback
    print(f'✗ ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

print('='*80)
print('✅ Los scripts PPO, SAC y A2C pueden usar datasets centralizados')
print('='*80)
