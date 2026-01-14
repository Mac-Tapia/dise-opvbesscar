#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
from scripts._common import load_all

cfg, rp = load_all("configs/default.yaml")

# Simular lo que hace dataset_builder
from citylearn import data
dataset = data.CityLearnEnvMetadata.downloads("citylearn_challenge_2022_phase_all_plus_evs")
dataset_dir = Path(dataset)
print(f"Dataset dir: {dataset_dir}")

# Buscar energy_simulation.csv
energy_files = list(dataset_dir.glob("**/energy_simulation*.csv"))
print(f"Energy simulation files: {energy_files}")

if energy_files:
    energy_path = energy_files[0]
    df_energy = pd.read_csv(energy_path)
    print(f"\n energy_simulation.csv")
    print(f"  Original shape: {df_energy.shape}")
    print(f"  First rows: {df_energy.shape[0]}")
    
    n = min(len(df_energy), 8760)
    print(f"  n calculated: {n}")
    
    df_energy_truncated = df_energy.iloc[:n]
    print(f"  After truncation: {len(df_energy_truncated)} rows")
