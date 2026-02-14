#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate complete SAC KPI Dashboard from real timeseries data.

This script extracts real metrics from SAC training outputs:
- timeseries_sac.csv (hourly data)
- result_sac.json (episode summaries)

Generates 6-panel KPI dashboard with:
1. Net Electricity Consumption (kWh/day)
2. Cost (USD/day) 
3. Carbon Emissions (kg CO2/day)
4. Ramping (kW avg)
5. Daily Peak (kW)
6. (1 - Load Factor)
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Tuple
import seaborn as sns

# Configure styling
sns.set_style("whitegrid")
plt.rcParams['font.size'] = 10
plt.rcParams['figure.facecolor'] = 'white'


class SACKPIDashboardGenerator:
    """Generate KPI dashboard from SAC training data."""
    
    def __init__(self, sac_training_dir: Path = Path('outputs/sac_training')):
        """Initialize with SAC training directory."""
        self.sac_dir = Path(sac_training_dir)
        self.timeseries_file = self.sac_dir / 'timeseries_sac.csv'
        self.result_file = self.sac_dir / 'result_sac.json'
        
        self.df_timeseries = None
        self.result_json = None
        
    def load_data(self) -> bool:
        """Load timeseries and result data."""
        try:
            # Load timeseries
            if not self.timeseries_file.exists():
                print(f"❌ Timeseries file not found: {self.timeseries_file}")
                return False
            
            print(f"📥 Loading timeseries: {self.timeseries_file.name}")
            self.df_timeseries = pd.read_csv(self.timeseries_file)
            print(f"   ✓ Loaded {len(self.df_timeseries)} hourly records")
            
            # Load result JSON
            if self.result_file.exists():
                print(f"📥 Loading results: {self.result_file.name}")
                with open(self.result_file, 'r') as f:
                    self.result_json = json.load(f)
                print(f"   ✓ Loaded {self.result_json.get('episodes_completed', 0)} episodes")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def aggregate_by_day(self) -> Dict[str, List[float]]:
        """
        Aggregate hourly timeseries data by day (24-hour periods).
        
        Returns dict with daily aggregations:
        - net_consumption_kwh
        - cost_usd
        - co2_emissions_kg
        - peak_load_kw
        - avg_load_kw
        - ramping_kw
        """
        
        print("\n📊 Aggregating hourly data to daily metrics...")
        
        daily_metrics = {
            'net_consumption_kwh': [],
            'cost_usd': [],
            'co2_emissions_kg': [],
            'peak_load_kw': [],
            'avg_load_kw': [],
            'ramping_kw': [],
            'days': []
        }
        
        # Group by day (every 24 hours)
        num_days = len(self.df_timeseries) // 24
        
        for day_idx in range(num_days):
            start_hour = day_idx * 24
            end_hour = start_hour + 24
            
            day_slice = self.df_timeseries.iloc[start_hour:end_hour]
            
            if len(day_slice) < 24:
                continue
            
            # 1. Net consumption = sum(grid_import_kw) * 1h - grid_export
            try:
                grid_import = pd.to_numeric(day_slice['grid_import_kw'], errors='coerce').fillna(0)
                grid_export = pd.to_numeric(day_slice['grid_export_kw'], errors='coerce').fillna(0) if 'grid_export_kw' in day_slice.columns else pd.Series([0.0]*len(day_slice))
                net_consumption = (grid_import.sum() - float(grid_export.sum()))
                daily_metrics['net_consumption_kwh'].append(max(0, net_consumption))
            except Exception as e:
                daily_metrics['net_consumption_kwh'].append(0.0)
            
            # 2. Cost = grid_import * cost_factor (€0.15/kWh)
            # or extract from 'cost_eur' or 'cost_usd' if available
            try:
                if 'cost_eur' in day_slice.columns:
                    cost = pd.to_numeric(day_slice['cost_eur'], errors='coerce').sum()
                elif 'cost_usd' in day_slice.columns:
                    cost = pd.to_numeric(day_slice['cost_usd'], errors='coerce').sum()
                else:
                    # Estimate: grid_import * 0.15 EUR/kWh
                    cost = grid_import.sum() * 0.15
                daily_metrics['cost_usd'].append(max(0, cost))
            except:
                daily_metrics['cost_usd'].append(0.0)
            
            # 3. CO2 emissions = grid_import * 0.4521 kg/kWh (Iquitos grid)
            try:
                if 'co2_kg' in day_slice.columns:
                    co2 = pd.to_numeric(day_slice['co2_kg'], errors='coerce').sum()
                else:
                    # Estimate: grid_import * 0.4521 kg CO2/kWh
                    co2 = grid_import.sum() * 0.4521
                daily_metrics['co2_emissions_kg'].append(max(0, co2))
            except:
                daily_metrics['co2_emissions_kg'].append(0.0)
            
            # 4. Daily peak load (kW)
            try:
                load_kw = pd.to_numeric(day_slice['grid_import_kw'], errors='coerce').fillna(0)
                peak = float(load_kw.max())
                daily_metrics['peak_load_kw'].append(peak)
            except:
                daily_metrics['peak_load_kw'].append(0.0)
            
            # 5. Average load (kW) for load factor
            try:
                avg_load = load_kw.mean()
                daily_metrics['avg_load_kw'].append(avg_load)
            except:
                daily_metrics['avg_load_kw'].append(0.0)
            
            # 6. Ramping = mean|load[t] - load[t-1]|
            try:
                diffs = load_kw.diff().abs()
                ramping = diffs.mean()
                daily_metrics['ramping_kw'].append(ramping)
            except:
                daily_metrics['ramping_kw'].append(0.0)
            
            daily_metrics['days'].append(day_idx + 1)
        
        print(f"   ✓ Aggregated to {len(daily_metrics['days'])} days")
        
        # Check if we have enough data
        if len(daily_metrics['days']) == 0:
            print("   ⚠️  No daily data could be aggregated!")
            return None
        
        return daily_metrics
    
    def smooth(self, values: List[float], window: int = 5) -> List[float]:
        """Apply simple moving average smoothing."""
        if len(values) < window:
            return values
        s = pd.Series(values)
        return s.rolling(window=window, center=True, min_periods=1).mean().tolist()
    
    def generate_dashboard(self, daily_metrics: Dict) -> bool:
        """Generate 6-panel KPI dashboard."""
        
        print("\n📈 Generating KPI Dashboard (2×3 layout)...")
        
        if not daily_metrics or len(daily_metrics['days']) == 0:
            print("❌ No daily metrics available for dashboard")
            return False
        
        try:
            # Create figure with 2x3 subplots
            fig, axes = plt.subplots(2, 3, figsize=(16, 10))
            fig.patch.set_facecolor('white')
            
            days = np.array(daily_metrics['days'])
            
            # Color scheme
            colors = {
                'consumption': '#1f77b4',      # Blue
                'cost': '#2ca02c',              # Green
                'emissions': '#d62728',         # Red
                'ramping': '#9467bd',           # Purple
                'peak': '#ff7f0e',              # Orange
                'load_factor': '#8c564b'        # Brown
            }
            
            # ===== ROW 1: Main KPIs =====
            
            # 1. Net Consumption (kWh/day)
            ax = axes[0, 0]
            consumption = daily_metrics['net_consumption_kwh']
            consumption_smooth = self.smooth(consumption)
            ax.plot(days, consumption_smooth, color=colors['consumption'], linewidth=2.5, label='Net Consumption')
            ax.fill_between(days, consumption_smooth, alpha=0.2, color=colors['consumption'])
            ax.set_title('Net Electricity Consumption', fontsize=12, fontweight='bold')
            ax.set_xlabel('Day')
            ax.set_ylabel('kWh/day')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_ylim(bottom=0)
            
            # Add improvement annotation
            if len(consumption) > 1:
                improvement = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}%',
                           xy=(0.98, 0.05), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right', fontweight='bold')
            
            # 2. Cost (USD/day)
            ax = axes[0, 1]
            cost = daily_metrics['cost_usd']
            cost_smooth = self.smooth(cost)
            ax.plot(days, cost_smooth, color=colors['cost'], linewidth=2.5)
            ax.fill_between(days, cost_smooth, alpha=0.2, color=colors['cost'])
            ax.set_title('Electricity Cost', fontsize=12, fontweight='bold')
            ax.set_xlabel('Day')
            ax.set_ylabel('USD/day')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_ylim(bottom=0)
            
            if len(cost) > 1:
                improvement = (cost[0] - cost[-1]) / max(abs(cost[0]), 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}%',
                           xy=(0.98, 0.05), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right', fontweight='bold')
            
            # 3. CO2 Emissions (kg/day)
            ax = axes[0, 2]
            emissions = daily_metrics['co2_emissions_kg']
            emissions_smooth = self.smooth(emissions)
            ax.plot(days, emissions_smooth, color=colors['emissions'], linewidth=2.5)
            ax.fill_between(days, emissions_smooth, alpha=0.2, color=colors['emissions'])
            ax.set_title('Carbon Emissions (CO₂)', fontsize=12, fontweight='bold')
            ax.set_xlabel('Day')
            ax.set_ylabel('kg CO₂/day')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_ylim(bottom=0)
            
            if len(emissions) > 1:
                improvement = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}%',
                           xy=(0.98, 0.05), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right', fontweight='bold')
            
            # ===== ROW 2: Secondary KPIs =====
            
            # 4. Ramping (kW avg)
            ax = axes[1, 0]
            ramping = daily_metrics['ramping_kw']
            ramping_smooth = self.smooth(ramping)
            ax.plot(days, ramping_smooth, color=colors['ramping'], linewidth=2.5)
            ax.fill_between(days, ramping_smooth, alpha=0.2, color=colors['ramping'])
            ax.set_title('Grid Ramping (Load Rate Change)', fontsize=12, fontweight='bold')
            ax.set_xlabel('Day')
            ax.set_ylabel('kW/step')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_ylim(bottom=0)
            
            if len(ramping) > 1:
                improvement = (ramping[0] - ramping[-1]) / max(ramping[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}%',
                           xy=(0.98, 0.05), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right', fontweight='bold')
            
            # 5. Daily Peak (kW)
            ax = axes[1, 1]
            peak = daily_metrics['peak_load_kw']
            peak_smooth = self.smooth(peak)
            ax.plot(days, peak_smooth, color=colors['peak'], linewidth=2.5)
            ax.fill_between(days, peak_smooth, alpha=0.2, color=colors['peak'])
            ax.axhline(y=250, color='red', linestyle='--', alpha=0.5, linewidth=2, label='Peak Limit 250kW')
            ax.set_title('Daily Peak Load', fontsize=12, fontweight='bold')
            ax.set_xlabel('Day')
            ax.set_ylabel('kW')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_ylim(bottom=0)
            ax.legend(loc='upper right', fontsize=9)
            
            if len(peak) > 1:
                improvement = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}%',
                           xy=(0.98, 0.05), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right', fontweight='bold')
            
            # 6. (1 - Load Factor) - Load distribution quality
            ax = axes[1, 2]
            avg_loads = daily_metrics['avg_load_kw']
            peak_loads = daily_metrics['peak_load_kw']
            
            one_minus_lf = []
            for avg, peak in zip(avg_loads, peak_loads):
                lf = avg / max(peak, 0.001)
                one_minus_lf.append(1.0 - lf)
            
            one_minus_lf_smooth = self.smooth(one_minus_lf)
            ax.plot(days, one_minus_lf_smooth, color=colors['load_factor'], linewidth=2.5)
            ax.fill_between(days, one_minus_lf_smooth, alpha=0.2, color=colors['load_factor'])
            ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7, linewidth=2, label='Good Distribution (≤0.3)')
            ax.fill_between(days, 0, 0.3, alpha=0.1, color='green')
            ax.set_title('(1 - Load Factor)\nLower = Better Load Distribution', fontsize=12, fontweight='bold')
            ax.set_xlabel('Day')
            ax.set_ylabel('(1 - LF) Factor')
            ax.set_ylim(0, 1)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.legend(loc='upper right', fontsize=9)
            
            if len(one_minus_lf) > 1:
                improvement = (one_minus_lf[0] - one_minus_lf[-1]) / max(one_minus_lf[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}%',
                           xy=(0.98, 0.05), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right', fontweight='bold')
            
            # ===== Overall Title =====
            
            # Calculate summary improvements for main title
            improvements = []
            if len(consumption) > 1:
                imp = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                if imp > 0:
                    improvements.append(f'Consumption: {imp:.1f}%↓')
            
            if len(emissions) > 1:
                imp = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'CO₂: {imp:.1f}%↓')
            
            if len(peak) > 1:
                imp = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'Peak: {imp:.1f}%↓')
            
            title = 'CityLearn v2 - SAC Agent KPI Dashboard (Real Metrics)'
            if improvements:
                title += f'\n✅ Daily Improvements: {" | ".join(improvements)}'
            
            fig.suptitle(title, fontsize=14, fontweight='bold', y=0.995)
            plt.tight_layout(rect=[0, 0, 1, 0.97])
            
            # Save
            output_path = self.sac_dir / 'kpi_dashboard.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"   ✅ Saved: {output_path.name}")
            
            plt.close(fig)
            
            # Print summary statistics
            print("\n📊 KPI Summary Statistics:")
            print(f"   Consumption:   {consumption[0]:.1f} → {consumption[-1]:.1f} kWh/day")
            print(f"   Cost:          {cost[0]:.1f} → {cost[-1]:.1f} USD/day")
            print(f"   CO₂ Emissions: {emissions[0]:.1f} → {emissions[-1]:.1f} kg/day")
            print(f"   Peak Load:     {peak[0]:.1f} → {peak[-1]:.1f} kW")
            print(f"   Ramping:       {ramping[0]:.2f} → {ramping[-1]:.2f} kW/step")
            print(f"   Load Factor:   {one_minus_lf[0]:.3f} → {one_minus_lf[-1]:.3f}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error generating dashboard: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run(self) -> bool:
        """Run complete pipeline."""
        print("=" * 70)
        print("🔴 SAC KPI DASHBOARD GENERATOR (Real Timeseries Data)")
        print("=" * 70)
        
        # Load data
        if not self.load_data():
            return False
        
        # Aggregate by day
        daily_metrics = self.aggregate_by_day()
        if daily_metrics is None:
            return False
        
        # Generate dashboard
        if not self.generate_dashboard(daily_metrics):
            return False
        
        print("\n" + "=" * 70)
        print("✅ KPI DASHBOARD GENERATION COMPLETE")
        print("=" * 70)
        return True


def main():
    """Main entry point."""
    generator = SACKPIDashboardGenerator()
    success = generator.run()
    exit(0 if success else 1)


if __name__ == '__main__':
    main()
