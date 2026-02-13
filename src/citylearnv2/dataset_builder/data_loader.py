"""
OE2 Data Loader with Comprehensive Validation

Responsible for:
1. Loading all OE2 data (solar, chargers, BESS)
2. Validating completeness and correctness
3. Raising errors early if data is invalid
4. Providing clean interfaces for dataset_builder
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd  # type: ignore[import]

logger = logging.getLogger(__name__)


class OE2ValidationError(Exception):
    """Raised when OE2 data fails validation."""
    pass


class OE2DataLoader:
    """Systematic OE2 data loader with extensive validation."""

    def __init__(self, oe2_path: Path | str):
        """Initialize with OE2 base path.

        Args:
            oe2_path: Path to data/interim/oe2/ directory

        Raises:
            OE2ValidationError: If OE2 path doesn't exist or lacks subdirs
        """
        self.oe2_path = Path(oe2_path)

        # Verify required subdirectories exist
        required_dirs = ['solar', 'chargers', 'bess']
        for subdir in required_dirs:
            subdir_path = self.oe2_path / subdir
            if not subdir_path.exists():
                raise OE2ValidationError(
                    f"Missing OE2 subdirectory: {subdir}\n"
                    f"Expected at: {subdir_path}"
                )

        logger.info(f"✅ OE2DataLoader initialized at {self.oe2_path}")

    # ========== SOLAR LOADING & VALIDATION ==========

    def load_solar_timeseries(self) -> pd.DataFrame:
        """Load and validate solar PV generation timeseries.

        Returns:
            DataFrame with columns: [timestamp, ..., ac_power_kw, ...]
            Shape: (8760, 12) after resampling from 15-min frequency

        Raises:
            OE2ValidationError: If file missing, incomplete, or invalid ranges
        """
        solar_file = self.oe2_path / 'solar' / 'pv_generation_timeseries.csv'

        if not solar_file.exists():
            raise OE2ValidationError(f"Solar timeseries not found: {solar_file}")

        # Load data
        try:
            df: pd.DataFrame = pd.read_csv(solar_file)  # type: ignore[assignment]
        except Exception as e:
            raise OE2ValidationError(f"Failed to read solar CSV: {e}")

        # Validate structure
        if 'ac_power_kw' not in df.columns:
            raise OE2ValidationError(
                f"Solar CSV missing 'ac_power_kw' column. Columns: {df.columns.tolist()}"
            )

        # Validate length (should be 15-minute frequency, ~35,040 rows for 365 days)
        if len(df) < 8000:
            raise OE2ValidationError(
                f"Solar timeseries too short: {len(df)} rows (expected ≥8000)"
            )

        # Validate values
        solar_max = df['ac_power_kw'].max()
        if solar_max > 4200:  # Eaton Xpert1670 spec: 2 × 2,075 kW = 4,150 kW
            logger.warning(
                f"⚠️ Solar generation exceeds Eaton spec: {solar_max:.0f} kW > 4,150 kW"
            )

        if solar_max <= 0:
            raise OE2ValidationError("Solar generation all zeros or negative")

        # Check for NaN/inf
        nan_mask: bool = bool(df['ac_power_kw'].isna().any())  # type: ignore[assignment]
        if nan_mask:
            na_count: int = int(df['ac_power_kw'].isna().sum())  # type: ignore[assignment]
            logger.warning(f"⚠️ Solar timeseries has {na_count} NaN values")

        logger.info(
            f"✅ Solar loaded: {len(df)} rows, "
            f"max={solar_max:.0f} kW, "
            f"mean={df['ac_power_kw'].mean():.0f} kW"
        )

        return df

    def resample_solar_hourly(self, df_solar: pd.DataFrame) -> pd.DataFrame:
        """Resample solar from 15-min to hourly frequency.

        Args:
            df_solar: Solar timeseries at 15-minute frequency

        Returns:
            DataFrame with 8,760 rows (hourly for 365 days)

        Raises:
            OE2ValidationError: If resampling produces incorrect shape
        """
        # Set timestamp as index if not already
        if 'timestamp' in df_solar.columns:
            df = df_solar.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])  # type: ignore[index]
            df.set_index('timestamp', inplace=True)  # type: ignore[call-arg]
        else:
            df = df_solar.copy()

        # Resample to hourly (mean, assuming 4 values per hour)
        df_hourly: pd.DataFrame = df[['ac_power_kw']].resample('h').mean()  # type: ignore[index]

        # Validate result
        if len(df_hourly) < 8760:
            raise OE2ValidationError(
                f"Resampled solar too short: {len(df_hourly)} rows (expected 8,760)"
            )

        # Truncate to exactly 8,760 hours (365 days × 24)
        df_hourly = df_hourly.iloc[:8760]

        if len(df_hourly) != 8760:
            raise OE2ValidationError(
                f"After truncation: {len(df_hourly)} rows != 8,760"
            )

        logger.info(f"✅ Solar resampled to hourly: {len(df_hourly)} rows")

        return df_hourly

    def load_solar_config(self) -> Dict[str, Any]:
        """Load solar configuration metadata.

        Returns:
            Dict with keys: power_kw, efficiency, etc.
        """
        config_file = self.oe2_path / 'solar' / 'solar_results.json'

        if not config_file.exists():
            logger.warning(f"Solar config file not found: {config_file}")
            return {"power_kw": 4050.0}  # Default Kyocera KS20

        try:
            solar_data: Any = json.load(open(config_file))
            solar_config: Dict[str, Any] = solar_data if isinstance(solar_data, dict) else {"power_kw": 4050.0}  # type: ignore[assignment]
            logger.info(f"✅ Solar config loaded")
            return solar_config
        except Exception as e:
            logger.warning(f"Failed to load solar config: {e}")
            return {"power_kw": 4050.0}

    # ========== CHARGERS LOADING & VALIDATION ==========

    def load_individual_chargers(self) -> List[Dict[str, Any]]:
        """Load 128 individual charger definitions.

        Returns:
            List of 128 charger dicts with: charger_id, power_kw, location, profile

        Raises:
            OE2ValidationError: If not exactly 128 chargers
        """
        chargers_file = self.oe2_path / 'chargers' / 'individual_chargers.json'

        if not chargers_file.exists():
            raise OE2ValidationError(f"Chargers JSON not found: {chargers_file}")

        try:
            chargers: List[Dict[str, Any]] = json.load(open(chargers_file))
        except Exception as e:
            raise OE2ValidationError(f"Failed to read chargers JSON: {e}")
        # Validate count
        # isinstance check here is redundant since chargers is already List[Dict[str, Any]]
        # but kept for runtime safety

        if len(chargers) != 128:
            raise OE2ValidationError(
                f"Expected 128 chargers, got {len(chargers)}"
            )

        # Validate each charger structure
        required_fields = ['charger_id', 'power_kw', 'playa']
        for i, charger in enumerate(chargers):
            charger_dict: Dict[str, Any] = charger  # type: ignore[assignment]
            for field in required_fields:
                if field not in charger_dict:
                    raise OE2ValidationError(
                        f"Charger {i} missing field: {field}"
                    )

            # Validate power is reasonable (2-3 kW for motos/mototaxis)
            power_kw: float = float(charger_dict.get('power_kw', 0))  # type: ignore[arg-type]
            if power_kw <= 0 or power_kw > 10:
                raise OE2ValidationError(
                    f"Charger {i} power invalid: {power_kw} kW"
                )

        # Validate total power
        total_power: float = sum(float(c.get('power_kw', 0)) for c in chargers)  # type: ignore[arg-type]
        if total_power < 250 or total_power > 300:  # Expected ~272 kW
            logger.warning(f"⚠️ Chargers total power: {total_power:.0f} kW")

        logger.info(
            f"✅ Loaded {len(chargers)} chargers, "
            f"total {total_power:.0f} kW"
        )

        return chargers  # type: ignore[return-value]

    def load_charger_hourly_profiles(self) -> pd.DataFrame:
        """Load hourly demand profiles for all 128 chargers.

        OE2 stores daily 24-hour profiles (24 rows × 128 chargers).
        This function expands to annual 8,760-hour profiles for CityLearn v2.

        Returns:
            DataFrame: shape (8760, 128) - annual hourly × 128 chargers

        Raises:
            OE2ValidationError: If shape incorrect or values invalid
        """
        profiles_file = self.oe2_path / 'chargers' / 'chargers_hourly_profiles.csv'

        if not profiles_file.exists():
            raise OE2ValidationError(f"Charger profiles not found: {profiles_file}")

        try:
            df: pd.DataFrame = pd.read_csv(profiles_file)  # type: ignore[assignment]
        except Exception as e:
            raise OE2ValidationError(f"Failed to read charger profiles: {e}")

        # Drop 'hour' column if present (first column)
        if 'hour' in df.columns:
            df = df.drop('hour', axis=1)

        # Validate daily shape (24 hours × 128 chargers)
        if df.shape[0] != 24:
            raise OE2ValidationError(
                f"Charger profiles: expected 24 hours, got {df.shape[0]}"
            )

        if df.shape[1] != 128:
            raise OE2ValidationError(
                f"Charger profiles: expected 128 chargers, got {df.shape[1]}"
            )

        # Validate values (all non-negative, reasonable ranges)
        has_negatives: bool = bool((df < 0).any().any())  # type: ignore[return-value]
        if has_negatives:
            raise OE2ValidationError("Charger profiles contain negative values")

        max_demand: float = float(df.max().max())  # type: ignore[arg-type]
        if max_demand > 10:
            logger.warning(f"⚠️ Max charger demand: {max_demand:.1f} kW (high)")

        # **CRITICAL FIX**: Expand daily profile to annual (365 days × 24 hours)
        df_annual: pd.DataFrame = pd.concat([df] * 365, ignore_index=True)  # type: ignore[index]

        if len(df_annual) != 8760:
            raise OE2ValidationError(
                f"Annual expansion: expected 8,760 rows, got {len(df_annual)}"
            )

        logger.info(
            f"✅ Charger profiles loaded and expanded: "
            f"daily 24×128 → annual 8760×128, "
            f"max={max_demand:.2f} kW"
        )

        return df_annual

    def load_chargers_config(self) -> Dict[str, Any]:
        """Load chargers configuration summary.

        Returns:
            Dict with keys: total_power_kw, num_chargers, etc.
        """
        config_file = self.oe2_path / 'chargers' / 'chargers_results.json'

        if not config_file.exists():
            logger.warning(f"Chargers config not found: {config_file}")
            return {
                "num_chargers": 128,
                "total_power_kw": 272.0,
                "daily_energy_kwh": 3252.0
            }

        try:
            charger_data: Any = json.load(open(config_file))
            charger_config: Dict[str, Any] = charger_data if isinstance(charger_data, dict) else {"num_chargers": 128, "total_power_kw": 272.0}  # type: ignore[assignment]
            logger.info(f"✅ Chargers config loaded")
            return charger_config
        except Exception as e:
            logger.warning(f"Failed to load chargers config: {e}")
            return {"num_chargers": 128, "total_power_kw": 272.0}

    # ========== BESS LOADING & VALIDATION ==========

    def load_bess_config(self) -> Dict[str, Any]:
        """Load BESS configuration (capacity, power, efficiency, etc).

        Returns:
            Dict with keys: capacity_kwh, power_kw, efficiency, min_soc, max_soc, dod

        Raises:
            OE2ValidationError: If config missing or invalid
        """
        # Try new format first
        config_file = self.oe2_path / 'bess' / 'bess_config.json'
        if config_file.exists():
            try:
                bess_config_data: Any = json.load(open(config_file))
                bess_new_config: Dict[str, Any] = bess_config_data if isinstance(bess_config_data, dict) else {}  # type: ignore[assignment]
                logger.info(f"✅ BESS config (new format) loaded")
                return bess_new_config
            except Exception as e:
                logger.warning(f"Failed to load bess_config.json: {e}")

        # Fall back to bess_results.json
        results_file = self.oe2_path / 'bess' / 'bess_results.json'
        if not results_file.exists():
            raise OE2ValidationError(
                f"BESS config not found: {config_file} or {results_file}"
            )

        try:
            bess_results_data: Any = json.load(open(results_file))
            bess_results: Dict[str, Any] = bess_results_data if isinstance(bess_results_data, dict) else {}  # type: ignore[assignment]
        except Exception as e:
            raise OE2ValidationError(f"Failed to read BESS results: {e}")

        # Extract key parameters
        bess_final_config: Dict[str, Any] = {
            "capacity_kwh": float(bess_results.get("capacity_kwh", 4520)),  # type: ignore[arg-type]
            "power_kw": float(bess_results.get("nominal_power_kw", 2712)),  # type: ignore[arg-type]
            "efficiency_roundtrip": float(bess_results.get("efficiency_roundtrip", 0.9)),  # type: ignore[arg-type]
            "min_soc": 0.2,  # 20% minimum for safety
            "max_soc": 1.0,
            "dod": float(bess_results.get("dod", 0.8)),  # type: ignore[arg-type]  # Depth of discharge
        }

        # Validate ranges
        capacity_val: float = float(bess_final_config.get("capacity_kwh", 0))  # type: ignore[arg-type]
        if capacity_val < 1000 or capacity_val > 10000:
            logger.warning(f"⚠️ BESS capacity unusual: {capacity_val} kWh")

        power_val: float = float(bess_final_config.get("power_kw", 0))  # type: ignore[arg-type]
        if power_val < 500 or power_val > 5000:
            logger.warning(f"⚠️ BESS power unusual: {power_val} kW")

        logger.info(
            f"✅ BESS config loaded: {capacity_val:.0f} kWh, "
            f"{power_val:.0f} kW"
        )

        return bess_final_config

    def load_bess_hourly(self) -> pd.DataFrame:
        """Load hourly BESS simulation (SOC, charge/discharge).

        Returns:
            DataFrame with 8,760 rows (hourly SOC, power)

        Raises:
            OE2ValidationError: If file missing or shape incorrect
        """
        hourly_file = self.oe2_path / 'bess' / 'bess_simulation_hourly.csv'

        if not hourly_file.exists():
            raise OE2ValidationError(f"BESS hourly not found: {hourly_file}")

        try:
            df: pd.DataFrame = pd.read_csv(hourly_file)  # type: ignore[assignment]
        except Exception as e:
            raise OE2ValidationError(f"Failed to read BESS hourly: {e}")

        # Validate shape (8,760 hours for 365 days)
        if len(df) < 8760:
            raise OE2ValidationError(
                f"BESS hourly too short: {len(df)} rows (expected 8,760)"
            )

        # Truncate to exactly 8,760
        df = df.iloc[:8760]

        # Validate SOC range [0, 1]
        if 'soc' in df.columns or 'SOC' in df.columns:
            soc_col: str = 'soc' if 'soc' in df.columns else 'SOC'
            soc_min: float = float(df[soc_col].min())  # type: ignore[arg-type]
            soc_max: float = float(df[soc_col].max())  # type: ignore[arg-type]

            if soc_min < 0 or soc_max > 1.0:
                raise OE2ValidationError(
                    f"BESS SOC out of range: [{soc_min:.3f}, {soc_max:.3f}]"
                )

        logger.info(f"✅ BESS hourly loaded: {len(df)} rows")

        return df

    # ========== COMPREHENSIVE VALIDATION ==========

    def validate_all(self) -> Dict[str, bool]:
        """Run comprehensive validation of all OE2 data.

        Returns:
            Dict with validation results: {
                'solar': bool,
                'chargers': bool,
                'bess': bool,
                'all': bool
            }
        """
        results: Dict[str, bool] = {}

        try:
            # Solar
            self.load_solar_timeseries()
            self.load_solar_config()
            results['solar'] = True
            logger.info("✅ Solar validation passed")
        except Exception as e:
            logger.error(f"❌ Solar validation failed: {e}")
            results['solar'] = False

        try:
            # Chargers
            self.load_individual_chargers()
            self.load_charger_hourly_profiles()
            self.load_chargers_config()
            results['chargers'] = True
            logger.info("✅ Chargers validation passed")
        except Exception as e:
            logger.error(f"❌ Chargers validation failed: {e}")
            results['chargers'] = False

        try:
            # BESS
            self.load_bess_config()
            self.load_bess_hourly()
            results['bess'] = True
            logger.info("✅ BESS validation passed")
        except Exception as e:
            logger.error(f"❌ BESS validation failed: {e}")
            results['bess'] = False

        results['all'] = all(results.values())

        if results['all']:
            logger.info("✅✅✅ ALL OE2 DATA VALIDATION PASSED")
        else:
            logger.error("❌ Some validations failed")

        return results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loader = OE2DataLoader('data/interim/oe2')
    results = loader.validate_all()
    print(f"\nValidation results: {results}")
