# MANDATORY DATASET LOADING FOR ALL AGENTS

## ⚠️ CRITICAL REQUIREMENT

All agents (SAC, PPO, A2C) **MUST** use `load_agent_dataset_mandatory()` to ensure:
- ✅ Datasets always loaded from `data/iquitos_ev_mall`
- ✅ All files present and validated
- ✅ Consistent data across all agents
- ✅ Early failure if datasets missing

## 🔧 HOW TO USE IN AGENTS

### Import
```python
from src.dataset_builder_citylearn.data_loader import load_agent_dataset_mandatory
```

### Usage (Replace ALL `load_datasets_from_processed()` calls)
```python
# BEFORE (OLD - DO NOT USE):
# def load_datasets_from_processed():
#     ...

# AFTER (NEW - MANDATORY):
datasets = load_agent_dataset_mandatory(agent_name="PPO")  # or "SAC" or "A2C"

# Access datasets:
solar = datasets["solar"]           # pd.DataFrame
bess = datasets["bess"]             # pd.DataFrame
chargers = datasets["chargers"]     # pd.DataFrame
demand = datasets["demand"]         # pd.DataFrame
config = datasets["config"]         # dict
```

## 📂 REQUIRED DIRECTORY STRUCTURE

Agents expect this exact structure:
```
data/
├── iquitos_ev_mall/
│   ├── citylearnv2_combined_dataset.csv   ✓ 8,760 rows × 22 cols
│   ├── solar_generation.csv               ✓ Solar timeseries
│   ├── bess_timeseries.csv                ✓ BESS data
│   ├── chargers_timeseries.csv            ✓ 38 chargers × 2 sockets
│   ├── mall_demand.csv                    ✓ Mall demand
│   ├── dataset_config_v7.json             ✓ System config
```

## ❌ IF DATASET MISSING: ERROR MESSAGE

```
❌ FATAL: Dataset not found in data/iquitos_ev_mall

REQUIRED DATASETS:
  • citylearnv2_combined_dataset.csv
  • solar_generation.csv
  • bess_timeseries.csv
  • chargers_timeseries.csv
  • mall_demand.csv

SOLUTION: Run data_loader to generate datasets:
  python -c "from src.dataset_builder_citylearn.data_loader import build_citylearn_dataset,save_citylearn_dataset; dataset = build_citylearn_dataset(); save_citylearn_dataset(dataset)"
```

## 🚀 EXAMPLE: MODIFIED TRAIN_PPO.py

```python
# OLD (BROKEN - DO NOT USE):
def load_datasets_from_processed():
    oe2_datasets = rebuild_oe2_datasets_complete()
    ...

# NEW (MANDATORY):
def load_datasets_iquitos():
    """Load datasets OBLIGATORILY from data/iquitos_ev_mall"""
    from src.dataset_builder_citylearn.data_loader import load_agent_dataset_mandatory
    
    datasets = load_agent_dataset_mandatory(agent_name="PPO")
    
    # Unpack datasets
    solar_df = datasets["solar"]
    bess_df = datasets["bess"]
    chargers_df = datasets["chargers"]
    demand_df = datasets["demand"]
    config = datasets["config"]
    
    return {
        'solar': solar_df,
        'bess': bess_df,
        'chargers': chargers_df,
        'demand': demand_df,
        'config': config,
    }

# In main():
datasets = load_datasets_iquitos()
```

## 📋 CHECKLIST

- [ ] SAC updated to use `load_agent_dataset_mandatory(agent_name="SAC")`
- [ ] PPO updated to use `load_agent_dataset_mandatory(agent_name="PPO")`
- [ ] A2C updated to use `load_agent_dataset_mandatory(agent_name="A2C")`
- [ ] All agents throw **fatal error** if `data/iquitos_ev_mall` missing
- [ ] All agents share **identical dataset** source
- [ ] No custom `load_datasets_from_processed()` fallbacks allowed

## 📞 FUNCTION SIGNATURE

```python
def load_agent_dataset_mandatory(agent_name: str = "Agent") -> Dict[str, Any]:
    """
    Load CityLearn dataset OBLIGATORILY from data/iquitos_ev_mall.
    
    Args:
        agent_name: Name of agent (for logging): "SAC", "PPO", "A2C"
    
    Returns:
        {
            "solar": pd.DataFrame (8,760 hours),
            "bess": pd.DataFrame (8,760 hours),
            "chargers": pd.DataFrame (8,760 hours × 38+ cols),
            "demand": pd.DataFrame (8,760 hours),
            "config": dict with system configuration
        }
    
    Raises:
        OE2ValidationError: If datasets missing or incomplete
    """
```

---

**Version:** v1 (2026-02-18)  
**Status:** MANDATORY ⚠️ - All agents MUST comply
