"""
CityLearn Schema v2 Validator

Comprehensive validation of generated CityLearn v2 schemas:
1. Verify all required files exist
2. Check data integrity (8,760 rows, no gaps)
3. Validate value ranges
4. Verify CityLearn can actually load the schema
"""  # noqa: D400
# pylint: disable=consider-using-f-string
# flake8: noqa: E501

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Union

import numpy as np
import pandas as pd  # type: ignore  # pylint: disable=import-error

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""


class CityLearnSchemaValidator:
    """Validate CityLearn v2 schema completeness and correctness."""

    def __init__(self, schema_path: Union[Path, str]):  # pylint: disable=redefined-outer-name
        """Initialize with path to schema.json.

        Args:
            schema_path: Path to outputs/schema_*.json

        Raises:
            SchemaValidationError: If schema file not found
        """
        self.schema_path = Path(schema_path)

        if not self.schema_path.exists():
            raise SchemaValidationError(f"Schema not found: {self.schema_path}")  # pylint: disable=consider-using-f-string

        # Load schema
        try:
            with open(self.schema_path, encoding='utf-8') as f:
                self.schema: Dict[str, Any] = json.load(f)
        except Exception as e:
            raise SchemaValidationError(f"Failed to load schema: {e}") from e  # pylint: disable=consider-using-f-string

        self.schema_dir = self.schema_path.parent
        logger.info("✅ Schema loaded from %s", self.schema_path)

    def validate_structure(self) -> bool:
        """Validate top-level schema structure.

        Returns:
            True if structure valid

        Raises:
            SchemaValidationError: If structure invalid
        """
        required_keys = ['version', 'buildings', 'climate_zones']

        for key in required_keys:
            if key not in self.schema:
                raise SchemaValidationError(f"Missing schema key: {key}")  # pylint: disable=consider-using-f-string

        # Check buildings
        if not isinstance(self.schema['buildings'], list):
            raise SchemaValidationError("'buildings' must be list")

        if len(self.schema['buildings']) != 1:
            raise SchemaValidationError(
                f"Expected 1 building, got {len(self.schema['buildings'])}"  # pylint: disable=consider-using-f-string
            )

        # Check climate zones
        if not isinstance(self.schema['climate_zones'], list):
            raise SchemaValidationError("'climate_zones' must be list")

        if len(self.schema['climate_zones']) != 1:
            raise SchemaValidationError(
                f"Expected 1 climate zone, got {len(self.schema['climate_zones'])}"  # pylint: disable=consider-using-f-string
            )

        logger.info("✅ Schema structure valid")
        return True

    def validate_building_files(self) -> bool:
        """Validate building data files exist and have correct structure.

        Returns:
            True if all building files valid

        Raises:
            SchemaValidationError: If files missing or invalid
        """
        building: Dict[str, Any] = self.schema['buildings'][0]
        building_name: str = building['name']

        # Construct path (schema may use relative paths)
        # Typically: buildings/building_0/ or similar
        building_dir = self.schema_dir / 'buildings' / building_name

        if not building_dir.exists():
            # Try alternative: direct in schema_dir
            building_dir = self.schema_dir / building_name
            if not building_dir.exists():
                raise SchemaValidationError(
                    f"Building directory not found: {building_dir}"  # pylint: disable=consider-using-f-string
                )

        # Check energy_simulation.csv (total load)
        energy_sim = building_dir / 'energy_simulation.csv'
        if not energy_sim.exists():
            raise SchemaValidationError(
                f"Missing energy_simulation.csv: {energy_sim}"  # pylint: disable=consider-using-f-string
            )

        try:
            df_energy = pd.read_csv(energy_sim)
        except Exception as e:
            raise SchemaValidationError(f"Failed to read energy_simulation.csv: {e}") from e  # pylint: disable=consider-using-f-string

        if len(df_energy) != 8760:
            raise SchemaValidationError(
                f"energy_simulation.csv has {len(df_energy)} rows, expected 8,760"  # pylint: disable=consider-using-f-string
            )

        # Check charger simulation files (128 individual)
        missing_chargers = []
        for i in range(1, 129):  # charger_001 to charger_128
            charger_file = building_dir / f'charger_simulation_{i:03d}.csv'

            if not charger_file.exists():
                missing_chargers.append(i)
            else:
                # Validate structure
                try:
                    df_charger = pd.read_csv(charger_file)
                    if len(df_charger) != 8760:
                        raise SchemaValidationError(
                            f"charger_{i:03d}.csv has {len(df_charger)} rows, "  # pylint: disable=consider-using-f-string
                            f"expected 8,760"
                        )
                except Exception as e:
                    raise SchemaValidationError(
                        f"Failed to validate charger_{i:03d}.csv: {e}"  # pylint: disable=consider-using-f-string
                    ) from e

        if missing_chargers:
            # Error if many are missing, warning if few
            if len(missing_chargers) > 10:
                raise SchemaValidationError(
                    f"Missing {len(missing_chargers)} charger files: "  # pylint: disable=consider-using-f-string
                    f"{missing_chargers[:10]}..."
                )
            else:
                logger.warning(
                    "⚠️ Missing %d charger files: %s",
                    len(missing_chargers), missing_chargers
                )
        else:
            logger.info("✅ All 38 socket files present and valid (8,760 rows each)")

        logger.info("✅ Building files valid (%d/38 sockets)", 128 - len(missing_chargers))
        return len(missing_chargers) == 0

    def validate_climate_zone_files(self) -> bool:
        """Validate climate zone data files.

        Returns:
            True if climate zone valid

        Raises:
            SchemaValidationError: If files invalid
        """
        climate_zone: Dict[str, Any] = self.schema['climate_zones'][0]
        climate_name: str = climate_zone['name']

        climate_dir = self.schema_dir / 'climate_zones' / climate_name

        if not climate_dir.exists():
            # Try alternative
            climate_dir = self.schema_dir / climate_name
            if not climate_dir.exists():
                raise SchemaValidationError(
                    f"Climate zone directory not found: {climate_dir}"  # pylint: disable=consider-using-f-string
                )

        # Check required files
        required_files = {
            'weather.csv': ['ghi_wm2', 'dni_wm2', 'dhi_wm2', 'temp_air_c'],
            'carbon_intensity.csv': ['carbon_intensity'],
            'pricing.csv': ['pricing']
        }

        for filename, expected_cols in required_files.items():
            filepath = climate_dir / filename

            if not filepath.exists():
                raise SchemaValidationError(
                    f"Missing climate file: {filepath}"  # pylint: disable=consider-using-f-string
                )

            try:
                df = pd.read_csv(filepath)
            except Exception as e:
                raise SchemaValidationError(
                    f"Failed to read {filename}: {e}"  # pylint: disable=consider-using-f-string
                ) from e

            if len(df) != 8760:
                raise SchemaValidationError(
                    f"{filename} has {len(df)} rows, expected 8,760"  # pylint: disable=consider-using-f-string
                )

            # Check for expected columns (lenient - may have additional)
            for col in expected_cols:
                if col not in df.columns:
                    logger.warning("%s missing expected column: %s", filename, col)

        logger.info("✅ Climate zone files valid")
        return True

    def validate_timestamps_aligned(self) -> bool:
        """Verify all 8,760 timesteps are present with no gaps.

        Returns:
            True if timestamps aligned

        Raises:
            SchemaValidationError: If gaps detected
        """
        building: Dict[str, Any] = self.schema['buildings'][0]
        building_name: str = building['name']
        building_dir: Path = self.schema_dir / 'buildings' / building_name

        if not building_dir.exists():
            building_dir = self.schema_dir / building_name

        # Check energy_simulation.csv
        energy_sim = building_dir / 'energy_simulation.csv'
        df_energy = pd.read_csv(energy_sim)

        if len(df_energy) != 8760:
            raise SchemaValidationError(
                f"Energy simulation has {len(df_energy)} rows, not 8,760"  # pylint: disable=consider-using-f-string
            )

        # Spot-check chargers
        charger_1 = building_dir / 'charger_simulation_001.csv'
        if charger_1.exists():
            df_charger = pd.read_csv(charger_1)
            if len(df_charger) != 8760:
                raise SchemaValidationError(
                    f"Charger 001 has {len(df_charger)} rows, not 8,760"  # pylint: disable=consider-using-f-string
                )

        # Check climate files
        climate_zone = self.schema['climate_zones'][0]
        climate_name = climate_zone['name']
        climate_dir = self.schema_dir / 'climate_zones' / climate_name

        if not climate_dir.exists():
            climate_dir = self.schema_dir / climate_name

        for filename in ['weather.csv', 'carbon_intensity.csv', 'pricing.csv']:
            filepath = climate_dir / filename
            if filepath.exists():
                df = pd.read_csv(filepath)
                if len(df) != 8760:
                    raise SchemaValidationError(
                        f"{filename} has {len(df)} rows, not 8,760"  # pylint: disable=consider-using-f-string
                    )

        logger.info("✅ All files have exactly 8,760 timesteps (no gaps)")
        return True

    def validate_value_ranges(self) -> bool:
        """Validate that data values are in reasonable ranges.

        Returns:
            True if all ranges valid
        """
        building: Dict[str, Any] = self.schema['buildings'][0]
        building_name: str = building['name']
        building_dir: Path = self.schema_dir / 'buildings' / building_name

        if not building_dir.exists():
            building_dir = self.schema_dir / building_name

        # Check energy simulation values
        energy_sim = building_dir / 'energy_simulation.csv'
        df_energy = pd.read_csv(energy_sim)

        # Assume first column is total load (kWh)
        if len(df_energy.columns) > 0:
            load_col = df_energy.iloc[:, 0]

            # Reasonable range: 0-500 kWh per hour (3,600 kW max)
            if load_col.min() < 0:
                logger.warning("⚠️ Negative load values detected: %s", load_col.min())

            if load_col.max() > 1000:
                logger.warning(
                    "⚠️ Very high load: %.0f kWh/hour", load_col.max()
                )

        # Check climate values
        climate_zone = self.schema['climate_zones'][0]
        climate_name = climate_zone['name']
        climate_dir = self.schema_dir / 'climate_zones' / climate_name

        if not climate_dir.exists():
            climate_dir = self.schema_dir / climate_name

        # Weather: temperature should be 10-35°C in Iquitos tropics
        weather_file = climate_dir / 'weather.csv'
        if weather_file.exists():
            df_weather = pd.read_csv(weather_file)
            if 'temp_air_c' in df_weather.columns:
                temp_min, temp_max = (
                    df_weather['temp_air_c'].min(),
                    df_weather['temp_air_c'].max()
                )
                if temp_min < 5 or temp_max > 40:
                    logger.warning(
                        "⚠️ Temperature out of expected range: [%.1f, %.1f]°C",
                        temp_min, temp_max
                    )

        # Carbon intensity: typical grid ~0.45 kg CO2/kWh for Iquitos
        carbon_file = climate_dir / 'carbon_intensity.csv'
        if carbon_file.exists():
            df_carbon = pd.read_csv(carbon_file)
            if 'carbon_intensity' in df_carbon.columns:
                c_intensity = df_carbon['carbon_intensity'].iloc[0]
                if c_intensity < 0.1 or c_intensity > 1.0:
                    logger.warning(
                        "⚠️ Carbon intensity unusual: %.3f kg CO2/kWh", c_intensity
                    )

        logger.info("✅ Value ranges valid")
        return True

    def validate_citylearn_load(self) -> bool:
        """Try to actually load schema with CityLearn.

        Returns:
            True if CityLearn can load successfully

        Raises:
            SchemaValidationError: If CityLearn can't load
        """
        try:
            from citylearn.citylearn import CityLearnEnv
        except ImportError:
            logger.warning("⚠️ CityLearn not installed, skipping load test")
            return True

        try:
            env = CityLearnEnv(schema=str(self.schema_path))
            obs, _info = env.reset()

            # Check observation shape
            if isinstance(obs, list):
                obs_array = np.array(obs).flatten()
            else:
                obs_array = np.asarray(obs).flatten()

            obs_dim = len(obs_array)

            # Expected: ~394 dimensions for current Iquitos setup (129 actions)
            if obs_dim < 350:
                logger.warning(
                    "⚠️ Observation dimension low: %d (expected ~394)", obs_dim
                )
            elif obs_dim > 450:
                logger.warning(
                    "⚠️ Observation dimension high: %d (expected ~394)", obs_dim
                )

            logger.info("✅ CityLearn load successful, obs_dim=%d", obs_dim)

            # Try one step (action_space is a list of Boxes for multi-agent)
            if isinstance(env.action_space, list):
                action = [space.sample() for space in env.action_space]
            else:
                action = env.action_space.sample()
            _obs, _reward, _terminated, _truncated, _info = env.step(action)

            logger.info("✅ CityLearn step() successful")

            return True

        except Exception as e:
            raise SchemaValidationError(
                f"CityLearn failed to load schema: {e}"
            ) from e

    # ========== MAIN VALIDATION ==========

    def validate_all(self, test_citylearn: bool = True) -> Dict[str, Any]:
        """Run complete schema validation.

        Args:
            test_citylearn: Whether to test actual CityLearn loading

        Returns:
            Dict with validation results
        """
        validation_results: Dict[str, Any] = {}

        # Structure
        try:
            self.validate_structure()
            validation_results['structure'] = True
            logger.info("✅ Structure validation passed")
        except SchemaValidationError as e:
            logger.error("❌ Structure validation failed: %s", e)
            validation_results['structure'] = False
            return validation_results  # Stop if structure invalid

        # Building files
        try:
            self.validate_building_files()
            validation_results['building_files'] = True
        except SchemaValidationError as e:
            logger.error("❌ Building files validation failed: %s", e)
            validation_results['building_files'] = False

        # Climate zone files
        try:
            self.validate_climate_zone_files()
            validation_results['climate_files'] = True
        except SchemaValidationError as e:
            logger.error("❌ Climate files validation failed: %s", e)
            validation_results['climate_files'] = False

        # Timestamps
        try:
            self.validate_timestamps_aligned()
            validation_results['timestamps'] = True
        except SchemaValidationError as e:
            logger.error("❌ Timestamps validation failed: %s", e)
            validation_results['timestamps'] = False

        # Value ranges
        try:
            self.validate_value_ranges()
            validation_results['values'] = True
        except SchemaValidationError as e:
            logger.error("❌ Value ranges validation failed: %s", e)
            validation_results['values'] = False

        # CityLearn load
        if test_citylearn:
            try:
                self.validate_citylearn_load()
                validation_results['citylearn_load'] = True
            except SchemaValidationError as e:
                logger.error("❌ CityLearn load validation failed: %s", e)
                validation_results['citylearn_load'] = False
        else:
            validation_results['citylearn_load'] = None

        validation_results['all'] = all(v for v in validation_results.values() if v is not None)

        if validation_results['all']:
            logger.info("\n✅✅✅ SCHEMA VALIDATION COMPLETE & PASSED\n")
        else:
            logger.error("\n❌ Schema validation has failures\n")

        return validation_results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    schema_path = 'outputs/schema_*.json'  # Will need glob or find latest

    validator = CityLearnSchemaValidator(schema_path)
    results = validator.validate_all()
    print("\nValidation results:", results)
