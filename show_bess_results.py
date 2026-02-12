#!/usr/bin/env python3
"""Muestra resumen de resultados BESS generados"""
import json
from pathlib import Path

bess_results = Path("data/oe2/bess/bess_results.json")
if not bess_results.exists():
    print("ERROR: No se encontró bess_results.json")
    exit(1)

with open(bess_results) as f:
    results = json.load(f)

print("\n" + "="*70)
print("DIMENSIONAMIENTO BESS v3.0 COMPLETADO")
print("="*70)

print("\n[ESPECIFICACIONES DIMENSIONADAS]")
print(f"  Capacidad:          {results.get('capacity_kwh', 0):,.0f} kWh")
print(f"  Potencia nominal:   {results.get('nominal_power_kw', 0):,.0f} kW")
print(f"  DoD (Depth of Discharge): {results.get('dod', 0)*100:.0f}%")
print(f"  C-rate:             {results.get('c_rate', 0):.2f}")
print(f"  Eficiencia:         {results.get('efficiency_roundtrip', 0)*100:.0f}%")

print("\n[BALANCE ENERGETICO ANUAL]")
ev_day = results.get('ev_demand_kwh_day', 0)
pv_day = results.get('pv_generation_kwh_day', 0)
mall_day = results.get('mall_demand_kwh_day', 0)
print(f"  Generación PV:      {pv_day*365:,.0f} kWh/año")
print(f"  Demanda Mall:       {mall_day*365:,.0f} kWh/año")
print(f"  Demanda EV (v3.0):  {ev_day*365:,.0f} kWh/año")
print(f"  Demanda Total:      {(ev_day+mall_day)*365:,.0f} kWh/año")

print("\n[ARCHIVOS GENERADOS]")
data_dir = Path("data/oe2/bess")
files = [
    "bess_results.json",
    "bess_simulation_hourly.csv",
    "bess_daily_balance_24h.csv",
]
for fname in files:
    fpath = data_dir / fname
    if fpath.exists():
        size_kb = fpath.stat().st_size / 1024
        print(f"  OK  {fname:40s} ({size_kb:8.1f} KB)")

print("\n[GRAFICAS GENERADAS]")
reports_dir = Path("reports/oe2/oe2/bess") if Path("reports/oe2/oe2/bess").exists() else Path("reports/oe2/bess")
if reports_dir.exists():
    pngs = list(reports_dir.glob("*.png"))
    for png in pngs:
        print(f"  OK  {png.name}")
else:
    print(f"  (No se encontró directorio: {reports_dir})")

print("\n" + "="*70)
print("DATOS LISTOS PARA OE3 (CityLearn v2) - RL AGENTS")
print("="*70 + "\n")
