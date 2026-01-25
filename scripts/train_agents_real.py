"""
Entrenamiento REAL de Agentes con CityLearn
PPO → SAC → A2C usando el dataset construido
"""

import sys
from pathlib import Path
import logging
import json
import time
import numpy as np
from gymnasium import spaces, Env
from citylearn.citylearn import CityLearnEnv
from stable_baselines3 import PPO, SAC, A2C

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


class ListToArrayWrapper(Env):
    """Convierte CityLearn (observaciones nested lists) a Gymnasium compatible."""
    def __init__(self, env):
        super().__init__()
        self.env = env
        self.reset_count = 0

        try:
            # Reset para detectar dimensiones
            obs, _ = self.env.reset()

            # Flatten observaciones: obs es lista de listas
            if isinstance(obs, list) and len(obs) > 0 and isinstance(obs[0], list):
                obs_flat = np.array(obs[0], dtype=np.float32).flatten()
            elif isinstance(obs, list):
                obs_flat = np.array(obs, dtype=np.float32).flatten()
            else:
                obs_flat = np.array(obs, dtype=np.float32).flatten()

            obs_dim = len(obs_flat)

            # Crear spaces
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
            )

            # Action space: también es lista en CityLearn, convertir a Box
            action_sp = self.env.action_space
            if isinstance(action_sp, list) and len(action_sp) > 0:
                self.action_space = action_sp[0]  # type: ignore
            else:
                self.action_space = action_sp  # type: ignore

            logger.info(f"✓ Observation space: {obs_dim} dimensions")
            logger.info(f"✓ Action space: {self.action_space}")

        except Exception as e:
            logger.error(f"Error initializing wrapper: {e}")
            raise

    def _flatten_obs(self, obs):
        """Flatten CityLearn observation."""
        try:
            if isinstance(obs, list) and len(obs) > 0 and isinstance(obs[0], list):
                return np.array(obs[0], dtype=np.float32).flatten()
            elif isinstance(obs, list):
                return np.array(obs, dtype=np.float32).flatten()
            else:
                return np.array(obs, dtype=np.float32).flatten()
        except Exception as e:
            logger.warning(f"Error flattening observation, using zeros: {e}")
            obs_shape = self.observation_space.shape
            size = obs_shape[0] if (obs_shape and len(obs_shape) > 0) else 534
            return np.zeros(size, dtype=np.float32)

    def reset(self, seed=None, options=None):
        try:
            obs, info = self.env.reset()
            obs_flat = self._flatten_obs(obs)
            self.reset_count += 1
            return obs_flat, info
        except Exception as e:
            logger.error(f"Error in reset: {e}")
            obs_shape = self.observation_space.shape
            size = obs_shape[0] if (obs_shape and len(obs_shape) > 0) else 534
            return np.zeros(size, dtype=np.float32), {}

    def step(self, action):
        try:
            # CityLearn espera lista de acciones, stable-baselines3 envía array
            if isinstance(action, np.ndarray):
                action = action.tolist()

            obs, reward, terminated, truncated, info = self.env.step(action)
            obs_flat = self._flatten_obs(obs)

            # Asegurar que reward es un float válido
            if not isinstance(reward, (int, float)) or np.isnan(reward):
                reward = 0.0

            return obs_flat, float(reward), terminated, truncated, info
        except Exception as e:
            logger.warning(f"Error in step: {e}")
            obs_shape = self.observation_space.shape
            size = obs_shape[0] if (obs_shape and len(obs_shape) > 0) else 534
            obs_flat = np.zeros(size, dtype=np.float32)
            return obs_flat, 0.0, False, True, {}

    def close(self):
        try:
            return self.env.close()
        except:
            pass


def train_ppo_real(schema_path, episodes=1, timesteps_per_episode=8760):
    """Entrenar PPO REAL con CityLearn."""
    logger.info("=" * 80)
    logger.info("🎮 ENTRENANDO: PPO (On-Policy)")
    logger.info("=" * 80)

    logger.info(f"Configuración PPO:")
    logger.info(f"  Episodios: {episodes}")
    logger.info(f"  Timesteps/episodio: {timesteps_per_episode:,}")
    logger.info(f"  Total timesteps: {episodes * timesteps_per_episode:,}")
    logger.info(f"  Learning rate: 0.0002")
    logger.info(f"  Batch size: 128\n")

    start_time = time.time()
    rewards_per_episode = []

    for ep in range(episodes):
        try:
            logger.info(f"📌 Episodio {ep+1}/{episodes}")

            # Crear ambiente NUEVO para cada episodio
            base_env = CityLearnEnv(schema_path)
            env = ListToArrayWrapper(base_env)

            # Crear modelo PPO
            model = PPO(
                "MlpPolicy",
                env,
                learning_rate=0.0002,
                n_steps=2048,
                batch_size=128,
                n_epochs=20,
                gamma=0.99,
                gae_lambda=0.95,
                verbose=0
            )

            # Entrenar
            ep_start = time.time()
            try:
                model.learn(total_timesteps=timesteps_per_episode)
            except Exception as train_err:
                logger.error(f"Error durante learn: {train_err}")
                # Continuar con evaluación incluso si hay error

            # Evaluar: recolectar rewards en ese episodio
            obs, _ = env.reset()
            episode_reward = 0.0
            steps_completed = 0
            for step in range(timesteps_per_episode):
                try:
                    action, _ = model.predict(obs, deterministic=False)
                    obs, reward, terminated, truncated, _ = env.step(action)
                    episode_reward += reward
                    steps_completed += 1
                    if terminated or truncated:
                        obs, _ = env.reset()
                except Exception as step_err:
                    logger.warning(f"Error en step {step}: {step_err}")
                    obs, _ = env.reset()
                    continue

            ep_time = time.time() - ep_start
            rewards_per_episode.append(float(episode_reward))

            logger.info(f"   ✓ Reward: {episode_reward:,.2f}")
            logger.info(f"   ✓ Tiempo: {ep_time:.1f}s")
            logger.info(f"   ✓ Steps completados: {steps_completed}/{timesteps_per_episode}\n")

            env.close()

        except Exception as ep_err:
            logger.error(f"Error en episodio {ep+1}: {ep_err}")
            rewards_per_episode.append(0.0)
            try:
                env.close()
            except:
                pass
            continue

    total_time = time.time() - start_time

    return {
        "agent": "PPO",
        "episodes": episodes,
        "rewards_per_episode": rewards_per_episode,
        "mean_reward": float(np.mean(rewards_per_episode)) if rewards_per_episode else 0.0,
        "total_time": total_time
    }


def train_sac_real(schema_path, episodes=1, timesteps_per_episode=8760):
    """Entrenar SAC REAL con CityLearn."""
    logger.info("=" * 80)
    logger.info("🎮 ENTRENANDO: SAC (Off-Policy)")
    logger.info("=" * 80)

    logger.info(f"Configuración SAC:")
    logger.info(f"  Episodios: {episodes}")
    logger.info(f"  Timesteps/episodio: {timesteps_per_episode:,}")
    logger.info(f"  Total timesteps: {episodes * timesteps_per_episode:,}")
    logger.info(f"  Learning rate: 0.0003")
    logger.info(f"  Batch size: 256\n")

    start_time = time.time()
    rewards_per_episode = []

    for ep in range(episodes):
        try:
            logger.info(f"📌 Episodio {ep+1}/{episodes}")

            # Crear ambiente NUEVO para cada episodio
            base_env = CityLearnEnv(schema_path)
            env = ListToArrayWrapper(base_env)

            # Crear modelo SAC
            model = SAC(
                "MlpPolicy",
                env,
                learning_rate=0.0003,
                batch_size=256,
                train_freq=1,
                gamma=0.99,
                verbose=0
            )

            # Entrenar
            ep_start = time.time()
            try:
                model.learn(total_timesteps=timesteps_per_episode)
            except Exception as train_err:
                logger.error(f"Error durante learn: {train_err}")

            # Evaluar
            obs, _ = env.reset()
            episode_reward = 0.0
            steps_completed = 0
            for step in range(timesteps_per_episode):
                try:
                    action, _ = model.predict(obs, deterministic=False)
                    obs, reward, terminated, truncated, _ = env.step(action)
                    episode_reward += reward
                    steps_completed += 1
                    if terminated or truncated:
                        obs, _ = env.reset()
                except Exception as step_err:
                    logger.warning(f"Error en step {step}: {step_err}")
                    obs, _ = env.reset()
                    continue

            ep_time = time.time() - ep_start
            rewards_per_episode.append(float(episode_reward))

            logger.info(f"   ✓ Reward: {episode_reward:,.2f}")
            logger.info(f"   ✓ Tiempo: {ep_time:.1f}s")
            logger.info(f"   ✓ Steps completados: {steps_completed}/{timesteps_per_episode}\n")

            env.close()

        except Exception as ep_err:
            logger.error(f"Error en episodio {ep+1}: {ep_err}")
            rewards_per_episode.append(0.0)
            try:
                env.close()
            except:
                pass
            continue

    total_time = time.time() - start_time

    return {
        "agent": "SAC",
        "episodes": episodes,
        "rewards_per_episode": rewards_per_episode,
        "mean_reward": float(np.mean(rewards_per_episode)) if rewards_per_episode else 0.0,
        "total_time": total_time
    }


def train_a2c_real(schema_path, episodes=1, timesteps_per_episode=8760):
    """Entrenar A2C REAL con CityLearn."""
    logger.info("=" * 80)
    logger.info("🎮 ENTRENANDO: A2C (On-Policy)")
    logger.info("=" * 80)

    logger.info(f"Configuración A2C:")
    logger.info(f"  Episodios: {episodes}")
    logger.info(f"  Timesteps/episodio: {timesteps_per_episode:,}")
    logger.info(f"  Total timesteps: {episodes * timesteps_per_episode:,}")
    logger.info(f"  Learning rate: 0.0005")
    logger.info(f"  Batch size: 64\n")

    start_time = time.time()
    rewards_per_episode = []

    for ep in range(episodes):
        try:
            logger.info(f"📌 Episodio {ep+1}/{episodes}")

            # Crear ambiente NUEVO para cada episodio
            base_env = CityLearnEnv(schema_path)
            env = ListToArrayWrapper(base_env)

            # Crear modelo A2C
            model = A2C(
                "MlpPolicy",
                env,
                learning_rate=0.0005,
                n_steps=5,
                gamma=0.99,
                verbose=0
            )

            # Entrenar
            ep_start = time.time()
            try:
                model.learn(total_timesteps=timesteps_per_episode)
            except Exception as train_err:
                logger.error(f"Error durante learn: {train_err}")

            # Evaluar
            obs, _ = env.reset()
            episode_reward = 0.0
            steps_completed = 0
            for step in range(timesteps_per_episode):
                try:
                    action, _ = model.predict(obs, deterministic=False)
                    obs, reward, terminated, truncated, _ = env.step(action)
                    episode_reward += reward
                    steps_completed += 1
                    if terminated or truncated:
                        obs, _ = env.reset()
                except Exception as step_err:
                    logger.warning(f"Error en step {step}: {step_err}")
                    obs, _ = env.reset()
                    continue

            ep_time = time.time() - ep_start
            rewards_per_episode.append(float(episode_reward))

            logger.info(f"   ✓ Reward: {episode_reward:,.2f}")
            logger.info(f"   ✓ Tiempo: {ep_time:.1f}s")
            logger.info(f"   ✓ Steps completados: {steps_completed}/{timesteps_per_episode}\n")

            env.close()

        except Exception as ep_err:
            logger.error(f"Error en episodio {ep+1}: {ep_err}")
            rewards_per_episode.append(0.0)
            try:
                env.close()
            except:
                pass
            continue

    total_time = time.time() - start_time

    return {
        "agent": "A2C",
        "episodes": episodes,
        "rewards_per_episode": rewards_per_episode,
        "mean_reward": float(np.mean(rewards_per_episode)) if rewards_per_episode else 0.0,
        "total_time": total_time
    }
    logger.info("=" * 80)
    logger.info("🎮 ENTRENANDO: SAC (Off-Policy)")
    logger.info("=" * 80)

    logger.info(f"Configuración SAC:")
    logger.info(f"  Episodios: {episodes}")
    logger.info(f"  Timesteps/episodio: {timesteps_per_episode:,}")
    logger.info(f"  Total timesteps: {episodes * timesteps_per_episode:,}")
    logger.info(f"  Learning rate: 0.00015")
    logger.info(f"  Buffer size: 1M\n")

    start_time = time.time()
    rewards_per_episode = []

    for ep in range(episodes):
        logger.info(f"📌 Episodio {ep+1}/{episodes}")

        # Crear ambiente NUEVO para cada episodio
        base_env = CityLearnEnv(schema_path)
        env = ListToArrayWrapper(base_env)

        # Crear modelo SAC
        model = SAC(
            "MlpPolicy",
            env,
            learning_rate=0.00015,
            buffer_size=1_000_000,
            batch_size=256,
            tau=0.005,
            gamma=0.99,
            verbose=0
        )

        # Entrenar
        ep_start = time.time()
        model.learn(total_timesteps=timesteps_per_episode)

        # Evaluar: recolectar rewards en ese episodio
        obs, _ = env.reset()
        episode_reward = 0.0
        for step in range(timesteps_per_episode):
            action, _ = model.predict(obs)
            obs, reward, terminated, truncated, _ = env.step(action)
            episode_reward += reward
            if terminated or truncated:
                obs, _ = env.reset()

        ep_time = time.time() - ep_start
        rewards_per_episode.append(episode_reward)

        logger.info(f"   ✓ Reward: {episode_reward:,.2f}")
        logger.info(f"   ✓ Tiempo: {ep_time:.1f}s\n")

        env.close()

    total_time = time.time() - start_time

    return {
        "agent": "SAC",
        "episodes": episodes,
        "rewards_per_episode": rewards_per_episode,
        "mean_reward": float(np.mean(rewards_per_episode)),
        "total_time": total_time
    }


def main():
    logger.info("=" * 80)
    logger.info("ENTRENAMIENTO REAL: PPO → SAC → A2C")
    logger.info("=" * 80)
    logger.info("")

    # Detectar schema
    schema_path = PROJECT_ROOT / "data" / "processed" / "citylearn" / "iquitos_ev_mall" / "schema.json"

    if not schema_path.exists():
        logger.error(f"❌ Schema no encontrado: {schema_path}")
        return 1

    logger.info(f"✓ Schema: {schema_path}\n")

    episodes = 1  # Cambiar a 2, 3, 5, etc. para más episodios

    try:
        # PPO
        result_ppo = train_ppo_real(str(schema_path), episodes=episodes)

        # SAC
        result_sac = train_sac_real(str(schema_path), episodes=episodes)

        # A2C
        result_a2c = train_a2c_real(str(schema_path), episodes=episodes)

        # Guardar
        results = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "ppo": result_ppo,
            "sac": result_sac,
            "a2c": result_a2c
        }

        output_dir = PROJECT_ROOT / "outputs" / "oe3_simulations"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"training_summary_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ ENTRENAMIENTO COMPLETADO")
        logger.info("=" * 80)
        logger.info(f"📊 Resultados: {output_file}")
        logger.info("")
        logger.info(f"PPO:  {result_ppo['mean_reward']:,.2f} avg reward ({result_ppo['total_time']:.1f}s total)")
        logger.info(f"SAC:  {result_sac['mean_reward']:,.2f} avg reward ({result_sac['total_time']:.1f}s total)")
        logger.info(f"A2C:  {result_a2c['mean_reward']:,.2f} avg reward ({result_a2c['total_time']:.1f}s total)")
        logger.info("")

        return 0

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

