#!/usr/bin/env python3
"""
Build CityLearn Dataset Schema (PV + BESS)
Constructs schema_pv_bess.json from raw data
"""
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from scripts._common import load_all

print("\n" + "=" * 80)
print("BUILDING CITYLEARN DATASET (PV + BESS)")
print("=" * 80 + "\n")

try:
    # Load config
    logger.info("Loading configuration...")
    cfg, rp = load_all("configs/default.yaml")

    dataset_name = cfg["oe3"]["dataset"]["name"]
    processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

    if processed_dataset_dir.exists() and (processed_dataset_dir / "schema_pv_bess.json").exists():
        logger.info(f"Dataset already exists: {processed_dataset_dir}")
        schema_path = processed_dataset_dir / "schema_pv_bess.json"
    else:
        logger.info("Building dataset...")
        built = build_citylearn_dataset(
            cfg=cfg,
            _raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )
        schema_path = built.dataset_dir / "schema_pv_bess.json"
        logger.info(f"Dataset built: {built.dataset_dir}")

    # Verify schema
    if schema_path.exists():
        size_mb = schema_path.stat().st_size / (1024 * 1024)
        logger.info(f"[OK] Schema exists: {schema_path} ({size_mb:.2f} MB)")

        # Verify structure
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema: dict[str, Any] = json.load(f)
            buildings_list: list[dict[str, Any]] = schema.get('buildings', [])
            logger.info(f"[OK] Schema structure verified: {len(buildings_list)} buildings")

            # Check first building
            if buildings_list:
                b: dict[str, Any] = buildings_list[0]
                b_name: str = str(b.get('name', 'unnamed'))
                ev_chargers: list[Any] = b.get('electric_vehicle_chargers', [])
                has_battery: bool = bool(b.get('battery'))
                has_pv: bool = bool(b.get('solar_electric_power_generation'))

                logger.info(f"    Building 0: {b_name}")
                logger.info(f"      - Electric Vehicle Charger: {len(ev_chargers)} units")
                logger.info(f"      - Battery: {'Yes' if has_battery else 'No'}")
                logger.info(f"      - PV: {'Yes' if has_pv else 'No'}")

        print("\n" + "=" * 80)
        print("DATASET BUILD SUCCESSFUL")
        print("=" * 80)
        sys.exit(0)
    else:
        logger.error(f"Schema not found after build: {schema_path}")
        sys.exit(1)

except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
    sys.exit(1)
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in schema: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Error building dataset: {e}", exc_info=True)
    sys.exit(1)
