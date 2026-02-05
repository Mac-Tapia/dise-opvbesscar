#!/usr/bin/env python3
"""
SCRIPT: Run BESS & Mall Demand Integration Tests
Objetivo: Verificar que dataset_builder.py está correctamente integrado con:
1. bess_hourly_dataset_2024.csv
2. demandamallhorakwh.csv
"""

from pathlib import Path
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Run all integration tests"""

    logger.info("=" * 80)
    logger.info("BESS & MALL DEMAND INTEGRATION TEST SUITE")
    logger.info("=" * 80)

    # TEST 1: Check file existence
    logger.info("\n[TEST 1] Checking dataset files exist...")
    bess_file = Path("data/oe2/bess/bess_hourly_dataset_2024.csv")
    mall_file = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")

    tests_passed = 0
    tests_total = 4

    if bess_file.exists():
        logger.info("✅ BESS file found: %s", bess_file)
        tests_passed += 1
    else:
        logger.error("❌ BESS file NOT found: %s", bess_file)

    if mall_file.exists():
        logger.info("✅ Mall demand file found: %s", mall_file)
        tests_passed += 1
    else:
        logger.error("❌ Mall demand file NOT found: %s", mall_file)

    # TEST 2: Load and validate BESS dataset
    logger.info("\n[TEST 2] Validating BESS dataset structure...")
    try:
        import pandas as pd
        bess_df = pd.read_csv(bess_file, index_col=0, parse_dates=True)

        if len(bess_df) == 8760:
            logger.info("✅ BESS dataset has correct shape: %s", bess_df.shape)
            tests_passed += 1
        else:
            logger.error("❌ BESS dataset has wrong rows: %d (expected 8760)", len(bess_df))

        if "soc_percent" in bess_df.columns:
            logger.info("✅ BESS has soc_percent column")
        else:
            logger.warning("⚠️  BESS missing soc_percent column, columns: %s", bess_df.columns.tolist())
    except Exception as e:
        logger.error("❌ Error loading BESS: %s", e)

    # TEST 3: Load and validate Mall demand dataset
    logger.info("\n[TEST 3] Validating Mall demand dataset structure...")
    try:
        # Try different separators
        mall_df = None
        for sep in [',', ';']:
            try:
                mall_df = pd.read_csv(mall_file, sep=sep)
                break
            except:
                continue

        if mall_df is not None:
            if len(mall_df) >= 8760:
                logger.info("✅ Mall dataset has correct rows: %d", len(mall_df))
                tests_passed += 1
            else:
                logger.error("❌ Mall dataset has wrong rows: %d (expected ≥8760)", len(mall_df))
        else:
            logger.error("❌ Could not load mall dataset with any separator")
    except Exception as e:
        logger.error("❌ Error loading Mall: %s", e)

    # TEST 4: Check dataset_builder integration
    logger.info("\n[TEST 4] Checking dataset_builder.py integration...")
    try:
        dataset_builder = Path("src/citylearnv2/dataset_builder/dataset_builder.py")
        content = dataset_builder.read_text()

        if "bess_hourly_2024" in content and "PRIORITY 1: NEW BESS" in content:
            logger.info("✅ dataset_builder.py has BESS hourly integration")
            if "demandamallhorakwh" in content and "PRIORITY 1: Converted to exact 8,760" in content:
                logger.info("✅ dataset_builder.py has Mall demand integration")
                tests_passed += 1
            else:
                logger.error("❌ dataset_builder.py missing Mall integration")
        else:
            logger.error("❌ dataset_builder.py missing BESS integration")
    except Exception as e:
        logger.error("❌ Error checking dataset_builder: %s", e)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY: %d/%d tests passed", tests_passed, tests_total)
    logger.info("=" * 80)

    if tests_passed == tests_total:
        logger.info("✅ ALL TESTS PASSED - Ready to build CityLearn v2 dataset!")
        return 0
    else:
        logger.error("❌ Some tests failed - Fix issues before building dataset")
        return 1

if __name__ == "__main__":
    sys.exit(main())
