#!/usr/bin/env python3
"""
Genera el resumen de ubicacion (OE1) segun la Tabla 9.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe1.location import build_location_summary, write_location_outputs
from scripts._common import load_all


def main() -> None:
    ap = argparse.ArgumentParser(description="Resumen de ubicacion OE1")
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    out_dir = rp.interim_dir / "oe1"
    chargers_results = rp.interim_dir / "oe2" / "chargers" / "chargers_results.json"
    chargers_results_path = chargers_results if chargers_results.exists() else None

    summary = build_location_summary(
        cfg=cfg,
        chargers_results_path=chargers_results_path,
        out_dir=out_dir,
        reports_dir=rp.reports_dir,
    )

    write_location_outputs(summary, out_dir=out_dir, reports_dir=rp.reports_dir)

    print("\nOE1 - Location summary saved:")
    print(f"  {summary.get('results_path')}")
    if summary.get("report_path"):
        print(f"  {summary.get('report_path')}")


if __name__ == "__main__":
    main()
