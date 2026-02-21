"""
AUDITORÍA COMPLETA: Validación de 6 Fases BESS v8
════════════════════════════════════════════════════════════════════════════════

Objetivo: 
1. Verificar que cada FASE se ejecuta en las horas correctas
2. Detectar solapamientos (carga + descarga simultánea)
3. Identificar cuál FASE está causando el desbalance de 136k kWh
4. Generar reporte detallado por FASE

6 Fases esperadas:
  FASE 1 (6-9h):    CARGA PRIMERO (EV=0, BESS absorbe PV)
  FASE 2 (9-SOC99%): EV MÁXIMA + BESS carga en paralelo
  FASE 3 (SOC≥99%):  HOLDING (BESS mantiene 100%)
  FASE 4 (PV<MALL, mall>1900): PEAK SHAVING (BESS descarga MALL)
  FASE 5 (EV deficit): EV + MALL DISCHARGE (BESS cubre EV 100%)
  FASE 6 (22-6h):   REPOSO (IDLE, BESS en 20%)

════════════════════════════════════════════════════════════════════════════════
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from collections import defaultdict

# Cargar dataset BESS
BESS_CSV = Path("data/oe2/bess/bess_ano_2024.csv")
print(f"📋 Cargando: {BESS_CSV}")

try:
    df = pd.read_csv(BESS_CSV)
    print(f"✓ {len(df)} registros cargados (esperados 8,760)")
except Exception as e:
    print(f"❌ Error cargando CSV: {e}")
    exit(1)

# Validar columnas necesarias
print("\n" + "="*80)
print("1️⃣ VALIDACIÓN DE COLUMNAS")
print("="*80)

required_cols = {
    "date": "Timestamp horario",
    "hour_of_day": "Hora del día (0-23)",
    "pv_generation_kw": "Generación PV",
    "ev_demand_kw": "Demanda EV",
    "mall_demand_kw": "Demanda MALL",
    "bess_charge_kw": "Carga BESS",
    "bess_discharge_kw": "Descarga BESS",
    "bess_soc_percent": "Estado de carga BESS",
    "pv_to_bess": "Energía PV → BESS",
    "pv_to_ev": "Energía PV → EV",
    "pv_to_mall": "Energía PV → MALL",
    "bess_to_ev": "Energía BESS → EV",
    "bess_to_mall": "Energía BESS → MALL",
    "grid_to_ev": "Energía RED → EV",
    "grid_to_mall": "Energía RED → MALL",
}

missing = [col for col in required_cols.keys() if col not in df.columns]
if missing:
    print(f"❌ Columnas faltantes: {missing}")
    print(f"✓ Columnas disponibles: {list(df.columns)[:10]}...")
else:
    print(f"✓ Todas {len(required_cols)} columnas presentes")

# Analizar por FASE
print("\n" + "="*80)
print("2️⃣ ANÁLISIS DE EJECUCIÓN DE FASES (Muestra de 7 días típicos)")
print("="*80)

# Usar días 100-107 como muestra (invierno)
sample_hours = df[df.index.isin(range(100*24, 107*24))].copy()

phase_execution = defaultdict(lambda: {"count": 0, "hours": [], "issues": []})

for idx, row in sample_hours.iterrows():
    hour = row["hour_of_day"]
    pv = row["pv_generation_kw"]
    ev = row["ev_demand_kw"]
    mall = row["mall_demand_kw"]
    soc = row["bess_soc_percent"] / 100.0  # convert % to decimal
    charge = row["bess_charge_kw"]
    discharge = row["bess_discharge_kw"]
    pv_to_bess = row["pv_to_bess"]
    pv_to_ev = row["pv_to_ev"]
    bess_to_ev = row["bess_to_ev"]
    bess_to_mall = row["bess_to_mall"]
    
    closing_hour = 22
    soc_max = 1.0
    soc_min = 0.2
    PEAK_SHAVING_THRESHOLD = 1900.0
    
    # Simulación de lógica de fases para detectar cuál se ejecutó
    phases_triggered = []
    
    # FASE 1 (6-9h): CARGA PRIMERO
    if hour < 9:
        phases_triggered.append("FASE1")
        if charge > 0.1:
            phase_execution["FASE1"]["count"] += 1
            phase_execution["FASE1"]["hours"].append(hour)
    
    # FASE 2 (9h hasta SOC≥99%)
    elif hour >= 9 and soc < 0.99:
        phases_triggered.append("FASE2")
        if charge > 0.1 or pv_to_ev > 0.1:
            phase_execution["FASE2"]["count"] += 1
            phase_execution["FASE2"]["hours"].append(hour)
    
    # FASE 3 (SOC≥99%)
    elif hour >= 9 and soc >= 0.99:
        phases_triggered.append("FASE3")
        phase_execution["FASE3"]["count"] += 1
        phase_execution["FASE3"]["hours"].append(hour)
    
    # FASE 4: PEAK SHAVING (PV < MALL and mall > 1900)
    if pv < mall and mall > PEAK_SHAVING_THRESHOLD and soc > soc_min and hour < closing_hour:
        phases_triggered.append("FASE4")
        if discharge > 0.1 or bess_to_mall > 0.1:
            phase_execution["FASE4"]["count"] += 1
            phase_execution["FASE4"]["hours"].append(hour)
    
    # FASE 5: EV DEFICIT
    ev_deficit_kwh = ev - pv_to_ev  # Deficit de EV
    if ev_deficit_kwh > 0.1 and soc > soc_min and hour < closing_hour:
        phases_triggered.append("FASE5")
        if discharge > 0.1 or bess_to_ev > 0.1:
            phase_execution["FASE5"]["count"] += 1
            phase_execution["FASE5"]["hours"].append(hour)
    
    # FASE 6 (22-6h): REPOSO
    if hour >= 22 or hour < 6:
        phases_triggered.append("FASE6")
        phase_execution["FASE6"]["count"] += 1
        phase_execution["FASE6"]["hours"].append(hour)
    
    # 🚨 PROBLEMA: Detectar carga + descarga simultánea
    if charge > 0.1 and discharge > 0.1:
        issue = f"⚠️ CARGA+DESCARGA simultánea en h={hour}: carga={charge:.1f}kW, descarga={discharge:.1f}kW, SOC={soc*100:.1f}%"
        for phase in phases_triggered:
            phase_execution[phase]["issues"].append(issue)

# Resumen por FASE
print("\n📊 EJECUCIÓN DE FASES (Días 100-107, muestra de 168 horas):")
print("-" * 80)

for phase in ["FASE1", "FASE2", "FASE3", "FASE4", "FASE5", "FASE6"]:
    stats = phase_execution[phase]
    exec_pct = (stats["count"] / 168) * 100 if stats["count"] > 0 else 0
    print(f"\n{phase}:")
    print(f"  Ejecuciones:    {stats['count']}/168 horas ({exec_pct:.1f}%)")
    print(f"  Horas típicas:  {sorted(set(stats['hours'][:5]))[:3]}... (mostrando primeras 3)")
    
    if stats["issues"]:
        print(f"  🚨 PROBLEMAS ({len(stats['issues'])} eventos):")
        for issue in stats["issues"][:3]:  # Mostrar primeras 3
            print(f"     {issue}")
        if len(stats["issues"]) > 3:
            print(f"     ... y {len(stats['issues'])-3} más")

# Análisis de balance energético
print("\n" + "="*80)
print("3️⃣ ANÁLISIS DE BALANCE ENERGÉTICO (AÑO COMPLETO)")
print("="*80)

# Energía cargada vs descargada
energy_charged_kwh = df["pv_to_bess"].sum()
energy_discharged_total_kwh = (df["bess_to_ev"] + df["bess_to_mall"]).sum()
balance_error_kwh = energy_charged_kwh - energy_discharged_total_kwh

print(f"\nEnergía CARGADA (PV→BESS):    {energy_charged_kwh:>12,.0f} kWh")
print(f"Energía DESCARGADA total:      {energy_discharged_total_kwh:>12,.0f} kWh")
print(f"  → DESCARGADA a EV:           {df['bess_to_ev'].sum():>12,.0f} kWh ({(df['bess_to_ev'].sum()/energy_discharged_total_kwh*100):>5.1f}%)")
print(f"  → DESCARGADA a MALL:         {df['bess_to_mall'].sum():>12,.0f} kWh ({(df['bess_to_mall'].sum()/energy_discharged_total_kwh*100):>5.1f}%)")

# Diferencia entre lo que se cargó y descargó
expected_loss_ratio = 1 - 0.95  # 5% pérdida round-trip ideal
expected_loss_kwh = energy_charged_kwh * expected_loss_ratio

print(f"\n⚖️  BALANCE:")
print(f"  Energía sin contar = Cargado - Descargado:")
print(f"  {balance_error_kwh:>12,.0f} kWh")
print(f"\n  Pérdida de eficiencia esperada (5% round-trip):")
print(f"  {expected_loss_kwh:>12,.0f} kWh")

if balance_error_kwh > expected_loss_kwh * 1.5:
    print(f"\n  🚨 ERROR CRÍTICO: Hay {balance_error_kwh - expected_loss_kwh:,.0f} kWh NO explicados")
    print(f"     Esto es {((balance_error_kwh - expected_loss_kwh)/energy_charged_kwh*100):.1f}% de lo cargado")
else:
    print(f"\n  ✓ Balance dentro de lo esperado por eficiencia")

# SOC progression check
print("\n" + "="*80)
print("4️⃣ VALIDACIÓN DE SOC DIARIO (Ciclo 20% → 100% → 20%)")
print("="*80)

# Agregar SOC inicial y final diario
df["date"] = pd.to_datetime(df["date"])
df["day"] = df["date"].dt.date

daily_soc = df.groupby("day").agg({
    "bess_soc_percent": ["min", "max", "first", "last"],
    "hour_of_day": "count"
})

# Verificar ciclo
soc_issues = 0
for day in daily_soc.index[:7]:  # Primeros 7 días
    min_soc = daily_soc.loc[day, ("bess_soc_percent", "min")]
    max_soc = daily_soc.loc[day, ("bess_soc_percent", "max")]
    start_soc = daily_soc.loc[day, ("bess_soc_percent", "first")]
    end_soc = daily_soc.loc[day, ("bess_soc_percent", "last")]
    
    print(f"\nDía {day}:")
    print(f"  SOC rango: {min_soc:>6.1f}% - {max_soc:>6.1f}%")
    print(f"  SOC inicio: {start_soc:>6.1f}%, SOC cierre: {end_soc:>6.1f}%")
    
    # Validar ciclo esperado: debe terminar en ~20% (6h cierre)
    if end_soc < 15:
        print(f"  ✓ Cierre correcta (SOC < 20%)")
    else:
        print(f"  ⚠️ Cierre problemática (SOC = {end_soc:.1f}% > 20%)")
        soc_issues += 1

if soc_issues == 0:
    print(f"\n✓ Ciclo diario OK: BESS cierra a ~20% cada día")
else:
    print(f"\n⚠️ {soc_issues} días con cierre problemático")

# Análisis de horas con mayor desbalance
print("\n" + "="*80)
print("5️⃣ HORAS CON MAYOR DESBALANCE (Carga/Descarga no equilibrado)")
print("="*80)

df["imbalance_kwh"] = abs(df["pv_to_bess"] - (df["bess_to_ev"] + df["bess_to_mall"]))
problem_hours = df.nlargest(10, "imbalance_kwh")[["hour_of_day", "pv_generation_kw", "bess_soc_percent", 
                                                    "pv_to_bess", "bess_to_ev", "bess_to_mall", "imbalance_kwh"]]

print("\nTop 10 horas con mayor desbalance (PV→BESS vs BESS→[EV+MALL]):")
print("-" * 80)
for idx, row in problem_hours.iterrows():
    print(f"\nHora {row['hour_of_day']:2.0f}: PV={row['pv_generation_kw']:>7.0f}kW, SOC={row['bess_soc_percent']:>6.1f}%")
    print(f"  Cargado:    {row['pv_to_bess']:>10.1f} kWh")
    print(f"  Descargado: {row['bess_to_ev'] + row['bess_to_mall']:>10.1f} kWh (EV={row['bess_to_ev']:.1f}, MALL={row['bess_to_mall']:.1f})")
    print(f"  Desbalance: {row['imbalance_kwh']:>10.1f} kWh ⚠️")

print("\n" + "="*80)
print("✓ AUDITORÍA COMPLETADA")
print("="*80)
