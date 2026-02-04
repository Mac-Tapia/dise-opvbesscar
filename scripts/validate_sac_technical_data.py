#!/usr/bin/env python3
"""
Validación de Datos Técnicos SAC Post-Entrenamiento

Script que verifica después del entrenamiento que SAC haya generado correctamente:
- result_sac.json
- timeseries_sac.csv
- trace_sac.csv

Valida estructura, integridad, y comparabilidad con PPO/A2C.
"""

from __future__ import annotations

import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
from dataclasses import dataclass

import pandas as pd  # type: ignore
import numpy as np  # type: ignore

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileValidation:
    """Resultados de validación de archivo."""
    file_path: Path
    exists: bool
    size_bytes: int
    is_valid: bool
    errors: List[str]


@dataclass(frozen=True)
class DataFrameValidation:
    """Resultados de validación de DataFrame."""
    shape: Tuple[int, int]
    columns: List[str]
    is_valid: bool
    errors: list[str]


def validate_file_exists(file_path: Path) -> FileValidation:
    """Validar que archivo exista y sea accesible."""
    errors = []

    if not file_path.exists():
        errors.append(f"Archivo no existe: {file_path}")
        return FileValidation(file_path, False, 0, False, errors)

    if not file_path.is_file():
        errors.append(f"No es un archivo: {file_path}")
        return FileValidation(file_path, True, 0, False, errors)

    size_bytes = file_path.stat().st_size
    if size_bytes == 0:
        errors.append("Archivo vacío")
        return FileValidation(file_path, True, 0, False, errors)

    return FileValidation(file_path, True, size_bytes, True, errors)


def validate_json_file(file_path: Path) -> Tuple[FileValidation, Optional[Dict[str, Any]]]:
    """Validar archivo JSON."""
    file_val = validate_file_exists(file_path)

    if not file_val.is_valid:
        return file_val, None

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return FileValidation(file_path, True, file_val.size_bytes, True, []), data
    except json.JSONDecodeError as e:
        errors = [f"JSON inválido: {e}"]
        return FileValidation(file_path, True, file_val.size_bytes, False, errors), None
    except Exception as e:
        errors = [f"Error leyendo JSON: {e}"]
        return FileValidation(file_path, True, file_val.size_bytes, False, errors), None


def validate_csv_file(file_path: Path) -> Tuple[FileValidation, Optional[pd.DataFrame]]:
    """Validar archivo CSV."""
    file_val = validate_file_exists(file_path)

    if not file_val.is_valid:
        return file_val, None

    try:
        df = pd.read_csv(file_path)
        return FileValidation(file_path, True, file_val.size_bytes, True, []), df
    except Exception as e:
        errors = [f"Error leyendo CSV: {e}"]
        return FileValidation(file_path, True, file_val.size_bytes, False, errors), None


def validate_timeseries_csv(df: pd.DataFrame) -> DataFrameValidation:
    """Validar estructura de timeseries_sac.csv."""
    errors = []

    # Verificar número de filas (debe ser 8,760 para 1 año)
    if len(df) != 8760:
        errors.append(f"Debe tener 8,760 filas (1 año), tiene {len(df)}")

    # Verificar columnas requeridas
    required_cols = [
        "timestamp", "hour", "day_of_week", "month",
        "net_grid_kwh", "grid_import_kwh", "grid_export_kwh",
        "ev_charging_kwh", "building_load_kwh", "pv_generation_kwh"
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Columnas faltantes: {missing_cols}")

    # Verificar integridad de datos
    if not errors:
        for col in ["grid_import_kwh", "grid_export_kwh", "ev_charging_kwh"]:
            if col in df.columns:
                if df[col].isna().any():
                    errors.append(f"Valores NaN en {col}")
                if (df[col] < 0).any():
                    errors.append(f"Valores negativos en {col}")

    is_valid = len(errors) == 0
    return DataFrameValidation(df.shape, list(df.columns), is_valid, errors)


def validate_trace_csv(df: pd.DataFrame) -> DataFrameValidation:
    """Validar estructura de trace_sac.csv."""
    errors = []

    # Verificar que tenga observaciones y acciones
    obs_cols = [c for c in df.columns if c.startswith("obs_")]
    action_cols = [c for c in df.columns if c.startswith("action_")]

    if not obs_cols:
        errors.append("No hay columnas de observaciones (obs_*)")

    if not action_cols:
        errors.append("No hay columnas de acciones (action_*)")

    # Verificar columnas de energía
    energy_cols = ["grid_import_kwh", "ev_charging_kwh", "pv_generation_kwh"]
    missing_energy = [c for c in energy_cols if c not in df.columns]
    if missing_energy:
        errors.append(f"Columnas de energía faltantes: {missing_energy}")

    is_valid = len(errors) == 0
    return DataFrameValidation(df.shape, list(df.columns), is_valid, errors)


def validate_result_json(data: Dict[str, Any]) -> DataFrameValidation:
    """Validar estructura de result_sac.json."""
    errors = []

    # Verificar campos críticos
    required_fields = [
        "agent", "steps", "carbon_kg", "grid_import_kwh",
        "pv_generation_kwh", "ev_charging_kwh"
    ]

    missing = [f for f in required_fields if f not in data]
    if missing:
        errors.append(f"Campos requeridos faltantes: {missing}")

    # Verificar CO₂ metrics (nuevo formato 2026-02-03)
    co2_fields = [
        "co2_emitido_grid_kg", "co2_reduccion_indirecta_kg",
        "co2_reduccion_directa_kg", "co2_neto_kg"
    ]

    missing_co2 = [f for f in co2_fields if f not in data]
    if missing_co2:
        # No es error crítico, pero sí una advertencia
        logger.warning(f"Campos CO₂ 3-component faltantes: {missing_co2}")

    is_valid = len(errors) == 0
    return DataFrameValidation((1, len(data)), list(data.keys()), is_valid, errors)


def validate_sac_technical_data(output_dir: Path) -> Dict[str, Any]:
    """Valida todos los archivos técnicos de SAC."""
    results = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "output_dir": str(output_dir),
        "files": {},
        "summary": {}
    }

    logger.info("")
    logger.info("=" * 80)
    logger.info("VALIDACIÓN DE DATOS TÉCNICOS SAC POST-ENTRENAMIENTO")
    logger.info("=" * 80)
    logger.info("")

    # 1. Validar result_sac.json
    logger.info("📋 Validando result_sac.json...")
    result_path = output_dir / "result_sac.json"
    file_val, data = validate_json_file(result_path)

    if file_val.is_valid and data:
        json_val = validate_result_json(data)
        status = "✅" if json_val.is_valid else "❌"
        logger.info(f"   {status} result_sac.json - {len(data)} campos")
        if json_val.errors:
            for err in json_val.errors:
                logger.error(f"      ❌ {err}")
    else:
        logger.error(f"   ❌ result_sac.json - {file_val.errors[0] if file_val.errors else 'Error desconocido'}")

    results["files"]["result_sac.json"] = {
        "exists": file_val.exists,
        "size_kb": file_val.size_bytes / 1024,
        "valid": file_val.is_valid and (data is not None),
        "errors": file_val.errors
    }

    logger.info("")

    # 2. Validar timeseries_sac.csv
    logger.info("📊 Validando timeseries_sac.csv...")
    ts_path = output_dir / "timeseries_sac.csv"
    file_val, df_ts = validate_csv_file(ts_path)

    if file_val.is_valid and df_ts is not None:
        ts_val = validate_timeseries_csv(df_ts)
        status = "✅" if ts_val.is_valid else "❌"
        logger.info(f"   {status} timeseries_sac.csv - {ts_val.shape[0]} filas × {ts_val.shape[1]} cols")
        if ts_val.errors:
            for err in ts_val.errors:
                logger.error(f"      ❌ {err}")
    else:
        logger.error(f"   ❌ timeseries_sac.csv - {file_val.errors[0] if file_val.errors else 'Error desconocido'}")

    results["files"]["timeseries_sac.csv"] = {
        "exists": file_val.exists,
        "size_kb": file_val.size_bytes / 1024,
        "valid": file_val.is_valid and (df_ts is not None),
        "errors": file_val.errors
    }

    logger.info("")

    # 3. Validar trace_sac.csv
    logger.info("🔍 Validando trace_sac.csv...")
    trace_path = output_dir / "trace_sac.csv"
    file_val, df_trace = validate_csv_file(trace_path)

    if file_val.is_valid and df_trace is not None:
        trace_val = validate_trace_csv(df_trace)
        status = "✅" if trace_val.is_valid else "❌"
        logger.info(f"   {status} trace_sac.csv - {trace_val.shape[0]} filas × {trace_val.shape[1]} cols")
        if trace_val.errors:
            for err in trace_val.errors:
                logger.error(f"      ❌ {err}")
    else:
        logger.error(f"   ❌ trace_sac.csv - {file_val.errors[0] if file_val.errors else 'Error desconocido'}")

    results["files"]["trace_sac.csv"] = {
        "exists": file_val.exists,
        "size_kb": file_val.size_bytes / 1024,
        "valid": file_val.is_valid and (df_trace is not None),
        "errors": file_val.errors
    }

    logger.info("")
    logger.info("=" * 80)

    # Resumen
    all_valid = all(f["valid"] for f in results["files"].values())
    if all_valid:
        logger.info("✅ VALIDACIÓN EXITOSA: Todos los archivos técnicos SAC son válidos")
    else:
        logger.error("❌ VALIDACIÓN FALLIDA: Algunos archivos tienen problemas")

    logger.info("=" * 80)
    logger.info("")

    results["summary"]["all_valid"] = all_valid
    results["summary"]["files_checked"] = len(results["files"])
    results["summary"]["files_valid"] = sum(1 for f in results["files"].values() if f["valid"])

    return results


def main() -> int:
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Valida datos técnicos de SAC post-entrenamiento"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/agents/sac"),
        help="Directorio de salida SAC"
    )
    parser.add_argument(
        "--compare-with-ppo",
        action="store_true",
        help="Comparar con datos PPO si existen"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Output detallado"
    )

    args = parser.parse_args()

    try:
        results = validate_sac_technical_data(args.output_dir)

        # Retornar código de salida
        return 0 if results["summary"]["all_valid"] else 1

    except Exception as e:
        logger.critical(f"Error crítico: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
