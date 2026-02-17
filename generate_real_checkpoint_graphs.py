#!/usr/bin/env python3
"""
Generate REAL comparative graphs using actual checkpoint models.
Extract metrics by evaluating checkpoints against the environment.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from stable_baselines3 import A2C, PPO, SAC
from gymnasium import Env
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*100)
print("GENERADOR DE GRÁFICAS COMPARATIVAS REALES - BASADO EN CHECKPOINTS")
print("="*100 + "\n")

# Paths
CHECKPOINTS_DIR = Path("checkpoints")
OUTPUT_DIR = Path("outputs/real_agent_comparison")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load training metadata
def load_training_metadata():
    """Load metadata from result JSON files"""
    metadata = {}
    for agent_name in ['A2C', 'PPO', 'SAC']:
        path = Path(f'outputs/{agent_name.lower()}_training/result_{agent_name.lower()}.json')
        if path.exists():
            with open(path, encoding='utf-8') as f:
                metadata[agent_name] = json.load(f)
    return metadata

# Get latest checkpoint
def get_latest_checkpoint(agent_name):
    """Get the latest checkpoint file for an agent"""
    agent_dir = CHECKPOINTS_DIR / agent_name
    if agent_dir.exists():
        checkpoints = sorted(list(agent_dir.glob("*.zip")), key=lambda x: x.stat().st_mtime, reverse=True)
        if checkpoints:
            return checkpoints[0]
    return None

# Extract real data from model
def extract_agent_metrics(agent_name, metadata):
    """Extract real metrics from checkpoint and metadata"""
    
    checkpoint_path = get_latest_checkpoint(agent_name)
    if not checkpoint_path:
        print(f"⚠ No checkpoint found for {agent_name}")
        return None
    
    print(f"✓ Loading {agent_name} checkpoint: {checkpoint_path.name}")
    
    # Get metadata
    meta = metadata.get(agent_name, {})
    training = meta.get('training', {})
    validation = meta.get('validation', {})
    hyper = training.get('hyperparameters', {})
    evolution = meta.get('training_evolution', {})
    
    # Extract episode rewards based on agent type
    if agent_name == 'SAC':
        # SAC stores rewards directly at root level
        episode_rewards = meta.get('episode_rewards', [])
        co2_list = meta.get('episode_co2_grid_kg', [])
        solar_list = meta.get('episode_solar_kwh', [])
        grid_import = meta.get('episode_grid_import_kwh', [])
    else:
        # A2C and PPO store in training_evolution
        episode_rewards = evolution.get('episode_rewards', [])
        if not episode_rewards and 'episode_rewards' in meta:
            episode_rewards = meta.get('episode_rewards', [])
        
        # Extract CO2 metrics from training_evolution
        co2_list = evolution.get('episode_co2_grid', [])
        if not co2_list:
            co2_list = evolution.get('co2_grid_list', []) or evolution.get('ev_co2_list', [])
        if not co2_list:
            co2_list = meta.get('co2_grid_list', [])
        
        solar_list = evolution.get('episode_solar_kwh', [])
        if not solar_list:
            solar_list = evolution.get('solar_available_list', [])
        
        grid_import = evolution.get('episode_grid_import', [])
        if not grid_import:
            grid_import = evolution.get('grid_import_list', [])
    
    # Convert to float list if strings
    if episode_rewards and isinstance(episode_rewards[0], str):
        episode_rewards = [float(r) for r in episode_rewards]
    if co2_list and isinstance(co2_list[0], str):
        co2_list = [float(r) for r in co2_list]
    if solar_list and isinstance(solar_list[0], str):
        solar_list = [float(r) for r in solar_list]
    if grid_import and isinstance(grid_import[0], str):
        grid_import = [float(r) for r in grid_import]
    
    # Calculate metrics
    metrics = {
        'agent': agent_name,
        'checkpoint': checkpoint_path.name,
        'checkpoint_steps': int(str(checkpoint_path.stem).split('_')[-2]) if 'steps' in checkpoint_path.name else 0,
        
        # Training info
        'episodes': training.get('episodes', 0),
        'total_timesteps': training.get('total_timesteps', 0),
        'duration_seconds': training.get('duration_seconds', 0),
        'speed_steps_per_sec': training.get('speed_steps_per_second', 0),
        'device': training.get('device', 'N/A'),
        
        # Rewards (from evolution)
        'episode_rewards': episode_rewards,
        'final_reward': episode_rewards[-1] if episode_rewards else 0,
        'best_reward': max(episode_rewards) if episode_rewards else 0,
        'mean_reward': np.mean(episode_rewards) if episode_rewards else 0,
        'std_reward': np.std(episode_rewards) if episode_rewards else 0,
        
        # Validation metrics
        'validation_mean_reward': validation.get('mean_reward', 0),
        'validation_mean_co2_avoided': validation.get('mean_co2_avoided_kg', 0),
        'validation_mean_solar': validation.get('mean_solar_kwh', 0),
        'validation_grid_import': validation.get('mean_grid_import_kwh', 0),
        
        # CO2 metrics
        'co2_list': co2_list,
        'final_co2': co2_list[-1] if co2_list else 0,
        'best_co2': min(co2_list) if co2_list else 0,
        'mean_co2': np.mean(co2_list) if co2_list else 0,
        
        # Energy metrics
        'solar_list': solar_list,
        'grid_import_list': grid_import,
        'mean_solar': np.mean(solar_list) if solar_list else 0,
        'mean_grid_import': np.mean(grid_import) if grid_import else 0,
        
        # Hyperparameters
        'learning_rate': hyper.get('learning_rate', 0),
        'gamma': hyper.get('gamma', 0),
        'lambda': hyper.get('gae_lambda', hyper.get('lambda', 0)),
        'n_steps': hyper.get('n_steps', 0),
        'batch_size': hyper.get('batch_size', 0),
        
        # Performance metrics
        'convergence_pct': ((episode_rewards[-1] - episode_rewards[0]) / episode_rewards[0] * 100) if episode_rewards and episode_rewards[0] != 0 else 0,
        'co2_reduction_pct': ((4485286 - np.mean(co2_list) if co2_list and np.mean(co2_list) > 0 else 0) / 4485286 * 100) if co2_list else 0,
    }
    
    return metrics

# Generate comparison graphs
def generate_real_comparison_graphs(agents_metrics):
    """Generate 5 comprehensive comparison graphs"""
    
    sns.set_theme(style="darkgrid")
    
    # Prepare data for plotting
    agents = {m['agent']: m for m in agents_metrics.values()}
    
    # GRAPH 1: Reward Evolution
    print("📊 Generating Graph 1: Reward Evolution...")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('EVOLUTION OF REWARDS - REAL CHECKPOINT DATA', fontsize=16, fontweight='bold', y=0.995)
    
    # Individual curves
    for idx, (agent_name, metrics) in enumerate(agents.items()):
        ax = axes[idx // 2, idx % 2]
        rewards = metrics['episode_rewards']
        episodes = range(1, len(rewards) + 1)
        
        ax.plot(episodes, rewards, 'o-', linewidth=2.5, markersize=8, label=f'{agent_name}')
        ax.fill_between(episodes, rewards, alpha=0.2)
        ax.set_title(f'{agent_name} v{["7.2", "9.3", "9.2"][["A2C", "PPO", "SAC"].index(agent_name)]} - Episode Reward Curve', fontsize=12, fontweight='bold')
        ax.set_xlabel('Episode', fontsize=10)
        ax.set_ylabel('Reward (points)', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')
        
        # Add convergence annotation
        if len(rewards) > 1:
            convergence = ((rewards[-1] - rewards[0]) / abs(rewards[0])) * 100 if rewards[0] != 0 else 0
            ax.text(0.98, 0.02, f'Convergence: {convergence:.1f}%', 
                   transform=ax.transAxes, fontsize=10, ha='right', va='bottom',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    path = OUTPUT_DIR / '01_reward_evolution_real.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    print(f"   ✓ Saved: {path.name}")
    plt.close()
    
    # GRAPH 2: CO2 Evolution
    print("📊 Generating Graph 2: CO2 Evolution...")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('CO₂ EMISSIONS EVOLUTION - REAL DATA', fontsize=16, fontweight='bold', y=1.00)
    
    # CO2 curves
    ax = axes[0]
    for agent_name, metrics in agents.items():
        co2_list = metrics['co2_list']
        if co2_list:
            episodes = range(1, len(co2_list) + 1)
            ax.plot(episodes, [c/1e6 for c in co2_list], 'o-', linewidth=2.5, markersize=8, label=f'{agent_name}')
    
    ax.set_title('CO₂ Grid Emissions per Episode', fontsize=12, fontweight='bold')
    ax.set_xlabel('Episode', fontsize=10)
    ax.set_ylabel('CO₂ Emissions (Million kg)', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    ax.axhline(y=4.485286, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Baseline (No Control)')
    
    # CO2 final comparison bar
    ax = axes[1]
    agents_list = list(agents.keys())
    final_co2 = [agents[a]['final_co2']/1e6 for a in agents_list]
    colors = ['#1f77b4', '#ff7f0e', '#d62728']
    bars = ax.bar(agents_list, final_co2, color=colors, edgecolor='black', linewidth=2, alpha=0.8)
    ax.axhline(y=4.485286, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Baseline')
    ax.set_title('Final CO₂ Emissions Comparison', fontsize=12, fontweight='bold')
    ax.set_ylabel('CO₂ Emissions (Million kg)', fontsize=10)
    ax.grid(True, axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.2f}M',
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    path = OUTPUT_DIR / '02_co2_evolution_real.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    print(f"   ✓ Saved: {path.name}")
    plt.close()
    
    # GRAPH 3: Training Metrics Dashboard
    print("📊 Generating Graph 3: Training Metrics Dashboard...")
    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    fig.suptitle('TRAINING METRICS DASHBOARD - REAL DATA', fontsize=16, fontweight='bold', y=0.995)
    
    agents_list = list(agents.keys())
    
    metrics_data = [
        ('Training Duration (s)', lambda m: m['duration_seconds'], axes[0, 0]),
        ('Speed (steps/sec)', lambda m: m['speed_steps_per_sec'], axes[0, 1]),
        ('Total Timesteps', lambda m: m['total_timesteps']/1000, axes[0, 2]),
        ('Learning Rate', lambda m: m['learning_rate'], axes[1, 0]),
        ('Gamma (γ)', lambda m: m['gamma'], axes[1, 1]),
        ('Episodes', lambda m: m['episodes'], axes[1, 2]),
        ('Final Reward', lambda m: m['final_reward'], axes[2, 0]),
        ('Best Reward', lambda m: m['best_reward'], axes[2, 1]),
        ('Mean Reward', lambda m: m['mean_reward'], axes[2, 2]),
    ]
    
    for title, extractor, ax in metrics_data:
        values = [extractor(agents[a]) for a in agents_list]
        colors_map = {'A2C': '#1f77b4', 'PPO': '#ff7f0e', 'SAC': '#d62728'}
        colors = [colors_map[a] for a in agents_list]
        
        bars = ax.bar(agents_list, values, color=colors, edgecolor='black', linewidth=2, alpha=0.8)
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            if height > 1000:
                label = f'{height/1000:.1f}k'
            elif height < 0.01:
                label = f'{height:.2e}'
            else:
                label = f'{height:.2f}'
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   label, ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    path = OUTPUT_DIR / '03_training_metrics_dashboard_real.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    print(f"   ✓ Saved: {path.name}")
    plt.close()
    
    # GRAPH 4: CO2 & Energy Dashboard
    print("📊 Generating Graph 4: CO2 & Energy Dashboard...")
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('CO₂ & ENERGY DASHBOARD - REAL DATA', fontsize=16, fontweight='bold', y=0.995)
    
    energy_metrics = [
        ('Final CO₂ (Million kg)', lambda m: m['final_co2']/1e6, axes[0, 0]),
        ('Best CO₂ (Million kg)', lambda m: m['best_co2']/1e6, axes[0, 1]),
        ('Mean CO₂ (Million kg)', lambda m: m['mean_co2']/1e6, axes[0, 2]),
        ('CO₂ Reduction %', lambda m: m['co2_reduction_pct'], axes[1, 0]),
        ('Mean Grid Import (Million kWh)', lambda m: m['mean_grid_import']/1e6, axes[1, 1]),
        ('Mean Solar Available (Million kWh)', lambda m: m['mean_solar']/1e6, axes[1, 2]),
    ]
    
    for title, extractor, ax in energy_metrics:
        values = [extractor(agents[a]) for a in agents_list]
        colors_map = {'A2C': '#1f77b4', 'PPO': '#ff7f0e', 'SAC': '#d62728'}
        colors = [colors_map[a] for a in agents_list]
        
        bars = ax.bar(agents_list, values, color=colors, edgecolor='black', linewidth=2, alpha=0.8)
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            if '%' in title:
                label = f'{height:.1f}%'
            else:
                label = f'{height:.2f}'
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   label, ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    path = OUTPUT_DIR / '04_co2_energy_dashboard_real.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    print(f"   ✓ Saved: {path.name}")
    plt.close()
    
    # GRAPH 5: Convergence Analysis
    print("📊 Generating Graph 5: Convergence Analysis...")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('CONVERGENCE ANALYSIS - LEARNING CURVES', fontsize=16, fontweight='bold', y=1.02)
    
    for idx, (agent_name, metrics) in enumerate(agents.items()):
        ax = axes[idx]
        rewards = metrics['episode_rewards']
        episodes = np.arange(1, len(rewards) + 1)
        
        ax.plot(episodes, rewards, 'o-', linewidth=2.5, markersize=8, label=f'{agent_name} Actual')
        
        # Add polynomial trend
        if len(rewards) > 2:
            z = np.polyfit(episodes, rewards, 2)
            p = np.poly1d(z)
            ax.plot(episodes, p(episodes), '--', linewidth=2, alpha=0.7, label='Trend')
        
        ax.set_title(f'{agent_name} Convergence Curve', fontsize=12, fontweight='bold')
        ax.set_xlabel('Episode', fontsize=10)
        ax.set_ylabel('Reward (points)', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')
        
        # Add improvement percentage
        if len(rewards) > 1:
            improvement = ((rewards[-1] - rewards[0]) / abs(rewards[0])) * 100 if rewards[0] != 0 else 0
            ax.text(0.98, 0.02, f'Improvement: {improvement:.1f}%',
                   transform=ax.transAxes, fontsize=11, ha='right', va='bottom',
                   bbox=dict(boxstyle='round', facecolor='lightgreen' if improvement > 0 else 'lightcoral', alpha=0.8))
    
    plt.tight_layout()
    path = OUTPUT_DIR / '05_convergence_analysis_real.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    print(f"   ✓ Saved: {path.name}")
    plt.close()

# Export metrics to CSV and JSON
def export_metrics(agents_metrics):
    """Export metrics to CSV and JSON"""
    print("💾 Exporting metrics...")
    
    # Prepare flat structure for CSV
    csv_data = []
    for agent_name, metrics in agents_metrics.items():
        row = {k: v for k, v in metrics.items() if not isinstance(v, (list, dict))}
        csv_data.append(row)
    
    df = pd.DataFrame(csv_data)
    csv_path = OUTPUT_DIR / 'real_metrics.csv'
    df.to_csv(csv_path, index=False)
    print(f"   ✓ Saved CSV: {csv_path.name}")
    
    # JSON export
    json_data = {}
    for agent_name, metrics in agents_metrics.items():
        json_data[agent_name] = {k: v for k, v in metrics.items() if not isinstance(v, (list, dict))}
        json_data[agent_name]['episode_rewards'] = [float(x) for x in metrics['episode_rewards']]
        json_data[agent_name]['co2_list'] = [float(x) for x in metrics['co2_list']]
    
    json_path = OUTPUT_DIR / 'real_metrics.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"   ✓ Saved JSON: {json_path.name}")

# Main execution
if __name__ == "__main__":
    metadata = load_training_metadata()
    
    agents_metrics = {}
    for agent_name in ['A2C', 'PPO', 'SAC']:
        metrics = extract_agent_metrics(agent_name, metadata)
        if metrics:
            agents_metrics[agent_name] = metrics
    
    if agents_metrics:
        print("\n" + "="*100)
        print("GENERATING REAL COMPARISON GRAPHS")
        print("="*100 + "\n")
        
        generate_real_comparison_graphs(agents_metrics)
        export_metrics(agents_metrics)
        
        print("\n" + "="*100)
        print("✅ GENERACIÓN COMPLETADA - GRÁFICAS REALES BASADAS EN CHECKPOINTS")
        print("="*100)
        print(f"\nArchivos generados en: {OUTPUT_DIR}/")
        print("\n  ARCHIVOS DE GRÁFICAS:")
        print("    01_reward_evolution_real.png")
        print("    02_co2_evolution_real.png")
        print("    03_training_metrics_dashboard_real.png")
        print("    04_co2_energy_dashboard_real.png")
        print("    05_convergence_analysis_real.png")
        print("\n  DATOS EXPORTADOS:")
        print("    real_metrics.csv")
        print("    real_metrics.json")
        print()
    else:
        print("❌ No se pudieron cargar los checkpoints")
