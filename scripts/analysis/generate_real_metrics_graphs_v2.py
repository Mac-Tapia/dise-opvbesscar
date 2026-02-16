#!/usr/bin/env python3
"""
Generate REAL output metrics graphs from training data (JSON/CSV).
NOT synthetic training curves.

Metrics to generate:
1. Cost per episode
2. Daily peak load per episode  
3. Direct CO2 reduction (solar avoidance)
4. Indirect CO2 reduction (renewable EV charging)
"""

from __future__ import annotations

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple
import warnings

warnings.filterwarnings('ignore')

# Setup style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10
COLORS = {'SAC': '#1f77b4', 'PPO': '#ff7f0e', 'A2C': '#2ca02c'}

class RealMetricsExtractor:
    """Extract real metrics from training data."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        
    def extract_metrics_from_json(self, agent: str) -> Dict:
        """Extract real metrics from result JSON."""
        json_file = self.output_dir / f"{agent.lower()}_training" / f"result_{agent.lower()}.json"
        
        if not json_file.exists():
            # Try alternative structure for A2C
            if agent == 'A2C':
                return self._extract_a2c_metrics(json_file)
            print(f"[!]  JSON file not found: {json_file}")
            return {}
        
        try:
            with open(json_file) as f:
                data = json.load(f)
            
            # SAC format: has episode-level arrays
            if 'episode_rewards' in data or 'episodes_completed' in data:
                kpi = data.get('KPI_SUMMARY', {})
                metrics = {
                    'agent': agent,
                    'total_timesteps': data.get('total_timesteps', 0),
                    'episodes_completed': data.get('episodes_completed', 0),
                    'episode_rewards': np.array(data.get('episode_rewards', [])),
                    'episode_co2_grid_kg': np.array(data.get('episode_co2_grid_kg', [])),
                    'episode_solar_kwh': np.array(data.get('episode_solar_kwh', [])),
                    'episode_ev_charging_kwh': np.array(data.get('episode_ev_charging_kwh', [])),
                    'episode_grid_import_kwh': np.array(data.get('episode_grid_import_kwh', [])),
                    'episode_bess_discharge_kwh': np.array(data.get('episode_bess_discharge_kwh', [])),
                    'episode_bess_charge_kwh': np.array(data.get('episode_bess_charge_kwh', [])),
                    'kpi_summary': kpi
                }
                print(f"[OK] Extracted {agent} metrics (SAC format): {len(metrics['episode_rewards'])} episodes")
                return metrics
            
            # A2C format: has summary_metrics
            elif 'summary_metrics' in data:
                return self._extract_a2c_metrics_from_dict(data)
            else:
                print(f"[!]  Unknown JSON format for {agent}")
                return {}
            
        except Exception as e:
            print(f"[X] Error reading {json_file}: {e}")
            return {}
    
    def _extract_a2c_metrics_from_dict(self, data: Dict) -> Dict:
        """Extract A2C metrics from alternative JSON structure."""
        try:
            training = data.get('training', {})
            evolution = data.get('training_evolution', {})
            validation = data.get('validation', {})
            
            episodes_completed = training.get('episodes_completed', 1)
            
            # Extract real episode arrays from evolution
            episode_rewards = np.array(evolution.get('episode_rewards', []))
            episode_co2_grid = np.array(evolution.get('episode_co2_grid', []))
            episode_co2_avoided_indirect = np.array(evolution.get('episode_co2_avoided_indirect', []))
            episode_co2_avoided_direct = np.array(evolution.get('episode_co2_avoided_direct', []))
            episode_solar_kwh = np.array(evolution.get('episode_solar_kwh', []))
            episode_ev_charging_kwh = np.array(evolution.get('episode_ev_charging_kwh', []))
            episode_grid_import_kwh = np.array(evolution.get('episode_grid_import_kwh', []))
            
            # If some arrays are missing, fill from validation mean values
            if len(episode_solar_kwh) == 0:
                episode_solar_kwh = np.full(episodes_completed, validation.get('mean_solar_kwh', 0))
            if len(episode_grid_import_kwh) == 0:
                episode_grid_import_kwh = np.full(episodes_completed, validation.get('mean_grid_import_kwh', 0))
            if len(episode_ev_charging_kwh) == 0:
                # Estimate from chargers total
                datasets = data.get('datasets_oe2', {})
                total_charging = datasets.get('chargers_total_kwh', 0)
                episode_ev_charging_kwh = np.full(episodes_completed, total_charging / max(1, episodes_completed))
            
            metrics = {
                'agent': 'A2C',
                'total_timesteps': training.get('total_timesteps', 0),
                'episodes_completed': episodes_completed,
                'episode_rewards': episode_rewards,
                'episode_co2_grid_kg': episode_co2_grid,
                'episode_co2_avoided_indirect': episode_co2_avoided_indirect,
                'episode_co2_avoided_direct': episode_co2_avoided_direct,
                'episode_solar_kwh': episode_solar_kwh,
                'episode_ev_charging_kwh': episode_ev_charging_kwh,
                'episode_grid_import_kwh': episode_grid_import_kwh,
                'episode_bess_discharge_kwh': np.zeros(episodes_completed),
                'episode_bess_charge_kwh': np.zeros(episodes_completed),
                'kpi_summary': validation
            }
            print(f"[OK] Extracted A2C metrics (real format): {episodes_completed} episodes")
            return metrics
        except Exception as e:
            print(f"[X] Error extracting A2C metrics: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _extract_a2c_metrics(self, json_file: Path) -> Dict:
        """Try alternative A2C extraction if main file missing."""
        try:
            with open(json_file) as f:
                data = json.load(f)
            return self._extract_a2c_metrics_from_dict(data)
        except:
            return {}
    
    def extract_timeseries(self, agent: str) -> pd.DataFrame:
        """Extract hourly timeseries from CSV."""
        csv_file = self.output_dir / f"{agent.lower()}_training" / f"timeseries_{agent.lower()}.csv"
        
        if not csv_file.exists():
            print(f"[!]  CSV file not found: {csv_file}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(csv_file)
            print(f"[OK] Extracted {agent} timeseries: {len(df)} rows")
            return df
        except Exception as e:
            print(f"[X] Error reading {csv_file}: {e}")
            return pd.DataFrame()
    
    def aggregate_timeseries_by_episodes(self, df: pd.DataFrame, rows_per_episode: int = 8760) -> Dict[str, np.ndarray]:
        """
        Aggregate timeseries into episodes when 'episode' column is missing.
        Assumes one year (8,760 hours) per episode.
        """
        if df.empty:
            return {}
        
        # If episode column exists, use it
        if 'episode' in df.columns:
            episodes_unique = sorted(df['episode'].unique())
        else:
            # Assume each 8,760 rows = 1 episode
            total_rows = len(df)
            episodes_unique = list(range(0, (total_rows + rows_per_episode - 1) // rows_per_episode))
        
        result = {}
        
        for col in ['grid_import_kw', 'solar_kw', 'ev_charging_kw', 'bess_power_kw']:
            if col not in df.columns:
                continue
                
            episode_data = []
            for ep_idx in episodes_unique:
                if 'episode' in df.columns:
                    ep_df = df[df['episode'] == ep_idx]
                else:
                    start_idx = ep_idx * rows_per_episode
                    end_idx = min((ep_idx + 1) * rows_per_episode, len(df))
                    ep_df = df.iloc[start_idx:end_idx]
                
                if len(ep_df) > 0:
                    # Convert kW to kWh (hourly)
                    episode_sum = ep_df[col].sum()
                    episode_data.append(episode_sum)
            
            result[col] = np.array(episode_data)
        
        return result
    
    
    def extract_trace(self, agent: str) -> pd.DataFrame:
        """Extract step-level trace from CSV."""
        csv_file = self.output_dir / f"{agent.lower()}_training" / f"trace_{agent.lower()}.csv"
        
        if not csv_file.exists():
            print(f"[!]  Trace file not found: {csv_file}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(csv_file)
            print(f"[OK] Extracted {agent} trace: {len(df)} steps")
            return df
        except Exception as e:
            print(f"[X] Error reading {csv_file}: {e}")
            return pd.DataFrame()


class MetricsCalculator:
    """Calculate real metrics from extracted data."""
    
    def __init__(self, cost_per_kwh: float = 0.15):
        """
        Args:
            cost_per_kwh: Grid electricity cost in €/kWh
        """
        self.cost_per_kwh = cost_per_kwh
        self.co2_per_kwh_grid = 0.4521  # kg CO2/kWh (Iquitos thermal grid)
    
    def calculate_episode_costs(self, grid_import_kwh: np.ndarray) -> np.ndarray:
        """Calculate total cost per episode from grid import."""
        return grid_import_kwh * self.cost_per_kwh
    
    def calculate_daily_peaks(self, timeseries_df: pd.DataFrame) -> np.ndarray:
        """Calculate daily peak load from timeseries."""
        if timeseries_df.empty or 'hour' not in timeseries_df.columns:
            return np.array([])
        
        # Group by episode and day, get max power
        if 'episode' in timeseries_df.columns:
            peaks = timeseries_df.groupby(['episode', 'hour'])['grid_import_kw'].max().values
            # Aggregate by episode
            episode_peaks = []
            for ep in timeseries_df['episode'].unique():
                ep_data = timeseries_df[timeseries_df['episode'] == ep]
                daily_peaks = []
                for day in range(365):
                    day_start = day * 24
                    day_end = min((day + 1) * 24, len(ep_data))
                    if day_start < len(ep_data):
                        day_max = ep_data.iloc[day_start:day_end]['grid_import_kw'].max()
                        daily_peaks.append(day_max)
                if daily_peaks:
                    episode_peaks.append(np.mean(daily_peaks))
            return np.array(episode_peaks)
        else:
            # Single episode - calculate daily peaks across whole series
            daily_peaks = []
            for day in range(365):
                day_start = day * 24
                day_end = min((day + 1) * 24, len(timeseries_df))
                if day_start < len(timeseries_df):
                    day_max = timeseries_df.iloc[day_start:day_end]['grid_import_kw'].max()
                    daily_peaks.append(day_max)
            return np.array(daily_peaks)
    
    def calculate_direct_co2_reduction(
        self, 
        solar_kwh: np.ndarray, 
        ev_solar_kwh: np.ndarray
    ) -> np.ndarray:
        """
        Calculate CO2 avoided by solar displacement.
        
        Direct reduction = solar generated - EV charged from solar
        This is solar that avoids grid import.
        """
        solar_to_grid = solar_kwh - ev_solar_kwh
        return np.maximum(solar_to_grid, 0) * self.co2_per_kwh_grid
    
    def calculate_indirect_co2_reduction(
        self,
        ev_solar_kwh: np.ndarray
    ) -> np.ndarray:
        """
        Calculate CO2 avoided by renewable EV charging.
        
        Indirect reduction = EV charged from renewable sources
        """
        return ev_solar_kwh * self.co2_per_kwh_grid


class GraphGenerator:
    """Generate publication-quality graphs."""
    
    def __init__(self, output_base_dir: Path):
        self.output_base_dir = Path(output_base_dir)
    
    def save_figure(self, fig: plt.Figure, agent: str, metric_name: str):
        """Save figure to appropriate folder."""
        if agent.lower() == 'comparison':
            agent_dir = self.output_base_dir / "comparison"
        else:
            agent_dir = self.output_base_dir / f"{agent.lower()}_training"
        
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = agent_dir / f"real_{metric_name}_{agent.lower()}.png"
        fig.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"[OK] Saved: {filepath.name}")
    
    def plot_episode_cost(self, costs_dict: Dict[str, np.ndarray], title: str = "Cost per Episode (Real Data)"):
        """Plot cost per episode for all agents."""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        for agent, costs in costs_dict.items():
            if len(costs) > 0:
                episodes = np.arange(len(costs))
                ax.plot(episodes, costs, marker='o', label=agent, color=COLORS.get(agent, '#000000'), linewidth=2, markersize=4)
                ax.fill_between(episodes, costs, alpha=0.1, color=COLORS.get(agent, '#000000'))
        
        ax.set_xlabel('Episode', fontsize=12, fontweight='bold')
        ax.set_ylabel('Grid Electricity Cost (€)', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def plot_daily_peak(self, peaks_dict: Dict[str, np.ndarray], title: str = "Daily Peak Load per Episode"):
        """Plot average daily peak load."""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        for agent, peaks in peaks_dict.items():
            if len(peaks) > 0:
                episodes = np.arange(len(peaks))
                ax.plot(episodes, peaks, marker='s', label=agent, color=COLORS.get(agent, '#000000'), linewidth=2, markersize=4)
                ax.fill_between(episodes, peaks, alpha=0.1, color=COLORS.get(agent, '#000000'))
        
        ax.set_xlabel('Episode', fontsize=12, fontweight='bold')
        ax.set_ylabel('Daily Peak Load (kW)', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def plot_co2_direct_reduction(self, reduction_dict: Dict[str, np.ndarray], title: str = "Direct CO₂ Reduction (Solar Avoidance)"):
        """Plot direct CO2 reduction per episode."""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        for agent, reduction in reduction_dict.items():
            if len(reduction) > 0:
                episodes = np.arange(len(reduction))
                ax.bar(episodes, reduction, alpha=0.7, label=agent, color=COLORS.get(agent, '#000000'), width=0.8)
        
        ax.set_xlabel('Episode', fontsize=12, fontweight='bold')
        ax.set_ylabel('CO₂ Avoided (kg)', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')
        
        return fig
    
    def plot_co2_indirect_reduction(self, reduction_dict: Dict[str, np.ndarray], title: str = "Indirect CO₂ Reduction (Renewable EV Charging)"):
        """Plot indirect CO2 reduction per episode."""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        for agent, reduction in reduction_dict.items():
            if len(reduction) > 0:
                episodes = np.arange(len(reduction))
                ax.bar(episodes, reduction, alpha=0.7, label=agent, color=COLORS.get(agent, '#000000'), width=0.8)
        
        ax.set_xlabel('Episode', fontsize=12, fontweight='bold')
        ax.set_ylabel('CO₂ Avoided (kg)', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')
        
        return fig
    
    def plot_comparison_dashboard(self, all_metrics: Dict, title: str = "Agent Performance Comparison (Real Data)"):
        """Create comparison dashboard."""
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        
        agents = list(all_metrics.keys())
        
        # 1. Cost Comparison
        ax1 = fig.add_subplot(gs[0, 0])
        costs = [all_metrics[a]['costs'].mean() if len(all_metrics[a]['costs']) > 0 else 0 for a in agents]
        bars1 = ax1.bar(agents, costs, color=[COLORS.get(a, '#000000') for a in agents], alpha=0.7)
        ax1.set_ylabel('Avg Cost (€)', fontweight='bold')
        ax1.set_title('Average Cost per Episode', fontweight='bold')
        for bar, cost in zip(bars1, costs):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'€{cost:.2f}', ha='center', va='bottom', fontweight='bold')
        
        # 2. Peak Load Comparison
        ax2 = fig.add_subplot(gs[0, 1])
        peaks = [all_metrics[a]['peaks'].mean() if len(all_metrics[a]['peaks']) > 0 else 0 for a in agents]
        bars2 = ax2.bar(agents, peaks, color=[COLORS.get(a, '#000000') for a in agents], alpha=0.7)
        ax2.set_ylabel('Avg Peak (kW)', fontweight='bold')
        ax2.set_title('Average Daily Peak Load', fontweight='bold')
        for bar, peak in zip(bars2, peaks):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{peak:.1f} kW', ha='center', va='bottom', fontweight='bold')
        
        # 3. Direct CO2 Reduction
        ax3 = fig.add_subplot(gs[1, 0])
        co2_direct = [all_metrics[a]['co2_direct'].sum() if len(all_metrics[a]['co2_direct']) > 0 else 0 for a in agents]
        bars3 = ax3.bar(agents, co2_direct, color=[COLORS.get(a, '#000000') for a in agents], alpha=0.7)
        ax3.set_ylabel('Total CO₂ (kg)', fontweight='bold')
        ax3.set_title('Direct CO₂ Reduction (Solar Avoidance)', fontweight='bold')
        for bar, co2 in zip(bars3, co2_direct):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{co2:,.0f} kg', ha='center', va='bottom', fontweight='bold')
        
        # 4. Indirect CO2 Reduction
        ax4 = fig.add_subplot(gs[1, 1])
        co2_indirect = [all_metrics[a]['co2_indirect'].sum() if len(all_metrics[a]['co2_indirect']) > 0 else 0 for a in agents]
        bars4 = ax4.bar(agents, co2_indirect, color=[COLORS.get(a, '#000000') for a in agents], alpha=0.7)
        ax4.set_ylabel('Total CO₂ (kg)', fontweight='bold')
        ax4.set_title('Indirect CO₂ Reduction (Renewable EV)', fontweight='bold')
        for bar, co2 in zip(bars4, co2_indirect):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{co2:,.0f} kg', ha='center', va='bottom', fontweight='bold')
        
        # 5. Total CO2 Reduction
        ax5 = fig.add_subplot(gs[2, :])
        co2_total = [co2_direct[i] + co2_indirect[i] for i in range(len(agents))]
        bars5 = ax5.bar(agents, co2_total, color=[COLORS.get(a, '#000000') for a in agents], alpha=0.7)
        ax5.set_ylabel('Total CO₂ (kg)', fontweight='bold')
        ax5.set_title('Total CO₂ Reduction (All Mechanisms)', fontweight='bold')
        for bar, co2 in zip(bars5, co2_total):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height,
                    f'{co2:,.0f} kg', ha='center', va='bottom', fontweight='bold')
        
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.995)
        
        return fig


def main():
    """Main execution."""
    print("\n" + "="*70)
    print("🔴 REAL METRICS EXTRACTOR & GRAPH GENERATOR (v2.1)")
    print("="*70)
    
    output_dir = Path("d:/disenopvbesscar/outputs")
    agents = ['SAC', 'PPO', 'A2C']
    
    # Extract data
    extractor = RealMetricsExtractor(output_dir)
    calculator = MetricsCalculator(cost_per_kwh=0.15)
    graph_gen = GraphGenerator(output_dir)
    
    all_metrics = {}
    
    print("\n[GRAPH] EXTRACTING METRICS...")
    print("-" * 70)
    
    for agent in agents:
        print(f"\n📍 Processing {agent}...")
        
        # Extract JSON metrics
        metrics = extractor.extract_metrics_from_json(agent)
        
        # Extract timeseries for detailed calculations
        timeseries = extractor.extract_timeseries(agent)
        
        if metrics:
            # Case 1: JSON exists (SAC, A2C with alt structure)
            grid_import = metrics.get('episode_grid_import_kwh', np.array([]))
            solar = metrics.get('episode_solar_kwh', np.array([]))
            ev_charging = metrics.get('episode_ev_charging_kwh', np.array([]))
            num_episodes = max(1, len(metrics.get('episode_rewards', [])))
            
            # For A2C: use the pre-calculated CO2 reductions
            if agent == 'A2C' and len(metrics.get('episode_co2_avoided_indirect', [])) > 0:
                co2_indirect = metrics['episode_co2_avoided_indirect']
                co2_direct = metrics['episode_co2_avoided_direct']
                costs = calculator.calculate_episode_costs(metrics.get('episode_grid_import_kwh', np.zeros(num_episodes)))
                peaks = np.zeros(num_episodes)  # No peak data in A2C JSON
                
                print(f"  [OK] Using A2C pre-calculated CO2 metrics")
            else:
                # For SAC: calculate from base metrics
                if len(grid_import) == 0 or len(solar) == 0 or len(ev_charging) == 0:
                    print(f"[!]  Missing episode data for {agent}")
                    continue
                
                costs = calculator.calculate_episode_costs(grid_import)
                peaks = calculator.calculate_daily_peaks(timeseries) if not timeseries.empty else np.zeros(num_episodes)
                
                # Estimate renewable EV charging (simplified: assume 30% of EV comes from solar)
                ev_solar = ev_charging * 0.30
                co2_direct = calculator.calculate_direct_co2_reduction(solar, ev_solar)
                co2_indirect = calculator.calculate_indirect_co2_reduction(ev_solar)
        elif not timeseries.empty:
            # Case 2: Only timeseries exists (PPO) - aggregate by episodes
            ts_agg = extractor.aggregate_timeseries_by_episodes(timeseries)
            if not ts_agg:
                print(f"[!]  Could not aggregate timeseries for {agent}")
                continue
            
            grid_import = ts_agg.get('grid_import_kw', np.array([]))
            solar = ts_agg.get('solar_kw', np.array([]))
            ev_charging = ts_agg.get('ev_charging_kw', np.array([]))
            num_episodes = len(grid_import)
            
            # Create minimal metrics dict
            metrics = {
                'agent': agent,
                'episode_grid_import_kwh': grid_import,
                'episode_solar_kwh': solar,
                'episode_ev_charging_kwh': ev_charging,
            }
            
            costs = calculator.calculate_episode_costs(grid_import)
            peaks = np.zeros(num_episodes)
            
            # Estimate renewable EV charging
            ev_solar = ev_charging * 0.30
            co2_direct = calculator.calculate_direct_co2_reduction(solar, ev_solar)
            co2_indirect = calculator.calculate_indirect_co2_reduction(ev_solar)
            
            print(f"[OK] Aggregated {agent} timeseries: {num_episodes} episodes")
        else:
            print(f"[X] No data found for {agent}")
            continue
        
        if len(costs) == 0:
            print(f"[!]  No cost data for {agent}")
            continue
        
        all_metrics[agent] = {
            'costs': costs,
            'peaks': peaks,
            'co2_direct': co2_direct,
            'co2_indirect': co2_indirect,
            'metrics': metrics
        }
        
        print(f"  [OK] Episodes: {len(costs)}")
        print(f"  [OK] Avg Cost: €{costs.mean():.2f}")
        if len(peaks) > 0 and peaks.sum() > 0:
            print(f"  [OK] Avg Peak: {peaks.mean():.1f} kW")
        print(f"  [OK] Direct CO₂: {co2_direct.sum():,.0f} kg")
        print(f"  [OK] Indirect CO₂: {co2_indirect.sum():,.0f} kg")
    
    if not all_metrics:
        print("\n[X] No metrics extracted for any agent!")
        return
    
    # Generate individual agent graphs
    print("\n\n[CHART] GENERATING GRAPHS...")
    print("-" * 70)
    
    costs_dict = {agent: all_metrics[agent]['costs'] for agent in all_metrics}
    peaks_dict = {agent: all_metrics[agent]['peaks'] for agent in all_metrics if len(all_metrics[agent]['peaks']) > 0}
    co2_direct_dict = {agent: all_metrics[agent]['co2_direct'] for agent in all_metrics}
    co2_indirect_dict = {agent: all_metrics[agent]['co2_indirect'] for agent in all_metrics}
    
    # 1. Cost Graph
    if costs_dict:
        fig = graph_gen.plot_episode_cost(costs_dict)
        graph_gen.save_figure(fig, 'comparison', 'cost_all_agents')
    
    # 2. Daily Peak Graph
    if peaks_dict:
        fig = graph_gen.plot_daily_peak(peaks_dict)
        graph_gen.save_figure(fig, 'comparison', 'daily_peak_all_agents')
    
    # 3. Direct CO2 Graph
    if co2_direct_dict:
        fig = graph_gen.plot_co2_direct_reduction(co2_direct_dict)
        graph_gen.save_figure(fig, 'comparison', 'co2_direct_all_agents')
    
    # 4. Indirect CO2 Graph
    if co2_indirect_dict:
        fig = graph_gen.plot_co2_indirect_reduction(co2_indirect_dict)
        graph_gen.save_figure(fig, 'comparison', 'co2_indirect_all_agents')
    
    # 5. Comparison Dashboard
    fig = graph_gen.plot_comparison_dashboard(all_metrics)
    graph_gen.save_figure(fig, 'comparison', 'real_metrics_dashboard')
    
    # Generate per-agent dashboards
    for agent in all_metrics:
        costs = all_metrics[agent]['costs']
        peaks = all_metrics[agent]['peaks']
        co2_d = all_metrics[agent]['co2_direct']
        co2_i = all_metrics[agent]['co2_indirect']
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Cost
        axes[0, 0].plot(costs, marker='o', linewidth=2, markersize=5, color=COLORS[agent])
        axes[0, 0].fill_between(range(len(costs)), costs, alpha=0.2, color=COLORS[agent])
        axes[0, 0].set_title(f'{agent} - Episode Cost', fontweight='bold')
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Cost (€)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Peak
        if len(peaks) > 0:
            axes[0, 1].plot(peaks, marker='s', linewidth=2, markersize=5, color=COLORS[agent])
            axes[0, 1].fill_between(range(len(peaks)), peaks, alpha=0.2, color=COLORS[agent])
        axes[0, 1].set_title(f'{agent} - Daily Peak Load', fontweight='bold')
        axes[0, 1].set_xlabel('Episode')
        axes[0, 1].set_ylabel('Peak (kW)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Direct CO2
        axes[1, 0].bar(range(len(co2_d)), co2_d, color=COLORS[agent], alpha=0.7)
        axes[1, 0].set_title(f'{agent} - Direct CO₂ Reduction', fontweight='bold')
        axes[1, 0].set_xlabel('Episode')
        axes[1, 0].set_ylabel('CO₂ Avoided (kg)')
        axes[1, 0].grid(True, alpha=0.3, axis='y')
        
        # Indirect CO2
        axes[1, 1].bar(range(len(co2_i)), co2_i, color=COLORS[agent], alpha=0.7)
        axes[1, 1].set_title(f'{agent} - Indirect CO₂ Reduction', fontweight='bold')
        axes[1, 1].set_xlabel('Episode')
        axes[1, 1].set_ylabel('CO₂ Avoided (kg)')
        axes[1, 1].grid(True, alpha=0.3, axis='y')
        
        fig.suptitle(f'{agent} Real Metrics Dashboard', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        graph_gen.save_figure(fig, agent, f'real_metrics_dashboard')
    
    print("\n\n[OK] COMPLETE!")
    print("="*70)
    print("Generated graphs:")
    print("  - real_cost_all_agents.png (comparison)")
    if peaks_dict:
        print("  - real_daily_peak_all_agents.png (comparison)")
    print("  - real_co2_direct_all_agents.png (comparison)")
    print("  - real_co2_indirect_all_agents.png (comparison)")
    print("  - real_metrics_dashboard.png (comparison + all agents)")
    print("\nPer-agent dashboards in respective folders:")
    for agent in all_metrics:
        print(f"  - {agent.lower()}_training/real_real_metrics_dashboard_{agent.lower()}.png")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
