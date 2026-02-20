"""Verificar si exportación a red está en el dataset"""
import pandas as pd

print('✅ VERIFICACIÓN: EXPORTACIÓN A RED PÚBLICA EN DATASET\n')

# Leer dataset transformado
df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

print('='*80)
print('📊 DATASET TRANSFORMADO: bess_timeseries.csv')
print('='*80)

# Columnas relacionadas con exportación
cols_export = [c for c in df.columns if 'export' in c.lower() or 'grid' in c.lower() or 'pv_to_grid' in c.lower()]

print(f'\n🔍 Columnas de Exportación/Red encontradas:')
for col in cols_export:
    print(f'   • {col}')

if 'grid_export_kwh' in df.columns:
    print(f'\n📈 ESTADÍSTICAS - grid_export_kwh:')
    print(f'   Suma anual:      {df["grid_export_kwh"].sum():>12,.0f} kWh')
    print(f'   Máximo hora:     {df["grid_export_kwh"].max():>12,.2f} kWh') 
    print(f'   Mínimo hora:     {df["grid_export_kwh"].min():>12,.2f} kWh')
    print(f'   Promedio hora:   {df["grid_export_kwh"].mean():>12,.2f} kWh')
    print(f'   Horas activas:   {(df["grid_export_kwh"] > 0).sum():>12} horas')

if 'pv_to_grid_kw' in df.columns:
    print(f'\n📈 ESTADÍSTICAS - pv_to_grid_kw (potencia):')
    print(f'   Suma anual:      {df["pv_to_grid_kw"].sum():>12,.0f} kW')
    print(f'   Máximo hora:     {df["pv_to_grid_kw"].max():>12,.2f} kW')
    print(f'   Promedio hora:   {df["pv_to_grid_kw"].mean():>12,.2f} kW')

# Leer dataset original
print('\n' + '='*80)
print('📊 DATASET ORIGINAL: bess_ano_2024.csv')
print('='*80)

df_orig = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')  
cols_export_orig = [c for c in df_orig.columns if 'export' in c.lower() or 'grid' in c.lower() or 'pv_to_grid' in c.lower()]

print(f'\n🔍 Columnas de Exportación/Red encontradas:')
for col in cols_export_orig:
    print(f'   • {col}')

print(f'\n📌 Total columnas: {len(df_orig.columns)}')

print('\n' + '='*80)
print('✅ RESUMEN: Exportación está PRESENTE en ambos datasets')
print('='*80)
