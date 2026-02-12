"""
ANÁLISIS COMPLETO: SOLAR DESPERDICIADO + BESS PARA MALL
========================================================
Objetivo: Calcular cuánta capacidad BESS se necesitaría para:
1. Aprovechar el PV curtailed (desperdiciado)
2. Cubrir demanda del Mall hasta las 22h con BESS

Autor: Análisis OE2 - Iquitos
Fecha: 2026-02-12
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ========================================
# CARGAR DATOS
# ========================================
print("="*70)
print("  ANÁLISIS COMPLETO: SOLAR + BESS + MALL")
print("="*70)

# Rutas
bess_path = Path("data/oe2/bess/bess_simulation_hourly.csv")
solar_path = Path("data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv")
mall_path = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
ev_path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")

# Cargar
bess = pd.read_csv(bess_path)
solar = pd.read_csv(solar_path)
mall = pd.read_csv(mall_path, sep=';')
ev = pd.read_csv(ev_path)

# Preparar hora
bess['h'] = pd.to_datetime(bess['datetime']).dt.hour

# ========================================
# 1. GENERACIÓN SOLAR Y CURTAILMENT
# ========================================
print("\n" + "="*70)
print("1. GENERACIÓN SOLAR Y CURTAILMENT")
print("="*70)

pv_total = solar['ac_energy_kwh'].sum()
curtailed_total = bess['pv_curtailed_kwh'].sum()
pv_usado = pv_total - curtailed_total

print(f"""
   PV Total generado:        {pv_total:>12,.0f} kWh/año ({pv_total/1e6:.2f} GWh)
   PV Curtailed (perdido):   {curtailed_total:>12,.0f} kWh/año ({curtailed_total/1e6:.2f} GWh)
   PV Utilizado:             {pv_usado:>12,.0f} kWh/año ({pv_usado/1e6:.2f} GWh)
   % Desperdiciado:          {curtailed_total/pv_total*100:>12.1f} %
""")

# Curtailment por hora
curt_hora = bess.groupby('h')['pv_curtailed_kwh'].sum()
print("   Curtailment por hora del día:")
for h in range(24):
    bar = "█" * int(curt_hora.get(h, 0) / 50000)
    print(f"      h{h:02d}: {curt_hora.get(h, 0):>10,.0f} kWh/año  {bar}")

# ========================================
# 2. DEMANDA MALL POR HORA (NOCTURNA)
# ========================================
print("\n" + "="*70)
print("2. DEMANDA MALL POR HORA (análisis nocturno h17-h22)")
print("="*70)

# Mall demand
mall_col = [c for c in mall.columns if 'kwh' in c.lower() or 'demand' in c.lower()]
if mall_col:
    mall_demand = mall[mall_col[0]].values[:8760]
else:
    mall_demand = mall.iloc[:8760, 1].values

mall_df = pd.DataFrame({'mall_kwh': mall_demand})
mall_df['h'] = mall_df.index % 24
mall_hora = mall_df.groupby('h')['mall_kwh'].mean()

print("\n   Demanda Mall promedio por hora (kW):")
for h in range(24):
    bar = "█" * int(mall_hora[h] / 100)
    sol = "☀" if 6 <= h <= 17 else "🌙"
    print(f"      h{h:02d}: {mall_hora[h]:>8,.0f} kW  {sol} {bar}")

# Periodo nocturno sin sol (h18-h22)
mall_nocturno = mall_df[(mall_df['h'] >= 18) & (mall_df['h'] <= 22)]['mall_kwh'].sum() / 365
print(f"\n   Demanda Mall nocturna (h18-h22): {mall_nocturno:,.0f} kWh/noche promedio")

# ========================================
# 3. DEMANDA EV POR HORA
# ========================================
print("\n" + "="*70)
print("3. DEMANDA EV POR HORA")
print("="*70)

ev_cols = [c for c in ev.columns if 'charging_power' in c.lower()]
ev['ev_total'] = ev[ev_cols].sum(axis=1)
ev['h'] = ev.index % 24
ev_hora = ev.groupby('h')['ev_total'].mean()

print("\n   Demanda EV promedio por hora (kW):")
for h in range(24):
    bar = "█" * int(ev_hora.get(h, 0) / 10)
    print(f"      h{h:02d}: {ev_hora.get(h, 0):>8,.1f} kW  {bar}")

ev_nocturno = ev[(ev['h'] >= 17) & (ev['h'] <= 21)]['ev_total'].sum() / 365
print(f"\n   Demanda EV nocturna (h17-h21): {ev_nocturno:,.0f} kWh/noche promedio")

# ========================================
# 4. ANÁLISIS BESS ACTUAL
# ========================================
print("\n" + "="*70)
print("4. BESS ACTUAL (940 kWh / 342 kW)")
print("="*70)

bess_cap = 940  # kWh
bess_power = 342  # kW
dod = 0.80
soc_min = 1 - dod  # 20%

capacidad_util = bess_cap * dod
carga_total = bess['bess_charge_kwh'].sum()
descarga_total = bess['bess_discharge_kwh'].sum()
soc_min_real = bess['soc_percent'].min()
soc_max_real = bess['soc_percent'].max()

print(f"""
   Capacidad nominal:        {bess_cap:>8} kWh
   Capacidad utilizable:     {capacidad_util:>8.0f} kWh (DOD {dod*100:.0f}%)
   Potencia:                 {bess_power:>8} kW
   
   Carga total/año:          {carga_total:>8,.0f} kWh
   Descarga total/año:       {descarga_total:>8,.0f} kWh
   
   SOC mínimo alcanzado:     {soc_min_real:>8.1f} % (debería ser {soc_min*100:.0f}%)
   SOC máximo alcanzado:     {soc_max_real:>8.1f} %
   
   ⚠️  El BESS NO llega al SOC mínimo de {soc_min*100:.0f}%
       porque la demanda EV nocturna ({ev_nocturno:.0f} kWh) es menor
       que la capacidad utilizable ({capacidad_util:.0f} kWh)
""")

# ========================================
# 5. ESCENARIOS DE EXPANSIÓN BESS
# ========================================
print("\n" + "="*70)
print("5. ESCENARIOS DE EXPANSIÓN BESS")
print("="*70)

# Escenario A: BESS óptimo solo para EV (usar 100% capacidad)
bess_optimo_ev = ev_nocturno / dod
print(f"""
   ESCENARIO A: BESS óptimo para EV únicamente
   ────────────────────────────────────────────
   Demanda EV nocturna:      {ev_nocturno:>8,.0f} kWh/noche
   BESS óptimo (DOD 80%):    {bess_optimo_ev:>8,.0f} kWh
   BESS actual:              {bess_cap:>8} kWh
   Exceso actual:            {bess_cap - bess_optimo_ev:>8,.0f} kWh ({(bess_cap/bess_optimo_ev-1)*100:.0f}% sobredimensionado)
""")

# Escenario B: BESS para EV + Mall nocturno (h18-h22)
demanda_nocturna_total = ev_nocturno + mall_nocturno
bess_ev_mall = demanda_nocturna_total / dod
print(f"""
   ESCENARIO B: BESS para EV + Mall nocturno (h18-h22)
   ────────────────────────────────────────────────────
   Demanda EV nocturna:      {ev_nocturno:>8,.0f} kWh/noche
   Demanda Mall nocturna:    {mall_nocturno:>8,.0f} kWh/noche
   TOTAL nocturno:           {demanda_nocturna_total:>8,.0f} kWh/noche
   
   BESS necesario (DOD 80%): {bess_ev_mall:>8,.0f} kWh
   Potencia necesaria:       {max(mall_hora[18:23]):>8,.0f} kW (pico Mall h18-h22)
   
   ⚠️  Esto es {bess_ev_mall/1000:.1f} MWh - muy grande para el proyecto
""")

# Escenario C: Aprovechar curtailment con BESS más grande
print(f"""
   ESCENARIO C: Aprovechar PV Curtailed
   ─────────────────────────────────────
   PV Curtailed disponible:  {curtailed_total:>8,.0f} kWh/año ({curtailed_total/365:.0f} kWh/día)
   
   Horario de curtailment (mediodía):
""")

# Curtailment promedio por hora
curt_prom = curt_hora / 365
horas_curtail = curt_prom[curt_prom > 10]
for h in horas_curtail.index:
    print(f"      h{h:02d}: {curt_prom[h]:>6,.0f} kWh/hora disponible")

curtail_dia = curt_prom.sum()
bess_curtail = curtail_dia / dod
print(f"""
   Curtailment diario:       {curtail_dia:>8,.0f} kWh/día
   BESS para capturar todo:  {bess_curtail:>8,.0f} kWh (DOD 80%)
   
   Potencia carga necesaria: {curt_prom.max():>8,.0f} kW (para capturar pico h{curt_prom.idxmax():02d})
""")

# ========================================
# 6. RESUMEN DE DECISIONES
# ========================================
print("\n" + "="*70)
print("6. RESUMEN PARA TOMA DE DECISIONES")
print("="*70)

print(f"""
   ┌─────────────────────────────────────────────────────────────────────┐
   │ SITUACIÓN ACTUAL                                                    │
   ├─────────────────────────────────────────────────────────────────────┤
   │ • BESS 940 kWh está SOBREDIMENSIONADO para EV ({bess_cap/bess_optimo_ev:.0f}x lo necesario)   │
   │ • Solo descarga ~{ev_nocturno:.0f} kWh/noche de {capacidad_util:.0f} kWh utilizables       │
   │ • SOC mínimo real: {soc_min_real:.1f}% (no llega al 20% de DOD)             │
   │ • PV Curtailed: {curtailed_total/1e6:.2f} GWh/año ({curtailed_total/pv_total*100:.1f}% de generación)           │
   └─────────────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────────────┐
   │ OPCIONES                                                           │
   ├─────────────────────────────────────────────────────────────────────┤
   │                                                                     │
   │ OPCIÓN 1: Reducir BESS a {bess_optimo_ev:.0f} kWh (óptimo para EV)             │
   │    ✓ BESS trabaja a capacidad completa (20%-100% SOC)              │
   │    ✓ Menor costo de inversión                                       │
   │    ✗ No aprovecha curtailment adicional                            │
   │                                                                     │
   │ OPCIÓN 2: Mantener BESS 940 kWh y usar para Mall parcial           │
   │    ✓ Aprovecha capacidad existente                                  │
   │    ✓ Reduce importación red para Mall                               │
   │    ~ Requiere modificar estrategia de descarga                      │
   │                                                                     │
   │ OPCIÓN 3: Expandir BESS para capturar todo curtailment             │
   │    Necesario: ~{bess_curtail:.0f} kWh + potencia {curt_prom.max():.0f} kW                     │
   │    ✓ Maximiza uso de PV                                             │
   │    ✗ Alto costo de inversión                                        │
   │                                                                     │
   └─────────────────────────────────────────────────────────────────────┘

   DATOS CLAVE PARA DECISIÓN:
   ─────────────────────────────
   • Curtailment aprovechable:     {curtailed_total:>10,.0f} kWh/año
   • Demanda Mall nocturna:        {mall_nocturno*365:>10,.0f} kWh/año
   • Demanda EV nocturna:          {ev_nocturno*365:>10,.0f} kWh/año
   • Capacidad BESS actual:        {bess_cap:>10} kWh
   • Capacidad BESS óptima EV:     {bess_optimo_ev:>10,.0f} kWh
""")

# ========================================
# 7. CALCULOS DETALLADOS
# ========================================
print("\n" + "="*70)
print("7. CÁLCULOS DETALLADOS POR HORA")
print("="*70)

# Tabla resumen por hora
print("\n   Hora | PV Gen | Mall | EV | Curtail | Balance")
print("   " + "-"*55)
pv_hora = solar.copy()
pv_hora['h'] = pv_hora.index % 24
pv_promedio = pv_hora.groupby('h')['ac_energy_kwh'].mean()

for h in range(24):
    pv = pv_promedio.get(h, 0)
    m = mall_hora.get(h, 0)
    e = ev_hora.get(h, 0)
    c = curt_prom.get(h, 0)
    balance = pv - m - e
    signo = "+" if balance >= 0 else ""
    print(f"   h{h:02d}  | {pv:>6.0f} | {m:>4.0f} | {e:>5.1f} | {c:>7.0f} | {signo}{balance:>7.0f}")

print("\n   ✓ Análisis completo finalizado")
