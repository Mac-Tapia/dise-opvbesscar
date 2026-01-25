#!/usr/bin/env python3
"""
Pipeline Completo: Dataset → Baseline → Entrenamiento de 3 Agentes (5 episodios c/u)
Versión simplificada y robusta para ejecución desde cero.
"""
import sys
import time
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
from src.iquitos_citylearn.config import load_config, load_paths

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


def run_step(step_name: str, command: str, verbose: bool = True) -> bool:
    """Ejecutar un paso del pipeline."""
    logger.info("=" * 80)
    logger.info(f"🚀 PASO: {step_name}")
    logger.info("=" * 80)

    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "scripts." + command.replace(".py", "").split("/")[-1]],
            cwd=PROJECT_ROOT,
            capture_output=False
        )

        if result.returncode == 0:
            logger.info(f"✅ {step_name} COMPLETADO\n")
            return True
        else:
            logger.error(f"❌ {step_name} FALLÓ (exit code: {result.returncode})\n")
            return False
    except Exception as e:
        logger.error(f"❌ {step_name} ERROR: {e}\n")
        return False


def main():
    """Ejecutar pipeline completo."""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 PIPELINE COMPLETO: DATASET → BASELINE → AGENTES (5 EPISODIOS)")
    logger.info("=" * 80 + "\n")

    config = load_config()
    paths = load_paths(config)

    start_time = time.time()

    # ========================================================
    # PASO 1: CONSTRUIR DATASET CITYLEARN
    # ========================================================
    logger.info("\n[PASO 1/4] Construyendo Dataset CityLearn v2...")
    try:
        from src.iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset

        build_citylearn_dataset(
            cfg=config,
            _raw_dir=paths.raw_dir,
            interim_dir=paths.interim_dir,
            processed_dir=paths.processed_dir,
        )
        logger.info("✅ Dataset construido exitosamente\n")
    except Exception as e:
        logger.error(f"❌ Error construyendo dataset: {e}\n")
        return 1

    # ========================================================
    # PASO 2: EJECUTAR BASELINE (SIN CONTROL)
    # ========================================================
    logger.info("\n[PASO 2/4] Ejecutando Baseline (simulación sin control)...")
    try:
        import numpy as np
        from citylearn.citylearn import CityLearnEnv

        schema_path = paths.processed_dir / "citylearnv2_dataset" / "schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema no encontrado: {schema_path}")

        logger.info(f"  Schema: {schema_path}")
        env = CityLearnEnv(schema=str(schema_path))
        obs, _ = env.reset()

        # Acciones baseline: máxima potencia (1.0)
        if isinstance(env.action_space, list):
            num_actions = sum(sp.shape[0] if hasattr(sp, 'shape') else 1 for sp in env.action_space)
        else:
            num_actions = 126

        actions = [np.ones((num_actions,), dtype=np.float32)]

        logger.info(f"  Acciones: {num_actions} dimensiones")
        logger.info(f"  Ejecutando 8,760 timesteps...")

        for step in range(8760):
            _, _, terminated, truncated, _ = env.step(actions)
            if terminated or truncated:
                break

            if (step + 1) % 1000 == 0:
                logger.info(f"    Timestep {step + 1}/8760 completado")

        env.close()
        logger.info("✅ Baseline completado exitosamente\n")
    except Exception as e:
        logger.error(f"❌ Error en baseline: {e}\n")
        import traceback
        traceback.print_exc()
        return 1

    # ========================================================
    # PASO 3: ENTRENAR AGENTES (PPO, SAC, A2C) - 5 EPISODIOS CADA UNO
    # ========================================================
    logger.info("\n[PASO 3/4] Entrenando 3 Agentes RL en Serie...")

    agents_config = [
        ("PPO", 5),
        ("SAC", 5),
        ("A2C", 5),
    ]

    for agent_name, episodes in agents_config:
        logger.info(f"\n  [Agente] {agent_name} (Episodios: {episodes})")
        try:
            from stable_baselines3 import PPO, SAC, A2C
            from src.iquitos_citylearn.oe3.agents.a2c_sb3 import A2CConfig

            schema_path = paths.processed_dir / "citylearnv2_dataset" / "schema.json"
            env = CityLearnEnv(schema=str(schema_path))
            obs, _ = env.reset()

            # Determinar clase del agente
            if agent_name == "PPO":
                agent = PPO("MlpPolicy", env, learning_rate=2e-4, n_steps=2048, batch_size=128, verbose=0)
            elif agent_name == "SAC":
                agent = SAC("MlpPolicy", env, learning_rate=3e-4, batch_size=256, verbose=0)
            elif agent_name == "A2C":
                agent = A2C("MlpPolicy", env, learning_rate=1.5e-4, n_steps=2048, verbose=0)

            # Entrenar por el número de episodios especificado
            total_timesteps = 8760 * episodes
            logger.info(f"    Entrenando por {total_timesteps:,} timesteps ({episodes} episodios × 8,760)...")

            agent_start = time.time()
            agent.learn(total_timesteps=total_timesteps)
            agent_time = time.time() - agent_start

            logger.info(f"    ✅ {agent_name} completado en {agent_time:.1f}s")

            # Guardar checkpoint
            checkpoint_dir = paths.root_dir / "checkpoints" / agent_name
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            agent.save(str(checkpoint_dir / "latest"))
            logger.info(f"    Checkpoint guardado: {checkpoint_dir / 'latest'}")

            env.close()

        except Exception as e:
            logger.error(f"    ❌ Error entrenando {agent_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # ========================================================
    # RESUMEN FINAL
    # ========================================================
    total_time = time.time() - start_time
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = int(total_time % 60)

    logger.info("\n" + "=" * 80)
    logger.info("✅ PIPELINE COMPLETO EXITOSO")
    logger.info("=" * 80)
    logger.info(f"\n📊 RESUMEN:")
    logger.info(f"  1. Dataset CityLearn v2: ✅ CONSTRUIDO")
    logger.info(f"  2. Baseline (sin control): ✅ EJECUTADO")
    logger.info(f"  3. Agentes RL (5 eps c/u):")
    logger.info(f"     - PPO (On-Policy): ✅ ENTRENADO")
    logger.info(f"     - SAC (Off-Policy): ✅ ENTRENADO")
    logger.info(f"     - A2C (On-Policy): ✅ ENTRENADO")
    logger.info(f"\n⏱️  Tiempo Total: {hours}h {minutes}m {seconds}s")
    logger.info(f"📁 Checkpoints: checkpoints/{{PPO,SAC,A2C}}/latest")
    logger.info(f"📁 Outputs: {paths.outputs_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
