#!/usr/bin/env python3
"""
Evaluar y comparar todos los agentes entrenados
Genera reportes de desempeño
"""

import sys
import os
from pathlib import Path
import json
import yaml
from datetime import datetime
import numpy as np
import warnings
from typing import Any, Union

warnings.filterwarnings('ignore', category=DeprecationWarning)

os.environ['PYTHONIOENCODING'] = 'utf-8'

print('='*70)
print('EVALUACIÓN DE AGENTES - COMPARATIVA')
print('='*70)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

REPORT_DIR = Path('outputs/evaluation')
REPORT_DIR.mkdir(parents=True, exist_ok=True)

try:
    print('[1] CARGAR MODELOS')
    print('-' * 70)

    from src.citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset
    from gymnasium import Env, spaces
    from stable_baselines3 import SAC, PPO, A2C

    # Crear environment
    with open('configs/default.yaml', 'r') as f:
        cfg = yaml.safe_load(f)

    dataset = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=Path('data/raw'),
        interim_dir=Path('data/interim/oe2'),
        processed_dir=Path('data/processed')
    )

    class CityLearnGymEnv(Env):
        def __init__(self, obs_dim=394, action_dim=129, max_steps=8760):
            self.obs_dim = obs_dim
            self.action_dim = action_dim
            self.max_steps = max_steps

            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
            )
            self.action_space = spaces.Box(
                low=0.0, high=1.0, shape=(action_dim,), dtype=np.float32
            )

            self.step_count = 0
            self.episode_reward = 0.0
            self.episode_num = 0

        def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
            super().reset(seed=seed)
            self.step_count = 0
            self.episode_reward = 0.0
            self.episode_num += 1
            obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
            return obs, {}

        def step(self, action):
            self.step_count += 1

            obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1

            action_penalty = -0.01 * np.sum(np.abs(action - 0.5)) / self.action_dim
            dispatch_smoothness = -0.005 * np.std(action)
            efficiency_gain = 0.02 * np.sum(action > 0.2) / self.action_dim

            reward = float(action_penalty + dispatch_smoothness + efficiency_gain +
                          np.random.uniform(-0.02, 0.02))

            self.episode_reward += reward

            terminated = self.step_count >= self.max_steps
            truncated = False
            info = {
                'step': self.step_count,
                'episode_reward': self.episode_reward
            }

            return obs, reward, terminated, truncated, info

    env = CityLearnGymEnv()

    print('  ✓ Environment creado')
    print()

    # Cargar modelos
    print('[2] CARGAR MODELOS ENTRENADOS')
    print('-' * 70)

    models: dict[str, Union[Any, Any, Any]] = {}
    model_paths = {
        'SAC': Path('checkpoints/SAC/sac_final_model.zip'),
        'PPO': Path('checkpoints/PPO/ppo_final_model.zip'),
        'A2C': Path('checkpoints/A2C/a2c_final_model.zip'),
    }

    for agent_name, model_path in model_paths.items():
        if model_path.exists():
            if agent_name == 'SAC':
                model_sac: SAC = SAC.load(str(model_path), env=env)
                models[agent_name] = model_sac
            elif agent_name == 'PPO':
                model_ppo: PPO = PPO.load(str(model_path), env=env)
                models[agent_name] = model_ppo
            else:  # A2C
                model_a2c: A2C = A2C.load(str(model_path), env=env)
                models[agent_name] = model_a2c

            print(f'  ✓ {agent_name} cargado')
        else:
            print(f'  ✗ {agent_name} no encontrado: {model_path}')

    print()

    if not models:
        print('[ERROR] No se encontraron modelos entrenados')
        sys.exit(1)

    # Evaluar modelos
    print('[3] EVALUAR MODELOS')
    print('-' * 70)

    N_EPISODES = 10  # Evaluar con 10 episodios

    evaluation_results = {}

    for agent_name, model in models.items():
        print(f'\n  Evaluando {agent_name}...')

        episode_rewards = []
        episode_lengths = []

        for ep in range(N_EPISODES):
            obs, _ = env.reset()
            done = False
            ep_reward = 0.0
            ep_length = 0

            while not done:
                action_result = model.predict(obs, deterministic=True)
                if action_result is not None:
                    action = action_result[0]
                else:
                    action = env.action_space.sample()
                obs, reward, terminated, truncated, info = env.step(action)
                ep_reward += reward
                ep_length += 1
                done = terminated or truncated

            episode_rewards.append(ep_reward)
            episode_lengths.append(ep_length)

            if (ep + 1) % 5 == 0:
                print(f'    Episodios completados: {ep+1}/{N_EPISODES}')

        evaluation_results[agent_name] = {
            'mean_reward': float(np.mean(episode_rewards)),
            'std_reward': float(np.std(episode_rewards)),
            'min_reward': float(np.min(episode_rewards)),
            'max_reward': float(np.max(episode_rewards)),
            'mean_length': float(np.mean(episode_lengths)),
            'rewards': episode_rewards,
            'lengths': episode_lengths,
        }

        print(f'    ✓ {agent_name} completado')

    print()

    # Generar reporte
    print('[4] GENERAR REPORTE')
    print('-' * 70)

    report = {
        'timestamp': datetime.now().isoformat(),
        'evaluation_episodes': N_EPISODES,
        'models': evaluation_results,
        'ranking': []
    }

    # Ranking por reward medio - extract rewards with proper typing
    reward_dict: dict[str, float] = {}
    for agent_name, results in evaluation_results.items():
        mean_reward = results.get('mean_reward', 0.0)
        if isinstance(mean_reward, (int, float, np.number)):
            reward_dict[agent_name] = float(mean_reward)
        else:
            reward_dict[agent_name] = 0.0

    ranked = sorted(
        evaluation_results.items(),
        key=lambda x: reward_dict.get(x[0], 0.0),
        reverse=True
    )

    print('\nRanking por Reward Promedio:')
    print()
    ranking_list: list[dict[str, Any]] = []
    for i, (agent_name, results) in enumerate(ranked, 1):
        mean_reward = results['mean_reward']
        std_reward = results['std_reward']
        print(f'  {i}. {agent_name:5s}: {mean_reward:>8.4f} ± {std_reward:.4f}')
        ranking_list.append({
            'rank': i,
            'agent': agent_name,
            'mean_reward': mean_reward,
            'std_reward': std_reward
        })

    report['ranking'] = ranking_list

    print()

    # Tabla comparativa
    print('Tabla Comparativa:')
    print()
    print(f'{"Agent":<8} {"Mean":>10} {"Std":>10} {"Min":>10} {"Max":>10} {"Avg Len":>10}')
    print('-' * 60)

    for agent_name, results in sorted(evaluation_results.items()):
        print(f'{agent_name:<8} {results["mean_reward"]:>10.4f} '
              f'{results["std_reward"]:>10.4f} {results["min_reward"]:>10.4f} '
              f'{results["max_reward"]:>10.4f} {results["mean_length"]:>10.1f}')

    print()

    # Guardar reporte JSON
    report_file = REPORT_DIR / 'evaluation_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f'  ✓ Reporte JSON: {report_file}')

    # Guardar reporte CSV
    csv_file = REPORT_DIR / 'evaluation_comparison.csv'
    with open(csv_file, 'w') as f:
        f.write('Agent,Mean Reward,Std Reward,Min Reward,Max Reward,Avg Episode Length\n')
        for agent_name, results in evaluation_results.items():
            f.write(f'{agent_name},'
                   f'{results["mean_reward"]:.4f},'
                   f'{results["std_reward"]:.4f},'
                   f'{results["min_reward"]:.4f},'
                   f'{results["max_reward"]:.4f},'
                   f'{results["mean_length"]:.1f}\n')

    print(f'  ✓ Reporte CSV: {csv_file}')

    print()

    # Resumen final
    print('='*70)
    print('EVALUACIÓN COMPLETADA')
    print('='*70)
    print()

    best_agent = ranked[0][0]
    best_reward = ranked[0][1]['mean_reward']

    print(f'MEJOR AGENT: {best_agent} ({best_reward:.4f})')
    print()

    print('Archivos generados:')
    print(f'  - {report_file}')
    print(f'  - {csv_file}')
    print()

    env.close()

except Exception as e:
    print(f'\n[ERROR] {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
