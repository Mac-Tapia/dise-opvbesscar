# 🎯 Complete Dataset Builder v7.0 - Integration Guide

## ✅ What It Does

The **Complete Dataset Builder v7.0** ensures that **ALL columns** from every dataset are loaded before agent training:

```
📊 Dataset Loading Summary:
├── Solar (11 columns)
│   └── datetime, irradiancia_ghi, temperatura_c, velocidad_viento_ms, potencia_kw, ...
├── BESS (25 columns)
│   └── datetime, pv_generation_kwh, ev_demand_kwh, mall_demand_kwh, ...
├── Chargers (353 columns)
│   └── 38 sockets × ~9 features per socket (power, SOC, active, etc.)
└── Demand (1 column)
    └── kWh (hourly mall demand)

Total: 390 available columns for observations
```

## 🚀 How to Use

### Method 1: Direct Usage in Training Scripts

```python
# At the START of any training script (before environment creation)

from src.dataset_builder_citylearn import build_complete_datasets_for_training

# Build ALL datasets with ALL columns
datasets = build_complete_datasets_for_training()

# Extract data
solar_df = datasets['solar']                    # 8,760 rows × 11 columns
bess_df = datasets['bess']                      # 8,760 rows × 25 columns
chargers_df = datasets['chargers']              # 8,760 rows × 353 columns
demand_df = datasets['demand']                  # 8,760 rows × 1 column
metadata = datasets['metadata']                 # Column info + constants

# Access column names dynamically
solar_columns = metadata['solar_columns']
bess_columns = metadata['bess_columns']
chargers_columns = metadata['chargers_columns']
demand_columns = metadata['demand_columns']

# Get observation dimensions
obs_dims = builder.get_observation_dimensions()
print(f"Total observation dimensions: {obs_dims['total']}")
```

### Method 2: Using the Builder Class Directly

```python
from src.dataset_builder_citylearn import CompleteDatasetBuilder

# Create builder
builder = CompleteDatasetBuilder(cwd=Path.cwd())

# Load all datasets
datasets = builder.load_all()

# Access loaded dataframes
solar_df = builder._solar_df
bess_df = builder._bess_df
chargers_df = builder._chargers_df
demand_df = builder._demand_df

# Access column lists
print("Solar columns:", builder.solar_columns)
print("BESS columns:", builder.bess_columns)
print("Chargers columns:", builder.chargers_columns)
print("Demand columns:", builder.demand_columns)

# Get observation dimensions
obs_dims = builder.get_observation_dimensions()
```

## 📋 Integration with Training Scripts

### For SAC Training

```python
#!/usr/bin/env python3
"""SAC Training with Complete Dataset Builder v7.0"""

from pathlib import Path
from stable_baselines3 import SAC
from src.dataset_builder_citylearn import build_complete_datasets_for_training
from src.agents.sac import make_sac

# ============ STEP 1: Build Complete Datasets ============
print("Building complete datasets...")
datasets = build_complete_datasets_for_training()

# Extract all data
solar_df = datasets['solar']
bess_df = datasets['bess']
chargers_df = datasets['chargers']
demand_df = datasets['demand']
metadata = datasets['metadata']

print(f"\n✅ Loaded {metadata['columns_summary']['total']} columns across all datasets")

# ============ STEP 2: Create Environment (with ALL columns) ============
# Environment builder should use ALL columns from datasets
from my_environment import create_env

env = create_env(
    solar_df=solar_df,
    bess_df=bess_df,
    chargers_df=chargers_df,
    demand_df=demand_df,
    metadata=metadata
)

# ============ STEP 3: Train Agent ============
agent = make_sac(env)
agent.learn(total_timesteps=1000000)
```

### For PPO Training

```python
#!/usr/bin/env python3
"""PPO Training with Complete Dataset Builder v7.0"""

from pathlib import Path
from stable_baselines3 import PPO
from src.dataset_builder_citylearn import build_complete_datasets_for_training

# Build complete datasets FIRST
datasets = build_complete_datasets_for_training()

# Rest of training script uses all available columns...
```

### For A2C Training

```python
#!/usr/bin/env python3
"""A2C Training with Complete Dataset Builder v7.0"""

from stable_baselines3 import A2C
from src.dataset_builder_citylearn import build_complete_datasets_for_training

# Build complete datasets FIRST
datasets = build_complete_datasets_for_training()

# Rest of training script...
```

## 🔄 Dynamic Variable & Function Updates

The Complete Dataset Builder returns **metadata** that dynamically contains all available columns:

```python
datasets = build_complete_datasets_for_training()
metadata = datasets['metadata']

# Dynamically discover available features
solar_features = metadata['solar_columns']        # List of column names
bess_features = metadata['bess_columns']          # List of column names
charger_features = metadata['chargers_columns']   # List of column names (353)

# Use in loops to process all columns
for feature in solar_features:
    # Process this feature dynamically
    values = datasets['solar'][feature].values

# Constants available in metadata
constants = metadata['constants']
bess_capacity = constants['bess_capacity_kwh']  # 1,700 kWh
solar_pv = constants['solar_pv_kwp']            # 4,050 kWp
```

## ✅ Validation Guarantees

The builder validates:

1. **Row Count**: All datasets must have exactly **8,760 rows** (1 year hourly)
2. **Charger Count**: Must detect **38 sockets** across charger columns
3. **Data Types**: Numeric columns properly formatted
4. **Paths Exist**: All canonical paths verified at load time
5. **No Missing Values**: Validates completeness

```python
datasets = build_complete_datasets_for_training()

# If validation fails, raises FileNotFoundError or ValueError with clear message
# Examples:
# - FileNotFoundError: "Solar file not found: data/oe2/Generacionsolar/..."
# - ValueError: "Solar must have 8,760 rows (hourly), got 2880"
```

## 📊 Metadata Structure

```python
metadata = {
    'n_rows': 8760,
    'n_sockets': 38,
    'n_chargers': 19,
    'solar_columns': ['datetime', 'irradiancia_ghi', ...],
    'bess_columns': ['datetime', 'pv_generation_kwh', ...],
    'chargers_columns': ['datetime', 'socket_000_charger_power_kw', ...],  # 353 total
    'demand_columns': ['kWh'],
    'columns_summary': {
        'solar': 11,
        'bess': 25,
        'chargers': 353,
        'demand': 1,
        'total': 390
    },
    'constants': {
        'bess_capacity_kwh': 1700.0,
        'bess_max_power_kw': 400.0,
        'solar_pv_kwp': 4050.0,
        'mall_demand_kw': 100.0
    }
}
```

## 🎯 Key Differences from Previous Approach

| Aspect | Old (v6.0) | New (v7.0) |
|--------|-----------|-----------|
| **Columns Loaded** | Selective (only used) | **ALL** (390 columns) |
| **Consistency** | Per-script | **Shared builder class** |
| **Metadata** | Hardcoded | **Dynamically discovered** |
| **Scalability** | Limited | **Automatic col detection** |
| **Agent Integration** | Manual per agent | **One builder, all agents** |

## ✅ Status

- **v7.0 Released**: 2026-02-17
- **Datasets Tested**: All 4 primary datasets load successfully
- **Total Columns Available**: 390
- **Breaking Changes**: 0 (fully backward compatible)

---

**Next Step**: Integrate `build_complete_datasets_for_training()` as first call in SAC/PPO/A2C training scripts
