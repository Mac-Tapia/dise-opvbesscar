#!/usr/bin/env python
"""
POST-BUILD VALIDATION SYSTEM
Validar TODOS los datos construidos para CityLearn v2 inmediatamente después de build_citylearn_dataset()

Ejecuta automáticamente tras cada construcción de dataset para asegurar que:
1. Baseline CSV tiene 8,760 filas
2. Schema JSON tiene estructura correcta
3. Charger simulation files existen
4. Energy CSV tiene datos válidos
5. BESS configuration es correcta
6. Sync checks entre OE2 → CityLearn

INTEGRACIÓN: Este script es llamado por run_oe3_build_dataset.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class CityLearnDataValidator:
    """Validador completo POST-construcción para CityLearn v2 datasets."""

    def __init__(self, processed_dir: Path):
        self.processed_dir = processed_dir
        self.citylearn_dir = processed_dir / "citylearn"
        self.errors = []
        self.warnings = []
        self.results = {}

    def run_all_checks(self) -> bool:
        """Ejecutar todas las validaciones. Retorna True si todo OK, False si hay errores críticos."""
        logger.info("")
        logger.info("="*80)
        logger.info("POST-BUILD VALIDATION: CityLearn v2 Dataset")
        logger.info("="*80)
        logger.info("")

        checks = [
            ("Schema structure", self.check_schema_structure),
            ("Baseline CSV", self.check_baseline_csv),
            ("Energy simulation CSV", self.check_energy_simulation),
            ("Charger simulation files", self.check_charger_files),
            ("BESS configuration", self.check_bess_config),
            ("Solar data sync", self.check_solar_sync),
            ("Data integrity", self.check_data_integrity),
        ]

        for name, check_fn in checks:
            try:
                logger.info(f"[{name}] Running...")
                result = check_fn()
                self.results[name] = result
                status = "✓ PASS" if result["status"] == "OK" else "⚠ WARN" if result["status"] == "WARN" else "✗ FAIL"
                logger.info(f"[{name}] {status}")
            except Exception as e:
                logger.error(f"[{name}] ERROR: {e}")
                self.results[name] = {"status": "ERROR", "error": str(e)}
                self.errors.append(f"{name}: {e}")

        # Summary
        logger.info("")
        logger.info("="*80)
        self._print_summary()
        logger.info("="*80)
        logger.info("")

        return len(self.errors) == 0

    def check_schema_structure(self) -> dict:
        """Verificar que schema.json tiene estructura correcta."""
        result = {"status": "FAIL", "details": {}}

        schema_files = list(self.citylearn_dir.glob("schema*.json"))
        if not schema_files:
            self.errors.append("Schema file not found")
            return result

        schema_path = schema_files[0]
        with open(schema_path) as f:
            schema = json.load(f)

        # Check basic structure
        if "buildings" not in schema:
            self.errors.append("Schema: missing 'buildings' key")
            return result

        if not schema["buildings"]:
            self.errors.append("Schema: 'buildings' is empty")
            return result

        building = list(schema["buildings"].values())[0]

        # Check critical components
        checks_passed = 0

        # PV
        has_pv = isinstance(building.get("pv"), dict) or isinstance(building.get("photovoltaic"), dict)
        if has_pv:
            checks_passed += 1
        else:
            self.warnings.append("Schema: PV not configured")

        # BESS
        has_bess = isinstance(building.get("electrical_storage"), dict)
        if has_bess:
            checks_passed += 1
        else:
            self.warnings.append("Schema: BESS not configured")

        # Chargers
        chargers = building.get("electric_vehicle_chargers", {})
        if chargers and len(chargers) == 128:
            checks_passed += 1
        else:
            self.warnings.append(f"Schema: Expected 128 chargers, found {len(chargers)}")

        # Time settings
        if schema.get("episode_time_steps") == 8760:
            checks_passed += 1
        else:
            self.warnings.append(f"Schema: episode_time_steps = {schema.get('episode_time_steps')}, expected 8760")

        if checks_passed >= 3:
            result["status"] = "OK"
        else:
            result["status"] = "WARN"

        result["details"] = {
            "schema_file": str(schema_path),
            "buildings": len(schema["buildings"]),
            "pv_configured": has_pv,
            "bess_configured": has_bess,
            "chargers": len(chargers),
            "checks_passed": checks_passed
        }

        return result

    def check_baseline_csv(self) -> dict:
        """Verificar que baseline_full_year_hourly.csv es válido."""
        result = {"status": "FAIL", "details": {}}

        baseline_files = list(self.processed_dir.glob("baseline*.csv"))
        if not baseline_files:
            self.errors.append("Baseline CSV not found in outputs/oe3/")
            return result

        baseline_path = baseline_files[0]
        df = pd.read_csv(baseline_path)

        # Check length
        if len(df) != 8760:
            self.errors.append(f"Baseline: Expected 8,760 rows, got {len(df)}")
            return result

        # Check columns
        required_cols = ["pv_generation", "ev_demand", "mall_load", "bess_soc", "co2_emissions"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            self.errors.append(f"Baseline: Missing columns {missing_cols}")
            return result

        # Check data ranges
        if (df["pv_generation"] < 0).any():
            self.errors.append("Baseline: pv_generation has negative values")
            return result

        if (df["ev_demand"] < 0).any():
            self.errors.append("Baseline: ev_demand has negative values")
            return result

        if (df["bess_soc"] < 0).any() or (df["bess_soc"] > 100).any():
            self.errors.append(f"Baseline: bess_soc outside [0,100] range")
            return result

        # Warnings for unusual values
        if df["pv_generation"].sum() < 7000000:
            self.warnings.append(f"Baseline: pv_generation sum too low: {df['pv_generation'].sum():.0f} kWh")

        result["status"] = "OK"
        result["details"] = {
            "rows": len(df),
            "columns": len(df.columns),
            "pv_generation_sum": float(df["pv_generation"].sum()),
            "ev_demand_sum": float(df["ev_demand"].sum()),
            "mall_load_sum": float(df["mall_load"].sum()),
            "bess_soc_min": float(df["bess_soc"].min()),
            "bess_soc_max": float(df["bess_soc"].max())
        }

        return result

    def check_energy_simulation(self) -> dict:
        """Verificar que energy_simulation.csv tiene datos válidos."""
        result = {"status": "FAIL", "details": {}}

        energy_files = list(self.citylearn_dir.glob("**/energy_simulation.csv"))
        if not energy_files:
            self.warnings.append("energy_simulation.csv not found (may be OK if CityLearn generates it)")
            result["status"] = "WARN"
            return result

        energy_path = energy_files[0]
        df = pd.read_csv(energy_path)

        if len(df) != 8760:
            self.errors.append(f"energy_simulation: Expected 8,760 rows, got {len(df)}")
            return result

        # Find solar and load columns
        solar_cols = [c for c in df.columns if "solar" in c.lower() or "generation" in c.lower()]
        load_cols = [c for c in df.columns if "non_shiftable" in c.lower() or "load" in c.lower()]

        if solar_cols:
            solar_sum = df[solar_cols[0]].sum()
            if solar_sum > 0:
                result["details"]["solar_sum"] = float(solar_sum)
        else:
            self.warnings.append("energy_simulation: No solar generation column found")

        if load_cols:
            load_sum = df[load_cols[0]].sum()
            if load_sum > 0:
                result["details"]["load_sum"] = float(load_sum)
        else:
            self.warnings.append("energy_simulation: No load column found")

        result["status"] = "OK"
        return result

    def check_charger_files(self) -> dict:
        """Verificar que todos 128 charger_simulation_*.csv existen."""
        result = {"status": "FAIL", "details": {}}

        charger_files = sorted(self.citylearn_dir.glob("*/charger_simulation_*.csv"))

        if len(charger_files) == 0:
            self.warnings.append("No charger_simulation files found (may be OK if CityLearn creates them)")
            result["status"] = "WARN"
            return result

        if len(charger_files) < 128:
            self.warnings.append(f"Expected 128 charger files, found {len(charger_files)}")

        # Check first charger file
        if charger_files:
            df = pd.read_csv(charger_files[0])
            if len(df) != 8760:
                self.errors.append(f"charger_simulation: Expected 8,760 rows, got {len(df)}")
                return result

        result["status"] = "OK"
        result["details"] = {
            "charger_files_found": len(charger_files),
            "expected": 128,
            "complete": len(charger_files) == 128
        }

        return result

    def check_bess_config(self) -> dict:
        """Verificar que BESS está correctamente configurado."""
        result = {"status": "FAIL", "details": {}}

        # Check schema
        schema_files = list(self.citylearn_dir.glob("schema*.json"))
        if not schema_files:
            self.warnings.append("Cannot validate BESS: schema not found")
            result["status"] = "WARN"
            return result

        with open(schema_files[0]) as f:
            schema = json.load(f)

        building = list(schema["buildings"].values())[0]
        bess = building.get("electrical_storage", {})

        if not bess:
            self.warnings.append("BESS not configured in schema")
            result["status"] = "WARN"
            return result

        capacity = bess.get("capacity") or bess.get("attributes", {}).get("capacity", 0)
        power = bess.get("nominal_power") or bess.get("attributes", {}).get("nominal_power", 0)

        if capacity != 4520:
            self.warnings.append(f"BESS capacity: {capacity} (expected 4520)")

        if power != 2712:
            self.warnings.append(f"BESS power: {power} (expected 2712)")

        result["status"] = "OK"
        result["details"] = {
            "capacity_kwh": capacity,
            "nominal_power_kw": power,
            "efficiency": bess.get("efficiency", bess.get("attributes", {}).get("efficiency", "N/A"))
        }

        return result

    def check_solar_sync(self) -> dict:
        """Verificar que datos solares están sincronizados entre archivos."""
        result = {"status": "FAIL", "details": {}}

        # Check baseline
        baseline_files = list(self.processed_dir.glob("baseline*.csv"))
        if not baseline_files:
            self.warnings.append("Cannot validate solar sync: baseline not found")
            result["status"] = "WARN"
            return result

        df_baseline = pd.read_csv(baseline_files[0])
        solar_baseline = df_baseline["pv_generation"].sum() if "pv_generation" in df_baseline.columns else 0

        # Expected from OE2
        oe2_solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
        if oe2_solar_path.exists():
            df_oe2 = pd.read_csv(oe2_solar_path)
            solar_cols = [c for c in df_oe2.columns if "ac_power" in c.lower() or "generation" in c.lower()]
            if solar_cols:
                solar_oe2 = df_oe2[solar_cols[0]].sum()
                diff_percent = abs(solar_baseline - solar_oe2) / solar_oe2 * 100 if solar_oe2 > 0 else 0

                if diff_percent > 5:
                    self.warnings.append(f"Solar sync: {diff_percent:.1f}% difference between OE2 and baseline")

                result["details"] = {
                    "oe2_solar_kwh": float(solar_oe2),
                    "baseline_solar_kwh": float(solar_baseline),
                    "difference_percent": float(diff_percent),
                    "in_sync": diff_percent <= 5
                }

        result["status"] = "OK"
        return result

    def check_data_integrity(self) -> dict:
        """Verificar integridad general de datos."""
        result = {"status": "FAIL", "details": {}}

        baseline_files = list(self.processed_dir.glob("baseline*.csv"))
        if not baseline_files:
            self.errors.append("Cannot check integrity: baseline not found")
            return result

        df = pd.read_csv(baseline_files[0])

        # Check for NaN
        nan_cols = df.columns[df.isna().any()].tolist()
        if nan_cols:
            self.errors.append(f"Data integrity: NaN values found in {nan_cols}")
            return result

        # Check for infinity
        inf_cols = df.columns[(df == np.inf).any() | (df == -np.inf).any()].tolist()
        if inf_cols:
            self.errors.append(f"Data integrity: Infinity values found in {inf_cols}")
            return result

        # Check time features
        if "hour" in df.columns:
            if not ((df["hour"] >= 0) & (df["hour"] <= 23)).all():
                self.warnings.append("Data integrity: hour values outside [0,23]")

        result["status"] = "OK"
        result["details"] = {
            "rows": len(df),
            "nan_issues": 0,
            "inf_issues": 0,
            "all_checks_passed": True
        }

        return result

    def _print_summary(self):
        """Imprimir resumen de validación."""
        passed = sum(1 for r in self.results.values() if r.get("status") == "OK")
        warned = sum(1 for r in self.results.values() if r.get("status") == "WARN")
        failed = sum(1 for r in self.results.values() if r.get("status") == "FAIL")

        logger.info("")
        logger.info("VALIDATION SUMMARY")
        logger.info("-" * 80)

        for check_name, result in self.results.items():
            status = result.get("status", "UNKNOWN")
            icon = "✓" if status == "OK" else "⚠" if status == "WARN" else "✗"
            logger.info(f"  {icon} {check_name}: {status}")

        logger.info("")
        logger.info(f"  Total: {passed} PASS, {warned} WARN, {failed} FAIL")

        if self.errors:
            logger.info("")
            logger.info("ERRORS:")
            for error in self.errors:
                logger.error(f"  ✗ {error}")

        if self.warnings:
            logger.info("")
            logger.info("WARNINGS:")
            for warning in self.warnings:
                logger.warning(f"  ⚠ {warning}")

        if passed == len(self.results) and not self.errors:
            logger.info("")
            logger.info("✅ POST-BUILD VALIDATION: ALL CHECKS PASSED")
        else:
            logger.info("")
            logger.info("❌ POST-BUILD VALIDATION: SOME CHECKS FAILED")


def validate_citylearn_dataset(processed_dir: Path) -> bool:
    """
    Ejecutar validación POST-construcción.

    Args:
        processed_dir: Path a outputs/processed/

    Returns:
        True si validación exitosa, False si hay errores críticos
    """
    validator = CityLearnDataValidator(processed_dir)
    return validator.run_all_checks()


if __name__ == "__main__":
    processed_path = Path("outputs/processed")
    success = validate_citylearn_dataset(processed_path)
    sys.exit(0 if success else 1)
