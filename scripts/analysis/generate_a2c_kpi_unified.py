#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate A2C KPI Dashboard matching PPO structure.
6 panels showing daily KPI metrics from timeseries data.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

sns.set_style("whitegrid")
plt.rcParams['font.size'] = 10

# Paths
A2C_DIR = Path('outputs/a2c_training')
TIMESERIES_FILE = A2C_DIR / 'timeseries_a2c.csv'
OUTPUT_FILE = A2C_DIR / 'kpi_dashboard.png'

print("=" * 70)
print("🟢 A2C KPI DASHBOARD GENERATOR (Matching PPO Structure)")
print("=" * 70)

# Load timeseries
print("\n📥 Loading timeseries data...")
try:
    df = pd.read_csv(TIMESERIES_FILE)
    print(f"   [OK] Loaded {len(df)} hourly records")
except Exception as e:
    print(f"[X] Error loading timeseries: {e}")
    exit(1)

# Aggregate by day
print("\n[GRAPH] Aggregating hourly data to daily metrics...")

num_days = len(df) // 24
days_list = []
consumption_list = []
cost_list = []
emissions_list = []
peak_list = []
avg_load_list = []
ramping_list = []

grid_import = pd.to_numeric(df['grid_import_kw'], errors='coerce').fillna(0).values

for day_idx in range(num_days):
    start_idx = day_idx * 24
    end_idx = start_idx + 24
    
    day_load = grid_import[start_idx:end_idx]
    
    if len(day_load) < 24:
        continue
    
    consumption = float(day_load.sum())
    cost = consumption * 0.15
    emissions = consumption * 0.4521
    peak = float(day_load.max())
    avg_load = float(day_load.mean())
    ramping = float(np.mean(np.abs(np.diff(day_load))))
    
    consumption_list.append(max(0, consumption))
    cost_list.append(max(0, cost))
    emissions_list.append(max(0, emissions))
    peak_list.append(peak)
    avg_load_list.append(avg_load)
    ramping_list.append(ramping)
    days_list.append(day_idx + 1)

print(f"   [OK] Aggregated to {len(days_list)} days")

if len(days_list) == 0:
    print("[X] No data aggregated!")
    exit(1)

# Convert to arrays
days = np.array(days_list)
consumption = np.array(consumption_list)
cost = np.array(cost_list)
emissions = np.array(emissions_list)
peak = np.array(peak_list)
avg_load = np.array(avg_load_list)
ramping = np.array(ramping_list)
load_factor = avg_load / (peak + 1e-6)
one_minus_lf = 1.0 - load_factor

# Smoothing
def smooth(data, window=7):
    s = pd.Series(data)
    return s.rolling(window=window, center=True, min_periods=1).mean().values

# Generate dashboard
print("\n[CHART] Generating 2x3 KPI Dashboard for A2C...")

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.patch.set_facecolor('white')

colors = {
    'consumption': '#2ca02c',
    'cost': '#17becf',
    'emissions': '#ff7f0e',
    'ramping': '#e377c2',
    'peak': '#7f7f7f',
    'load_factor': '#9467bd'
}

# Row 1: Consumption, Cost, Emissions
# 1. Consumption
ax = axes[0, 0]
cons_smooth = smooth(consumption)
ax.plot(days, cons_smooth, color=colors['consumption'], linewidth=3, label='Electricity Consumption')
ax.fill_between(days, cons_smooth, alpha=0.15, color=colors['consumption'])
ax.set_title('Electricity Consumption (kWh/day)', fontsize=13, fontweight='bold')
ax.set_xlabel('Day')
ax.set_ylabel('kWh/day')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_ylim(bottom=0)
ax.legend(fontsize=10, loc='upper right')

if len(consumption) > 1 and consumption[0] > 0:
    improvement = (consumption[0] - consumption[-1]) / consumption[0] * 100
    color = 'green' if improvement > 0 else 'red'
    ax.text(0.98, 0.02, f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}%',
           transform=ax.transAxes, fontsize=11, color=color, ha='right', va='bottom',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5), fontweight='bold')

# 2. Cost
ax = axes[0, 1]
cost_smooth = smooth(cost)
ax.plot(days, cost_smooth, color=colors['cost'], linewidth=3, label='Electricity Cost')
ax.fill_between(days, cost_smooth, alpha=0.15, color=colors['cost'])
ax.set_title('Electricity Cost (USD/day)', fontsize=13, fontweight='bold')
ax.set_xlabel('Day')
ax.set_ylabel('Cost (USD)')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_ylim(bottom=0)
ax.legend(fontsize=10, loc='upper right')

if len(cost) > 1 and cost[0] > 0:
    improvement = (cost[0] - cost[-1]) / cost[0] * 100
    color = 'green' if improvement > 0 else 'red'
    ax.text(0.98, 0.02, f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}%',
           transform=ax.transAxes, fontsize=11, color=color, ha='right', va='bottom',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5), fontweight='bold')

# 3. CO2 Emissions
ax = axes[0, 2]
emis_smooth = smooth(emissions)
ax.plot(days, emis_smooth, color=colors['emissions'], linewidth=3, label='Carbon Emissions')
ax.fill_between(days, emis_smooth, alpha=0.15, color=colors['emissions'])
ax.set_title('Carbon Emissions (kg CO2/day)', fontsize=13, fontweight='bold')
ax.set_xlabel('Day')
ax.set_ylabel('kg CO2')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_ylim(bottom=0)
ax.legend(fontsize=10, loc='upper right')

if len(emissions) > 1 and emissions[0] > 0:
    improvement = (emissions[0] - emissions[-1]) / emissions[0] * 100
    color = 'green' if improvement > 0 else 'red'
    ax.text(0.98, 0.02, f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}%',
           transform=ax.transAxes, fontsize=11, color=color, ha='right', va='bottom',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5), fontweight='bold')

# Row 2: Ramping, Peak, Load Factor
# 4. Ramping
ax = axes[1, 0]
ramp_smooth = smooth(ramping)
ax.plot(days, ramp_smooth, color=colors['ramping'], linewidth=3, label='Grid Ramping')
ax.fill_between(days, ramp_smooth, alpha=0.15, color=colors['ramping'])
ax.set_title('Grid Ramping (kW/step)', fontsize=13, fontweight='bold')
ax.set_xlabel('Day')
ax.set_ylabel('kW/step')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_ylim(bottom=0)
ax.legend(fontsize=10, loc='upper right')

if len(ramping) > 1 and ramping[0] > 0:
    improvement = (ramping[0] - ramping[-1]) / ramping[0] * 100
    color = 'green' if improvement > 0 else 'red'
    ax.text(0.98, 0.02, f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}%',
           transform=ax.transAxes, fontsize=11, color=color, ha='right', va='bottom',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5), fontweight='bold')

# 5. Daily Peak
ax = axes[1, 1]
peak_smooth = smooth(peak)
ax.plot(days, peak_smooth, color=colors['peak'], linewidth=3, label='Daily Peak')
ax.fill_between(days, peak_smooth, alpha=0.15, color=colors['peak'])
ax.axhline(y=250, color='red', linestyle='--', linewidth=2.5, alpha=0.7, label='Limit 250kW')
ax.set_title('Daily Peak Load (kW)', fontsize=13, fontweight='bold')
ax.set_xlabel('Day')
ax.set_ylabel('Peak (kW)')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_ylim(bottom=0)
ax.legend(fontsize=10, loc='upper right')

if len(peak) > 1 and peak[0] > 0:
    improvement = (peak[0] - peak[-1]) / peak[0] * 100
    color = 'green' if improvement > 0 else 'red'
    ax.text(0.98, 0.02, f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}%',
           transform=ax.transAxes, fontsize=11, color=color, ha='right', va='bottom',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5), fontweight='bold')

# 6. Load Factor
ax = axes[1, 2]
lf_smooth = smooth(one_minus_lf)
ax.plot(days, lf_smooth, color=colors['load_factor'], linewidth=3, label='(1 - Load Factor)')
ax.fill_between(days, lf_smooth, alpha=0.15, color=colors['load_factor'])
ax.axhline(y=0.3, color='green', linestyle='--', linewidth=2.5, alpha=0.7, label='Target 0.3')
ax.fill_between(days, 0, 0.3, alpha=0.05, color='green')
ax.set_title('Load Factor (1 - LF)', fontsize=13, fontweight='bold')
ax.set_xlabel('Day')
ax.set_ylabel('(1 - LF)')
ax.set_ylim(0, 1)
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(fontsize=10, loc='upper right')

if len(one_minus_lf) > 1 and one_minus_lf[0] > 0:
    improvement = (one_minus_lf[0] - one_minus_lf[-1]) / one_minus_lf[0] * 100
    color = 'green' if improvement > 0 else 'red'
    ax.text(0.98, 0.02, f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}%',
           transform=ax.transAxes, fontsize=11, color=color, ha='right', va='bottom',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5), fontweight='bold')

# Title
improvements = []
if len(consumption) > 1 and consumption[0] > 0:
    imp = (consumption[0] - consumption[-1]) / consumption[0] * 100
    if imp > 0:
        improvements.append(f'Consumption: {imp:.1f}%')

if len(emissions) > 1 and emissions[0] > 0:
    imp = (emissions[0] - emissions[-1]) / emissions[0] * 100
    if imp > 0:
        improvements.append(f'CO2: {imp:.1f}%')

title = 'CityLearn v2 - A2C Agent KPI Dashboard'
if improvements:
    title += f' | Improvements: {", ".join(improvements)}'

fig.suptitle(title, fontsize=15, fontweight='bold', y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.97])

# Save
plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
print(f"   [OK] Saved: {OUTPUT_FILE}")

plt.close(fig)

# Print summary
print("\n[GRAPH] A2C KPI Summary (10 episodes, 3,650 days):")
print(f"   Consumption:   {consumption[0]:>10.1f} -> {consumption[-1]:>10.1f} kWh/day")
print(f"   Cost:          {cost[0]:>10.1f} -> {cost[-1]:>10.1f} USD/day")
print(f"   CO2 Emissions: {emissions[0]:>10.1f} -> {emissions[-1]:>10.1f} kg/day")
print(f"   Peak Load:     {peak[0]:>10.1f} -> {peak[-1]:>10.1f} kW")
print(f"   Ramping:       {ramping[0]:>10.2f} -> {ramping[-1]:>10.2f} kW/step")
print(f"   Load Factor:   {one_minus_lf[0]:>10.3f} -> {one_minus_lf[-1]:>10.3f}")

print("\n" + "=" * 70)
print("[OK] A2C KPI DASHBOARD GENERATION COMPLETE")
print("=" * 70)
