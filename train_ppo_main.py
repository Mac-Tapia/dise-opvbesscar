#!/usr/bin/env python
"""Script principal para entrenar agente PPO con datos OE3 construidos.

Ejecuta:
    python train_ppo_main.py

o si está en .venv:
    .venv/Scripts/python train_ppo_main.py
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
import yaml

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Ejecuta entrenamiento PPO."""
    print("\n" + "="*80)
    print("🚀 ENTRENAMIENTO PPO CON DATOS OE3")
    print("="*80 + "\n")

    # 1. Cargar configuración
    config_path = Path("configs/default.yaml")
    if not config_path.exists():
        logger.error(f"Archivo de configuración no encontrado: {config_path}")
        return 1

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    logger.info(f"✓ Configuración cargada desde {config_path}")

    # 2. Construir ambiente CityLearn
    from src.iquitos_citylearn.oe3.dataset_builder_consolidated import build_iquitos_env

    dataset_dir = Path("data/interim/oe3")

    logger.info("Construyendo ambiente CityLearn con datos OE3...")
    env_result = build_iquitos_env(
        config=config,
        solar_csv_path="data/interim/oe3/pv_generation_timeseries.csv",
        chargers_json_path=None,  # Los chargers están en archivos CSV individuales
        dataset_dir=str(dataset_dir)
    )

    if not env_result["is_valid"]:
        logger.error("Error construyendo ambiente:")
        for error in env_result["errors"]:
            logger.error(f"  - {error}")
        return 1

    env = env_result.get("env")
    if env is None:
        logger.error("Ambiente CityLearn no se creó correctamente")
        return 1

    logger.info("✓ Ambiente CityLearn creado exitosamente")

    # 3. Validar espacios de observación y acción
    from src.utils.agent_utils import validate_env_spaces

    try:
        validate_env_spaces(env)
        logger.info("✓ Espacios de observación y acción validados")
    except Exception as e:
        logger.error(f"Error validando espacios: {e}")
        return 1

    # 4. Crear y entrenar agente PPO
    from src.agents.ppo_sb3 import PPOAgent, PPOConfig, make_ppo

    logger.info("\nConfiguración PPO:")
    ppo_config = PPOConfig(
        train_steps=50000,  # Comenzar con pasos reducidos para prueba
        n_steps=2048,
        batch_size=256,
        n_epochs=10,
        learning_rate=1e-4,
        clip_range=0.2,
        ent_coef=0.01,
    )
    logger.info(f"  - Training steps: {ppo_config.train_steps}")
    logger.info(f"  - Batch size: {ppo_config.batch_size}")
    logger.info(f"  - Learning rate: {ppo_config.learning_rate}")
    logger.info(f"  - Entropy coefficient: {ppo_config.ent_coef}")

    try:
        logger.info("\nCreando agente PPO...")
        agent = make_ppo(env, config=ppo_config)
        logger.info("✓ Agente PPO creado exitosamente")
    except Exception as e:
        logger.error(f"Error creando agente PPO: {e}")
        return 1

    # 5. Entrenamiento
    try:
        logger.info(f"\nIniciando entrenamiento por {ppo_config.train_steps} pasos...")
        logger.info("(Esto puede tomar varios minutos en GPU RTX 4060)")
        print("\n" + "-"*80)

        agent.learn(total_timesteps=ppo_config.train_steps)

        print("-"*80)
        logger.info("✓ Entrenamiento completado exitosamente")
    except KeyboardInterrupt:
        logger.warning("\nEntrenamiento interrumpido por usuario")
        print("-"*80)
    except Exception as e:
        logger.error(f"Error durante entrenamiento: {e}")
        return 1

    # 6. Guardar checkpoint
    try:
        from src.utils.agent_utils import save_checkpoint
        checkpoint_path = save_checkpoint(agent, agent_name="PPO")
        logger.info(f"✓ Checkpoint guardado en: {checkpoint_path}")
    except Exception as e:
        logger.warning(f"No se pudo guardar checkpoint: {e}")

    print("\n" + "="*80)
    print("✅ ENTRENAMIENTO PPO COMPLETADO")
    print("="*80)
    print(f"\nDetalles:")
    print(f"  - Pasos completados: {ppo_config.train_steps}")
    print(f"  - Ambiente: CityLearn v2 (8,760 timesteps)")
    print(f"  - Dispositivo: GPU (si disponible)")
    print(f"\nPróximos pasos:")
    print(f"  1. Evaluar el agente con validate_env.py")
    print(f"  2. Comparar con baselines (CON e SIN solar)")
    print(f"  3. Ejecutar scripts.run_dual_baselines para análisis completo\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
