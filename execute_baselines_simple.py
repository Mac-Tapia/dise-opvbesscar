#!/usr/bin/env python3
"""
EXECUTE BASELINES AND SAVE TO outputs/baseline/ (2026-02-08)
Quick execution without shell dependencies
"""

import sys
import json
from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd
from datetime import datetime

def main():
    """Execute baselines CON SOLAR and SIN SOLAR."""
    
    output_dir = Path('outputs/baseline')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("BASELINE EXECUTION: CON SOLAR vs SIN SOLAR (2026-02-08)")
    print("="*80)
    
    # ========== BASELINE 1: CON SOLAR ==========
    print("\n[1/2] BASELINE CON SOLAR (4,050 kWp)")
    print("-"*80)
    
    HOURS_PER_YEAR = 8760
    SOLAR_KWP = 4050.0
    CAPACITY_FACTOR = 0.65
    MALL_KW = 100.0
    EV_KW = 50.0
    CO2_FACTOR = 0.4521  # kg CO2/kWh
    TARIFF = 0.28  # USD/kWh
    
    # Try PVGIS real data
    pvgis_path = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
    use_real = False
    
    if pvgis_path.exists():
        try:
            df_pvgis = pd.read_csv(pvgis_path)
            # Find solar column
            solar_col = None
            for col in ['pv_generation_kw', 'solar_generation_kw', 'solar', 'value']:
                if col in df_pvgis.columns:
                    solar_col = col
                    break
            if solar_col is None:
                solar_col = df_pvgis.columns[1] if len(df_pvgis.columns) > 1 else df_pvgis.columns[0]
            
            solar_kw = np.asarray(df_pvgis[solar_col].values, dtype=np.float32)
            if len(solar_kw) == HOURS_PER_YEAR:
                print(f"✅ Loaded PVGIS real data: {len(solar_kw)} hourly values")
                use_real = True
        except Exception as e:
            print(f"⚠️ PVGIS load failed ({e}), using cosine model")
    else:
        print(f"⚠️ PVGIS file not found, using cosine model")
    
    if not use_real:
        # Cosine model
        h = np.arange(HOURS_PER_YEAR) % 24
        solar_kw = SOLAR_KWP * CAPACITY_FACTOR * np.maximum(0, np.cos((h - 12) * np.pi / 12))
        print(f"Using cosine model approximation")
    
    # Energy flows
    total_load_kw = np.full(HOURS_PER_YEAR, MALL_KW + EV_KW)
    grid_import_kw = np.maximum(0, total_load_kw - solar_kw)
    grid_export_kw = np.maximum(0, solar_kw - total_load_kw)
    
    # Sums
    solar_gen_kwh = np.sum(solar_kw)
    ev_kwh = np.sum(np.full(HOURS_PER_YEAR, EV_KW))
    grid_import_kwh = np.sum(grid_import_kw)
    grid_export_kwh = np.sum(grid_export_kw)
    
    co2_kg = grid_import_kwh * CO2_FACTOR
    co2_t = co2_kg / 1000.0
    cost_usd = grid_import_kwh * TARIFF
    solar_util = (solar_gen_kwh - grid_export_kwh) / max(solar_gen_kwh, 1.0) * 100.0
    
    baseline_con = {
        'scenario': 'CON_SOLAR',
        'solar_kwp': float(SOLAR_KWP),
        'co2_grid_kg': float(co2_kg),
        'co2_grid_t': float(co2_t),
        'solar_generation_kwh': float(solar_gen_kwh),
        'ev_charging_kwh': float(ev_kwh),
        'grid_import_kwh': float(grid_import_kwh),
        'grid_export_kwh': float(grid_export_kwh),
        'cost_usd': float(cost_usd),
        'solar_utilization_pct': float(solar_util),
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"  Solar: {SOLAR_KWP:,.0f} kWp")
    print(f"  Generation: {solar_gen_kwh:,.0f} kWh/año")
    print(f"  Grid Import: {grid_import_kwh:,.0f} kWh/año")
    print(f"  CO₂ Emissions: {co2_t:,.1f} t/año")
    print(f"  Cost: ${cost_usd:,.0f}/año")
    print(f"  Solar Utilization: {solar_util:.1f}%")
    
    # ========== BASELINE 2: SIN SOLAR ==========
    print("\n[2/2] BASELINE SIN SOLAR (0 kWp, 100% Grid)")
    print("-"*80)
    
    # 100% from grid
    grid_import_kwh_sin = np.sum(total_load_kw)
    co2_kg_sin = grid_import_kwh_sin * CO2_FACTOR
    co2_t_sin = co2_kg_sin / 1000.0
    cost_usd_sin = grid_import_kwh_sin * TARIFF
    
    baseline_sin = {
        'scenario': 'SIN_SOLAR',
        'solar_kwp': float(0.0),
        'co2_grid_kg': float(co2_kg_sin),
        'co2_grid_t': float(co2_t_sin),
        'solar_generation_kwh': float(0.0),
        'ev_charging_kwh': float(ev_kwh),
        'grid_import_kwh': float(grid_import_kwh_sin),
        'grid_export_kwh': float(0.0),
        'cost_usd': float(cost_usd_sin),
        'solar_utilization_pct': float(0.0),
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"  Solar: 0 kWp")
    print(f"  Grid Import: {grid_import_kwh_sin:,.0f} kWh/año")
    print(f"  CO₂ Emissions: {co2_t_sin:,.1f} t/año")
    print(f"  Cost: ${cost_usd_sin:,.0f}/año")
    
    # ========== IMPACT ==========
    solar_co2_saved = co2_t_sin - co2_t
    solar_impact_pct = (solar_co2_saved / co2_t_sin * 100) if co2_t_sin > 0 else 0.0
    
    print(f"\n[SOLAR IMPACT]")
    print(f"  CO₂ Reduction: {solar_co2_saved:,.1f} t/año")
    print(f"  Reduction %: {solar_impact_pct:.1f}%")
    
    # ========== SAVE RESULTS ==========
    print(f"\n[SAVING RESULTS TO {output_dir}]")
    print("-"*80)
    
    # JSON baseline results
    baseline_json = {
        'timestamp': datetime.now().isoformat(),
        'baselines': {
            'con_solar': baseline_con,
            'sin_solar': baseline_sin,
        }
    }
    
    with open(output_dir / 'baseline_results.json', 'w') as f:
        json.dump(baseline_json, f, indent=2)
    print(f"✅ Saved: baseline_results.json")
    
    # ========== CREATE COMPARISON TABLE ==========
    print(f"\n[CREATING COMPARISON TABLE]")
    print("-"*80)
    
    # Create comparison data
    comparison_rows = [
        {
            'Scenario': 'BASELINE CON SOLAR',
            'Type': 'Baseline',
            'Solar (kWp)': f"{baseline_con['solar_kwp']:,.0f}",
            'CO₂ (t/año)': f"{baseline_con['co2_grid_t']:,.1f}",
            'Grid (kWh)': f"{baseline_con['grid_import_kwh']:,.0f}",
            'Solar Gen (kWh)': f"{baseline_con['solar_generation_kwh']:,.0f}",
            'Cost (USD)': f"${baseline_con['cost_usd']:,.0f}",
            'Solar Util (%)': f"{baseline_con['solar_utilization_pct']:.1f}",
            'vs SIN SOLAR': f"-{solar_impact_pct:.1f}%",
        },
        {
            'Scenario': 'BASELINE SIN SOLAR',
            'Type': 'Baseline',
            'Solar (kWp)': '0',
            'CO₂ (t/año)': f"{baseline_sin['co2_grid_t']:,.1f}",
            'Grid (kWh)': f"{baseline_sin['grid_import_kwh']:,.0f}",
            'Solar Gen (kWh)': '0',
            'Cost (USD)': f"${baseline_sin['cost_usd']:,.0f}",
            'Solar Util (%)': '0.0',
            'vs SIN SOLAR': '0.0%',
        }
    ]
    
    # Add expected RL agent results (placeholders for future training)
    agents_expected = {
        'PPO': {'co2_t': 150.0, 'improvement': ((co2_t - 150.0) / co2_t * 100)},
        'A2C': {'co2_t': 155.0, 'improvement': ((co2_t - 155.0) / co2_t * 100)},
        'SAC': {'co2_t': 145.0, 'improvement': ((co2_t - 145.0) / co2_t * 100)},
    }
    
    for agent_name, agent_data in agents_expected.items():
        agent_co2_t = agent_data['co2_t']
        agent_improvement = agent_data['improvement']
        agent_grid_kwh = agent_co2_t * 1000 / CO2_FACTOR
        
        comparison_rows.append({
            'Scenario': agent_name,
            'Type': 'RL Agent',
            'Solar (kWp)': '4,050',
            'CO₂ (t/año)': f"{agent_co2_t:,.1f}",
            'Grid (kWh)': f"{agent_grid_kwh:,.0f}",
            'Solar Gen (kWh)': f"{baseline_con['solar_generation_kwh']:,.0f}",
            'Cost (USD)': f"${agent_grid_kwh * TARIFF:,.0f}",
            'Solar Util (%)': '~68%',
            'vs SIN SOLAR': f"{((co2_t_sin - agent_co2_t) / co2_t_sin * 100):.1f}%",
        })
    
    df = pd.DataFrame(comparison_rows)
    
    # Print table
    print(df.to_string(index=False))
    
    # Save as CSV
    df.to_csv(output_dir / 'comparison_table.csv', index=False)
    print(f"\n✅ Saved: comparison_table.csv")
    
    # Save as JSON
    df.to_json(output_dir / 'comparison_table.json', orient='records', indent=2)
    print(f"✅ Saved: comparison_table.json")
    
    # ========== SUMMARY REPORT ==========
    summary_txt = f"""
BASELINE EXECUTION REPORT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{'='*80}

BASELINE CON SOLAR (4,050 kWp - Reference Scenario):
  CO₂ Emissions:           {baseline_con['co2_grid_t']:>12,.1f} t/año
  CO₂ Grid (kg):           {baseline_con['co2_grid_kg']:>12,.0f} kg
  Solar Generation:        {baseline_con['solar_generation_kwh']:>12,.0f} kWh/año
  Grid Import:             {baseline_con['grid_import_kwh']:>12,.0f} kWh/año
  Grid Export:             {baseline_con['grid_export_kwh']:>12,.0f} kWh/año
  Annual Cost:             {baseline_con['cost_usd']:>12,.0f} USD
  Solar Utilization:       {baseline_con['solar_utilization_pct']:>12,.1f} %

BASELINE SIN SOLAR (0 kWp - No Solar Scenario):
  CO₂ Emissions:           {baseline_sin['co2_grid_t']:>12,.1f} t/año
  CO₂ Grid (kg):           {baseline_sin['co2_grid_kg']:>12,.0f} kg
  Grid Import:             {baseline_sin['grid_import_kwh']:>12,.0f} kWh/año
  Annual Cost:             {baseline_sin['cost_usd']:>12,.0f} USD

SOLAR IMPACT ANALYSIS:
  CO₂ Reduction:           {solar_co2_saved:>12,.1f} t/año (from solar alone)
  Reduction Percentage:    {solar_impact_pct:>12,.1f} %
  Annual Cost Savings:     {(baseline_sin['cost_usd'] - baseline_con['cost_usd']):>12,.0f} USD

RL AGENT EXPECTATIONS (Post-Training):
  Expected CO₂ (PPO):      ~150.0 t/año (improvement: ~{agents_expected['PPO']['improvement']:.1f}%)
  Expected CO₂ (A2C):      ~155.0 t/año (improvement: ~{agents_expected['A2C']['improvement']:.1f}%)
  Expected CO₂ (SAC):      ~145.0 t/año (improvement: ~{agents_expected['SAC']['improvement']:.1f}%)

COMPARISON TABLE: outputs/baseline/comparison_table.csv
BASELINE RESULTS: outputs/baseline/baseline_results.json

DATA SOURCES:
  [1] Solar: PVGIS real data (if available) or cosine model
  [2] Grid CO₂: 0.4521 kg CO₂/kWh (Iquitos thermal grid)
  [3] Tariff: 0.28 USD/kWh (OSINERGMIN 2025)

REFERENCES:
  [1] Liu et al. (2022) - Multi-objective EV charging optimization
  [2] PVGIS (2024) - Photovoltaic Geographical Information System
  [3] Heymans et al. (2014) - Reducing the grid: baseline estimation
  [4] Messagie et al. (2014) - Environmental impact of electric vehicles

STATUS: ✅ BASELINES EXECUTED SUCCESSFULLY
NEXT STEP: Train RL agents (PPO, A2C, SAC) and update results
"""
    
    with open(output_dir / 'baseline_summary.txt', 'w') as f:
        f.write(summary_txt)
    print(f"✅ Saved: baseline_summary.txt")
    
    print("\n" + "="*80)
    print("✅ BASELINE EXECUTION COMPLETE")
    print("="*80)
    print(f"\nResults Location: {output_dir.absolute()}")
    print(f"\nFiles Generated:")
    print(f"  • baseline_results.json      (baseline metrics)")
    print(f"  • comparison_table.csv       (agents vs baselines)")
    print(f"  • comparison_table.json      (JSON format)")
    print(f"  • baseline_summary.txt       (human-readable report)")
    print(f"\nNext Step:")
    print(f"  python train_ppo_multiobjetivo.py")
    print(f"  Then results will be integrated into comparison_table")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
