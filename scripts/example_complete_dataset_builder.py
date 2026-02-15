#!/usr/bin/env python3
"""
Example: SAC Agent Training with Complete Dataset Builder v7.0

This example shows how to properly construct and use ALL dataset columns
before training any agent.

Key Points:
1. Load ALL datasets with ALL columns FIRST (build_complete_datasets_for_training)
2. Extract metadata with column information
3. Use dynamic column lists to build observations
4. Train agent with complete feature set
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import sys

# Add workspace root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 100)
print("🎯 SAC TRAINING WITH COMPLETE DATASET BUILDER v7.0")
print("=" * 100)

# Step 1: Build COMPLETE datasets (ALL columns)
# ============================================================================
print("\n[STEP 1] Building complete datasets with ALL columns...")

from src.dataset_builder_citylearn import build_complete_datasets_for_training

datasets = build_complete_datasets_for_training()

# Step 2: Extract and Display Metadata
# ============================================================================
print("\n[STEP 2] Extracted metadata from datasets:")

solar_df = datasets['solar']
bess_df = datasets['bess']
chargers_df = datasets['chargers']
demand_df = datasets['demand']
metadata = datasets['metadata']

print(f"\n[GRAPH] Dataset Dimensions:")
print(f"  - Solar:    {len(solar_df):>6,} rows × {len(metadata['solar_columns']):>3} columns")
print(f"  - BESS:     {len(bess_df):>6,} rows × {len(metadata['bess_columns']):>3} columns")
print(f"  - Chargers: {len(chargers_df):>6,} rows × {len(metadata['chargers_columns']):>3} columns (38 sockets)")
print(f"  - Demand:   {len(demand_df):>6,} rows × {len(metadata['demand_columns']):>3} columns")
print(f"\n  {'TOTAL':>3}: {len(solar_df):>6,} rows × {metadata['columns_summary']['total']:>3} columns")

print(f"\n🔧 OE2 Constants (from metadata):")
constants = metadata['constants']
print(f"  - BESS Capacity:  {constants['bess_capacity_kwh']} kWh")
print(f"  - BESS Max Power: {constants['bess_max_power_kw']} kW")
print(f"  - Solar PV:       {constants['solar_pv_kwp']} kWp")
print(f"  - Mall Demand:    {constants['mall_demand_kw']} kW")

# Step 3: Example - Use ALL columns dynamically
# ============================================================================
print("\n[STEP 3] Dynamic column usage example:")

print(f"\n  Solar columns ({len(metadata['solar_columns'])}):")
for i, col in enumerate(metadata['solar_columns'][:5], 1):
    print(f"    {i}. {col}")
if len(metadata['solar_columns']) > 5:
    print(f"    ... +{len(metadata['solar_columns']) - 5} more")

print(f"\n  BESS columns ({len(metadata['bess_columns'])}):")
for i, col in enumerate(metadata['bess_columns'][:5], 1):
    print(f"    {i}. {col}")
if len(metadata['bess_columns']) > 5:
    print(f"    ... +{len(metadata['bess_columns']) - 5} more")

print(f"\n  Charger columns ({len(metadata['chargers_columns'])} total):")
# Show only socket columns
socket_cols = [c for c in metadata['chargers_columns'] if 'socket_' in c][:5]
for i, col in enumerate(socket_cols, 1):
    print(f"    {i}. {col}")
if len(metadata['chargers_columns']) > 5:
    print(f"    ... +{len(metadata['chargers_columns']) - 5} more (socket features)")

# Step 4: Observation Builder would use ALL columns
# ============================================================================
print("\n[STEP 4] Building observation with ALL available columns...")

obs_dims = {
    'solar': len(metadata['solar_columns']),
    'bess': len(metadata['bess_columns']),
    'chargers': len(metadata['chargers_columns']),
    'demand': len(metadata['demand_columns']),
}
obs_dims['total'] = sum(obs_dims.values())

print(f"\n  Observation space dimensions:")
for key, val in obs_dims.items():
    print(f"    - {key:<10}: {val:>3} dimensions")

# Step 5: Example - Process ALL columns
# ============================================================================
print("\n[STEP 5] Processing ALL columns example:")

def process_all_columns(datasets: Dict[str, Any], metadata: Dict[str, Any]):
    """Example function that processes ALL columns from all datasets."""
    
    solar_features = []
    for col in metadata['solar_columns']:
        # Process each column
        values = datasets['solar'][col].values
        if col != 'datetime':
            solar_features.append({
                'name': col,
                'type': str(datasets['solar'][col].dtype),
                'min': values.min() if values.dtype != 'object' else 'N/A',
                'max': values.max() if values.dtype != 'object' else 'N/A',
            })
    
    return solar_features

solar_features = process_all_columns(datasets, metadata)
print(f"\n  [OK] Processed {len(solar_features)} solar features")

# Step 6: Ready for Environment & Agent Training
# ============================================================================
print("\n[STEP 6] Ready for environment creation and agent training:")

print("""
  Next steps:
  1. Create CityLearn environment with complete datasets
  2. Build observation from ALL available columns
  3. Initialize agent (SAC/PPO/A2C)
  4. Train with full feature set
  
  Example:
    env = create_env_with_complete_datasets(datasets, metadata)
    agent = make_sac(env)
    agent.learn(total_timesteps=1000000)
""")

print("\n" + "=" * 100)
print("[OK] EXAMPLE COMPLETED - Ready to train agents with complete dataset builder")
print("=" * 100)

# Print summary
print(f"""

SUMMARY:
  Dataset Builder v7.0 ensures consistency across all agents by:
  [OK] Loading ALL {metadata['columns_summary']['total']} available columns
  [OK] Providing dynamic column discovery via metadata
  [OK] Validating data integrity (8,760 rows, 38 sockets)
  [OK] Sharing ONE builder class across SAC/PPO/A2C agents
  [OK] Updating variables automatically based on available columns

INTEGRATION POINTS:
  - Call build_complete_datasets_for_training() FIRST in any training script
  - Use metadata to discover available columns
  - Build observations with ALL features
  - Train agents with complete feature set
""")
