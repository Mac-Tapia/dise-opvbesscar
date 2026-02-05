"""Script de Simulación OE3 - Ejecuta agentes RL con dataset OE3.

Uso:
    python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac
    python -m scripts.run_oe3_simulate --config configs/default.yaml --agent ppo
    python -m scripts.run_oe3_simulate --config configs/default.yaml --agent a2c
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional, Any, Dict
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(config_path: str | Path) -> Dict[str, Any]:
    """Carga configuración desde YAML.

    Args:
        config_path: Ruta a YAML

    Returns:
        Diccionario con configuración

    Raises:
        FileNotFoundError: Si no existe archivo
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ValueError("Config must be a YAML dictionary")

        logger.info(f"✓ Config loaded: {config_path}")
        return config
    except ImportError:
        logger.error("PyYAML not installed")
        raise
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise


def build_environment(config: Dict[str, Any]) -> Any:
    """Construye CityLearn environment con datos OE3.

    Args:
        config: Configuración cargada

    Returns:
        CityLearn environment o mock para testing

    Raises:
        RuntimeError: Si no se puede construir env
    """
    try:
        from src.iquitos_citylearn.oe3.dataset_builder_consolidated import (
            build_iquitos_env,
            validate_dataset
        )
    except ImportError as e:
        logger.error(f"Cannot import dataset builder: {e}")
        raise

    dataset_dir = config.get("dataset_dir", "data/interim/oe3")

    logger.info(f"Building environment from {dataset_dir}...")

    # Validar dataset
    validation = validate_dataset(dataset_dir)
    if not validation["is_valid"]:
        logger.error(f"Dataset validation failed: {validation['errors']}")
        raise RuntimeError("Dataset validation failed")

    if validation["warnings"]:
        for warning in validation["warnings"]:
            logger.warning(f"Dataset warning: {warning}")

    # Construir environment
    result = build_iquitos_env(
        config,
        dataset_dir=dataset_dir
    )

    if not result["is_valid"]:
        logger.error(f"Environment build failed: {result['errors']}")
        raise RuntimeError("Environment build failed")

    env = result.get("env")
    if env is None:
        logger.warning("CityLearn environment not available, using mock")
        return _create_mock_env(config)

    logger.info(f"✓ Environment built successfully")
    return env


def _create_mock_env(config: Dict[str, Any]) -> Any:
    """Crea mock environment para testing (sin CityLearn real).

    Args:
        config: Configuración

    Returns:
        Mock object con interface compatible
    """
    class MockEnv:
        def __init__(self, cfg):
            self.config = cfg
            self.observation_space = MockSpace(shape=(394,))
            self.action_space = MockSpace(shape=(129,))
            self.buildings = [MockBuilding()]
            self.time_step = 0

        def reset(self):
            self.time_step = 0
            return np.zeros(394), {}

        def step(self, action):
            self.time_step += 1
            obs = np.zeros(394)
            reward = 0.1
            terminated = self.time_step >= 8760
            truncated = False
            return obs, reward, terminated, truncated, {}

    class MockSpace:
        def __init__(self, shape):
            self.shape = shape

    class MockBuilding:
        def __init__(self):
            self.energy_simulation = MockEnergySimulation()

    class MockEnergySimulation:
        def __init__(self):
            self.non_shiftable_load = [100.0] * 8760
            self.solar_generation = [500.0] * 8760

    import numpy as np
    logger.info("Using mock environment for testing")
    return MockEnv(config)


def create_agent(env: Any, agent_type: str, config: Dict[str, Any]) -> Any:
    """Crea agente RL del tipo especificado.

    Args:
        env: Environment
        agent_type: "sac", "ppo", o "a2c"
        config: Configuración

    Returns:
        Agente RL (SAC, PPO, o A2C)

    Raises:
        ValueError: Si agent_type inválido
    """
    from src.agents.sac import make_sac, SACConfig
    from src.agents.ppo_sb3 import make_ppo, PPOConfig
    from src.agents.a2c_sb3 import make_a2c, A2CConfig

    agent_type = agent_type.lower()

    if agent_type == "sac":
        cfg = SACConfig(
            episodes=config.get("sac_episodes", 5),
            learning_rate=config.get("sac_lr", 5e-5),
            checkpoint_dir=str(Path(config.get("checkpoint_dir", "checkpoints")) / "SAC"),
            progress_path=str(Path(config.get("output_dir", "outputs")) / "sac_progress.csv")
        )
        logger.info(f"Creating SAC agent: {cfg.episodes} episodes, lr={cfg.learning_rate}")
        return make_sac(env, cfg)

    elif agent_type == "ppo":
        cfg = PPOConfig(
            train_steps=config.get("ppo_steps", 500000),
            learning_rate=config.get("ppo_lr", 1e-4),
            checkpoint_dir=str(Path(config.get("checkpoint_dir", "checkpoints")) / "PPO"),
            progress_path=str(Path(config.get("output_dir", "outputs")) / "ppo_progress.csv")
        )
        logger.info(f"Creating PPO agent: {cfg.train_steps} steps, lr={cfg.learning_rate}")
        return make_ppo(env, cfg)

    elif agent_type == "a2c":
        cfg = A2CConfig(
            train_steps=config.get("a2c_steps", 500000),
            learning_rate=config.get("a2c_lr", 1e-4),
            checkpoint_dir=str(Path(config.get("checkpoint_dir", "checkpoints")) / "A2C"),
            progress_path=str(Path(config.get("output_dir", "outputs")) / "a2c_progress.csv")
        )
        logger.info(f"Creating A2C agent: {cfg.train_steps} steps, lr={cfg.learning_rate}")
        return make_a2c(env, cfg)

    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def main(
    config_path: str,
    agent_type: str = "sac",
    episodes: Optional[int] = None,
    steps: Optional[int] = None
) -> int:
    """Función main para ejecutar simulación.

    Args:
        config_path: Ruta a config YAML
        agent_type: "sac", "ppo", o "a2c"
        episodes: Override de episodios (solo para SAC)
        steps: Override de steps (para PPO/A2C)

    Returns:
        0 si éxito, 1 si error
    """
    try:
        # Cargar config
        config = load_config(config_path)

        # Crear directorios necesarios
        Path(config.get("checkpoint_dir", "checkpoints")).mkdir(parents=True, exist_ok=True)
        Path(config.get("output_dir", "outputs")).mkdir(parents=True, exist_ok=True)

        # Construir environment
        env = build_environment(config)

        # Crear agente
        agent = create_agent(env, agent_type, config)

        # Entrenar
        logger.info(f"Starting {agent_type.upper()} training...")
        if agent_type == "sac" and episodes is not None:
            agent.learn(episodes=episodes)
        elif agent_type in ("ppo", "a2c") and steps is not None:
            agent.learn(total_timesteps=steps)
        else:
            agent.learn()

        logger.info(f"✓ {agent_type.upper()} training completed")
        return 0

    except Exception as e:
        logger.error(f"Error during training: {e}", exc_info=True)
        return 1


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comando."""
    parser = argparse.ArgumentParser(
        description="OE3 Simulation - Run RL agents on CityLearn"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Path to YAML config file"
    )

    parser.add_argument(
        "--agent",
        type=str,
        choices=["sac", "ppo", "a2c"],
        default="sac",
        help="Agent type to train"
    )

    parser.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="Override number of episodes (SAC only)"
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Override total training steps (PPO/A2C only)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run
    exit_code = main(
        config_path=args.config,
        agent_type=args.agent,
        episodes=args.episodes,
        steps=args.steps
    )

    sys.exit(exit_code)
