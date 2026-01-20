#!/usr/bin/env python
"""
A2C TRAINING - DEBUG VERSION CON METRICAS Y VALIDACION
"""
import sys
import os
from pathlib import Path
import logging
import numpy as np
import gymnasium as gym
from stable_baselines3 import A2C
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback

# Setup logging con formato visible
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("analyses/logs/a2c_debug.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))
from citylearn.citylearn import CityLearnEnv


class MetricsCallback(BaseCallback):
    """Callback para registrar métricas durante entrenamiento"""
    
    def __init__(self):
        super().__init__()
        self.episode_rewards = []
        
    def _on_step(self) -> bool:
        # Registrar cada 100 pasos
        if self.num_timesteps % 100 == 0:
            logger.info(f"Step {self.num_timesteps}/17520 | Local steps: {self.model.num_timesteps}")
        return True


class FlatActionWrapper(gym.Wrapper):
    """Flatten action y observation para Gymnasium compatibility."""
    
    def __init__(self, env):
        super().__init__(env)
        
        if isinstance(self.env.action_space, list):
            self.agent_action_spaces = self.env.action_space
            self.total_action_size = sum(space.shape[0] for space in self.agent_action_spaces)
            logger.info(f"[ENV] Action spaces (list): {len(self.agent_action_spaces)} agents")
            for i, space in enumerate(self.agent_action_spaces):
                logger.debug(f"  Agent {i}: Box{space.shape}")
        else:
            logger.error("Unexpected action_space type")
            sys.exit(1)
        
        obs, _ = env.reset()
        obs_flat = self._flatten_obs(obs)
        logger.info(f"[ENV] Observation flattened shape: {obs_flat.shape}")
        
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf,
            shape=obs_flat.shape,
            dtype=np.float32,
        )
        self.action_space = gym.spaces.Box(
            low=-1.0, high=1.0,
            shape=(self.total_action_size,),
            dtype=np.float32,
        )
        logger.info(f"[ENV] Flattened action space: {self.action_space}")
    
    def _flatten_obs(self, obs):
        """Convierte obs (lista) a array."""
        if isinstance(obs, list):
            def flatten_recursive(x):
                if isinstance(x, (list, tuple)):
                    result = []
                    for item in x:
                        result.extend(flatten_recursive(item))
                    return result
                else:
                    return [x]
            flat = flatten_recursive(obs)
            return np.array(flat, dtype=np.float32)
        return np.array(obs, dtype=np.float32).flatten()
    
    def _unflatten_action(self, flat_action):
        """Convierte action flat a lista de actions."""
        actions = []
        idx = 0
        for space in self.agent_action_spaces:
            size = space.shape[0]
            actions.append(flat_action[idx:idx+size])
            idx += size
        return actions
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        return self._flatten_obs(obs), info
    
    def step(self, action):
        action_list = self._unflatten_action(action)
        obs, reward, terminated, truncated, info = self.env.step(action_list)
        obs_flat = self._flatten_obs(obs)
        if isinstance(reward, list):
            reward_scalar = float(sum(reward))
        else:
            reward_scalar = float(reward)
        return obs_flat, reward_scalar, terminated, truncated, info


def main():
    logger.info("="*100)
    logger.info("A2C TRAINING - DEBUG VERSION CON VALIDACION DE SCHEMA Y METRICAS")
    logger.info("="*100)
    
    # 1. VALIDAR SCHEMA
    logger.info("\n[PASO 1] VALIDANDO SCHEMA")
    schema_path = Path("data/raw/citylearn_templates/schema.json")
    if not schema_path.exists():
        logger.error(f"X SCHEMA NO ENCONTRADO: {schema_path}")
        sys.exit(1)
    logger.info(f"V Schema encontrado: {schema_path}")
    
    # 2. CREAR ENVIRONMENT
    logger.info("\n[PASO 2] CREANDO ENVIRONMENT (CONECTANDO A SCHEMA)")
    try:
        base_env = CityLearnEnv(schema=str(schema_path))
        logger.info(f"V Environment creado exitosamente")
        logger.info(f"  - Central agent: {base_env.central_agent}")
        logger.info(f"  - Num buildings: {len(base_env.buildings)}")
        logger.info(f"  - Timesteps: {base_env.time_steps}")
    except Exception as e:
        logger.error(f"X Error creando environment: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 3. APLICAR WRAPPER
    logger.info("\n[PASO 3] APLICANDO FLAT ACTION WRAPPER")
    try:
        env = FlatActionWrapper(base_env)
        logger.info(f"V Wrapper aplicado exitosamente")
    except Exception as e:
        logger.error(f"X Error aplicando wrapper: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 4. SETUP CHECKPOINTS
    logger.info("\n[PASO 4] SETUP DE CHECKPOINTS")
    ckpt_dir = Path("analyses/oe3/training/checkpoints/a2c")
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"V Checkpoint dir: {ckpt_dir}")
    
    # 5. BUSCAR CHECKPOINT PREVIO
    logger.info("\n[PASO 5] BUSCANDO CHECKPOINTS PREVIOS")
    latest_checkpoint = None
    latest_step = 0
    
    checkpoint_files = list(ckpt_dir.glob("a2c_model_*_steps.zip"))
    if checkpoint_files:
        for f in checkpoint_files:
            try:
                step_num = int(f.name.split("_")[2])
                if step_num > latest_step:
                    latest_step = step_num
                    latest_checkpoint = f
            except:
                pass
        
        if latest_checkpoint:
            logger.info(f"V Checkpoint previo encontrado: {latest_checkpoint.name}")
            logger.info(f"  - Pasos ya entrenados: {latest_step}")
    else:
        logger.info("X No hay checkpoints previos - Iniciando desde cero")
    
    # 6. CREAR/CARGAR MODELO
    logger.info("\n[PASO 6] SETUP DEL MODELO A2C")
    logger.info("\nHIPERPARAMETROS:")
    logger.info("  - Algoritmo: A2C (Actor-Critic)")
    logger.info("  - Policy: MlpPolicy (Multi-layer Perceptron)")
    logger.info("  - Learning rate: 1e-3")
    logger.info("  - N steps: 2048 (rollout buffer size)")
    logger.info("  - Gamma: 0.99 (discount factor)")
    logger.info("  - Gae lambda: 0.95 (advantage estimation)")
    logger.info("  - Entropy coef: 0.001")
    logger.info("  - VF coef: 0.5")
    logger.info("  - Max grad norm: 0.5")
    logger.info("  - Device: CPU")
    
    if latest_checkpoint:
        logger.info(f"\nCargando modelo desde checkpoint: {latest_checkpoint.name}")
        model = A2C.load(str(latest_checkpoint), env=env)
        reset_num_timesteps = False
        logger.info("V Modelo cargado - Continuando entrenamiento acumulable")
    else:
        logger.info("\nCreando modelo nuevo A2C")
        model = A2C(
            "MlpPolicy",
            env,
            learning_rate=1e-3,
            n_steps=2048,
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=0.001,
            vf_coef=0.5,
            max_grad_norm=0.5,
            device="cpu",
            seed=42,
            verbose=0,
        )
        reset_num_timesteps = True
        logger.info("V Modelo A2C creado")
    
    # 7. CALLBACKS
    logger.info("\n[PASO 7] SETUP DE CALLBACKS")
    checkpoint_callback = CheckpointCallback(
        save_freq=2048,
        save_path=str(ckpt_dir),
        name_prefix="a2c_model",
        save_replay_buffer=False,
        save_vecnormalize=False,
    )
    metrics_callback = MetricsCallback()
    logger.info("V CheckpointCallback: cada 2048 timesteps")
    logger.info("V MetricsCallback: logging cada 100 steps")
    
    # 8. ENTRENAMIENTO
    logger.info("\n" + "="*100)
    logger.info("[PASO 8] INICIANDO ENTRENAMIENTO")
    logger.info("="*100)
    logger.info(f"\nConfiguracion:")
    logger.info(f"  - Timesteps totales: 17,520")
    logger.info(f"  - Reset num timesteps: {reset_num_timesteps}")
    logger.info(f"  - Checkpoints cada: 2,048 timesteps")
    logger.info(f"  - Log interval: 50 pasos\n")
    
    try:
        model.learn(
            total_timesteps=17520,
            reset_num_timesteps=reset_num_timesteps,
            callback=[checkpoint_callback, metrics_callback],
            log_interval=50,
            progress_bar=False,
        )
        
        logger.info("\n" + "="*100)
        logger.info("[RESULTADO] A2C TRAINING COMPLETADO EXITOSAMENTE")
        logger.info("="*100)
        
        # Guardar modelo final
        final_path = ckpt_dir / "a2c_final"
        model.save(str(final_path))
        logger.info(f"\nV Modelo final guardado: {final_path}.zip")
        
        # Estadisticas finales
        logger.info(f"\nESTADISTICAS FINALES:")
        logger.info(f"  - Timesteps completados: {model.num_timesteps}")
        logger.info(f"  - Actualizaciones de policy: {model.num_timesteps // 2048}")
        
    except KeyboardInterrupt:
        logger.warning("\nX Entrenamiento interrumpido por usuario")
        logger.info("V Checkpoint actual guardado")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nX Error durante entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("\nCerrando environment...")
        env.close()
        logger.info("V Environment cerrado")


if __name__ == "__main__":
    main()
