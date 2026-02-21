import pandas as pd
import numpy as np

print('='*80)
print('VALIDACIÓN DE 6 FASES EN DATASET REGENERADO')
print('='*80)

# Cargar dataset
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

print(f'\n✓ Dataset cargado: {len(df)} filas, {len(df.columns)} columnas')

# VALIDACIÓN 1: Verificar 6 FASES intactas
print('\n' + '='*80)
print('VALIDACIÓN 1: 6 FASES INTACTAS')
print('='*80)

if 'bess_mode' in df.columns:
    modes = df['bess_mode'].value_counts().sort_index()
    print('\nModos BESS detectados (cada hora debe tener UNA acción):')
    for mode, count in modes.items():
        pct = (count / len(df)) * 100
        print(f'  {mode:15s}: {count:5d} horas ({pct:5.1f}%)')
    
    # Verificar que TODAS las horas tengan un modo asignado
    total_assigned = modes.sum()
    if total_assigned == len(df):
        print(f'\n✅ CORRECTO: 100% de horas tienen modo asignado')
    else:
        print(f'\n⚠️ ERROR: {len(df) - total_assigned} horas sin modo asignado')
else:
    print('⚠️ Columna bess_mode no encontrada')

# VALIDACIÓN 2: Conflictos carga+descarga
print('\n' + '='*80)
print('VALIDACIÓN 2: CONFLICTOS CARGA + DESCARGA SIMULTÁNEOS')
print('='*80)

if 'bess_charge_kwh' in df.columns and 'bess_discharge_kwh' in df.columns:
    # Horas con ambas acciones > 0
    conflict = (df['bess_charge_kwh'] > 0.1) & (df['bess_discharge_kwh'] > 0.1)
    n_conflicts = conflict.sum()
    
    print(f'\nHoras con CONFLICTO (carga AND descarga simultáneamente):')
    print(f'  ANTES (sin elif): 768 horas')
    print(f'  AHORA:            {n_conflicts} horas')
    
    if n_conflicts < 100:
        print(f'\n✅ CORRECTO: Conflictos reducidos de 768 → {n_conflicts} (<100)')
    else:
        print(f'\n⚠️  ERROR: Aún hay {n_conflicts} horas de conflicto')
    
    # Mostrar ejemplos de conflictos if hay
    if n_conflicts > 0:
        print(f'\nEjemplos de conflictos encontrados:')
        examples = df[conflict].head(5)
        for idx, row in examples.iterrows():
            hora = idx % 24
            print(f'  Hora {idx}: Carga={row["bess_charge_kwh"]:.1f}kWh, Descarga={row["bess_discharge_kwh"]:.1f}kWh')
else:
    print('⚠️ Columnas de carga/descarga no encontradas')

# VALIDACIÓN 3: Balance energético
print('\n' + '='*80)
print('VALIDACIÓN 3: BALANCE ENERGÉTICO')
print('='*80)

if 'bess_balance_error_hourly_kwh' in df.columns:
    balance_error = df['bess_balance_error_hourly_kwh'].sum()
    print(f'\nDiscrepancia balance energético:')
    print(f'  ANTES (if/if):    136,796 kWh')
    print(f'  AHORA (elif):     {balance_error:,.0f} kWh')
    
    if abs(balance_error) < 50000:
        print(f'\n✅ CORRECTO: Error < 50,000 kWh')
    else:
        print(f'\n⚠️  ERROR: Discrepancia aún alta')
else:
    print('⚠️ Columna bess_balance_error_hourly_kwh no encontrada')

# VALIDACIÓN 4: Distribucion de fases (horas por fase)
print('\n' + '='*80)
print('VALIDACIÓN 4: DISTRIBUCIÓN ESPERADA DE FASES')
print('='*80)

if 'bess_mode' in df.columns:
    print('\nEsperado:')
    print('  FASE 1 (6-9h):         3h/día × 365 días = 1,095 horas (~12%)')
    print('  FASE 2 (carga):        ~2,000-3,000 horas (~23-34%)')
    print('  FASE 3 (holding 100%): ~1,500-2,500 horas (~17-29%)')
    print('  FASE 4 (peak shaving): ~100-500 horas (~1-6%)')
    print('  FASE 5 (descarga EV):  ~1,000-2,000 horas (~11-23%)')
    print('  FASE 6 (reposo):       8h/día × 365 días = 2,920 horas (~33%)')
    print()
    print('Real:')
    
    phase_counts = df['bess_mode'].value_counts()
    for phase in ['charge', 'discharge', 'idle', 'holding']:
        if phase in phase_counts.index:
            count = phase_counts[phase]
            pct = (count / len(df)) * 100
            print(f'  {phase:20s}: {count:5d} horas ({pct:5.1f}%)')

print('\n' + '='*80)
print('✅ VALIDACIÓN COMPLETADA')
print('='*80)
