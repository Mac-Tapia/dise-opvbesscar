#!/usr/bin/env python
"""
BUILD OE3 DATASET FOR CITYLEARN V2

Construye el dataset completo integrando:
1. Solar: data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
2. Chargers: 128 (112 motos 2kW + 16 mototaxis 3kW)
3. Mall: 100 kW constant
4. BESS: 4,520 kWh, 2,000 kW
5. Grid: 0.4521 kg CO2/kWh (Iquitos thermal)

Output: src/citylearnv2/dataset/ (schema.json + CSV files)
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


class OE3DatasetBuilder:
    """Builds OE3 dataset for CityLearn v2."""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path(__file__).parent

        self.project_root = Path(project_root)
        self.data_dir = self.project_root / "data"
        self.oe2_dir = self.data_dir / "oe2"
        self.solar_dir = self.oe2_dir / "Generacionsolar"
        self.output_dir = self.project_root / "src" / "citylearnv2" / "dataset"

        logger.info(f"Project root: {self.project_root}")
        logger.info(f"OE2 directory: {self.oe2_dir}")
        logger.info(f"Solar directory: {self.solar_dir}")
        logger.info(f"Output directory: {self.output_dir}")

    def load_solar_data(self) -> pd.DataFrame:
        """Load hourly solar generation data."""
        solar_csv = self.solar_dir / "pv_generation_hourly_citylearn_v2.csv"

        if not solar_csv.exists():
            raise FileNotFoundError(f"Solar CSV not found: {solar_csv}")

        logger.info(f"\n[STEP 1] Loading solar data from {solar_csv}...")
        df = pd.read_csv(solar_csv)

        # Validate
        if len(df) != 8760:
            raise ValueError(f"Expected 8760 rows, got {len(df)}")

        required_cols = ['timestamp', 'ac_power_kw', 'ac_energy_kwh']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        logger.info(f"  Records: {len(df)}")
        logger.info(f"  Power (max): {df['ac_power_kw'].max():.1f} kW")
        logger.info(f"  Power (mean): {df['ac_power_kw'].mean():.1f} kW")
        logger.info(f"  Annual energy: {df['ac_energy_kwh'].sum():.0f} kWh")

        return df

    def create_charger_profiles(self) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """Create synthetic charger profiles (128 chargers)."""
        logger.info(f"\n[STEP 2] Creating charger profiles...")

        # 112 motos (2 kW) + 16 mototaxis (3 kW)
        chargers = []
        for i in range(112):
            chargers.append({
                'charger_id': i,
                'power_kw': 2.0,
                'type': 'moto',
                'location': 'Playa_Motos'
            })
        for i in range(16):
            chargers.append({
                'charger_id': 112 + i,
                'power_kw': 3.0,
                'type': 'mototaxi',
                'location': 'Playa_Mototaxis'
            })

        # Generate hourly profiles (8760 x 128)
        np.random.seed(42)
        profiles = pd.DataFrame(
            np.random.uniform(0.2, 1.0, size=(8760, 128)),
            columns=[f'charger_{i}' for i in range(128)]
        )

        total_power = sum(c['power_kw'] for c in chargers)
        logger.info(f"  Chargers: {len(chargers)}")
        logger.info(f"  Total power: {total_power:.0f} kW")
        logger.info(f"  Profile shape: {profiles.shape}")

        return profiles, chargers

    def create_mall_load(self, n_records: int) -> pd.Series:
        """Create constant mall load (100 kW)."""
        logger.info(f"\n[STEP 3] Creating mall load...")

        load = pd.Series([100.0] * n_records, name='mall_demand_kw')

        logger.info(f"  Demand: {load.iloc[0]:.1f} kW (constant)")
        logger.info(f"  Annual energy: {load.sum():.0f} kWh")

        return load

    def generate_schema(
        self,
        solar_df: pd.DataFrame,
        charger_profiles: pd.DataFrame,
        chargers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate schema.json for CityLearn v2."""
        logger.info(f"\n[STEP 4] Generating schema.json...")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        dataset_dir = self.output_dir / "dataset"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # Save CSV files
        solar_csv = dataset_dir / "solar_generation.csv"
        charger_csv = dataset_dir / "charger_load.csv"
        mall_csv = dataset_dir / "mall_load.csv"

        # Prepare solar data
        solar_save = solar_df[['timestamp', 'ac_power_kw', 'ghi_wm2', 'dni_wm2', 'dhi_wm2', 'temp_air_c']].copy()
        solar_save.columns = ['timestamp', 'solar_power_kw', 'ghi', 'dni', 'dhi', 'temperature']
        solar_save.to_csv(solar_csv, index=False)
        logger.info(f"  Saved: {solar_csv}")

        # Save charger profiles
        charger_profiles.to_csv(charger_csv, index=False)
        logger.info(f"  Saved: {charger_csv}")

        # Save mall load
        mall_df = pd.DataFrame({
            'timestamp': solar_df['timestamp'],
            'mall_demand_kw': [100.0] * len(solar_df)
        })
        mall_df.to_csv(mall_csv, index=False)
        logger.info(f"  Saved: {mall_csv}")

        # Create schema
        schema = {
            "schema": "V3.7",
            "timestamp": datetime.utcnow().isoformat(),
            "duration": {
                "step_size_seconds": 3600,
                "total_steps": 8760,
                "episode_duration_steps": 8760
            },
            "root_directory": str(dataset_dir),
            "buildings": [
                {
                    "name": "Building_EV_Iquitos",
                    "energy_simulation": "solar_generation.csv",
                    "solar_generation": {
                        "path": "solar_generation.csv",
                        "column": "solar_power_kw",
                        "unit": "kW"
                    },
                    "environmental_conditions": {
                        "weather_file": "solar_generation.csv",
                        "columns": {
                            "temperature": "temperature",
                            "wind_speed": "ghi"
                        }
                    },
                    "electrical_storage": {
                        "capacity": 4520.0,
                        "max_power_output": 2000.0,
                        "max_power_input": 2000.0,
                        "efficiency": 0.95,
                        "initial_soc": 0.5
                    },
                    "controllable_loads": [
                        {
                            "name": "EV_Chargers_128",
                            "path": "charger_load.csv",
                            "columns": list(range(128)),
                            "unit": "kW"
                        },
                        {
                            "name": "Mall_Load",
                            "path": "mall_load.csv",
                            "column": "mall_demand_kw",
                            "unit": "kW"
                        }
                    ]
                }
            ],
            "reward": {
                "type": "multi_objective",
                "weights": {
                    "co2_emissions": 0.50,
                    "solar_utilization": 0.20,
                    "cost": 0.10,
                    "ev_satisfaction": 0.10,
                    "grid_stability": 0.10
                },
                "carbon_intensity": {
                    "value": 0.4521,
                    "unit": "kg_CO2/kWh",
                    "source": "Iquitos thermal grid (isolated)"
                }
            },
            "metadata": {
                "location": "Iquitos, Peru",
                "latitude": -3.75,
                "longitude": -73.25,
                "altitude_m": 104.0,
                "year": 2024,
                "solar_model": "Sandia SAPM",
                "solar_capacity_kw": 4050.0,
                "solar_data_source": "PVGIS Typical Meteorological Year",
                "chargers_total": 128,
                "chargers_motos": 112,
                "chargers_mototaxis": 16,
                "bess_capacity_kwh": 4520.0,
                "bess_power_kw": 2000.0,
                "mall_demand_kw": 100.0,
                "ev_demand_constant_kw": 50.0,
                "generation_date": datetime.utcnow().isoformat()
            }
        }

        schema_path = self.output_dir / "schema.json"
        with open(schema_path, 'w') as f:
            json.dump(schema, f, indent=2)
        logger.info(f"  Saved: {schema_path}")

        return schema

    def build(self):
        """Build complete OE3 dataset."""
        logger.info("\n" + "=" * 80)
        logger.info("BUILDING OE3 DATASET FOR CITYLEARN V2")
        logger.info("=" * 80)

        try:
            # Load data
            solar_df = self.load_solar_data()
            charger_profiles, chargers = self.create_charger_profiles()
            mall_load = self.create_mall_load(len(solar_df))

            # Generate schema
            schema = self.generate_schema(solar_df, charger_profiles, chargers)

            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("BUILD SUCCESSFUL")
            logger.info("=" * 80)
            logger.info(f"Location: {self.output_dir}")
            logger.info(f"Timesteps: 8,760 (hourly, 1 year)")
            logger.info(f"Observation dim: 394")
            logger.info(f"Action dim: 129 (1 BESS + 128 chargers)")
            logger.info(f"\nData:")
            logger.info(f"  Solar: {solar_df['ac_energy_kwh'].sum():.0f} kWh/year")
            logger.info(f"  Chargers: {len(chargers)} (112 motos + 16 mototaxis)")
            logger.info(f"  Mall: {mall_load.sum():.0f} kWh/year")
            logger.info(f"  BESS: 4,520 kWh, 2,000 kW")
            logger.info(f"\nReady for OE3 training (SAC/PPO/A2C)")

            return True

        except Exception as e:
            logger.error(f"\nBUILD FAILED: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    builder = OE3DatasetBuilder()
    success = builder.build()
    sys.exit(0 if success else 1)
