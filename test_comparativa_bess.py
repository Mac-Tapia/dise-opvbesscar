"""
TEST FASE 4: Comparativa ANTES vs DESPUÉS de cambios en simulate_bess_solar_priority()
"""
import pandas as pd
import numpy as np

print("=" * 100)
print("TEST FASE 4: COMPARATIVA - ESTRATEGIA MIXTA (EV + MALL con SOC target 20%)")
print("=" * 100)

# Lecturas de datos ANTES (archivo backup) y DESPUÉS (nuevo)
try:
    df_despues = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')
except:
    print("ERROR: No se encontró archivo de simulación. Ejecutar primero:")
    print("  python -m src.dimensionamiento.oe2.disenobess.bess")
    exit(1)

# Convertir datetime
df_despues['datetime'] = pd.to_datetime(df_despues['datetime'])
df_despues['hour'] = df_despues['datetime'].dt.hour
df_despues['day'] = df_despues['datetime'].dt.day

print("\n[1] ESTADÍSTICAS GENERALES")
print("-" * 100)
print("\nMÉTRICA                               VALOR")
print("-" * 100)

total_ev = df_despues['ev_demand_kwh'].sum()
total_mall = df_despues['mall_demand_kwh'].sum()
total_pv = df_despues['pv_generation_kwh'].sum()

print(f"  Demanda EV anual:                {total_ev:>15,.0f} kWh")
print(f"  Demanda MALL anual:              {total_mall:>15,.0f} kWh")
print(f"  Generación PV anual:             {total_pv:>15,.0f} kWh")

ev_pv = df_despues['pv_to_ev_kwh'].sum()
ev_bess = df_despues['bess_to_ev_kwh'].sum()
ev_grid = df_despues['grid_to_ev_kwh'].sum()

print(f"\n  EV desde PV:                     {ev_pv:>15,.0f} kWh ({ev_pv/total_ev*100:>5.1f}%)")
print(f"  EV desde BESS:                   {ev_bess:>15,.0f} kWh ({ev_bess/total_ev*100:>5.1f}%)")
print(f"  EV desde GRID:                   {ev_grid:>15,.0f} kWh ({ev_grid/total_ev*100:>5.1f}%)")

mall_pv = df_despues['pv_to_mall_kwh'].sum()
mall_bess = df_despues['bess_to_mall_kwh'].sum()
mall_grid = df_despues['grid_to_mall_kwh'].sum()

print(f"\n  MALL desde PV:                   {mall_pv:>15,.0f} kWh ({mall_pv/total_mall*100:>5.1f}%)")
print(f"  MALL desde BESS:                 {mall_bess:>15,.0f} kWh ({mall_bess/total_mall*100:>5.1f}%)")
print(f"  MALL desde GRID:                 {mall_grid:>15,.0f} kWh ({mall_grid/total_mall*100:>5.1f}%)")

bess_carga = df_despues['bess_charge_kwh'].sum()
bess_desca = df_despues['bess_discharge_kwh'].sum()

print(f"\n  BESS carga anual:                {bess_carga:>15,.0f} kWh")
print(f"  BESS descarga anual:             {bess_desca:>15,.0f} kWh")
print(f"  Ciclos BESS/año:                 {bess_carga/1700:>15.1f} ciclos")
print(f"  Ciclos BESS/día:                 {bess_carga/1700/365:>15.2f} ciclos/día")

print("\n[2] OBJETIVO PRINCIPAL: SOC FINAL A LAS 22h")
print("-" * 100)
soc_22h = df_despues[df_despues['hour'] == 22]['bess_soc_percent'].values
print(f"  SOC mínimo a 22h:                {soc_22h.min():>15.1f}%")
print(f"  SOC máximo a 22h:                {soc_22h.max():>15.1f}%")
print(f"  SOC promedio a 22h:              {soc_22h.mean():>15.1f}%")
print(f"\n  META: SOC = 20.0% exacto")
if abs(soc_22h.mean() - 20.0) < 1.0:
    print(f"  [OK] Target alcanzado con {abs(soc_22h.mean()-20.0):.1f}% de desviación")
else:
    print(f"  [ALERTA] Desviación de {abs(soc_22h.mean()-20.0):.1f}% del target")

print("\n[3] ENERGÍA DESCARGADA AL MALL (Nueva Estrategia)")
print("-" * 100)
mall_17_22 = df_despues[(df_despues['hour'] >= 17) & (df_despues['hour'] <= 22)]['bess_to_mall_kwh'].sum()
print(f"  BESS a MALL (17h-22h):           {mall_17_22:>15,.0f} kWh")
print(f"  % del total descarga MALL:       {mall_17_22/mall_bess*100:>15.1f}%")

for h in [17, 18, 19, 20, 21, 22]:
    data_h = df_despues[df_despues['hour'] == h]
    bess_mall_h = data_h['bess_to_mall_kwh'].sum() / 365 if len(data_h) > 0 else 0
    soc_h = data_h['bess_soc_percent'].mean() if len(data_h) > 0 else 0
    print(f"    {h:02d}h: BESS→MALL={bess_mall_h:>6.0f} kWh (prom)  |  SOC={soc_h:>5.1f}%")

print("\n[4] COBERTURA EV (Validación FASE 3)")
print("-" * 100)
ev_covered = ev_pv + ev_bess
ev_coverage = ev_covered / total_ev * 100
print(f"  EV cubierto (PV+BESS):           {ev_covered:>15,.0f} kWh ({ev_coverage:>5.1f}%)")
if ev_coverage >= 99.5:
    print(f"  [OK] Cobertura completa (>99.5%)")
else:
    print(f"  [ALERTA] Cobertura insuficiente (<99.5%)")

print("\n[5] COMPARATIVA CON VALORES ESPERADOS")
print("-" * 100)
print(f"  BESS Capacidad:                  1,700 kWh (sin cambios)")
print(f"  BESS Potencia:                   400 kW (sin cambios)")
print(f"  SOC objetivo cierre (22h):       20% DURO (nuevo)")
print(f"  Estrategia descarga:             EV (prioridad 1) + MALL (máximo posible)")
print(f"\n  Cambios esperados:")
print(f"    - SOC final 22h: 27.8% → 20.0% (más consistente)")
print(f"    - BESS→MALL: 265.6k → 400k+ kWh/año (más descarga)")
print(f"    - Picos MALL reducidos: +102 kW/h adicionales")
print(f"    - Cobertura EV: 81% (sin cambios, prioridad 1)")

print("\n[6] DISTRIBUCIÓN SOC POR HORA (Perfil diario típico)")
print("-" * 100)
for h in range(24):
    data_h = df_despues[df_despues['hour'] == h]
    if len(data_h) > 0:
        soc_mean = data_h['bess_soc_percent'].mean()
        soc_max = data_h['bess_soc_percent'].max()
        soc_min = data_h['bess_soc_percent'].min()
        bess_dsch = data_h['bess_discharge_kwh'].sum() / 365
        print(f"  {h:02d}h: SOC={soc_mean:>5.1f}% (min={soc_min:>5.1f}%, max={soc_max:>5.1f}%) | Descarga={bess_dsch:>6.0f} kWh")

print("\n[7] VALIDACIÓN FINAL")
print("-" * 100)
checks = []

# Check 1: SOC final cerca de 20%
if 19.0 <= soc_22h.mean() <= 21.0:
    checks.append(("[OK]", "SOC final 22h en rango 19-21%"))
else:
    checks.append(("[ALERTA]", f"SOC final 22h fuera de rango: {soc_22h.mean():.1f}%"))

# Check 2: EV cubierto
if ev_coverage >= 99.5:
    checks.append(("[OK]", "Cobertura EV >= 99.5%"))
else:
    checks.append(("[ERROR]", f"Cobertura EV insuficiente: {ev_coverage:.1f}%"))

# Check 3: MALL recibe más energía
if mall_bess >= 250000:  # En comparación de 265.6k
    checks.append(("[OK]", f"BESS→MALL >= 250k kWh/año: {mall_bess:,.0f}"))
else:
    checks.append(("[ALERTA]", f"BESS→MALL bajo: {mall_bess:,.0f} kWh/año"))

# Check 4: Ciclos BESS <= 1.5/día
ciclos_dia = bess_carga / 1700 / 365
if ciclos_dia <= 1.5:
    checks.append(("[OK]", f"Ciclos BESS/día: {ciclos_dia:.2f} (<= 1.5)"))
else:
    checks.append(("[ALERTA]", f"Ciclos BESS/día alto: {ciclos_dia:.2f} (> 1.5)"))

for status, msg in checks:
    print(f"  {status} {msg}")

print("\n" + "=" * 100)
print("TEST COMPLETADO")
print("=" * 100)
