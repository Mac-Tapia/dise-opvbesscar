import pandas as pd
import numpy as np
from pathlib import Path

print('=' * 80)
print('SINCRONIZANDO DATASET: Original → Transformado')
print('=' * 80)

# Cargar original (tiene datos correctos de descarga)
df_orig = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
df_trans = pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv')

print(f'\nOriginal: {len(df_orig)} filas, ({len(df_orig.columns)} cols)')
print(f'Transformado: {len(df_trans)} filas, ({len(df_trans.columns)} cols)\n')

# Verificar que tengan mismo tamaño
if len(df_orig) != len(df_trans):
    print(f'ERROR: Tamaños diferentes! {len(df_orig)} vs {len(df_trans)}')
else:
    print('✓ Mismo número de filas\n')

# Mapear columnas del original al transformado
print('SINCRONIZANDO COLUMNAS DE BESS:')

# Estas columnas deben venir del original (tienen datos correctos)
mapping = {
    'bess_charge_kwh': 'bess_energy_stored_hourly_kwh',
    'bess_discharge_kwh': 'bess_energy_delivered_hourly_kwh',
    'bess_to_ev_kwh': 'bess_to_ev_kwh',  # Mantener si existe
    'bess_to_mall_kwh': 'bess_to_mall_kwh',  # Mantener si existe
}

for col_target, col_source in mapping.items():
    if col_source in df_orig.columns and col_target in df_trans.columns:
        # Reemplazar datos transformados con datos originales
        orig_sum = df_orig[col_source].sum()
        trans_sum_before = df_trans[col_target].sum()
        
        df_trans[col_target] = df_orig[col_source].values
        trans_sum_after = df_trans[col_target].sum()
        
        print(f'  {col_target}:')
        print(f'    Original: {orig_sum:,.0f} kWh')
        print(f'    Antes: {trans_sum_before:,.0f} kWh')
        print(f'    Después: {trans_sum_after:,.0f} kWh ✓')

# Guardar transformado sincronizado
df_trans.to_csv('data/iquitos_ev_mall/bess_timeseries.csv', index=False)

print('\n' + '=' * 80)
print('✅ Dataset transformado SINCRONIZADO correctamente')
print('=' * 80)

# Validación final
print('\nVALIDACIÓN:')
print(f'  Descarga BESS: {df_trans["bess_discharge_kwh"].sum():,.0f} kWh (debe ser ~594k)')
print(f'  Carga BESS: {df_trans["bess_charge_kwh"].sum():,.0f} kWh (debe ser ~623k)')
