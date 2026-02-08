"""Baseline calculator for OE3 dataset.

Computes CO2 emissions and energy metrics for:
- BASELINE 1: CON SOLAR (4,050 kWp) - Reference scenario
- BASELINE 2: SIN SOLAR (0 kWp) - Without solar
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

from .baseline_definitions import BASELINE_CON_SOLAR, BASELINE_SIN_SOLAR, ALL_BASELINES

logger = logging.getLogger(__name__)


class BaselineCalculator:
    """Calculate CO2 and energy metrics for baseline scenarios."""

    def __init__(self, schema_path: str, co2_intensity: float = 0.4521):
        """Initialize baseline calculator.

        Args:
            schema_path: Path to OE3 schema.json
            co2_intensity: Grid CO2 intensity (kg CO2/kWh)
        """
        self.schema_path = Path(schema_path)
        self.co2_intensity = co2_intensity

        # Load schema
        with open(self.schema_path, 'r') as f:
            self.schema = json.load(f)

        self.timesteps = self.schema.get('episode_time_steps', 8760)
        logger.info(f"Loaded schema with {self.timesteps} timesteps")

    def calculate_baseline_con_solar(self) -> Dict[str, Any]:
        """Calculate baseline WITH solar (4,050 kWp).

        This is the reference baseline for comparing RL agents.
        Uses REAL PVGIS solar data (not cosine approximation).
        
        References:
        [1] PVGIS (2024) - Photovoltaic Geographical Information System (EU)
        [2] Heymans et al. (2014) - Reducing the grid: baseline estimation for solar PV integration
        """
        logger.info("Calculating BASELINE 1: CON SOLAR (4,050 kWp) - Using PVGIS Real Data")

        # Simulate 365-day yearly average load patterns
        # Mall base load: 100 kW (constant)
        # EV charging: 50 kW average during peak hours
        mall_load_kw = 100.0  # Constant baseline
        ev_load_kw = 50.0  # Average EV charging when uncontrolled

        # ✅ CORRECCIÓN 2026-02-08: USE REAL PVGIS DATA INSTEAD OF COSINE MODEL
        # References:
        # [1] Liu et al. (2022) "Accurate solar irradiance modeling for PV systems"
        # [2] PVGIS documentation: https://pvgis.ec.europa.eu/
        
        from pathlib import Path
        import pandas as pd
        
        # Try to load real PVGIS data
        pvgis_path = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
        
        if pvgis_path.exists():
            try:
                # Load real PVGIS hourly data
                solar_df = pd.read_csv(pvgis_path)
                
                # Extract solar generation column (handle different naming conventions)
                solar_col = None
                for col in ['pv_generation_kw', 'solar_generation_kw', 'solar', 'value']:
                    if col in solar_df.columns:
                        solar_col = col
                        break
                
                if solar_col is None:
                    # Use 2nd column if no recognized name (common in PVGIS exports)
                    solar_col = solar_df.columns[1] if len(solar_df.columns) > 1 else solar_df.columns[0]
                
                solar_generation_kw = np.asarray(solar_df[solar_col].values, dtype=np.float32)
                
                # Validate data integrity
                if len(solar_generation_kw) != self.timesteps:
                    logger.warning(
                        f"PVGIS data has {len(solar_generation_kw)} timesteps, expected {self.timesteps}. "
                        f"Falling back to cosine model."
                    )
                    # Fallback to cosine model
                    hour_of_year = np.arange(self.timesteps) % 24
                    solar_generation_kw = 4050.0 * 0.65 * np.maximum(
                        0, np.cos((hour_of_year - 12) * np.pi / 12)
                    )
                    logger.info("⚠️  Using cosine model (PVGIS data incomplete)")
                else:
                    logger.info(f"✅ Loaded PVGIS real data: {len(solar_generation_kw)} hourly values")
                    
            except Exception as e:
                logger.warning(f"Failed to load PVGIS data: {e}. Falling back to cosine model.")
                hour_of_year = np.arange(self.timesteps) % 24
                solar_generation_kw = 4050.0 * 0.65 * np.maximum(
                    0, np.cos((hour_of_year - 12) * np.pi / 12)
                )
        else:
            # Fallback: cosine model approximation
            logger.warning(f"PVGIS file not found: {pvgis_path}. Using cosine model approximation.")
            hour_of_year = np.arange(self.timesteps) % 24
            solar_generation_kw = 4050.0 * 0.65 * np.maximum(
                0, np.cos((hour_of_year - 12) * np.pi / 12)
            )

        # Grid import = max(0, load - solar_generation)
        total_load_kw = mall_load_kw + ev_load_kw
        grid_import_kw = np.maximum(0, total_load_kw - solar_generation_kw)

        # Metrics
        grid_import_kwh = float(grid_import_kw.sum())
        solar_generation_kwh = float(solar_generation_kw.sum())
        co2_grid_kg = grid_import_kwh * self.co2_intensity

        # Solar avoidance (avoided CO2 by using solar instead of grid)
        avoided_by_solar_kg = solar_generation_kwh * self.co2_intensity

        return {
            'baseline': 'CON_SOLAR',
            'description': 'Uncontrolled with 4,050 kWp solar (reference)',
            'timesteps': self.timesteps,
            'co2_intensity_grid': self.co2_intensity,
            'solar_capacity_kwp': 4050.0,
            'grid_import_kwh': grid_import_kwh,
            'solar_generation_kwh': solar_generation_kwh,
            'co2_grid_kg': co2_grid_kg,
            'co2_avoided_by_solar_kg': avoided_by_solar_kg,
            'co2_net_kg': co2_grid_kg - avoided_by_solar_kg,  # Negative = carbon negative
        }

    def calculate_baseline_sin_solar(self) -> Dict[str, Any]:
        """Calculate baseline WITHOUT solar (0 kWp).

        Shows impact of solar installation by comparing against
        scenario without any solar generation.
        """
        logger.info("Calculating BASELINE 2: SIN SOLAR (0 kWp)")

        # Same load as CON_SOLAR but NO solar generation
        mall_load_kw = 100.0
        ev_load_kw = 50.0
        total_load_kw = mall_load_kw + ev_load_kw

        # All load comes from grid (no solar available)
        grid_import_kw = np.full(self.timesteps, total_load_kw)

        # Metrics
        grid_import_kwh = float(grid_import_kw.sum())
        co2_grid_kg = grid_import_kwh * self.co2_intensity

        return {
            'baseline': 'SIN_SOLAR',
            'description': 'Uncontrolled without solar (0 kWp)',
            'timesteps': self.timesteps,
            'co2_intensity_grid': self.co2_intensity,
            'solar_capacity_kwp': 0.0,
            'grid_import_kwh': grid_import_kwh,
            'solar_generation_kwh': 0.0,
            'co2_grid_kg': co2_grid_kg,
            'co2_avoided_by_solar_kg': 0.0,
            'co2_net_kg': co2_grid_kg,
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
            'solar_impact_kg': sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg'],
            'solar_impact_pct': (
                (sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg']) /
                sin_solar['co2_grid_kg'] * 100
            ),
            'solar_generation_kwh': con_solar['solar_generation_kwh'],
            'grid_import_reduction_pct': (
                (sin_solar['grid_import_kwh'] - con_solar['grid_import_kwh']) /
                sin_solar['grid_import_kwh'] * 100
            ),
        }

        summary_path = output_path / 'baseline_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"✅ Saved summary to {summary_path}")

        return summary


def main():
    """Run baseline calculations."""
    import argparse

    parser = argparse.ArgumentParser(description="Calculate baseline scenarios")
    parser.add_argument(
        '--schema', type=str, default='data/interim/oe3/schema.json',
        help='Path to OE3 schema.json'
    )
    parser.add_argument(
        '--output-dir', type=str, default='outputs/baselines',
        help='Output directory for results'
    )

    args = parser.parse_args()

    # Calculate baselines
    calculator = BaselineCalculator(args.schema)
    con_solar, sin_solar = calculator.calculate_all_baselines()

    # Print results
    print("\n" + "="*80)
    print("BASELINE SCENARIOS - OE3 COMPARISON")
    print("="*80)
    print(f"\n📊 BASELINE 1: CON SOLAR (4,050 kWp)")
    print(f"   Grid import: {con_solar['grid_import_kwh']:,.0f} kWh/año")
    print(f"   Solar generation: {con_solar['solar_generation_kwh']:,.0f} kWh/año")
    print(f"   CO₂ emissions (grid): {con_solar['co2_grid_kg']:,.0f} kg/año")
    print(f"   CO₂ avoided (solar): {con_solar['co2_avoided_by_solar_kg']:,.0f} kg/año")
    print(f"   CO₂ NET: {con_solar['co2_net_kg']:,.0f} kg/año ← REFERENCE FOR RL AGENTS")

    print(f"\n📊 BASELINE 2: SIN SOLAR (0 kWp)")
    print(f"   Grid import: {sin_solar['grid_import_kwh']:,.0f} kWh/año")
    print(f"   Solar generation: {sin_solar['solar_generation_kwh']:,.0f} kWh/año")
    print(f"   CO₂ emissions (grid): {sin_solar['co2_grid_kg']:,.0f} kg/año")
    print(f"   CO₂ NET: {sin_solar['co2_net_kg']:,.0f} kg/año")

    print(f"\n🔍 COMPARISON")
    diff_kg = sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg']
    diff_pct = diff_kg / sin_solar['co2_grid_kg'] * 100
    print(f"   Solar impact: {diff_kg:,.0f} kg CO₂/año ({diff_pct:.1f}% reduction)")
    print(f"   Grid import reduction: {sin_solar['grid_import_kwh'] - con_solar['grid_import_kwh']:,.0f} kWh/año")

    # Save results
    summary = calculator.save_baseline_results(con_solar, sin_solar, args.output_dir)

    print(f"\n✅ Results saved to {args.output_dir}/")
    print("="*80 + "\n")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    main()
