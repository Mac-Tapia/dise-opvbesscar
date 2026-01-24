#!/usr/bin/env python
"""Resumen del dataset OE3 generado."""
import json
from pathlib import Path

# Cargar resumen
summary_path = Path("d:/diseñopvbesscar/data/processed/citylearn/iquitos_128_tomas/dataset_summary.json")
with open(summary_path) as f:
    summary = json.load(f)

print("=" * 80)
print("DATASET OE3 - CITYLEARN v2 - RESUMEN COMPLETO")
print("=" * 80)

print(f"""
CONFIGURACIÓN:
  • Cargadores físicos: {summary['n_cargadores_total']} unidades
  • Tomas por cargador: 4
  • Total tomas controlables: {summary['n_tomas_total']}
  • Período de simulación: {summary['n_horas']} horas (1 año)

POTENCIA INSTALADA:
  • Total: {summary['potencia_total_kw']:.1f} kW

ENERGÍA ANUAL:
  • Total: {summary['energia_anual_kwh']:,.0f} kWh
  • Promedio diario: {summary['energia_anual_kwh']/365:,.0f} kWh/día
  • (Tabla 13 OE2 objetivo: 903 kWh/día)

POR PLAYA:
""")

for playa_name, playa_data in summary['playas'].items():
    n_carg = playa_data["n_cargadores"]
    n_tom = playa_data["n_tomas"]
    pw_tom = playa_data["power_per_toma_kw"]
    pw_tot = playa_data["total_power_kw"]
    en_tot = playa_data["total_energy_year_kwh"]
    en_avg = playa_data["avg_energy_per_toma_kwh"]

    print(f"  {playa_name}:")
    print(f"    • Cargadores: {n_carg}")
    print(f"    • Tomas: {n_tom}")
    print(f"    • Potencia por toma: {pw_tom:.1f} kW")
    print(f"    • Potencia total: {pw_tot:.1f} kW")
    print(f"    • Energía anual: {en_tot:,.0f} kWh")
    print(f"    • Energía promedio/toma: {en_avg:,.0f} kWh/año")
    print()

# Contar archivos
motos_path = Path("d:/diseñopvbesscar/data/processed/citylearn/iquitos_128_tomas/Playa_Motos")
mototaxis_path = Path("d:/diseñopvbesscar/data/processed/citylearn/iquitos_128_tomas/Playa_Mototaxis")
n_csvs_motos = len(list(motos_path.glob("*.csv")))
n_csvs_mototaxis = len(list(mototaxis_path.glob("*.csv")))

print(f"""ARCHIVOS GENERADOS:
  • Playa_Motos: {n_csvs_motos} archivos CSV
  • Playa_Mototaxis: {n_csvs_mototaxis} archivos CSV
  • Schema: schema_128_tomas.json
  • Resumen: dataset_summary.json

USO EN OE3:
  • Cada toma (CSV) es un charger controlable por el agente RL
  • El agente puede decidir: pausar carga, modular potencia, etc.
  • Observables: estado y potencia de cada toma
  • Acciones: control individual de cada una de las 128 tomas
""")
print("=" * 80)
