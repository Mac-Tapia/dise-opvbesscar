from __future__ import annotations

import argparse
from pathlib import Path

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.co2_table import EmissionsFactors, load_summary, compute_table, write_outputs
from scripts._common import load_all

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    summary_path = rp.interim_dir / "oe3" / "simulations" / "simulation_summary.json"
    summary = load_summary(summary_path)

    factors = EmissionsFactors(
        km_per_kwh=float(cfg["oe3"]["emissions"]["km_per_kwh"]),
        km_per_gallon=float(cfg["oe3"]["emissions"]["km_per_gallon"]),
        kgco2_per_gallon=float(cfg["oe3"]["emissions"]["kgco2_per_gallon"]),
        grid_kgco2_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        project_life_years=int(cfg["oe3"]["emissions"]["project_life_years"]),
    )

    df = compute_table(summary, factors)
    write_outputs(df, rp.reports_dir / "oe3")

if __name__ == "__main__":
    main()
