import pandas as pd
import numpy as np

# Cargar dataset
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

# Verificar cuándo comienza PV el día 180 
day_180_start = 180 * 24  # Inicio del día 180
day_180_end = (180 + 1) * 24  # Fin del día 180
day_df = df.iloc[day_180_start:day_180_end]

print("═" * 80)
print("ANÁLISIS DÍA 180 - GENERACIÓN PV Y CARGA BESS")
print("═" * 80)
print()

# Convertir hour a simple 0-23
day_df = day_df.reset_index(drop=True)
day_df['hour'] = np.arange(24)

# Mostrar cómo comienza PV y carga BESS
print("HORA | PV (kWh) | PV→BESS (kWh) | Carga (Sí/No)")
print("-" * 80)
for hour in range(24):
    row = day_df.iloc[hour]
    pv_val = row['pv_kwh'] if 'pv_kwh' in row else row.get('pv_generation_kw', 0)
    pv_to_bess = row['pv_to_bess_kwh'] if 'pv_to_bess_kwh' in row else 0
    has_charge = "SÍ" if pv_to_bess > 1 else "NO"
    
    print(f"{hour:02d}h  | {pv_val:>8.0f} | {pv_to_bess:>13.0f} | {has_charge:>13}")

print()
print("HORAS CRÍTICAS:")
print("-" * 80)

# Primera hora con PV > 100
first_pv_hour = None
for hour in range(24):
    row = day_df.iloc[hour]
    pv_val = row['pv_kwh'] if 'pv_kwh' in row else row.get('pv_generation_kw', 0)
    if pv_val > 100:
        first_pv_hour = hour
        print(f"✓ PRIMER PV SIGNIFICATIVO: Hora {hour:02d}h con {pv_val:.0f} kWh")
        break

# Primera hora con carga BESS
first_charge_hour = None
for hour in range(24):
    row = day_df.iloc[hour]
    pv_to_bess = row['pv_to_bess_kwh'] if 'pv_to_bess_kwh' in row else 0
    if pv_to_bess > 10:
        first_charge_hour = hour
        print(f"✓ PRIMERA CARGA BESS: Hora {hour:02d}h con {pv_to_bess:.0f} kWh")
        break

if first_pv_hour is not None and first_charge_hour is not None:
    diff = first_charge_hour - first_pv_hour
    if diff == 0:
        print(f"✓ SINCRONIZACIÓN: Perfecta - Carga inicia exactamente cuando comienza PV")
    else:
        print(f"✗ DESFASE: Carga inicia {diff:+d}h después del primer PV significativo")

print()
