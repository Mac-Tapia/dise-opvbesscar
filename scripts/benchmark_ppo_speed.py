#!/usr/bin/env python3
"""
Test rapido: Verifica si PPO esta realmente aprendiendo o si learn() es un no-op
"""

import time
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from gymnasium import Env, spaces
import gymnasium as gym

# Env sin

py simple para benchmark
class SimpleEnv(Env):
    def __init__(self):
        self.observation_space = spaces.Box(low=0, high=1, shape=(10,), dtype=np.float32)
        self.action_space = spaces.Box(low=0, high=1, shape=(2,), dtype=np.float32)
        self.step_count = 0
        self.max_steps = 100
    
    def reset(self, seed=None, options=None):
        self.step_count = 0
        return np.random.rand(10).astype(np.float32), {}
    
    def step(self, action):
        self.step_count += 1
        obs = np.random.rand(10).astype(np.float32)
        reward = float(1.0)  # Constant reward
        terminated = self.step_count >= self.max_steps
        truncated = False
        info = {}
        return obs, reward, terminated, truncated, info

def benchmark_ppo(num_steps=1000):
    """Benchmarkea cuanto tarda PPO en procesar N steps"""
    
    print('\n' + '='*100)
    print('[TIME]️  BENCHMARK: Medir tiempo real de model.learn()')
    print('='*100)
    
    print(f'\n[GRAPH] Configuracion:')
    print(f'   Environment: SimpleEnv (10-dim obs, 2-dim action)')
    print(f'   Total timesteps: {num_steps:,}')
    print(f'   Hardware: RTX 4060 CUDA')
    print(f'   Model: PPO (n_steps=128, batch_size=32, n_epochs=1)')
    
    # Crear env y modelo
    env = SimpleEnv()
    model = PPO(
        'MlpPolicy',
        env,
        n_steps=128,
        batch_size=32,
        n_epochs=1,
        learning_rate=3e-4,
        device='cuda',
        verbose=0
    )
    
    print(f'\n🚀 Iniciando entrenamiento...')
    start = time.time()
    model.learn(total_timesteps=num_steps, progress_bar=False)
    elapsed = time.time() - start
    
    actual_speed = num_steps / elapsed
    
    print(f'\n[OK] Entrenamiento completado')
    print(f'   Tiempo total: {elapsed:.2f} segundos')
    print(f'   Timesteps procesados: {num_steps:,}')
    print(f'   Velocidad: {actual_speed:.1f} steps/sec')
    
    print(f'\n🔍 Analisis:')
    
    # En una GPU normal (RTX 4060), el overhead es ~1-5ms por step
    # Policy forward: ~0.1-0.5ms
    # Value forward: ~0.1-0.5ms
    # Gradient computation: ~1-2ms
    # Total: ~2-4ms = 250-500 steps/sec teorico maximo
    
    if actual_speed < 100:
        print(f'   [!]  MUY LENTO: {actual_speed:.0f} steps/sec')
        print(f'      Probable: GPU no se usa, o hay overhead mayor')
    elif actual_speed < 300:
        print(f'   [OK] Normal: {actual_speed:.0f} steps/sec')
        print(f'      GPU siendo utilizada correctamente')
    elif actual_speed < 1000:
        print(f'   [!]  Rapido: {actual_speed:.0f} steps/sec')
        print(f'      Posible: Entorno muy simple, overhead bajo')
    else:
        print(f'   [X] ANORMALMENTE RAPIDO: {actual_speed:.0f} steps/sec')
        print(f'      Problema: learn() no esta haciendo forward/backward real')
        print(f'      O el contador de timesteps esta mal')
    
    print('\n' + '='*100 + '\n')
    
    return actual_speed

if __name__ == '__main__':
    # Test 1: Benchmark simple   
    speed = benchmark_ppo(num_steps=5000)
    
    # Proyectar a 87,600 timesteps (lo que hace PPO training)
    print(f'[CHART] Proyeccion a 87,600 timesteps:')
    projected_time_sec = 87600 / speed
    projected_time_min = projected_time_sec / 60
    projected_time_hour = projected_time_min / 60
    
    print(f'   Tiempo estimado: {projected_time_sec:.0f} sec = {projected_time_min:.1f} min = {projected_time_hour:.2f} horas')
    
    if projected_time_hour > 5:
        print(f'   [!]  Demasiado lento para entrenamiento productivo')
    elif projected_time_hour > 1:
        print(f'   [OK] Normal para entrenamiento con GPU')
    else:
        print(f'   [X] Sospechosamente rapido - verificar si learn() esta funcionando')
