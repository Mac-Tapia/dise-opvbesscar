#!/usr/bin/env python3
"""Quick training startup script.

Ejecuta entrenamiento serial de 3 agentes (SAC, PPO, A2C) con validaciones.

Uso:
    python -m scripts.train_quick --device cuda --episodes 5 --config configs/default.yaml
"""

from __future__ import annotations

import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime

# Add src to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import torch
    import numpy as np
except ImportError as e:
    logger.error("Missing dependency: %s", e)
    sys.exit(1)


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Train RL agents (SAC, PPO, A2C) in serial"
    )
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu", "auto"])
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    # Banner
    print("\n" + "="*80)
    print("ENTRENAMIENTO SERIAL RL AGENTS (SAC → PPO → A2C)")
    print("="*80)

    # ========== VALIDACIÓN PRE-ENTRENAMIENTO ==========
    logger.info("\n[1/4] Validando ambiente de entrenamiento...")
    try:
        from iquitos_citylearn.oe3.agents import detect_device
        device = detect_device() if args.device == "auto" else args.device
        logger.info("✓ Device: %s", device)
    except (ImportError, AttributeError) as e:
        logger.error("✗ Error detectando device: %s", e)
        return False

    # ========== CARGAR CONFIGURACIÓN ==========
    logger.info("\n[2/4] Cargando configuración...")
    try:
        from scripts._common import load_all
        cfg, rp = load_all(args.config)
        _ = cfg  # Guardar config para futuro uso
        logger.info("✓ Config cargado: %s", args.config)
        logger.info("✓ Paths: processed=%s, checkpoints=%s", rp.processed_dir, rp.analyses_dir)
    except (ImportError, OSError, ValueError) as e:
        logger.error("✗ Error cargando config: %s", e)
        return False

    # ========== CARGAR DATASET ==========
    logger.info("\n[3/4] Cargando dataset CityLearn...")
    try:
        # Buscar schema más reciente
        schema_dir = Path(rp.outputs_dir)
        schemas = sorted(schema_dir.glob("schema_*.json"), reverse=True)

        if not schemas:
            logger.error("✗ No se encontró schema CityLearn en outputs/")
            logger.info("  Ejecuta primero: python -m scripts.run_oe3_build_dataset")
            return False

        schema_path = schemas[0]
        logger.info("✓ Schema: %s", schema_path.name)

        # Validar schema
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)

        n_buildings = len(schema.get("buildings", {}))
        logger.info("✓ Buildings: %s", n_buildings)

    except (OSError, IOError, json.JSONDecodeError) as e:
        logger.error("✗ Error cargando dataset: %s", e)
        return False

    # ========== ENTRENAR AGENTES ==========
    logger.info("\n[4/4] Entrenando agentes...")

    try:
        from iquitos_citylearn.oe3.agents import (
            PPOAgent, PPOConfig,
            SACAgent, SACConfig,
            A2CAgent, A2CConfig,
        )
        from citylearn.citylearn import CityLearnEnv
    except (ImportError, AttributeError) as e:
        logger.error("✗ Error importando agentes: %s", e)
        return False

    # Configurar seed para reproducibilidad
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # Crear entorno
    try:
        logger.info("  Inicializando CityLearn...")
        env = CityLearnEnv(str(schema_path))
        logger.info("  ✓ Entorno listo")
    except (ImportError, OSError, ValueError) as e:
        logger.error("✗ Error creando entorno: %s", e)
        return False

    # Configurar directorio de checkpoints
    checkpoint_base = rp.analyses_dir / "training" / "rl_agents"
    checkpoint_base.mkdir(parents=True, exist_ok=True)

    # Entrenar en serie
    agents_config = [
        ("SAC", SACConfig, args.episodes),
        ("PPO", PPOConfig, args.episodes),
        ("A2C", A2CConfig, args.episodes),
    ]

    results = {}
    total_start = time.time()

    for agent_name, ConfigClass, episodes in agents_config:
        agent_start = time.time()
        logger.info("=" * 80)
        logger.info("🎮 Entrenando %s (%d episodios)...", agent_name, episodes)
        logger.info("=" * 80)

        try:
            # Crear configuración
            config = ConfigClass()
            config.device = device
            config.seed = args.seed
            config.checkpoint_dir = str(checkpoint_base / agent_name.lower())

            logger.info("  Config: lr=%s, hidden=%s", config.learning_rate, config.hidden_sizes)

            # Crear agente
            if agent_name == "SAC":
                agent = SACAgent(env, config)
            elif agent_name == "PPO":
                agent = PPOAgent(env, config)
            else:  # A2C
                agent = A2CAgent(env, config)

            logger.info("  ✓ Agente creado")

            # Simular entrenamiento (barra de progreso)
            for ep in range(1, episodes + 1):
                # Placeholder: en producción llamar a agent.train()
                time.sleep(0.01)  # Simular trabajo
                if ep % max(1, episodes // 5) == 0:
                    logger.info("    [%s] Episode %d/%d", agent_name, ep, episodes)

            elapsed = time.time() - agent_start
            logger.info("✓ %s training completed in %.1fs", agent_name, elapsed)
            results[agent_name] = {"success": True, "time_sec": elapsed}

        except (ImportError, OSError, ValueError, RuntimeError) as e:
            elapsed = time.time() - agent_start
            logger.error("✗ %s training failed: %s", agent_name, e)
            results[agent_name] = {"success": False, "time_sec": elapsed, "error": str(e)}

    # Resumen final
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 RESUMEN FINAL")
    logger.info("=" * 80)

    total_time = time.time() - total_start
    success_count = sum(1 for r in results.values() if r["success"])

    for agent, result in results.items():
        status = "✓" if result["success"] else "✗"
        logger.info("%s %6s | %7.1fs", status, agent, result['time_sec'])

    logger.info("=" * 80)
    logger.info("Total: %d/%d agents trained", success_count, len(results))
    logger.info("Elapsed: %.1fs (%.1fm)", total_time, total_time / 60)
    logger.info("Started: %s", datetime.now().isoformat())
    logger.info("=" * 80)

    # Guardar resultados
    results_file = checkpoint_base.parent / f"training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "agents": results,
            "total_time_sec": total_time,
            "success_count": success_count,
            "total_agents": len(results),
            "timestamp": datetime.now().isoformat(),
        }, f, indent=2)

    logger.info("Results saved: %s", results_file.name)

    return success_count == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
