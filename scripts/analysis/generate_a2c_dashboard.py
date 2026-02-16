#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate complete A2C Dashboard from training data.
Shows episode rewards, loss, value function, and other metrics.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

sns.set_style("whitegrid")
plt.rcParams['font.size'] = 10

# Paths
A2C_DIR = Path('outputs/a2c_training')
RESULT_FILE = A2C_DIR / 'result_a2c.json'
OUTPUT_FILE = A2C_DIR / 'a2c_dashboard.png'

print("=" * 70)
print("🟢 A2C TRAINING DASHBOARD GENERATOR")
print("=" * 70)

# Load results
print("\n📥 Loading A2C training results...")
try:
    with open(RESULT_FILE, 'r') as f:
        result = json.load(f)
    print(f"   [OK] Loaded A2C results")
except Exception as e:
    print(f"[X] Error loading results: {e}")
    exit(1)

# Extract data from different possible formats
print("\n[GRAPH] Extracting training metrics...")

# Check for training_evolution structure (A2C format)
if 'training_evolution' in result:
    training_data = result['training_evolution']
    episodes = len(training_data.get('episode_rewards', []))
    
    if episodes > 0:
        episode_nums = np.arange(1, episodes + 1)
        
        # Extract metrics with fallback to empty arrays
        episode_rewards = np.array(training_data.get('episode_rewards', []))
        episode_policy_loss = np.array(training_data.get('episode_policy_loss', []))
        episode_value_loss = np.array(training_data.get('episode_value_loss', []))
        episode_entropy = np.array(training_data.get('episode_entropy', []))
        episode_co2_grid = np.array(training_data.get('episode_co2_grid', []))
        episode_co2_avoided_direct = np.array(training_data.get('episode_co2_avoided_direct', []))
        episode_co2_avoided_indirect = np.array(training_data.get('episode_co2_avoided_indirect', []))
        
        print(f"   [OK] Extracted {episodes} episodes from training_evolution")
        
    else:
        print("   [!]  No episodes found in training_evolution")
        episodes = 0
else:
    print("   [!]  No training_evolution structure found")
    episodes = 0

if episodes == 0:
    print("[X] No training data available!")
    exit(1)

# Smoothing function
def smooth(data, window=3):
    if len(data) < window:
        return data
    s = pd.Series(data)
    return s.rolling(window=window, center=True, min_periods=1).mean().values

# Generate dashboard
print("\n[CHART] Generating 3x3 Training Dashboard for A2C...")

fig, axes = plt.subplots(3, 3, figsize=(18, 12))
fig.patch.set_facecolor('white')

colors = {
    'reward': '#2ca02c',
    'policy_loss': '#d62728',
    'value_loss': '#1f77b4',
    'entropy': '#ff7f0e',
    'co2_grid': '#e377c2',
    'co2_direct': '#7f7f7f',
    'co2_indirect': '#bcbd22'
}

# Row 1: Core Training Metrics
# 1. Episode Rewards
ax = axes[0, 0]
if len(episode_rewards) > 0:
    rewards_smooth = smooth(episode_rewards)
    ax.plot(episode_nums, episode_rewards, 'o-', color=colors['reward'], linewidth=2, markersize=6, alpha=0.6, label='Raw')
    ax.plot(episode_nums, rewards_smooth, 'o-', color=colors['reward'], linewidth=3, markersize=8, label='Smoothed')
    ax.set_title('Episode Rewards', fontsize=12, fontweight='bold')
    ax.set_xlabel('Episode')
    ax.set_ylabel('Total Reward')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    if len(episode_rewards) > 1:
        improve = (episode_rewards[-1] - episode_rewards[0]) / (abs(episode_rewards[0]) + 1e-6) * 100
        color = 'green' if improve > 0 else 'red'
        ax.annotate(f'{"^" if improve > 0 else "v"} {abs(improve):.1f}%',
                   xy=(0.98, 0.05), xycoords='axes fraction',
                   fontsize=10, color=color, ha='right', fontweight='bold')
else:
    ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
    ax.set_title('Episode Rewards', fontsize=12, fontweight='bold')

# 2. Policy Loss
ax = axes[0, 1]
if len(episode_policy_loss) > 0:
    ploss_smooth = smooth(episode_policy_loss)
    ax.plot(episode_nums, episode_policy_loss, 'o-', color=colors['policy_loss'], linewidth=2, markersize=6, alpha=0.6, label='Raw')
    ax.plot(episode_nums, ploss_smooth, 'o-', color=colors['policy_loss'], linewidth=3, markersize=8, label='Smoothed')
    ax.set_title('Policy Loss (L_actor)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Episode')
    ax.set_ylabel('Loss')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    if len(episode_policy_loss) > 1:
        improve = (episode_policy_loss[0] - episode_policy_loss[-1]) / (episode_policy_loss[0] + 1e-6) * 100
        color = 'green' if improve > 0 else 'red'
        ax.annotate(f'{"v" if improve > 0 else "^"} {abs(improve):.1f}%',
                   xy=(0.98, 0.05), xycoords='axes fraction',
                   fontsize=10, color=color, ha='right', fontweight='bold')
else:
    ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
    ax.set_title('Policy Loss', fontsize=12, fontweight='bold')

# 3. Value Loss
ax = axes[0, 2]
if len(episode_value_loss) > 0:
    vloss_smooth = smooth(episode_value_loss)
    ax.plot(episode_nums, episode_value_loss, 'o-', color=colors['value_loss'], linewidth=2, markersize=6, alpha=0.6, label='Raw')
    ax.plot(episode_nums, vloss_smooth, 'o-', color=colors['value_loss'], linewidth=3, markersize=8, label='Smoothed')
    ax.set_title('Value Loss (L_critic)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Episode')
    ax.set_ylabel('Loss')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    if len(episode_value_loss) > 1:
        improve = (episode_value_loss[0] - episode_value_loss[-1]) / (episode_value_loss[0] + 1e-6) * 100
        color = 'green' if improve > 0 else 'red'
        ax.annotate(f'{"v" if improve > 0 else "^"} {abs(improve):.1f}%',
                   xy=(0.98, 0.05), xycoords='axes fraction',
                   fontsize=10, color=color, ha='right', fontweight='bold')
else:
    ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
    ax.set_title('Value Loss', fontsize=12, fontweight='bold')

# Row 2: Entropy & CO2 Grid
# 4. Entropy
ax = axes[1, 0]
if len(episode_entropy) > 0:
    entropy_smooth = smooth(episode_entropy)
    ax.plot(episode_nums, episode_entropy, 'o-', color=colors['entropy'], linewidth=2, markersize=6, alpha=0.6, label='Raw')
    ax.plot(episode_nums, entropy_smooth, 'o-', color=colors['entropy'], linewidth=3, markersize=8, label='Smoothed')
    ax.set_title('Policy Entropy (Exploration)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Episode')
    ax.set_ylabel('Entropy')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    if len(episode_entropy) > 1:
        improve = (episode_entropy[0] - episode_entropy[-1]) / (episode_entropy[0] + 1e-6) * 100
        color = 'green' if improve > 0 else 'red'
        ax.annotate(f'{"v" if improve > 0 else "^"} {abs(improve):.1f}%',
                   xy=(0.98, 0.05), xycoords='axes fraction',
                   fontsize=10, color=color, ha='right', fontweight='bold')
else:
    ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
    ax.set_title('Policy Entropy', fontsize=12, fontweight='bold')

# 5. CO2 Grid Import
ax = axes[1, 1]
if len(episode_co2_grid) > 0:
    co2_grid_smooth = smooth(episode_co2_grid)
    ax.plot(episode_nums, episode_co2_grid, 'o-', color=colors['co2_grid'], linewidth=2, markersize=6, alpha=0.6, label='Raw')
    ax.plot(episode_nums, co2_grid_smooth, 'o-', color=colors['co2_grid'], linewidth=3, markersize=8, label='Smoothed')
    ax.set_title('CO2 from Grid Import', fontsize=12, fontweight='bold')
    ax.set_xlabel('Episode')
    ax.set_ylabel('kg CO2')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    if len(episode_co2_grid) > 1:
        improve = (episode_co2_grid[0] - episode_co2_grid[-1]) / (episode_co2_grid[0] + 1e-6) * 100
        color = 'green' if improve > 0 else 'red'
        ax.annotate(f'{"v" if improve > 0 else "^"} {abs(improve):.1f}%',
                   xy=(0.98, 0.05), xycoords='axes fraction',
                   fontsize=10, color=color, ha='right', fontweight='bold')
else:
    ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
    ax.set_title('CO2 Grid Import', fontsize=12, fontweight='bold')

# 6. Empty placeholder
ax = axes[1, 2]
ax.text(0.5, 0.5, 'Reserved', ha='center', va='center', transform=ax.transAxes, fontsize=12, color='gray')
ax.set_title('Reserved', fontsize=12, fontweight='bold')
ax.axis('off')

# Row 3: CO2 Reductions
# 7. Direct CO2 Reduction
ax = axes[2, 0]
if len(episode_co2_avoided_direct) > 0:
    co2_direct_smooth = smooth(episode_co2_avoided_direct)
    ax.plot(episode_nums, episode_co2_avoided_direct, 'o-', color=colors['co2_direct'], linewidth=2, markersize=6, alpha=0.6, label='Raw')
    ax.plot(episode_nums, co2_direct_smooth, 'o-', color=colors['co2_direct'], linewidth=3, markersize=8, label='Smoothed')
    ax.set_title('Direct CO2 Reduction (Solar Displacement)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Episode')
    ax.set_ylabel('kg CO2')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    if len(episode_co2_avoided_direct) > 1:
        improve = (episode_co2_avoided_direct[-1] - episode_co2_avoided_direct[0]) / (episode_co2_avoided_direct[0] + 1e-6) * 100
        color = 'green' if improve > 0 else 'red'
        ax.annotate(f'{"^" if improve > 0 else "v"} {abs(improve):.1f}%',
                   xy=(0.98, 0.05), xycoords='axes fraction',
                   fontsize=10, color=color, ha='right', fontweight='bold')
else:
    ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
    ax.set_title('CO2 Direct Reduction', fontsize=12, fontweight='bold')

# 8. Indirect CO2 Reduction
ax = axes[2, 1]
if len(episode_co2_avoided_indirect) > 0:
    co2_indirect_smooth = smooth(episode_co2_avoided_indirect)
    ax.plot(episode_nums, episode_co2_avoided_indirect, 'o-', color=colors['co2_indirect'], linewidth=2, markersize=6, alpha=0.6, label='Raw')
    ax.plot(episode_nums, co2_indirect_smooth, 'o-', color=colors['co2_indirect'], linewidth=3, markersize=8, label='Smoothed')
    ax.set_title('Indirect CO2 Reduction (Renewable EV Charging)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Episode')
    ax.set_ylabel('kg CO2')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    if len(episode_co2_avoided_indirect) > 1:
        improve = (episode_co2_avoided_indirect[-1] - episode_co2_avoided_indirect[0]) / (episode_co2_avoided_indirect[0] + 1e-6) * 100
        color = 'green' if improve > 0 else 'red'
        ax.annotate(f'{"^" if improve > 0 else "v"} {abs(improve):.1f}%',
                   xy=(0.98, 0.05), xycoords='axes fraction',
                   fontsize=10, color=color, ha='right', fontweight='bold')
else:
    ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
    ax.set_title('CO2 Indirect Reduction', fontsize=12, fontweight='bold')

# 9. Total CO2 Impact
ax = axes[2, 2]
if len(episode_co2_grid) > 0 and (len(episode_co2_avoided_direct) > 0 or len(episode_co2_avoided_indirect) > 0):
    total_co2_avoided = np.zeros(len(episode_co2_grid))
    if len(episode_co2_avoided_direct) > 0:
        total_co2_avoided += episode_co2_avoided_direct
    if len(episode_co2_avoided_indirect) > 0:
        total_co2_avoided += episode_co2_avoided_indirect
    
    net_co2 = episode_co2_grid - total_co2_avoided
    
    # Plot stacked
    ax.bar(episode_nums, episode_co2_grid, label='CO2 from Grid', color=colors['co2_grid'], alpha=0.7)
    ax.bar(episode_nums, -total_co2_avoided, label='CO2 Avoided', color='green', alpha=0.7)
    ax.axhline(y=0, color='black', linewidth=1)
    ax.set_title('Net CO2 Impact', fontsize=12, fontweight='bold')
    ax.set_xlabel('Episode')
    ax.set_ylabel('kg CO2')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax.legend(fontsize=9)
else:
    ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
    ax.set_title('Net CO2 Impact', fontsize=12, fontweight='bold')

# Overall title
title = f'CityLearn v2 - A2C Agent Training Dashboard\n{episodes} Episodes | {result.get("total_timesteps", "?")} Total Timesteps'
fig.suptitle(title, fontsize=14, fontweight='bold', y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.97])

# Save
plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
print(f"   [OK] Saved: {OUTPUT_FILE}")

plt.close(fig)

# Print summary
print("\n[GRAPH] A2C Training Summary:")
print(f"   Episodes:        {episodes}")
print(f"   Total Timesteps: {result.get('total_timesteps', 'N/A')}")

if len(episode_rewards) > 0:
    print(f"   Reward Range:    {episode_rewards.min():.2f} -> {episode_rewards.max():.2f}")

if len(episode_policy_loss) > 0:
    print(f"   Policy Loss:     {episode_policy_loss[-1]:.4f} (final)")

if len(episode_value_loss) > 0:
    print(f"   Value Loss:      {episode_value_loss[-1]:.4f} (final)")

if len(episode_co2_grid) > 0:
    improvement = (episode_co2_grid[0] - episode_co2_grid[-1]) / episode_co2_grid[0] * 100
    print(f"   CO2 Grid Reduction: {improvement:.1f}%")

print("\n" + "=" * 70)
print("[OK] A2C TRAINING DASHBOARD GENERATION COMPLETE")
print("=" * 70)
