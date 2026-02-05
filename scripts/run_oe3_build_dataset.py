#!/usr/bin/env python
"""Build OE3 dataset with schema and charger configurations."""

from __future__ import annotations

import json
import argparse
import logging
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict[str, Any]:
    """Load YAML configuration."""
    import yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        if config is None:
            return {}
        return config


def build_schema(output_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Build schema.json with CityLearn configuration."""

    logger.info("Building schema.json...")

    # Load OE2 data for reference
    oe2_solar = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
    oe2_chargers = Path("data/interim/oe2/chargers/individual_chargers.json")

    # Read solar data to get timesteps
    if oe2_solar.exists():
        solar_df = pd.read_csv(oe2_solar)
        timesteps = len(solar_df)
        logger.info(f"Loaded solar data: {timesteps} timesteps")
    else:
        timesteps = 8760  # Default: 1 year
        logger.warning(f"Solar data not found, using default {timesteps} timesteps")

    # Read charger specs
    chargers_list = []
    if oe2_chargers.exists():
        with open(oe2_chargers, 'r') as f:
            chargers_list = json.load(f)
        logger.info(f"Loaded {len(chargers_list)} charger specifications")

    # Build schema
    schema = {
        "root_directory": str(output_dir.resolve()),  # CityLearn v2 requires root_directory
        "episode_time_steps": timesteps,
        "time_step_minutes": 60,
        "central_agent": False,  # CityLearn required field
        "observations": {
            "building_0": ["solar_generation", "net_electricity_consumption"]
        },
        "actions": {
            "building_0": ["electrical_storage", "electric_vehicle_charging"]
        },
        "buildings": [
            {
                "name": "Iquitos_Mall",
                "energy_simulation": {
                    "solar_generation": "oe2/solar/pv_generation_timeseries.csv",
                    "non_shiftable_load": "oe2/mall_demand_hourly.csv",
                },
                "electrical_storage": {
                    "capacity": 4520,  # kWh
                    "power_rating": 600,  # kW
                },
                "controllable_charging": [
                    {
                        "name": f"charger_{i}",
                        "power_rating": 10.0,  # kW per socket
                        "sockets": 4,
                        "vehicle_type": charger.get("tipo_especifico", "moto") if i < len(chargers_list) else "moto"
                    }
                    for i, charger in enumerate(chargers_list)
                ]
            }
        ],
        "co2_context": {
            "region": "Iquitos",
            "country": "Peru",
            "co2_intensity_grid": 0.4521,  # kg CO2/kWh (thermal generation)
        },
        "reward_weights": {
            "co2_grid_minimization": 0.50,
            "solar_self_consumption": 0.20,
            "ev_charge_completion": 0.15,
            "grid_stability": 0.10,
            "cost_minimization": 0.05,
        },
        "dataset_version": "OE3-v2.0",
        "created_at": pd.Timestamp.now().isoformat(),
    }

    # Save schema
    schema_path = output_dir / "schema.json"
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)

    logger.info(f"✅ Schema saved to {schema_path}")
    return schema


def build_charger_files(output_dir: Path, schema: dict[str, Any]) -> None:
    """Generate charger CSV files (128 total: 32 chargers × 4 sockets)."""

    logger.info("Building charger CSV files...")

    chargers_dir = output_dir / "chargers"
    chargers_dir.mkdir(parents=True, exist_ok=True)

    # Load OE2 charger specs
    oe2_chargers = Path("data/interim/oe2/chargers/individual_chargers.json")
    chargers_list = []

    if oe2_chargers.exists():
        with open(oe2_chargers, 'r') as f:
            chargers_list = json.load(f)

    # Generate charger files (128 total: 32 chargers × 4 sockets per charger)
    # OE2 specifies 32 charger units, each with 4 sockets = 128 controllable charging points
    num_chargers = 32
    sockets_per_charger = 4
    total_sockets = num_chargers * sockets_per_charger  # 128

    timesteps = schema["episode_time_steps"]

    # Create 128 socket CSV files (one per controllable charger socket)
    for socket_id in range(total_sockets):
        charger_unit = socket_id // sockets_per_charger
        socket_num = socket_id % sockets_per_charger

        # Generate realistic charger data
        # Vehicle capacity: 100 kWh (typical for EV in Iquitos context)
        # SOC varies throughout year based on charging patterns
        charger_data = {
            "timestamp": pd.date_range("2024-01-01", periods=timesteps, freq="h"),
            "capacity_kwh": [100.0] * timesteps,  # Battery capacity (kWh)
            "current_soc": np.linspace(0.3, 0.9, timesteps).tolist(),  # State of charge varies
            "max_power_kw": [10.0] * timesteps,  # Max charging power per socket (10 kW)
            "available": np.random.choice([0, 1], timesteps, p=[0.3, 0.7]).tolist(),  # 70% available
            "charger_unit": [charger_unit] * timesteps,
            "socket_number": [socket_num] * timesteps,
        }

        df = pd.DataFrame(charger_data)
        charger_path = chargers_dir / f"charger_{socket_id:03d}.csv"  # charger_000 to charger_127
        df.to_csv(charger_path, index=False)

    logger.info(f"✅ Created {total_sockets} charger socket CSV files (32 units × 4 sockets)")
    logger.info(f"   Location: {chargers_dir}")

def main():
    parser = argparse.ArgumentParser(description="Build OE3 dataset")
    parser.add_argument("--config", type=str, default="configs/default.yaml", help="Config file path")
    parser.add_argument("--output-dir", type=str, default="data/interim/oe3", help="Output directory")

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    logger.info(f"Loaded config from {args.config}")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir.absolute()}")

    # Build schema
    schema = build_schema(output_dir, config)

    # Build charger files
    build_charger_files(output_dir, schema)

    logger.info(f"\n✅ Dataset generation COMPLETE!")
    logger.info(f"   Schema: {output_dir / 'schema.json'}")
    logger.info(f"   Chargers: {output_dir / 'chargers'}")


if __name__ == "__main__":
    main()
