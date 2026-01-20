#!/usr/bin/env python
"""
VERIFICACION: ¿Ha aprendido PPO correctamente?
Comparar política random vs PPO entrenado
"""
import sys
from pathlib import Path
import numpy as np
import gymnasium as gym
from stable_baselines3 import PPO
import logging

sys.path.insert(0, str(Path(__file__).parent))
from citylearn.citylearn import CityLearnEnv

logging.basicConfig(level=logging.WARNING)

SCHEMA_PATH = "data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json"
MODEL_PATH = "analyses/oe3/training/checkpoints/ppo_gpu/ppo_final.zip"

print("="*100)
print("VERIFICACION: ¿HA APRENDIDO PPO?")
print("="*100)

# Wrapper para compatibilidad
class FlatActionWrapper(gym.Wrapper):
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
                    return [float(x)]
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
        if isinstance(reward, (list, np.ndarray)):
            reward = float(np.mean(reward))
        else:
            reward = float(reward)
        return obs_flat, reward, terminated, truncated, info
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        obs_flat = self._flatten_obs(obs)
        return obs_flat, info

print("\n[1] CREAR AMBIENTE")
base_env = CityLearnEnv(schema=str(SCHEMA_PATH))
env = FlatActionWrapper(base_env)
print(f"    ✓ Ambiente: {base_env.buildings[0].name}")
print(f"    ✓ Acciones: {env.action_space.shape}")
print(f"    ✓ Observaciones: {env.observation_space.shape}")

print("\n[2] POLITICA ALEATORIA (Baseline)")
obs, _ = env.reset()
random_rewards = []
for step in range(100):
    action = env.action_space.sample()  # Acción aleatoria
    obs, reward, terminated, truncated, info = env.step(action)
    random_rewards.append(reward)
    if terminated or truncated:
        obs, _ = env.reset()

random_mean = np.mean(random_rewards)
random_std = np.std(random_rewards)
print(f"    Recompensa media: {random_mean:.4f} +/- {random_std:.4f}")
print(f"    Min: {np.min(random_rewards):.4f}")
print(f"    Max: {np.max(random_rewards):.4f}")

print("\n[3] CARGAR MODELO PPO ENTRENADO")
if not Path(MODEL_PATH).exists():
    print(f"    ✗ MODELO NO ENCONTRADO: {MODEL_PATH}")
    sys.exit(1)

model = PPO.load(MODEL_PATH, env=env)
print(f"    ✓ Modelo cargado: {MODEL_PATH}")
print(f"    ✓ Policy: {model.policy_class.__name__}")
print(f"    ✓ Device: {model.device}")

print("\n[4] POLITICA ENTRENADA PPO")
obs, _ = env.reset()
ppo_rewards = []
actions_diversity = []
for step in range(100):
    action, _ = model.predict(obs, deterministic=True)  # Política determinista (sin ruido)
    obs, reward, terminated, truncated, info = env.step(action)
    ppo_rewards.append(reward)
    actions_diversity.append(np.mean(np.abs(action)))
    if terminated or truncated:
        obs, _ = env.reset()

ppo_mean = np.mean(ppo_rewards)
ppo_std = np.std(ppo_rewards)
print(f"    Recompensa media: {ppo_mean:.4f} +/- {ppo_std:.4f}")
print(f"    Min: {np.min(ppo_rewards):.4f}")
print(f"    Max: {np.max(ppo_rewards):.4f}")
print(f"    Promedio acciones: {np.mean(actions_diversity):.4f}")

print("\n[5] COMPARATIVA: RANDOM vs PPO")
improvement = ((ppo_mean - random_mean) / abs(random_mean)) * 100 if random_mean != 0 else 0
print(f"    Baseline (random): {random_mean:.4f}")
print(f"    PPO (entrenado):   {ppo_mean:.4f}")
print(f"    Mejora: {improvement:+.1f}%")

if ppo_mean > random_mean:
    print(f"    ✓ PPO APRENDI CORRECTAMENTE (+{improvement:.1f}%)")
elif ppo_mean < random_mean:
    print(f"    ⚠ PPO EMPEOR (-{abs(improvement):.1f}%)")
else:
    print(f"    ~ PPO SIN CAMBIO")

print("\n[6] VARIABILIDAD DE RECOMPENSAS")
print(f"    Random std: {random_std:.4f}")
print(f"    PPO std:    {ppo_std:.4f}")
if ppo_std < random_std:
    print(f"    ✓ PPO es más consistente (menor variabilidad)")
else:
    print(f"    ⚠ PPO tiene más variabilidad")

print("\n[7] ACCIONES DEL MODELO")
obs, _ = env.reset()
print(f"    Primeros 5 timesteps (acciones PPO):")
for step in range(5):
    action, _ = model.predict(obs, deterministic=True)
    print(f"    Step {step+1}: action range [{action.min():.3f}, {action.max():.3f}], mean={action.mean():.3f}")
    obs, _, terminated, truncated, _ = env.step(action)
    if terminated or truncated:
        break

print("\n" + "="*100)
if ppo_mean > random_mean:
    print("CONCLUSION: PPO APRENDI CORRECTAMENTE")
    print(f"  - Mejora de rendimiento: {improvement:+.1f}%")
    print(f"  - Política convergió a acciones útiles")
    print(f"  - Modelo está listo para evaluación/deployment")
elif improvement > -10:
    print("CONCLUSION: PPO CON LEARNING MARGINAL")
    print(f"  - Cambio: {improvement:+.1f}%")
    print(f"  - Considerar más epochs/timesteps de entrenamiento")
else:
    print("CONCLUSION: PPO NO APRENDI")
    print(f"  - Empeoramiento: {improvement:.1f}%")
    print(f"  - Revisar configuración de entrenamiento")
print("="*100)

env.close()
