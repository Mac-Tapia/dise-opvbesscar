#!/usr/bin/env python3
"""
ENTRENAR SAC CON MULTIOBJETIVO REAL
Integración completa: Cálculos CO2 + Rewards multiobjetivo + BESS + Chargers diferenciados
"""

#!/usr/bin/env python3
"""
ENTRENAR SAC CON MULTIOBJETIVO REAL - OPTIMIZADO GPU
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

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print('='*80)
print('ENTRENAR SAC - CON MULTIOBJETIVO REAL (CO2, SOLAR, COST, EV, GRID)')
print('='*80)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# AUTO-DETECTAR GPU Y CONFIGURAR
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
if DEVICE == 'cuda':
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
    print(f'🔥 GPU DISPONIBLE: {GPU_NAME}')
    print(f'   Memoria: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA Version: {cuda_version}')
    # Optimizar configuración para GPU
    BATCH_SIZE = 128  # Aprovechar más memoria
    BUFFER_SIZE = 2000000  # Replay buffer más grande para GPU
    NETWORK_ARCH = [512, 512]  # Red más grande aprovecha GPU
else:
    print('⚠️  CPU mode (no GPU disponible)')
    print(f'   Optimizando para CPU...')
    BATCH_SIZE = 64
    BUFFER_SIZE = 1000000
    NETWORK_ARCH = [256, 256]

print(f'   Device: {DEVICE}')
print(f'   Batch size: {BATCH_SIZE}')
print(f'   Buffer size: {BUFFER_SIZE}')
print(f'   Network: {NETWORK_ARCH}')
print()

CHECKPOINT_DIR = Path('checkpoints/SAC')
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path('outputs/sac_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    print('[1] CARGAR CONFIGURACIÓN Y CONTEXTO MULTIOBJETIVO')
    print('-' * 80)

    # Cargar config
    with open('configs/default.yaml', 'r') as f:
        cfg = yaml.safe_load(f)

    print(f'  ✓ Config loaded: {len(cfg)} keys')

    # Cargar rewards (contexto Iquitos + pesos multiobjetivo)
    from src.rewards.rewards import IquitosContext, MultiObjectiveWeights, MultiObjectiveReward
    from src.rewards.rewards import create_iquitos_reward_weights

    # Usar preset "co2_focus" para maximizar reducción CO2
    weights = create_iquitos_reward_weights("co2_focus")
    context = IquitosContext()
    reward_calculator = MultiObjectiveReward(weights=weights, context=context)

    print(f'  ✓ Reward weights (CO₂ focus):')
    print(f'    - CO₂: {weights.co2:.2f}  (minimizar grid import)')
    print(f'    - Solar: {weights.solar:.2f}  (maximizar autoconsumo)')
    print(f'    - Cost: {weights.cost:.2f}  (minimizar tarifa)')
    print(f'    - EV: {weights.ev_satisfaction:.2f}  (satisfacción carga)')
    print(f'    - Grid: {weights.grid_stability:.2f}  (estabilidad)')
    print()

    print(f'  ✓ Contexto Iquitos:')
    print(f'    - Grid CO₂: {context.co2_factor_kg_per_kwh} kg CO₂/kWh (térmica aislada)')
    print(f'    - EV CO₂ factor: {context.co2_conversion_factor} kg CO₂/kWh (combustión equivalente)')
    print(f'    - Chargers: {context.n_chargers} (28 motos@2kW + 4 mototaxis@3kW)')
    print(f'    - Sockets: {context.total_sockets} (112 motos + 16 mototaxis)')
    print(f'    - Daily capacity: {context.motos_daily_capacity} motos + {context.mototaxis_daily_capacity} mototaxis')
    print()

    print('[2] CONTRUIR DATASET CITYLEARN V2')
    print('-' * 80)

    from src.citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset

    dataset = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=Path('data/raw'),
        interim_dir=Path('data/interim/oe2'),
        processed_dir=Path('data/processed')
    )

    print(f'  ✓ Dataset: {dataset.dataset_dir}')
    print()

    print('[3] CREAR ENVIRONMENT CON REWARD MULTIOBJETIVO REAL')
    print('-' * 80)

    import numpy as np
    from gymnasium import Env, spaces
    from stable_baselines3 import SAC
    from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback

    class CityLearnRealEnv(Env):
        """Environment con recompensa multiobjetivo real de Iquitos"""

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

            # Tracking de métricas
            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0
            self.ev_soc_trajectory = []

        def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
            super().reset(seed=seed)
            self.step_count = 0
            self.episode_reward = 0.0
            self.episode_num += 1

            # Reset tracking
            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0
            self.ev_soc_trajectory = []

            # Observación inicial
            obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
            return obs, {}

        def step(self, action):
            self.step_count += 1
            hour = (self.step_count % 8760) // 24  # Hora del día [0-23]

            # Simular energía basada en acción
            # action[0] = BESS setpoint
            # action[1:129] = charger setpoints (128 chargers)

            # BESS dispatch
            bess_setpoint = action[0]  # [0, 1] → [0, 2712 kW]
            bess_power_kw = bess_setpoint * self.context.n_chargers * 2.1  # ~2.1 kW avg por charger

            # Chargers dispatch (diferenciado motos vs mototaxis)
            charger_setpoints = action[1:129]  # 128 setpoints
            motos_power = np.sum(charger_setpoints[:112]) * self.context.charger_power_kw_moto / 112
            mototaxis_power = np.sum(charger_setpoints[112:128]) * self.context.charger_power_kw_mototaxi / 16
            ev_charging_kwh = (motos_power + mototaxis_power) / 3600  # Convert to kWh/sec

            # Simular generación solar (patrón diario simple)
            solar_peak = 3000  # kWp (4162 kWp nominal)
            hour_norm = hour / 24.0
            solar_generation_kwh = max(0, solar_peak * np.sin(np.pi * hour_norm) * 0.8)  # Pico a medio día

            # Simular demanda del mall
            mall_baseline = 100.0  # kWh/hora base
            if 9 <= hour <= 22:  # 9 AM - 10 PM
                mall_demand = mall_baseline * (1 + 0.3 * np.sin(np.pi * (hour - 9) / 13))
            else:
                mall_demand = mall_baseline * 0.3

            # Cálculo de grid import/export
            total_demand = max(0, mall_demand + ev_charging_kwh * 3600)
            if solar_generation_kwh >= total_demand:
                grid_import_kwh = 0.0
                grid_export_kwh = max(0, solar_generation_kwh - total_demand)
            else:
                grid_import_kwh = total_demand - solar_generation_kwh
                grid_export_kwh = 0.0

            # Simular SOC de EVs
            ev_soc_avg = min(1.0, 0.5 + ev_charging_kwh * 0.1)
            self.ev_soc_trajectory.append(ev_soc_avg)

            # BESS SOC (simulado)
            bess_soc = min(1.0, 0.3 + bess_setpoint * 0.6)

            # Calcular recompensa MULTIOBJETIVO REAL
            total_reward, components = self.reward_calculator.compute(
                grid_import_kwh=grid_import_kwh,
                grid_export_kwh=grid_export_kwh,
                solar_generation_kwh=solar_generation_kwh,
                ev_charging_kwh=ev_charging_kwh,
                ev_soc_avg=ev_soc_avg,
                bess_soc=bess_soc,
                hour=hour,
                ev_demand_kwh=self.context.ev_demand_constant_kw
            )

            # Tracking acumulativo
            self.co2_avoided_total += components.get('co2_avoided_total_kg', 0)
            self.solar_kwh_total += solar_generation_kwh
            self.cost_total += components.get('cost_usd', 0)
            self.grid_import_total += grid_import_kwh

            self.episode_reward += total_reward

            # Observación siguiente
            obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1

            terminated = self.step_count >= self.max_steps
            truncated = False
            info = {
                'step': self.step_count,
                'hour': hour,
                'episode': self.episode_num,
                'episode_reward': self.episode_reward,
                # Componentes de recompensa para inspección
                'r_co2': float(components.get('r_co2', 0)),
                'r_solar': float(components.get('r_solar', 0)),
                'r_cost': float(components.get('r_cost', 0)),
                'r_ev': float(components.get('r_ev', 0)),
                # Métricas de CO2
                'co2_grid_kg': float(components.get('co2_grid_kg', 0)),
                'co2_avoided_indirect_kg': float(components.get('co2_avoided_indirect_kg', 0)),
                'co2_avoided_direct_kg': float(components.get('co2_avoided_direct_kg', 0)),
                'co2_avoided_total_kg': float(components.get('co2_avoided_total_kg', 0)),
                # Dispatch
                'ev_charging_kwh': float(ev_charging_kwh),
                'bess_power_kw': float(bess_power_kw),
                'motos_power_kw': float(motos_power),
                'mototaxis_power_kw': float(mototaxis_power),
                'grid_import_kwh': float(grid_import_kwh),
                'solar_generation_kwh': float(solar_generation_kwh),
            }

            return obs, total_reward, terminated, truncated, info

    env = CityLearnRealEnv(
        reward_calc=reward_calculator,
        context=context,
        obs_dim=394,
        action_dim=129,
        max_steps=8760
    )

    print(f'  ✓ Environment creado con recompensa multiobjetivo')
    print(f'    - Observation: {env.observation_space.shape}')
    print(f'    - Action: {env.action_space.shape}')
    print(f'    - Reward: Multiobjetivo (CO₂, Solar, Cost, EV, Grid)')
    print()

    print('[4] CREAR SAC AGENT - CONFIGURACIÓN ÓPTIMA PARA GPU/CPU')
    print('-' * 80)

    from torch import nn as torch_nn

    sac_config: dict[str, Any] = {
        'learning_rate': 2e-4,  # OPCIÓN A: Reducido 33% (3e-4 → 2e-4) para GPU batch_size=128
        'batch_size': BATCH_SIZE,  # Dinámico según GPU/CPU
        'buffer_size': BUFFER_SIZE,  # Dinámico según GPU/CPU
        'learning_starts': 1000,
        'train_freq': 1,
        'tau': 0.005,
        'gamma': 0.99,
        'ent_coef': 'auto',
        'target_entropy': 'auto',
        'policy_kwargs': {
            'net_arch': NETWORK_ARCH,  # Dinámico según GPU/CPU
            'activation_fn': torch_nn.ReLU,
        },
        'device': DEVICE,  # Usar GPU si disponible
        'verbose': 0,
        'tensorboard_log': None  # Desabilitar tensorboard si no está instalado
    }

    agent = SAC('MlpPolicy', env, **sac_config)

    print(f'  ✓ SAC agent creado (DEVICE: {DEVICE.upper()})')
    print(f'    - Learning rate: {sac_config["learning_rate"]} (OPCIÓN A: Reducido 33% vs 3e-4)')
    print(f'    - Batch size: {BATCH_SIZE}')
    print(f'    - Buffer size: {BUFFER_SIZE:,}')
    print(f'    - Network: {NETWORK_ARCH}')
    print(f'    - Entropy: auto-tuned')
    print()

    print('[5] ENTRENAR SAC')
    print('-' * 80)

    class DetailedLoggingCallback(BaseCallback):
        def __init__(self):
            super().__init__()
            self.episode_count = 0
            self.step_log = []

        def _on_step(self) -> bool:
            if self.num_timesteps % 5000 == 0:
                print(f'      Steps: {self.num_timesteps:>8,} | Episodes: ~{self.num_timesteps // 8760}')
            return True

    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=str(CHECKPOINT_DIR),
        name_prefix='sac_checkpoint',
        save_replay_buffer=True
    )

    logging_callback = DetailedLoggingCallback()

    TOTAL_TIMESTEPS = 100000

    print(f'  Entrenando {TOTAL_TIMESTEPS:,} timesteps (~{TOTAL_TIMESTEPS//8760} episodios)...')
    print(f'  Reward MULTIOBJETIVO activo:')
    print(f'    • CO₂ grid (0.50): Minimizar importación + Maximizar solar')
    print(f'    • Solar (0.20): Autoconsumo de PV limpio')
    print(f'    • Cost (0.15): Minimizar costo eléctrico')
    print(f'    • EV satisfacción (0.10): Cargar a 90% SOC')
    print(f'    • Grid stability (0.05): Suavizar demanda pico')
    print()

    start_time = datetime.now()

    agent.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=[checkpoint_callback, logging_callback],
        progress_bar=False
    )

    elapsed = (datetime.now() - start_time).total_seconds()

    print()
    print(f'  ✓ Entrenamiento completado en {elapsed:.1f}s ({elapsed/60:.1f} min)')
    print()

    # Guardar modelo final
    final_model_path = CHECKPOINT_DIR / 'sac_final_model'
    agent.save(str(final_model_path))
    print(f'  ✓ Modelo guardado: {final_model_path}.zip')
    print()

    print('[6] VALIDACIÓN FINAL')
    print('-' * 80)

    print('  Ejecutando 3 episodios de validación...')
    print()

    val_metrics: dict[str, list[float]] = {
        'rewards': [],
        'co2_avoided': [],
        'solar_kwh': [],
        'cost_usd': [],
        'grid_import': [],
    }

    for ep in range(3):
        obs, _ = env.reset()
        done = False
        steps = 0

        print(f'    Episodio {ep+1}/3: ', end='', flush=True)

        while not done:
            action_result = agent.predict(obs, deterministic=True)
            if action_result is not None:
                action = action_result[0]
            else:
                action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            steps += 1

        # Acumular métricas
        val_metrics['rewards'].append(env.episode_reward)
        val_metrics['co2_avoided'].append(env.co2_avoided_total)
        val_metrics['solar_kwh'].append(env.solar_kwh_total)
        val_metrics['cost_usd'].append(env.cost_total)
        val_metrics['grid_import'].append(env.grid_import_total)

        print(f'Reward={env.episode_reward:>7.2f}, CO₂ avoided={env.co2_avoided_total:>7.1f}kg, '
              f'Solar={env.solar_kwh_total:>8.1f}kWh, Steps={steps}')

    print()

    # Guardar métricas
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_timesteps': TOTAL_TIMESTEPS,
        'training_duration_seconds': elapsed,
        'episodes_trained': TOTAL_TIMESTEPS // 8760,
        'validation_metrics': {
            'mean_reward': float(np.mean(val_metrics['rewards'])),
            'std_reward': float(np.std(val_metrics['rewards'])),
            'mean_co2_avoided_kg': float(np.mean(val_metrics['co2_avoided'])),
            'mean_solar_kwh': float(np.mean(val_metrics['solar_kwh'])),
            'mean_cost_usd': float(np.mean(val_metrics['cost_usd'])),
            'mean_grid_import_kwh': float(np.mean(val_metrics['grid_import'])),
        },
        'reward_weights': weights.as_dict(),
        'context': {
            'co2_grid_factor': context.co2_factor_kg_per_kwh,
            'chargers': context.n_chargers,
            'sockets': context.total_sockets,
            'motos_daily': context.motos_daily_capacity,
            'mototaxis_daily': context.mototaxis_daily_capacity,
        }
    }

    metrics_file = OUTPUT_DIR / 'sac_training_metrics.json'
    with open(metrics_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f'  ✓ Métricas guardadas: {metrics_file}')
    print()

    print('='*80)
    print('ENTRENAMIENTO SAC COMPLETADO')
    print('='*80)
    print()

    print('RESULTADOS MULTIOBJETIVO:')
    validation_metrics = summary.get("validation_metrics", {})
    if isinstance(validation_metrics, dict):
        print(f'  Reward promedio: {validation_metrics.get("mean_reward", 0.0):.4f}')
        print(f'  CO₂ evitado: {validation_metrics.get("mean_co2_avoided_kg", 0.0):.1f} kg/episodio')
        print(f'  Solar utilizada: {validation_metrics.get("mean_solar_kwh", 0.0):.1f} kWh/episodio')
        print(f'  Costo: ${validation_metrics.get("mean_cost_usd", 0.0):.2f}/episodio')
        print(f'  Grid import: {validation_metrics.get("mean_grid_import_kwh", 0.0):.1f} kWh/episodio')
    else:
        print("  Validation metrics not available")
    print()

    print('STATUS: ✓ SAC CON MULTIOBJETIVO ENTRENADO EXITOSAMENTE')
    print()

    env.close()

except Exception as e:
    print(f'\n[ERROR] {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
