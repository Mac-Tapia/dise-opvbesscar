#!/usr/bin/env python3
"""
VERIFICACIÓN COMPLETA DE REGLAS DE AGENTES
============================================

Verifica:
1. Reglas de despacho (Solar→EV→BESS→Grid)
2. Control de BESS por agentes
3. Asignación correcta de chargers (motos vs mototaxis)
4. Transición correcta entre agentes (SAC→PPO→A2C)
5. Que no se estanca el entrenamiento en cambio de agente
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd  # type: ignore
import yaml  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# VERIFICACIÓN 1: REGLAS DE DESPACHO
# ============================================================================

def verify_dispatch_rules() -> Dict[str, Any]:
    """Verifica que las reglas de despacho están configuradas correctamente."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("[1/5] VERIFICACIÓN DE REGLAS DE DESPACHO (Solar→EV→BESS→Grid)")
    logger.info("=" * 80)

    config_path = Path("configs/default.yaml")
    if not config_path.exists():
        logger.error(f"❌ No encontrado: {config_path}")
        return {"status": "ERROR", "message": "Config no existe"}

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    dispatch = config.get("oe2", {}).get("dispatch_rules", {})
    enabled = dispatch.get("enabled", False)

    logger.info(f"✓ Dispatch rules enabled: {enabled}")

    # Verificar prioridades
    priorities = {
        "priority_1_pv_to_ev": "☀️ Solar→EV (MÁXIMA PRIORIDAD)",
        "priority_2_pv_to_bess": "☀️ Solar→BESS (almacenar)",
        "priority_3_bess_to_ev": "🔋 BESS→EV (noche)",
        "priority_4_bess_to_grid": "🔋 BESS→MALL (desaturar)",
        "priority_5_grid_import": "⚡ Grid import (último recurso)",
    }

    dispatch_ok = True
    for key, desc in priorities.items():
        if key in dispatch:
            p = dispatch[key]
            if isinstance(p, dict) and p.get("enabled", False):
                logger.info(f"  ✓ {desc}: ENABLED")
            else:
                logger.warning(f"  ⚠ {desc}: DISABLED")
                dispatch_ok = False
        else:
            logger.warning(f"  ⚠ {desc}: NOT FOUND")

    # Verificar BESS config
    bess = config.get("oe2", {}).get("bess", {})
    logger.info(f"\n✓ BESS Configuration:")
    logger.info(f"  - Capacity: {bess.get('fixed_capacity_kwh', 'N/A')} kWh")
    logger.info(f"  - Power: {bess.get('fixed_power_kw', 'N/A')} kW")
    logger.info(f"  - Min SOC: {bess.get('min_soc_percent', 'N/A')}%")
    logger.info(f"  - Max SOC: {bess.get('dod', 'N/A')} (DoD)")
    logger.info(f"  - Efficiency: {bess.get('efficiency_roundtrip', 'N/A')}")
    logger.info(f"  - Load scope: {bess.get('load_scope', 'N/A')} (only EV allowed)")

    return {
        "status": "OK" if dispatch_ok else "WARNING",
        "dispatch_enabled": enabled,
        "all_priorities_enabled": dispatch_ok,
        "bess_config": bess,
    }

# ============================================================================
# VERIFICACIÓN 2: CONTROL DE BESS EN AGENTES
# ============================================================================

def verify_bess_control_in_agents() -> Dict[str, Any]:
    """Verifica que los agentes pueden controlar BESS."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("[2/5] VERIFICACIÓN: CONTROL DE BESS EN AGENTES")
    logger.info("=" * 80)

    # Revisar schema para verificar que BESS está incluido
    schema_path = Path("outputs/schema_building.json")
    if not schema_path.exists():
        logger.error(f"❌ No encontrado: {schema_path}")
        return {"status": "ERROR", "message": "Schema no existe"}

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    building = schema.get("buildings", {})
    if not building:
        logger.error("❌ No buildings found in schema")
        return {"status": "ERROR", "message": "No buildings"}

    building_name = list(building.keys())[0]
    bldg = building[building_name]

    # Buscar BESS en el schema
    has_bess = False
    bess_type = None
    for key in bldg.keys():
        if "batt" in key.lower() or "bess" in key.lower() or "storage" in key.lower():
            has_bess = True
            bess_type = key
            logger.info(f"✓ BESS found in schema: {key}")
            logger.info(f"  Value: {bldg.get(key, 'N/A')}")
            break

    if not has_bess:
        logger.warning("⚠ BESS not found in schema keys")
        logger.info(f"  Available keys: {list(bldg.keys())}")

    # Revisar observation space
    obs_space = schema.get("observation_space", [])
    n_obs = len(obs_space)
    logger.info(f"\n✓ Observation space size: {n_obs} dimensions")

    # Revisar action space (debe incluir 126 dims para 128 chargers - 2 reserved)
    action_space = schema.get("action_space", [])
    n_actions = len(action_space)
    logger.info(f"✓ Action space size: {n_actions} dimensions")
    logger.info(f"  Expected: 126 (128 chargers - 2 reserved)")
    if n_actions != 126:
        logger.warning(f"⚠ Action space mismatch: expected 126, got {n_actions}")

    # Revisar que la observación incluye BESS state
    bess_obs_count = sum(1 for obs in obs_space if "batt" in obs.lower() or "bess" in obs.lower() or "soc" in obs.lower())
    logger.info(f"✓ BESS-related observations: {bess_obs_count} dimensions")

    return {
        "status": "OK" if has_bess and n_obs > 0 and n_actions == 126 else "WARNING",
        "has_bess": has_bess,
        "bess_key": bess_type,
        "observation_dims": n_obs,
        "action_dims": n_actions,
        "bess_obs_count": bess_obs_count,
    }

# ============================================================================
# VERIFICACIÓN 3: ASIGNACIÓN DE CHARGERS (MOTOS vs MOTOTAXIS)
# ============================================================================

def verify_charger_assignment() -> Dict[str, Any]:
    """Verifica que los chargers están asignados correctamente a motos/mototaxis."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("[3/5] VERIFICACIÓN: ASIGNACIÓN DE CHARGERS (MOTOS vs MOTOTAXIS)")
    logger.info("=" * 80)

    charger_path = Path("data/interim/oe2/chargers/individual_chargers.json")
    if not charger_path.exists():
        logger.error(f"❌ No encontrado: {charger_path}")
        return {"status": "ERROR", "message": "Chargers file not found"}

    with open(charger_path, "r", encoding="utf-8") as f:
        chargers = json.load(f)

    # Agrupar por tipo
    motos = [c for c in chargers if c.get("charger_type", "").lower() == "moto"]
    mototaxis = [c for c in chargers if c.get("charger_type", "").lower() == "mototaxi"]
    unknown = [c for c in chargers if c.get("charger_type", "").lower() not in ["moto", "mototaxi"]]

    logger.info(f"✓ Total chargers: {len(chargers)}")
    logger.info(f"  - Motos: {len(motos)} chargers")
    logger.info(f"  - Mototaxis: {len(mototaxis)} chargers")
    logger.info(f"  - Unknown type: {len(unknown)} chargers")

    # Verificar distribución de poder
    motos_power = sum(c.get("power_kw", 0) for c in motos)
    mototaxis_power = sum(c.get("power_kw", 0) for c in mototaxis)
    total_power = sum(c.get("power_kw", 0) for c in chargers)

    logger.info(f"\n✓ Power distribution:")
    logger.info(f"  - Motos power: {motos_power:.1f} kW ({motos_power/total_power*100:.1f}%)")
    logger.info(f"  - Mototaxis power: {mototaxis_power:.1f} kW ({mototaxis_power/total_power*100:.1f}%)")
    logger.info(f"  - Total power: {total_power:.1f} kW")

    # Verificar sockets
    motos_sockets = sum(c.get("sockets", 0) for c in motos)
    mototaxis_sockets = sum(c.get("sockets", 0) for c in mototaxis)
    total_sockets = sum(c.get("sockets", 0) for c in chargers)

    logger.info(f"\n✓ Socket distribution:")
    logger.info(f"  - Motos sockets: {motos_sockets} (expected: 112)")
    logger.info(f"  - Mototaxis sockets: {mototaxis_sockets} (expected: 16)")
    logger.info(f"  - Total sockets: {total_sockets} (expected: 128)")

    # Validación
    ok = (
        len(chargers) == 32 and
        len(motos) > 0 and
        len(mototaxis) > 0 and
        total_sockets == 128 and
        abs(motos_sockets - 112) <= 1  # Allow 1 socket margin
    )

    status = "OK" if ok else "WARNING"
    if len(unknown) > 0:
        logger.warning(f"⚠ Found {len(unknown)} chargers with unknown type")
        status = "WARNING"

    return {
        "status": status,
        "total_chargers": len(chargers),
        "motos": len(motos),
        "mototaxis": len(mototaxis),
        "motos_sockets": motos_sockets,
        "mototaxis_sockets": mototaxis_sockets,
        "total_sockets": total_sockets,
        "motos_power_kw": motos_power,
        "mototaxis_power_kw": mototaxis_power,
        "total_power_kw": total_power,
    }

# ============================================================================
# VERIFICACIÓN 4: TRANSICIÓN ENTRE AGENTES
# ============================================================================

def verify_agent_transition() -> Dict[str, Any]:
    """Verifica que la transición SAC→PPO→A2C no causa problemas."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("[4/5] VERIFICACIÓN: TRANSICIÓN ENTRE AGENTES (SAC→PPO→A2C)")
    logger.info("=" * 80)

    # Revisar código de simulate.py para ver cómo se manejan las transiciones
    simulate_path = Path("src/iquitos_citylearn/oe3/simulate.py")
    if not simulate_path.exists():
        logger.error(f"❌ No encontrado: {simulate_path}")
        return {"status": "ERROR", "message": "simulate.py not found"}

    with open(simulate_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Verificar que hay manejo de reset_num_timesteps
    has_reset_check = "reset_num_timesteps" in code
    logger.info(f"✓ reset_num_timesteps handling: {has_reset_check}")

    # Verificar que hay checkpoint management
    has_checkpoint = "_latest_checkpoint" in code
    logger.info(f"✓ Checkpoint management: {has_checkpoint}")

    # Verificar que hay resume logic para cada agente
    agents = ["sac", "ppo", "a2c"]
    for agent in agents:
        has_resume = f"{agent}_resume" in code.lower()
        logger.info(f"  - {agent.upper()} resume logic: {has_resume}")

    # Verificar que los agentes se crean independientemente
    has_env_reset = "raw_env =" in code and "env =" in code
    logger.info(f"✓ Environment reset between agents: {has_env_reset}")

    # Verificar que los checkpoints se guardan separadamente
    checkpoint_dirs = ["sac_checkpoint_dir", "ppo_checkpoint_dir", "a2c_checkpoint_dir"]
    all_separate = all(ckpt in code for ckpt in checkpoint_dirs)
    logger.info(f"✓ Separate checkpoint directories: {all_separate}")

    status = "OK" if (has_reset_check and has_checkpoint and all_separate) else "WARNING"

    return {
        "status": status,
        "has_reset_num_timesteps": has_reset_check,
        "has_checkpoint_management": has_checkpoint,
        "has_resume_logic": all(f"{agent}_resume" in code.lower() for agent in agents),
        "has_separate_checkpoints": all_separate,
    }

# ============================================================================
# VERIFICACIÓN 5: NO SE ESTANCA EN CAMBIO DE AGENTE
# ============================================================================

def verify_no_stalls() -> Dict[str, Any]:
    """Verifica que el cambio de agente no causa bloqueos."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("[5/5] VERIFICACIÓN: NO SE ESTANCA EN CAMBIO DE AGENTE")
    logger.info("=" * 80)

    simulate_path = Path("src/iquitos_citylearn/oe3/simulate.py")
    if not simulate_path.exists():
        logger.error(f"❌ No encontrado: {simulate_path}")
        return {"status": "ERROR", "message": "simulate.py not found"}

    with open(simulate_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Verificar timeout handling
    has_timeout = "timeout" in code.lower() or "TIMEOUT" in code
    logger.info(f"✓ Timeout handling: {has_timeout}")

    # Verificar try-except para agent creation
    has_exception_handling = "except Exception as e" in code
    logger.info(f"✓ Exception handling for agent creation: {has_exception_handling}")

    # Verificar fallback to Uncontrolled
    has_fallback = "UncontrolledChargingAgent" in code and "Falling back" in code
    logger.info(f"✓ Fallback to Uncontrolled agent: {has_fallback}")

    # Verificar que episode completes
    has_episode_complete = "_run_episode_safe" in code
    logger.info(f"✓ Safe episode runner: {has_episode_complete}")

    # Verificar que rewards are tracked
    has_reward_tracking = "trace_rewards" in code
    logger.info(f"✓ Reward tracking for stall detection: {has_reward_tracking}")

    # Verificar logging of progress
    has_progress_logging = "paso" in code.lower() and "logging" in code.lower()
    logger.info(f"✓ Progress logging: {has_progress_logging}")

    status = "OK" if all([
        has_exception_handling,
        has_fallback,
        has_episode_complete,
        has_reward_tracking,
        has_progress_logging,
    ]) else "WARNING"

    return {
        "status": status,
        "has_timeout_handling": has_timeout,
        "has_exception_handling": has_exception_handling,
        "has_fallback_agent": has_fallback,
        "has_safe_episode_runner": has_episode_complete,
        "has_reward_tracking": has_reward_tracking,
        "has_progress_logging": has_progress_logging,
    }

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ejecutar todas las verificaciones."""
    logger.info("")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 15 + "VERIFICACIÓN COMPLETA DE REGLAS DE AGENTES" + " " * 21 + "║")
    logger.info("╚" + "=" * 78 + "╝")

    results = {
        "dispatch_rules": verify_dispatch_rules(),
        "bess_control": verify_bess_control_in_agents(),
        "charger_assignment": verify_charger_assignment(),
        "agent_transition": verify_agent_transition(),
        "no_stalls": verify_no_stalls(),
    }

    # Resumen final
    logger.info("")
    logger.info("=" * 80)
    logger.info("RESUMEN FINAL")
    logger.info("=" * 80)

    for check_name, result in results.items():
        status = result.get("status", "UNKNOWN")
        emoji = "✅" if status == "OK" else "⚠️" if status == "WARNING" else "❌"
        logger.info(f"{emoji} {check_name}: {status}")

    # Determinar estado general
    all_ok = all(r.get("status") == "OK" for r in results.values())
    any_error = any(r.get("status") == "ERROR" for r in results.values())

    logger.info("")
    if all_ok:
        logger.info("✅ TODAS LAS VERIFICACIONES PASARON - Sistema listo para entrenar")
    elif any_error:
        logger.error("❌ ERRORES ENCONTRADOS - Revisar los errores anteriores")
    else:
        logger.warning("⚠️ ADVERTENCIAS ENCONTRADAS - Sistema funcional pero revisar notas")

    logger.info("")

    # Guardar resultados en JSON
    results_file = Path("outputs/agent_verification_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Resultados guardados en: {results_file}")

if __name__ == "__main__":
    main()
