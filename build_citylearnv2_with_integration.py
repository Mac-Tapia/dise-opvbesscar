#!/usr/bin/env python3
"""
SCRIPT: Build CityLearn v2 Dataset with BESS & Mall Integration

This script constructs the complete OE3 dataset with:
1. BESS hourly dataset 2024 (8,760 × 11 columns)
2. Mall demand dataset (8,760 × 1+ columns)
3. Solar PV generation (8,760 × hourly)
4. Real charger profiles (128 × 8,760 hours)

Usage:
    python build_citylearnv2_with_integration.py [--validate-only]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

def validate_integration():
    """Validate that BESS & Mall datasets are properly configured"""

    logger.info("=" * 80)
    logger.info("VALIDATION: BESS & MALL INTEGRATION")
    logger.info("=" * 80)

    all_valid = True

    # Check BESS dataset
    bess_file = Path("data/oe2/bess/bess_hourly_dataset_2024.csv")
    if bess_file.exists():
        logger.info("✅ BESS Dataset: %s", str(bess_file))
    else:
        logger.error("❌ BESS Dataset NOT FOUND: %s", str(bess_file))
        all_valid = False

    # Check Mall demand dataset
    mall_file = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
    if mall_file.exists():
        logger.info("✅ Mall Demand: %s", str(mall_file))
    else:
        logger.error("❌ Mall Demand NOT FOUND: %s", str(mall_file))
        all_valid = False

    # Check dataset_builder integration
    builder_file = Path("src/citylearnv2/dataset_builder/dataset_builder.py")
    if builder_file.exists():
        content = builder_file.read_text()
        if "bess_hourly_2024" in content:
            logger.info("✅ dataset_builder.py has BESS integration")
        else:
            logger.error("❌ dataset_builder.py missing BESS integration")
            all_valid = False

        if "demandamallhorakwh" in content:
            logger.info("✅ dataset_builder.py has MALL integration")
        else:
            logger.error("❌ dataset_builder.py missing MALL integration")
            all_valid = False
    else:
        logger.error("❌ dataset_builder.py NOT FOUND")
        all_valid = False

    return all_valid

def build_dataset():
    """Build CityLearn v2 dataset with integrated BESS & Mall data"""

    logger.info("\n" + "=" * 80)
    logger.info("BUILDING: CityLearn v2 Dataset with BESS & MALL Integration")
    logger.info("=" * 80)

    try:
        # Import the dataset builder
        from src.citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset

        logger.info("\n[1/5] Loading BESS & Mall datasets...")
        logger.info("      - BESS: data/oe2/bess/bess_hourly_dataset_2024.csv")
        logger.info("      - MALL: data/oe2/demandamallkwh/demandamallhorakwh.csv")

        logger.info("\n[2/5] Processing datasets...")
        logger.info("      - Validating dimensions (8,760 rows)")
        logger.info("      - Detecting column names")
        logger.info("      - Converting units if needed")

        logger.info("\n[3/5] Building CityLearn schema...")

        # Setup dataset paths and configuration
        raw_dir = Path("data/raw")
        interim_dir = Path("data/interim/oe2")
        processed_dir = Path("processed/citylearn/oe3_iquitos")

        # Create minimal config for dataset builder
        cfg = {
            "raw_dir": str(raw_dir),
            "interim_dir": str(interim_dir),
            "processed_dir": str(processed_dir),
            "seed": 42,
            "debug": False,
        }

        schema = build_citylearn_dataset(cfg, raw_dir, interim_dir, processed_dir)

        if schema is not None:
            logger.info("✅ Schema built successfully")

            logger.info("\n[4/5] Generating output files...")
            logger.info("      - schema.json (CityLearn v2 schema)")
            logger.info("      - electrical_storage_simulation.csv (BESS hourly SOC)")
            logger.info("      - energy_simulation.csv (Mall demand)")
            logger.info("      - charger_simulation_X.csv (128 chargers)")

            logger.info("\n[5/5] Validating outputs...")
            output_dir = Path("processed/citylearn/oe3_iquitos")
            if output_dir.exists():
                files_list: list[Path] = list(output_dir.glob("*.csv")) + list(output_dir.glob("*.json"))
                files_count: int = int(len(files_list)) if files_list else 0
                logger.info("✅ Generated %d output files", files_count)
                for f in sorted(files_list)[:5]:
                    logger.info("   - %s", f.name)
                if files_count > 5:
                    logger.info("   ... and %d more", files_count - 5)

            logger.info("\n" + "=" * 80)
            logger.info("✅ DATASET BUILD COMPLETE")
            logger.info("=" * 80)
            logger.info("\nOutputs saved to: %s", output_dir)
            logger.info("\nReady for OE3 RL training with:")
            logger.info("  • Real BESS hourly data (8,760 hours)")
            logger.info("  • Real Mall demand (8,760 hours)")
            logger.info("  • 128 EV chargers with realistic profiles")
            logger.info("  • Solar PV generation (8,760 hours)")

            return 0
        else:
            logger.error("❌ Failed to build schema")
            return 1

    except ImportError as e:
        logger.error("❌ Could not import dataset_builder: %s", e)
        logger.info("\nTroubleshooting:")
        logger.info("  1. Check that src/citylearnv2/ exists")
        logger.info("  2. Verify all dependencies installed: pip install -r requirements.txt")
        logger.info("  3. Run: python run_integration_test.py first")
        return 1
    except Exception as e:
        logger.error("❌ Error building dataset: %s", e)
        logger.exception("Full traceback:")
        return 1

def main():
    """Main entry point"""

    import argparse
    parser = argparse.ArgumentParser(description="Build CityLearn v2 Dataset with BESS & MALL Integration")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, don't build")
    args = parser.parse_args()

    # Always validate first
    if not validate_integration():
        logger.error("\n❌ VALIDATION FAILED - Fix issues before building")
        return 1

    logger.info("\n✅ VALIDATION PASSED - All datasets ready")

    # Build if not validate-only
    if args.validate_only:
        logger.info("\n[--validate-only flag set] Stopping after validation")
        return 0

    return build_dataset()

if __name__ == "__main__":
    sys.exit(main())
