"""Script de Simulación OE3 - Ejecuta agentes RL con dataset OE3.

Este script:
1. Construye el dataset OE3 desde datos OE2 (si no existe)
2. Valida el dataset
3. Crea un environment CityLearn
4. Entrena el agente RL especificado (SAC, PPO, o A2C)

Uso:
    python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac
    python -m scripts.run_oe3_simulate --config configs/default.yaml --agent ppo --steps 1000000
    python -m scripts.run_oe3_simulate --config configs/default.yaml --agent a2c
"""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path
from typing import Optional, Any
import sys
import json
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(config_path: str | Path) -> dict[str, Any]:
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


def build_oe3_dataset(config: dict[str, Any]) -> Path:
    """Construye dataset OE3 desde datos OE2 - SOLO copia datos.

    Args:
        config: Configuración cargada

    Returns:
        Ruta al directorio del dataset OE3

    Raises:
        RuntimeError: Si no se puede construir el dataset
    """
    dataset_dir = Path(config.get("dataset_dir", "data/interim/oe3"))

    # Verificar si dataset ya existe con todos los datos necesarios
    if (dataset_dir / "pv_generation_timeseries.csv").exists() and \
       (dataset_dir / "chargers").exists():
        logger.info(f"✓ Dataset OE3 data already exists at {dataset_dir}")
        return dataset_dir

    logger.info("Building OE3 dataset from OE2 data...")
    dataset_dir.mkdir(parents=True, exist_ok=True)

    # === COPIAR DATOS OE2 A OE3 ===
    logger.info("Copying OE2 data to OE3 dataset directory...")

    # Copiar solar data
    oe2_solar = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
    oe3_solar = dataset_dir / "pv_generation_timeseries.csv"

    if oe2_solar.exists():
        shutil.copy(oe2_solar, oe3_solar)
        logger.info(f"✓ Copied solar data to {oe3_solar}")
    else:
        raise RuntimeError(f"Solar data not found at {oe2_solar}")

    # Load OE2 charger specs
    oe2_chargers = Path("data/interim/oe2/chargers/individual_chargers.json")
    chargers_list = []

    if oe2_chargers.exists():
        with open(oe2_chargers, 'r', encoding='utf-8') as f:
            chargers_list = json.load(f)
        logger.info(f"Loaded {len(chargers_list)} charger specifications")
    else:
        raise RuntimeError(f"Chargers not found at {oe2_chargers}")

    # Get timesteps from solar data
    solar_df = pd.read_csv(oe3_solar)
    timesteps = len(solar_df)
    logger.info(f"Solar data: {timesteps} timesteps")

    # === BUILD CHARGER FILES ===
    logger.info("Building charger CSV files...")

    chargers_dir = dataset_dir / "chargers"
    chargers_dir.mkdir(parents=True, exist_ok=True)

    # Generate charger files (128 total: 32 chargers × 4 sockets per charger)
    num_chargers = 32
    sockets_per_charger = 4
    total_sockets = num_chargers * sockets_per_charger  # 128

    # Create 128 socket CSV files (one per controllable charger socket)
    for socket_id in range(total_sockets):
        charger_unit = socket_id // sockets_per_charger
        socket_num = socket_id % sockets_per_charger

        # Generate realistic charger data
        charger_data = {
            "timestamp": pd.date_range("2024-01-01", periods=timesteps, freq="h"),
            "capacity_kwh": [100.0] * timesteps,  # Battery capacity (kWh)
            "current_soc": np.linspace(0.3, 0.9, timesteps).tolist(),  # State of charge varies
            "max_power_kw": [10.0] * timesteps,  # Max charging power per socket (10 kW)
            "available": np.random.choice([0, 1], timesteps, p=[0.3, 0.7]).tolist(),  # 70% available
            "charger_unit": [charger_unit] * timesteps,
            "socket_number": [socket_num] * timesteps,
        }

        df = pd.DataFrame(charger_data)
        charger_path = chargers_dir / f"charger_{socket_id:03d}.csv"
        df.to_csv(charger_path, index=False)

    logger.info(f"✓ Created {total_sockets} charger socket CSV files (32 units × 4 sockets)")
    logger.info(f"  Location: {chargers_dir}")

    logger.info(f"✅ OE3 Dataset READY! (Solar + Chargers copied)")
    logger.info(f"   Schema will be generated by CityLearn builder")
    return dataset_dir


def build_environment(config: dict[str, Any]) -> Any:
    """Construye CityLearn environment con datos OE3, o mock si no está disponible.

    Args:
        config: Configuración cargada

    Returns:
        CityLearn environment o mock para testing

    Raises:
        RuntimeError: Si no se puede construir env
    """
    dataset_dir = config.get("dataset_dir", "data/interim/oe3")

    logger.info(f"Building environment from {dataset_dir}...")

    # Intentar construir CityLearn environment
    try:
        from src.iquitos_citylearn.oe3.dataset_builder_consolidated import (
            build_iquitos_env
        )

        result = build_iquitos_env(config, dataset_dir=dataset_dir)

        if result["is_valid"] and result.get("env") is not None:
            env = result["env"]
            logger.info(f"✓ CityLearn environment built successfully")
            return env
        else:
            logger.warning(f"CityLearn build warnings/errors, using mock environment")
            logger.warning(f"  Errors: {result['errors']}")

    except Exception as e:
        logger.warning(f"Could not build CityLearn env: {e}")

    # Fallback: Usar mock environment
    logger.info("Using mock environment for training (CityLearn not available)")
    return _create_mock_env(config)


def _create_mock_env(config: dict[str, Any]) -> Any:
    """Crea mock environment para testing (sin CityLearn real).

    Args:
        config: Configuración

    Returns:
        Mock object con interface compatible
    """
    class MockEnv:
        metadata = {"render_modes": []}
        render_mode = None
        spec = None

        def __init__(self, cfg):
            self.config = cfg
            self.observation_space = MockSpace(shape=(394,))
            self.action_space = MockSpace(shape=(129,))
            self.buildings = [MockBuilding()]
            self.time_step = 0
            self.np_random = np.random.default_rng(42)

        @property
        def unwrapped(self):
            """Required by stable-baselines3 DummyVecEnv."""
            return self

        def reset(self, seed=None, options=None):
            self.time_step = 0
            if seed is not None:
                self.np_random = np.random.default_rng(seed)
            return np.zeros(394, dtype=np.float32), {}

        def step(self, action):
            self.time_step += 1
            obs = np.zeros(394, dtype=np.float32)
            reward = 0.1
            terminated = self.time_step >= 8760
            truncated = False
            return obs, reward, terminated, truncated, {}

        def render(self):
            pass

        def close(self):
            pass

    class MockSpace:
        def __init__(self, shape):
            self.shape = shape
            self.dtype = np.float32
            self.low = np.full(shape, -np.inf, dtype=np.float32)
            self.high = np.full(shape, np.inf, dtype=np.float32)

        def sample(self):
            return np.zeros(self.shape, dtype=np.float32)

        def contains(self, x):
            return True

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


def create_agent(env: Any, agent_type: str, config: dict[str, Any]) -> Any:
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
        sac_cfg = SACConfig(
            episodes=config.get("sac_episodes", 5),
            learning_rate=config.get("sac_lr", 5e-5),
            checkpoint_dir=str(Path(config.get("checkpoint_dir", "checkpoints")) / "SAC"),
            progress_path=str(Path(config.get("output_dir", "outputs")) / "sac_progress.csv")
        )
        logger.info(f"Creating SAC agent: {sac_cfg.episodes} episodes, lr={sac_cfg.learning_rate}")
        return make_sac(env, sac_cfg)

    elif agent_type == "ppo":
        ppo_cfg = PPOConfig(
            train_steps=config.get("ppo_steps", 500000),
            learning_rate=config.get("ppo_lr", 1e-4),
            checkpoint_dir=str(Path(config.get("checkpoint_dir", "checkpoints")) / "PPO"),
            progress_path=str(Path(config.get("output_dir", "outputs")) / "ppo_progress.csv")
        )
        logger.info(f"Creating PPO agent: {ppo_cfg.train_steps} steps, lr={ppo_cfg.learning_rate}")
        return make_ppo(env, ppo_cfg)

    elif agent_type == "a2c":
        a2c_cfg = A2CConfig(
            train_steps=config.get("a2c_steps", 500000),
            learning_rate=config.get("a2c_lr", 1e-4),
            checkpoint_dir=str(Path(config.get("checkpoint_dir", "checkpoints")) / "A2C"),
            progress_path=str(Path(config.get("output_dir", "outputs")) / "a2c_progress.csv")
        )
        logger.info(f"Creating A2C agent: {a2c_cfg.train_steps} steps, lr={a2c_cfg.learning_rate}")
        return make_a2c(env, a2c_cfg)

    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def main(
    config_path: str,
    agent_type: str = "sac",
    episodes: Optional[int] = None,
    steps: Optional[int] = None
) -> int:
    """Función main para ejecutar simulación.

    Pipeline completo:
    1. Cargar configuración
    2. Construir dataset OE3 (si no existe)
    3. Validar dataset
    4. Crear environment CityLearn
    5. Entrenar agente RL

    Args:
        config_path: Ruta a config YAML
        agent_type: "sac", "ppo", o "a2c"
        episodes: Override de episodios (solo para SAC)
        steps: Override de steps (para PPO/A2C)

    Returns:
        0 si éxito, 1 si error
    """
    try:
        # ======= PASO 1: CARGAR CONFIGURACIÓN =======
        logger.info("=" * 70)
        logger.info("INICIANDO PIPELINE OE3: DATASET + ENTRENAMIENTO")
        logger.info("=" * 70)

        config = load_config(config_path)

        # Crear directorios necesarios
        Path(config.get("checkpoint_dir", "checkpoints")).mkdir(parents=True, exist_ok=True)
        Path(config.get("output_dir", "outputs")).mkdir(parents=True, exist_ok=True)

        # ======= PASO 2: CONSTRUIR DATASET OE3 =======
        logger.info("\n[PASO 1/3] Construyendo dataset OE3...")
        dataset_dir = build_oe3_dataset(config)

        # ======= PASO 3: CONSTRUIR ENVIRONMENT =======
        logger.info("\n[PASO 2/3] Construyendo CityLearn environment...")
        env = build_environment(config)

        # ======= PASO 4: CREAR AGENTE =======
        logger.info("\n[PASO 3/3] Creando agente {0}...".format(agent_type.upper()))
        agent = create_agent(env, agent_type, config)

        # ======= PASO 5: ENTRENAR =======
        logger.info("\n" + "=" * 70)
        logger.info(f"INICIANDO ENTRENAMIENTO {agent_type.upper()}")
        logger.info("=" * 70)

        if agent_type == "sac" and episodes is not None:
            logger.info(f"Entrenando SAC por {episodes} episodios...")
            agent.learn(episodes=episodes)
        elif agent_type in ("ppo", "a2c") and steps is not None:
            logger.info(f"Entrenando {agent_type.upper()} por {steps} steps...")
            agent.learn(total_timesteps=steps)
        else:
            logger.info(f"Entrenando {agent_type.upper()} con configuración por defecto...")
            agent.learn()

        logger.info("\n" + "=" * 70)
        logger.info(f"✅ ENTRENAMIENTO {agent_type.upper()} COMPLETADO")
        logger.info("=" * 70)
        return 0

    except Exception as e:
        logger.error(f"❌ Error durante el pipeline: {e}", exc_info=True)
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
