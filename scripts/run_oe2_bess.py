from __future__ import annotations

import argparse
from pathlib import Path

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe2.bess import run_bess_sizing
from scripts._common import load_all

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    out_dir = rp.interim_dir / "oe2" / "bess"
    mall = cfg["oe2"]["mall"]
    bess_cfg = cfg["oe2"]["bess"]

    pv_profile_24h_path = rp.interim_dir / "oe2" / "solar" / "pv_profile_24h.csv"
    ev_profile_24h_path = rp.interim_dir / "oe2" / "ev" / "perfil_horario_carga.csv"

    run_bess_sizing(
        out_dir=out_dir,
        mall_energy_kwh_day=float(mall["energy_kwh_day"]),
        pv_profile_24h_path=pv_profile_24h_path,
        ev_profile_24h_path=ev_profile_24h_path,
        dod=float(bess_cfg["dod"]),
        c_rate=float(bess_cfg["c_rate"]),
        round_kwh=float(bess_cfg["round_kwh"]),
        mall_shape_24h=None if mall.get("shape_24h") is None else mall["shape_24h"],
    )

if __name__ == "__main__":
    main()
