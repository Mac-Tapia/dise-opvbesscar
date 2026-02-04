#!/usr/bin/env python3
"""
================================================================================
VALIDACIÓN: Generación de Archivos Técnicos SAC
================================================================================

Verifica que SAC genera correctamente los 3 archivos técnicos:
1. result_sac.json - Métricas finales de simulación
2. timeseries_sac.csv - Datos horarios (8,760 registros)
3. trace_sac.csv - Trazas de observación/acción

Ejecución:
    python scripts/validate_sac_file_generation.py --check-only
    python scripts/validate_sac_file_generation.py --train --episodes 1
    python scripts/validate_sac_file_generation.py --full-analysis

================================================================================
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

import pandas as pd
import numpy as np


class FileValidation:
    """Valida y analiza los archivos técnicos generados por SAC."""

    def __init__(self, output_dir: Path | None = None):
        """Inicializa validador con directorio de salida."""
        if output_dir is None:
            output_dir = Path("outputs/oe3")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: Dict[str, Any] = {}

    def validate_result_json(self) -> Tuple[bool, str]:
        """Valida result_sac.json."""
        result_file = self.output_dir / "result_sac.json"

        if not result_file.exists():
            return False, f"[MISSING] result_sac.json not found at {result_file}"

        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validar campos críticos
            required_fields = [
                "agent", "steps", "carbon_kg", "grid_import_kwh",
                "pv_generation_kwh", "ev_charging_kwh", "timeseries_path"
            ]
            missing = [f for f in required_fields if f not in data]
            if missing:
                return False, f"[INVALID] Missing fields in result_sac.json: {missing}"

            # Verificar valores numéricos
            try:
                steps = int(data.get("steps", 0))
                carbon = float(data.get("carbon_kg", 0))
                grid_import = float(data.get("grid_import_kwh", 0))
                pv_gen = float(data.get("pv_generation_kwh", 0))
                ev_charging = float(data.get("ev_charging_kwh", 0))
            except (ValueError, TypeError) as e:
                return False, f"[INVALID] Non-numeric values in result_sac.json: {e}"

            # Validar rango de valores
            if steps <= 0 or steps > 26280:  # Max 3 episodes × 8,760 steps
                return False, f"[INVALID] Steps out of range: {steps}"

            file_size = result_file.stat().st_size
            self.results["result_json"] = {
                "status": "VALID",
                "file_size_bytes": file_size,
                "agent": data.get("agent"),
                "steps": steps,
                "carbon_kg": carbon,
                "grid_import_kwh": grid_import,
                "pv_generation_kwh": pv_gen,
                "ev_charging_kwh": ev_charging,
            }

            return True, f"[OK] result_sac.json valid ({file_size} bytes, {steps} steps)"

        except json.JSONDecodeError as e:
            return False, f"[INVALID] JSON parse error: {e}"
        except Exception as e:
            return False, f"[ERROR] Unexpected error reading result_sac.json: {e}"

    def validate_timeseries_csv(self) -> Tuple[bool, str]:
        """Valida timeseries_sac.csv."""
        ts_file = self.output_dir / "timeseries_sac.csv"

        if not ts_file.exists():
            return False, f"[MISSING] timeseries_sac.csv not found at {ts_file}"

        try:
            df = pd.read_csv(ts_file)

            # Validar dimensiones
            n_rows = len(df)
            n_cols = len(df.columns)

            if n_rows < 8760:
                return False, f"[INVALID] Expected ≥8,760 rows (hourly data), got {n_rows}"

            if n_rows > 26280:
                return False, f"[INVALID] Expected ≤26,280 rows (max 3 episodes), got {n_rows}"

            # Validar columnas críticas
            required_cols = [
                "timestamp", "grid_import_kwh", "grid_export_kwh",
                "ev_charging_kwh", "building_load_kwh", "pv_generation_kwh"
            ]
            missing_cols = [c for c in required_cols if c not in df.columns]
            if missing_cols:
                return False, f"[INVALID] Missing columns in timeseries_sac.csv: {missing_cols}"

            # Validar datos numéricos
            numeric_cols = [
                "grid_import_kwh", "grid_export_kwh", "ev_charging_kwh",
                "building_load_kwh", "pv_generation_kwh"
            ]
            for col in numeric_cols:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    if df[col].isna().sum() > 0:
                        return False, f"[INVALID] Non-numeric values in column '{col}'"
                except Exception as e:
                    return False, f"[INVALID] Error converting column '{col}': {e}"

            # Validar valores razonables
            grid_import_sum = df["grid_import_kwh"].sum()
            pv_gen_sum = df["pv_generation_kwh"].sum()
            ev_charging_sum = df["ev_charging_kwh"].sum()

            if grid_import_sum < 0:
                return False, f"[INVALID] Negative grid_import_kwh sum: {grid_import_sum}"

            if pv_gen_sum < 0:
                return False, f"[INVALID] Negative pv_generation_kwh sum: {pv_gen_sum}"

            file_size = ts_file.stat().st_size
            self.results["timeseries_csv"] = {
                "status": "VALID",
                "file_size_bytes": file_size,
                "rows": n_rows,
                "columns": n_cols,
                "grid_import_kwh_total": grid_import_sum,
                "pv_generation_kwh_total": pv_gen_sum,
                "ev_charging_kwh_total": ev_charging_sum,
                "data_quality": "EXCELLENT" if ev_charging_sum > 0 else "WARNING: No EV charging"
            }

            return True, f"[OK] timeseries_sac.csv valid ({n_rows} rows, {n_cols} cols, {file_size} bytes)"

        except pd.errors.ParserError as e:
            return False, f"[INVALID] CSV parse error: {e}"
        except Exception as e:
            return False, f"[ERROR] Unexpected error reading timeseries_sac.csv: {e}"

    def validate_trace_csv(self) -> Tuple[bool, str]:
        """Valida trace_sac.csv."""
        trace_file = self.output_dir / "trace_sac.csv"

        if not trace_file.exists():
            return False, f"[MISSING] trace_sac.csv not found at {trace_file}"

        try:
            df = pd.read_csv(trace_file)

            n_rows = len(df)
            n_cols = len(df.columns)

            # Validar que tiene algunos datos
            if n_rows == 0:
                return False, "[INVALID] trace_sac.csv is empty"

            # Validar columnas críticas
            if "step" not in df.columns:
                return False, "[INVALID] Missing 'step' column"

            # Trace puede tener estructura variable (depende del agente)
            # Mínimo requerido: step + algunas columnas de energía
            energy_cols = [c for c in df.columns if any(x in c.lower() for x in ["grid", "ev", "pv", "kwh", "reward"])]
            if len(energy_cols) == 0:
                return False, "[INVALID] No energy/reward columns found in trace"

            file_size = trace_file.stat().st_size

            self.results["trace_csv"] = {
                "status": "VALID",
                "file_size_bytes": file_size,
                "rows": n_rows,
                "columns": n_cols,
                "energy_columns": energy_cols[:5],  # Primeras 5 para brevedad
            }

            return True, f"[OK] trace_sac.csv valid ({n_rows} rows, {n_cols} cols, {file_size} bytes)"

        except pd.errors.ParserError as e:
            return False, f"[INVALID] CSV parse error: {e}"
        except Exception as e:
            return False, f"[ERROR] Unexpected error reading trace_sac.csv: {e}"

    def run_full_validation(self) -> Dict[str, Any]:
        """Ejecuta validación completa de los 3 archivos."""
        print("\n" + "=" * 80)
        print("SAC FILE GENERATION VALIDATION")
        print("=" * 80)
        print(f"Output Directory: {self.output_dir}")
        print()

        validation_status = {}

        # Validar result_sac.json
        print("[1/3] Validating result_sac.json...")
        ok, msg = self.validate_result_json()
        validation_status["result_sac.json"] = ok
        print(f"      {msg}\n")

        # Validar timeseries_sac.csv
        print("[2/3] Validating timeseries_sac.csv...")
        ok, msg = self.validate_timeseries_csv()
        validation_status["timeseries_sac.csv"] = ok
        print(f"      {msg}\n")

        # Validar trace_sac.csv
        print("[3/3] Validating trace_sac.csv...")
        ok, msg = self.validate_trace_csv()
        validation_status["trace_sac.csv"] = ok
        print(f"      {msg}\n")

        # Resumen
        print("=" * 80)
        all_valid = all(validation_status.values())
        if all_valid:
            print("[SUCCESS] All 3 SAC technical files generated correctly!")
            print("=" * 80)
            print("\nGenerated Files Summary:")
            for file_key, file_data in self.results.items():
                print(f"\n{file_key}:")
                for key, value in file_data.items():
                    if isinstance(value, (int, float)):
                        if key.endswith("_bytes"):
                            print(f"  {key}: {value:,} bytes")
                        elif key.endswith("_kwh_total"):
                            print(f"  {key}: {value:,.0f} kWh")
                        else:
                            print(f"  {key}: {value}")
                    else:
                        print(f"  {key}: {value}")
        else:
            print("[FAILURE] Some SAC technical files are invalid or missing!")
            print(f"         result_sac.json: {'OK' if validation_status.get('result_sac.json') else 'MISSING/INVALID'}")
            print(f"         timeseries_sac.csv: {'OK' if validation_status.get('timeseries_sac.csv') else 'MISSING/INVALID'}")
            print(f"         trace_sac.csv: {'OK' if validation_status.get('trace_sac.csv') else 'MISSING/INVALID'}")
            print("=" * 80)
            sys.exit(1)

        return {
            "timestamp": datetime.now().isoformat(),
            "validation_status": validation_status,
            "all_valid": all_valid,
            "details": self.results
        }

    def run_check_only(self):
        """Solo verificar si existen los archivos sin validar contenido."""
        print("\n" + "=" * 80)
        print("SAC FILE EXISTENCE CHECK")
        print("=" * 80)
        print(f"Output Directory: {self.output_dir}\n")

        files_to_check = [
            "result_sac.json",
            "timeseries_sac.csv",
            "trace_sac.csv"
        ]

        exists_count = 0
        for filename in files_to_check:
            file_path = self.output_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  [EXISTS] {filename} ({size:,} bytes)")
                exists_count += 1
            else:
                print(f"  [MISSING] {filename}")

        print("\n" + "=" * 80)
        print(f"Result: {exists_count}/3 files exist")
        if exists_count == 3:
            print("Status: READY FOR FULL VALIDATION")
        else:
            print("Status: INCOMPLETE - Run SAC training first")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Validate SAC technical file generation"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check file existence (fast)"
    )
    parser.add_argument(
        "--full-analysis",
        action="store_true",
        help="Full validation with detailed analysis"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/oe3",
        help="Output directory (default: outputs/oe3)"
    )

    args = parser.parse_args()

    validator = FileValidation(output_dir=args.output_dir)

    if args.check_only:
        validator.run_check_only()
    else:
        # Full validation (default)
        result = validator.run_full_validation()

        # Guardar reporte de validación
        report_path = Path("reports/sac_file_validation_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print(f"\nValidation report saved: {report_path}")


if __name__ == "__main__":
    main()
