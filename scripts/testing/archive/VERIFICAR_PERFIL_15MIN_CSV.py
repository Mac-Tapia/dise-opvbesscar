"""
Verificación del archivo perfil_horario_carga.csv
con resolución de 15 minutos
"""
import pandas as pd

# Cargar archivo
df = pd.read_csv('data/oe2/perfil_horario_carga.csv')

print("=" * 70)
print("VERIFICACIÓN PERFIL CSV - RESOLUCIÓN 15 MINUTOS")
print("=" * 70)
print(f"\nIntervalos totales: {len(df)}")
print(f"Columnas: {df.columns.tolist()}")

print(f"\n{'='*70}")
print("PRIMEROS 12 INTERVALOS (primeras 3 horas):")
print("="*70)
print(df.head(12).to_string())

print(f"\n{'='*70}")
print("INTERVALOS DE HORA PICO (18h = intervalos 72-75):")
print("="*70)
print(df.iloc[72:76].to_string())

# Calcular energía total
if 'energy_kwh' in df.columns:
    total_energy = df['energy_kwh'].sum()
    print(f"\n{'='*70}")
    print(f"ENERGÍA TOTAL: {total_energy:.2f} kWh/día")
    print("="*70)
elif 'power_kw' in df.columns:
    total_energy = df['power_kw'].sum() * 0.25  # kW × 0.25h = kWh
    print(f"\n{'='*70}")
    print(f"ENERGÍA TOTAL (calculada): {total_energy:.2f} kWh/día")
    print("="*70)
