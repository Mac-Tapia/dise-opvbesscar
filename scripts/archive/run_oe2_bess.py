#!/usr/bin/env python3
"""
Ejecuta el dimensionamiento del sistema BESS.

Uso:
    python scripts/run_oe2_bess.py --config configs/default.yaml [--no-plots]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe2.bess import run_bess_sizing
from scripts._common import load_all


def main() -> None:
    ap = argparse.ArgumentParser(description="Dimensionamiento del sistema BESS")
    ap.add_argument("--config", default="configs/default.yaml", help="Archivo de configuración")
    ap.add_argument("--no-plots", action="store_true", help="Omitir generación de gráficas")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    out_dir = rp.interim_dir / "oe2" / "bess"
    mall = cfg["oe2"]["mall"]
    bess_cfg = cfg["oe2"]["bess"]
    solar_cfg = cfg["oe2"]["solar"]
    ev_cfg = cfg["oe2"]["ev_fleet"]
    location_cfg = cfg["oe2"].get("location", {})
    year = int(cfg["project"]["year"])

    # Rutas de entrada
    pv_profile_path = rp.interim_dir / "oe2" / "solar" / "pv_profile_24h.csv"
    ev_profile_path = rp.interim_dir / "oe2" / "chargers" / "perfil_horario_carga.csv"
    demand_dir = rp.interim_dir / "oe2" / "demandamallkwh"
    mall_demand_candidates = [
        demand_dir / "demandamallkwh.csv",
        demand_dir / "demanda_mall_kwh.csv",
    ]
    mall_demand_path = next((p for p in mall_demand_candidates if p.exists()), None)

    discharge_hours = None
    if bool(bess_cfg.get("discharge_only_ev_hours", False)):
        opening_hour = int(ev_cfg["opening_hour"])
        closing_hour = int(ev_cfg["closing_hour"])
        discharge_hours = list(range(opening_hour, closing_hour + 1))

    soc_min_percent = bess_cfg.get("min_soc_percent")
    if soc_min_percent is not None:
        soc_min_percent = float(soc_min_percent)

    discharge_only_no_solar = bool(bess_cfg.get("discharge_only_no_solar", False))
    pv_night_threshold_kwh = float(bess_cfg.get("pv_night_threshold_kwh", 0.1))

    result = run_bess_sizing(
        out_dir=out_dir,
        mall_energy_kwh_day=float(mall["energy_kwh_day"]),
        pv_profile_path=pv_profile_path,
        ev_profile_path=ev_profile_path,
        mall_demand_path=mall_demand_path,
        dod=float(bess_cfg["dod"]),
        c_rate=float(bess_cfg["c_rate"]),
        round_kwh=float(bess_cfg["round_kwh"]),
        efficiency_roundtrip=float(bess_cfg.get("efficiency_roundtrip", 0.90)),
        autonomy_hours=float(bess_cfg.get("autonomy_hours", 4.0)),
        pv_dc_kw=float(solar_cfg["target_dc_kw"]),
        tz=str(location_cfg.get("tz")) if location_cfg.get("tz") else None,
        sizing_mode=str(bess_cfg.get("sizing_mode", "ev_open_hours")),
        soc_min_percent=soc_min_percent,
        load_scope=str(bess_cfg.get("load_scope", "total")),
        discharge_hours=discharge_hours,
        discharge_only_no_solar=discharge_only_no_solar,
        pv_night_threshold_kwh=pv_night_threshold_kwh,
        surplus_target_kwh_day=float(bess_cfg.get("surplus_target_kwh_day", 0) or 0),
        year=year,
        generate_plots=not args.no_plots,
        reports_dir=rp.reports_dir,
        fixed_capacity_kwh=float(bess_cfg.get("fixed_capacity_kwh", 0) or 0),
        fixed_power_kw=float(bess_cfg.get("fixed_power_kw", 0) or 0),
    )

    # Mostrar resumen
    print("\nRESUMEN FINAL BESS:")
    assert isinstance(result['capacity_kwh'], (int, float)), "capacity_kwh debe ser numérico"
    assert isinstance(result['nominal_power_kw'], (int, float)), "nominal_power_kw debe ser numérico"
    assert isinstance(result['self_sufficiency'], (int, float)), "self_sufficiency debe ser numérico"
    assert isinstance(result['grid_import_kwh_day'], (int, float)), "grid_import_kwh_day debe ser numérico"

    capacity_kwh: float = float(result['capacity_kwh'])
    power_kw: float = float(result['nominal_power_kw'])
    self_suff: float = float(result['self_sufficiency'])
    grid_import: float = float(result['grid_import_kwh_day'])

    print(f"   Capacidad: {capacity_kwh:.0f} kWh")
    print(f"   Potencia:  {power_kw:.0f} kW")
    print(f"   Autosuficiencia: {self_suff * 100:.1f}%")
    print(f"   Import red: {grid_import:.0f} kWh/dia")


if __name__ == "__main__":
    main()
