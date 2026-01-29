#!/usr/bin/env python
"""
FULL PIPELINE: Dataset Build + Baseline Calculation (NO AGENTS)
Seguro, robusto, sin interrupciones, deja consola libre
"""
from __future__ import annotations

import sys
import logging
import traceback
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iquitos_citylearn.config import load_config, load_paths, RuntimePaths
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.utils.logging import setup_logging


def log_section(logger, title: str) -> None:
    """Print section header with formatting"""
    logger.info("=" * 80)
    logger.info(f"{'':=^80}")
    logger.info(f"{title:^80}")
    logger.info(f"{'':=^80}")
    logger.info("=" * 80)


def validate_oe2_artifacts(paths: RuntimePaths) -> bool:
    """Validate that all required OE2 artifacts exist"""
    logger = logging.getLogger(__name__)

    required_files = [
        paths.interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv",
        paths.interim_dir / "oe2" / "chargers" / "perfil_horario_carga.csv",
        paths.interim_dir / "oe2" / "chargers" / "individual_chargers.json",
        paths.interim_dir / "oe2" / "bess" / "bess_config.json",
    ]

    logger.info("Validating OE2 artifacts...")
    all_exist = True
    for fpath in required_files:
        exists = fpath.exists()
        status = "[OK]" if exists else "[MISSING]"
            cfg=cfg,
            _raw_dir=paths.raw_dir,
            interim_dir=paths.interim_dir,
            processed_dir=paths.processed_dir,
        )

        schema_path = dataset.schema_path
        logger.info(f"[OK] Schema generated: {schema_path}")
        logger.info(f"[OK] Building CSVs created in processed directory")

        return True
    except Exception as e:
        logger.error(f"[ERROR] Dataset build failed: {str(e)}")
    log_section(logger, "PHASE 2: BASELINE CALCULATION (NO AGENTS)")

    try:
        import pandas as pd
        import numpy as np
        from citylearn import CityLearnEnv
        import json

        # Find schema
        schema_files = list((paths.outputs_dir / "oe3_simulations").glob("schema_*.json"))
        if not schema_files:
            logger.error("✗ No schema found in outputs/oe3_simulations/")
            return False

        schema_path = sorted(schema_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        logger.info(f"Using schema: {schema_path.name}")

        # Initialize environment
        logger.info("Initializing CityLearn environment...")
        env = CityLearnEnv(str(schema_path))
        obs = env.reset()

        logger.info(f"✓ Environment initialized")
        logger.info(f"  - Observation shape: {len(obs) if isinstance(obs, list) else obs.shape}")
        logger.info(f"  - Timesteps per year: 8,760")

        # Run baseline simulation
        logger.info("\nRunning simulation (8,760 hours)...")

        pv_total = 0.0
        grid_total = 0.0
        co2_total = 0.0
        curtailed_total = 0.0
        demand_total = 0.0
        pv_to_load = 0.0
        pv_to_bess = 0.0

        start_time = datetime.now()

        for step in range(8760):
            # Actions: all zeros (no intelligent control)
            action = [0.0] * len(env.action_space.sample())
            obs, reward, done, info = env.step(action)

            # Extract metrics from environment (approximated)
            # In baseline: chargers always on at full power if demand
            if hasattr(env, 'buildings') and len(env.buildings) > 0:
                building = env.buildings[0]

                # PV generation
                if hasattr(building, 'solar_generation'):
                    pv_gen = building.solar_generation[-1] if building.solar_generation else 0
                    pv_total += max(0, pv_gen)

                # Grid import
                if hasattr(building, 'grid_electricity_import'):
                    grid_import = building.grid_electricity_import[-1] if building.grid_electricity_import else 0
                    grid_total += max(0, grid_import)

                # CO2
                if hasattr(building, 'carbon_intensity'):
                    ci = building.carbon_intensity[-1] if building.carbon_intensity else 0.4521
                    co2_total += max(0, grid_import) * ci

            # Progress every 500 hours
            if (step + 1) % 500 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                pct = ((step + 1) / 8760) * 100
                logger.info(f"  hora {step+1:5d}/8760 ({pct:5.1f}%) | "
                           f"PV={pv_total/1000:7.0f} MWh | "
                           f"Grid={grid_total/1000:7.0f} MWh | "
                           f"CO2={co2_total/1000:7.0f} tCO2")

            if done:
                logger.info(f"  Simulation ended at step {step+1}")
                break

        elapsed_total = (datetime.now() - start_time).total_seconds() / 60
        logger.info(f"\n✓ Simulation completed in {elapsed_total:.2f} minutes")

        # Final results
        log_section(logger, "BASELINE RESULTS")
        logger.info(f"PV Generated:        {pv_total/1e6:10.2f} GWh")
        logger.info(f"Grid Import:         {grid_total/1e6:10.2f} GWh")
        logger.info(f"CO2 Emissions:       {co2_total/1e6:10.2f} MtCO2")
        logger.info(f"Grid per 1 MWh PV:   {(grid_total/pv_total if pv_total > 0 else 0):.2f}x")

        # Save results
        results = {
            "timestamp": datetime.now().isoformat(),
            "scenario": "uncontrolled_baseline",
            "duration_years": 1,
            "timesteps": 8760,
            "metrics": {
                "pv_generated_kwh": float(pv_total),
                "grid_import_kwh": float(grid_total),
                "co2_emissions_kg": float(co2_total),
                "grid_per_pv_ratio": float(grid_total / pv_total if pv_total > 0 else 0),
            }
        }

        results_path = paths.outputs_dir / "baseline_results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"\n✓ Results saved: {results_path}")

        return True

    except Exception as e:
        logger.error(f"✗ Baseline calculation failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def main():
    """Main pipeline: Dataset + Baseline"""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        log_section(logger, "FULL PIPELINE: BUILD DATASET + CALCULATE BASELINE")
        logger.info(f"Start time: {datetime.now().isoformat()}")
        logger.info("Configuration: No agent training (SAC/PPO/A2C skipped)")

        # Load config and paths
        cfg = load_config("configs/default.yaml")
        paths = load_paths(cfg)

        logger.info(f"Output dir: {paths.outputs_dir}")
        logger.info(f"Interim dir: {paths.interim_dir}")

        # Validate OE2 artifacts
        if not validate_oe2_artifacts(paths):
            logger.error("\n[FATAL] Missing OE2 artifacts. Cannot proceed.")
            return False

        logger.info("[OK] All OE2 artifacts found\n")
        if not build_dataset_phase(cfg, paths):
            logger.error("\n[FATAL] Dataset build failed. Cannot proceed to baseline.")
            return False

        # Phase 2: Baseline
        if not calculate_baseline_phase(cfg, paths):
            logger.error("\n[FATAL] Baseline calculation failed.")
            return False

        # Success
        log_section(logger, "PIPELINE COMPLETE [OK]")
        logger.info(f"End time: {datetime.now().isoformat()}")
        logger.info("\nNext steps:")
        logger.info("  1. Review baseline metrics in outputs/baseline_results.json")
        logger.info("  2. Compare with trained agents when ready")
        logger.info("  3. Analyze PV utilization and grid dependency")

        return True

    except Exception as e:
        logger.error(f"\n[FATAL] Pipeline failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
