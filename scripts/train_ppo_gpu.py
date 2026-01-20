#!/usr/bin/env python
"""
PPO TRAINING - GPU OPTIMIZED VERSION
MALL IQUITOS CON PLAYAS DE CARGA (128 TOMAS)
"""
import sys
from pathlib import Path
import logging
import numpy as np
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
import torch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("analyses/logs/ppo_gpu.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))
from citylearn.citylearn import CityLearnEnv

# SCHEMA CONFIGURATION
SCHEMA_PATH = "data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json"


class MetricsCallback(BaseCallback):
    """Callback para registrar métricas durante entrenamiento"""
    def __init__(self):
        super().__init__()
    
    def _on_step(self) -> bool:
        if self.num_timesteps % 100 == 0:
            logger.info(f"Step {self.num_timesteps}/17520 | GPU util: {torch.cuda.utilization():.1f}%")
        return True


class FlatActionWrapper(gym.Wrapper):
    """Flatten action y observation para Gymnasium compatibility."""
    def __init__(self, env):
        super().__init__(env)
        
        if isinstance(self.env.action_space, list):
            self.agent_action_spaces = self.env.action_space
            self.total_action_size = sum(space.shape[0] for space in self.agent_action_spaces)
        else:
            raise ValueError("Unexpected action_space type")
        
        obs, _ = env.reset()
        obs_flat = self._flatten_obs(obs)
        
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
    
    def _flatten_obs(self, obs):
        if isinstance(obs, list):
            def flatten_recursive(x):
                if isinstance(x, (list, tuple)):
                    result = []
                    for item in x:
                        result.extend(flatten_recursive(item))
                    return result
                else:
                    return [x]
            return np.array(flatten_recursive(obs), dtype=np.float32)
        else:
            return np.array(obs, dtype=np.float32).flatten()
    
    def _unflatten_action(self, flat_action):
        actions = []
        idx = 0
        for space in self.agent_action_spaces:
            dim = space.shape[0]
            actions.append(flat_action[idx:idx+dim])
            idx += dim
        return actions
    
    def step(self, action):
        unflat_action = self._unflatten_action(action)
        obs, reward, terminated, truncated, info = self.env.step(unflat_action)
        obs_flat = self._flatten_obs(obs)
        return obs_flat, reward, terminated, truncated, info
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        obs_flat = self._flatten_obs(obs)
        return obs_flat, info


def main():
    logger.info("="*100)
    logger.info("PPO TRAINING - GPU OPTIMIZED VERSION")
    logger.info("MALL IQUITOS (128 TOMAS EV: 16 MOTOTAXIS + 112 MOTOS)")
    logger.info("="*100)
    
    # Verificar GPU
    logger.info(f"\n[GPU STATUS]")
    logger.info(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"CUDA Device: {torch.cuda.get_device_name(0)}")
        torch_version = torch.__dict__.get("version")
        cuda_version = getattr(torch_version, "cuda", None) if torch_version is not None else None
        logger.info(f"CUDA Version: {cuda_version or 'unknown'}")
        logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        device = "cuda"
    else:
        logger.warning("GPU no disponible - usando CPU")
        device = "cpu"
    
    # 1. VALIDAR SCHEMA
    logger.info(f"\n[PASO 1] VALIDANDO SCHEMA")
    schema_path = Path(SCHEMA_PATH)
    if not schema_path.exists():
        logger.error(f"Schema no encontrado: {schema_path}")
        sys.exit(1)
    logger.info(f"✓ Schema: {schema_path}")
    
    # 2. CREAR ENVIRONMENT
    logger.info(f"\n[PASO 2] CREANDO ENVIRONMENT")
    try:
        base_env = CityLearnEnv(schema=str(schema_path))
        logger.info(f"✓ Edificio: {base_env.buildings[0].name}")
        logger.info(f"✓ Timesteps: {base_env.time_steps}")
        logger.info(f"✓ Central agent: {base_env.central_agent}")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    
    # 3. APLICAR WRAPPER
    logger.info(f"\n[PASO 3] APLICANDO FLAT ACTION WRAPPER")
    env = FlatActionWrapper(base_env)
    logger.info(f"✓ Action space: {env.action_space}")
    logger.info(f"✓ Observation space: {env.observation_space}")
    
    # 4. CHECKPOINTS
    logger.info(f"\n[PASO 4] SETUP DE CHECKPOINTS")
    ckpt_dir = Path("analyses/oe3/training/checkpoints/ppo_gpu")
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✓ Checkpoint dir: {ckpt_dir}")
    
    # 5. BUSCAR CHECKPOINTS PREVIOS
    logger.info(f"\n[PASO 5] BUSCANDO CHECKPOINTS PREVIOS")
    latest_checkpoint = None
    latest_step = 0
    
    checkpoint_files = list(ckpt_dir.glob("ppo_model_*_steps.zip"))
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
        logger.info(f"✓ Checkpoint encontrado: {latest_checkpoint.name}")
        logger.info(f"  Pasos entrenados: {latest_step}")
        model = PPO.load(str(latest_checkpoint), env=env, device=device)
        logger.info(f"✓ Modelo cargado desde checkpoint")
    else:
        logger.info(f"✗ Sin checkpoints - iniciando desde cero")
        model = None
    
    # 6. CREAR MODELO PPO
    logger.info(f"\n[PASO 6] SETUP PPO MODEL - GPU OPTIMIZED")
    
    if model is None:
        model = PPO(
            "MlpPolicy",
            env,
            learning_rate=2.5e-4,
            n_steps=4096,        # Aumentado para GPU
            batch_size=512,
            n_epochs=20,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.005,       # Corregido: ent_coef (no entropy_coef)
            vf_coef=0.5,
            max_grad_norm=0.5,
            device=device,
            verbose=0
        )
        logger.info(f"✓ Modelo PPO creado")
    
    logger.info(f"\nHiperparámetros:")
    logger.info(f"  - Device: {device}")
    logger.info(f"  - Learning rate: 2.5e-4")
    logger.info(f"  - N steps: 4096 (GPU optimized)")
    logger.info(f"  - Batch size: 512")
    logger.info(f"  - N epochs: 20")
    logger.info(f"  - Timesteps totales: 17,520")
    
    # 7. CALLBACKS
    logger.info(f"\n[PASO 7] SETUP CALLBACKS")
    checkpoint_callback = CheckpointCallback(
        save_freq=2048,
        save_path=str(ckpt_dir),
        name_prefix="ppo_model"
    )
    metrics_callback = MetricsCallback()
    logger.info(f"✓ Callbacks configurados")
    
    # 8. TRAINING
    logger.info(f"\n[PASO 8] INICIANDO ENTRENAMIENTO CON GPU")
    logger.info(f"Timesteps a entrenar: 17,520")
    logger.info(f"Estimado: 30-40 minutos en GPU RTX 4060")
    
    try:
        model.learn(
            total_timesteps=17520,
            callback=[checkpoint_callback, metrics_callback],
            reset_num_timesteps=False if latest_checkpoint else True,
            log_interval=1
        )
        logger.info(f"\n✓ ENTRENAMIENTO COMPLETADO")
        
        # Guardar modelo final
        final_path = ckpt_dir / "ppo_final.zip"
        model.save(str(final_path))
        logger.info(f"✓ Modelo final guardado: {final_path}")
        
    except KeyboardInterrupt:
        logger.warning(f"\n⚠ Entrenamiento interrumpido por usuario")
        # Guardar checkpoint actual
        model.save(str(ckpt_dir / "ppo_interrupted.zip"))
    except Exception as e:
        logger.error(f"Error durante training: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info(f"Cerrando environment...")
        env.close()
        logger.info(f"✓ Done")


if __name__ == "__main__":
    main()
