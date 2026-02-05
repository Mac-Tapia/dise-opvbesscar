#!/usr/bin/env python3
"""
VALIDADOR DE OUTPUTS POST-ENTRENAMIENTO: SAC, PPO, A2C
======================================================

Verifica DESPUÉS de entrenar:
1. Checkpoint {agent}_final_model.zip existe y es válido
2. result_{agent}.json existe con estructura correcta
3. timeseries_{agent}.csv existe con columnas requeridas
4. trace_{agent}.csv existe con columnas requeridas
5. Métricas tienen valores esperados (no NaN, no infinitos)
6. Archivos no están vacíos o dañados
"""

from __future__ import annotations

import sys
from pathlib import Path
import json
import pandas as pd
import logging
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("VALIDADOR DE OUTPUTS POST-ENTRENAMIENTO: SAC, PPO, A2C")
print("="*80)

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

AGENTS = ['SAC', 'PPO', 'A2C']

EXPECTED_OUTPUTS = {
    'SAC': {
        'checkpoint': 'checkpoints/SAC/sac_final_model.zip',
        'result_json': 'outputs/sac_training/result_sac.json',
        'timeseries_csv': 'outputs/sac_training/timeseries_sac.csv',
        'trace_csv': 'outputs/sac_training/trace_sac.csv',
    },
    'PPO': {
        'checkpoint': 'checkpoints/PPO/ppo_final_model.zip',
        'result_json': 'outputs/ppo_training/result_ppo.json',
        'timeseries_csv': 'outputs/ppo_training/timeseries_ppo.csv',
        'trace_csv': 'outputs/ppo_training/trace_ppo.csv',
    },
    'A2C': {
        'checkpoint': 'checkpoints/A2C/a2c_final_model.zip',
        'result_json': 'outputs/a2c_training/result_a2c.json',
        'timeseries_csv': 'outputs/a2c_training/timeseries_a2c.csv',
        'trace_csv': 'outputs/a2c_training/trace_a2c.csv',
    },
}

REQUIRED_RESULT_JSON_KEYS = [
    'agent', 'total_timesteps', 'total_episodes', 'mean_reward',
    'co2_avoided_kg', 'solar_utilization_pct', 'ev_soc_avg',
    'datetime', 'device'
]

REQUIRED_TIMESERIES_COLUMNS = [
    'episode', 'timestep', 'total_reward', 'co2_grid_kg',
    'solar_utilized_kwh', 'ev_satisfaction', 'grid_import_kwh'
]

REQUIRED_TRACE_COLUMNS = [
    'step', 'episode', 'reward', 'done'
]

# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

def validate_checkpoint(agent: str, checkpoint_path: Path) -> Tuple[bool, str]:
    """Validar que checkpoint existe y es válido."""
    if not checkpoint_path.exists():
        return False, f"❌ Checkpoint NO existe: {checkpoint_path}"

    size_mb = checkpoint_path.stat().st_size / 1e6
    if size_mb < 0.1:
        return False, f"❌ Checkpoint demasiado pequeño ({size_mb:.2f} MB)"

    return True, f"✓ Checkpoint válido ({size_mb:.2f} MB)"


def validate_result_json(agent: str, json_path: Path) -> Tuple[bool, str]:
    """Validar que result JSON existe y tiene estructura correcta."""
    if not json_path.exists():
        return False, f"❌ {json_path.name} NO existe"

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"❌ {json_path.name} JSON inválido: {e}"

    # Verificar keys requeridas
    missing_keys = set(REQUIRED_RESULT_JSON_KEYS) - set(data.keys())
    if missing_keys:
        return False, f"❌ Faltan keys en {json_path.name}: {missing_keys}"

    # Verificar que valores no sean NaN o infinito
    for key in ['mean_reward', 'co2_avoided_kg', 'solar_utilization_pct', 'ev_soc_avg']:
        val = data.get(key)
        if val is None:
            return False, f"❌ {key} es None"
        if isinstance(val, float) and (val != val or val == float('inf')):  # NaN o inf
            return False, f"❌ {key} es NaN o infinito"

    return True, f"✓ {json_path.name} válido ({len(data)} keys)"


def validate_timeseries_csv(agent: str, csv_path: Path) -> Tuple[bool, str]:
    """Validar que timeseries CSV existe y tiene estructura correcta."""
    if not csv_path.exists():
        return False, f"❌ {csv_path.name} NO existe"

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return False, f"❌ {csv_path.name} no se puede leer: {e}"

    if df.empty:
        return False, f"❌ {csv_path.name} está vacío"

    # Verificar columnas
    missing_cols = set(REQUIRED_TIMESERIES_COLUMNS) - set(df.columns)
    if missing_cols:
        return False, f"❌ Faltan columnas en {csv_path.name}: {missing_cols}"

    # Verificar que no haya NaN en columnas críticas
    for col in ['episode', 'timestep', 'total_reward']:
        if df[col].isna().any():
            return False, f"❌ Columna {col} tiene NaN"

    return True, f"✓ {csv_path.name} válido ({len(df)} filas)"


def validate_trace_csv(agent: str, csv_path: Path) -> Tuple[bool, str]:
    """Validar que trace CSV existe y tiene estructura correcta."""
    if not csv_path.exists():
        return False, f"❌ {csv_path.name} NO existe"

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return False, f"❌ {csv_path.name} no se puede leer: {e}"

    if df.empty:
        return False, f"❌ {csv_path.name} está vacío"

    # Verificar columnas básicas
    required_basic = ['step', 'episode', 'reward']  # Mínimo requerido
    missing_cols = set(required_basic) - set(df.columns)
    if missing_cols:
        return False, f"❌ Faltan columnas en {csv_path.name}: {missing_cols}"

    return True, f"✓ {csv_path.name} válido ({len(df)} filas)"


# ============================================================================
# MAIN VALIDATION
# ============================================================================

print("\nValidando outputs post-entrenamiento...\n")

results = {}

for agent in AGENTS:
    print(f"\n[{agent}]")
    print("-" * 40)

    outputs = EXPECTED_OUTPUTS[agent]
    agent_results = {}

    # Validar checkpoint
    checkpoint_path = Path(outputs['checkpoint'])
    is_valid, msg = validate_checkpoint(agent, checkpoint_path)
    print(f"  Checkpoint: {msg}")
    agent_results['checkpoint'] = is_valid

    # Validar result JSON
    json_path = Path(outputs['result_json'])
    is_valid, msg = validate_result_json(agent, json_path)
    print(f"  Result JSON: {msg}")
    agent_results['result_json'] = is_valid

    # Validar timeseries CSV
    csv_path = Path(outputs['timeseries_csv'])
    is_valid, msg = validate_timeseries_csv(agent, csv_path)
    print(f"  Timeseries: {msg}")
    agent_results['timeseries_csv'] = is_valid

    # Validar trace CSV
    trace_path = Path(outputs['trace_csv'])
    is_valid, msg = validate_trace_csv(agent, trace_path)
    print(f"  Trace: {msg}")
    agent_results['trace_csv'] = is_valid

    results[agent] = agent_results

# ============================================================================
# RESUMEN
# ============================================================================

print("\n" + "="*80)
print("RESUMEN VALIDACIÓN")
print("="*80)

all_valid = True
for agent in AGENTS:
    agent_valid = all(results[agent].values())
    status = "✅ PASS" if agent_valid else "❌ FAIL"
    print(f"{agent:6} {status}")
    all_valid = all_valid and agent_valid

print("\n" + "="*80)
if all_valid:
    print("✅ TODOS LOS OUTPUTS VÁLIDOS - ENTRENAMIENTO COMPLETADO")
else:
    print("❌ ALGUNOS OUTPUTS INVÁLIDOS - REVISAR ARRIBA")
print("="*80)

# ============================================================================
# EXPORTAR REPORTE
# ============================================================================

report = {
    'timestamp': pd.Timestamp.now().isoformat(),
    'all_agents_valid': all_valid,
    'validation_results': results,
}

report_path = Path('outputs/validation_posttraining.json')
report_path.parent.mkdir(parents=True, exist_ok=True)

with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"\nReporte guardado: {report_path}")

sys.exit(0 if all_valid else 1)
