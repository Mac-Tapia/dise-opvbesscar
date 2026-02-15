#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate comprehensive agent comparison graphs with SAC, A2C, and PPO.
Integrates real data from timeseries and KPI dashboards.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

sns.set_style("whitegrid")
plt.rcParams['font.size'] = 10

# Paths
SAC_DIR = Path('outputs/sac_training')
A2C_DIR = Path('outputs/a2c_training')
PPO_DIR = Path('outputs/ppo_training')
COMPARISON_DIR = Path('outputs/comparison_training')
COMPARISON_DIR.mkdir(exist_ok=True)

print("=" * 80)
print("🔵 COMPREHENSIVE AGENT COMPARISON GENERATOR (SAC + A2C + PPO)")
print("=" * 80)

# ============================================================================
# LOAD DATA FOR ALL AGENTS
# ============================================================================

print("\n📥 Loading agent data...")

# Define agent properties
agents = {
    'SAC': {
        'dir': SAC_DIR,
        'color': '#1f77b4',
        'timeseries_file': SAC_DIR / 'timeseries_sac.csv',
        'result_file': SAC_DIR / 'result_sac.json',
        'episodes': 15,
        'data': {}
    },
    'A2C': {
        'dir': A2C_DIR,
        'color': '#2ca02c',
        'timeseries_file': A2C_DIR / 'timeseries_a2c.csv',
        'result_file': A2C_DIR / 'result_a2c.json',
        'episodes': 10,
        'data': {}
    },
    'PPO': {
        'dir': PPO_DIR,
        'color': '#ff7f0e',
        'timeseries_file': PPO_DIR / 'timeseries_ppo.csv',
        'result_file': PPO_DIR / 'result_ppo.json',
        'episodes': None,  # Will estimate
        'data': {}
    }
}

# Load real timeseries data for each agent
for agent_name, agent_info in agents.items():
    try:
        if agent_info['timeseries_file'].exists():
            df = pd.read_csv(agent_info['timeseries_file'])
            print(f"   ✓ {agent_name}: {len(df)} hourly records loaded")
            
            # Detect grid import column (varies by agent)
            grid_col = None
            if 'grid_import_kw' in df.columns:
                grid_col = 'grid_import_kw'
            elif 'grid_import_kWh' in df.columns:
                grid_col = 'grid_import_kWh'
            elif 'grid_import_kwh' in df.columns:
                grid_col = 'grid_import_kwh'
            else:
                # For PPO, use consumption as proxy if grid_import not found
                grid_col = 'consumption_kWh' if 'consumption_kWh' in df.columns else None
            
            if grid_col is None:
                print(f"   ⚠️  {agent_name}: Could not find grid_import column")
                continue
            
            # Aggregate to daily metrics
            num_days = len(df) // 24
            grid_import = pd.to_numeric(df[grid_col], errors='coerce').fillna(0).values
            
            consumption_list = []
            cost_list = []
            emissions_list = []
            peak_list = []
            avg_load_list = []
            ramping_list = []
            
            for day_idx in range(num_days):
                start_idx = day_idx * 24
                end_idx = start_idx + 24
                day_load = grid_import[start_idx:end_idx]
                
                if len(day_load) < 24:
                    continue
                
                consumption_list.append(float(day_load.sum()))
                cost_list.append(float(day_load.sum()) * 0.15)
                emissions_list.append(float(day_load.sum()) * 0.4521)
                peak_list.append(float(day_load.max()))
                avg_load_list.append(float(day_load.mean()))
                ramping_list.append(float(np.mean(np.abs(np.diff(day_load)))))
            
            agent_info['data'] = {
                'consumption': np.array(consumption_list),
                'cost': np.array(cost_list),
                'emissions': np.array(emissions_list),
                'peak': np.array(peak_list),
                'avg_load': np.array(avg_load_list),
                'ramping': np.array(ramping_list),
                'days': np.arange(1, len(consumption_list) + 1)
            }
            
        else:
            print(f"   ⚠️  {agent_name}: timeseries file not found, skipping")
            
    except Exception as e:
        print(f"   ❌ {agent_name}: {e}")

# Filter out agents without data
agents_with_data = {k: v for k, v in agents.items() if v['data']}

if len(agents_with_data) < 2:
    print("\n❌ Not enough agents with data for comparison!")
    exit(1)

print(f"\n   ✓ {len(agents_with_data)} agents have data for comparison")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def smooth(data, window=7):
    """Apply moving average smoothing."""
    s = pd.Series(data)
    return s.rolling(window=window, center=True, min_periods=1).mean().values

def plot_comparison(metric_name, metric_key, ylabel, title, filename):
    """Generate comparison graph for a metric across all agents."""
    
    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor('white')
    
    for agent_name, agent_info in agents_with_data.items():
        if metric_key not in agent_info['data']:
            continue
        
        metric_data = agent_info['data'][metric_key]
        days = agent_info['data']['days']
        metric_smooth = smooth(metric_data)
        
        ax.plot(days, metric_smooth, 
               color=agent_info['color'], 
               linewidth=3, 
               label=f"{agent_name} ({len(metric_data)} days)",
               marker='o',
               markersize=4,
               alpha=0.8)
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Day', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, loc='best')
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    output_path = COMPARISON_DIR / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"   ✅ {filename}")
    
    return output_path

# ============================================================================
# GENERATE COMPARISON GRAPHS
# ============================================================================

print("\n📈 Generating comparison graphs...")

# 1. Consumption Comparison
plot_comparison(
    'Consumption', 
    'consumption',
    'kWh/day',
    'Electricity Consumption Comparison (All Agents)',
    'real_cost_all_agents_comparison.png'
)

# 2. Cost Comparison
plot_comparison(
    'Cost',
    'cost',
    'USD/day',
    'Electricity Cost Comparison (All Agents)',
    'real_daily_peak_all_agents_comparison.png'
)

# 3. CO2 Emissions Comparison
plot_comparison(
    'CO2',
    'emissions',
    'kg CO2/day',
    'Carbon Emissions Comparison (All Agents)',
    'real_co2_direct_all_agents_comparison.png'
)

# 4. Peak Load Comparison
plot_comparison(
    'Peak',
    'peak',
    'kW',
    'Daily Peak Load Comparison (All Agents)',
    'real_co2_indirect_all_agents_comparison.png'
)

# 5. Ramping Comparison
plot_comparison(
    'Ramping',
    'ramping',
    'kW/step',
    'Grid Ramping Comparison (All Agents)',
    'real_ramping_all_agents_comparison.png'
)

# ============================================================================
# GENERATE COMPREHENSIVE DASHBOARD COMPARISON
# ============================================================================

print("\n📊 Generating comprehensive dashboard...")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.patch.set_facecolor('white')

# Metrics to plot
metrics = [
    ('consumption', 'Electricity Consumption (kWh/day)', 'kWh/day', 0, 0),
    ('cost', 'Electricity Cost (USD/day)', 'USD/day', 0, 1),
    ('emissions', 'CO2 Emissions (kg/day)', 'kg CO2', 0, 2),
    ('peak', 'Daily Peak Load (kW)', 'kW', 1, 0),
    ('ramping', 'Grid Ramping (kW/step)', 'kW/step', 1, 1),
]

# Smoothing
for metric_key, title, ylabel, row, col in metrics:
    ax = axes[row, col]
    
    for agent_name, agent_info in agents_with_data.items():
        if metric_key not in agent_info['data']:
            continue
        
        metric_data = agent_info['data'][metric_key]
        days = agent_info['data']['days']
        metric_smooth = smooth(metric_data)
        
        ax.plot(days, metric_smooth,
               color=agent_info['color'],
               linewidth=2.5,
               label=agent_name,
               alpha=0.85)
    
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('Day', fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=10, loc='best')
    ax.set_ylim(bottom=0)

# 6th panel: Summary Statistics Table
ax = axes[1, 2]
ax.axis('off')

# Create summary table
summary_data = []
for agent_name, agent_info in agents_with_data.items():
    data = agent_info['data']
    if data:
        summary_data.append([
            agent_name,
            f"{data['consumption'][0]:.0f}",
            f"{data['consumption'][-1]:.0f}",
            f"{data['cost'][-1]:.0f}",
            f"{data['emissions'][-1]:.0f}",
        ])

if summary_data:
    table = ax.table(
        cellText=summary_data,
        colLabels=['Agent', 'Cons₀', 'Cons_f', 'Cost_f', 'CO2_f'],
        cellLoc='center',
        loc='center',
        bbox=[0, 0, 1, 1]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Color header (5 columns: Agent, Cons₀, Cons_f, Cost_f, CO2_f)
    for i in range(5):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Color rows by agent
    for i, (agent_name, _) in enumerate([(a, None) for a, _ in agents_with_data.items()]):
        table[(i+1, 0)].set_facecolor(agents_with_data[agent_name]['color'])
        table[(i+1, 0)].set_text_props(color='white', weight='bold')

title = 'CityLearn v2 - Multi-Agent Comparison Dashboard (SAC + A2C + PPO)'
fig.suptitle(title, fontsize=15, fontweight='bold', y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.97])

output_path = COMPARISON_DIR / 'real_real_metrics_dashboard_comparison.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
plt.close(fig)
print(f"   ✅ real_real_metrics_dashboard_comparison.png")

# ============================================================================
# GENERATE SUMMARY CSV
# ============================================================================

print("\n📄 Generating summary statistics...")

summary_rows = []
for agent_name, agent_info in agents_with_data.items():
    data = agent_info['data']
    if data and len(data['consumption']) > 0:
        summary_rows.append({
            'Agent': agent_name,
            'Episodes': agent_info['episodes'] or 'N/A',
            'Days': len(data['consumption']),
            'Consumption_Initial_kWh': f"{data['consumption'][0]:.1f}",
            'Consumption_Final_kWh': f"{data['consumption'][-1]:.1f}",
            'Cost_Initial_USD': f"{data['cost'][0]:.1f}",
            'Cost_Final_USD': f"{data['cost'][-1]:.1f}",
            'CO2_Initial_kg': f"{data['emissions'][0]:.1f}",
            'CO2_Final_kg': f"{data['emissions'][-1]:.1f}",
            'Peak_Load_kW': f"{data['peak'].max():.1f}",
            'Avg_Ramping_kW': f"{data['ramping'].mean():.2f}",
        })

summary_df = pd.DataFrame(summary_rows)
summary_path = COMPARISON_DIR / 'comparison_summary.csv'
summary_df.to_csv(summary_path, index=False)
print(f"   ✅ comparison_summary.csv")

# Print summary table
print("\n📊 Summary Statistics:")
print(summary_df.to_string(index=False))

print("\n" + "=" * 80)
print("✅ COMPARISON GRAPHS GENERATION COMPLETE")
print(f"📁 Saved to: {COMPARISON_DIR}")
print("=" * 80)
