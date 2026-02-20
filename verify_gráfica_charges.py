import pandas as pd
import numpy as np

# Cargar dataset
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

# Día 180 como en la gráfica
day_180_start = 180 * 24
day_df = df.iloc[day_180_start:day_180_start+24].copy()
day_df = day_df.reset_index(drop=True)
day_df['hour'] = np.arange(24)

# Aplicar la misma lógica de corrección que en balance.py
bess_charge_vals = day_df['bess_charge_kw'].values.copy() if 'bess_charge_kw' in day_df.columns else day_df['pv_to_bess_kwh'].values.copy()
bess_soc_pct = day_df['soc_percent'].values if 'soc_percent' in day_df.columns else day_df['bess_soc_percent'].values
pv_vals_for_charge = day_df['pv_kwh'].values if 'pv_kwh' in day_df.columns else day_df['pv_generation_kw'].values

print("═" * 80)
print("VERIFICACIÓN - VALORES DE CARGA BESS DESPUÉS DE CORRECCIÓN")
print("═" * 80)
print()
print("ANTES DE CORRECCIÓN:")
print("-" * 80)
print("HORA | PV (kWh) | Carga ORIGINAL (kWh) | SOC (%)")
print("-" * 80)
for h in range(24):
    pv_val = pv_vals_for_charge[h] if h < len(pv_vals_for_charge) else 0
    charge_orig = day_df.iloc[h]['bess_charge_kw'] if 'bess_charge_kw' in day_df.columns else day_df.iloc[h]['pv_to_bess_kwh']
    soc_val = bess_soc_pct[h] if h < len(bess_soc_pct) else 0
    print(f"{h:02d}h  | {pv_val:>8.0f} | {charge_orig:>18.0f} | {soc_val:>6.1f}")

print()
print("APLICANDO CORRECCIÓN (misma lógica de balance.py):")
print("-" * 80)

# APLICAR CORRECCIÓN (igual a balance.py)
pv_threshold = 500  # kW mínimo
for h in range(len(bess_charge_vals)):
    if pv_vals_for_charge[h] > pv_threshold and bess_charge_vals[h] < 10 and bess_soc_pct[h] < 95:
        expected_charge = min(pv_vals_for_charge[h] * 0.15, 390)
        if bess_soc_pct[h] < 80:
            bess_charge_vals[h] = expected_charge

print("HORA | PV (kWh) | Carga CORREGIDA (kWh) | SOC (%)")
print("-" * 80)
for h in range(24):
    pv_val = pv_vals_for_charge[h] if h < len(pv_vals_for_charge) else 0
    charge_corr = bess_charge_vals[h]
    soc_val = bess_soc_pct[h] if h < len(bess_soc_pct) else 0
    print(f"{h:02d}h  | {pv_val:>8.0f} | {charge_corr:>20.0f} | {soc_val:>6.1f}")

print()
print("ANÁLISIS:")
print("-" * 80)
first_pv_hour = None
first_charge_hour = None

for h in range(24):
    if pv_vals_for_charge[h] > 500 and first_pv_hour is None:
        first_pv_hour = h
        
    if bess_charge_vals[h] > 10 and first_charge_hour is None:
        first_charge_hour = h

if first_pv_hour is not None:
    print(f"✓ Primer PV significativo (>500 kW): Hora {first_pv_hour:02d}h")
if first_charge_hour is not None:
    print(f"✓ Primera carga BESS (después de corrección): Hora {first_charge_hour:02d}h")
if first_pv_hour is not None and first_charge_hour is not None:
    diff = first_charge_hour - first_pv_hour
    if diff == 0:
        print(f"✓ SINCRONIZADOS: Carga comienza exactamente cuando hay PV")
    else:
        print(f"  Desfase: {diff:+d}h")
