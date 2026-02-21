#!/usr/bin/env python
import pandas as pd

df = pd.read_csv('data/interim/oe2/bess/bess_ano_2024.csv')
h = df.iloc[155]

print(f"\nHora 11, Día 7 (Índice global 155):")
print(f"  pv_to_bess_kwh: {h['pv_to_bess_kwh']:.2f}")
print(f"  bess_to_ev_kwh: {h['bess_to_ev_kwh']:.2f}")
print(f"  bess_to_mall_kwh: {h['bess_to_mall_kwh']:.2f}")

charge = h['pv_to_bess_kwh']
discharge = h['bess_to_ev_kwh'] + h['bess_to_mall_kwh']

print(f"\nCarga total PV->BESS: {charge:.2f} kWh")
print(f"Descarga total BESS: {discharge:.2f} kWh")

if charge > 0.1 and discharge > 0.1:
    print(f"\n❌ PROBLEMA: ¡¡Carga Y descarga simultáneamente!!")
else:
    print(f"\n✓ OK: Mutuamente excluyentes (sin carga-descarga simultánea)")
