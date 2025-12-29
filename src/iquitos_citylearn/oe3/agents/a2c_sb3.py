from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List, Callable
import numpy as np
import logging

from ..progress import append_progress_row

logger = logging.getLogger(__name__)


def _progress_pct(current: int, total: int) -> Optional[float]:
    """Calcula porcentaje de avance, None si no aplica."""
    if total is None or total <= 0:
        return None
    try:
        return round(100.0 * float(current) / float(total), 1)
    except Exception:
        return None


def detect_device() -> str:
    """Auto-detecta el mejor dispositivo disponible (CUDA/MPS/CPU)."""
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            logger.info("GPU CUDA detectada: %s", device_name)
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("GPU MPS (Apple Silicon) detectada")
            return "mps"
    except ImportError:
        pass
    logger.info("Usando CPU para entrenamiento")
    return "cpu"


@dataclass
class A2CConfig:
    """Configuración para A2C (SB3) con soporte CUDA/GPU."""
    train_steps: int = 100000
    n_steps: int = 256
    learning_rate: float = 3e-4
    lr_schedule: str = "constant"
    gamma: float = 0.99
    gae_lambda: float = 1.0
    ent_coef: float = 0.01
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    hidden_sizes: tuple = (256, 256)
    activation: str = "tanh"
    device: str = "auto"
    seed: int = 42
    verbose: int = 0
    log_interval: int = 1000
    checkpoint_dir: Optional[str] = None
    checkpoint_freq_steps: int = 0
    save_final: bool = True
    progress_path: Optional[str] = None
    progress_interval_episodes: int = 1


class A2CAgent:
    """Agente A2C robusto usando Stable-Baselines3."""

    def __init__(self, env: Any, config: Optional[A2CConfig] = None):
        self.env = env
        self.config = config or A2CConfig()
        self.model = None
        self.wrapped_env = None
        self._trained = False
        self.training_history: List[Dict[str, float]] = []
        self.device = self._setup_device()

    def _setup_device(self) -> str:
        if self.config.device == "auto":
            return detect_device()
        return self.config.device

    def learn(self, episodes: int = 5, total_timesteps: Optional[int] = None):
        try:
            import gymnasium as gym
            from stable_baselines3 import A2C
            from stable_baselines3.common.env_util import make_vec_env
            from stable_baselines3.common.callbacks import BaseCallback, CallbackList
            from stable_baselines3.common.monitor import Monitor
        except ImportError as e:
            logger.warning("stable_baselines3 no disponible: %s", e)
            return

        steps = total_timesteps or self.config.train_steps

        class CityLearnWrapper(gym.Wrapper):
            def __init__(self, env):
                super().__init__(env)
                self._obs_dim = self._get_obs_dim()
                self._act_dim = self._get_act_dim()

                self.observation_space = gym.spaces.Box(
                    low=-np.inf, high=np.inf, shape=(self._obs_dim,), dtype=np.float32
                )
                self.action_space = gym.spaces.Box(
                    low=-1.0, high=1.0, shape=(self._act_dim,), dtype=np.float32
                )

            def _get_obs_dim(self):
                obs, _ = self.env.reset()
                return len(self._flatten(obs))

            def _get_act_dim(self):
                if isinstance(self.env.action_space, list):
                    return sum(sp.shape[0] for sp in self.env.action_space)
                return self.env.action_space.shape[0]

            def _flatten(self, obs):
                if isinstance(obs, dict):
                    return np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
                if isinstance(obs, (list, tuple)):
                    return np.concatenate([np.array(o, dtype=np.float32).ravel() for o in obs])
                return np.array(obs, dtype=np.float32).ravel()

            def _unflatten_action(self, action):
                if isinstance(self.env.action_space, list):
                    result = []
                    idx = 0
                    for sp in self.env.action_space:
                        dim = sp.shape[0]
                        result.append(action[idx:idx + dim].tolist())
                        idx += dim
                    return result
                return [action.tolist()]

            def reset(self, **kwargs):
                obs, info = self.env.reset(**kwargs)
                return self._flatten(obs), info

            def step(self, action):
                citylearn_action = self._unflatten_action(action)
                obs, reward, terminated, truncated, info = self.env.step(citylearn_action)

                if truncated and not terminated:
                    terminated = True
                    truncated = False

                if isinstance(reward, (list, tuple)):
                    reward = sum(reward)

                return self._flatten(obs), float(reward), terminated, truncated, info

        self.wrapped_env = Monitor(CityLearnWrapper(self.env))
        vec_env = make_vec_env(lambda: self.wrapped_env, n_envs=1, seed=self.config.seed)

        lr_schedule = self._get_lr_schedule(steps)
        policy_kwargs = {
            "net_arch": list(self.config.hidden_sizes),
            "activation_fn": self._get_activation(),
        }

        logger.info("Creando modelo A2C en dispositivo: %s", self.device)
        self.model = A2C(
            "MlpPolicy",
            vec_env,
            learning_rate=lr_schedule,
            n_steps=int(self.config.n_steps),
            gamma=self.config.gamma,
            gae_lambda=self.config.gae_lambda,
            ent_coef=self.config.ent_coef,
            vf_coef=self.config.vf_coef,
            max_grad_norm=self.config.max_grad_norm,
            policy_kwargs=policy_kwargs,
            verbose=self.config.verbose,
            seed=self.config.seed,
            device=self.device,
        )

        progress_path = Path(self.config.progress_path) if self.config.progress_path else None
        if progress_path is not None and progress_path.exists():
            progress_path.unlink()
        progress_headers = (
            "timestamp",
            "agent",
            "episode",
            "episode_reward",
            "episode_length",
            "global_step",
            "progress_pct",
        )
        expected_episodes = int(steps // 8760) if steps > 0 else 0

        class TrainingCallback(BaseCallback):
            def __init__(self, agent, progress_path: Optional[Path], progress_headers, expected_episodes: int, verbose=0):
                super().__init__(verbose)
                self.agent = agent
                self.progress_path = progress_path
                self.progress_headers = progress_headers
                self.expected_episodes = expected_episodes
                self.episode_count = 0
                self.log_interval_steps = int(agent.config.log_interval or 0)

            def _on_step(self):
                infos = self.locals.get("infos", [])
                if isinstance(infos, dict):
                    infos = [infos]
                if not infos:
                    return True
                if self.log_interval_steps > 0 and self.n_calls % self.log_interval_steps == 0:
                    approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
                    pct = _progress_pct(approx_episode, self.expected_episodes)
                    pct_str = f" ({pct:.1f}%)" if pct is not None else ""
                    logger.info(
                        "[A2C] paso %d | ep~%d%s | pasos_global=%d",
                        self.n_calls,
                        approx_episode,
                        pct_str,
                        int(self.model.num_timesteps),
                    )
                    if self.progress_path is not None:
                        row = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": "a2c",
                            "episode": approx_episode,
                            "episode_reward": "",
                            "episode_length": "",
                            "global_step": int(self.model.num_timesteps),
                            "progress_pct": pct,
                        }
                        append_progress_row(self.progress_path, row, self.progress_headers)
                for info in infos:
                    episode = info.get("episode")
                    if not episode:
                        continue
                    self.episode_count += 1
                    reward = float(episode.get("r", 0.0))
                    length = int(episode.get("l", 0))
                    self.agent.training_history.append({
                        "step": int(self.model.num_timesteps),
                        "mean_reward": reward,
                    })
                    if self.agent.config.progress_interval_episodes > 0 and (
                        self.episode_count % self.agent.config.progress_interval_episodes == 0
                    ):
                        pct = _progress_pct(self.episode_count, self.expected_episodes)
                        row = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": "a2c",
                            "episode": self.episode_count,
                            "episode_reward": reward,
                            "episode_length": length,
                            "global_step": int(self.model.num_timesteps),
                            "progress_pct": pct,
                        }
                        if self.progress_path is not None:
                            append_progress_row(self.progress_path, row, self.progress_headers)
                        if self.expected_episodes > 0:
                            logger.info(
                                "[A2C] ep %d/%d (%.1f%%) reward=%.4f len=%d step=%d",
                                self.episode_count,
                                self.expected_episodes,
                                pct if pct is not None else 0.0,
                                reward,
                                length,
                                int(self.model.num_timesteps),
                            )
                        else:
                            logger.info(
                                "[A2C] ep %d reward=%.4f len=%d step=%d",
                                self.episode_count,
                                reward,
                                length,
                                int(self.model.num_timesteps),
                            )
                return True

        checkpoint_dir = self.config.checkpoint_dir
        checkpoint_freq = int(self.config.checkpoint_freq_steps or 0)
        if checkpoint_dir:
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)

        class CheckpointCallback(BaseCallback):
            def __init__(self, save_dir: Optional[str], freq: int, verbose=0):
                super().__init__(verbose)
                self.save_dir = Path(save_dir) if save_dir else None
                self.freq = freq

            def _on_step(self):
                if self.save_dir is None or self.freq <= 0:
                    return True
                if self.n_calls % self.freq == 0:
                    save_path = self.save_dir / f"a2c_step_{self.n_calls}"
                    try:
                        self.model.save(save_path)
                        logger.info("Checkpoint A2C guardado en %s", save_path)
                    except Exception as exc:
                        logger.warning("No se pudo guardar checkpoint A2C (%s)", exc)
                return True

        callback = CallbackList([
            TrainingCallback(self, progress_path, progress_headers, expected_episodes),
            CheckpointCallback(checkpoint_dir, checkpoint_freq),
        ])

        self.model.learn(total_timesteps=int(steps), callback=callback)
        self._trained = True
        logger.info("A2C entrenado con %d timesteps", steps)

        if self.model is not None and checkpoint_dir and self.config.save_final:
            final_path = Path(checkpoint_dir) / "a2c_final"
            try:
                self.model.save(final_path)
                logger.info("Modelo A2C guardado en %s", final_path)
            except Exception as exc:
                logger.warning("No se pudo guardar modelo A2C (%s)", exc)

    def _get_lr_schedule(self, total_steps: int) -> Callable:
        from stable_baselines3.common.utils import get_linear_fn

        if self.config.lr_schedule == "linear":
            return get_linear_fn(self.config.learning_rate, self.config.learning_rate * 0.1, 1.0)
        if self.config.lr_schedule == "cosine":
            def cosine_schedule(progress):
                return self.config.learning_rate * (0.5 * (1 + np.cos(np.pi * (1 - progress))))
            return cosine_schedule
        return self.config.learning_rate

    def _get_activation(self):
        import torch.nn as nn
        activations = {
            "relu": nn.ReLU,
            "tanh": nn.Tanh,
            "elu": nn.ELU,
            "leaky_relu": nn.LeakyReLU,
            "gelu": nn.GELU,
            "silu": nn.SiLU,
        }
        return activations.get(self.config.activation, nn.Tanh)

    def predict(self, observations: Any, deterministic: bool = True):
        if self.model is None:
            return self._zero_action()

        obs = self._flatten_obs(observations)
        action, _ = self.model.predict(obs, deterministic=deterministic)
        return self._unflatten_action(action)

    def _flatten_obs(self, obs):
        if isinstance(obs, dict):
            return np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
        if isinstance(obs, (list, tuple)):
            return np.concatenate([np.array(o, dtype=np.float32).ravel() for o in obs])
        return np.array(obs, dtype=np.float32).ravel()

    def _unflatten_action(self, action):
        if isinstance(self.env.action_space, list):
            result = []
            idx = 0
            for sp in self.env.action_space:
                dim = sp.shape[0]
                result.append(action[idx:idx + dim].tolist())
                idx += dim
            return result
        if isinstance(action, np.ndarray):
            return [action.tolist()]
        return [action]

    def _zero_action(self):
        action_space = getattr(self.env, "action_space", None)
        if action_space is None:
            return [[0.0]]
        if isinstance(action_space, list):
            return [[0.0] * sp.shape[0] for sp in action_space]
        return [[0.0] * action_space.shape[0]]

    def save(self, path: str):
        if self.model is not None:
            self.model.save(path)
            logger.info("Modelo A2C guardado en %s", path)

    def load(self, path: str):
        from stable_baselines3 import A2C
        self.model = A2C.load(path)
        self._trained = True
        logger.info("Modelo A2C cargado desde %s", path)


def make_a2c(env: Any, config: Optional[A2CConfig] = None, **kwargs) -> A2CAgent:
    cfg = config or A2CConfig(**kwargs) if kwargs else A2CConfig()
    return A2CAgent(env, cfg)
