#!/usr/bin/env python3
"""
Análisis detallado por episodio de la curva de aprendizaje SAC v9.0
"""
import pandas as pd
import numpy as np

trace_df = pd.read_csv('outputs/sac_training/trace_sac.csv')

print("=" * 80)
print("SAC v9.0 - DETAILED LEARNING CURVE (Per Episode)")
print("=" * 80)
print()

# Agrupar por episodio
episode_stats = []
for ep in sorted(trace_df['episode'].unique()):
    ep_data = trace_df[trace_df['episode'] == ep]
    
    ep_stats = {
        'episode': int(ep),
        'steps': len(ep_data),
        'total_reward': ep_data['reward'].sum(),
        'mean_reward': ep_data['reward'].mean(),
        'mean_grid_import': ep_data['grid_import_kwh'].mean(),
        'mean_solar': ep_data['solar_generation_kwh'].mean(),
        'total_co2': ep_data['co2_grid_kg'].sum(),
        'mean_co2': ep_data['co2_grid_kg'].mean(),
        'mean_ev_charging': ep_data['ev_charging_kwh'].mean(),
        'mean_bess_soc': ep_data['bess_soc'].mean(),
    }
    episode_stats.append(ep_stats)

ep_df = pd.DataFrame(episode_stats)

# Mostrar tabla
print("EPISODE METRICS TABLE:")
print("-" * 80)
for _, row in ep_df.iterrows():
    print(f"\nEpisode {int(row['episode']):2d}:")
    print(f"  Steps: {int(row['steps']):5d}  |  Total Reward: {row['total_reward']:10.6f}")
    print(f"  Grid Import: {row['mean_grid_import']:7.1f} kW  |  Solar Gen: {row['mean_solar']:7.1f} kW")
    print(f"  Total CO2: {row['total_co2']:10.0f} kg  |  Mean CO2: {row['mean_co2']:7.2f} kg/h")
    print(f"  EV Charging: {row['mean_ev_charging']:6.1f} kW  |  BESS SOC: {row['mean_bess_soc']:6.1f}%")

# Análisis de tendencia
print()
print("=" * 80)
print("LEARNING TREND ANALYSIS:")
print("=" * 80)

# Reward trend
reward_improvement = ((ep_df['total_reward'].iloc[-1] - ep_df['total_reward'].iloc[0]) / 
                      abs(ep_df['total_reward'].iloc[0])) * 100 if ep_df['total_reward'].iloc[0] != 0 else float('inf')
print(f"\n✓ REWARD EVOLUTION:")
print(f"  First episode (Ep 0): {ep_df['total_reward'].iloc[0]:.6f}")
print(f"  Latest episode (Ep {int(ep_df['episode'].max())}): {ep_df['total_reward'].iloc[-1]:.6f}")
print(f"  Trend: {reward_improvement:+.1f}% (negative = better rewards for v9.0 grid penalty)")

# Grid control trend
grid_improvement = ((ep_df['mean_grid_import'].iloc[0] - ep_df['mean_grid_import'].iloc[-1]) / 
                   ep_df['mean_grid_import'].iloc[0]) * 100
print(f"\n✓ GRID IMPORT MINIMIZATION:")
print(f"  First episode (Ep 0): {ep_df['mean_grid_import'].iloc[0]:.1f} kW")
print(f"  Latest episode (Ep {int(ep_df['episode'].max())}): {ep_df['mean_grid_import'].iloc[-1]:.1f} kW")
print(f"  Improvement: {grid_improvement:+.1f}% (positive = reduction)")

# CO2 trend
co2_improvement = ((ep_df['total_co2'].iloc[0] - ep_df['total_co2'].iloc[-1]) / 
                  ep_df['total_co2'].iloc[0]) * 100
print(f"\n✓ CO2 EMISSIONS REDUCTION:")
print(f"  First episode (Ep 0): {ep_df['total_co2'].iloc[0]:.0f} kg")
print(f"  Latest episode (Ep {int(ep_df['episode'].max())}): {ep_df['total_co2'].iloc[-1]:.0f} kg")
print(f"  Improvement: {co2_improvement:+.1f}% (positive = reduction)")

# Solar utilization trend (inverse of grid import when solar available)
print(f"\n✓ OPERATIONAL METRICS:")
print(f"  Mean BESS SOC trend: {ep_df['mean_bess_soc'].iloc[0]:.1f}% → {ep_df['mean_bess_soc'].iloc[-1]:.1f}%")
print(f"  EV Charging stability: {ep_df['mean_ev_charging'].std():.2f} kW std (lower = more stable control)")

# Convergence status
last_5_rewards = ep_df['total_reward'].tail(5).values
reward_variance = np.std(last_5_rewards)
print(f"\n✓ CONVERGENCE STATUS:")
print(f"  Last 5 episode rewards: {last_5_rewards}")
print(f"  Variance (last 5): {reward_variance:.8f}")
if reward_variance < 0.001:
    print(f"  Status: ✓ CONVERGING (low variance in recent episodes)")
elif reward_variance < 0.01:
    print(f"  Status: ⚠ LEARNING (moderate variance, still improving)")
else:
    print(f"  Status: ? UNCERTAIN (high variance, may need more training)")

print()
print("=" * 80)
if grid_improvement > -5 and co2_improvement > -5:
    print("⚠️ OBSERVATION: Grid/CO2 metrics show high variance across episodes.")
    print("This may indicate unstable policy or early training phase.")
    print("Recommend 3-4 more episodes to establish clear learning trend.")
elif grid_improvement > 0 or co2_improvement > 0:
    print("✓ LEARNING DETECTED: Agent is beginning to minimize grid/CO2.")
else:
    print("✗ NO CLEAR LEARNING: Agent not yet learning to control effectively.")
    print("May need parameter adjustment or longer training.")
print("=" * 80)
