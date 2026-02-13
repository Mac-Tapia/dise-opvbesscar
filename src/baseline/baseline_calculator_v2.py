"""Baseline calculator for OE3 dataset (v5.4 UPDATED).

Computes CO2 emissions and energy metrics for:
- BASELINE 1: CON SOLAR (4,050 kWp) - Reference scenario with real OE2 v5.4 data
- BASELINE 2: SIN SOLAR (0 kWp) - Without solar

Uses cleaned datasets from BESS v5.4 simulation:
- Solar: pv_generation_kwh from bess_simulation_hourly.csv
- Mall: mall_demand_kwh from bess_simulation_hourly.csv  
- EV: ev_demand_kwh from bess_simulation_hourly.csv
"""

from __future__ import annotations

import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class BaselineCalculator:
    """Calculate CO2 and energy metrics for baseline scenarios using real OE2 v5.4 data."""

    def __init__(self, co2_intensity: float = 0.4521):
        """Initialize baseline calculator.

        Args:
            co2_intensity: Grid CO2 intensity (kg CO2/kWh) - Iquitos diesel B5 (OSINERGMIN)
        """
        self.co2_intensity = co2_intensity
        self.timesteps = 8760  # 1 year of hourly data
        
        logger.info(f"BaselineCalculator initialized (OE2 v5.4):")
        logger.info(f"  - CO2 intensity: {self.co2_intensity} kg CO2/kWh (Iquitos thermal grid)")
        logger.info(f"  - Time horizon: {self.timesteps} hours (1 year)")

    def _load_bess_data(self) -> pd.DataFrame:
        """Load BESS simulation data with fallback to backward compatibility alias.
        
        Returns:
            DataFrame with columns: pv_generation_kwh, ev_demand_kwh, mall_demand_kwh, etc.
        
        Raises:
            FileNotFoundError: If neither primary nor alias path exists
        """
        # Try primary path first, then backward compatibility alias
        bess_data_path = Path('data/oe2/bess/bess_simulation_hourly.csv')
        bess_alt_path = Path('data/oe2/bess/bess_hourly_dataset_2024.csv')
        
        if bess_data_path.exists():
            actual_path = bess_data_path
        elif bess_alt_path.exists():
            actual_path = bess_alt_path
            logger.info("  (using bess_hourly_dataset_2024.csv backward compatibility alias)")
        else:
            raise FileNotFoundError(
                f"ERROR: BESS simulation data not found:\n"
                f"  - {bess_data_path}\n"
                f"  - {bess_alt_path}\n"
                f"  Please run: python src/dimensionamiento/oe2/disenobess/bess.py"
            )
        
        # Load and validate
        bess_df = pd.read_csv(actual_path, index_col=0)
        
        if len(bess_df) != self.timesteps:
            raise ValueError(f"ERROR: BESS data has {len(bess_df)} rows, expected exactly {self.timesteps}")
        
        return bess_df

    def calculate_baseline_con_solar(self) -> Dict[str, Any]:
        """Calculate baseline WITH solar (4,050 kWp).

        This is the reference baseline for comparing RL agents.
        Uses REAL data from BESS simulation (OE2 v5.4 cleaned datasets).
        
        Data sources (all validated 8,760 hours):
        - Solar: data/oe2/bess/bess_simulation_hourly.csv column 'pv_generation_kwh'
        - Mall load: Real data from bess_simulation_hourly.csv
        - EV load: Real data from bess_simulation_hourly.csv (chargers v3)
        """
        logger.info("Calculating BASELINE 1: CON SOLAR (4,050 kWp) - Using Real OE2 v5.4 Data")

        try:
            # Load BESS simulation data (includes all hourly flows)
            bess_df = self._load_bess_data()
            
            # Extract hourly profiles from BESS simulation
            solar_generation_kw = bess_df['pv_generation_kwh'].values.astype(np.float32)
            ev_demand_kw = bess_df['ev_demand_kwh'].values.astype(np.float32)
            mall_demand_kw = bess_df['mall_demand_kwh'].values.astype(np.float32)
            
            # Validate data integrity
            if solar_generation_kw.sum() == 0:
                raise ValueError("ERROR: Solar generation is zero - data not loaded correctly")
            if ev_demand_kw.sum() == 0:
                raise ValueError("ERROR: EV demand is zero - data not loaded correctly")
            if mall_demand_kw.sum() == 0:
                raise ValueError("ERROR: Mall demand is zero - data not loaded correctly")
            
            logger.info(f"  ✓ Solar generation: {solar_generation_kw.sum():,.0f} kWh/año")
            logger.info(f"  ✓ EV demand: {ev_demand_kw.sum():,.0f} kWh/año")
            logger.info(f"  ✓ Mall demand: {mall_demand_kw.sum():,.0f} kWh/año")
            
        except Exception as e:
            logger.error(f"ERROR loading BESS data: {e}")
            raise
        
        # Total demand (EVs + Mall)
        total_load_kw = mall_demand_kw + ev_demand_kw
        
        # Grid import = max(0, total_load - solar_generation)
        # This represents uncontrolled scenario without BESS or RL optimization
        grid_import_kw = np.maximum(0, total_load_kw - solar_generation_kw)

        # Metrics (annual)
        grid_import_kwh = float(grid_import_kw.sum())
        solar_generation_kwh = float(solar_generation_kw.sum())
        co2_grid_kg = grid_import_kwh * self.co2_intensity

        # Solar avoidance (avoided CO2 by using solar instead of grid)
        avoided_by_solar_kg = solar_generation_kwh * self.co2_intensity

        return {
            'baseline': 'CON_SOLAR',
            'description': 'Uncontrolled with 4,050 kWp solar (reference) - OE2 v5.4 real data',
            'timesteps': self.timesteps,
            'co2_intensity_grid': self.co2_intensity,
            'solar_capacity_kwp': 4050.0,
            'bess_capacity_kwh': 1700.0,  # v5.4 specification
            'grid_import_kwh': grid_import_kwh,
            'solar_generation_kwh': solar_generation_kwh,
            'co2_grid_kg': co2_grid_kg,
            'co2_avoided_by_solar_kg': avoided_by_solar_kg,
            'co2_net_kg': co2_grid_kg - avoided_by_solar_kg,
            'co2_t': co2_grid_kg / 1000,  # Converted to metric tons
        }

    def calculate_baseline_sin_solar(self) -> Dict[str, Any]:
        """Calculate baseline WITHOUT solar (0 kWp).

        Shows impact of solar installation by comparing against
        scenario without any solar generation (same loads, no PV).
        """
        logger.info("Calculating BASELINE 2: SIN SOLAR (0 kWp) - Using Real Load Data from OE2 v5.4")

        try:
            # Load actual load data from BESS simulation
            bess_df = self._load_bess_data()
            ev_demand_kw = bess_df['ev_demand_kwh'].values.astype(np.float32)
            mall_demand_kw = bess_df['mall_demand_kwh'].values.astype(np.float32)
            
            logger.info(f"  ✓ EV demand: {ev_demand_kw.sum():,.0f} kWh/año")
            logger.info(f"  ✓ Mall demand: {mall_demand_kw.sum():,.0f} kWh/año")
            
        except Exception as e:
            logger.error(f"ERROR loading BESS data: {e}")
            raise
        
        # Total load (no solar generation, so 100% from grid)
        total_load_kw = mall_demand_kw + ev_demand_kw
        
        # All load comes from grid (no solar available)
        grid_import_kw = total_load_kw.astype(np.float32)

        # Metrics
        grid_import_kwh = float(grid_import_kw.sum())
        co2_grid_kg = grid_import_kwh * self.co2_intensity

        return {
            'baseline': 'SIN_SOLAR',
            'description': 'Uncontrolled without solar (0 kWp) - OE2 v5.4 real data',
            'timesteps': self.timesteps,
            'co2_intensity_grid': self.co2_intensity,
            'solar_capacity_kwp': 0.0,
            'bess_capacity_kwh': 1700.0,  # v5.4 specification
            'grid_import_kwh': grid_import_kwh,
            'solar_generation_kwh': 0.0,
            'co2_grid_kg': co2_grid_kg,
            'co2_avoided_by_solar_kg': 0.0,
            'co2_net_kg': co2_grid_kg,
            'co2_t': co2_grid_kg / 1000,  # Converted to metric tons
        }

    def calculate_all_baselines(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Calculate both baselines.

        Returns:
            Tuple of (baseline_con_solar, baseline_sin_solar)
        """
        con_solar = self.calculate_baseline_con_solar()
        sin_solar = self.calculate_baseline_sin_solar()
        return con_solar, sin_solar

    def save_baseline_results(
        self, con_solar: Dict[str, Any], sin_solar: Dict[str, Any],
        output_dir: str = 'outputs/baselines'
    ) -> Dict[str, Any]:
        """Save baseline results to JSON files. Returns summary dict.

        Args:
            con_solar: CON_SOLAR baseline results
            sin_solar: SIN_SOLAR baseline results
            output_dir: Output directory for results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save as individual JSON files
        con_solar_path = output_path / 'baseline_con_solar.json'
        sin_solar_path = output_path / 'baseline_sin_solar.json'

        with open(con_solar_path, 'w') as f:
            json.dump(con_solar, f, indent=2)
        logger.info(f"✅ Saved CON_SOLAR results to {con_solar_path}")

        with open(sin_solar_path, 'w') as f:
            json.dump(sin_solar, f, indent=2)
        logger.info(f"✅ Saved SIN_SOLAR results to {sin_solar_path}")

        # Save comparison as CSV
        comparison_df = pd.DataFrame([con_solar, sin_solar])
        comparison_path = output_path / 'baseline_comparison.csv'
        comparison_df.to_csv(comparison_path, index=False)
        logger.info(f"✅ Saved comparison to {comparison_path}")

        # Save summary statistics
        summary = {
            'baseline_con_solar_co2_kg': con_solar['co2_grid_kg'],
            'baseline_sin_solar_co2_kg': sin_solar['co2_grid_kg'],
            'baseline_con_solar_co2_t': con_solar['co2_t'],
            'baseline_sin_solar_co2_t': sin_solar['co2_t'],
            'solar_impact_kg': sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg'],
            'solar_impact_t': (sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg']) / 1000,
            'solar_impact_pct': (
                (sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg']) /
                sin_solar['co2_grid_kg'] * 100
            ),
            'solar_generation_kwh': con_solar['solar_generation_kwh'],
            'grid_import_reduction_pct': (
                (sin_solar['grid_import_kwh'] - con_solar['grid_import_kwh']) /
                sin_solar['grid_import_kwh'] * 100
            ),
            'data_source': 'OE2 v5.4 (BESS simulation with real solar/EV/mall hourly data)',
        }

        summary_path = output_path / 'baseline_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"✅ Saved summary to {summary_path}")

        return summary


def main():
    """Run baseline calculations."""
    import argparse

    parser = argparse.ArgumentParser(description="Calculate baseline scenarios (OE2 v5.4)")
    parser.add_argument(
        '--output-dir', type=str, default='outputs/baselines',
        help='Output directory for results'
    )

    args = parser.parse_args()

    # Calculate baselines
    calculator = BaselineCalculator(co2_intensity=0.4521)  # Iquitos thermal grid
    con_solar, sin_solar = calculator.calculate_all_baselines()

    # Print results
    print("\n" + "="*80)
    print("BASELINE SCENARIOS - OE2 v5.4 COMPARISON (CITYLEARN v2 REFERENCE)")
    print("="*80)
    
    print(f"\n📊 BASELINE 1: CON SOLAR (4,050 kWp)")
    print(f"   Description: Uncontrolled + Real Solar")
    print(f"   Grid import: {con_solar['grid_import_kwh']:,.0f} kWh/año")
    print(f"   Solar generation: {con_solar['solar_generation_kwh']:,.0f} kWh/año")
    print(f"   CO₂ emissions (grid): {con_solar['co2_grid_kg']:,.0f} kg/año ({con_solar['co2_t']:,.1f} t/año)")
    print(f"   CO₂ avoided (solar): {con_solar['co2_avoided_by_solar_kg']:,.0f} kg/año")
    print(f"   CO₂ NET: {con_solar['co2_net_kg']:,.0f} kg/año ← REFERENCE FOR RL AGENTS")

    print(f"\n📊 BASELINE 2: SIN SOLAR (0 kWp)")
    print(f"   Description: Uncontrolled + No Solar (shows solar impact)")
    print(f"   Grid import: {sin_solar['grid_import_kwh']:,.0f} kWh/año")
    print(f"   Solar generation: {sin_solar['solar_generation_kwh']:,.0f} kWh/año")
    print(f"   CO₂ emissions (grid): {sin_solar['co2_grid_kg']:,.0f} kg/año ({sin_solar['co2_t']:,.1f} t/año)")
    print(f"   CO₂ NET: {sin_solar['co2_net_kg']:,.0f} kg/año")

    print(f"\n🔍 SOLAR IMPACT ANALYSIS")
    diff_kg = sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg']
    diff_t = diff_kg / 1000
    diff_pct = diff_kg / sin_solar['co2_grid_kg'] * 100
    print(f"   CO₂ reduction (solar): {diff_kg:,.0f} kg/año ({diff_t:,.1f} t/año)")
    print(f"   Percentage: {diff_pct:.1f}% CO₂ reduction with 4,050 kWp")
    print(f"   Grid import reduction: {sin_solar['grid_import_kwh'] - con_solar['grid_import_kwh']:,.0f} kWh/año")

    # Save results
    summary = calculator.save_baseline_results(con_solar, sin_solar, args.output_dir)

    print(f"\n✅ Baseline calculations completed")
    print(f"   Results saved to: {args.output_dir}/")
    print(f"   - baseline_con_solar.json")
    print(f"   - baseline_sin_solar.json")
    print(f"   - baseline_comparison.csv")
    print(f"   - baseline_summary.json")
    print("="*80 + "\n")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    main()
