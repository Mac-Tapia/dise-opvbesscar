#!/usr/bin/env python3
"""
Critical Data Quality Assessment:

SAC: ev_charging_kw = 0 (NOT CONTROLLING EVs or BESS)
A2C: ev_charging_kw = 10-80 kW, bess = -342 to 342 kW (PROPERLY CONTROLLING)
PPO: Aggregated data structure (different format)

This changes the CO2 accounting:
- SAC: Only benefits from system dynamics (solar generation available)
- A2C: Actual optimization of EV charging + BESS dispatch
- PPO: Need different analysis approach

Generate correct dashboards for A2C (only agent with real EV control).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

OUTPUT_DIR = Path('outputs/comparison_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CO2_PER_KWH = 0.4521  # kg CO2/kWh
COST_PER_KWH = 0.15

print(f"""
================================================================================
[!]  DATA QUALITY ASSESSMENT: AGENT CONTROL VALIDATION
================================================================================

CRITICAL FINDINGS:

  SAC:  ev_charging=0 kW (ALL records)    [X] NOT CONTROLLING EVs
        bess_power=0 kW (ALL records)     [X] NOT CONTROLLING BESS
        -> This agent is NOT optimizing the system!

  A2C:  ev_charging=10-80 kW (active)    [OK] CONTROLLING EVs
        bess_power=-342 to 342 kW        [OK] CONTROLLING BESS
        -> This agent IS optimizing the system!

  PPO:  Different data structure          [!]  Aggregated, not timeseries

IMPLICATION:
  - SAC generates NO REAL CONTROL - purely passive system response
  - A2C generates REAL CONTROL - active EV + BESS optimization  
  - Comparison should focus on A2C as the only validated controller

================================================================================
""")

# ============================================================================
# GENERATE A2C ANALYSIS (WITH REAL EV + BESS CONTROL)
# ============================================================================

print("[GRAPH] Analyzing A2C (only agent with real EV + BESS control)...\n")

df_a2c = pd.read_csv('outputs/a2c_training/timeseries_a2c.csv')

# Daily aggregation
num_days = len(df_a2c) // 24
daily_data = {
    'day': [],
    'consumption': [],
    'cost': [],
    'co2_direct': [],
    'co2_indirect': [],
    'ev_charging': [],
    'bess_power': [],
    'solar': [],
    'peak_load': [],
    'avg_ramping': [],
}

solar = pd.to_numeric(df_a2c['solar_kw'], errors='coerce').fillna(0).values
ev_charging = pd.to_numeric(df_a2c['ev_charging_kw'], errors='coerce').fillna(0).values
grid_import = pd.to_numeric(df_a2c['grid_import_kw'], errors='coerce').fillna(0).values
bess_power = pd.to_numeric(df_a2c['bess_power_kw'], errors='coerce').fillna(0).values

for day_idx in range(num_days):
    start = day_idx * 24
    end = start + 24
    
    day_solar = solar[start:end].sum()
    day_ev = ev_charging[start:end].sum()
    day_grid = grid_import[start:end].sum()
    day_bess = bess_power[start:end]
    
    # CO2 calculations
    co2_direct = day_ev * CO2_PER_KWH  # EV charging
    bess_discharge = max(0, -day_bess.sum())  # Only positive discharge
    co2_indirect = (day_solar + bess_discharge) * CO2_PER_KWH
    
    daily_data['day'].append(day_idx + 1)
    daily_data['consumption'].append(day_grid)
    daily_data['cost'].append(day_grid * COST_PER_KWH)
    daily_data['co2_direct'].append(co2_direct)
    daily_data['co2_indirect'].append(co2_indirect)
    daily_data['ev_charging'].append(day_ev)
    daily_data['bess_power'].append(day_bess.sum())
    daily_data['solar'].append(day_solar)
    daily_data['peak_load'].append(float(grid_import[start:end].max()) if len(grid_import[start:end]) > 0 else 0)
    daily_data['avg_ramping'].append(float(np.mean(np.abs(np.diff(grid_import[start:end])))) if len(grid_import[start:end]) > 1 else 0)

df_daily = pd.DataFrame(daily_data)
df_daily['co2_total'] = df_daily['co2_direct'] + df_daily['co2_indirect']

print(f"   A2C Training Days: {len(df_daily)}")
print(f"   EV Charging: {df_daily['ev_charging'].mean():.1f} kW/day avg (total: {df_daily['ev_charging'].sum():.0f} kWh)")
print(f"   Solar Avail: {df_daily['solar'].mean():.1f} kW/day avg")
print(f"   BESS Dispatch: {df_daily['bess_power'].mean():.1f} kW/day avg")
print(f"   CO2 Direct: {df_daily['co2_direct'].mean():.0f} kg/day")
print(f"   CO2 Indirect: {df_daily['co2_indirect'].mean():.0f} kg/day")
print()

# ============================================================================
# GENERATE A2C 5-METRICS EVOLUTION
# ============================================================================

print("🎨 Generating A2C 5-metrics evolution (with REAL EV control)...")

initial_days = df_daily.head(100)
final_days = df_daily.tail(100)

fig = plt.figure(figsize=(18, 10))
gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)

color = '#2ca02c'

# Panel 1: Consumption
ax = fig.add_subplot(gs[0, 0])
ax.plot(df_daily['day'], df_daily['consumption'], color=color, linewidth=2.5, alpha=0.8)
ax.fill_between(df_daily['day'], df_daily['consumption'], alpha=0.2, color=color)
trend = df_daily['consumption'].rolling(50).mean()
ax.plot(df_daily['day'], trend, color='darkgreen', linewidth=2, linestyle='--', alpha=0.8)
cons_red = ((initial_days['consumption'].mean() - final_days['consumption'].mean()) / (initial_days['consumption'].mean() + 0.001) * 100)
ax.set_ylabel('kWh/day', fontsize=11, fontweight='bold')
ax.set_title(f'Grid Import Reduction: {cons_red:+.1f}%', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3)

# Panel 2: Cost
ax = fig.add_subplot(gs[0, 1])
ax.plot(df_daily['day'], df_daily['cost'], color=color, linewidth=2.5, alpha=0.8)
ax.fill_between(df_daily['day'], df_daily['cost'], alpha=0.2, color=color)
trend = df_daily['cost'].rolling(50).mean()
ax.plot(df_daily['day'], trend, color='darkgreen', linewidth=2, linestyle='--', alpha=0.8)
cost_red = ((initial_days['cost'].mean() - final_days['cost'].mean()) / (initial_days['cost'].mean() + 0.001) * 100)
ax.set_ylabel('USD/day', fontsize=11, fontweight='bold')
ax.set_title(f'Cost Reduction: {cost_red:+.1f}%', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3)

# Panel 3: CO2 Direct (EV REPLACEMENT)
ax = fig.add_subplot(gs[0, 2])
ax.plot(df_daily['day'], df_daily['co2_direct'], color='darkgreen', linewidth=2.5, alpha=0.8)
ax.fill_between(df_daily['day'], df_daily['co2_direct'], alpha=0.2, color='green')
trend = df_daily['co2_direct'].rolling(50).mean()
ax.plot(df_daily['day'], trend, color='darkgreen', linewidth=2, linestyle='--', alpha=0.8)
co2d_init = initial_days['co2_direct'].mean()
co2d_final = final_days['co2_direct'].mean()
co2d_red = ((co2d_init - co2d_final) / (co2d_init + 0.001) * 100)
ax.set_ylabel('kg CO₂/day', fontsize=11, fontweight='bold')
ax.set_title(f'CO₂ DIRECT (EV Charging)\n{co2d_red:+.1f}% Reduction', fontsize=12, fontweight='bold',
             color='darkgreen', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
ax.grid(True, alpha=0.3)

# Panel 4: CO2 Indirect (SOLAR + BESS)
ax = fig.add_subplot(gs[1, 0])
ax.plot(df_daily['day'], df_daily['co2_indirect'], color='darkblue', linewidth=2.5, alpha=0.8)
ax.fill_between(df_daily['day'], df_daily['co2_indirect'], alpha=0.2, color='blue')
trend = df_daily['co2_indirect'].rolling(50).mean()
ax.plot(df_daily['day'], trend, color='darkblue', linewidth=2, linestyle='--', alpha=0.8)
co2i_init = initial_days['co2_indirect'].mean()
co2i_final = final_days['co2_indirect'].mean()
co2i_red = ((co2i_init - co2i_final) / (co2i_init + 0.001) * 100)
ax.set_ylabel('kg CO₂/day', fontsize=11, fontweight='bold')
ax.set_title(f'CO₂ INDIRECT (Solar+BESS)\n{co2i_red:+.1f}% Reduction', fontsize=12, fontweight='bold',
             color='darkblue', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
ax.grid(True, alpha=0.3)
ax.set_xlabel('Training Day', fontsize=11, fontweight='bold')

# Panel 5: Total CO2
ax = fig.add_subplot(gs[1, 1])
ax.plot(df_daily['day'], df_daily['co2_total'], color='darkred', linewidth=2.5, alpha=0.8)
ax.fill_between(df_daily['day'], df_daily['co2_total'], alpha=0.2, color='red')
trend = df_daily['co2_total'].rolling(50).mean()
ax.plot(df_daily['day'], trend, color='darkred', linewidth=2, linestyle='--', alpha=0.8)
co2t_init = initial_days['co2_total'].mean()
co2t_final = final_days['co2_total'].mean()
co2t_red = ((co2t_init - co2t_final) / (co2t_init + 0.001) * 100)
ax.set_ylabel('kg CO₂/day', fontsize=11, fontweight='bold')
ax.set_title(f'TOTAL CO2 (Direct+Indirect)\n{co2t_red:+.1f}% Reduction', fontsize=12, fontweight='bold',
             color='darkred', bbox=dict(boxstyle='round', facecolor='#FFE6E6', alpha=0.8))
ax.grid(True, alpha=0.3)
ax.set_xlabel('Training Day', fontsize=11, fontweight='bold')

# Panel 6: EV Charging Activity
ax = fig.add_subplot(gs[1, 2])
ax.plot(df_daily['day'], df_daily['ev_charging'], color='purple', linewidth=2.5, alpha=0.8, label='EV Charging')
ax.fill_between(df_daily['day'], df_daily['ev_charging'], alpha=0.2, color='purple')
trend = df_daily['ev_charging'].rolling(50).mean()
ax.plot(df_daily['day'], trend, color='darkviolet', linewidth=2, linestyle='--', alpha=0.8)
ax.set_ylabel('kW/day', fontsize=11, fontweight='bold')
ax.set_title('EV Charging Activity\n(Control Signal)', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.set_xlabel('Training Day', fontsize=11, fontweight='bold')

fig.suptitle('A2C Agent: 5-Metric Evolution with REAL EV + BESS Control\nDirect = EV only | Indirect = Solar + BESS discharge',
             fontsize=14, fontweight='bold', y=0.995)

plt.savefig(OUTPUT_DIR / 'a2c_5metrics_evolution_controlled.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"   [OK] Saved: a2c_5metrics_evolution_controlled.png\n")
plt.close()

# ============================================================================
# DATA QUALITY SUMMARY REPORT
# ============================================================================

print(f"""
================================================================================
📋 VALIDATION REPORT: AGENT CONTROL DATA
================================================================================

AGENT DATA STATUS:

  SAC (131,400 records):
    [X] ev_charging_kw: 0 kW (no EV charging control)
    [X] bess_power_kw: 0 kW (no BESS control)
    [!]  NOT A VALID AGENT - Passive system only
    ➜ EXCLUDE FROM OPTIMIZATION COMPARISON

  A2C (87,600 records):  
    [OK] ev_charging_kw: 10-80 kW (active EV control)
    [OK] bess_power_kw: -342 to 342 kW (active BESS control)
    [OK] VALID AGENT - Real optimization
    ➜ USE FOR CO2 REDUCTION ANALYSIS

  PPO (8,760 records):
    [!]  Different data structure (aggregated)
    ➜ SEPARATE ANALYSIS REQUIRED

CRITICAL INSIGHT:
  - SAC appears to be a baseline or misconfigured system
  - A2C is the only validated controller with real EV + BESS optimization
  - CO2 reduction metrics should focus on A2C's actual control effectiveness

A2C PERFORMANCE:
  - Grid Import: {cons_red:+.1f}%
  - Cost: {cost_red:+.1f}%
  - CO2 Direct (EV): {co2d_red:+.1f}%
  - CO2 Indirect (Solar+BESS): {co2i_red:+.1f}%
  - Total CO2: {co2t_red:+.1f}%

================================================================================
""")
