#!/usr/bin/env python3
"""
Calculate CO₂ metrics CORRECTLY:

CO₂ DIRECTO: Cantidad de EVs cargados (cambio modal combustion -> electrico)
  Source: reduccion_directa_co2_kg from chargers data

CO₂ INDIRECTO: Energia que viene de SOLAR + BESS (no del grid diesel)
  Calculation: (Solar_generation + BESS_discharge) * 0.4521 kg CO₂/kWh
  This represents energy that AVOIDS thermal generation

Grid NO reduce porque esta en diagonal a diesel (igual que mall).
El unico beneficio indirecto es la energia limpia usada para cargar EVs.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

OUTPUT_DIR = Path('outputs/comparison_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CO2_THERMAL_FACTOR = 0.4521  # kg CO₂/kWh from diesel grid

print(f"""
================================================================================
[OK] CORRECT CO₂ CALCULATION METHODOLOGY
================================================================================

CO₂ DIRECTO (Direct Emissions Reduction):
  +- Source: reduccion_directa_co2_kg (from chargers_ev_ano_2024_v3.csv)
  +- Definition: CO₂ avoided by EVs instead of combustion motos/mototaxis
  +- Unit: kg CO₂/day
  +- Note: Based on NUMBER of vehicles charged, not energy

CO₂ INDIRECTO (Indirect Emissions Reduction):
  +- Source: (Solar generation + BESS discharge) from training timeseries
  +- Definition: Energy from clean sources used to charge EVs
  +- Calculation: (solar_kw + bess_discharge_kw) × 0.4521 kg CO₂/kWh
  +- Unit: kg CO₂/day
  +- Note: This energy avoids thermal generation from diesel grid

Grid & Mall:
  +- Both connected to diesel thermal generation
  +- Grid import does NOT reduce CO₂ (just shifts burden)
  +- Only SOLAR + BESS reduce CO₂ by avoiding thermal

================================================================================
""")

# ============================================================================
# LOAD OE2 DATA (Infrastructure & Direct CO2)
# ============================================================================

print("📥 Loading OE2 data (infrastructure & direct CO₂)...\n")

# Load chargers with direct CO2 reduction
chargers_file = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
chargers_df = pd.read_csv(chargers_file)

# Convert datetime
chargers_df['datetime'] = pd.to_datetime(chargers_df['datetime'])
chargers_df = chargers_df.sort_values('datetime')

print(f"   [OK] Chargers data: {len(chargers_df)} hourly records")
print(f"     - Direct CO₂ reduction column: 'reduccion_directa_co2_kg'")

# Daily aggregation
chargers_daily = chargers_df.groupby(chargers_df['datetime'].dt.date).agg({
    'ev_energia_total_kwh': 'sum',
    'ev_energia_motos_kwh': 'sum',
    'ev_energia_mototaxis_kwh': 'sum',
    'reduccion_directa_co2_kg': 'sum',
    'ev_demand_kwh': 'sum'
}).reset_index()

chargers_daily.columns = ['date', 'ev_energy_total', 'ev_energy_motos', 
                          'ev_energy_mototaxis', 'co2_direct', 'ev_demand']
chargers_daily['date'] = pd.to_datetime(chargers_daily['date'])

print(f"   [OK] Aggregated to {len(chargers_daily)} daily records")
print(f"     - CO₂ Direct sample: {chargers_daily['co2_direct'].iloc[:5].values} kg/day\n")

# ============================================================================
# LOAD AGENT TRAINING DATA (Solar + BESS for Indirect CO2)
# ============================================================================

print("📥 Loading agent training timeseries (solar + BESS for indirect CO₂)...\n")

agents_data = {}

# SAC
sac_file = Path('outputs/sac_training/timeseries_sac.csv')
if sac_file.exists():
    sac_ts = pd.read_csv(sac_file)
    print(f"   [OK] SAC: {len(sac_ts)} hourly records")
    
    # Check for solar and BESS columns
    has_solar = 'solar_kw' in sac_ts.columns
    has_bess = 'bess_power_kw' in sac_ts.columns
    print(f"     - Solar column: {has_solar}")
    print(f"     - BESS column: {has_bess}")
    
    agents_data['SAC'] = {
        'timeseries': sac_ts,
        'days': len(sac_ts) // 24,
        'color': '#1f77b4'
    }

# A2C
a2c_file = Path('outputs/a2c_training/timeseries_a2c.csv')
if a2c_file.exists():
    a2c_ts = pd.read_csv(a2c_file)
    print(f"   [OK] A2C: {len(a2c_ts)} hourly records")
    
    has_solar = 'solar_kw' in a2c_ts.columns
    has_bess = 'bess_power_kw' in a2c_ts.columns
    print(f"     - Solar column: {has_solar}")
    print(f"     - BESS column: {has_bess}")
    
    agents_data['A2C'] = {
        'timeseries': a2c_ts,
        'days': len(a2c_ts) // 24,
        'color': '#2ca02c'
    }

# PPO
ppo_file = Path('outputs/ppo_training/timeseries_ppo.csv')
if ppo_file.exists():
    ppo_ts = pd.read_csv(ppo_file)
    print(f"   [OK] PPO: {len(ppo_ts)} hourly records")
    
    has_solar = 'solar_kw' in ppo_ts.columns
    has_bess = 'bess_power_kw' in ppo_ts.columns
    print(f"     - Solar column: {has_solar}")
    print(f"     - BESS column: {has_bess}")
    
    agents_data['PPO'] = {
        'timeseries': ppo_ts,
        'days': len(ppo_ts) // 24,
        'color': '#ff7f0e'
    }

print()

# ============================================================================
# CALCULATE METRICS FOR EACH AGENT
# ============================================================================

print("🧮 Calculating CO₂ metrics for each agent...\n")

agent_metrics = {}

for agent_name, agent_info in agents_data.items():
    ts = agent_info['timeseries']
    n_days = agent_info['days']
    
    daily_metrics = {
        'day': [],
        'consumption': [],           # Grid import (kWh/day)
        'cost': [],                  # Operating cost (USD/day)
        'solar_generated': [],       # Solar generation (kWh/day)
        'bess_dispatched': [],       # BESS discharge (kWh/day)
        'co2_direct': [],            # From chargers data (kg/day)
        'co2_indirect': [],          # From solar+BESS (kg/day)
        'peak_load': [],             # Peak grid demand (kW)
        'ramping': []                # Power ramping (kW/step)
    }
    
    for day_idx in range(min(n_days, len(chargers_daily))):
        start = day_idx * 24
        end = start + 24
        
        # Make sure we have the data
        if end > len(ts):
            break
        
        day_ts = ts.iloc[start:end]
        
        # Grid consumption
        if 'grid_import_kw' in ts.columns:
            grid_import = pd.to_numeric(day_ts['grid_import_kw'], errors='coerce').fillna(0).values
        elif 'grid_import_kwh' in ts.columns:
            grid_import = pd.to_numeric(day_ts['grid_import_kwh'], errors='coerce').fillna(0).values
        else:
            grid_import = np.zeros(24)
        
        consumption = float(grid_import.sum())
        cost = consumption * 0.15  # €0.15/kWh
        
        # Solar generation
        if 'solar_kw' in ts.columns:
            solar_gen = pd.to_numeric(day_ts['solar_kw'], errors='coerce').fillna(0).values
        else:
            solar_gen = np.zeros(24)
        
        solar_energy = float(solar_gen.sum())
        
        # BESS discharge (only positive = discharge)
        if 'bess_power_kw' in ts.columns:
            bess_power = pd.to_numeric(day_ts['bess_power_kw'], errors='coerce').fillna(0).values
            # Only count discharge (positive values)
            bess_discharge = float(np.sum(bess_power[bess_power > 0]))
        else:
            bess_discharge = 0.0
        
        # CO₂ DIRECT: From chargers data (quantity of vehicles)
        if day_idx < len(chargers_daily):
            co2_direct = float(chargers_daily.iloc[day_idx]['co2_direct'])
        else:
            co2_direct = 0.0
        
        # CO₂ INDIRECT: Clean energy used for EVs
        clean_energy = solar_energy + bess_discharge  # kWh that doesn't come from diesel
        co2_indirect = clean_energy * CO2_THERMAL_FACTOR  # kg CO₂ avoided
        
        # Peak load and ramping
        peak_load = float(grid_import.max())
        if len(grid_import) > 1:
            ravging_values = np.abs(np.diff(grid_import))
            avg_ramping = float(np.mean(ravging_values))
        else:
            avg_ramping = 0.0
        
        daily_metrics['day'].append(day_idx + 1)
        daily_metrics['consumption'].append(consumption)
        daily_metrics['cost'].append(cost)
        daily_metrics['solar_generated'].append(solar_energy)
        daily_metrics['bess_dispatched'].append(bess_discharge)
        daily_metrics['co2_direct'].append(co2_direct)
        daily_metrics['co2_indirect'].append(co2_indirect)
        daily_metrics['peak_load'].append(peak_load)
        daily_metrics['ramping'].append(avg_ramping)
    
    daily_df = pd.DataFrame(daily_metrics)
    agent_metrics[agent_name] = {
        'daily': daily_df,
        'color': agent_info['color'],
        'days': len(daily_df)
    }
    
    print(f"   [OK] {agent_name}: {len(daily_df)} days processed")
    if len(daily_df) > 0:
        print(f"     - CO₂ Direct avg: {daily_df['co2_direct'].mean():.2f} kg/day")
        print(f"     - CO₂ Indirect avg: {daily_df['co2_indirect'].mean():.2f} kg/day")
        print(f"     - Clean energy avg: {(daily_df['solar_generated'].mean() + daily_df['bess_dispatched'].mean()):.2f} kWh/day")
    print()

# ============================================================================
# GENERATE INDIVIDUAL 5-METRIC GRAPHS
# ============================================================================

print("🎨 Generating individual 5-metric graphs...\n")

for agent_name, agent_data in agent_metrics.items():
    daily_df = agent_data['daily']
    color = agent_data['color']
    
    if len(daily_df) < 10:
        print(f"   [!] {agent_name}: Insufficient data ({len(daily_df)} days)")
        continue
    
    # Calculate trends (first 10% vs last 10%)
    n_period = max(int(len(daily_df) * 0.1), 7)
    initial = daily_df.iloc[:n_period]
    final = daily_df.iloc[-n_period:]
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)
    
    # 1. Consumption
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(daily_df['day'], daily_df['consumption'], color=color, linewidth=2.5, alpha=0.8)
    ax.fill_between(daily_df['day'], daily_df['consumption'], alpha=0.15, color=color)
    trend = daily_df['consumption'].rolling(30, center=True).mean()
    ax.plot(daily_df['day'], trend, 'k--', linewidth=2, alpha=0.5)
    cons_change = ((initial['consumption'].mean() - final['consumption'].mean()) / initial['consumption'].mean() * 100)
    ax.set_ylabel('kWh/day', fontsize=11, fontweight='bold')
    ax.set_title(f'Grid Consumption\n({cons_change:+.1f}%)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 2. Cost
    ax = fig.add_subplot(gs[0, 1])
    ax.plot(daily_df['day'], daily_df['cost'], color=color, linewidth=2.5, alpha=0.8)
    ax.fill_between(daily_df['day'], daily_df['cost'], alpha=0.15, color=color)
    trend = daily_df['cost'].rolling(30, center=True).mean()
    ax.plot(daily_df['day'], trend, 'k--', linewidth=2, alpha=0.5)
    cost_change = ((initial['cost'].mean() - final['cost'].mean()) / initial['cost'].mean() * 100)
    ax.set_ylabel('USD/day', fontsize=11, fontweight='bold')
    ax.set_title(f'Operating Cost\n({cost_change:+.1f}%)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 3. CO₂ DIRECT (from modal shift: motos/mototaxis fuel -> electric)
    ax = fig.add_subplot(gs[0, 2])
    ax.plot(daily_df['day'], daily_df['co2_direct'], color='darkred', linewidth=2.5, alpha=0.85)
    ax.fill_between(daily_df['day'], daily_df['co2_direct'], alpha=0.2, color='red')
    trend = daily_df['co2_direct'].rolling(30, center=True).mean()
    ax.plot(daily_df['day'], trend, color='darkred', linewidth=2.5, linestyle='--', alpha=0.7)
    direct_change = ((initial['co2_direct'].mean() - final['co2_direct'].mean()) / (initial['co2_direct'].mean() + 0.001) * 100)
    ax.set_ylabel('kg CO₂/day', fontsize=11, fontweight='bold')
    ax.set_title(f'🔴 CO₂ DIRECT\n(Vehicle Modal Shift)\n({direct_change:+.1f}%)',
                 fontsize=11, fontweight='bold', 
                 bbox=dict(boxstyle='round', facecolor='#FFE6E6', alpha=0.9))
    ax.grid(True, alpha=0.3)
    
    # 4. CO₂ INDIRECT (from SOLAR + BESS avoiding grid diesel)
    ax = fig.add_subplot(gs[1, 0])
    ax.plot(daily_df['day'], daily_df['co2_indirect'], color='darkgreen', linewidth=2.5, alpha=0.85)
    ax.fill_between(daily_df['day'], daily_df['co2_indirect'], alpha=0.2, color='green')
    trend = daily_df['co2_indirect'].rolling(30, center=True).mean()
    ax.plot(daily_df['day'], trend, color='darkgreen', linewidth=2.5, linestyle='--', alpha=0.7)
    indirect_change = ((initial['co2_indirect'].mean() - final['co2_indirect'].mean()) / (initial['co2_indirect'].mean() + 0.001) * 100)
    ax.set_ylabel('kg CO₂/day', fontsize=11, fontweight='bold')
    ax.set_title(f'🟢 CO₂ INDIRECT\n(SOLAR + BESS Clean Energy)\n({indirect_change:+.1f}%)',
                 fontsize=11, fontweight='bold',
                 bbox=dict(boxstyle='round', facecolor='#E6FFE6', alpha=0.9))
    ax.set_xlabel('Training Day', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 5. Power Ramping (Stability)
    ax = fig.add_subplot(gs[1, 1])
    ax.plot(daily_df['day'], daily_df['ramping'], color='darkblue', linewidth=2.5, alpha=0.8)
    ax.fill_between(daily_df['day'], daily_df['ramping'], alpha=0.15, color='blue')
    trend = daily_df['ramping'].rolling(30, center=True).mean()
    ax.plot(daily_df['day'], trend, 'k--', linewidth=2, alpha=0.5)
    ramp_change = ((initial['ramping'].mean() - final['ramping'].mean()) / (initial['ramping'].mean() + 0.001) * 100)
    ax.set_ylabel('kW/step', fontsize=11, fontweight='bold')
    ax.set_title(f'Ramping (Stability)\n({ramp_change:+.1f}%)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Training Day', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 6. Summary
    ax = fig.add_subplot(gs[1, 2])
    ax.axis('off')
    
    total_co2 = daily_df['co2_direct'].sum() + daily_df['co2_indirect'].sum()
    clean_energy_total = daily_df['solar_generated'].sum() + daily_df['bess_dispatched'].sum()
    
    summary_text = f"""{agent_name} TRAINING SUMMARY
Days: {agent_data['days']}

CONSUMPTION:
  {initial['consumption'].mean():.0f} -> {final['consumption'].mean():.0f} kWh/day
  {cons_change:+.1f}%

COST:
  ${initial['cost'].mean():.0f} -> ${final['cost'].mean():.0f}/day
  {cost_change:+.1f}%

CO₂ DIRECT (Modal Shift):
  {initial['co2_direct'].mean():.1f} -> {final['co2_direct'].mean():.1f} kg/day
  {direct_change:+.1f}%

CO₂ INDIRECT (SOLAR+BESS):
  {initial['co2_indirect'].mean():.1f} -> {final['co2_indirect'].mean():.1f} kg/day
  {indirect_change:+.1f}%

CLEAN ENERGY USED:
  {daily_df['solar_generated'].sum() / 1000:.1f}k + {daily_df['bess_dispatched'].sum() / 1000:.1f}k = {clean_energy_total / 1000:.1f}k kWh

TOTAL CO₂ AVOIDED:
  {total_co2:.0f} kg
  ({(total_co2 / 365):.1f} kg/day avg)"""
    
    ax.text(0.05, 0.95, summary_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor=color, alpha=0.15))
    
    fig.suptitle(f'{agent_name}: 5-Metric Evolution with CORRECT CO₂ Calculation\nDirect (Modal Shift) + Indirect (SOLAR+BESS)',
                 fontsize=14, fontweight='bold', y=0.995)
    
    output_file = OUTPUT_DIR / f'{agent_name.lower()}_5metrics_CO2correct.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"   [OK] Saved: {agent_name.lower()}_5metrics_CO2correct.png")
    plt.close()

print()

# ============================================================================
# GENERATE 3-AGENT COMPARISON
# ============================================================================

print("[GRAPH] Generating 3-agent comparison dashboard...\n")

fig = plt.figure(figsize=(20, 12))
gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.28)

# Prepare comparison data
comparison_metrics = {}
for agent_name, agent_data in agent_metrics.items():
    daily_df = agent_data['daily']
    if len(daily_df) < 10:
        continue
    
    n_period = max(int(len(daily_df) * 0.1), 7)
    initial = daily_df.iloc[:n_period]
    final = daily_df.iloc[-n_period:]
    
    comparison_metrics[agent_name] = {
        'color': agent_data['color'],
        'consumption': ((initial['consumption'].mean() - final['consumption'].mean()) / initial['consumption'].mean() * 100),
        'cost': ((initial['cost'].mean() - final['cost'].mean()) / initial['cost'].mean() * 100),
        'co2_direct': ((initial['co2_direct'].mean() - final['co2_direct'].mean()) / (initial['co2_direct'].mean() + 0.001) * 100),
        'co2_indirect': ((initial['co2_indirect'].mean() - final['co2_indirect'].mean()) / (initial['co2_indirect'].mean() + 0.001) * 100),
        'ramping': ((initial['ramping'].mean() - final['ramping'].mean()) / (initial['ramping'].mean() + 0.001) * 100),
    }

agents_list = list(comparison_metrics.keys())
colors = [comparison_metrics[a]['color'] for a in agents_list]

# Graph 1: Consumption
ax = fig.add_subplot(gs[0, 0])
vals = [comparison_metrics[a]['consumption'] for a in agents_list]
bars = ax.bar(agents_list, vals, color=colors, alpha=0.75, edgecolor='black', linewidth=2)
ax.axhline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
ax.set_ylabel('Reduction %', fontsize=11, fontweight='bold')
ax.set_title('Consumption\nReduction', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (max(vals)*0.02), f'{val:+.1f}%',
            ha='center', va='bottom', fontweight='bold', fontsize=10)

# Graph 2: Cost
ax = fig.add_subplot(gs[0, 1])
vals = [comparison_metrics[a]['cost'] for a in agents_list]
bars = ax.bar(agents_list, vals, color=colors, alpha=0.75, edgecolor='black', linewidth=2)
ax.axhline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
ax.set_ylabel('Reduction %', fontsize=11, fontweight='bold')
ax.set_title('Cost\nReduction', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (max(vals)*0.02), f'{val:+.1f}%',
            ha='center', va='bottom', fontweight='bold', fontsize=10)

# Graph 3: CO₂ DIRECT (Modal Shift)
ax = fig.add_subplot(gs[0, 2])
vals = [comparison_metrics[a]['co2_direct'] for a in agents_list]
bars = ax.bar(agents_list, vals, color=colors, alpha=0.85, edgecolor='darkred', linewidth=3)
ax.axhline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
ax.set_ylabel('Change %', fontsize=11, fontweight='bold')
ax.set_title('🔴 CO₂ DIRECT\n(Vehicle Modal Shift)',
             fontsize=12, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='#FFE6E6', alpha=0.9))
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, vals):
    y_pos = bar.get_height() + (max(vals)*0.02 if val > 0 else -max(vals)*0.05)
    ax.text(bar.get_x() + bar.get_width()/2, y_pos, f'{val:+.1f}%',
            ha='center', va='bottom' if val > 0 else 'top', fontweight='bold', fontsize=11, color='darkred')

# Graph 4: CO₂ INDIRECT (SOLAR + BESS)
ax = fig.add_subplot(gs[1, 0])
vals = [comparison_metrics[a]['co2_indirect'] for a in agents_list]
bars = ax.bar(agents_list, vals, color=colors, alpha=0.85, edgecolor='darkgreen', linewidth=3)
ax.axhline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
ax.set_ylabel('Change %', fontsize=11, fontweight='bold')
ax.set_title('🟢 CO₂ INDIRECT\n(SOLAR + BESS Clean Energy)',
             fontsize=12, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='#E6FFE6', alpha=0.9))
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, vals):
    y_pos = bar.get_height() + (max(vals)*0.02 if val > 0 else -max(vals)*0.05)
    ax.text(bar.get_x() + bar.get_width()/2, y_pos, f'{val:+.1f}%',
            ha='center', va='bottom' if val > 0 else 'top', fontweight='bold', fontsize=11, color='darkgreen')

# Graph 5: Ramping
ax = fig.add_subplot(gs[1, 1])
vals = [comparison_metrics[a]['ramping'] for a in agents_list]
bars = ax.bar(agents_list, vals, color=colors, alpha=0.75, edgecolor='black', linewidth=2)
ax.axhline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
ax.set_ylabel('Reduction %', fontsize=11, fontweight='bold')
ax.set_title('Ramping\nReduction', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (max(vals)*0.02), f'{val:+.1f}%',
            ha='center', va='bottom', fontweight='bold', fontsize=10)

# Graph 6: TOTAL CO₂ (Both Direct + Indirect)
ax = fig.add_subplot(gs[1, 2])
direct_vals = [comparison_metrics[a]['co2_direct'] for a in agents_list]
indirect_vals = [comparison_metrics[a]['co2_indirect'] for a in agents_list]
total_vals = [(d + i) / 2 for d, i in zip(direct_vals, indirect_vals)]

x = np.arange(len(agents_list))
width = 0.35

bars1 = ax.bar(x - width/2, direct_vals, width, label='Direct', color='darkred', alpha=0.65, edgecolor='black')
bars2 = ax.bar(x + width/2, indirect_vals, width, label='Indirect', color='darkgreen', alpha=0.65, edgecolor='black')

ax.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)
ax.set_ylabel('Change %', fontsize=11, fontweight='bold')
ax.set_title('⭐ TOTAL CO₂ REDUCTION\n(Direct + Indirect)',
             fontsize=12, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='#E6D9FF', alpha=0.9))
ax.set_xticks(x)
ax.set_xticklabels(agents_list)
ax.legend(loc='best', fontsize=10)
ax.grid(axis='y', alpha=0.3)

# Add values on bars
for bar in bars1:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height + 1, f'{height:+.1f}%',
            ha='center', va='bottom', fontsize=9, color='darkred')
for bar in bars2:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height + 1, f'{height:+.1f}%',
            ha='center', va='bottom', fontsize=9, color='darkgreen')

fig.suptitle('3-AGENT COMPARISON: 5-METRIC ANALYSIS with CORRECT CO₂\nDirect (Modal Shift) vs Indirect (SOLAR+BESS Clean Energy)',
             fontsize=15, fontweight='bold', y=0.995)

output_file = OUTPUT_DIR / 'COMPARISON_3agents_CO2correct.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
print(f"   [OK] Saved: COMPARISON_3agents_CO2correct.png\n")
plt.close()

# ============================================================================
# SUMMARY TABLE
# ============================================================================

print("[GRAPH] COMPARATIVE METRICS SUMMARY:\n")

summary_rows = []
for agent in agents_list:
    metrics = comparison_metrics[agent]
    total_co2 = (metrics['co2_direct'] + metrics['co2_indirect']) / 2
    summary_rows.append({
        'Agent': agent,
        'Consumption': f"{metrics['consumption']:+.1f}%",
        'Cost': f"{metrics['cost']:+.1f}%",
        'CO₂ Direct': f"{metrics['co2_direct']:+.1f}%",
        'CO₂ Indirect': f"{metrics['co2_indirect']:+.1f}%",
        'Avg Total': f"{total_co2:+.1f}%",
        'Ramping': f"{metrics['ramping']:+.1f}%"
    })

summary_df = pd.DataFrame(summary_rows)
print(summary_df.to_string(index=False))

print(f"""
================================================================================
[OK] ANALYSIS COMPLETE with CORRECT CO₂ METHODOLOGY
================================================================================

Generated Files (outputs/comparison_training/):
  [OK] sac_5metrics_CO2correct.png (if SAC data available)
  [OK] a2c_5metrics_CO2correct.png (if A2C data available)
  [OK] ppo_5metrics_CO2correct.png (if PPO data available)
  [OK] COMPARISON_3agents_CO2correct.png

KEY DEFINITIONS USED:

CO₂ DIRECTO (Direct Reduction):
  +- Definition: Emission avoidance from modal shift (fuel motos -> Electric EVs)
  +- Source: reduccion_directa_co2_kg from chargers infrastructure data
  +- Unit: kg CO₂/day
  +- Note: Depends on NUMBER of vehicles charged, not energy consumed

CO₂ INDIRECTO (Indirect Reduction):
  +- Definition: Emission avoidance from clean energy (SOLAR + BESS -> EVs)
  +- Calculation: (Solar_generation + BESS_discharge) × 0.4521 kg CO₂/kWh
  +- Unit: kg CO₂/day
  +- Why: This energy AVOIDS thermal diesel generation from grid
  +- Note: Grid itself is diesel, so clean energy = only way to reduce grid CO₂

Grid & Mall Impact:
  +- Grid + Mall = both connected to thermal (diesel) generation
  +- Grid import ≠ reduce CO₂ (just shifts/delays thermal burn)
  +- ONLY SOLAR + BESS reduce actual CO₂ by avoiding thermal entirely

================================================================================
""")
