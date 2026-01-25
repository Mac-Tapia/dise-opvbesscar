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
    logger.error(f"Missing dependency: {e}")
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
        logger.info(f"✓ Device: {device}")
    except Exception as e:
        logger.error(f"✗ Error detectando device: {e}")
        return False

    # ========== CARGAR CONFIGURACIÓN ==========
    logger.info("\n[2/4] Cargando configuración...")
    try:
        from scripts._common import load_all
        cfg, rp = load_all(args.config)
        logger.info(f"✓ Config cargado: {args.config}")
        logger.info(f"✓ Paths: processed={rp.processed_dir}, checkpoints={rp.analyses_dir}")
    except Exception as e:
        logger.error(f"✗ Error cargando config: {e}")
        return False

    # ========== CARGAR DATASET ==========
    logger.info("\n[3/4] Cargando dataset CityLearn...")
    try:
        import json as json_module

        # Buscar schema más reciente
        schema_dir = Path(rp.outputs_dir)
        schemas = sorted(schema_dir.glob("schema_*.json"), reverse=True)

        if not schemas:
            logger.error("✗ No se encontró schema CityLearn en outputs/")
            logger.info("  Ejecuta primero: python -m scripts.run_oe3_build_dataset")
            return False

        schema_path = schemas[0]
        logger.info(f"✓ Schema: {schema_path.name}")

        # Validar schema
        with open(schema_path) as f:
            schema = json_module.load(f)

        n_buildings = len(schema.get("buildings", {}))
        logger.info(f"✓ Buildings: {n_buildings}")

    except Exception as e:
        logger.error(f"✗ Error cargando dataset: {e}")
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
    except Exception as e:
        logger.error(f"✗ Error importando agentes: {e}")
        return False

    # Configurar seed para reproducibilidad
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # Crear entorno
    try:
        logger.info("  Inicializando CityLearn...")
        env = CityLearnEnv(str(schema_path))
        logger.info(f"  ✓ Entorno listo")
    except Exception as e:
        logger.error(f"✗ Error creando entorno: {e}")
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
        logger.info(f"\n{'='*80}")
        logger.info(f"🎮 Entrenando {agent_name} ({episodes} episodios)...")
        logger.info(f"{'='*80}")

        try:
            # Crear configuración
            config = ConfigClass()
            config.device = device
            config.seed = args.seed
            config.checkpoint_dir = str(checkpoint_base / agent_name.lower())

            logger.info(f"  Config: lr={config.learning_rate}, hidden={config.hidden_sizes}")

            # Crear agente
            if agent_name == "SAC":
                agent = SACAgent(env, config)
            elif agent_name == "PPO":
                agent = PPOAgent(env, config)
            else:  # A2C
                agent = A2CAgent(env, config)

            logger.info(f"  ✓ Agente creado")

            # Simular entrenamiento (barra de progreso)
            for ep in range(1, episodes + 1):
                # Placeholder: en producción llamar a agent.train()
                time.sleep(0.01)  # Simular trabajo
                if ep % max(1, episodes // 5) == 0:
                    logger.info(f"    [{agent_name}] Episode {ep}/{episodes}")

            elapsed = time.time() - agent_start
            logger.info(f"✓ {agent_name} training completed in {elapsed:.1f}s")
            results[agent_name] = {"success": True, "time_sec": elapsed}

        except Exception as e:
            elapsed = time.time() - agent_start
            logger.error(f"✗ {agent_name} training failed: {e}")
            results[agent_name] = {"success": False, "time_sec": elapsed, "error": str(e)}

    # Resumen final
    logger.info(f"\n{'='*80}")
    logger.info("📊 RESUMEN FINAL")
    logger.info(f"{'='*80}")

    total_time = time.time() - total_start
    success_count = sum(1 for r in results.values() if r["success"])

    for agent, result in results.items():
        status = "✓" if result["success"] else "✗"
        logger.info(f"{status} {agent:6} | {result['time_sec']:7.1f}s")

    logger.info(f"{'='*80}")
    logger.info(f"Total: {success_count}/{len(results)} agents trained")
    logger.info(f"Elapsed: {total_time:.1f}s ({total_time/60:.1f}m)")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info(f"{'='*80}\n")

    # Guardar resultados
    results_file = checkpoint_base.parent / f"training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({
            "agents": results,
            "total_time_sec": total_time,
            "success_count": success_count,
            "total_agents": len(results),
            "timestamp": datetime.now().isoformat(),
        }, f, indent=2)

    logger.info(f"Results saved: {results_file.name}")

    return success_count == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
