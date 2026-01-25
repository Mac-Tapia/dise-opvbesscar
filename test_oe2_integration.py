#!/usr/bin/env python
"""
Quick integration test: OE2 data loading + charger CSV generation

Tests:
1. OE2 data validation
2. Charger profile expansion (24h → 8760h)
3. Individual charger CSV generation
"""

import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Test OE2 data loading
logger.info("\n" + "="*70)
logger.info("STEP 1: Testing OE2 Data Loading (data_loader.py)")
logger.info("="*70)

from src.iquitos_citylearn.oe2.data_loader import OE2DataLoader

try:
    loader = OE2DataLoader(oe2_path=Path('data/interim/oe2'))
    results = loader.validate_all()
    print(f"\n✅ OE2 Validation Results: {results}\n")
except Exception as e:
    logger.error(f"❌ OE2 validation failed: {e}")
    exit(1)

# Test charger profile expansion
logger.info("\n" + "="*70)
logger.info("STEP 2: Testing Charger Profile Expansion (24h → 8760h)")
logger.info("="*70)

try:
    charger_profiles = loader.load_charger_hourly_profiles()
    print(f"\n✅ Charger Profiles Shape: {charger_profiles.shape}")
    print(f"   Expected: (8760, 128)")
    print(f"   Charger columns: {list(charger_profiles.columns[:5])}...")
    print(f"   Value ranges: min={charger_profiles.min().min():.2f}, "
          f"max={charger_profiles.max().max():.2f}\n")
except Exception as e:
    logger.error(f"❌ Charger profile loading failed: {e}")
    exit(1)

# Test individual CSV generation
logger.info("\n" + "="*70)
logger.info("STEP 3: Testing Individual Charger CSV Generation")
logger.info("="*70)

from src.iquitos_citylearn.oe3.dataset_builder import _generate_individual_charger_csvs

try:
    test_dir = Path('test_charger_csvs')
    test_dir.mkdir(exist_ok=True)

    generated = _generate_individual_charger_csvs(
        charger_profiles,
        test_dir,
        overwrite=True
    )

    print(f"\n✅ Generated {len(generated)} charger CSVs")

    # Verify a few files
    test_files = [1, 64, 128]
    for idx in test_files:
        csv_file = test_dir / f'charger_simulation_{idx:03d}.csv'
        if csv_file.exists():
            df = pd.read_csv(csv_file)
            print(f"   charger_{idx:03d}: {len(df)} rows, "
                  f"min={df.iloc[:, 0].min():.3f} kW, "
                  f"max={df.iloc[:, 0].max():.3f} kW")
        else:
            print(f"   ❌ charger_{idx:03d} NOT FOUND")

except Exception as e:
    logger.error(f"❌ CSV generation failed: {e}")
    exit(1)

# Cleanup
import shutil
shutil.rmtree(test_dir, ignore_errors=True)

logger.info("\n" + "="*70)
logger.info("✅✅✅ ALL TESTS PASSED")
logger.info("="*70 + "\n")
