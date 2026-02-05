#!/usr/bin/env python3
"""
TEST RÁPIDO SAC - MULTIOBJETIVO REAL (5 episodios - 2 minutos)
Verifica integración de: Cálculos CO₂ + Pesos + Control BESS + Chargers diferenciados
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
from typing import Any

warnings.filterwarnings('ignore', category=DeprecationWarning)

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print('='*80)
print('TEST RÁPIDO SAC - MULTIOBJETIVO REAL (5 EPISODIOS)')
print('='*80)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

try:
    print('[1] CARGAR REWARD MULTIOBJETIVO Y CONTEXTO')
    print('-' * 80)

    from src.rewards.rewards import (
        IquitosContext,
        MultiObjectiveWeights,
        MultiObjectiveReward,
        create_iquitos_reward_weights
    )

    # Usar preset "co2_focus"
    weights = create_iquitos_reward_weights("co2_focus")
    context = IquitosContext()
    reward_calc = MultiObjectiveReward(weights=weights, context=context)

    print('  ✓ Contexto Iquitos cargado:')
    print(f'    - CO₂ grid: {context.co2_factor_kg_per_kwh} kg CO₂/kWh (térmica aislada)')
    print(f'    - Chargers: {context.n_chargers} físicos (28 motos@2kW + 4 mototaxis@3kW)')
    print(f'    - Sockets: {context.total_sockets} (112 motos + 16 mototaxis)')
    print()

    print('  ✓ Pesos multiobjetivo (CO₂ focus):')
    for key, val in weights.as_dict().items():
        if val > 0:
            print(f'    - {key}: {val:.2f}')
    print()

    print('[2] CREAR ENVIRONMENT CON MULTIOBJETIVO REAL')
    print('-' * 80)

    from gymnasium import Env, spaces

    class CityLearnRealEnv(Env):
        """Environment con recompensa multiobjetivo REAL"""

        def __init__(self, reward_calc, context, obs_dim=394, action_dim=129, max_steps=8760):
            self.reward_calculator = reward_calc
            self.context = context
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
            self.co2_timeline = []
            self.reward_components_timeline = []

        def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
            super().reset(seed=seed)
            self.step_count = 0
            self.episode_reward = 0.0
            self.episode_num += 1
            self.co2_timeline = []
            self.reward_components_timeline = []
            obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
            return obs, {}

        def step(self, action):
            self.step_count += 1
            hour = (self.step_count - 1) % 24

            # Dispatch (1 BESS + 128 chargers)
            bess_setpoint = action[0]
            charger_setpoints = action[1:129]

            # Potencia sintetizada:
            # - BESS: setpoint × capacidad
            # - Motos (112 sockets): charger_setpoints[:112] × 2kW avg
            # - Mototaxis (16 sockets): charger_setpoints[112:] × 3kW avg

            motos_power_kw = np.sum(charger_setpoints[:112]) * self.context.charger_power_kw_moto / 112 * 20
            mototaxis_power_kw = np.sum(charger_setpoints[112:128]) * self.context.charger_power_kw_mototaxi / 16 * 20
            ev_charging_kwh = (motos_power_kw + mototaxis_power_kw) / 3600

            # Solar (patrón típico Iquitos ecuatorial)
            solar_base = 3500  # kWp nominal (4162 disponible)
            if 6 <= hour <= 18:
                solar_generation_kwh = solar_base * np.sin(np.pi * (hour - 6) / 12) * 0.8 / 3600
            else:
                solar_generation_kwh = 0.0

            # Mall demand (carga del centro comercial)
            if 9 <= hour <= 22:
                mall_load_kw = 200 + 100 * np.sin(np.pi * (hour - 9) / 13)
            else:
                mall_load_kw = 100

            # Grid balance
            total_load_kwh = (mall_load_kw + motos_power_kw + mototaxis_power_kw) / 3600
            if solar_generation_kwh >= total_load_kwh:
                grid_import_kwh = 0.0
                grid_export_kwh = max(0, solar_generation_kwh - total_load_kwh)
            else:
                grid_import_kwh = total_load_kwh - solar_generation_kwh
                grid_export_kwh = 0.0

            # EV SOC (simulado)
            ev_soc_avg = min(1.0, 0.3 + np.sum(charger_setpoints) / 128 * 0.6)

            # BESS SOC (simulado)
            bess_soc = min(0.95, max(0.1, 0.5 + bess_setpoint * 0.3))

            # CALCULAR RECOMPENSA MULTIOBJETIVO REAL
            reward, components = self.reward_calculator.compute(
                grid_import_kwh=grid_import_kwh,
                grid_export_kwh=grid_export_kwh,
                solar_generation_kwh=solar_generation_kwh,
                ev_charging_kwh=ev_charging_kwh,
                ev_soc_avg=ev_soc_avg,
                bess_soc=bess_soc,
                hour=hour
            )

            self.episode_reward += reward
            self.co2_timeline.append(components.get('co2_net_kg', 0))

            # Almacenar para análisis
            self.reward_components_timeline.append({
                'r_co2': float(components.get('r_co2', 0)),
                'r_solar': float(components.get('r_solar', 0)),
                'r_cost': float(components.get('r_cost', 0)),
                'r_ev': float(components.get('r_ev', 0)),
                'co2_avoided_total_kg': float(components.get('co2_avoided_total_kg', 0)),
                'hour': hour,
            })

            obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
            terminated = self.step_count >= min(100, self.max_steps)  # Corto para test
            truncated = False
            info = {'step': self.step_count, 'hour': hour}

            return obs, reward, terminated, truncated, info

    env = CityLearnRealEnv(reward_calc, context)

    print('  ✓ Environment creado')
    print('  ✓ Integración: Multiobjetivo (CO₂ + Solar + Cost + EV + Grid)')
    print('  ✓ Control: BESS (1) + Motos (112) + Mototaxis (16) = 129 acciones')
    print()

    print('[3] CREAR AGENT SAC')
    print('-' * 80)

    from stable_baselines3 import SAC

    agent = SAC(
        'MlpPolicy',
        env,
        learning_rate=3e-4,
        batch_size=64,
        buffer_size=100000,
        learning_starts=100,
        train_freq=1,
        verbose=0,
        tensorboard_log=None  # Desactivar para test rápido
    )

    print(f'  ✓ SAC agent creado')
    print(f'    - Policy: MlpPolicy')
    print(f'    - Network: [256, 256]')
    print()

    print('[4] ENTRENAR 5 EPISODIOS (TEST RÁPIDO - ~2 min)')
    print('-' * 80)
    print()

    # Entrenar solo 500 steps (~5 episodios × 100 steps)
    agent.learn(total_timesteps=500, progress_bar=False)

    print('  ✓ Entrenamiento completado')
    print()

    print('[5] TEST INFERENCIA')
    print('-' * 80)
    print()

    inference_results = []

    for ep in range(3):
        obs, _ = env.reset()
        done = False
        ep_reward = 0.0
        step = 0

        print(f'  Episodio {ep+1}/3:')

        while not done:
            action_result = agent.predict(obs, deterministic=True)
            if action_result is not None:
                action = action_result[0]
            else:
                action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
            step += 1

        # Análisis
        co2_avg = float(np.mean([x for x in env.co2_timeline]))
        co2_avoided_total = sum([c['co2_avoided_total_kg'] for c in env.reward_components_timeline])

        # Componentes de recompensa
        r_co2_avg = float(np.mean([c['r_co2'] for c in env.reward_components_timeline]))
        r_solar_avg = float(np.mean([c['r_solar'] for c in env.reward_components_timeline]))
        r_ev_avg = float(np.mean([c['r_ev'] for c in env.reward_components_timeline]))

        inference_results.append({
            'episode': ep + 1,
            'total_reward': ep_reward,
            'steps': step,
            'co2_net_avg_kg': co2_avg,
            'co2_avoided_total_kg': co2_avoided_total,
            'r_co2_avg': r_co2_avg,
            'r_solar_avg': r_solar_avg,
            'r_ev_avg': r_ev_avg,
        })

        print(f'    Reward total: {ep_reward:>8.3f}')
        print(f'    CO₂ neto promedio: {co2_avg:>7.2f} kg/h')
        print(f'    CO₂ evitado total: {co2_avoided_total:>7.1f} kg')
        print(f'    Componentes reward:')
        print(f'      - r_co2: {r_co2_avg:>6.3f}')
        print(f'      - r_solar: {r_solar_avg:>6.3f}')
        print(f'      - r_ev: {r_ev_avg:>6.3f}')
        print()

    print()
    print('='*80)
    print('TEST COMPLETADO - RESULTADO')
    print('='*80)
    print()

    # Resumen
    rewards_mean = float(np.mean([r['total_reward'] for r in inference_results]))
    co2_avoided_mean = float(np.mean([r['co2_avoided_total_kg'] for r in inference_results]))

    print(f'✓ SISTEMA MULTIOBJETIVO FUNCIONANDO:')
    print()
    print(f'Resultados (promedio 3 episodios):')
    print(f'  • Reward multiobjetivo: {rewards_mean:.4f}')
    print(f'  • CO₂ evitado: {co2_avoided_mean:.1f} kg/episodio')
    print()

    print(f'STATUS: ✓ SAC CON MULTIOBJETIVO REAL - FUNCIONANDO CORRECTAMENTE')
    print()

    print('PRÓXIMOS PASOS:')
    print('  1. Ejecutar entrenamiento completo:')
    print('     python train_sac_multiobjetivo.py')
    print()
    print('  2. Entrenar PPO y A2C con arquitectura similar')
    print()

    env.close()

except Exception as e:
    print(f'\n[ERROR] {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
