#!/usr/bin/env python
"""
================================================================================
DATASET BUILDER v2.0 - CONSOLIDATED & ROBUST
OE3 CITYLEARN V2.5.0 DATASET CONSTRUCTION
================================================================================

🎯 PURPOSE:
- Unified dataset builder combining OE2 dimensioning → OE3 CityLearn v2 environment
- Integrates: Solar (4,050 kWp) + Chargers (128 sockets) + BESS (4,520 kWh) + Mall (100 kW)
- Multi-objective reward context: CO₂ minimization (0.4521 kg/kWh grid Iquitos)
- Produces: 8,760 hourly timesteps with 394-dim observations + 129-dim actions

📊 DATASET SPECS:
- Timesteps: 8,760 hours (exactly 1 year, hourly resolution)
- Observations: 394 dimensions (solar, grid, BESS, chargers, time features)
- Actions: 129 continuous [0,1] (1 BESS + 128 chargers)
- Resolution: HOURLY ONLY (no 15-minute data, no sub-hourly)

🔗 INTEGRATIONS:
✅ rewards.py: IquitosContext + MultiObjectiveWeights
✅ OE2 artifacts: Solar PV, chargers, BESS, mall demand
✅ Data validation: Early error detection, comprehensive checks
✅ Schema generation: co2_context + reward_weights for agent access
✅ Charger profiles: 128 individual socket CSV files (CityLearn format)

📅 VERSION: v2.0 (2026-02-04)
   - Consolidated from dataset_builder.py, build_citylearn_dataset.py, data_loader.py, validate_citylearn_build.py
   - Single authoritative file (no duplication, no split responsibilities)
   - Fully backward compatible with existing scripts
================================================================================
"""

from __future__ import annotations

import json
import logging
import shutil
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd  # type: ignore[import]

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

# Critical specifications (from OE2 dimensioning)
SPECS = {
    "timesteps": 8760,  # Exactly 1 year, hourly resolution
    "chargers_physical": 32,  # Physical chargers (28 motos + 4 mototaxis)
    "sockets_per_charger": 4,  # Sockets per physical charger
    "total_sockets": 128,  # Total individually controllable sockets
    "motos": 112,  # Sockets for motos (2 kW each)
    "mototaxis": 16,  # Sockets for mototaxis (3 kW each)
    "observation_dim": 394,
    "action_dim": 129,  # 1 BESS + 128 chargers
    "solar_capacity_kwp": 4050,  # PV capacity installed
    "solar_capacity_kw": 3200,  # AC capacity
    "bess_capacity_kwh": 4520,
    "bess_power_kw": 2000,
    "mall_load_kw": 100,
    "ev_peak_kw": 50,  # EV charging peak demand
    "co2_grid_kg_per_kwh": 0.4521,  # Iquitos thermal grid
    "co2_ev_conversion_kg_per_kwh": 2.146,  # EV combustion equivalent
}

# =============================================================================
# REWARD FUNCTIONS INTEGRATION
# =============================================================================

try:
    from src.rewards.rewards import (
        MultiObjectiveWeights,
        IquitosContext,
        MultiObjectiveReward,
        create_iquitos_reward_weights,
    )
    REWARDS_AVAILABLE = True
    logger.info("[INIT] ✅ Rewards module loaded successfully")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning("[INIT] ⚠️ Rewards module unavailable: %s (will use defaults)", str(e)[:100])
    REWARDS_AVAILABLE = False

# =============================================================================
# EXCEPTIONS & CUSTOM ERRORS
# =============================================================================

class DatasetValidationError(Exception):
    """Raised when data validation fails."""
    pass

class OE2DataLoaderException(Exception):
    """Raised when OE2 data loading fails."""
    pass

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class BuiltDataset:
    """Result of successful dataset construction."""
    dataset_dir: Path
    schema_path: Path
    building_name: str
    timestamp: str
    specs: Dict[str, Any]

@dataclass
class DataLoaderState:
    """State container for OE2 data loading."""
    project_root: Path
    data_dir: Path
    oe2_dir: Path
    interim_dir: Path
    processed_dir: Path
    artifacts: Dict[str, Any]
    errors: List[str]
    warnings: List[str]

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_solar_timeseries(df: pd.DataFrame) -> None:
    """
    CRITICAL: Validate solar timeseries is EXACTLY 8,760 hourly rows.

    ❌ REJECTED: 15-minute data (52,560 rows), 30-min (17,520 rows), etc.
    ✅ REQUIRED: Hourly only (8,760 rows)

    Args:
        df: Solar generation DataFrame

    Raises:
        DatasetValidationError: If validation fails
    """
    n_rows = len(df)

    if n_rows == 52560:
        raise DatasetValidationError(
            "❌ CRITICAL: Solar data is 15-minute resolution (52,560 rows).\n"
            "   OE3 requires HOURLY ONLY (8,760 rows).\n"
            "   Downsample using: df.set_index('time').resample('h').mean()"
        )

    if n_rows != SPECS["timesteps"]:
        raise DatasetValidationError(
            f"❌ Solar timeseries has {n_rows} rows, need exactly {SPECS['timesteps']} (hourly).\n"
            f"   Current frequency appears to be: {n_rows / 8760:.1f}x sub-hourly"
        )

    # Validate data integrity
    if df.isna().any().any():
        na_cols = df.columns[df.isna().any()].tolist()
        raise DatasetValidationError(
            f"❌ Solar data has NaN values in: {na_cols}"
        )

    logger.info("✅ Solar validation PASSED: %d hourly records", n_rows)

def validate_charger_profiles(df: pd.DataFrame) -> None:
    """
    Validate charger profiles have correct shape: (8,760, 128).

    Args:
        df: Charger profiles DataFrame

    Raises:
        DatasetValidationError: If shape incorrect
    """
    if df.shape != (SPECS["timesteps"], SPECS["total_sockets"]):
        raise DatasetValidationError(
            f"❌ Charger profiles shape {df.shape} != required "
            f"({SPECS['timesteps']}, {SPECS['total_sockets']})"
        )

    if df.isna().any().any():
        raise DatasetValidationError("❌ Charger profiles contain NaN values")

    logger.info("✅ Charger validation PASSED: %s shape", df.shape)

def validate_dataset_completeness(artifacts: Dict[str, Any]) -> Dict[str, bool]:
    """
    Comprehensive validation of all loaded artifacts.

    Returns:
        Dict with validation status for each component
    """
    results = {
        "solar": "solar_ts" in artifacts,
        "chargers": "chargers_real_hourly_2024" in artifacts or "chargers_hourly_profiles_annual" in artifacts,
        "bess": "bess_hourly_2024" in artifacts or "bess" in artifacts,
        "mall_demand": "mall_demand" in artifacts,
        "rewards": "iquitos_context" in artifacts and "reward_weights" in artifacts,
    }

    missing = [k for k, v in results.items() if not v]

    if missing:
        logger.warning("⚠️  Missing components: %s", ", ".join(missing))
    else:
        logger.info("✅ All components present: %s", ", ".join(results.keys()))

    return results

# =============================================================================
# OE2 DATA LOADER
# =============================================================================

class OE2DataLoader:
    """
    Systematic loader for all OE2 dimensioning artifacts.

    Handles:
    - Solar generation timeseries (hourly)
    - Charger profiles (128 sockets, 8,760 hours)
    - BESS system (capacity, power, SOC)
    - Mall demand
    - EV vehicle specs
    """

    def __init__(self, oe2_dir: Path):
        """
        Initialize with OE2 base directory.

        Args:
            oe2_dir: Path to data/interim/oe2/ or data/oe2/

        Raises:
            OE2DataLoaderException: If required subdirs missing
        """
        self.oe2_dir = Path(oe2_dir)

        # Verify structure
        required = ["solar", "chargers", "bess"]
        missing = [d for d in required if not (self.oe2_dir / d).exists()]

        if missing:
            raise OE2DataLoaderException(
                f"❌ OE2 directory incomplete. Missing: {missing}\n"
                f"   Expected at: {self.oe2_dir}"
            )

        logger.info("✅ OE2DataLoader initialized at %s", self.oe2_dir)

    def load_solar(self) -> pd.DataFrame:
        """Load solar generation (HOURLY ONLY)."""
        candidates = [
            self.oe2_dir / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv",
            self.oe2_dir / "solar" / "pv_generation_hourly_citylearn_v2.csv",
            self.oe2_dir / "Generacionsolar" / "pv_generation_timeseries.csv",
            self.oe2_dir / "solar" / "pv_generation_timeseries.csv",
        ]

        for path in candidates:
            if path.exists():
                try:
                    df = pd.read_csv(path)
                    validate_solar_timeseries(df)
                    logger.info("✅ Solar loaded from %s", path.name)
                    return df
                except Exception as e:
                    logger.warning("⚠️  Error loading %s: %s", path.name, str(e)[:100])

        raise OE2DataLoaderException(
            f"❌ Solar data not found. Checked: {[p.name for p in candidates]}"
        )

    def load_chargers(self) -> pd.DataFrame:
        """Load charger profiles (128 sockets, 8,760 hours)."""
        candidates = [
            self.oe2_dir / "chargers" / "chargers_real_hourly_2024.csv",
            self.oe2_dir / "chargers" / "chargers_hourly_profiles_annual.csv",
        ]

        for path in candidates:
            if path.exists():
                try:
                    df = pd.read_csv(path)
                    validate_charger_profiles(df)
                    logger.info("✅ Chargers loaded from %s", path.name)
                    return df
                except Exception as e:
                    logger.warning("⚠️  Error loading %s: %s", path.name, str(e)[:100])

        raise OE2DataLoaderException(
            f"❌ Charger data not found. Checked: {[p.name for p in candidates]}"
        )

    def load_bess(self) -> Optional[pd.DataFrame]:
        """Load BESS hourly dataset (8,760 records)."""
        path = self.oe2_dir / "bess" / "bess_hourly_dataset_2024.csv"

        if path.exists():
            try:
                df = pd.read_csv(path, index_col=0, parse_dates=True)
                if len(df) == SPECS["timesteps"] and "soc_percent" in df.columns:
                    logger.info("✅ BESS loaded from %s", path.name)
                    return df
            except Exception as e:
                logger.warning("⚠️  Error loading BESS: %s", str(e)[:100])

        logger.info("ℹ️  BESS hourly data not found, will use defaults")
        return None

    def load_mall_demand(self) -> Optional[pd.DataFrame]:
        """Load mall demand (8,760 hourly records)."""
        candidates = [
            self.oe2_dir / "demandamallkwh" / "demandamallhorakwh.csv",
            self.oe2_dir / "demandamallkwh" / "demanda_mall_horaria_anual.csv",
        ]

        for path in candidates:
            if path.exists():
                try:
                    # Try multiple separators
                    for sep in [",", ";"]:
                        df = pd.read_csv(path, sep=sep, decimal=".")
                        if len(df) >= SPECS["timesteps"]:
                            logger.info("✅ Mall demand loaded from %s", path.name)
                            return df
                except Exception as e:
                    logger.warning("⚠️  Error loading %s: %s", path.name, str(e)[:100])

        logger.info("ℹ️  Mall demand data not found, will use default (100 kW constant)")
        return None

    def load_carbon_intensity(self) -> Optional[pd.DataFrame]:
        """Load carbon intensity timeseries (kg CO₂/kWh, 8,760 hourly records).

        Returns:
            DataFrame with time index and carbon_intensity column, or None if not found
        """
        # Try multiple path candidates (relative and absolute)
        candidates = [
            Path("src/citylearnv2/climate_zone") / "carbon_intensity.csv",
            Path(__file__).parent.parent / "climate_zone" / "carbon_intensity.csv",
        ]

        for path in candidates:
            if path.exists():
                try:
                    df = pd.read_csv(path)
                    # Ensure we have time column for indexing
                    if "time" in df.columns:
                        df.set_index("time", inplace=True)
                    # Validate row count
                    if len(df) >= SPECS["timesteps"]:
                        logger.info("✅ Carbon intensity loaded from %s", path.name)
                        return df[:int(SPECS["timesteps"])]  # Ensure exactly 8,760 rows
                except Exception as e:
                    logger.warning("⚠️  Error loading carbon_intensity.csv: %s", str(e)[:100])

        logger.info("ℹ️  Carbon intensity data not found, will use grid default (0.4521 kg CO₂/kWh)")
        return None

    def load_pricing(self) -> Optional[pd.DataFrame]:
        """Load electricity pricing timeseries (USD/kWh, 8,760 hourly records).

        Returns:
            DataFrame with time index and electricity_pricing column, or None if not found
        """
        # Try multiple path candidates (relative and absolute)
        candidates = [
            Path("src/citylearnv2/climate_zone") / "pricing.csv",
            Path(__file__).parent.parent / "climate_zone" / "pricing.csv",
        ]

        for path in candidates:
            if path.exists():
                try:
                    df = pd.read_csv(path)
                    # Ensure we have time column for indexing
                    if "time" in df.columns:
                        df.set_index("time", inplace=True)
                    # Validate row count
                    if len(df) >= SPECS["timesteps"]:
                        logger.info("✅ Electricity pricing loaded from %s", path.name)
                        return df[:int(SPECS["timesteps"])]  # Ensure exactly 8,760 rows
                except Exception as e:
                    logger.warning("⚠️  Error loading pricing.csv: %s", str(e)[:100])

        logger.info("ℹ️  Pricing data not found, will use default (0.20 USD/kWh)")
        return None

    def load_weather(self) -> Optional[pd.DataFrame]:
        """Load weather data (temperature, humidity, wind, irradiance, 8,760 hourly records).

        Expected columns: time, dry_bulb_temperature, relative_humidity, wind_speed,
                         direct_normal_irradiance, diffuse_horizontal_irradiance

        Returns:
            DataFrame with time index and weather feature columns, or None if not found
        """
        # Try multiple path candidates (relative and absolute)
        candidates = [
            Path("src/citylearnv2/climate_zone") / "weather.csv",
            Path(__file__).parent.parent / "climate_zone" / "weather.csv",
        ]

        for path in candidates:
            if path.exists():
                try:
                    df = pd.read_csv(path)
                    # Ensure we have time column for indexing
                    if "time" in df.columns:
                        df.set_index("time", inplace=True)
                    # Validate row count
                    if len(df) >= SPECS["timesteps"]:
                        logger.info("✅ Weather data loaded from %s", path.name)
                        return df[:int(SPECS["timesteps"])]  # Ensure exactly 8,760 rows
                except Exception as e:
                    logger.warning("⚠️  Error loading weather.csv: %s", str(e)[:100])

        logger.info("ℹ️  Weather data not found, will use defaults (Iquitos typical climate)")
        return None

# =============================================================================
# DATASET CONSTRUCTION
# =============================================================================

def build_citylearn_dataset(
    processed_dir: Optional[Path] = None,
    building_name: str = "Iquitos_EV_Mall",
    overwrite: bool = False,
) -> BuiltDataset:
    """
    Build complete OE3 CityLearn v2 dataset from OE2 dimensioning artifacts.

    🎯 WORKFLOW:
    1. Load OE2 data (solar, chargers, BESS, mall)
    2. Validate all components (8,760 hourly)
    3. Initialize reward context (CO₂, weights, EV specs)
    4. Generate schema.json with co2_context + reward_weights
    5. Create 128 individual charger CSV files (CityLearn format)
    6. Post-validation to ensure data integrity

    Args:
        processed_dir: Output directory (default: data/processed/oe3/citylearn)
        building_name: Building name in CityLearn (default: Iquitos_EV_Mall)
        overwrite: Force regeneration if dataset exists

    Returns:
        BuiltDataset with paths and specs

    Raises:
        DatasetValidationError: If any validation fails
        OE2DataLoaderException: If OE2 data cannot be loaded
    """

    # =========================================================================
    # STEP 1: DETECT PATHS
    # =========================================================================

    if processed_dir is None:
        project_root = Path(__file__).parent.parent.parent.parent
        processed_dir = project_root / "data" / "processed" / "oe3" / "citylearn"
    else:
        processed_dir = Path(processed_dir)

    processed_dir.mkdir(parents=True, exist_ok=True)

    # Detect OE2 directory
    project_root = processed_dir.parent.parent.parent
    oe2_candidates = [
        project_root / "data" / "interim" / "oe2",
        project_root / "data" / "oe2",
    ]

    oe2_dir = None
    for candidate in oe2_candidates:
        if candidate.exists():
            oe2_dir = candidate
            break

    if oe2_dir is None:
        raise OE2DataLoaderException(
            f"❌ OE2 directory not found. Checked:\n"
            + "\n".join(f"   - {c}" for c in oe2_candidates)
        )

    logger.info("✅ Paths detected:")
    logger.info("   OE2: %s", oe2_dir)
    logger.info("   Output: %s", processed_dir)

    # =========================================================================
    # STEP 2: LOAD OE2 ARTIFACTS
    # =========================================================================

    logger.info("\n" + "="*80)
    logger.info("LOADING OE2 ARTIFACTS")
    logger.info("="*80)

    loader = OE2DataLoader(oe2_dir)
    artifacts = {}

    try:
        artifacts["solar_ts"] = loader.load_solar()
    except OE2DataLoaderException as e:
        raise DatasetValidationError(f"❌ Cannot proceed without solar data: {e}")

    try:
        artifacts["chargers_hourly"] = loader.load_chargers()
    except OE2DataLoaderException as e:
        raise DatasetValidationError(f"❌ Cannot proceed without charger data: {e}")

    artifacts["bess_hourly"] = loader.load_bess()  # Optional
    artifacts["mall_demand"] = loader.load_mall_demand()  # Optional
    artifacts["carbon_intensity"] = loader.load_carbon_intensity()  # Optional
    artifacts["pricing"] = loader.load_pricing()  # Optional
    artifacts["weather"] = loader.load_weather()  # Optional

    # =========================================================================
    # STEP 3: LOAD REWARD CONTEXT
    # =========================================================================

    logger.info("\n" + "="*80)
    logger.info("INITIALIZING REWARD CONTEXT")
    logger.info("="*80)

    if REWARDS_AVAILABLE:
        try:
            # IquitosContext usa atributos de clase, no parámetros del constructor
            artifacts["iquitos_context"] = IquitosContext()
            logger.info("IquitosContext loaded:")
            logger.info("   CO2 grid: %.4f kg/kWh", SPECS["co2_grid_kg_per_kwh"])
            logger.info("   CO2 EV: %.3f kg/kWh", SPECS["co2_ev_conversion_kg_per_kwh"])
            logger.info("   EV capacity: %d motos + %d mototaxis/day", 2685, 388)
        except Exception as e:
            logger.error("Failed to load IquitosContext: %s", e)

        try:
            artifacts["reward_weights"] = create_iquitos_reward_weights(priority="balanced")
            rw = artifacts["reward_weights"]
            logger.info("✅ Reward weights loaded:")
            logger.info("   CO₂: %.2f, Solar: %.2f, Cost: %.2f, EV: %.2f, Grid: %.2f",
                       rw.co2, rw.solar, rw.cost, rw.ev_satisfaction, rw.grid_stability)
        except Exception as e:
            logger.error("❌ Failed to load reward weights: %s", e)

    # =========================================================================
    # STEP 4: VALIDATE DATASET COMPLETENESS
    # =========================================================================

    logger.info("\n" + "="*80)
    logger.info("VALIDATING DATASET COMPLETENESS")
    logger.info("="*80)

    validation_results = validate_dataset_completeness(artifacts)

    if not validation_results["solar"] or not validation_results["chargers"]:
        raise DatasetValidationError(
            f"❌ Critical components missing: {validation_results}"
        )

    # =========================================================================
    # STEP 5: GENERATE SCHEMA.JSON
    # =========================================================================

    logger.info("\n" + "="*80)
    logger.info("GENERATING SCHEMA.JSON")
    logger.info("="*80)

    building_dir = processed_dir / building_name / "building"
    building_dir.mkdir(parents=True, exist_ok=True)

    schema = _build_schema(artifacts, building_name)

    schema_path = processed_dir / building_name / "schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)

    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, default=str)

    logger.info("✅ Schema generated: %s", schema_path)

    # =========================================================================
    # STEP 6: GENERATE CHARGER CSV FILES
    # =========================================================================

    logger.info("\n" + "="*80)
    logger.info("GENERATING CHARGER CSV FILES")
    logger.info("="*80)

    chargers_df = artifacts["chargers_hourly"]
    _generate_charger_csvs(chargers_df, building_dir, overwrite=overwrite)

    # =========================================================================
    # STEP 6B: GENERATE CLIMATE ZONE CSV FILES
    # =========================================================================

    logger.info("\n" + "="*80)
    logger.info("GENERATING CLIMATE ZONE CSV FILES")
    logger.info("="*80)

    _generate_climate_csvs(artifacts, building_dir, overwrite=overwrite)

    # =========================================================================
    # STEP 7: POST-VALIDATION
    # =========================================================================

    logger.info("\n" + "="*80)
    logger.info("POST-BUILD VALIDATION")
    logger.info("="*80)

    _validate_output(building_dir, schema_path)

    # =========================================================================
    # COMPLETE
    # =========================================================================

    logger.info("\n" + "="*80)
    logger.info("✅ DATASET CONSTRUCTION COMPLETE")
    logger.info("="*80)
    logger.info("Building: %s", building_name)
    logger.info("Schema: %s", schema_path)
    logger.info("Timesteps: %d (hourly)", SPECS["timesteps"])
    logger.info("Chargers: %d sockets", SPECS["total_sockets"])
    logger.info("Reward context: %s", "Yes" if REWARDS_AVAILABLE else "No")
    logger.info("")

    return BuiltDataset(
        dataset_dir=processed_dir,
        schema_path=schema_path,
        building_name=building_name,
        timestamp=datetime.now().isoformat(),
        specs=SPECS,
    )

# =============================================================================
# SCHEMA GENERATION
# =============================================================================

def _build_schema(artifacts: Dict[str, Any], building_name: str) -> Dict[str, Any]:
    """
    Build CityLearn v2 schema.json with integrated reward context.

    Includes:
    - co2_context: Grid CO₂, EV CO₂, daily capacities
    - reward_weights: Multi-objective optimization weights
    - Building structure (electric storage, chargers, loads)
    """

    schema = {
        "version": "2.5.0",
        "time_steps": SPECS["timesteps"],
        "buildings": [
            {
                "name": building_name,
                "energy_simulation": {
                    "type": "physics-based",
                    "system_parameters": {
                        "solar_pv_capacity_kw": SPECS["solar_capacity_kw"],
                        "bess_capacity_kwh": SPECS["bess_capacity_kwh"],
                        "bess_power_kw": SPECS["bess_power_kw"],
                        "chargers_total": SPECS["total_sockets"],
                        "mall_load_kw": SPECS["mall_load_kw"],
                    }
                },
                "electrical_storage": {
                    "capacity_kwh": SPECS["bess_capacity_kwh"],
                    "power_kw": SPECS["bess_power_kw"],
                },
                "solar_generation": f"solar_generation.csv",
                "net_electricity_consumption": f"net_electricity_consumption.csv",
                "carbon_intensity": f"carbon_intensity.csv",
                "electricity_pricing": f"electricity_pricing.csv",
                "weather": f"weather.csv",
            }
        ],
    }

    # Add reward context if available
    if "iquitos_context" in artifacts:
        ctx = artifacts["iquitos_context"]
        # CRITICAL FIX: Convert peak_hours to list explicitly (may be object/dict/set)
        peak_hours_val: Any = ctx.peak_hours
        peak_hours_list: list[Any] = list(peak_hours_val) if isinstance(peak_hours_val, (list, tuple, dict, set)) else [peak_hours_val]
        schema["co2_context"] = {
            "co2_factor_kg_per_kwh": float(ctx.co2_factor_kg_per_kwh),
            "co2_conversion_factor": float(ctx.co2_conversion_factor),
            "motos_daily_capacity": int(ctx.motos_daily_capacity),
            "mototaxis_daily_capacity": int(ctx.mototaxis_daily_capacity),
            "max_evs_total": int(ctx.max_evs_total),
            "tariff_usd_per_kwh": float(ctx.tariff_usd_per_kwh),
            "peak_hours": peak_hours_list,
            "description": "Contexto real de Iquitos para cálculo de CO₂ (thermal grid, aislado)"
        }

    if "reward_weights" in artifacts:
        rw = artifacts["reward_weights"]
        # CRITICAL FIX: Convert dict/object to dict explicitly
        rw_dict: dict[str, Any] = dict(rw) if hasattr(rw, 'items') else rw
        schema["reward_weights"] = {
            "co2": float(rw_dict.get("co2", 0.0)),
            "cost": float(rw_dict.get("cost", 0.0)),
            "solar": float(rw_dict.get("solar", 0.0)),
            "ev_satisfaction": float(rw_dict.get("ev_satisfaction", 0.0)),
            "ev_utilization": float(rw_dict.get("ev_utilization", 0.0)),
            "grid_stability": float(rw_dict.get("grid_stability", 0.0)),
            "description": "Pesos multiobjetivo para optimización de agentes RL"
        }

    return schema

# =============================================================================
# CHARGER CSV GENERATION
# =============================================================================

def _generate_charger_csvs(
    chargers_df: pd.DataFrame,
    building_dir: Path,
    overwrite: bool = False,
) -> None:
    """
    Generate 128 individual charger_simulation_XXX.csv files.

    CityLearn v2 requires each charger's demand in a separate CSV:
    - charger_simulation_001.csv through charger_simulation_128.csv
    - Each: 8,760 rows × 1 column (kW demand)
    """

    if chargers_df.shape[0] != SPECS["timesteps"]:
        raise DatasetValidationError(
            f"❌ Chargers must have {SPECS['timesteps']} rows, got {chargers_df.shape[0]}"
        )

    if chargers_df.shape[1] != SPECS["total_sockets"]:
        raise DatasetValidationError(
            f"❌ Chargers must have {SPECS['total_sockets']} columns, got {chargers_df.shape[1]}"
        )

    building_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Generating %d charger CSVs...", int(SPECS["total_sockets"]))

    for i in range(int(SPECS["total_sockets"])):
        csv_name = f"charger_simulation_{i+1:03d}.csv"
        csv_path = building_dir / csv_name

        if csv_path.exists() and not overwrite:
            logger.debug("  Skipped %s (exists)", csv_name)
            continue

        # Convertir ExtensionArray a numpy array explícitamente
        demand_ext = chargers_df.iloc[:, i].values
        demand: np.ndarray = np.asarray(demand_ext, dtype=np.float64).reshape(-1, 1)
        df_charger = pd.DataFrame(demand, columns=["kw"])
        df_charger.to_csv(csv_path, index=False)

    logger.info("✅ Generated %d charger CSVs in %s", int(SPECS["total_sockets"]), building_dir)


def _generate_climate_csvs(
    artifacts: Dict[str, Any],
    building_dir: Path,
    overwrite: bool = False,
) -> None:
    """
    Generate climate zone CSV files (carbon_intensity, electricity_pricing, weather).

    CityLearn v2 supports optional climate data files:
    - carbon_intensity.csv: kg CO₂/kWh (8,760 rows)
    - electricity_pricing.csv: USD/kWh (8,760 rows)
    - weather.csv: Temperature, humidity, wind, irradiance (8,760 rows)
    """

    building_dir.mkdir(parents=True, exist_ok=True)

    climate_files = {
        "carbon_intensity": artifacts.get("carbon_intensity"),
        "electricity_pricing": artifacts.get("pricing"),
        "weather": artifacts.get("weather"),
    }

    for file_key, df in climate_files.items():
        if df is None:
            logger.info("ℹ️  Skipped %s (not loaded)", file_key)
            continue

        # Determine output filename based on artifact key
        if file_key == "carbon_intensity":
            csv_name = "carbon_intensity.csv"
        elif file_key == "electricity_pricing":
            csv_name = "electricity_pricing.csv"
        elif file_key == "weather":
            csv_name = "weather.csv"
        else:
            continue

        csv_path = building_dir / csv_name

        if csv_path.exists() and not overwrite:
            logger.debug("  Skipped %s (exists)", csv_name)
            continue

        # Reset index if present (to include time column)
        df_out = df.reset_index() if df.index.name else df
        df_out.to_csv(csv_path, index=False)
        logger.info("✅ Generated %s (%d rows)", csv_name, int(len(df_out)))

    logger.info("✅ Climate zone CSVs generated in %s", building_dir)

# =============================================================================
# POST-VALIDATION
# =============================================================================

def _validate_output(building_dir: Path, schema_path: Path) -> None:
    """
    Post-build validation:
    - All 128 charger CSVs exist
    - Schema valid JSON
    - Required keys in schema
    """

    # Check charger CSVs
    charger_files = list(building_dir.glob("charger_simulation_*.csv"))
    if len(charger_files) != SPECS["total_sockets"]:
        logger.warning(
            "⚠️  Expected %d charger CSVs, found %d",
            SPECS["total_sockets"], len(charger_files)
        )
    else:
        logger.info("✅ All %d charger CSVs present", SPECS["total_sockets"])

    # Check schema
    with open(schema_path) as f:
        schema = json.load(f)

    required_keys = ["version", "buildings"]
    missing = [k for k in required_keys if k not in schema]
    if missing:
        logger.warning("⚠️  Schema missing keys: %s", missing)
    else:
        logger.info("✅ Schema structure valid")

    # Check reward context
    if "co2_context" in schema:
        logger.info("✅ co2_context present in schema")
    if "reward_weights" in schema:
        logger.info("✅ reward_weights present in schema")

# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    try:
        output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
        result = build_citylearn_dataset(processed_dir=output_dir)
        logger.info("✅ Dataset built successfully at %s", result.schema_path)
        sys.exit(0)
    except Exception as e:
        logger.error("❌ Failed: %s", e, exc_info=True)
        sys.exit(1)
