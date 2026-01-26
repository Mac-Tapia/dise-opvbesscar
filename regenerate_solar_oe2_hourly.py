#!/usr/bin/env python3
"""
Regenera datos solares OE2 con resolución HORARIA (1 hora = 3600 segundos).

Este script calcula la generación solar correcta usando:
- PVGIS TMY (datos meteorológicos anuales típicos)
- Modelo Sandia completo (pérdidas reales)
- Resolución HORARIA (8,760 rows/año) para OE3
- Configuración: 4,162 kW DC + 3,201.2 kW AC

Pasos:
1. Descargar TMY desde PVGIS
2. Interpolar a resolución horaria
3. Aplicar modelo Sandia (pérdidas, temperatura)
4. Guardar CSV con ac_power_kw horario
5. Comparar con OE2 target (3.97 GWh)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Validar Python 3.11
if sys.version_info[:2] != (3, 11):
    print(f"ERROR: Python 3.11 requerido, tienes {sys.version_info[0]}.{sys.version_info[1]}")
    sys.exit(1)

try:
    from iquitos_citylearn.utils.logging import setup_logging
    from iquitos_citylearn.oe2.solar_pvlib import build_pv_timeseries_sandia, PVSystemConfig
    from scripts._common import load_all
except ImportError as e:
    print(f"ERROR importando módulos: {e}")
    print("Asegúrate que estés en el venv correcto y el proyecto está instalado")
    sys.exit(1)

import pandas as pd

def main() -> None:
    """Regenera datos solares OE2 con resolución horaria."""

    print("=" * 100)
    print("REGENERACION DE DATOS SOLARES OE2 - RESOLUCION HORARIA (1 HORA)")
    print("=" * 100)

    setup_logging()

    # Cargar configuración
    cfg, rp = load_all("configs/default.yaml")

    out_dir = rp.interim_dir / "oe2" / "solar"
    out_dir.mkdir(parents=True, exist_ok=True)

    loc = cfg["oe2"]["location"]
    solar = cfg["oe2"]["solar"]

    print(f"\n[CONFIG OE2]")
    print(f"  Ubicación: Iquitos, Perú")
    print(f"    Lat: {loc['lat']}°, Lon: {loc['lon']}°")
    print(f"  Panel Solar: {solar.get('target_dc_kw', 4162)} kW DC")
    print(f"  Inversor: {solar.get('target_ac_kw', 3201.2)} kW AC")
    print(f"  Objetivo anual: {solar.get('target_annual_kwh', 3972478):,} kWh")
    print(f"  Resolución: 1 HORA (8,760 rows/año para OE3)")

    # Configuración PV
    # total_losses_factor se calcula automáticamente desde pérdidas individuales
    config = PVSystemConfig(
        latitude=float(loc["lat"]),
        longitude=float(loc["lon"]),
        altitude=float(loc.get("alt", 104.0)),
        timezone=str(loc["tz"]),
        area_total_m2=float(solar.get("area_total_m2", 20637.0)),
        factor_diseno=float(solar.get("factor_diseno", 0.65)),
        tilt=float(solar.get("surface_tilt", 10.0)),
        azimuth=float(solar.get("surface_azimuth", 0.0)),
    )

    # Ejecutar simulación con resolución HORARIA (3600 segundos = 1 hora)
    print(f"\n[EJECUCION]")
    print(f"  Descargando datos TMY desde PVGIS...")
    print(f"  Aplicando modelo Sandia (temperatura, PoA, etc)...")
    print(f"  Interpolando a resolución: 1 HORA")
    print(f"  Calculando generación ac_power_kw...")

    results_df, metadata = build_pv_timeseries_sandia(
        year=int(cfg["project"]["year"]),
        config=config,
        target_dc_kw=float(solar["target_dc_kw"]),
        target_ac_kw=float(solar["target_ac_kw"]),
        target_annual_kwh=float(solar["target_annual_kwh"]),
        seconds_per_time_step=3600,  # 1 HORA - CRITICO PARA OE3
        selection_mode=str(solar.get("selection_mode", "manual")),
        candidate_count=int(solar.get("candidate_count", 5)),
        selection_metric=str(solar.get("selection_metric", "energy_per_m2")),
    )

    # Validar resultado
    n_rows = len(results_df)
    annual_kwh = results_df["ac_energy_kwh"].sum()

    print(f"\n[RESULTADO]")
    print(f"  Filas generadas: {n_rows}")
    print(f"  Resolución: {n_rows} rows = 8,760 horas/año ✓" if n_rows == 8760 else f"  WARN: {n_rows} rows != 8,760")
    print(f"  Generación anual: {annual_kwh:,.0f} kWh = {annual_kwh/1e6:.2f} GWh")
    print(f"  Target OE2: {solar.get('target_annual_kwh', 3972478):,} kWh = {float(solar.get('target_annual_kwh', 3972478))/1e6:.2f} GWh")

    # Guardar CSV para OE3
    output_csv = out_dir / "pv_generation_timeseries.csv"

    # Formato esperado por OE3: timestamp, ac_power_kw (y otras columnas)
    export_df = results_df[["ac_power_kw"]].copy()
    export_df.index.name = "timestamp"
    export_df.to_csv(output_csv)

    print(f"\n[ARCHIVO GENERADO]")
    print(f"  Guardado en: {output_csv}")
    print(f"  Filas: {len(export_df)}")
    print(f"  Columnas: {list(export_df.columns)}")
    print(f"  Formato: CSV con timestamp + ac_power_kw (horario)")

    # Validación final
    print(f"\n[VALIDACION]")
    df_check = pd.read_csv(output_csv, index_col=0)
    print(f"  ✓ CSV cargado: {len(df_check)} filas")
    print(f"  ✓ ac_power_kw rango: {df_check['ac_power_kw'].min():.2f} - {df_check['ac_power_kw'].max():.2f} kW")
    print(f"  ✓ Generación total: {df_check['ac_power_kw'].sum():.0f} kWh")

    print(f"\n" + "=" * 100)
    print(f"EXITO: Datos solares regenerados con resolución HORARIA para OE3")
    print(f"=" * 100 + "\n")

if __name__ == "__main__":
    main()
