#!/usr/bin/env python
"""Reporte final de cálculo de baseline real en CityLearn v2"""
from __future__ import annotations

import json
from pathlib import Path


def main():
    baseline_summary = Path("outputs/oe3/baseline_full_year_summary.json")

    with open(baseline_summary) as f:
        baseline = json.load(f)

    print("\n" + "=" * 80)
    print("BASELINE REAL COMPLETADO EN CITYLEARN v2".center(80))
    print("=" * 80)
    print()

    # Energy Summary
    print("[ENERGIA ANUAL]")
    e = baseline["energy"]
    print(f"  PV Generado:                   {e['pv_generation_kwh']:>12,.0f} kWh")
    print(f"  Demanda EV:                    {e['ev_demand_kwh']:>12,.0f} kWh")
    print(f"  Demanda Mall:                  {e['mall_load_kwh']:>12,.0f} kWh")
    print(f"  Demanda Total:                 {e['total_demand_kwh']:>12,.0f} kWh")
    print()
    print(f"  PV -> Cargas Directas:         {e['pv_to_load_kwh']:>12,.0f} kWh")
    print(f"  PV -> BESS:                    {e['pv_to_bess_kwh']:>12,.0f} kWh")
    print(f"  PV Descartado:                 {e['pv_curtailed_kwh']:>12,.0f} kWh")
    print(f"  Importacion Grid:              {e['grid_import_kwh']:>12,.0f} kWh")
    print()

    # Emissions
    print("[EMISIONES CO2]")
    em = baseline["emissions"]
    print(f"  Total Anual:                   {em['total_co2_kg']:>12,.0f} kg CO2")
    print(f"  Promedio Diario:               {em['daily_avg_co2_kg']:>12,.1f} kg CO2/dia")
    print(f"  Intensidad Carbono:            {em['carbon_intensity_kg_per_kwh']:>12.4f} kg CO2/kWh")
    print()

    # Efficiency
    print("[EFICIENCIA]")
    eff = baseline["efficiency"]
    print(f"  Utilizacion PV:                {eff['pv_utilization_pct']:>12.1f} %")
    print(f"  PV Descartado:                 {eff['pv_curtailed_pct']:>12.1f} %")
    print(f"  Dependencia Grid:              {eff['grid_dependency_pct']:>12.1f} %")
    print(f"  Auto-Consumo Solar:            {eff['self_consumption_pct']:>12.1f} %")
    print()

    # BESS Statistics
    print("[BESS PERFORMANCE]")
    bess = baseline["bess"]
    print(f"  Capacidad Total:               {4520:>12,.0f} kWh")
    print(f"  SOC Final:                     {bess['final_soc_kwh']:>12,.0f} kWh")
    print(f"  SOC Promedio:                  {bess['avg_soc_kwh']:>12,.0f} kWh")
    print(f"  Ciclos Anuales:                {bess['cycles_approx']:>12,.1f} ciclos")
    print()

    print("=" * 80)
    print("[SUCCESS] Baseline real calculado exitosamente en CityLearn v2".center(80))
    print("=" * 80)
    print()
    print("Archivos generados:")
    print(f"  - {baseline_summary}")
    print(f"  - outputs/oe3/baseline_full_year_hourly.csv (8,760 horas)")
    print()
    print("Este baseline sirve como referencia para comparar agentes RL (SAC/PPO/A2C)")
    print()


if __name__ == "__main__":
    main()
