#!/usr/bin/env python
"""Validar lógica de picos en BESS simulado."""
import pandas as pd
import numpy as np

# Leer el CSV simulado y analizar picos
df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')

# Calcular demanda total por hora
df['total_demand'] = df['ev_demand_kwh'] + df['mall_demand_kwh']

# Picos
max_total = df['total_demand'].max()
max_ev = df['ev_demand_kwh'].max()
max_mall = df['mall_demand_kwh'].max()
max_pv = df['pv_generation_kwh'].max()

print("=" * 60)
print("ANÁLISIS DE PICOS - BESS SIMULADO")
print("=" * 60)
print(f"\nPicos instantáneos (horarios):")
print(f"  Demanda total (EV+Mall):  {max_total:.1f} kW")
print(f"  Demanda EV:               {max_ev:.1f} kW")
print(f"  Demanda Mall:             {max_mall:.1f} kW")
print(f"  Generación PV:            {max_pv:.1f} kW")

# Analizar si BESS ayuda con picos
print(f"\nCobertura BESS en picos:")
max_bess_discharge = df['bess_discharge_kwh'].max()
print(f"  Máxima descarga BESS:     {max_bess_discharge:.1f} kW")

# Horas donde total_demand > 2000
hours_over_2000 = (df['total_demand'] > 2000).sum()
peak_hours_avg = df[df['total_demand'] > 2000]['total_demand'].mean() if hours_over_2000 > 0 else 0

print(f"\nControl de picos (2000 kW):")
print(f"  Horas/año con demanda > 2000 kW: {hours_over_2000}")
print(f"  Promedio en esas horas:         {peak_hours_avg:.1f} kW")

# Ver ejemplo de hora con alto pico
if hours_over_2000 > 0:
    peak_idx = df['total_demand'].idxmax()
    peak_row = df.loc[peak_idx]
    print(f"\nHora con máximo pico:")
    print(f"  EV:          {peak_row['ev_demand_kwh']:.1f} kW")
    print(f"  Mall:        {peak_row['mall_demand_kwh']:.1f} kW")
    print(f"  Total:       {peak_row['total_demand']:.1f} kW")
    print(f"  PV gen:      {peak_row['pv_generation_kwh']:.1f} kW")
    print(f"  BESS desc:   {peak_row['bess_discharge_kwh']:.1f} kW")
    print(f"  BESS SOC:    {peak_row['soc_percent']:.1f}%")

    # Mostrar tabla de horas sobre 2000 kW (primeras 10)
    print(f"\nPrimeras 10 horas con demanda > 2000 kW:")
    peak_hours = df[df['total_demand'] > 2000].head(10)
    for idx, row in peak_hours.iterrows():
        demand_net = row['total_demand'] - row['bess_discharge_kwh']
        print(f"  h={idx:4d} | total={row['total_demand']:7.1f} | BESS={row['bess_discharge_kwh']:6.1f} | red={demand_net:7.1f} kW")

print("\n" + "=" * 60)
