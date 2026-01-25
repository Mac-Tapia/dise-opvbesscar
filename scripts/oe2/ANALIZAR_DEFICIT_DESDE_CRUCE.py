"""
Analizar energía que solar NO puede cubrir desde cruce hasta cierre.
"""

import pandas as pd
import numpy as np

# Cargar datos
df_ev = pd.read_csv('data/oe2/perfil_horario_carga.csv')
df_pv = pd.read_csv('data/oe2/pv_profile_24h.csv')

# Crear perfil solar 15 min
pv_15min = []
for h in range(24):
    pv_hour = df_pv[df_pv['hour'] == h]['pv_kwh'].mean() if len(df_pv[df_pv['hour'] == h]) > 0 else 0
    for i in range(4):
        pv_15min.append(pv_hour / 4.0)

# Perfil EV 15 min (primer día)
ev_15min = df_ev.head(96)['energy_kwh'].values

print("="*70)
print("ANÁLISIS: SOLAR NO PUEDE CUBRIR EV DESDE CRUCE HASTA CIERRE")
print("="*70)
print()

# CRUCE: Intervalo 64 = 16:00
# CIERRE: Intervalo 88 = 22:00
intervalo_cruce = 64  # 16:00
intervalo_cierre = 88  # 22:00

# Energía desde cruce hasta cierre
ev_total_cruce_cierre = sum(ev_15min[intervalo_cruce:intervalo_cierre])
solar_total_cruce_cierre = sum(pv_15min[intervalo_cruce:intervalo_cierre])

# Déficit = lo que solar NO puede cubrir
deficit_cruce_cierre = ev_total_cruce_cierre - solar_total_cruce_cierre

print(f"PERÍODO: 16:00 - 22:00 (6 horas)")
print(f"  Intervalo inicio: {intervalo_cruce} (16:00)")
print(f"  Intervalo fin:    {intervalo_cierre-1} (21:45)")
print()
print(f"DEMANDA EV 16h-22h:        {ev_total_cruce_cierre:>8.1f} kWh")
print(f"SOLAR DISPONIBLE 16h-22h:  {solar_total_cruce_cierre:>8.1f} kWh")
print(f"─" * 70)
print(f"DÉFICIT (Solar NO cubre):  {deficit_cruce_cierre:>8.1f} kWh")
print()

# Desglose por hora
print("DESGLOSE POR HORA:")
print(f"{'Hora':<10} {'EV (kWh)':<12} {'Solar (kWh)':<14} {'Déficit (kWh)':<15}")
print("─" * 70)

for hora in range(16, 22):
    idx_inicio = hora * 4
    idx_fin = (hora + 1) * 4

    ev_hora = sum(ev_15min[idx_inicio:idx_fin])
    solar_hora = sum(pv_15min[idx_inicio:idx_fin])
    deficit_hora = max(0, ev_hora - solar_hora)

    print(f"{hora:02d}:00-{hora+1:02d}:00  {ev_hora:>8.2f}     {solar_hora:>8.2f}       {deficit_hora:>8.2f}")

print()
print(f"✅ BESS debe cubrir: {deficit_cruce_cierre:.1f} kWh desde 16h hasta 22h")
print(f"✅ BESS dimensionado: 360 kWh (capacidad para cubrir {360*0.8:.0f} kWh)")
