#!/usr/bin/env python
"""Ejecuta el dimensionamiento del sistema BESS para Iquitos."""

from pathlib import Path
from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing

if __name__ == "__main__":
    out_dir = Path("data/interim/oe2/bess")

    print("\n" + "="*80)
    print("EJECUTANDO DIMENSIONAMIENTO DEL SISTEMA BESS - IQUITOS")
    print("="*80 + "\n")

    try:
        results = run_bess_sizing(
            out_dir=out_dir,
            mall_energy_kwh_day=21600,  # 7.88 GWh / 365 dias
            pv_profile_path=Path("data/interim/oe2/solar/pv_generation_timeseries.csv"),
            ev_profile_path=Path("data/interim/oe2/ev_demand/ev_profile_96intervals.csv"),
            mall_demand_path=Path("data/interim/oe2/demandamallkwh/demandamallhorakwh.csv"),
            dod=0.90,
            c_rate=0.60,
            pv_dc_kw=4049.56,
            sizing_mode="ev_open_hours",
            efficiency_roundtrip=0.90,
            autonomy_hours=4.0,
            generate_plots=True,
        )

        print("\n" + "="*80)
        print("✓ DIMENSIONAMIENTO BESS COMPLETADO EXITOSAMENTE")
        print("="*80 + "\n")

        if results:
            print("Resultados principales:")
            for key, value in list(results.items())[:10]:
                print(f"  {key}: {value}")

    except Exception as e:
        print(f"\n✗ ERROR durante la ejecución: {type(e).__name__}")
        print(f"  Detalle: {str(e)}\n")
        import traceback
        traceback.print_exc()
