#!/usr/bin/env python
"""
Script para ejecutar el BESS y generar dataset horario del ano 2024.

Genera un CSV con:
- Indice: DatetimeIndex (2024-01-01 a 2024-12-31, horario UTC-5)
- Columnas: Simulacion horaria del BESS (8,760 timesteps)

Salida: data/oe2/bess/bess_hourly_dataset_2024.csv
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Add src to path
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))

from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing


def main():
    """Ejecutar BESS y guardar dataset con fechas 2024."""

    logger.info("\n" + "="*80)
    logger.info("GENERACION DE DATASET BESS HORARIO 2024")
    logger.info("="*80)

    # ========================================================================
    # DEFINIR RUTAS
    # ========================================================================

    # Directorio de trabajo
    interim_dir = workspace_root / "data/interim/oe2"
    oe2_dir = workspace_root / "data/oe2"
    bess_output_dir = oe2_dir / "bess"

    # Crear directorio de salida
    bess_output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"\n[OK] Directorio de salida: {bess_output_dir}")

    # Rutas de entrada
    pv_profile_path = interim_dir / "solar" / "pv_hourly_profile.csv"
    ev_profile_path = interim_dir / "chargers" / "ev_hourly_profile.csv"
    mall_demand_path = interim_dir / "mall" / "mall_demand_real.csv"

    logger.info(f"\n📁 Rutas de entrada:")
    logger.info(f"   PV Profile:   {pv_profile_path.name}")
    logger.info(f"   EV Profile:   {ev_profile_path.name}")
    logger.info(f"   Mall Demand:  {mall_demand_path.name}")

    # Verificar que existan
    if not pv_profile_path.exists():
        logger.error(f"[X] No encontrado: {pv_profile_path}")
        return 1
    if not ev_profile_path.exists():
        logger.error(f"[X] No encontrado: {ev_profile_path}")
        return 1

    # Mall demand es opcional
    if not mall_demand_path.exists():
        logger.warning(f"[!]  No encontrado: {mall_demand_path}, usando demanda sintetica")

    # ========================================================================
    # EJECUTAR BESS
    # ========================================================================

    logger.info(f"\n🚀 Ejecutando dimensionamiento BESS...")

    try:
        results = run_bess_sizing(
            out_dir=interim_dir,
            mall_energy_kwh_day=100.0,  # Fallback: 100 kWh/dia
            pv_profile_path=pv_profile_path,
            ev_profile_path=ev_profile_path,
            mall_demand_path=mall_demand_path if mall_demand_path.exists() else None,
            dod=0.80,
            c_rate=0.36,  # v5.2: 0.36 C-rate
            round_kwh=10.0,
            efficiency_roundtrip=0.95,
            autonomy_hours=4.0,
            pv_dc_kw=4050.0,  # 4,050 kWp (OE2 dimensionamiento)
            tz="America/Lima",  # UTC-5
            sizing_mode="ev_open_hours",
            soc_min_percent=20.0,
            year=2024,
            generate_plots=True,
            reports_dir=bess_output_dir,
        )

        logger.info(f"[OK] BESS ejecutado exitosamente")

    except Exception as e:
        logger.error(f"[X] Error ejecutando BESS: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ========================================================================
    # OBTENER DATAFRAME DE SIMULACION
    # ========================================================================

    if 'df_sim' not in results:
        logger.error("[X] No se encontro 'df_sim' en resultados del BESS")
        return 1

    df_sim = results['df_sim']
    logger.info(f"\n[GRAPH] Datos de simulacion:")
    logger.info(f"   Shape: {df_sim.shape}")
    logger.info(f"   Columnas: {', '.join(df_sim.columns.tolist())}")

    # ========================================================================
    # CREAR INDICE DE FECHAS 2024
    # ========================================================================

    # Crear DatetimeIndex para 2024 (8,760 horas)
    # Hora local Peru: UTC-5
    date_index = pd.date_range(
        start="2024-01-01 00:00:00",
        periods=8760,
        freq="h",
        tz="America/Lima"
    )

    logger.info(f"\n📅 Indice temporal:")
    logger.info(f"   Inicio: {date_index[0]}")
    logger.info(f"   Fin: {date_index[-1]}")
    logger.info(f"   Periodos: {len(date_index)}")
    logger.info(f"   Frecuencia: {date_index.freq}")

    # ========================================================================
    # ASIGNAR INDICE Y GUARDAR
    # ========================================================================

    # Asignar indice de fechas al DataFrame
    df_output = df_sim.copy()
    df_output.index = date_index

    # Asegurar que el indice tenga nombre
    df_output.index.name = "datetime"

    # Guardar CSV
    output_csv = bess_output_dir / "bess_hourly_dataset_2024.csv"

    logger.info(f"\n💾 Guardando dataset...")
    df_output.to_csv(output_csv)
    logger.info(f"   [OK] Guardado en: {output_csv}")
    logger.info(f"   Tamano: {output_csv.stat().st_size / (1024*1024):.1f} MB")

    # ========================================================================
    # VALIDACION Y RESUMEN
    # ========================================================================

    logger.info(f"\n[OK] DATASET GENERADO EXITOSAMENTE")
    logger.info(f"\n📋 RESUMEN:")
    logger.info(f"   Archivo: bess_hourly_dataset_2024.csv")
    logger.info(f"   Ubicacion: {bess_output_dir}")
    logger.info(f"   Dimensiones: {df_output.shape[0]} filas × {df_output.shape[1]} columnas")
    logger.info(f"   Indice: DatetimeIndex (2024, horario, UTC-5)")
    logger.info(f"   Periodo: {df_output.index[0].strftime('%Y-%m-%d %H:%M')} a {df_output.index[-1].strftime('%Y-%m-%d %H:%M')}")

    # Mostrar primeras y ultimas filas
    logger.info(f"\n📖 Primeras 5 filas:")
    for idx, row in df_output.head(5).iterrows():
        logger.info(f"   {idx}: {row['pv_kwh']:.1f} kWh (PV), {row['soc_percent']:.1f}% (SOC)")

    logger.info(f"\n📖 Ultimas 5 filas:")
    for idx, row in df_output.tail(5).iterrows():
        logger.info(f"   {idx}: {row['pv_kwh']:.1f} kWh (PV), {row['soc_percent']:.1f}% (SOC)")

    # Estadisticas
    logger.info(f"\n[GRAPH] Estadisticas anuales:")
    logger.info(f"   PV generacion: {df_output['pv_kwh'].sum():,.0f} kWh")
    logger.info(f"   Carga EV: {df_output['ev_kwh'].sum():,.0f} kWh")
    logger.info(f"   Carga Mall: {df_output['mall_kwh'].sum():,.0f} kWh")
    logger.info(f"   BESS carga: {df_output['bess_charge_kwh'].sum():,.0f} kWh")
    logger.info(f"   BESS descarga: {df_output['bess_discharge_kwh'].sum():,.0f} kWh")
    logger.info(f"   Grid importado: {df_output['grid_import_kwh'].sum():,.0f} kWh")
    logger.info(f"   Grid exportado: {df_output['grid_export_kwh'].sum():,.0f} kWh")

    # SOC (State of Charge)
    logger.info(f"\n🔋 BESS (Estado de Carga):")
    logger.info(f"   SOC minimo: {df_output['soc_percent'].min():.1f}%")
    logger.info(f"   SOC maximo: {df_output['soc_percent'].max():.1f}%")
    logger.info(f"   SOC promedio: {df_output['soc_percent'].mean():.1f}%")

    # Verificar integridad
    logger.info(f"\n[OK] Verificacion de integridad:")
    assert len(df_output) == 8760, f"Error: Se esperaban 8,760 filas, se obtuvieron {len(df_output)}"
    logger.info(f"   [OK] 8,760 filas (1 ano completo)")

    assert df_output.index.is_unique, "Error: Indice tiene duplicados"
    logger.info(f"   [OK] Indice unico")

    assert not df_output.isna().any().any(), "Error: Hay valores NaN"
    logger.info(f"   [OK] Sin valores NaN")

    assert df_output.index[0].year == 2024, "Error: Ano incorrecto"
    logger.info(f"   [OK] Ano 2024 correcto")

    logger.info(f"\n" + "="*80)
    logger.info(f"[OK] PROCESO COMPLETADO EXITOSAMENTE")
    logger.info(f"="*80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
