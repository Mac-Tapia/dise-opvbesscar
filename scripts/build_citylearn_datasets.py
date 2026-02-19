#!/usr/bin/env python
"""
Build and save CityLearn v2 datasets from OE2 sources.

Esta script:
1. Carga todos los datasets OE2 (Solar, BESS, Chargers, Mall demand)
2. Construye dataset unificado para CityLearn v2
3. Guarda en: data/processed/citylearn/iquitos_ev_mall/
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_builder_citylearn.data_loader import (
    build_citylearn_dataset,
    save_citylearn_dataset,
    PROCESSED_CITYLEARN_DIR,
)


def main():
    """Main execution."""
    print("=" * 80)
    print("BUILD CITYLEARN v2 DATASETS FROM OE2 SOURCES")
    print("=" * 80)
    print()
    
    try:
        # Build dataset
        print("[PASO 1] Construir dataset CityLearn v2...")
        print("-" * 80)
        dataset = build_citylearn_dataset()
        print()
        
        # Save dataset
        print("[PASO 2] Guardar datasets en disco...")
        print("-" * 80)
        output_dir = save_citylearn_dataset(dataset, output_dir=PROCESSED_CITYLEARN_DIR)
        print()
        
        print("=" * 80)
        print("✅ SUCCESS - Datasets guardados en:")
        print(f"   {output_dir}")
        print("=" * 80)
        print()
        print("Archivos generados:")
        print(f"  • citylearnv2_combined_dataset.csv")
        print(f"  • solar_generation.csv")
        print(f"  • bess_timeseries.csv")
        print(f"  • chargers_timeseries.csv")
        print(f"  • mall_demand.csv")
        print(f"  • dataset_config_v7.json")
        print()
        return 0

    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ ERROR: {type(e).__name__}")
        print("=" * 80)
        print(str(e))
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
