from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import numpy as np

@dataclass
class PPOConfig:
    train_steps: int = 50000

def train_ppo(env, cfg: PPOConfig, seed: int = 42):
    """Entrena PPO (SB3) sobre CityLearn. 
    Nota: depende de compatibilidad gymnasium de CityLearn. Si falla, usa RBC.
    """
    import gymnasium as gym
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env

    # CityLearn ya suele cumplir API gymnasium; vectorizamos 1 env
    def _make():
        env.reset(seed=seed)
        return env

    # SB3 espera env que retorne obs np.ndarray; CityLearn puede devolver list/dict.
    # Convertimos a Box con FlattenObservation wrapper si es necesario.
    class ObsWrapper(gym.Wrapper):
        def reset(self, **kwargs):
            obs, info = self.env.reset(**kwargs)
            return self._flat(obs), info
        def step(self, action):
            obs, reward, terminated, truncated, info = self.env.step(action)
            return self._flat(obs), reward, terminated, truncated, info
        def _flat(self, obs):
            if isinstance(obs, dict):
                arr = np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
            elif isinstance(obs, (list, tuple)):
                arr = np.array(obs, dtype=np.float32).ravel()
            else:
                arr = np.array(obs, dtype=np.float32).ravel()
            return arr

    wrapped = ObsWrapper(env)

    vec_env = make_vec_env(lambda: wrapped, n_envs=1, seed=seed)
    model = PPO("MlpPolicy", vec_env, verbose=0, seed=seed)
    model.learn(total_timesteps=int(cfg.train_steps))
    return model, wrapped

def ppo_predict(model, obs):
    action, _ = model.predict(obs, deterministic=True)
    return action
