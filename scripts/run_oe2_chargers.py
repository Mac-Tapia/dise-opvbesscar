from __future__ import annotations

import argparse
from pathlib import Path

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe2.chargers import run_charger_sizing
from scripts._common import load_all

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    out_dir = rp.interim_dir / "oe2" / "ev"
    ev = cfg["oe2"]["ev_fleet"]
    seed = int(cfg["project"]["seed"])

    run_charger_sizing(
        out_dir=out_dir,
        seed=seed,
        n_motos=int(ev["motos_count"]),
        n_mototaxis=int(ev["mototaxis_count"]),
        peak_share_day=float(ev["peak_share_day"]),
        session_minutes=float(ev["session_minutes"]),
        utilization=float(ev["utilization"]),
        charger_power_kw=float(ev["charger_power_kw"]),
        sockets_per_charger=int(ev["sockets_per_charger"]),
        opening_hour=int(ev["opening_hour"]),
        closing_hour=int(ev["closing_hour"]),
        peak_hours=list(ev["peak_hours"]),
        n_scenarios=100,
    )

if __name__ == "__main__":
    main()
