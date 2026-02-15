#!/usr/bin/env python3
"""
Regenerate SAC KPI graphs with real training data:
- kpi_electricity_consumption.png
- kpi_electricity_cost.png
- kpi_ramping.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

OUTPUT_DIR = Path('outputs/sac_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COST_PER_KWH = 0.15  # €/kWh
CO2_PER_KWH = 0.4521  # kg CO₂/kWh

print(f"""
================================================================================
🔵 SAC KPI METRICS REGENERATION (Real Training Data)
================================================================================
""")

# ============================================================================
# LOAD SAC TIMESERIES DATA
# ============================================================================

print("📥 Loading SAC timeseries data...")

ts_file = OUTPUT_DIR / 'timeseries_sac.csv'
if not ts_file.exists():
    print(f"[X] {ts_file} not found")
    exit(1)

df = pd.read_csv(ts_file)
print(f"   [OK] Loaded {len(df)} hourly records")

# Detect grid import column
grid_col = None
for col in ['grid_import_kw', 'grid_import_kWh', 'grid_import_kwh']:
    if col in df.columns:
        grid_col = col
        break

if grid_col is None:
    print(f"[X] Could not find grid_import column")
    exit(1)

# ============================================================================
# AGGREGATE HOURLY DATA TO DAILY METRICS
# ============================================================================

print("[GRAPH] Aggregating to daily metrics...")

grid_import = pd.to_numeric(df[grid_col], errors='coerce').fillna(0).values
num_days = len(grid_import) // 24

daily_data = {
    'day': [],
    'consumption': [],
    'cost': [],
    'co2': [],
    'peak_load': [],
    'avg_ramping': [],
}

for day_idx in range(num_days):
    start = day_idx * 24
    end = start + 24
    day_load = grid_import[start:end]
    
    if len(day_load) < 24:
        continue
    
    consumption = float(day_load.sum())
    cost = consumption * COST_PER_KWH
    co2 = consumption * CO2_PER_KWH
    peak = float(day_load.max())
    ramping = float(np.mean(np.abs(np.diff(day_load))))
    
    daily_data['day'].append(day_idx + 1)
    daily_data['consumption'].append(consumption)
    daily_data['cost'].append(cost)
    daily_data['co2'].append(co2)
    daily_data['peak_load'].append(peak)
    daily_data['avg_ramping'].append(ramping)

daily_df = pd.DataFrame(daily_data)
print(f"   [OK] Aggregated to {len(daily_df)} daily records")

# ============================================================================
# CALCULATE REFERENCE VALUES
# ============================================================================

initial_consumption = daily_df['consumption'].iloc[:100].mean()
final_consumption = daily_df['consumption'].iloc[-100:].mean()
initial_cost = daily_df['cost'].iloc[:100].mean()
final_cost = daily_df['cost'].iloc[-100:].mean()
initial_ramping = daily_df['avg_ramping'].iloc[:100].mean()
final_ramping = daily_df['avg_ramping'].iloc[-100:].mean()

# ============================================================================
# GRAPH 1: ELECTRICITY CONSUMPTION
# ============================================================================

print("\n🎨 Generating KPI graphs...")
print("   Creating kpi_electricity_consumption.png...")

fig, ax = plt.subplots(figsize=(14, 6))

# Plot consumption with smooth trend
ax.plot(daily_df['day'], daily_df['consumption'], color='#1f77b4', linewidth=2.5, 
        label='Daily Consumption', alpha=0.8)
ax.fill_between(daily_df['day'], daily_df['consumption'], alpha=0.2, color='#1f77b4')

# Add trend line (50-day moving average)
trend = daily_df['consumption'].rolling(window=50, center=True).mean()
ax.plot(daily_df['day'], trend, color='darkblue', linewidth=2.5, linestyle='--', 
        label='50-Day Trend', alpha=0.8)

# Add initial and final reference lines
ax.axhline(initial_consumption, color='green', linestyle=':', linewidth=2.5, 
           label=f'Start Average: {initial_consumption:.0f} kWh/day', alpha=0.7)
ax.axhline(final_consumption, color='orange', linestyle=':', linewidth=2.5, 
           label=f'End Average: {final_consumption:.0f} kWh/day', alpha=0.7)

# Calculate reduction percentage
reduction_pct = ((initial_consumption - final_consumption) / initial_consumption * 100)

ax.set_xlabel('Training Day', fontsize=12, fontweight='bold')
ax.set_ylabel('Electricity Consumption (kWh/day)', fontsize=12, fontweight='bold')
ax.set_title(f'SAC Agent: Daily Electricity Consumption Evolution\n(Reduction: {reduction_pct:+.1f}%)',
             fontsize=13, fontweight='bold', pad=15)
ax.legend(loc='best', fontsize=10, framealpha=0.95)
ax.grid(True, alpha=0.3, linestyle='--')

# Add statistics box
stats_text = f"""Training Statistics:
Total Days: {len(daily_df):,}
Initial Avg: {initial_consumption:.1f} kWh/day
Final Avg: {final_consumption:.1f} kWh/day
Change: {reduction_pct:+.1f}%
Min Daily: {daily_df['consumption'].min():.0f} kWh
Max Daily: {daily_df['consumption'].max():.0f} kWh"""

ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'kpi_electricity_consumption.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"   [OK] Saved: kpi_electricity_consumption.png")
plt.close()

# ============================================================================
# GRAPH 2: ELECTRICITY COST
# ============================================================================

print("   Creating kpi_electricity_cost.png...")

fig, ax = plt.subplots(figsize=(14, 6))

# Plot cost with smooth trend
ax.plot(daily_df['day'], daily_df['cost'], color='#2ca02c', linewidth=2.5, 
        label='Daily Cost', alpha=0.8)
ax.fill_between(daily_df['day'], daily_df['cost'], alpha=0.2, color='#2ca02c')

# Add trend line
trend = daily_df['cost'].rolling(window=50, center=True).mean()
ax.plot(daily_df['day'], trend, color='darkgreen', linewidth=2.5, linestyle='--', 
        label='50-Day Trend', alpha=0.8)

# Add reference lines
ax.axhline(initial_cost, color='blue', linestyle=':', linewidth=2.5, 
           label=f'Start Average: ${initial_cost:.0f}/day', alpha=0.7)
ax.axhline(final_cost, color='red', linestyle=':', linewidth=2.5, 
           label=f'End Average: ${final_cost:.0f}/day', alpha=0.7)

# Calculate cost reduction
cost_reduction_pct = ((initial_cost - final_cost) / initial_cost * 100)

ax.set_xlabel('Training Day', fontsize=12, fontweight='bold')
ax.set_ylabel('Operating Cost (USD/day)', fontsize=12, fontweight='bold')
ax.set_title(f'SAC Agent: Daily Operating Cost Evolution\n(Reduction: {cost_reduction_pct:+.1f}%)',
             fontsize=13, fontweight='bold', pad=15)
ax.legend(loc='best', fontsize=10, framealpha=0.95)
ax.grid(True, alpha=0.3, linestyle='--')

# Add statistics box
stats_text = f"""Operating Cost Statistics:
Total Days: {len(daily_df):,}
Initial Avg: ${initial_cost:.2f}/day
Final Avg: ${final_cost:.2f}/day
Change: {cost_reduction_pct:+.1f}%
Total Cost (training): ${daily_df['cost'].sum():.0f}
Min Daily Cost: ${daily_df['cost'].min():.0f}
Max Daily Cost: ${daily_df['cost'].max():.0f}"""

ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'kpi_electricity_cost.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"   [OK] Saved: kpi_electricity_cost.png")
plt.close()

# ============================================================================
# GRAPH 3: POWER RAMPING
# ============================================================================

print("   Creating kpi_ramping.png...")

fig, ax = plt.subplots(figsize=(14, 6))

# Plot ramping with smooth trend
ax.plot(daily_df['day'], daily_df['avg_ramping'], color='#ff7f0e', linewidth=2.5, 
        label='Daily Avg Ramping', alpha=0.8)
ax.fill_between(daily_df['day'], daily_df['avg_ramping'], alpha=0.2, color='#ff7f0e')

# Add trend line
trend = daily_df['avg_ramping'].rolling(window=50, center=True).mean()
ax.plot(daily_df['day'], trend, color='darkorange', linewidth=2.5, linestyle='--', 
        label='50-Day Trend', alpha=0.8)

# Add reference lines
ax.axhline(initial_ramping, color='purple', linestyle=':', linewidth=2.5, 
           label=f'Start Average: {initial_ramping:.0f} kW/step', alpha=0.7)
ax.axhline(final_ramping, color='brown', linestyle=':', linewidth=2.5, 
           label=f'End Average: {final_ramping:.0f} kW/step', alpha=0.7)

# Calculate ramping reduction
ramping_reduction_pct = ((initial_ramping - final_ramping) / (initial_ramping + 0.001) * 100)

ax.set_xlabel('Training Day', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Power Ramping (kW/step)', fontsize=12, fontweight='bold')
ax.set_title(f'SAC Agent: Power Ramping Rate Evolution\n(Reduction: {ramping_reduction_pct:+.1f}%)',
             fontsize=13, fontweight='bold', pad=15)
ax.legend(loc='best', fontsize=10, framealpha=0.95)
ax.grid(True, alpha=0.3, linestyle='--')

# Add statistics box
stats_text = f"""Power Ramping Statistics:
Total Days: {len(daily_df):,}
Initial Avg: {initial_ramping:.2f} kW/step
Final Avg: {final_ramping:.2f} kW/step
Change: {ramping_reduction_pct:+.1f}%
Min Daily Ramp: {daily_df['avg_ramping'].min():.2f} kW
Max Daily Ramp: {daily_df['avg_ramping'].max():.2f} kW
Smoothness (lower=better)"""

ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'kpi_ramping.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"   [OK] Saved: kpi_ramping.png")
plt.close()

# ============================================================================
# SUMMARY
# ============================================================================

print(f"""
================================================================================
[GRAPH] SAC KPI METRICS REGENERATED
================================================================================

Generated Files:
  [OK] kpi_electricity_consumption.png  (Consumption reduction: {reduction_pct:+.1f}%)
  [OK] kpi_electricity_cost.png         (Cost reduction: {cost_reduction_pct:+.1f}%)
  [OK] kpi_ramping.png                  (Ramping reduction: {ramping_reduction_pct:+.1f}%)

Training Period: {len(daily_df)} days

Key Metrics:
  Consumption: {initial_consumption:.0f} -> {final_consumption:.0f} kWh/day
  Cost:        ${initial_cost:.0f} -> ${final_cost:.0f}/day
  Ramping:     {initial_ramping:.0f} -> {final_ramping:.0f} kW/step

================================================================================
All graphs generated with REAL data from SAC training
================================================================================
""")
