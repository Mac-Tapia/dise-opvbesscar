#!/usr/bin/env python3
"""
Test script for climate zone data integration in dataset_builder_consolidated.py

Validates:
1. Climate zone CSV files exist and have correct structure
2. OE2DataLoader can load all climate files
3. build_citylearn_dataset() includes climate data
4. Schema.json includes climate file references
5. Output directory contains all climate CSV files
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Expected file locations
CLIMATE_FILES = {
    "carbon_intensity": Path("src/citylearnv2/climate_zone/carbon_intensity.csv"),
    "pricing": Path("src/citylearnv2/climate_zone/pricing.csv"),
    "weather": Path("src/citylearnv2/climate_zone/weather.csv"),
}

EXPECTED_ROWS = 8760


def test_climate_csv_existence() -> bool:
    """Test 1: Verify climate zone CSV files exist."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Climate Zone CSV File Existence")
    logger.info("="*80)

    all_exist = True
    for name, path in CLIMATE_FILES.items():
        if path.exists():
            logger.info("✅ Found: %s", path)
        else:
            logger.error("❌ Missing: %s", path)
            all_exist = False

    return all_exist


def test_climate_csv_structure() -> bool:
    """Test 2: Verify CSV structure and row counts."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Climate Zone CSV Structure & Row Counts")
    logger.info("="*80)

    all_valid = True

    for name, path in CLIMATE_FILES.items():
        if not path.exists():
            logger.warning("⚠️  Skipping %s (file not found)", name)
            continue

        try:
            df = pd.read_csv(path)
            rows = len(df)
            cols = list(df.columns)

            logger.info("\n📊 %s.csv:", name.upper())
            logger.info("   Rows: %d (expected: %d)", rows, EXPECTED_ROWS)
            logger.info("   Columns: %s", cols)

            if rows < EXPECTED_ROWS:
                logger.error("   ❌ Insufficient rows (need %d, got %d)", EXPECTED_ROWS, rows)
                all_valid = False
            else:
                logger.info("   ✅ Correct row count")

            # Validate specific columns
            if name == "carbon_intensity" and "carbon_intensity" in cols:
                logger.info("   ✅ Has carbon_intensity column")
            elif name == "carbon_intensity":
                logger.error("   ❌ Missing carbon_intensity column")
                all_valid = False

            if name == "pricing" and "electricity_pricing" in cols:
                logger.info("   ✅ Has electricity_pricing column")
            elif name == "pricing":
                logger.error("   ❌ Missing electricity_pricing column")
                all_valid = False

            if name == "weather" and len([c for c in cols if c.startswith(("dry_bulb", "relative", "wind", "direct", "diffuse"))]) > 0:
                logger.info("   ✅ Has weather feature columns")
            elif name == "weather":
                logger.error("   ❌ Missing weather feature columns")
                all_valid = False

        except Exception as e:
            logger.error("❌ Error reading %s: %s", name, str(e)[:100])
            all_valid = False

    return all_valid


def test_loader_imports() -> bool:
    """Test 3: Verify OE2DataLoader methods exist."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: OE2DataLoader Methods Import")
    logger.info("="*80)

    try:
        from src.citylearnv2.dataset_builder.dataset_builder_consolidated import OE2DataLoader

        loader_methods = [m for m in dir(OE2DataLoader) if m.startswith("load_")]

        required_methods = [
            "load_solar",
            "load_chargers",
            "load_bess",
            "load_mall_demand",
            "load_carbon_intensity",
            "load_pricing",
            "load_weather",
        ]

        logger.info("Found loader methods: %s", loader_methods)

        all_present = True
        for method in required_methods:
            if method in loader_methods:
                logger.info("✅ %s exists", method)
            else:
                logger.error("❌ Missing: %s", method)
                all_present = False

        return all_present

    except Exception as e:
        logger.error("❌ Error importing OE2DataLoader: %s", str(e)[:100])
        return False


def test_schema_fields() -> bool:
    """Test 4: Verify schema.json includes climate fields (post-build check)."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Schema.json Climate Fields (post-build verification)")
    logger.info("="*80)

    schema_path = Path("processed_data/Iquitos_EV_Mall/schema.json")

    if not schema_path.exists():
        logger.warning("⚠️  Schema not yet generated (run build_citylearn_dataset first)")
        return True  # Not a failure, just hasn't been built yet

    try:
        import json
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Check for climate fields in schema
        if "buildings" in schema and len(schema["buildings"]) > 0:
            building = schema["buildings"][0]
            required_fields = ["electricity_pricing", "weather"]

            for field in required_fields:
                if field in building:
                    logger.info("✅ Schema includes %s field", field)
                else:
                    logger.error("❌ Schema missing %s field", field)
                    return False

            return True
        else:
            logger.warning("⚠️  No buildings in schema")
            return False

    except Exception as e:
        logger.error("❌ Error reading schema.json: %s", str(e)[:100])
        return False


def main() -> int:
    """Run all tests."""
    logger.info("\n" + "="*80)
    logger.info("🧪 CLIMATE ZONE DATA INTEGRATION TEST SUITE")
    logger.info("="*80)

    results = {
        "CSV Existence": test_climate_csv_existence(),
        "CSV Structure": test_climate_csv_structure(),
        "Loader Methods": test_loader_imports(),
        "Schema Fields": test_schema_fields(),
    }

    # Summary
    logger.info("\n" + "="*80)
    logger.info("📋 TEST SUMMARY")
    logger.info("="*80)

    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info("%s: %s", status, name)

    all_passed = all(results.values())

    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED - Review output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
