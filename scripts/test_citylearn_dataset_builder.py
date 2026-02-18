#!/usr/bin/env python3
"""Test script for CityLearn v2 dataset builder.

Tests the complete dataset building pipeline:
1. build_citylearn_dataset() - Load and combine all OE2 data
2. save_citylearn_dataset() - Save to processed directory
3. load_citylearn_dataset() - Reload from disk
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dataset_builder_citylearn import (
    build_citylearn_dataset,
    save_citylearn_dataset,
    load_citylearn_dataset,
)


def main():
    """Test the CityLearn v2 dataset builder."""
    print("\n" + "=" * 80)
    print("🧪 TEST: CityLearn v2 Dataset Builder")
    print("=" * 80)

    try:
        # Step 1: Build dataset from OE2 sources
        print("\n[1/3] Building CityLearn v2 dataset from OE2 sources...")
        dataset = build_citylearn_dataset()

        print("\n✅ Dataset built successfully!")
        print(f"\n📊 Dataset summary:")
        print(f"   • Solar: {dataset['solar'].n_hours} hours, {dataset['solar'].mean_kw:.1f} kW avg")
        print(f"   • BESS: {dataset['bess'].capacity_kwh:.0f} kWh")
        print(f"   • Chargers: {dataset['chargers'].total_sockets} sockets")
        print(f"   • Demand: {dataset['demand'].n_hours} hours")
        print(f"   • Combined: {dataset['combined'].shape}")

        # Step 2: Save dataset to disk
        print("\n[2/3] Saving dataset to disk...")
        output_dir = save_citylearn_dataset(dataset)

        print(f"\n✅ Dataset saved to {output_dir}")

        # Step 3: Load dataset from disk
        print("\n[3/3] Loading dataset from disk...")
        loaded = load_citylearn_dataset(output_dir)

        print(f"\n✅ Dataset loaded successfully!")
        print(f"\n📊 Loaded dataset keys: {list(loaded.keys())}")
        print(f"   • Combined shape: {loaded['combined'].shape}")
        print(f"   • Solar shape: {loaded['solar'].shape}")
        print(f"   • BESS shape: {loaded['bess'].shape}")
        print(f"   • Chargers shape: {loaded['chargers'].shape}")
        print(f"   • Demand shape: {loaded['demand'].shape}")

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\n📂 Dataset saved to: data/processed/citylearn/iquitos_ev_mall/")
        print("   Files created:")
        print("   • citylearnv2_combined_dataset.csv")
        print("   • solar_generation.csv")
        print("   • bess_timeseries.csv")
        print("   • chargers_timeseries.csv")
        print("   • mall_demand.csv")
        print("   • dataset_config_v7.json")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
