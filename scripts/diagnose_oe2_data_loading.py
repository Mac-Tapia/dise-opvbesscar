#!/usr/bin/env python3
"""
DIAGNOSIS SCRIPT: OE2 Data Loading Verification (2026-02-04)

Verifica que los datos REALES de OE2 se cargan correctamente en CityLearn.

Checks:
1. OE2 archivos existen
2. Datos se leen correctamente
3. Datos se escriben en CityLearn schema
4. 8,760 timesteps están presentes
"""

from __future__ import annotations
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
import pandas as pd
import json

from iquitos_citylearn.config import load_config, load_paths
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset, _load_oe2_artifacts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def diagnose():
    """Ejecuta diagnóstico completo del cargue de datos OE2."""

    logger.info("")
    logger.info("="*80)
    logger.info("[DIAGNÓSTICO] Verificando cargue de datos OE2 en CityLearn")
    logger.info("="*80)
    logger.info("")

    # Step 1: Load config and paths
    logger.info("STEP 1: Cargando configuración...")
    cfg = load_config(Path(__file__).parent.parent / "configs" / "default.yaml")
    paths = load_paths(cfg)
    logger.info("✓ Config cargada: %s", cfg.get('project', {}).get('name', 'unknown'))
    logger.info("✓ Paths: interim_dir = %s", paths.interim_dir)
    logger.info("")

    # Step 2: Load OE2 artifacts
    logger.info("STEP 2: Leyendo artifacts OE2...")
    artifacts = _load_oe2_artifacts(paths.interim_dir)

    # Check what was loaded
    artifact_keys = list(artifacts.keys())
    logger.info("Artifacts cargados (%d total):", len(artifact_keys))
    for key in artifact_keys:
        val = artifacts[key]
        if isinstance(val, pd.DataFrame):
            logger.info("  - %s: DataFrame con shape %s", key, val.shape)
        elif isinstance(val, dict):
            logger.info("  - %s: Dict con %d keys", key, len(val))
        elif isinstance(val, list):
            logger.info("  - %s: List con %d items", key, len(val))
        elif isinstance(val, Path):
            logger.info("  - %s: Path", key)
        else:
            logger.info("  - %s: %s", key, type(val).__name__)
    logger.info("")

    # Step 3: Check critical data
    logger.info("STEP 3: Verificando datos críticos...")

    # Solar
    if "solar_ts" in artifacts:
        solar_df = artifacts["solar_ts"]
        logger.info("✓ Solar timeseries: %d filas (esperado 8,760)", len(solar_df))
        logger.info("  Columnas: %s", list(solar_df.columns)[:5])
        if len(solar_df) > 0:
            logger.info("  Suma: %.1f (esperado ~8M kWh/año)", solar_df.iloc[:, 0].sum() if len(solar_df.columns) > 0 else 0)
    else:
        logger.error("✗ Solar timeseries NO cargada")

    # Mall demand
    if "mall_demand" in artifacts:
        mall_df = artifacts["mall_demand"]
        logger.info("✓ Mall demand: %d filas", len(mall_df))
        logger.info("  Columnas: %s", list(mall_df.columns)[:5])
    else:
        logger.warning("⚠ Mall demand NO cargada (usará sintético)")

    # Chargers
    if "chargers_hourly_profiles_annual" in artifacts:
        charger_df = artifacts["chargers_hourly_profiles_annual"]
        logger.info("✓ Charger profiles anuales: shape %s", charger_df.shape)
    else:
        logger.error("✗ Charger profiles NO cargados")

    # BESS
    if "bess_simulation_hourly" in artifacts or "bess" in artifacts:
        logger.info("✓ BESS configuration found")
    else:
        logger.warning("⚠ BESS simulation NO cargada")

    logger.info("")

    # Step 4: Build dataset and check output
    logger.info("STEP 4: Construyendo dataset CityLearn...")
    try:
        result = build_citylearn_dataset(
            cfg=cfg,
            _raw_dir=paths.raw_dir,
            interim_dir=paths.interim_dir,
            processed_dir=paths.processed_dir,
        )
        logger.info("✓ Dataset construido en: %s", result.dataset_dir)
        logger.info("  Schema: %s", result.schema_path)
        logger.info("  Building: %s", result.building_name)
    except Exception as e:
        logger.error("✗ Error construyendo dataset: %s", e)
        return False

    logger.info("")

    # Step 5: Verify output files
    logger.info("STEP 5: Verificando archivos de salida...")

    # Check schema.json
    schema_path = result.dataset_dir / "schema.json"
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        n_buildings = len(schema.get("buildings", {}))
        logger.info("✓ schema.json: %d buildings", n_buildings)

        # Check simulation length
        sim_end = schema.get("simulation_end_time_step", 0)
        logger.info("  Simulation end time step: %d (esperado 8,759)", sim_end)
    else:
        logger.error("✗ schema.json NO existe")

    # Check energy_simulation.csv
    energy_path = result.dataset_dir / "Building_" + result.building_name / "energy_simulation.csv" if result.building_name != "Building_1" else result.dataset_dir / "energy_simulation.csv"
    if not energy_path.exists():
        # Try alternative paths
        for alt_path in [result.dataset_dir / "energy_simulation.csv",
                         result.dataset_dir / f"Building_{result.building_name}" / "energy_simulation.csv"]:
            if alt_path.exists():
                energy_path = alt_path
                break

    if energy_path.exists():
        energy_df = pd.read_csv(energy_path)
        logger.info("✓ energy_simulation.csv: %d filas", len(energy_df))

        # Check for key columns
        cols = list(energy_df.columns)
        has_load = any("non_shiftable" in c.lower() or "load" in c.lower() for c in cols)
        has_solar = any("solar" in c.lower() for c in cols)

        logger.info("  Non-shiftable load: %s", "✓" if has_load else "✗")
        logger.info("  Solar generation: %s", "✓" if has_solar else "✗")

        # Check data values
        if has_load:
            load_col = next((c for c in cols if "non_shiftable" in c.lower() or "load" in c.lower()), None)
            if load_col:
                load_sum = energy_df[load_col].sum()
                logger.info("    Sum: %.1f kWh (esperado ~880k kWh/año)", load_sum)

        if has_solar:
            solar_col = next((c for c in cols if "solar" in c.lower()), None)
            if solar_col:
                solar_sum = energy_df[solar_col].sum()
                logger.info("    Sum: %.1f (esperado ~8M kWh/año)", solar_sum)
    else:
        logger.error("✗ energy_simulation.csv NO existe en: %s", energy_path)

    logger.info("")

    # Step 6: Summary
    logger.info("="*80)
    logger.info("[RESULTADO] Diagnóstico completado")
    logger.info("="*80)

    logger.info("")
    logger.info("✓ = Correcto   ⚠ = Warning   ✗ = Error")
    logger.info("")
    logger.info("Si todos están ✓, los datos OE2 REALES están cargándose correctamente.")
    logger.info("Si hay ✗ en solar, mall o chargers, revisar _load_oe2_artifacts().")
    logger.info("")

    return True

if __name__ == "__main__":
    success = diagnose()
    sys.exit(0 if success else 1)
