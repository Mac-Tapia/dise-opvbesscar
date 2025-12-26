from __future__ import annotations

import argparse
from pathlib import Path

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.co2_table import (
    EmissionsFactors, 
    CityBaseline,
    load_summary, 
    compute_table, 
    compute_agent_comparison,
    compute_breakdown,
    compute_control_comparison,
    write_outputs,
)
from scripts._common import load_all

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    summary_path = rp.outputs_dir / "oe3" / "simulations" / "simulation_summary.json"
    summary = load_summary(summary_path)

    factors = EmissionsFactors(
        km_per_kwh=float(cfg["oe3"]["emissions"]["km_per_kwh"]),
        km_per_gallon=float(cfg["oe3"]["emissions"]["km_per_gallon"]),
        kgco2_per_gallon=float(cfg["oe3"]["emissions"]["kgco2_per_gallon"]),
        grid_kgco2_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        project_life_years=int(cfg["oe3"]["emissions"]["project_life_years"]),
    )
    
    # Contexto de la ciudad de Iquitos
    city_baseline = CityBaseline(
        transport_tpy=float(cfg["oe3"]["city_baseline_tpy"]["transport"]),
        electricity_tpy=float(cfg["oe3"]["city_baseline_tpy"]["electricity_generation"]),
    )
    
    # Comparación de todos los agentes
    agent_comparison = compute_agent_comparison(summary, factors)
    
    # Tabla principal de emisiones
    df = compute_table(summary, factors, city_baseline)

    # Desglose Tabla 9
    breakdown = compute_breakdown(summary, factors)
    control_comparison = compute_control_comparison(summary, factors)
    
    # Escribir resultados
    write_outputs(df, rp.analyses_dir / "oe3", agent_comparison, breakdown, control_comparison)
    
    # Resumen en consola
    print("\n" + "="*60)
    print("SELECCIÓN DE AGENTE INTELIGENTE - OE3")
    print("="*60)
    print(f"Agente óptimo seleccionado: {df.attrs.get('best_agent')}")
    print(f"Reduccion CO2 vs combustion: {df.attrs.get('reduction_tco2_y', 0):.2f} tCO2/anio")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
