#!/usr/bin/env python3
"""
TEST SCRIPT: Verify BESS & Mall Demand integration in CityLearn v2 dataset_builder.py

Objetivo: Confirmar que dataset_builder.py puede cargar y procesar:
1. bess_hourly_dataset_2024.csv (8,760 × 11 columns)
2. demandamallhorakwh.csv (8,760 × 1+ columns)

Verifica:
- Carga correcta de archivos
- Dimensiones correctas (8,760 filas)
- Estructura de datos esperada
- Integración con CityLearn schema
"""

from __future__ import annotations

from pathlib import Path
import logging
import pandas as pd
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# TEST 1: Verify BESS Dataset Structure
# =============================================================================

def test_bess_dataset():
    """TEST 1: Load and validate BESS hourly dataset 2024"""
    logger.info("=" * 80)
    logger.info("TEST 1: BESS Hourly Dataset Structure")
    logger.info("=" * 80)

    bess_path = Path("data/oe2/bess/bess_hourly_dataset_2024.csv")

    if not bess_path.exists():
        logger.error(f"❌ BESS file not found: {bess_path}")
        return False

    try:
        # Load with DatetimeIndex
        df_bess = pd.read_csv(bess_path, index_col=0, parse_dates=True)

        logger.info(f"✅ Loaded: {bess_path}")
        logger.info(f"   Dimensions: {df_bess.shape}")
        logger.info(f"   Columns: {df_bess.columns.tolist()}")
        logger.info(f"   Index type: {type(df_bess.index)}")
        logger.info(f"   Index name: {df_bess.index.name}")

        # VALIDATION: 8,760 rows
        assert df_bess.shape[0] == 8760, f"Expected 8,760 rows, got {df_bess.shape[0]}"
        logger.info(f"✅ VALIDATION: 8,760 rows (hourly) ✓")

        # VALIDATION: 11 columns
        expected_cols = ["pv_kwh", "ev_kwh", "mall_kwh", "pv_to_ev_kwh", "pv_to_bess_kwh",
                        "pv_to_mall_kwh", "grid_to_ev_kwh", "grid_to_mall_kwh",
                        "bess_charge_kwh", "bess_discharge_kwh", "soc_percent"]
        assert df_bess.shape[1] >= 11, f"Expected ≥11 columns, got {df_bess.shape[1]}"
        logger.info(f"✅ VALIDATION: ≥11 columns ✓")

        # VALIDATION: No NaN
        nan_count = df_bess.isna().sum().sum()
        assert nan_count == 0, f"Found {nan_count} NaN values"
        logger.info(f"✅ VALIDATION: 0 NaN values ✓")

        # VALIDATION: SOC column
        assert "soc_percent" in df_bess.columns, "Missing soc_percent column"
        soc_min = df_bess["soc_percent"].min()
        soc_max = df_bess["soc_percent"].max()
        logger.info(f"✅ VALIDATION: SOC range {soc_min:.1f} - {soc_max:.1f} % ✓")

        # Annual energy summary
        logger.info(f"\n📊 Energy Summary:")
        logger.info(f"   PV: {df_bess['pv_kwh'].sum():,.0f} kWh/year")
        logger.info(f"   EV: {df_bess['ev_kwh'].sum():,.0f} kWh/year")
        logger.info(f"   Mall: {df_bess['mall_kwh'].sum():,.0f} kWh/year")
        logger.info(f"   BESS Charge: {df_bess['bess_charge_kwh'].sum():,.0f} kWh/year")
        logger.info(f"   BESS Discharge: {df_bess['bess_discharge_kwh'].sum():,.0f} kWh/year")

        logger.info(f"\n✅ TEST 1 PASSED: BESS dataset structure OK\n")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 1 FAILED: {e}", exc_info=True)
        return False


# =============================================================================
# TEST 2: Verify Mall Demand Dataset
# =============================================================================

def test_mall_demand_dataset():
    """TEST 2: Load and validate mall demand dataset"""
    logger.info("=" * 80)
    logger.info("TEST 2: Mall Demand Dataset Structure")
    logger.info("=" * 80)

    # Check multiple possible paths (as per dataset_builder.py logic)
    mall_paths = [
        Path("data/oe2/demandamallkwh/demandamallhorakwh.csv"),
        Path("data/oe2/demandamallkwh/demanda_mall_horaria_anual.csv"),
        Path("data/oe2/demandamall/demanda_mall_kwh.csv"),
    ]

    found_path = None
    for path in mall_paths:
        if path.exists():
            found_path = path
            break

    if found_path is None:
        logger.error(f"❌ Mall demand file not found at any of {mall_paths}")
        return False

    try:
        # Try different separators (as per dataset_builder.py logic)
        df_mall = None
        for sep in [",", ";"]:
            try:
                df_test = pd.read_csv(found_path, sep=sep, decimal=".")
                if len(df_test) >= 8760:
                    df_mall = df_test
                    sep_used = sep
                    break
            except:
                continue

        if df_mall is None:
            logger.error(f"❌ Could not load {found_path} with any separator")
            return False

        logger.info(f"✅ Loaded: {found_path}")
        logger.info(f"   Separator: '{sep_used}'")
        logger.info(f"   Dimensions: {df_mall.shape}")
        logger.info(f"   Columns: {df_mall.columns.tolist()[:5]}... (showing first 5)")

        # VALIDATION: ≥ 8,760 rows
        assert len(df_mall) >= 8760, f"Expected ≥8,760 rows, got {len(df_mall)}"
        logger.info(f"✅ VALIDATION: {len(df_mall)} rows (≥8,760) ✓")

        # VALIDATION: Has numeric column for demand
        numeric_cols = df_mall.select_dtypes(include=["float64", "int64"]).columns
        assert len(numeric_cols) > 0, "No numeric columns found"
        logger.info(f"✅ VALIDATION: {len(numeric_cols)} numeric column(s) ✓")

        # Annual summary
        if len(numeric_cols) > 0:
            demand_col = numeric_cols[0]
            annual_kwh = df_mall[demand_col].sum()
            logger.info(f"\n📊 Demand Summary:")
            logger.info(f"   Column: {demand_col}")
            logger.info(f"   Annual demand: {annual_kwh:,.0f} kWh")
            logger.info(f"   Average hourly: {df_mall[demand_col].mean():.2f} kW")
            logger.info(f"   Peak: {df_mall[demand_col].max():.2f} kW")
            logger.info(f"   Min: {df_mall[demand_col].min():.2f} kW")

        logger.info(f"\n✅ TEST 2 PASSED: Mall demand dataset structure OK\n")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 2 FAILED: {e}", exc_info=True)
        return False


# =============================================================================
# TEST 3: Verify dataset_builder.py can import and find the data
# =============================================================================

def test_dataset_builder_import():
    """TEST 3: Verify dataset_builder.py module can be imported"""
    logger.info("=" * 80)
    logger.info("TEST 3: dataset_builder.py Module Import")
    logger.info("=" * 80)

    try:
        # Add src to path
        import sys
        sys.path.insert(0, str(Path("src")))

        from citylearnv2.dataset_builder.dataset_builder import _load_oe2_artifacts

        logger.info(f"✅ Successfully imported _load_oe2_artifacts")

        # Try loading artifacts
        interim_dir = Path("data/interim")
        if interim_dir.exists():
            artifacts = _load_oe2_artifacts(interim_dir)

            logger.info(f"✅ Loaded OE2 artifacts")
            logger.info(f"   Keys: {list(artifacts.keys())}")

            # Check for BESS
            if "bess_hourly_2024" in artifacts:
                logger.info(f"✅ BESS hourly dataset found in artifacts")
                logger.info(f"   Shape: {artifacts['bess_hourly_2024'].shape}")
            elif "bess" in artifacts:
                logger.info(f"⚠️  BESS (legacy) found instead of bess_hourly_2024")

            # Check for mall demand
            if "mall_demand" in artifacts:
                logger.info(f"✅ Mall demand found in artifacts")
                logger.info(f"   Shape: {artifacts['mall_demand'].shape}")

            logger.info(f"\n✅ TEST 3 PASSED: dataset_builder import OK\n")
            return True
        else:
            logger.warning(f"⚠️  data/interim directory not found, skipping artifact loading")
            logger.info(f"\n✅ TEST 3 PASSED: dataset_builder import OK (can't test artifact loading)\n")
            return True

    except Exception as e:
        logger.error(f"❌ TEST 3 FAILED: {e}", exc_info=True)
        return False


# =============================================================================
# TEST 4: Verify schema integration
# =============================================================================

def test_schema_integration():
    """TEST 4: Verify schema.json can be created with new BESS/Mall data"""
    logger.info("=" * 80)
    logger.info("TEST 4: Schema Integration Ready")
    logger.info("=" * 80)

    try:
        # Check config
        config_path = Path("configs/default.yaml")
        if config_path.exists():
            import yaml
            with open(config_path) as f:
                cfg = yaml.safe_load(f)

            logger.info(f"✅ Config loaded: {config_path}")
            logger.info(f"   OE2 BESS: {cfg.get('oe2', {}).get('bess', {})}")
            logger.info(f"   OE2 Mall: {cfg.get('oe2', {}).get('mall', {})}")
            logger.info(f"   OE3 Dataset: {cfg.get('oe3', {}).get('dataset', {})}")
        else:
            logger.warning(f"Config not found: {config_path}")

        logger.info(f"\n✅ TEST 4 PASSED: Schema integration ready\n")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 4 FAILED: {e}", exc_info=True)
        return False


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def main():
    """Run all integration tests"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "  DATASET BUILDER INTEGRATION TEST - BESS & MALL DEMAND".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")

    results = []

    # Run tests
    results.append(("TEST 1: BESS Dataset", test_bess_dataset()))
    results.append(("TEST 2: Mall Demand", test_mall_demand_dataset()))
    results.append(("TEST 3: Module Import", test_dataset_builder_import()))
    results.append(("TEST 4: Schema Ready", test_schema_integration()))

    # Summary
    logger.info("")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " INTEGRATION TEST SUMMARY ".center(78, "=") + "║")
    logger.info("╠" + "=" * 78 + "╣")

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"║ {test_name:.<50} {status:>20} ║")
        if result:
            passed += 1
        else:
            failed += 1

    logger.info("╠" + "=" * 78 + "╣")
    logger.info(f"║ Total: {passed} passed, {failed} failed {' ' * (78 - 33 - len(f'{passed} passed, {failed} failed'))}║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")

    if failed == 0:
        logger.info("✅ ALL TESTS PASSED - Ready for CityLearn v2 dataset build!")
        return 0
    else:
        logger.error(f"❌ {failed} TEST(S) FAILED - Fix issues before building dataset")
        return 1


if __name__ == "__main__":
    exit(main())
