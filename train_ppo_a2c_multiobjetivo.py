#!/usr/bin/env python3
"""
ENTRENAR PPO Y A2C - CON MULTIOBJETIVO REAL - OPTIMIZADO GPU
v2.0 - Auto-detecta GPU, configuración óptima según hardware disponible
"""

import sys
import os
from pathlib import Path
import json
import yaml
from datetime import datetime
import logging
import warnings
import numpy as np
import torch
from typing import Any

warnings.filterwarnings('ignore', category=DeprecationWarning)

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.WARNING)

# AUTO-DETECTAR GPU
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
if DEVICE == 'cuda':
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    # Configuración óptima para GPU
    PPO_N_STEPS = 4096  # Más steps grandes en GPU
    PPO_BATCH_SIZE = 256
    PPO_NETWORK = [512, 512]
    A2C_BATCH_SIZE = 128
    A2C_NETWORK = [256, 256]
else:
    # Configuración conservadora para CPU
    PPO_N_STEPS = 2048
    PPO_BATCH_SIZE = 128
    PPO_NETWORK = [256, 256]
    A2C_BATCH_SIZE = 64
    A2C_NETWORK = [128, 128]

# ============================================================================
# ENTRENAR PPO
# ============================================================================

def train_ppo():
    print('='*80)
    print('ENTRENAR PPO - MULTIOBJETIVO REAL')
    print('='*80)
    print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    CHECKPOINT_DIR = Path('checkpoints/PPO')
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    OUTPUT_DIR = Path('outputs/ppo_training')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from src.rewards.rewards import IquitosContext, create_iquitos_reward_weights, MultiObjectiveReward
        from gymnasium import Env, spaces
        from stable_baselines3 import PPO
        from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback

        print('[1] CARGAR CONTEXTO MULTIOBJETIVO')
        print('-' * 80)

        weights = create_iquitos_reward_weights("co2_focus")
        context = IquitosContext()
        reward_calc = MultiObjectiveReward(weights=weights, context=context)

        print(f'  ✓ CO₂ grid: {context.co2_factor_kg_per_kwh} kg CO₂/kWh')
        print(f'  ✓ Pesos: CO₂={weights.co2:.2f}, Solar={weights.solar:.2f}, Cost={weights.cost:.2f}')
        print()

        print('[2] CREAR ENVIRONMENT')
        print('-' * 80)

        class CityLearnEnv(Env):
            def __init__(self, reward_calc, context, obs_dim=394, action_dim=129, max_steps=8760):
                self.reward_calculator = reward_calc
                self.context = context
                self.obs_dim = obs_dim
                self.action_dim = action_dim
                self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)
                self.action_space = spaces.Box(low=0.0, high=1.0, shape=(action_dim,), dtype=np.float32)
                self.step_count = 0
                self.episode_reward = 0.0
                self.episode_num = 0
                self.max_steps = max_steps

            def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
                super().reset(seed=seed)
                self.step_count = 0
                self.episode_reward = 0.0
                self.episode_num += 1
                obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
                return obs, {}

            def step(self, action):
                self.step_count += 1
                hour = (self.step_count - 1) % 24

                # Dispatch
                bess_setpoint = action[0]
                charger_setpoints = action[1:129]

                # Sintetizar energías
                motos_power_kw = np.sum(charger_setpoints[:112]) * 2.0 / 112 * 20
                mototaxis_power_kw = np.sum(charger_setpoints[112:]) * 3.0 / 16 * 20
                ev_charging_kwh = (motos_power_kw + mototaxis_power_kw) / 3600

                # Solar (patrón ecuatorial)
                if 6 <= hour <= 18:
                    solar_generation_kwh = 3500 * np.sin(np.pi * (hour - 6) / 12) * 0.8 / 3600
                else:
                    solar_generation_kwh = 0.0

                # Mall
                if 9 <= hour <= 22:
                    mall_load_kw = 200 + 100 * np.sin(np.pi * (hour - 9) / 13)
                else:
                    mall_load_kw = 100

                # Grid
                total_load_kwh = (mall_load_kw + motos_power_kw + mototaxis_power_kw) / 3600
                if solar_generation_kwh >= total_load_kwh:
                    grid_import_kwh = 0.0
                else:
                    grid_import_kwh = total_load_kwh - solar_generation_kwh
                grid_export_kwh = max(0, solar_generation_kwh - total_load_kwh)

                # SOC
                ev_soc_avg = min(1.0, 0.3 + np.sum(charger_setpoints) / 128 * 0.6)
                bess_soc = min(0.95, max(0.1, 0.5 + bess_setpoint * 0.3))

                # REWARD MULTIOBJETIVO
                reward, _ = self.reward_calculator.compute(
                    grid_import_kwh=grid_import_kwh,
                    grid_export_kwh=grid_export_kwh,
                    solar_generation_kwh=solar_generation_kwh,
                    ev_charging_kwh=ev_charging_kwh,
                    ev_soc_avg=ev_soc_avg,
                    bess_soc=bess_soc,
                    hour=hour
                )

                self.episode_reward += reward
                obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
                terminated = self.step_count >= self.max_steps
                truncated = False
                info = {'step': self.step_count, 'hour': hour}

                return obs, reward, terminated, truncated, info

        env = CityLearnEnv(reward_calc, context)
        print('  ✓ Environment creado')
        print()

        print('[3] ENTRENAR PPO - CONFIGURACIÓN ÓPTIMA')
        print('-' * 80)

        ppo_config = {
            'learning_rate': 2e-4,  # OPCIÓN A: Reducido 33% (3e-4 → 2e-4) para GPU batch_size=256
            'n_steps': PPO_N_STEPS,  # Dinámico según GPU/CPU
            'batch_size': PPO_BATCH_SIZE,  # Dinámico según GPU/CPU
            'n_epochs': 10,
            'gamma': 0.99,
            'gae_lambda': 0.95,
            'clip_range': 0.2,
            'ent_coef': 0.0,
            'vf_coef': 0.5,
            'max_grad_norm': 0.5,
            'policy_kwargs': {'net_arch': PPO_NETWORK},  # Dinámico según GPU/CPU
            'device': DEVICE,  # Usar GPU si disponible
            'verbose': 0,
            'tensorboard_log': None  # Desabilitar tensorboard
        }

        agent = PPO('MlpPolicy', env, **ppo_config)

        print(f'  ✓ PPO agent creado (DEVICE: {DEVICE.upper()})')
        print(f'    - n_steps: {PPO_N_STEPS}')
        print(f'    - batch_size: {PPO_BATCH_SIZE}')
        print(f'    - Network: {PPO_NETWORK}')
        print()
        print('  Entrenando PPO (100k timesteps)...')

        class LogCallback(BaseCallback):
            def _on_step(self) -> bool:
                if self.num_timesteps % 10000 == 0:
                    print(f'    Steps: {self.num_timesteps:,}')
                return True

        agent.learn(
            total_timesteps=100000,
            callback=[LogCallback()],
            progress_bar=False
        )

        # Guardar
        final_model_path = CHECKPOINT_DIR / 'ppo_final_model'
        agent.save(str(final_model_path))

        print(f'  ✓ Modelo PPO guardado: {final_model_path}.zip')
        print()

        # Validación
        val_rewards = []
        for ep in range(3):
            obs, _ = env.reset()
            done = False
            while not done:
                action, _ = agent.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
            val_rewards.append(env.episode_reward)

        # Guardar métricas
        metrics = {
            'agent': 'PPO',
            'validation_mean_reward': float(np.mean(val_rewards)),
            'validation_std_reward': float(np.std(val_rewards)),
            'timestamp': datetime.now().isoformat()
        }

        with open(OUTPUT_DIR / 'ppo_training_metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)

        print(f'  ✓ Validación: reward={float(np.mean(val_rewards)):.4f}')
        print()

        env.close()
        return True

    except Exception as e:
        print(f'[ERROR] {e}')
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# ENTRENAR A2C
# ============================================================================

def train_a2c():
    print()
    print('='*80)
    print('ENTRENAR A2C - MULTIOBJETIVO REAL')
    print('='*80)
    print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    CHECKPOINT_DIR = Path('checkpoints/A2C')
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    OUTPUT_DIR = Path('outputs/a2c_training')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from src.rewards.rewards import IquitosContext, create_iquitos_reward_weights, MultiObjectiveReward
        from gymnasium import Env, spaces
        from stable_baselines3 import A2C
        from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback

        print('[1] CARGAR CONTEXTO MULTIOBJETIVO')
        print('-' * 80)

        weights = create_iquitos_reward_weights("co2_focus")
        context = IquitosContext()
        reward_calc = MultiObjectiveReward(weights=weights, context=context)

        print(f'  ✓ A2C simple on-policy (actualización cada 5 steps)')
        print()

        print('[2] CREAR ENVIRONMENT')
        print('-' * 80)

        class CityLearnEnv(Env):
            def __init__(self, reward_calc, context, obs_dim=394, action_dim=129, max_steps=8760):
                self.reward_calculator = reward_calc
                self.context = context
                self.obs_dim = obs_dim
                self.action_dim = action_dim
                self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)
                self.action_space = spaces.Box(low=0.0, high=1.0, shape=(action_dim,), dtype=np.float32)
                self.step_count = 0
                self.episode_reward = 0.0
                self.episode_num = 0
                self.max_steps = max_steps

            def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
                super().reset(seed=seed)
                self.step_count = 0
                self.episode_reward = 0.0
                self.episode_num += 1
                obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
                return obs, {}

            def step(self, action):
                self.step_count += 1
                hour = (self.step_count - 1) % 24

                motos_power_kw = np.sum(action[1:113]) * 2.0 / 112 * 20
                mototaxis_power_kw = np.sum(action[113:129]) * 3.0 / 16 * 20
                ev_charging_kwh = (motos_power_kw + mototaxis_power_kw) / 3600

                if 6 <= hour <= 18:
                    solar_generation_kwh = 3500 * np.sin(np.pi * (hour - 6) / 12) * 0.8 / 3600
                else:
                    solar_generation_kwh = 0.0

                if 9 <= hour <= 22:
                    mall_load_kw = 200 + 100 * np.sin(np.pi * (hour - 9) / 13)
                else:
                    mall_load_kw = 100

                total_load_kwh = (mall_load_kw + motos_power_kw + mototaxis_power_kw) / 3600
                grid_import_kwh = max(0, total_load_kwh - solar_generation_kwh)
                grid_export_kwh = max(0, solar_generation_kwh - total_load_kwh)

                ev_soc_avg = min(1.0, 0.3 + np.sum(action[1:129]) / 128 * 0.6)
                bess_soc = min(0.95, max(0.1, 0.5 + action[0] * 0.3))

                reward, _ = self.reward_calculator.compute(
                    grid_import_kwh=grid_import_kwh,
                    grid_export_kwh=grid_export_kwh,
                    solar_generation_kwh=solar_generation_kwh,
                    ev_charging_kwh=ev_charging_kwh,
                    ev_soc_avg=ev_soc_avg,
                    bess_soc=bess_soc,
                    hour=hour
                )

                self.episode_reward += reward
                obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
                terminated = self.step_count >= self.max_steps
                truncated = False
                info = {'step': self.step_count}

                return obs, reward, terminated, truncated, info

        env = CityLearnEnv(reward_calc, context)
        print('  ✓ Environment creado')
        print()

        print('[3] ENTRENAR A2C - CONFIGURACIÓN ÓPTIMA')
        print('-' * 80)

        agent = A2C(
            'MlpPolicy',
            env,
            learning_rate=5e-4,  # OPCIÓN A: Reducido 28% (7e-4 → 5e-4) para GPU n_steps=5
            n_steps=5,
            gamma=0.99,
            vf_coef=0.5,
            ent_coef=0.0,
            max_grad_norm=0.5,
            policy_kwargs={'net_arch': A2C_NETWORK},  # Dinámico según GPU/CPU
            device=DEVICE,  # Usar GPU si disponible
            verbose=0,
            tensorboard_log=None  # Desabilitar tensorboard
        )

        print(f'  ✓ A2C agent creado (DEVICE: {DEVICE.upper()})')
        print(f'    - Network: {A2C_NETWORK}')
        print(f'    - n_steps: 5 (actualización frecuente)')
        print()
        print('  Entrenando A2C (100k timesteps)...')

        class LogCallback(BaseCallback):
            def _on_step(self) -> bool:
                if self.num_timesteps % 10000 == 0:
                    print(f'    Steps: {self.num_timesteps:,}')
                return True

        agent.learn(
            total_timesteps=100000,
            callback=[LogCallback()],
            progress_bar=False
        )

        # Guardar
        final_model_path = CHECKPOINT_DIR / 'a2c_final_model'
        agent.save(str(final_model_path))

        print(f'  ✓ Modelo A2C guardado: {final_model_path}.zip')
        print()

        # Validación
        val_rewards = []
        for ep in range(3):
            obs, _ = env.reset()
            done = False
            while not done:
                action, _ = agent.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
            val_rewards.append(env.episode_reward)

        # Guardar métricas
        metrics = {
            'agent': 'A2C',
            'validation_mean_reward': float(np.mean(val_rewards)),
            'validation_std_reward': float(np.std(val_rewards)),
            'timestamp': datetime.now().isoformat()
        }

        with open(OUTPUT_DIR / 'a2c_training_metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)

        print(f'  ✓ Validación: reward={float(np.mean(val_rewards)):.4f}')
        print()

        env.close()
        return True

    except Exception as e:
        print(f'[ERROR] {e}')
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    success_ppo = train_ppo()
    success_a2c = train_a2c()

    print('='*80)
    print('RESUMEN FINAL')
    print('='*80)
    print()
    print(f'PPO: {"✓ SUCCESS" if success_ppo else "✗ FAILED"}')
    print(f'A2C: {"✓ SUCCESS" if success_a2c else "✗ FAILED"}')
    print()
