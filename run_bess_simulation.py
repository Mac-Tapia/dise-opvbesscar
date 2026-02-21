import sys
sys.path.insert(0, 'src')
import pandas as pd
import numpy as np
from dimensionamiento.oe2.disenobess.bess import simulate_bess_ev_exclusive

print('='*80)
print('REGENERANDO DATASET CON CORRECCIONES (FASE 2→elif, FASE 4 con prioridad)')
print('='*80)

# Cargar datos de CSVs
pv_csv = 'data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv'
ev_csv = 'data/oe2/demandamallkwh/ev_ano_2024.csv'
mall_csv = 'data/oe2/demandamallkwh/mall_ano_2024.csv'

pv_df = pd.read_csv(pv_csv)
ev_df = pd.read_csv(ev_csv)
mall_df = pd.read_csv(mall_csv)

pv_kwh = pv_df.iloc[:, 0].values if len(pv_df.columns) > 0 else pv_df['pv_kwh'].values
ev_kwh = ev_df.iloc[:, 0].values if len(ev_df.columns) > 0 else ev_df['ev_kwh'].values
mall_kwh = mall_df.iloc[:, 0].values if len(mall_df.columns) > 0 else mall_df['mall_kwh'].values

print(f'✓ PV cargado: {len(pv_kwh)} horas')
print(f'✓ EV cargado: {len(ev_kwh)} horas')
print(f'✓ MALL cargado: {len(mall_kwh)} horas')

# Ejecutar simulación
df_sim, metrics = simulate_bess_ev_exclusive(
    pv_kwh=pv_kwh,
    ev_kwh=ev_kwh,
    mall_kwh=mall_kwh,
    capacity_kwh=2000.0,
    power_kw=400.0,
    efficiency=0.95
)

print(f'\n✓ Simulación completada: {len(df_sim)} registros')
print(f'Columnas generadas: {len(df_sim.columns)}')

# Guardar dataset
output_path = 'data/oe2/bess/bess_ano_2024.csv'
df_sim.to_csv(output_path, index=False)
print(f'\n✓ Dataset guardado: {output_path}')

# Mostrar métricas
print('\n' + '='*80)
print('MÉTRICAS ANUALES')
print('='*80)
for key, value in sorted(metrics.items()):
    print(f'{key:40s}: {value:,.2f}')

print('\n' + '='*80)
print('VALIDACIÓN DEL DATASET')
print('='*80)

# Cargar y validar
df_check = pd.read_csv(output_path)
print(f'\nColumnas del dataset: {list(df_check.columns)[:5]}... ({len(df_check.columns)} total)')

# Verificar balance
if 'bess_balance_error_hourly_kwh' in df_check.columns:
    balance_error = df_check['bess_balance_error_hourly_kwh'].sum()
    print(f'Balance error anual: {balance_error:,.2f} kWh')
    
    # Contar horas con conflicto
    conflict_hours = (df_check['bess_charge_kwh'] > 0) & (df_check['bess_discharge_kwh'] > 0)
    print(f'Horas con conflicto carga+descarga: {conflict_hours.sum()} (antes: 768)')
else:
    print('⚠ Columna bess_balance_error_hourly_kwh no encontrada')

# Validar 6 fases
print('\n' + '='*80)
print('VALIDACIÓN DE 6 FASES')
print('='*80)

if 'bess_mode' in df_check.columns:
    modes = df_check['bess_mode'].value_counts()
    print(f'\nModos BESS detectados:')
    for mode, count in modes.items():
        print(f'  {mode:20s}: {count:5d} horas')
else:
    print('⚠ Columna bess_mode no encontrada')

print('\n✅ Validación completada')
