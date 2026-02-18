"""
Dataset Builder - Entry Point for OE2 → OE3 Integration

This module serves as the unified interface for loading OE2 artifacts
and constructing CityLearn v2 environments.

It wraps the actual implementation in dataset_builder_citylearn.data_loader
to provide a consistent, backwards-compatible API.

Usage:
    from src.dataset_builder import (
        load_solar_data,
        load_bess_data,
        load_chargers_data,
        load_mall_demand_data,
        validate_oe2_complete,
        OE2ValidationError
    )
    
    # Load all OE2 datasets
    solar = load_solar_data()
    bess = load_bess_data()
    chargers = load_chargers_data()
    demand = load_mall_demand_data()
"""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

# Import from the actual implementation location
try:
    from src.dataset_builder_citylearn.data_loader import (
        load_solar_data,
        load_bess_data,
        load_chargers_data,
        load_mall_demand_data,
        validate_oe2_complete,
        OE2ValidationError,
        SolarData,
        BESSData,
        ChargerData,
        DemandData,
    )
except ImportError:
    # Fallback if structure changes
    try:
        from dataset_builder_citylearn.data_loader import (
            load_solar_data,
            load_bess_data,
            load_chargers_data,
            load_mall_demand_data,
            validate_oe2_complete,
            OE2ValidationError,
            SolarData,
            BESSData,
            ChargerData,
            DemandData,
        )
    except ImportError as e:
        raise ImportError(
            "Cannot import data loaders from dataset_builder_citylearn.data_loader. "
            "Ensure src/dataset_builder_citylearn/data_loader.py exists and has the required functions."
        ) from e


if TYPE_CHECKING:
    from pathlib import Path
    import pandas as pd

__all__ = [
    "load_solar_data",
    "load_bess_data",
    "load_chargers_data",
    "load_mall_demand_data",
    "validate_oe2_complete",
    "OE2ValidationError",
    "SolarData",
    "BESSData",
    "ChargerData",
    "DemandData",
]

__version__ = "5.5.0"
__author__ = "pvbesscar Team"
__description__ = "Entry point for OE2 → OE3 dataset integration"


def load_all_oe2_datasets() -> dict[str, any]:
    """
    Convenience function to load all OE2 datasets at once.
    
    Returns:
        Dictionary with keys: solar, bess, chargers, demand
        
    Raises:
        OE2ValidationError: If any dataset is missing or invalid
    """
    return {
        "solar": load_solar_data(),
        "bess": load_bess_data(),
        "chargers": load_chargers_data(),
        "demand": load_mall_demand_data(),
    }


# Test imports on module load (optional, can be disabled in production)
def _test_imports(verbose: bool = False) -> bool:
    """Test that all imports are working correctly."""
    try:
        from src.dataset_builder_citylearn.data_loader import load_solar_data
        if verbose:
            print(f"✓ Data loaders loaded from dataset_builder_citylearn.data_loader")
        return True
    except Exception as e:
        if verbose:
            print(f"✗ Failed to load data loaders: {e}")
        return False


if __name__ == "__main__":
    # Test that imports work
    print(f"\nDataset Builder v{__version__}")
    print(f"Description: {__description__}")
    print("\nTesting imports...")
    success = _test_imports(verbose=True)
    print(f"Import Status: {'✓ SUCCESS' if success else '✗ FAILED'}\n")
    
    if success:
        print("Loading all OE2 datasets...")
        datasets = load_all_oe2_datasets()
        print(f"  ✓ Solar: {len(datasets['solar'].data)} rows")
        print(f"  ✓ BESS: {datasets['bess'].capacity} kWh")
        print(f"  ✓ Chargers: {datasets['chargers'].n_chargers} units")
        print(f"  ✓ Demand: {len(datasets['demand'].data)} rows\n")

