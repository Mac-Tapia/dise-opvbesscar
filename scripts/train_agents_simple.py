#!/usr/bin/env python3
"""
Script simple para entrenar agentes RL usando los módulos de data_loader y dataset_constructor.

Este script:
1. Carga el dataset ya construido (EJECUTAR_PIPELINE_MAESTRO.py debe ejecutarse primero)
2. Entrena agentes SAC y PPO con stable-baselines3
3. Guarda checkpoints en checkpoints/SAC y checkpoints/PPO
4. Monitorea progreso en consola
"""

import json
import logging
import sys
from pathlib import Path
from dataclasses import dataclass

import numpy as np

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Rutas
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED = PROJECT_ROOT / 'data' / 'processed'
CHECKPOINTS_DIR = PROJECT_ROOT / 'checkpoints'


@dataclass
class TrainingConfig:
    """Configuración de entrenamiento RL."""
    total_steps: int = 50000  # Total de pasos de entrenamiento
    learning_rate: float = 2.0e-4
    batch_size: int = 128
    device: str = "cpu"  # "cpu" o "cuda"
    save_interval: int = 5000  # Guardar checkpoint cada N pasos
    log_interval: int = 1000  # Log cada N pasos


def check_dependencies():
    """Verificar si existen las dependencias necesarias."""
    try:
        import gymnasium as gym
        import stable_baselines3
        logger.info("✓ Dependencias instaladas: gymnasium, stable_baselines3")
        return True
    except ImportError as e:
        logger.warning(f"⚠ Falta instalación: {e}")
        logger.info("Instala con: pip install stable-baselines3[extra] gymnasium")
        return False


def load_dataset():
    """Cargar dataset del procesamiento anterior."""
    logger.info("Cargando dataset...")

    observations_file = DATA_PROCESSED / 'dataset' / 'observations_raw.csv'
    if not observations_file.exists():
        logger.error(f"❌ Dataset no encontrado: {observations_file}")
        logger.error("Ejecuta primero: python scripts/EJECUTAR_PIPELINE_MAESTRO.py")
        return None

    try:
        import pandas as pd
        obs_df = pd.read_csv(observations_file, index_col=0)
        observations = obs_df.values.astype(np.float32)
        logger.info(f"✓ Observaciones cargadas: shape={observations.shape}")
        return observations
    except Exception as e:
        logger.error(f"Error cargando dataset: {e}")
        return None


def create_dummy_env(observation_dim=394, action_dim=126):
    """
    Crear un environment dummy que tenga la interfaz de Gymnasium.

    Este es un placeholder para cuando el usuario instale gymnasium
    y quiera usar CityLearnEnv real.
    """
    import gymnasium as gym
    from gymnasium import spaces

    class DummyRLEnv(gym.Env):
        """Environment placeholder para RL training."""
        def __init__(self, obs_dim=394, act_dim=126):
            super().__init__()
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
            )
            self.action_space = spaces.Box(
                low=0.0, high=1.0, shape=(act_dim,), dtype=np.float32
            )
            self.timestep = 0
            self.max_timesteps = 8760

        def step(self, action):
            # Reward dummy: suma de acciones (agente aprende a maximizar)
            reward = float(np.sum(action))
            self.timestep += 1
            done = self.timestep >= self.max_timesteps
            obs = np.random.randn(self.observation_space.shape[0]).astype(np.float32)
            return obs, reward, done, False, {}

        def reset(self, seed=None):
            super().reset(seed=seed)
            self.timestep = 0
            obs = np.random.randn(self.observation_space.shape[0]).astype(np.float32)
            return obs, {}

        def render(self):
            pass

    return DummyRLEnv(obs_dim=observation_dim, act_dim=action_dim)


def train_sac_agent(env, config: TrainingConfig):
    """Entrenar agente SAC."""
    from stable_baselines3 import SAC

    logger.info("="*70)
    logger.info("Entrenando SAC (Soft Actor-Critic)")
    logger.info("="*70)

    # Crear o cargar modelo
    model_path = CHECKPOINTS_DIR / 'SAC' / 'latest'
    if model_path.exists():
        logger.info(f"Cargando SAC desde: {model_path}")
        model = SAC.load(str(model_path), env=env, device=config.device)
    else:
        logger.info("Creando nuevo modelo SAC")
        model = SAC(
            'MlpPolicy',
            env,
            learning_rate=config.learning_rate,
            batch_size=config.batch_size,
            device=config.device,
            verbose=1,
            tensorboard_log=str(PROJECT_ROOT / 'logs')
        )

    try:
        model.learn(
            total_timesteps=config.total_steps,
            log_interval=config.log_interval,
            progress_bar=True
        )

        # Guardar modelo
        save_dir = CHECKPOINTS_DIR / 'SAC'
        save_dir.mkdir(parents=True, exist_ok=True)
        model.save(str(save_dir / 'latest'))
        logger.info(f"✓ SAC guardado en: {save_dir / 'latest'}.zip")

        return model
    except KeyboardInterrupt:
        logger.info("⚠ Entrenamiento SAC interrumpido por usuario")
        return model


def train_ppo_agent(env, config: TrainingConfig):
    """Entrenar agente PPO."""
    from stable_baselines3 import PPO

    logger.info("="*70)
    logger.info("Entrenando PPO (Proximal Policy Optimization)")
    logger.info("="*70)

    # Crear o cargar modelo
    model_path = CHECKPOINTS_DIR / 'PPO' / 'latest'
    if model_path.exists():
        logger.info(f"Cargando PPO desde: {model_path}")
        model = PPO.load(str(model_path), env=env, device=config.device)
    else:
        logger.info("Creando nuevo modelo PPO")
        model = PPO(
            'MlpPolicy',
            env,
            learning_rate=config.learning_rate,
            batch_size=config.batch_size,
            n_epochs=20,
            n_steps=2048,
            device=config.device,
            verbose=1,
            tensorboard_log=str(PROJECT_ROOT / 'logs')
        )

    try:
        model.learn(
            total_timesteps=config.total_steps,
            log_interval=config.log_interval,
            progress_bar=True
        )

        # Guardar modelo
        save_dir = CHECKPOINTS_DIR / 'PPO'
        save_dir.mkdir(parents=True, exist_ok=True)
        model.save(str(save_dir / 'latest'))
        logger.info(f"✓ PPO guardado en: {save_dir / 'latest'}.zip")

        return model
    except KeyboardInterrupt:
        logger.info("⚠ Entrenamiento PPO interrumpido por usuario")
        return model


def main():
    """Función principal."""
    logger.info("="*70)
    logger.info("ENTRENAR AGENTES RL (SAC, PPO)")
    logger.info("="*70)
    logger.info("")

    # Verificar dependencias
    if not check_dependencies():
        logger.warning("\n⚠ No se pueden entrenar agentes sin dependencias.")
        logger.info("Instala con: pip install stable-baselines3[extra] gymnasium")
        logger.info("\nPero el dataset ya está construido y listo para training.")
        return 1

    # Cargar dataset
    obs_data = load_dataset()
    if obs_data is None:
        return 1

    # Crear environment
    obs_dim = obs_data.shape[1]
    action_dim = 126

    logger.info(f"Creando environment: obs_dim={obs_dim}, action_dim={action_dim}")
    try:
        env = create_dummy_env(observation_dim=obs_dim, action_dim=action_dim)
        logger.info("✓ Environment creado")
    except Exception as e:
        logger.error(f"Error creando environment: {e}")
        return 1

    # Configuración
    config = TrainingConfig(
        total_steps=50000,
        learning_rate=2.0e-4,
        batch_size=128,
        device="cpu"  # Cambiar a "cuda" si está disponible
    )

    # Entrenar agentes
    try:
        sac_model = train_sac_agent(env, config)
        logger.info("✓ SAC entrenado exitosamente\n")
    except Exception as e:
        logger.error(f"Error entrenando SAC: {e}")
        sac_model = None

    try:
        ppo_model = train_ppo_agent(env, config)
        logger.info("✓ PPO entrenado exitosamente\n")
    except Exception as e:
        logger.error(f"Error entrenando PPO: {e}")
        ppo_model = None

    logger.info("="*70)
    logger.info("ENTRENAMIENTO COMPLETADO")
    logger.info("="*70)
    logger.info(f"Checkpoints guardados en: {CHECKPOINTS_DIR}")
    logger.info("Para usar los modelos entrenados:")
    logger.info("  from stable_baselines3 import SAC, PPO")
    logger.info("  sac = SAC.load('checkpoints/SAC/latest')")
    logger.info("  ppo = PPO.load('checkpoints/PPO/latest')")

    return 0


if __name__ == "__main__":
    sys.exit(main())
