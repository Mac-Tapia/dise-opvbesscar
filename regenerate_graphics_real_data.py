#!/usr/bin/env python3
"""
Regenerate graphics using real training data from 5 episodes - SIMPLIFIED
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# Matplotlib configuration
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 13

def load_training_data():
    """Load training metrics."""
    episode_summary = pd.read_csv('analyses/oe3/agent_episode_summary.csv')
    with open('outputs/oe3/simulations/simulation_summary.json', 'r') as f:
        simulation = json.load(f)
    return episode_summary, simulation

def plot_training_metrics(episode_summary, simulation):
    """Plot training metrics from real 5-episode data."""
    agents = ['SAC', 'PPO', 'A2C']
    colors = {'SAC': '#27ae60', 'PPO': '#3498db', 'A2C': '#f39c12', 'Uncontrolled': '#e74c3c'}
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    
    # Plot 1: Steps
    ax = axes[0, 0]
    steps_data = [episode_summary[episode_summary['agent'] == a]['steps'].values[0] for a in agents]
    bars = ax.bar(agents, steps_data, color=[colors[a] for a in agents], edgecolor='black', linewidth=1.5, width=0.6)
    for bar, val in zip(bars, steps_data):
        ax.text(bar.get_x() + bar.get_width()/2, val, f'{val:,}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    ax.set_ylabel('Timesteps', fontweight='bold')
    ax.set_title('Training Steps (5 Episodes)', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    # Plot 2: Environment Reward
    ax = axes[0, 1]
    env_rewards = [episode_summary[episode_summary['agent'] == a]['reward_env_mean'].values[0] for a in agents]
    bars = ax.bar(agents, env_rewards, color=[colors[a] for a in agents], edgecolor='black', linewidth=1.5, width=0.6)
    for bar, val in zip(bars, env_rewards):
        ax.text(bar.get_x() + bar.get_width()/2, val, f'{val:.3f}', ha='center', va='bottom' if val > 0 else 'top', fontweight='bold', fontsize=10)
    ax.set_ylabel('Mean Reward', fontweight='bold')
    ax.set_title('Environment Reward', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    
    # Plot 3: Total Reward
    ax = axes[1, 0]
    total_rewards = [episode_summary[episode_summary['agent'] == a]['reward_total_mean'].values[0] for a in agents]
    bars = ax.bar(agents, total_rewards, color=[colors[a] for a in agents], edgecolor='black', linewidth=1.5, width=0.6)
    for bar, val in zip(bars, total_rewards):
        ax.text(bar.get_x() + bar.get_width()/2, val, f'{val:.3f}', ha='center', va='bottom' if val > 0 else 'top', fontweight='bold', fontsize=10)
    ax.set_ylabel('Mean Reward', fontweight='bold')
    ax.set_title('Total Multi-Objective Reward', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    
    # Plot 4: Penalty
    ax = axes[1, 1]
    penalties = [episode_summary[episode_summary['agent'] == a]['penalty_total_mean'].values[0] for a in agents]
    bars = ax.bar(agents, penalties, color=[colors[a] for a in agents], edgecolor='black', linewidth=1.5, width=0.6, alpha=0.7)
    for bar, val in zip(bars, penalties):
        ax.text(bar.get_x() + bar.get_width()/2, val, f'{val:.3f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    ax.set_ylabel('Mean Penalty', fontweight='bold')
    ax.set_title('Total Penalty (Lower is Better)', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    plt.suptitle('Training Metrics: 5 Episodes Real Data', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('outputs/oe3/graphics/training_metrics_real.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: training_metrics_real.png")
    plt.close()

def plot_simulation_results(simulation):
    """Plot simulation results with CO2 and energy metrics."""
    agents = ['SAC', 'PPO', 'A2C']
    colors = {'SAC': '#27ae60', 'PPO': '#3498db', 'A2C': '#f39c12'}
    baseline_co2 = simulation['grid_only_result']['carbon_kg'] / 1e6
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    
    # Plot 1: CO2 Emissions
    ax = axes[0, 0]
    co2_values = [simulation['pv_bess_results'][a]['carbon_kg']/1e6 for a in agents]
    ax.axhline(y=baseline_co2, color='red', linestyle='--', linewidth=2.5, label=f'Baseline: {baseline_co2:.2f}M')
    bars = ax.bar(agents, co2_values, color=[colors[a] for a in agents], edgecolor='black', linewidth=1.5, width=0.6)
    for bar, val in zip(bars, co2_values):
        reduction = ((baseline_co2 - val) / baseline_co2) * 100
        ax.text(bar.get_x() + bar.get_width()/2, val, f'{val:.2f}M\n(-{reduction:.1f}%)', ha='center', va='bottom', fontweight='bold', fontsize=9)
    ax.set_ylabel('CO₂ Emissions (M kg)', fontweight='bold')
    ax.set_title('CO₂ Emissions vs Baseline', fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    
    # Plot 2: Grid Import
    ax = axes[0, 1]
    grid_import = [simulation['pv_bess_results'][a]['grid_import_kwh']/1e6 for a in agents]
    baseline_import = simulation['pv_bess_uncontrolled']['grid_import_kwh'] / 1e6
    ax.axhline(y=baseline_import, color='red', linestyle='--', linewidth=2.5, label=f'Baseline: {baseline_import:.1f}M')
    bars = ax.bar(agents, grid_import, color=[colors[a] for a in agents], edgecolor='black', linewidth=1.5, width=0.6)
    for bar, val in zip(bars, grid_import):
        reduction = ((baseline_import - val) / baseline_import) * 100
        ax.text(bar.get_x() + bar.get_width()/2, val, f'{val:.1f}M\n(-{reduction:.1f}%)', ha='center', va='bottom', fontweight='bold', fontsize=9)
    ax.set_ylabel('Grid Import (MWh)', fontweight='bold')
    ax.set_title('Grid Import Reduction', fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    
    # Plot 3: PV Generation
    ax = axes[1, 0]
    pv_gen = [simulation['pv_bess_results'][a]['pv_generation_kwh']/1e6 for a in agents]
    bars = ax.bar(agents, pv_gen, color=[colors[a] for a in agents], edgecolor='black', linewidth=1.5, width=0.6)
    for bar, val in zip(bars, pv_gen):
        ax.text(bar.get_x() + bar.get_width()/2, val, f'{val:.2f}M', ha='center', va='bottom', fontweight='bold', fontsize=10)
    ax.set_ylabel('PV Generation (MWh)', fontweight='bold')
    ax.set_title('Solar Panel Output', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    # Plot 4: EV Charging
    ax = axes[1, 1]
    ev_charge = [simulation['pv_bess_results'][a]['ev_charging_kwh']/1e3 for a in agents]
    bars = ax.bar(agents, ev_charge, color=[colors[a] for a in agents], edgecolor='black', linewidth=1.5, width=0.6)
    for bar, val in zip(bars, ev_charge):
        ax.text(bar.get_x() + bar.get_width()/2, val, f'{val:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    ax.set_ylabel('EV Charging (MWh)', fontweight='bold')
    ax.set_title('EV Charging Output', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    plt.suptitle('Simulation Results: 5 Episodes Real Data', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('outputs/oe3/graphics/simulation_results_real.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: simulation_results_real.png")
    plt.close()

def plot_reward_breakdown(simulation):
    """Plot multi-objective reward breakdown."""
    agents = ['SAC', 'PPO', 'A2C']
    colors = {'SAC': '#27ae60', 'PPO': '#3498db', 'A2C': '#f39c12'}
    
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    
    reward_names = ['CO2', 'Cost', 'Solar', 'EV', 'Grid']
    
    for idx, agent in enumerate(agents):
        ax = axes[idx]
        data = simulation['pv_bess_results'][agent]
        
        rewards = [
            abs(data['reward_co2_mean']),
            abs(data['reward_cost_mean']),
            abs(data['reward_solar_mean']),
            abs(data['reward_ev_mean']),
            abs(data['reward_grid_mean'])
        ]
        
        bars = ax.bar(reward_names, rewards, color=['#e74c3c', '#3498db', '#f39c12', '#2ecc71', '#9b59b6'], 
                      edgecolor='black', linewidth=1.2, alpha=0.8)
        
        for bar, val in zip(bars, rewards):
            ax.text(bar.get_x() + bar.get_width()/2, val, f'{val:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        ax.set_ylabel('Reward (Normalized)', fontweight='bold')
        ax.set_title(f'{agent} - Multi-Objective Rewards', fontweight='bold', fontsize=12)
        ax.set_ylim(0, 1.1)
        ax.grid(axis='y', alpha=0.3)
        ax.tick_params(axis='x', rotation=45)
    
    plt.suptitle('Multi-Objective Reward Breakdown: 5 Episodes', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('outputs/oe3/graphics/reward_breakdown_real.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: reward_breakdown_real.png")
    plt.close()

def main():
    """Main execution."""
    print("=" * 80)
    print("REGENERATING GRAPHICS WITH REAL 5-EPISODE TRAINING DATA")
    print("=" * 80)
    
    Path('outputs/oe3/graphics').mkdir(parents=True, exist_ok=True)
    
    print("\n📂 Loading training data...")
    episode_summary, simulation = load_training_data()
    print(f"✅ Loaded episode summary: {len(episode_summary)} agents")
    print(f"✅ Loaded simulation data")
    
    print("\n📊 Generating visualizations...")
    plot_training_metrics(episode_summary, simulation)
    plot_simulation_results(simulation)
    plot_reward_breakdown(simulation)
    
    print("\n" + "=" * 80)
    print("✅ GRAPHICS GENERATION COMPLETE!")
    print("=" * 80)
    print("\n📊 Graphics saved to: outputs/oe3/graphics/")
    print("\n📈 Generated files:")
    print("  • training_metrics_real.png")
    print("  • simulation_results_real.png")
    print("  • reward_breakdown_real.png")
    print("\n💾 Based on real training data from:")
    print("  • Episode Summary: analyses/oe3/agent_episode_summary.csv")
    print("  • Simulation Results: outputs/oe3/simulations/simulation_summary.json")

if __name__ == '__main__':
    main()
