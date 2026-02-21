"""
AUDITORÍA v8.1: Validación de 6 Fases BESS - Análisis del Desbalance de 136k kWh
════════════════════════════════════════════════════════════════════════════════

Objetivo: 
1. Identificar DÓNDE está el desbalance (qué horas, qué fases)
2. Cuantificar error de balance por FASE
3. Detectar si hay carga+descarga simultánea
4. Recomendar corrección

────────────────────────────────────────────────────────────────────────────────
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

BESS_CSV = Path("data/oe2/bess/bess_ano_2024.csv")
print(f"📋 Cargando: {BESS_CSV}")

df = pd.read_csv(BESS_CSV)
print(f"✓ {len(df)} registros cargados\n")

# Reconstruir hour_of_day a partir del índice (cada 24 horas = 1 día)
df["hour_of_day"] = df.index % 24
df["day_number"] = df.index // 24

print("="*80)
print("1️⃣ BALANCE DE ENERGÍA GENERAL")
print("="*80)

total_pv_kwh = df["pv_kwh"].sum()
total_ev_demand = df["ev_kwh"].sum()
total_mall_demand = df["mall_kwh"].sum()
total_load = df["load_kwh"].sum()

# BESS energy flows
pv_to_bess = df["pv_to_bess_kwh"].sum()
bess_to_ev = df["bess_to_ev_kwh"].sum()
bess_to_mall = df["bess_to_mall_kwh"].sum()
bess_total_discharged = bess_to_ev + bess_to_mall

print(f"\nGENERACIÓN Y DEMANDA:")
print(f"  PV generación:       {total_pv_kwh:>12,.0f} kWh/año")
print(f"  EV demanda total:    {total_ev_demand:>12,.0f} kWh/año")
print(f"  MALL demanda total:  {total_mall_demand:>12,.0f} kWh/año")
print(f"  Carga total:         {total_load:>12,.0f} kWh/año")

print(f"\nBESS ENERGY FLOWS:")
print(f"  PV → BESS:           {pv_to_bess:>12,.0f} kWh")
print(f"  BESS → EV:           {bess_to_ev:>12,.0f} kWh ({(bess_to_ev/bess_total_discharged*100):>5.1f}%)")
print(f"  BESS → MALL:         {bess_to_mall:>12,.0f} kWh ({(bess_to_mall/bess_total_discharged*100):>5.1f}%)")
print(f"  BESS total → FUE:    {bess_total_discharged:>12,.0f} kWh")

# Desbalance total
balance_error = pv_to_bess - bess_total_discharged
eff_roundtrip = 0.95
expected_loss = pv_to_bess * (1 - eff_roundtrip)

print(f"\n⚖️  BALANCE:")
print(f"  Energía cargada - descargada: {balance_error:>12,.0f} kWh")
print(f"  Pérdida esperada (5%):        {expected_loss:>12,.0f} kWh")
print(f"  ERROR ADICIONAL:              {balance_error - expected_loss:>12,.0f} kWh")
print(f"  % de cargado sin explicar:    {(balance_error - expected_loss) / pv_to_bess * 100:>12.2f}%")

# Investigar horas con error
print("\n" + "="*80)
print("2️⃣ HORAS CON MAYOR ERROR DE BALANCE")
print("="*80)

# El dataset ya tiene bess_balance_error_hourly_kwh
df["balance_error"] = abs(df["bess_balance_error_hourly_kwh"])

# Top 20 horas con mayor error
problem_hours = df.nlargest(20, "balance_error")

print(f"\nTop 20 horas con mayor |balance error| (sobre ~{df['balance_error'].sum():.0f} kWh total):\n")
print(f"{'Hora':>5} {'Día':>5} {'PV':>7}  {'SOC%':>6}  {'Est.':>8}  {'Ent.':>8}  {'Error':>8}  {'Status':<10}")
print("-" * 85)

for idx, row in problem_hours.iterrows():
    h = int(row['hour_of_day'])
    d = int(row['day_number'])
    pv = row['pv_kwh']
    soc = row['soc_percent']
    stored = row['bess_energy_stored_hourly_kwh']
    delivered = row['bess_energy_delivered_hourly_kwh']
    error = abs(row['bess_balance_error_hourly_kwh'])
    status = row['bess_validation_status_hourly']
    
    print(f"{h:>5} {d:>5} {pv:>7.0f} {soc:>6.1f}  {stored:>8.1f}  {delivered:>8.1f}  {error:>8.1f}  {status:<10}")

# Agrupar errores por hora del día
print("\n" + "="*80)
print("3️⃣ ANÁLISIS POR HORA DEL DÍA")
print("="*80)

hourly_summary = df.groupby("hour_of_day").agg({
    "bess_balance_error_hourly_kwh": ["sum", "mean", "count"],
    "pv_to_bess_kwh": "sum",
    "bess_to_ev_kwh": "sum",
    "bess_to_mall_kwh": "sum",
    "soc_percent": "mean",
    "bess_action_kwh": "sum"
}).round(1)

print(f"\n     {'Acum.Error':>12} {'Prom.Error':>12} {'Total Cargado':>14} {'Total Descargado':>16}")
print("-" * 65)

cumulative_error = 0
for hour in range(24):
    if hour in hourly_summary.index:
        total_error = hourly_summary.loc[hour, ("bess_balance_error_hourly_kwh", "sum")]
        avg_error = hourly_summary.loc[hour, ("bess_balance_error_hourly_kwh", "mean")]
        charged = hourly_summary.loc[hour, ("pv_to_bess_kwh", "sum")]
        discharged = (hourly_summary.loc[hour, ("bess_to_ev_kwh", "sum")] + 
                     hourly_summary.loc[hour, ("bess_to_mall_kwh", "sum")])
        
        cumulative_error += total_error
        
        # Marcar horas problemáticas (error > 1000 kWh)
        marker = "🚨" if abs(total_error) > 1000 else "  "
        
        print(f"{hour:2d}h {marker} {total_error:>12,.0f} {avg_error:>12.1f} {charged:>14,.0f} {discharged:>16,.0f}")

print(f"\nCumulative error (acumula errores a lo largo del día):")
print(f"  {cumulative_error:,.0f} kWh")

# Detectar FASES por horas
print("\n" + "="*80)
print("4️⃣ EJECUCIÓN DE FASES POR COMPORTAMIENTO")
print("="*80)

print("\nFASE 1 (6-9h): CARGA PRIMERO (EV=0)")
fase1 = df[(df["hour_of_day"] < 9)]
print(f"  Carga total:       {fase1['pv_to_bess_kwh'].sum():>12,.0f} kWh")
print(f"  EV servida por PV: {fase1['pv_to_ev_kwh'].sum():>12,.0f} kWh (¿debe ser ~0?)")
print(f"  Action count:      {(fase1['bess_action_kwh'] > 0).sum():>12.0f} horas")

print("\nFASE 2 (9h-SOC99%): EV MÁXIMA + BESS carga")
fase2 = df[(df["hour_of_day"] >= 9) & (df["soc_percent"] < 99)]
print(f"  Carga total:       {fase2['pv_to_bess_kwh'].sum():>12,.0f} kWh")
print(f"  EV servida por PV: {fase2['pv_to_ev_kwh'].sum():>12,.0f} kWh")
print(f"  Action count:      {(fase2['bess_action_kwh'] > 0).sum():>12.0f} horas")

print("\nFASE 3 (SOC≥99%): HOLDING")
fase3 = df[(df["hour_of_day"] >= 9) & (df["soc_percent"] >= 99)]
print(f"  Carga total:       {fase3['pv_to_bess_kwh'].sum():>12,.0f} kWh (¿debe ser ~0?)")
print(f"  EV servida por PV: {fase3['pv_to_ev_kwh'].sum():>12,.0f} kWh")
print(f"  Action count:      {(fase3['bess_action_kwh'] > 0).sum():>12.0f} horas")

print("\nFASE 4 (PV<MALL, mall>1900): PEAK SHAVING")
fase4 = df[(df["pv_kwh"] < df["mall_kwh"]) & (df["mall_kwh"] > 1900) & (df["hour_of_day"] < 22)]
print(f"  Descarga (MALL):   {fase4['bess_to_mall_kwh'].sum():>12,.0f} kWh")
print(f"  Action count:      {(fase4['bess_action_kwh'] > 0).sum():>12.0f} horas (¿que pasó aquí?)")

print("\nFASE 5 (EV deficit): EV + MALL DISCHARGE")
# EV deficit = EV demand - PV available for EV
ev_deficit = df["ev_kwh"] - df["pv_to_ev_kwh"]
fase5 = df[ev_deficit > 0].copy()
fase5 = fase5[(fase5["hour_of_day"] < 22)]
print(f"  Descarga (EV):     {fase5['bess_to_ev_kwh'].sum():>12,.0f} kWh")
print(f"  Descarga (MALL):   {fase5['bess_to_mall_kwh'].sum():>12,.0f} kWh")
print(f"  Action count:      {(fase5['bess_action_kwh'] > 0).sum():>12.0f} horas")

print("\nFASE 6 (22-6h): REPOSO")
fase6 = df[((df["hour_of_day"] >= 22) | (df["hour_of_day"] < 6))]
print(f"  Carga total:       {fase6['pv_to_bess_kwh'].sum():>12,.0f} kWh (¿debe ser ~0?)")
print(f"  Descarga total:    {(fase6['bess_to_ev_kwh'] + fase6['bess_to_mall_kwh']).sum():>12,.0f} kWh (¿debe ser ~0?)")
print(f"  Action count:      {(fase6['bess_action_kwh'] > 0).sum():>12.0f} horas (¿debe ser 0?)")

# Detectar carga+descarga simultánea
print("\n" + "="*80)
print("5️⃣ VALIDACIÓN: ¿CARGA Y DESCARGA SIMULTÁNEA?")
print("="*80)

df["charge"] = df["pv_to_bess_kwh"]
df["discharge"] = df["bess_to_ev_kwh"] + df["bess_to_mall_kwh"]
df["simultaneous"] = (df["charge"] > 0.1) & (df["discharge"] > 0.1)

simultaneous_count = df["simultaneous"].sum()
simultaneous_energy = df[df["simultaneous"]][["charge", "discharge"]].sum()

print(f"\n🔍 Carga + Descarga simultánea en MISMA HORA:")
print(f"  Horas afectadas:      {simultaneous_count:>6.0f}/8760 ({simultaneous_count/8760*100:>5.2f}%)")
print(f"  Energía cargada:      {simultaneous_energy['charge']:>12,.0f} kWh")
print(f"  Energía descargada:   {simultaneous_energy['discharge']:>12,.0f} kWh")

if simultaneous_count > 100:
    print(f"\n  ⚠️ PROBLEMA DETECTADO: {simultaneous_count} horas tienen carga+descarga simultánea")
    print(f"     Esto viola el concepto de '6 fases' donde solo UNA debe ejecutar")
    print(f"     Estas horas pueden estar causando el error de ~136k kWh")
    
    # Mostrar primeras 15 horas problemáticas
    print(f"\n  Primeras 15 horas con carga+descarga simultánea:")
    simul_hours = df[df["simultaneous"]].head(15)
    for idx, row in simul_hours.iterrows():
        print(f"    Hora {row['hour_of_day']:2.0f}: Carga={row['charge']:>7.1f}kWh, Descarga={row['discharge']:>7.1f}kWh, SOC={row['soc_percent']:>6.1f}%")
else:
    print(f"\n  ✓ OK: Carga y descarga NO son simultáneas")

print("\n" + "="*80)
print("✓ AUDITORÍA COMPLETADA")
print("="*80)
