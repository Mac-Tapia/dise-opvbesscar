#!/usr/bin/env python3
"""
Ejecuta el dimensionamiento de cargadores EV.

Uso:
    python scripts/run_oe2_chargers.py --config configs/default.yaml [--no-plots]
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe2.chargers import run_charger_sizing
from scripts._common import load_all


def main() -> None:
    ap = argparse.ArgumentParser(description="Dimensionamiento de cargadores EV")
    ap.add_argument("--config", default="configs/default.yaml", help="Archivo de configuración")
    ap.add_argument("--no-plots", action="store_true", help="Omitir generación de gráficas")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    out_dir = rp.interim_dir / "oe2" / "chargers"
    ev = cfg["oe2"]["ev_fleet"]
    emissions = cfg["oe3"]["emissions"]
    grid_ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    seed = int(cfg["project"]["seed"])

    result = run_charger_sizing(
        out_dir=out_dir,
        seed=seed,
        n_motos=int(ev["motos_count"]),
        n_mototaxis=int(ev["mototaxis_count"]),
        pe_motos=float(ev["pe_motos"]),
        pe_mototaxis=float(ev["pe_mototaxis"]),
        fc_motos=float(ev["fc_motos"]),
        fc_mototaxis=float(ev["fc_mototaxis"]),
        peak_share_day=float(ev["peak_share_day"]),
        session_minutes=float(ev["session_minutes"]),
        utilization=float(ev["utilization"]),
        charger_power_kw_moto=float(ev["charger_power_kw_moto"]),
        charger_power_kw_mototaxi=float(ev["charger_power_kw_mototaxi"]),
        sockets_per_charger=int(ev["sockets_per_charger"]),
        opening_hour=int(ev["opening_hour"]),
        closing_hour=int(ev["closing_hour"]),
        km_per_kwh=float(emissions["km_per_kwh"]),
        km_per_gallon=float(emissions["km_per_gallon"]),
        kgco2_per_gallon=float(emissions["kgco2_per_gallon"]),
        grid_carbon_kg_per_kwh=grid_ci,
        peak_hours=list(ev["peak_hours"]),
        n_scenarios=100,
        generate_plots=not args.no_plots,
        reports_dir=rp.reports_dir,
    )

    analyses_dir = rp.analyses_dir / "oe2" / "chargers"
    analyses_dir.mkdir(parents=True, exist_ok=True)
    scenarios_path = out_dir / "selection_pe_fc_completo.csv"
    if scenarios_path.exists():
        shutil.copy2(scenarios_path, analyses_dir / scenarios_path.name)
    
    # Mostrar resumen
    esc_rec = result["esc_rec"]
    print("\nRESUMEN FINAL:")
    print(f"   Cargadores recomendados: {result['n_chargers_recommended']}")
    print(f"   Sockets totales: {int(esc_rec['sockets_total'])}")
    print(f"   Energía diaria: {result['total_daily_energy_kwh']:.0f} kWh")
    print(f"   Potencia pico: {result['peak_power_kw']:.0f} kW")
    print("\nDEMANDA TOTAL INSTALADA:")
    print(f"   Motos:     {result['n_motos']:,} × {result['charger_power_kw_moto']} kW = {result['potencia_instalada_motos_kw']:,.0f} kW")
    print(f"   Mototaxis: {result['n_mototaxis']:,} × {result['charger_power_kw_mototaxi']} kW = {result['potencia_instalada_mototaxis_kw']:,.0f} kW")
    print(f"   TOTAL:     {result['potencia_total_instalada_kw']:,.0f} kW")


if __name__ == "__main__":
    main()
