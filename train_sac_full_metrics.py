#!/usr/bin/env python3
"""
ENTRENAR SAC CON METRICAS COMPLETAS Y VISIBILIDAD
- Motos y mototaxis cargadas
- CO2 grid, directo, indirecto
- Solar y grid kWh
- Parametros de entrenamiento visibles
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging
import yaml
import numpy as np

# Configurar encoding UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Silenciar logs verbosos
logging.getLogger('stable_baselines3').setLevel(logging.WARNING)
logging.getLogger('gymnasium').setLevel(logging.WARNING)

print("=" * 80)
print("ENTRENAMIENTO SAC - METRICAS COMPLETAS")
print("=" * 80)
print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================================================
# 1. CARGAR CONFIGURACION
# ============================================================================
print("[1] CONFIGURACION")
print("-" * 40)

config_path = Path("configs/default.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Parametros del proyecto
TOTAL_MOTOS = 2912
TOTAL_MOTOTAXIS = 416
TOTAL_VEHICULOS = TOTAL_MOTOS + TOTAL_MOTOTAXIS
GRID_CO2_INTENSITY = 0.4521  # kg CO2/kWh (Iquitos)
SOLAR_CAPACITY_KWP = 4050  # kWp instalado
BESS_CAPACITY_KWH = 4520  # kWh BESS
CHARGERS_TOTAL = 128  # 32 chargers x 4 sockets

print(f"  Motos: {TOTAL_MOTOS:,}")
print(f"  Mototaxis: {TOTAL_MOTOTAXIS:,}")
print(f"  Total vehiculos: {TOTAL_VEHICULOS:,}")
print(f"  Solar: {SOLAR_CAPACITY_KWP:,} kWp")
print(f"  BESS: {BESS_CAPACITY_KWH:,} kWh")
print(f"  Chargers: {CHARGERS_TOTAL}")
print(f"  CO2 grid: {GRID_CO2_INTENSITY} kg/kWh")
print()

# ============================================================================
# 2. CREAR ENVIRONMENT
# ============================================================================
print("[2] CREAR ENVIRONMENT")
print("-" * 40)

from src.iquitos_citylearn.oe3.dataset_builder_consolidated import _create_simple_env
env = _create_simple_env(config)

print(f"  Observation space: {env.observation_space.shape}")
print(f"  Action space: {env.action_space.shape}")
print(f"  Episode steps: {env.episode_steps}")
print()

# ============================================================================
# 3. CREAR SAC AGENT
# ============================================================================
print("[3] CREAR SAC AGENT")
print("-" * 40)

from src.agents.sac import SACAgent, SACConfig

# Configuracion optimizada para visibilidad
sac_config = SACConfig(
    episodes=5,
    batch_size=256,
    buffer_size=200000,
    learning_rate=5e-5,
    gamma=0.995,
    tau=0.02,
    ent_coef='auto',
    hidden_sizes=(256, 256),
    device='auto',
    verbose=1,
    log_interval=500,  # Log cada 500 steps
    checkpoint_dir="checkpoints/SAC",
    checkpoint_freq_steps=2000,
    save_final=True,
    normalize_observations=True,
    normalize_rewards=False,
    clip_obs=10.0,
    # Estabilidad
    critic_clip_gradients=True,
    critic_max_grad_norm=1.0,
    critic_loss_scale=0.1,
    max_grad_norm=10.0,
)

print(f"  Learning rate: {sac_config.learning_rate}")
print(f"  Batch size: {sac_config.batch_size}")
print(f"  Buffer size: {sac_config.buffer_size:,}")
print(f"  Hidden sizes: {sac_config.hidden_sizes}")
print(f"  Gamma: {sac_config.gamma}")
print(f"  Tau: {sac_config.tau}")
print(f"  Log interval: {sac_config.log_interval} steps")
print(f"  Checkpoint: cada {sac_config.checkpoint_freq_steps} steps")
print()

agent = SACAgent(env, sac_config)
print(f"  Device: {agent.device}")
print()

# ============================================================================
# 4. ENTRENAR
# ============================================================================
print("[4] ENTRENAR SAC")
print("-" * 40)

TOTAL_TIMESTEPS = 26280  # 3 episodios (8760 * 3)
EPISODES_EXPECTED = TOTAL_TIMESTEPS // 8760

print(f"  Total timesteps: {TOTAL_TIMESTEPS:,}")
print(f"  Episodios esperados: {EPISODES_EXPECTED}")
print(f"  Duracion episodio: 8760 steps (1 anio horario)")
print()
print("  METRICAS A MONITOREAR:")
print("  - grid_kWh: Energia importada del grid")
print("  - solar_kWh: Energia solar utilizada")
print("  - co2_grid: CO2 emitido por grid (kg)")
print("  - co2_direct: CO2 evitado por solar (kg)")
print("  - co2_indirect: CO2 evitado por transporte electrico (kg)")
print("  - motos: Motos cargadas (acumulado)")
print("  - mototaxis: Mototaxis cargadas (acumulado)")
print()
print("=" * 80)
print("INICIANDO ENTRENAMIENTO...")
print("=" * 80)
print()

start_time = datetime.now()

try:
    agent.learn(total_timesteps=TOTAL_TIMESTEPS)

    duration = datetime.now() - start_time
    print()
    print("=" * 80)
    print("ENTRENAMIENTO COMPLETADO")
    print("=" * 80)
    print(f"  Duracion: {duration}")
    print(f"  Timesteps: {TOTAL_TIMESTEPS:,}")
    print(f"  Checkpoint: checkpoints/SAC/")
    print()

except KeyboardInterrupt:
    print("\n[!] Entrenamiento interrumpido por usuario")
    duration = datetime.now() - start_time
    print(f"  Duracion parcial: {duration}")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

print()
print("FIN")
