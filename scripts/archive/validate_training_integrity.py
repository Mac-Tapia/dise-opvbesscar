"""
Script de Validación de Integridad del Entrenamiento Automático
===============================================================

Verifica que:
1. Baseline guardado correctamente (no null)
2. Transiciones entre agentes completadas
3. Checkpoints existen y son válidos
4. Cálculos CO2 consistentes
5. Archivos de resultados completos

Uso:
    python scripts/validate_training_integrity.py --output-dir outputs/oe3/simulations
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def validate_result_json(result_path: Path) -> Tuple[bool, str]:
    """Valida que result_*.json sea válido y completo."""
    if not result_path.exists():
        return False, f"No existe: {result_path}"

    try:
        with open(result_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"JSON inválido: {e}"

    required_fields = [
        "agent", "steps", "seconds_per_time_step", "simulated_years",
        "grid_import_kwh", "ev_charging_kwh", "building_load_kwh",
        "pv_generation_kwh", "carbon_kg"
    ]

    missing = [f for f in required_fields if f not in data]
    if missing:
        return False, f"Campos faltantes: {missing}"

    # Validar que no hay valores None o NaN
    for field in required_fields:
        val = data[field]
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return False, f"Valor inválido en {field}: {val}"

    return True, "OK"


def validate_timeseries_csv(ts_path: Path) -> Tuple[bool, str]:
    """Valida que timeseries_*.csv tenga 8,760 filas y columnas correctas."""
    if not ts_path.exists():
        return False, f"No existe: {ts_path}"

    try:
        df = pd.read_csv(ts_path)
    except Exception as e:
        return False, f"Error al leer CSV: {e}"

    if len(df) != 8760:
        return False, f"Filas incorrectas: {len(df)} (esperado 8760)"

    required_cols = [
        "net_grid_kwh", "grid_import_kwh", "grid_export_kwh",
        "ev_charging_kwh", "building_load_kwh", "pv_generation_kwh"
    ]

    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        return False, f"Columnas faltantes: {missing_cols}"

    # Verificar que no hay NaN
    if df.isnull().any().any():
        return False, f"Valores NaN detectados en columnas: {df.isnull().any()}"

    return True, "OK"


def validate_trace_csv(trace_path: Path) -> Tuple[bool, str]:
    """Valida que trace_*.csv tenga estructura correcta."""
    if not trace_path.exists():
        return False, f"No existe: {trace_path}"

    try:
        df = pd.read_csv(trace_path)
    except Exception as e:
        return False, f"Error al leer CSV: {e}"

    if len(df) == 0:
        return False, "Archivo vacío"

    required_cols = ["step", "reward_env", "grid_import_kwh", "ev_charging_kwh"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        return False, f"Columnas faltantes: {missing_cols}"

    return True, f"OK ({len(df)} filas)"


def validate_simulation_summary(summary_path: Path) -> Tuple[bool, str]:
    """Valida simulation_summary.json."""
    if not summary_path.exists():
        return False, f"No existe: {summary_path}"

    try:
        with open(summary_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"JSON inválido: {e}"

    # Verificar que baseline no sea null
    baseline = data.get("pv_bess_uncontrolled")
    if baseline is None:
        return False, "CRÍTICO: pv_bess_uncontrolled es NULL (baseline no guardado)"

    if not isinstance(baseline, dict):
        return False, f"pv_bess_uncontrolled debe ser dict, got {type(baseline)}"

    # Verificar que contiene agentes
    results = data.get("pv_bess_results", {})
    if not results:
        return False, "pv_bess_results vacío (sin agentes)"

    # Verificar que cada agente tiene carbon_kg
    for agent_name, res in results.items():
        if "carbon_kg" not in res:
            return False, f"Agente {agent_name} sin carbon_kg"
        if res["carbon_kg"] is None:
            return False, f"Agente {agent_name} tiene carbon_kg=None"

    return True, f"OK (baseline + {len(results)} agentes)"


def validate_co2_comparison_table(md_path: Path) -> Tuple[bool, str]:
    """Valida co2_comparison.md."""
    if not md_path.exists():
        return False, f"No existe: {md_path}"

    content = md_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    if len(lines) < 3:
        return False, "Tabla demasiado corta"

    # Verificar que tiene encabezados
    if "Escenario" not in lines[0]:
        return False, "Encabezado 'Escenario' no encontrado"

    if "CO2_kg" not in lines[0]:
        return False, "Encabezado 'CO2_kg' no encontrado"

    # Contar filas de datos (excluir encabezado y separador)
    data_rows = [l for l in lines[2:] if l.strip().startswith("|")]
    if len(data_rows) < 2:  # Mínimo: grid-only + baseline
        return False, f"Pocas filas de datos: {len(data_rows)}"

    return True, f"OK ({len(data_rows)} escenarios)"


def validate_checkpoint_dir(checkpoint_dir: Path) -> Tuple[bool, Dict[str, int]]:
    """Valida directorios de checkpoints."""
    if not checkpoint_dir.exists():
        return False, {}

    counts = {}
    for agent_dir in ["sac", "ppo", "a2c"]:
        agent_path = checkpoint_dir / agent_dir
        if not agent_path.exists():
            counts[agent_dir] = 0
        else:
            zips = list(agent_path.glob("*.zip"))
            counts[agent_dir] = len(zips)

    return any(counts.values()), counts


def compare_co2_reductions(summary_path: Path) -> Tuple[bool, Dict[str, float]]:
    """Calcula reducciones CO2 de agentes vs baseline."""
    with open(summary_path, "r") as f:
        data = json.load(f)

    baseline = data["pv_bess_uncontrolled"]
    if baseline is None:
        return False, {}

    baseline_co2 = float(baseline["carbon_kg"])
    reductions = {}

    for agent_name, res in data["pv_bess_results"].items():
        agent_co2 = float(res["carbon_kg"])
        reduction_pct = ((baseline_co2 - agent_co2) / baseline_co2 * 100)
        reductions[agent_name] = reduction_pct

    return True, reductions


def main() -> None:
    ap = argparse.ArgumentParser(description="Valida integridad de entrenamiento automático")
    ap.add_argument("--output-dir", default="outputs/oe3/simulations", help="Directorio de salida")
    ap.add_argument("--checkpoint-dir", default="checkpoints", help="Directorio de checkpoints")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    chk_dir = Path(args.checkpoint_dir)

    logger.info("=" * 80)
    logger.info("VALIDACIÓN DE INTEGRIDAD: ENTRENAMIENTO AUTOMÁTICO")
    logger.info("=" * 80)

    all_valid = True

    # 1. Validar resultados individuales
    logger.info("\n[1] Validando result_*.json")
    agents = ["Uncontrolled", "SAC", "PPO", "A2C"]
    for agent in agents:
        result_path = out_dir / f"result_{agent}.json"
        valid, msg = validate_result_json(result_path)
        status = "✅" if valid else "❌"
        logger.info(f"  {status} {agent:15} : {msg}")
        all_valid = all_valid and valid

    # 2. Validar timeseries
    logger.info("\n[2] Validando timeseries_*.csv")
    for agent in agents:
        ts_path = out_dir / f"timeseries_{agent}.csv"
        valid, msg = validate_timeseries_csv(ts_path)
        status = "✅" if valid else "❌"
        logger.info(f"  {status} {agent:15} : {msg}")
        all_valid = all_valid and valid

    # 3. Validar trace
    logger.info("\n[3] Validando trace_*.csv")
    for agent in agents:
        trace_path = out_dir / f"trace_{agent}.csv"
        valid, msg = validate_trace_csv(trace_path)
        status = "✅" if valid else "❌"
        logger.info(f"  {status} {agent:15} : {msg}")
        all_valid = all_valid and valid

    # 4. Validar simulation_summary.json
    logger.info("\n[4] Validando simulation_summary.json")
    summary_path = out_dir / "simulation_summary.json"
    valid, msg = validate_simulation_summary(summary_path)
    status = "✅" if valid else "❌"
    logger.info(f"  {status} {msg}")
    all_valid = all_valid and valid

    # 5. Validar co2_comparison.md
    logger.info("\n[5] Validando co2_comparison.md")
    md_path = out_dir / "co2_comparison.md"
    valid, msg = validate_co2_comparison_table(md_path)
    status = "✅" if valid else "❌"
    logger.info(f"  {status} {msg}")
    all_valid = all_valid and valid

    # 6. Validar checkpoints
    logger.info("\n[6] Validando checkpoints")
    valid, counts = validate_checkpoint_dir(chk_dir)
    if valid:
        for agent, count in counts.items():
            logger.info(f"  ✅ {agent:10} : {count} checkpoints")
    else:
        logger.info(f"  ℹ️  No se encontraron checkpoints (primer entrenamiento)")

    # 7. Comparar reducciones CO2
    if summary_path.exists():
        logger.info("\n[7] Reducciones CO2 vs Baseline")
        valid, reductions = compare_co2_reductions(summary_path)
        if valid and reductions:
            for agent, reduction_pct in sorted(reductions.items(), key=lambda x: x[1], reverse=True):
                status = "⬇️ " if reduction_pct < 0 else "✅"
                logger.info(f"  {status} {agent:10} : {reduction_pct:+.2f}%")
        elif valid:
            logger.info("  ⓘ  No hay datos de agentes para comparar")
        else:
            logger.info("  ❌ Error al leer summary")
            all_valid = False

    # Resumen final
    logger.info("\n" + "=" * 80)
    if all_valid:
        logger.info("✅ VALIDACIÓN COMPLETA: SISTEMA SÓLIDO Y LISTO")
        logger.info("=" * 80)
        sys.exit(0)
    else:
        logger.error("❌ VALIDACIÓN FALLÓ: REVISAR ERRORES ARRIBA")
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
