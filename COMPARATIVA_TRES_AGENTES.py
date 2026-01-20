#!/usr/bin/env python
"""
COMPARATIVA FINAL DE 3 AGENTES
PPO vs A2C vs SAC - Con baseline randomizado
"""
import sys
import numpy as np
import logging
from pathlib import Path
from stable_baselines3 import PPO, A2C, SAC
import gymnasium as gym

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("analyses/logs/COMPARATIVA_TRES_AGENTES.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
from citylearn.citylearn import CityLearnEnv

SCHEMA_PATH = "data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json"

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


def evaluate_agent(agent_name, model=None, num_episodes=1):
    """Evaluar un agente (o baseline random)"""
    logger.info(f"\n{'='*80}")
    logger.info(f"Evaluando: {agent_name}")
    logger.info(f"{'='*80}")
    
    # Crear environment
    base_env = CityLearnEnv(schema=str(SCHEMA_PATH))
    env = FlatActionWrapper(base_env)
    
    total_rewards = []
    
    for episode in range(num_episodes):
        obs, _ = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            if model is None:  # Baseline random
                action = env.action_space.sample()
            else:  # Agente entrenado
                action, _ = model.predict(obs, deterministic=True)
            
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            done = terminated or truncated
        
        total_rewards.append(episode_reward)
        logger.info(f"  Episodio {episode+1}: {episode_reward:.4f}")
    
    env.close()
    
    mean_reward = np.mean(total_rewards)
    std_reward = np.std(total_rewards)
    
    logger.info(f"  Media: {mean_reward:.4f}")
    logger.info(f"  Std: {std_reward:.4f}")
    
    return mean_reward, std_reward, total_rewards


def main():
    logger.info("\n")
    logger.info("╔" + "="*78 + "╗")
    logger.info("║" + " "*78 + "║")
    logger.info("║" + "COMPARATIVA FINAL: PPO vs A2C vs SAC".center(78) + "║")
    logger.info("║" + "MALL IQUITOS - 128 TOMAS".center(78) + "║")
    logger.info("║" + " "*78 + "║")
    logger.info("╚" + "="*78 + "╝\n")
    
    results = {}
    
    # 1. BASELINE (RANDOM)
    logger.info("\n[PASO 1] BASELINE RANDOMIZADO")
    baseline_mean, baseline_std, _ = evaluate_agent("BASELINE (Random)", model=None, num_episodes=2)
    results['baseline'] = {
        'mean': baseline_mean,
        'std': baseline_std,
        'timesteps': 'N/A'
    }
    
    # 2. PPO
    logger.info("\n[PASO 2] PPO (17,520 timesteps)")
    ppo_path = Path("analyses/oe3/training/checkpoints/ppo_gpu/ppo_final.zip")
    if ppo_path.exists():
        try:
            ppo_model = PPO.load(str(ppo_path))
            ppo_mean, ppo_std, _ = evaluate_agent("PPO", model=ppo_model, num_episodes=2)
            results['ppo'] = {
                'mean': ppo_mean,
                'std': ppo_std,
                'timesteps': 17520
            }
        except Exception as e:
            logger.error(f"Error cargando PPO: {e}")
            results['ppo'] = {'mean': 0, 'std': 0, 'timesteps': 17520}
    else:
        logger.warning(f"No encontrado: {ppo_path}")
        results['ppo'] = {'mean': 0, 'std': 0, 'timesteps': 17520}
    
    # 3. A2C
    logger.info("\n[PASO 3] A2C (17,520 timesteps)")
    a2c_path = Path("analyses/oe3/training/checkpoints/a2c_gpu/a2c_final.zip")
    if a2c_path.exists():
        try:
            a2c_model = A2C.load(str(a2c_path))
            a2c_mean, a2c_std, _ = evaluate_agent("A2C", model=a2c_model, num_episodes=2)
            results['a2c'] = {
                'mean': a2c_mean,
                'std': a2c_std,
                'timesteps': 17520
            }
        except Exception as e:
            logger.error(f"Error cargando A2C: {e}")
            results['a2c'] = {'mean': 0, 'std': 0, 'timesteps': 17520}
    else:
        logger.warning(f"No encontrado: {a2c_path}")
        results['a2c'] = {'mean': 0, 'std': 0, 'timesteps': 17520}
    
    # 4. SAC (si existe)
    logger.info("\n[PASO 4] SAC (17,500 timesteps - Histórico)")
    sac_path = Path("analyses/oe3/training/checkpoints/sac_gpu/sac_final.zip")
    if sac_path.exists():
        try:
            sac_model = SAC.load(str(sac_path))
            sac_mean, sac_std, _ = evaluate_agent("SAC", model=sac_model, num_episodes=2)
            results['sac'] = {
                'mean': sac_mean,
                'std': sac_std,
                'timesteps': 17500
            }
        except Exception as e:
            logger.error(f"Error cargando SAC: {e}")
            results['sac'] = {'mean': 0, 'std': 0, 'timesteps': 17500}
    else:
        logger.info(f"SAC no encontrado (esperado)")
        results['sac'] = {'mean': 0, 'std': 0, 'timesteps': 17500}
    
    # RESUMEN
    logger.info("\n")
    logger.info("╔" + "="*78 + "╗")
    logger.info("║" + "RESULTADOS FINALES".center(78) + "║")
    logger.info("║" + "="*78 + "║")
    
    logger.info("║" + " "*78 + "║")
    logger.info("║ {:20} {:15} {:15} {:15}".format("Agente", "Media", "Std", "Timesteps") + " ║")
    logger.info("║" + "-"*78 + "║")
    
    for agent_name, data in results.items():
        agent_display = agent_name.upper()
        mean_val = f"{data['mean']:.4f}"
        std_val = f"{data['std']:.4f}"
        ts_val = f"{data['timesteps']}"
        logger.info("║ {:20} {:15} {:15} {:15}".format(agent_display, mean_val, std_val, ts_val) + " ║")
    
    logger.info("║" + " "*78 + "║")
    logger.info("╚" + "="*78 + "╝\n")
    
    # RANKING
    logger.info("\n[RANKING DE RENDIMIENTO]")
    sorted_results = sorted(
        [(k, v['mean']) for k, v in results.items() if v['mean'] > 0],
        key=lambda x: x[1],
        reverse=True
    )
    
    for rank, (agent, score) in enumerate(sorted_results, 1):
        improvement = ((score - results['baseline']['mean']) / results['baseline']['mean'] * 100)
        logger.info(f"{rank}. {agent.upper():10} - Score: {score:.4f} ({improvement:+.1f}% vs baseline)")
    
    logger.info("\n")

if __name__ == "__main__":
    main()
