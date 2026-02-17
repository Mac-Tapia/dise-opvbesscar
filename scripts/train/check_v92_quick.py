#!/usr/bin/env python3
"""Análisis ultra-rápido de v9.2 - primeros episodios"""
import pandas as pd
import numpy as np

df = pd.read_csv('outputs/sac_training/trace_sac.csv')

# Análisis por episodio
print("="*70)
print("SAC v9.2 - CONVERGENCE CHECK (PRIMEROS EPISODIOS)")
print("="*70)

for ep in sorted(df['episode'].unique())[:5]:  # Primeros 5 episodios
    ep_data = df[df['episode'] == ep]
    mean_reward = ep_data['reward'].mean()
    total_reward = ep_data['reward'].sum()
    mean_grid = ep_data['grid_import_kwh'].mean()
    
    print(f"\nEpisode {int(ep)}:")
    print(f"  Total Reward: {total_reward:10.6f}")
    print(f"  Mean Reward:  {mean_reward:10.8f}")
    print(f"  Grid Import:  {mean_grid:7.1f} kW")
    print(f"  Reward range: [{ep_data['reward'].min():.6f}, {ep_data['reward'].max():.6f}]")

print("\n" + "="*70)
print("✓ Si Mean Reward está en [-0.0005, +0.0005], v9.2 funciona OK")
print("✓ Expected Q-values: 0-5 (range)")
print("="*70)
