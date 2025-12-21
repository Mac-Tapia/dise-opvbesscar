from __future__ import annotations

import argparse
from pathlib import Path

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe2.solar_pvlib import run_solar_sizing
from scripts._common import load_all

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    out_dir = rp.interim_dir / "oe2" / "solar"
    loc = cfg["oe2"]["location"]
    solar = cfg["oe2"]["solar"]

    run_solar_sizing(
        out_dir=out_dir,
        year=int(cfg["project"]["year"]),
        tz=str(loc["tz"]),
        lat=float(loc["lat"]),
        lon=float(loc["lon"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        target_dc_kw=float(solar["target_dc_kw"]),
        target_ac_kw=float(solar["target_ac_kw"]),
        target_annual_kwh=float(solar["target_annual_kwh"]),
        use_pvlib=bool(solar.get("use_pvlib", True)),
    )

if __name__ == "__main__":
    main()
