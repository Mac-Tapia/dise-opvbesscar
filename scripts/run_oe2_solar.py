#!/usr/bin/env python3
"""
Ejecuta el dimensionamiento solar con modelo Sandia y PVGIS TMY.

Uso:
    python scripts/run_oe2_solar.py --config configs/default.yaml [--interval 15] [--no-plots]
"""
from __future__ import annotations

import argparse
import shutil

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe2.solar_pvlib import run_solar_sizing, prepare_solar_for_citylearn
from iquitos_citylearn.oe2.solar_plots import generate_all_solar_plots
from scripts._common import load_all


def main() -> None:
    ap = argparse.ArgumentParser(description="Dimensionamiento solar con Sandia + PVGIS")
    ap.add_argument("--config", default="configs/default.yaml", help="Archivo de configuración")
    ap.add_argument("--interval", type=int, default=60, help="Intervalo en minutos (default: 60 HORAS para OE3)")
    ap.add_argument("--no-plots", action="store_true", help="No generar gráficas")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    out_dir = rp.interim_dir / "oe2" / "solar"
    loc = cfg["oe2"]["location"]
    solar = cfg["oe2"]["solar"]
    selection_mode = str(solar.get("selection_mode", "manual"))
    candidate_count = int(solar.get("candidate_count", 5))
    selection_metric = str(solar.get("selection_metric", "energy_per_m2"))

    # Parámetros Sandia para modelo riguroso con PVGIS TMY
    sandia_params = {
        'altitude': float(loc.get("alt", 104.0)),
        'area_total_m2': float(solar.get("area_total_m2", 20637.0)),
        'factor_diseno': float(solar.get("factor_diseno", 0.65)),
        'tilt': float(solar.get("surface_tilt", 10.0)),
        'azimuth': float(solar.get("surface_azimuth", 0.0)),
        'module_name': str(solar.get("module_name", "Kyocera_Solar_KS20__2008__E__")),
        'inverter_name': str(solar.get("inverter_name", "Eaton__Xpert1670")),
    }

    # Usar intervalo de 15 minutos por defecto para mayor precisión
    seconds_per_time_step = args.interval * 60

    result = run_solar_sizing(
        out_dir=out_dir,
        year=int(cfg["project"]["year"]),
        tz=str(loc["tz"]),
        lat=float(loc["lat"]),
        lon=float(loc["lon"]),
        seconds_per_time_step=seconds_per_time_step,
        target_dc_kw=float(solar["target_dc_kw"]),
        target_ac_kw=float(solar["target_ac_kw"]),
        target_annual_kwh=float(solar["target_annual_kwh"]),
        use_pvlib=bool(solar.get("use_pvlib", True)),
        selection_mode=selection_mode,
        candidate_count=candidate_count,
        selection_metric=selection_metric,
        **sandia_params
    )

    analyses_dir = rp.analyses_dir / "oe2" / "solar"
    analyses_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "pv_candidates_modules.csv",
        "pv_candidates_inverters.csv",
        "pv_candidates_combinations.csv",
    ):
        src = out_dir / name
        if src.exists():
            shutil.copy2(src, analyses_dir / name)

    # Preparar datos para CityLearn (OE3)
    pv_timeseries_path = out_dir / "pv_generation_timeseries.csv"
    if pv_timeseries_path.exists():
        prepare_solar_for_citylearn(
            pv_timeseries_path=pv_timeseries_path,
            out_dir=out_dir,
            pv_dc_kw=float(solar["target_dc_kw"]),
            pv_ac_kw=float(solar["target_ac_kw"]),
            year=int(cfg["project"]["year"]),
        )

    # Generar gráficas avanzadas
    if not args.no_plots:
        plots_dir = rp.reports_dir / "oe2" / "solar_plots"
        generate_all_solar_plots(out_dir, plots_dir)

    # Mostrar resumen final
    print("\nRESUMEN FINAL SOLAR:")
    print(f"   Capacidad DC: {result['target_dc_kw']:,.0f} kWp")
    print(f"   Energía anual: {result['annual_kwh']/1e6:,.3f} GWh")
    print(f"   Factor de capacidad: {result['capacity_factor']*100:.1f}%")
    print(f"   Performance Ratio: {result['performance_ratio']*100:.1f}%")


if __name__ == "__main__":
    main()
