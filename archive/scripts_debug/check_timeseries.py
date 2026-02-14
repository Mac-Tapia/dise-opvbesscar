#!/usr/bin/env python3
import pandas as pd

print("Checking SAC timeseries:")
df_sac = pd.read_csv('outputs/sac_training/timeseries_sac.csv')
print(f"Shape: {df_sac.shape}")
print(f"ev_charging_kw mean: {df_sac['ev_charging_kw'].mean():.2f}")
print(f"ev_charging_kw max: {df_sac['ev_charging_kw'].max():.2f}")

print("\n\nChecking A2C timeseries:")
df_a2c = pd.read_csv('outputs/a2c_training/timeseries_a2c.csv')
print(f"Shape: {df_a2c.shape}")
print(f"ev_charging_kw mean: {df_a2c['ev_charging_kw'].mean():.2f}")
print(f"ev_charging_kw max: {df_a2c['ev_charging_kw'].max():.2f}")

print("\n\nChecking PPO timeseries:")
if pd.io.common.file_exists('outputs/ppo_training/timeseries_ppo.csv'):
    df_ppo = pd.read_csv('outputs/ppo_training/timeseries_ppo.csv')
    print(f"Columns: {df_ppo.columns.tolist()}")
    print(f"Shape: {df_ppo.shape}")
else:
    print("PPO timeseries not found")
