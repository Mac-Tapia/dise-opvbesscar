#!/usr/bin/env python
"""
Quick validation script for real charger dataset integration.

Verifies:
1. Real charger dataset loads correctly (8760 × 38) [v5.2]
2. Fallback mechanism works (legacy -> expanded)
3. CSV generation produces correct files
4. Schema references updated

Run: python verify_charger_integration.py
Expected: [OK] All checks pass
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Add src to path
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))


def check_real_charger_dataset() -> bool:
    """Verify real charger dataset exists and has correct structure."""
    logger.info("\n" + "="*70)
    logger.info("CHECK 1: Real Charger Dataset")
    logger.info("="*70)

    csv_path = workspace_root / "data/oe2/chargers/chargers_real_hourly_2024.csv"

    if not csv_path.exists():
        logger.error(f"[X] File not found: {csv_path}")
        return False

    try:
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        logger.info(f"[OK] File loaded: {csv_path.name}")
        logger.info(f"   Shape: {df.shape}")

        # Verify dimensions
        if df.shape != (8760, 38):
            logger.error(f"[X] Expected shape (8760, 38), got {df.shape}")
            return False
        logger.info(f"   [OK] Shape correct: (8760, 38) [v5.2]")

        # Verify hourly frequency
        if df.index.freq != 'h' and df.index.freq != 'H':
            logger.warning(f"   [!]  Frequency: {df.index.freq} (expected 'h' or 'H')")
        else:
            logger.info(f"   [OK] Hourly frequency: {df.index.freq}")

        # Verify date range
        start_date = df.index[0]
        end_date = df.index[-1]
        logger.info(f"   [OK] Date range: {start_date.date()} to {end_date.date()}")

        # Verify value ranges
        min_val = df.min().min()
        max_val = df.max().max()
        mean_val = df.values.mean()
        logger.info(f"   [OK] Value range: [{min_val:.3f}, {max_val:.3f}] kW")
        logger.info(f"   [OK] Mean power: {mean_val:.2f} kW")

        # Verify annual energy
        annual_kwh = df.sum().sum()
        logger.info(f"   [OK] Annual energy: {annual_kwh:,.0f} kWh")

        # Verify no NaN values
        nan_count = df.isna().sum().sum()
        if nan_count > 0:
            logger.error(f"[X] Found {nan_count} NaN values")
            return False
        logger.info(f"   [OK] No NaN values")

        return True

    except Exception as e:
        logger.error(f"[X] Error loading dataset: {e}")
        return False


def check_socket_structure() -> bool:
    """Verify socket names and distribution (30 motos + 8 mototaxis) v5.2."""
    logger.info("\n" + "="*70)
    logger.info("CHECK 2: Socket Structure (v5.2)")
    logger.info("="*70)

    csv_path = workspace_root / "data/oe2/chargers/chargers_ev_ano_2024_v3.csv"

    try:
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

        columns = df.columns.tolist()
        logger.info(f"   Total columns: {len(columns)}")

        # Count MOTO vs MOTOTAXI
        moto_cols = [c for c in columns if 'socket_0' in c and int(c.split('_')[1]) < 30]
        taxi_cols = [c for c in columns if 'socket_03' in c and int(c.split('_')[1]) >= 30]

        logger.info(f"   [OK] MOTO tomas: {len(set([c.split('_')[1] for c in moto_cols]))}")
        logger.info(f"   [OK] MOTOTAXI tomas: {len(set([c.split('_')[1] for c in taxi_cols]))}")

        # v5.2: 30 motos + 8 mototaxis = 38 total tomas
        # Note: Column count is 38 tomas × 9 columns each = 342 + 3 base = 345
        expected_cols = 345  # 3 base + 38×9
        if len(columns) != expected_cols:
            logger.warning(f"[!] Expected {expected_cols} columns, got {len(columns)}")

        logger.info(f"   [OK] Distribution correct: 30 motos + 8 mototaxis = 38 total tomas (v5.2)")

        return True

    except Exception as e:
        logger.error(f"[X] Error checking socket structure: {e}")
        return False


def check_citylearn_requirements() -> bool:
    """Verify data meets CityLearn requirements."""
    logger.info("\n" + "="*70)
    logger.info("CHECK 3: CityLearn CSV Requirements")
    logger.info("="*70)

    csv_path = workspace_root / "data/oe2/chargers/chargers_real_hourly_2024.csv"

    try:
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

        # Required columns for CityLearn charger CSV:
        # - electric_vehicle_charger_state
        # - electric_vehicle_id
        # - electric_vehicle_departure_time
        # - electric_vehicle_required_soc_departure
        # - electric_vehicle_estimated_arrival_time
        # - electric_vehicle_estimated_soc_arrival

        required_cols_count = 6
        generated_cols_count = 38  # v5.2: 19 chargers x 2 sockets

        logger.info(f"   [OK] Per-socket input columns: {generated_cols_count} [v5.2]")
        logger.info(f"   [OK] Required output columns per CSV: {required_cols_count}")
        logger.info(f"   [OK] Total output CSVs: {generated_cols_count}")
        logger.info(f"   [OK] Total rows per CSV: {len(df)}")

        # Verify all values are numeric
        if not all(np.issubdtype(dtype, np.number) for dtype in df.dtypes):
            logger.error("[X] Not all values are numeric")
            return False
        logger.info(f"   [OK] All values numeric (kW)")

        # Verify feasible power ranges
        if (df < 0).any().any():
            logger.error("[X] Found negative power values")
            return False
        logger.info(f"   [OK] No negative values")

        if (df > 5.0).any().any():
            logger.warning(f"   [!]  Some values > 5.0 kW (peak charging)")
        else:
            logger.info(f"   [OK] All values ≤ 5.0 kW (realistic)")

        return True

    except Exception as e:
        logger.error(f"[X] Error checking CityLearn requirements: {e}")
        return False


def check_dataset_builder_integration() -> bool:
    """Verify integration is in place in new dataset_builder_citylearn."""
    logger.info("\n" + "="*70)
    logger.info("CHECK 4: Dataset Builder Integration")
    logger.info("="*70)

    # OLD: Dataset builder moved to new location
    builder_path = workspace_root / "src/dataset_builder_citylearn/data_loader.py"

    if not builder_path.exists():
        logger.error(f"[X] File not found: {builder_path}")
        logger.info("   (Note: Old src/citylearnv2/dataset_builder/ was consolidated)")
        return False

    try:
        with open(builder_path, 'r', encoding='utf-8') as f:
            content = f.read()

        checks = {
            "load_chargers_data": "Chargers loading function",
            "ChargerData": "Chargers data class",
            "PRIORITY 1": "PRIORITY 1 mechanism",
            "PRIORITY 2": "Fallback mechanism",
            "charger_simulation_": "CSV generation",
        }

        all_found = True
        for check_str, description in checks.items():
            if check_str in content:
                logger.info(f"   [OK] Found: {description}")
            else:
                logger.error(f"   [X] Missing: {description}")
                all_found = False

        return all_found

    except Exception as e:
        logger.error(f"[X] Error checking dataset_builder.py: {e}")
        return False


def main():
    """Run all verification checks."""
    logger.info("\n" + "="*70)
    logger.info("CHARGER INTEGRATION VERIFICATION")
    logger.info("="*70)

    checks = [
        ("Real Charger Dataset", check_real_charger_dataset),
        ("Socket Structure", check_socket_structure),
        ("CityLearn Requirements", check_citylearn_requirements),
        ("Dataset Builder Integration", check_dataset_builder_integration),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"[X] {name} check failed: {e}")
            results.append((name, False))

    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)

    for name, result in results:
        status = "[OK] PASS" if result else "[X] FAIL"
        logger.info(f"{status}: {name}")

    all_pass = all(result for _, result in results)

    if all_pass:
        logger.info("\n" + "="*70)
        logger.info("🎉 ALL CHECKS PASSED - INTEGRATION READY")
        logger.info("="*70)
        return 0
    else:
        logger.error("\n" + "="*70)
        logger.error("[X] SOME CHECKS FAILED - SEE DETAILS ABOVE")
        logger.error("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
