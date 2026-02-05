#!/usr/bin/env python
"""
Validate OE3 dataset and schema integrity.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


def validate_dataset() -> bool:
    """Validate OE3 dataset completeness and integrity."""
    project_root = Path(__file__).parent
    dataset_dir = project_root / "src" / "citylearnv2" / "dataset"
    data_dir = dataset_dir / "dataset"
    schema_file = dataset_dir / "schema.json"

    print("\n" + "=" * 80)
    print("VALIDATING OE3 DATASET")
    print("=" * 80)

    # Check files exist
    print("\n[1] Checking files exist...")
    files_to_check = [
        schema_file,
        data_dir / "solar_generation.csv",
        data_dir / "charger_load.csv",
        data_dir / "mall_load.csv",
    ]

    for f in files_to_check:
        if f.exists():
            size_kb = f.stat().st_size / 1024
            print(f"    ✓ {f.name:30} ({size_kb:8.1f} KB)")
        else:
            print(f"    ✗ {f.name:30} MISSING")
            return False

    # Load and validate schema
    print("\n[2] Validating schema.json...")
    try:
        with open(schema_file) as f:
            schema = json.load(f)

        assert schema["schema"] == "V3.7", "Schema version must be V3.7"
        assert schema["duration"]["total_steps"] == 8760, "Must have 8760 timesteps"
        assert schema["duration"]["step_size_seconds"] == 3600, "Step must be 3600 seconds (1 hour)"
        assert len(schema["buildings"]) == 1, "Must have 1 building"

        building = schema["buildings"][0]
        assert building["name"] == "Building_EV_Iquitos", "Building name check"
        assert building["electrical_storage"]["capacity"] == 4520.0, "BESS capacity check"
        assert building["electrical_storage"]["max_power_output"] == 2000.0, "BESS power output check"

        # Check reward
        reward = schema["reward"]
        weights = reward["weights"]
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01, f"Reward weights must sum to 1.0, got {total_weight}"
        assert reward["carbon_intensity"]["value"] == 0.4521, "Carbon intensity check"

        print("    ✓ Schema format valid")
        print(f"    ✓ Duration: {schema['duration']['total_steps']} timesteps")
        print(f"    ✓ Buildings: {len(schema['buildings'])}")
        print(f"    ✓ Reward weights sum: {total_weight:.2f}")
        print(f"    ✓ Carbon intensity: {reward['carbon_intensity']['value']} kg CO2/kWh")

    except Exception as e:
        print(f"    ✗ Schema validation failed: {e}")
        return False

    # Load and validate CSV files
    print("\n[3] Validating CSV files...")

    try:
        # Solar
        solar = pd.read_csv(data_dir / "solar_generation.csv")
        assert len(solar) == 8760, f"Solar must have 8760 rows, got {len(solar)}"
        assert "solar_power_kw" in solar.columns, "Missing solar_power_kw column"
        assert solar["solar_power_kw"].min() >= 0, "Solar power cannot be negative"
        annual_energy = solar["solar_power_kw"].sum()

        print(f"    ✓ Solar: {len(solar)} rows")
        print(f"      - Power: {solar['solar_power_kw'].min():.1f} - {solar['solar_power_kw'].max():.1f} kW")
        print(f"      - Annual: {annual_energy:.0f} kWh")

        # Chargers
        chargers = pd.read_csv(data_dir / "charger_load.csv")
        assert len(chargers) == 8760, f"Chargers must have 8760 rows, got {len(chargers)}"
        assert chargers.shape[1] == 128, f"Must have 128 chargers, got {chargers.shape[1]}"
        assert chargers.min().min() >= 0.0, "Utilization cannot be negative"
        assert chargers.max().max() <= 1.0, "Utilization cannot exceed 1.0"

        print(f"    ✓ Chargers: {len(chargers)} rows × {chargers.shape[1]} chargers")
        print(f"      - Utilization: {chargers.min().min():.2f} - {chargers.max().max():.2f}")

        # Mall
        mall = pd.read_csv(data_dir / "mall_load.csv")
        assert len(mall) == 8760, f"Mall must have 8760 rows, got {len(mall)}"
        assert "mall_demand_kw" in mall.columns, "Missing mall_demand_kw column"
        assert (mall["mall_demand_kw"] == 100.0).all(), "Mall demand must be constant 100 kW"
        annual_mall = mall["mall_demand_kw"].sum()

        print(f"    ✓ Mall: {len(mall)} rows")
        print(f"      - Demand: {mall['mall_demand_kw'].iloc[0]:.1f} kW (constant)")
        print(f"      - Annual: {annual_mall:.0f} kWh")

    except Exception as e:
        print(f"    ✗ CSV validation failed: {e}")
        return False

    # Check controllable loads match schema
    print("\n[4] Validating schema-CSV correspondence...")
    try:
        schema_charger_count = len(schema["buildings"][0]["controllable_loads"][0]["columns"])
        actual_charger_count = chargers.shape[1]
        assert schema_charger_count == actual_charger_count, \
            f"Schema has {schema_charger_count} chargers, CSV has {actual_charger_count}"
        print(f"    ✓ Schema-CSV charger count matches: {actual_charger_count}")
    except Exception as e:
        print(f"    ✗ Schema-CSV correspondence failed: {e}")
        return False

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Location: {dataset_dir}")
    print(f"Timesteps: 8,760 (hourly, full year)")
    print(f"Solar annual: {annual_energy:,.0f} kWh")
    print(f"Chargers: 128 (112 motos 2kW + 16 mototaxis 3kW)")
    print(f"Mall: {annual_mall:,.0f} kWh (100 kW constant)")
    print(f"BESS: 4,520 kWh, 2,000 kW")
    print(f"Carbon intensity: 0.4521 kg CO2/kWh")
    print(f"\n✅ ALL VALIDATIONS PASSED - Dataset ready for OE3 training!")

    return True


if __name__ == "__main__":
    success = validate_dataset()
    sys.exit(0 if success else 1)
