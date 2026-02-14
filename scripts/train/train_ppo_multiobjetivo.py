#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR PPO CON MULTIOBJETIVO REAL - OPTIMIZADO
================================================================================
Entrenamiento de agente PPO con datos reales OE2 (Iquitos, Peru)
- 10 episodios completos (87,600 timesteps = 1 año)
- Datos: 38 sockets (19 chargers × 2), mall demand, BESS SOC, solar generation
- Reward: Multiobjetivo (CO2 focus, solar self-consumption, EV satisfaction)
- Optimizacion: GPU CUDA, batch normalization, gradient clipping

Referencias:
  [1] Schulman et al. (2017) "Proximal Policy Optimization Algorithms"
  [2] Stable-Baselines3: https://stable-baselines3.readthedocs.io/
  [3] Gymnasium: https://gymnasium.farama.org/
  [4] CityLearn v2: Multi-agent energy management benchmark
================================================================================
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# CRÍTICO: Agregar src/ directory a Python path para la estructura package_dir={"": "src"}
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import numpy as np
import pandas as pd
import torch
import yaml
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI para servidores/scripts
import matplotlib.pyplot as plt
from gymnasium import Env, spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
# VecNormalize: CRÍTICO para normalizar returns y resolver EV negativo (Engstrom 2020)
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

# Importaciones del módulo de rewards (OE3)
from src.dataset_builder_citylearn.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)

# Importar escenarios de carga de VEHICULOS
from vehicle_charging_scenarios import (
    VehicleChargingSimulator,
    VehicleChargingScenario,
    SCENARIO_OFF_PEAK,
    SCENARIO_PEAK_AFTERNOON,
    SCENARIO_PEAK_EVENING,
    SCENARIO_EXTREME_PEAK,
)

# ============================================================================
# CONFIGURACION BASICA - UTF-8 Encoding
# ============================================================================
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    if hasattr(sys.stdout, 'reconfigure'):  # type: ignore
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
except (AttributeError, TypeError, RuntimeError):
    pass

warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# ============================================================================
# LOGGER CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('train_ppo_log.txt', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class PPOConfig:
    """
    Configuracion optimada para PPO entrenamiento.
    Basada en aplicaciones de RL en energia y control de sistemas.
    
    Hiperparámetros clave [Schulman et al. 2017]:
    ===============================================
    - n_steps (rollout length): 128-2048, común 256/512/2048 según memoria y entorno
    - batch_size: 64-256, minibatches dentro del rollout total
    - n_epochs: 3-10 epochs por update (más = más sample efficiency, riesgo overfitting)
    - clip_range (ε): 0.1-0.3, típico 0.2 (controla cuánto puede cambiar la política)
    - gae_lambda: 0.9-0.97, típico 0.95 (balance bias-variance en advantage estimation)
    - ent_coef: 0.0-0.02 (promueve exploración, muy dependiente del entorno)
    - vf_coef: 0.5 típico (peso del value loss en el loss total)
    - max_grad_norm: 0.5-1.0 típico (gradient clipping para estabilidad)
    - target_kl: 0.01-0.05 típico (early stop si KL > target, IMPORTANTE para estabilidad)
    
    Señales de problemas típicos:
    - KL muy alto + clip_fraction alta → LR alto, demasiadas epochs, batch pequeño
    - Entropy colapsa temprano → ent_coef muy bajo o reward shaping agresivo
    - Explained variance negativa → crítico está fallando, revisar arquitectura
    """
    def __init__(self, device: str = 'cuda'):
        self.device = device

        # Hiperparametros PPO [Schulman et al. 2017 + Engstrom 2020 "Implementation Matters"]
        # ================================================================================
        # CORRECCIONES v3.0 (2026-02-13): Problema detectado - KL=16, EV=-25
        # Causa raíz: Updates demasiado agresivos, value function no converge
        # 
        # Referencias aplicadas:
        #   [1] Engstrom et al. (2020) "Implementation Matters in Deep RL"
        #   [2] Andrychowicz et al. (2021) "What Matters for On-Policy Deep Actor-Critic"
        #   [3] Henderson et al. (2018) "Deep RL That Matters"
        # ================================================================================
        
        # LEARNING RATE: Usar función de schedule (Engstrom 2020)
        # "LR annealing es CRÍTICO para PPO - alto KL indica LR muy agresivo"
        # v5.5: Reducido a 1.5e-4 after KL warnings
        # 
        # Ref: Engstrom et al (2020) "Implementation Matters in Deep RL"
        #      "Learning rate is the most important factor for PPO stability"
        # KL divergence alto (>0.03) es señal de que LR es muy agresivo
        self.learning_rate = 1.5e-4  # v5.5: MÁS BAJO para evitar KL alto
        self.use_lr_schedule = True  # Schedule lineal: 1.5e-4 → 0
        
        # N_STEPS: 2048 (más contexto temporal para episodios largos)
        # Con 8760 timesteps/episodio, n_steps=2048 captura ~23% del episodio
        # vs n_steps=1024 que solo captura ~12%
        self.n_steps = 2048  # AUMENTADO - más contexto mejora value function
        
        # BATCH_SIZE: v5.1 → 256 (menos varianza por minibatch, más estabilidad)
        # Con rollout de 2048 → 8 minibatches de 256 cada uno
        self.batch_size = 256 if device == 'cuda' else 128  # AUMENTADO para estabilidad
        
        # N_EPOCHS: 3 epochs por update (REDUCIDO v5.5 para evitar KL drift)
        # Engstrom 2020: "Fewer epochs = better KL control"
        # Por cada rollout, hacer solo 3 passes de gradient (no 5, no 10)
        # Menos updates = menos cambio en política = lower KL
        self.n_epochs = 3  # v5.5: REDUCIDO ahora a 3 (fue 5, fue 10)
        
        # GAMMA: 0.99 → 0.85 (MUY REDUCIDO para episodios ultra-largos)
        # Con 8,760 timesteps/episodio:
        #   gamma=0.99: return ≈ r/(1-γ) = r/0.01 = 100×r (IMPOSIBLE)
        #   gamma=0.95: return ≈ r/(1-γ) = r/0.05 = 20×r (difícil)
        #   gamma=0.90: return ≈ r/(1-γ) = r/0.10 = 10×r (inestable)
        #   gamma=0.85: return ≈ r/(1-γ) = r/0.15 = 6.7×r (mejor)
        # Andrychowicz 2021 + resultados empíricos v5.0
        self.gamma = 0.85  # v5.1: Reducido de 0.90 para estabilidad inter-episodio
        
        self.gae_lambda = 0.95  # GAE lambda (estándar)
        
        # CLIP_RANGE: 0.2 (estándar según Schulman et al 2017)
        # Schulman et al 2017: "ε is a hyperparameter, usually 0.1 or 0.2"
        # clip_range=0.3 es DEMASIADO ALTO, causa clip_fraction>30%
        self.clip_range = 0.2  # CORRECTO: Schulman et al 2017 recomendation
        
        # ENT_COEF: 0.01 (promover más exploración, evitar convergencia prematura)
        self.ent_coef = 0.01  # v5.3: Aumentado para mejor exploración
        
        # VF_COEF: 0.5 (Stable-Baselines3 default, estándar comunidad)
        # vf_coef=0.1 es TOO CONSERVATIVE, value network no se entrena → advantage ruidoso
        # Ref: Stable-Baselines3 defaults, Schulman et al 2017 - policy y value deben aprender al mismo ritmo
        self.vf_coef = 0.5  # ESTÁNDAR: SB3 default, permite value network aprender correctamente
        
        # MAX_GRAD_NORM: gradient clipping para estabilidad
        self.max_grad_norm = 0.5  # ESTÁNDAR - previene gradient explosion sin ser excesivo
        
        self.normalize_advantage = True  # MANTENER - necesario para estabilidad
        
        # TARGET_KL: 0.05 (relaxed para permitir learning)
        # v5.5: AUMENTADO de 0.02 a 0.05 (target_kl muy bajo causa paradas prematuras)
        # 
        # Formula [Schulman 2017]: early_stop si approx_kl > target_kl
        # target_kl=0.01: muy estricto, policy no puede aprender
        # target_kl=0.05: permite cambio controlado pero sin drift excesivo
        # target_kl=0.10: demasiado laxo, policy puede diverger
        # 
        # Reference: Schulman et al 2017 "Proximal Policy Optimization Algorithms"
        # Sección 5: "target_kl = 0.01 is a reasonable default"
        # BUT Engstrom 2020 encontró que en práctica 0.03-0.05 es mejor
        self.target_kl: Optional[float] = 0.05  # v5.5: Menos agresivo
        
        # CLIP_RANGE_VF: DESHABILITADO (Andrychowicz 2021)
        # "Value function loss clipping can HURT performance"
        # Engstrom 2020 también encontró que NO mejora y puede dañar
        # Mantener None para permitir que value function aprenda libremente
        self.clip_range_vf: Optional[float] = None  # DESHABILITADO - daña EV
        
        self.policy_kwargs = {
            # RED MÁS GRANDE para 124-dim obs (Andrychowicz 2021)
            # Actor y Critic SEPARADOS para mejor aprendizaje del value function
            'net_arch': dict(
                pi=[256, 256],  # Actor: 2 capas de 256
                vf=[512, 512]   # Critic: 2 capas de 512 (MÁS GRANDE para EV positivo)
            ),
            'activation_fn': torch.nn.Tanh,  # Tanh mejor que ReLU para PPO (bounded)
            # Inicialización ortogonal (Engstrom 2020: mejora convergencia value function)
            'ortho_init': True,
        }

# ============================================================================
# CONSTANTES OE2 v5.2 (Iquitos, Perú) - 2026-02-12
# ============================================================================
CO2_FACTOR_IQUITOS = 0.4521  # kg CO2/kWh - factor de emisión grid Iquitos
BESS_CAPACITY_KWH = 940.0    # 940 kWh (exclusivo EV, 100% cobertura)
BESS_MAX_KWH = BESS_CAPACITY_KWH  # Alias para compatibilidad v5.3
BESS_MAX_POWER_KW = 342.0    # 342 kW potencia máxima BESS

# ============================================================================
# CONSTANTES DE NORMALIZACIÓN (CRÍTICO para PPO - Engstrom 2020)
# ============================================================================
# Las observaciones DEBEN estar normalizadas a ~[0,1] para que el value function
# pueda aprender. Sin normalización, PPO sufre de:
# - Explained Variance negativo (value function no predice nada)
# - KL divergence explosiva (política cambia erráticamente)
# - Value Loss muy alto (gradientes inestables)
# 
# Valores de normalización basados en datos OE2 Iquitos:
SOLAR_MAX_KW = 4100.0        # 4,050 kWp instalado + margen
MALL_MAX_KW = 150.0          # Demanda máxima mall ~100 kW + margen
CHARGER_MAX_KW = 10.0        # Por socket: 7.4 kW nominal + margen
CHARGER_MEAN_KW = 4.6        # Consumo promedio por socket (kW)
DEMAND_MAX_KW = 300.0        # Demanda total máxima esperada

# DIRECTORIOS DE SALIDA
OUTPUT_DIR = Path('outputs/ppo_training')
CHECKPOINT_DIR = Path('checkpoints/PPO')
OE3_OUTPUT_DIR = Path('data/interim/oe3')

# ============================================================================
# FUNCIONES DE PREPARACIÓN - DATASET Y CHECKPOINTS
# ============================================================================

def validate_oe2_datasets() -> Dict[str, Any]:
    """
    Validar y cargar los 5 datasets OE2 obligatorios.
    
    SINCRONIZACIÓN DATASET_BUILDER v5.5:
    ================================================================================
    Esta función valida que TODOS los datasets considerados en dataset_builder.py
    estén disponibles y con las columnas observables correctas:
    
    CHARGERS (10 cols): Sockets 000-037 (38 total)
      - Columnas "ev_*": is_hora_punta, tarifa_aplicada_soles, energia_total_kwh,
        costo_carga_soles, energia_motos_kwh, energia_mototaxis_kwh,
        co2_reduccion_motos_kg (0.87/kWh), co2_reduccion_mototaxis_kg (0.47/kWh),
        reduccion_directa_co2_kg, demand_kwh
      - Archivo: chargers_ev_ano_2024_v3.csv (353 columnas, 8760 horas)
    
    SOLAR (6 cols): 4,050 kWp
      - Columnas "solar_*": is_hora_punta, tarifa_aplicada_soles, ahorro_soles,
        reduccion_indirecta_co2_kg (0.4521/kWh), co2_mall_kg (67%), co2_ev_kg (33%)
      - Archivo: pv_generation_citylearn2024.csv (8760 horas)
    
    BESS (5 cols): 1,700 kWh, 400 kW v5.5 NEW
      - Columnas "bess_*": soc_percent (20-100%), charge_kwh, discharge_kwh,
        to_mall_kwh, to_ev_kwh
      - Archivo: bess_ano_2024.csv (8760 horas)
    
    MALL (3 cols): Demanda edificio commercial v5.5 NEW
      - Columnas "mall_*": demand_kwh, demand_reduction_kwh, cost_soles
      - Archivo: demandamallhorakwh.csv (8760 horas)
    
    TARIFFS Y CONSTANTS:
      - HP (hora punta 18-23h): 0.45 S/./kWh
      - HFP (fuera punta): 0.28 S/./kWh
      - CO2 carbon intensity: 0.4521 kg CO2/kWh (red térmica Iquitos)
    
    METADATA DE ESCENARIOS (data/oe2/chargers/) v5.5:
      - selection_pe_fc_completo.csv: 54 escenarios (pe, fc, chargers_required, etc.)
      - tabla_escenarios_detallados.csv: CONSERVADOR, MEDIANO, RECOMENDADO*, MÁXIMO
      - tabla_estadisticas_escenarios.csv: Estadísticas agregadas
      - escenarios_tabla13.csv: 101 escenarios PE/FC
      → Cargar con: data_loader.load_scenarios_metadata()
      → ESCENARIO RECOMENDADO v5.5: PE=1.00, FC=1.00, 19 cargadores, 38 tomas, 1129 kWh/día
    
    El agente PPO recibe observaciones de TODAS ESTAS COLUMNAS para entrenar.
    ================================================================================
    """
    print('=' * 80)
    print('[PRE-PASO] VALIDAR SINCRONIZACION CON 5 DATASETS OE2')
    print('=' * 80)

    OE2_FILES = {
        'solar': Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv'),
        'chargers_hourly': Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),
        'chargers_stats': Path('data/oe2/chargers/chargers_real_statistics.csv'),
        'bess': Path('data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv'),
        'mall_demand': Path('data/oe2/demandamallkwh/demandamallhorakwh.csv'),
    }

    oe2_validation_ok = True
    oe2_summary = {}

    for name, path in OE2_FILES.items():
        if path.exists():
            df = pd.read_csv(path, nrows=5, sep=';' if 'mall' in name else ',')
            rows = len(pd.read_csv(path, sep=';' if 'mall' in name else ','))
            cols = len(df.columns)
            oe2_summary[name] = {'rows': rows, 'cols': cols, 'path': path}
            status = 'OK' if rows >= 8760 or name == 'chargers_stats' else 'WARN'
            print(f'  [{status}] {name}: {rows:,} filas x {cols} columnas ({path.name})')
        else:
            print(f'  [ERROR] {name}: NO ENCONTRADO ({path})')
            oe2_validation_ok = False

    if not oe2_validation_ok:
        raise FileNotFoundError('Faltan archivos OE2 obligatorios. Ver errores arriba.')

    print()
    print('  SINCRONIZACION OE2 -> CityLearn:')
    print(f'    Solar PVGIS:          {oe2_summary["solar"]["rows"]:,} horas')
    print(f'    Chargers 38 sockets:          {oe2_summary["chargers_hourly"]["rows"]:,} horas x 38 sockets (19 chargers × 2)')
    print(f'    BESS SOC:             {oe2_summary["bess"]["rows"]:,} horas')
    print(f'    Mall Demand:          {oe2_summary["mall_demand"]["rows"]:,} horas')
    print('  [OK] Todos los datasets OE2 sincronizados')
    print('=' * 80)
    print()
    
    return oe2_summary


def clean_checkpoints_ppo() -> None:
    """Limpiar checkpoints PPO anteriores para entrenamiento desde cero."""
    print('[PRE-PASO] LIMPIEZA DE CHECKPOINTS PPO')
    print('-' * 80)
    
    if CHECKPOINT_DIR.exists():
        import shutil
        files = list(CHECKPOINT_DIR.glob('*.zip')) + list(CHECKPOINT_DIR.glob('*.json'))
        if files:
            for f in files:
                f.unlink()
            print(f'  Eliminados {len(files)} archivos de checkpoint')
        else:
            print('  No hay checkpoints previos')
    else:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        print('  Directorio de checkpoints creado')
    print()


class CityLearnEnvironment(Env):
    """Environment compatible con Gymnasium para CityLearn v2.

    Basado en el benchmark CityLearn v2 para control multi-agente en sistemas
    de energía. Implementa la API de Gymnasium para compatible con SB3.

    Referencias:
      - CityLearn v2 Documentation: https://github.com/intelligent-environments-lab/CityLearn
      - Gymnasium API: https://gymnasium.farama.org/

    Observation Space (156-dim v5.3 - COMUNICACIÓN COMPLETA):
    ================================================================
    ENERGÍA DEL SISTEMA [0-7]:
    - [0]: Solar generation normalizado [0,1]
    - [1]: Mall demand normalizado [0,1]
    - [2]: BESS SOC normalizado [0,1]
    - [3]: BESS energía disponible para descarga (kWh norm)
    - [4]: Solar excedente disponible para carga (kWh norm)
    - [5]: Grid import actual normalizado [0,1]
    - [6]: Balance energético (solar - demanda) normalizado
    - [7]: Capacidad total de carga disponible normalizada
    
    ESTADO DE CARGADORES POR SOCKET [8-45] (38 sockets):
    - Demanda actual de cada socket normalizada [0,1]
    
    POTENCIA ACTUAL POR SOCKET [46-83] (38 sockets):
    - Potencia entregada a cada socket normalizada [0,1]
    
    OCUPACIÓN POR SOCKET [84-121] (38 sockets):
    - 1.0 si hay vehículo conectado, 0.0 si libre
    
    ESTADO DE VEHÍCULOS [122-137] (16 features):
    - [122]: Motos cargando actualmente (count/30)
    - [123]: Mototaxis cargando actualmente (count/8)  
    - [124]: Motos en cola esperando (count/100)
    - [125]: Mototaxis en cola esperando (count/20)
    - [126]: SOC promedio motos cargando [0,1]
    - [127]: SOC promedio mototaxis cargando [0,1]
    - [128]: Tiempo restante carga motos (horas norm)
    - [129]: Tiempo restante carga mototaxis (horas norm)
    - [130]: Sockets motos disponibles (count/30)
    - [131]: Sockets mototaxis disponibles (count/8)
    - [132]: Motos cargadas 100% hoy (count/270)
    - [133]: Mototaxis cargados 100% hoy (count/39)
    - [134]: Eficiencia carga actual [0,1]
    - [135]: Ratio solar usado para carga [0,1]
    - [136]: CO2 evitado acumulado (norm)
    - [137]: CO2 evitado potencial si carga más (norm)
    
    TIME FEATURES [138-143] (6 features):
    - [138]: Hora del día normalizada [0,1]
    - [139]: Día de semana normalizado [0,1]
    - [140]: Mes normalizado [0,1]
    - [141]: Indicador hora pico [0,1]
    - [142]: Factor CO2 Iquitos
    - [143]: Tarifa eléctrica (USD/kWh)
    
    COMUNICACIÓN INTER-SISTEMA [144-155] (12 features):
    - [144]: BESS puede suministrar a EVs [0,1]
    - [145]: Solar suficiente para demanda EV [0,1]
    - [146]: Grid necesario para completar carga [0,1]
    - [147]: Prioridad carga motos vs mototaxis [0,1]
    - [148]: Urgencia de carga (vehículos pendientes/capacidad)
    - [149]: Oportunidad solar (excedente/demanda EV)
    - [150]: BESS debería cargar (solar alto, demanda baja)
    - [151]: BESS debería descargar (solar bajo, demanda alta)
    - [152]: Potencial reducción CO2 con más carga
    - [153]: Saturación del sistema [0,1]
    - [154]: Eficiencia sistema completo [0,1]
    - [155]: Meta diaria de vehículos (progreso [0,1])

    Action Space (129-dim REAL v5.2):
    - [0]: BESS control [0,1] (0=carga máx, 0.5=idle, 1=descarga máx)
    - [1:39]: 38 socket setpoints [0,1] (potencia asignada a cada socket)
    """

    HOURS_PER_YEAR: int = 8760  # Constant for year length
    NUM_CHARGERS: int = 38      # OE2 v5.2: 19 chargers × 2 sockets
    OBS_DIM: int = 156          # OE2: 8 + 38*3 + 1 + 6 + 12 = 156
    ACTION_DIM: int = 39        # OE2: 1 BESS + 38 sockets

    metadata = {'render_modes': []}

    def __init__(
        self,
        reward_calc,
        context,
        solar_kw: np.ndarray,
        chargers_kw: np.ndarray,
        mall_kw: np.ndarray,
        bess_soc: np.ndarray,
        charger_max_power_kw: Optional[np.ndarray] = None,
        charger_mean_power_kw: Optional[np.ndarray] = None,
        max_steps: int = HOURS_PER_YEAR
    ):
        """
        Inicializa environment con datos OE2 reales.

        Args:
            reward_calc: Función de recompensa multiobjetivo
            context: Contexto OE2 (CO2, tariffs, etc)
            solar_kw: Array solar generation (8760,)
            chargers_kw: Array charger demands (8760, n_chargers)
            mall_kw: Array mall demand (8760,)
            bess_soc: Array BESS SOC (8760,)
            charger_max_power_kw: (38,) potencia máxima por socket desde chargers_real_statistics.csv
            charger_mean_power_kw: (38,) potencia media por socket desde chargers_real_statistics.csv
            max_steps: Duración episodio en timesteps
        """
        super().__init__()

        self.reward_calc = reward_calc
        self.context = context

        # DATOS REALES (8760 horas = 1 año)
        self.solar_hourly = np.asarray(solar_kw, dtype=np.float32)
        self.chargers_hourly = np.asarray(chargers_kw, dtype=np.float32)
        self.mall_hourly = np.asarray(mall_kw, dtype=np.float32)
        self.bess_soc_hourly = np.asarray(bess_soc, dtype=np.float32)
        
        # ESTADISTICAS REALES DE CARGADORES (5to dataset OE2)
        # Usadas para escalar acciones según capacidad real de cada socket
        if charger_max_power_kw is not None:
            self.charger_max_power = np.asarray(charger_max_power_kw, dtype=np.float32)
        else:
            # Fallback v5.2: 7.4 kW por socket (Modo 3 monofásico 32A @ 230V)
            self.charger_max_power = np.full(self.NUM_CHARGERS, 7.4, dtype=np.float32)
            
        if charger_mean_power_kw is not None:
            self.charger_mean_power = np.asarray(charger_mean_power_kw, dtype=np.float32)
        else:
            # Fallback v5.2: potencia efectiva = 7.4 × 0.62 = 4.6 kW 
            self.charger_mean_power = np.full(self.NUM_CHARGERS, 4.6, dtype=np.float32)

        # Validación de datos
        if len(self.solar_hourly) != self.HOURS_PER_YEAR:
            raise ValueError(f"Solar data must be {self.HOURS_PER_YEAR} hours, got {len(self.solar_hourly)}")
        if len(self.mall_hourly) != self.HOURS_PER_YEAR:
            raise ValueError(f"Mall data must be {self.HOURS_PER_YEAR} hours, got {len(self.mall_hourly)}")
        if len(self.bess_soc_hourly) != self.HOURS_PER_YEAR:
            raise ValueError(f"BESS data must be {self.HOURS_PER_YEAR} hours, got {len(self.bess_soc_hourly)}")
        if self.chargers_hourly.shape[0] != self.HOURS_PER_YEAR:
            raise ValueError(f"Chargers data must be {self.HOURS_PER_YEAR} hours, got {self.chargers_hourly.shape[0]}")

        self.max_steps = self.HOURS_PER_YEAR  # [OK] FORZAR 8760 timesteps (episodios completos de 1 año)
        self.n_chargers = self.chargers_hourly.shape[1]

        # Espacios (Gymnasium API)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.OBS_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.ACTION_DIM,), dtype=np.float32
        )

        # STATE TRACKING
        self.step_count = 0
        self.episode_num = 0
        self.episode_reward = 0.0
        self.episode_co2_avoided = 0.0
        self.episode_solar_kwh = 0.0
        self.episode_grid_import = 0.0
        self.episode_ev_satisfied = 0.0
        
        # [v5.3] TRACKING DE VEHÍCULOS CARGANDO EN TIEMPO REAL
        self.motos_charging_now: int = 0        # Motos actualmente cargando
        self.mototaxis_charging_now: int = 0    # Mototaxis actualmente cargando
        self.motos_waiting: int = 0             # Motos en cola
        self.mototaxis_waiting: int = 0         # Mototaxis en cola
        self.motos_soc_avg: float = 0.0         # SOC promedio motos cargando
        self.mototaxis_soc_avg: float = 0.0     # SOC promedio mototaxis cargando
        self.motos_time_remaining: float = 0.0  # Tiempo restante carga motos (horas)
        self.mototaxis_time_remaining: float = 0.0  # Tiempo restante carga mototaxis
        self.motos_charged_today: int = 0       # Motos cargadas 100% hoy
        self.mototaxis_charged_today: int = 0   # Mototaxis cargados 100% hoy
        self.daily_co2_avoided: float = 0.0     # CO2 evitado hoy (kg)
        self.episode_ev_energy_charged_kwh: float = 0.0  # v5.5: Total energía EV
        self.episode_bess_discharged_kwh: float = 0.0    # v5.5: Total BESS descarga
        self.episode_bess_charged_kwh: float = 0.0       # v5.5: Total BESS carga
        
        # [v5.3] COMUNICACIÓN INTER-SISTEMA
        self.bess_available_kwh: float = 0.0    # Energía BESS disponible
        self.solar_surplus_kwh: float = 0.0     # Excedente solar
        self.current_grid_import: float = 0.0   # Import grid actual
        self.system_efficiency: float = 0.0    # Eficiencia del sistema
        
        # [v5.5] TRACKING DE VEHICULOS POR SOC - cambiar a SUM acumulado (no MAX)
        self.episode_motos_10_max: int = 0
        self.episode_motos_20_max: int = 0
        self.episode_motos_30_max: int = 0
        self.episode_motos_50_max: int = 0
        self.episode_motos_70_max: int = 0
        self.episode_motos_80_max: int = 0
        self.episode_motos_100_max: int = 0
        
        self.episode_taxis_10_max: int = 0
        self.episode_taxis_20_max: int = 0
        self.episode_taxis_30_max: int = 0
        self.episode_taxis_50_max: int = 0
        self.episode_taxis_70_max: int = 0
        self.episode_taxis_80_max: int = 0
        self.episode_taxis_100_max: int = 0
        
        # Simulador de escenarios de carga
        self.vehicle_simulator = VehicleChargingSimulator()
        # Seleccionar escenario basado en hora (hora del año -> mapear a escenario)
        self.scenarios_by_hour = self._create_hour_scenarios()
    
    def _create_hour_scenarios(self) -> Dict[int, VehicleChargingScenario]:
        """Mapea cada hora del año a un escenario de carga realista de Iquitos."""
        scenarios = {}
        for h in range(self.HOURS_PER_YEAR):
            hour_of_day = h % 24
            
            # Off-peak: 2-6 AM
            if 2 <= hour_of_day < 6:
                scenarios[h] = SCENARIO_OFF_PEAK
            # Morning: 6-14 (bajo a moderado)
            elif 6 <= hour_of_day < 14:
                scenarios[h] = SCENARIO_PEAK_AFTERNOON
            # Afternoon: 14-18 (carga rápida, moderada)
            elif 14 <= hour_of_day < 18:
                scenarios[h] = SCENARIO_PEAK_AFTERNOON
            # Evening: 18-23 (pico máximo)
            elif 18 <= hour_of_day <= 22:
                scenarios[h] = SCENARIO_EXTREME_PEAK if (19 <= hour_of_day <= 20) else SCENARIO_PEAK_EVENING
            # Noche: 23-2 (bajo)
            else:
                scenarios[h] = SCENARIO_OFF_PEAK
        
        return scenarios

    def _make_observation(self, hour_idx: int) -> np.ndarray:
        """
        Crea observación v5.3 (156-dim) con COMUNICACIÓN COMPLETA del sistema.

        NORMALIZACIÓN CRÍTICA [Engstrom 2020 "Implementation Matters"]:
        ================================================================
        Todas las features están en rango ~[0,1] para estabilidad del training.
        
        COMUNICACIÓN DEL SISTEMA:
        - El agente ve el estado completo de BESS, Solar, EVs, Cargadores
        - Puede coordinar carga de motos/mototaxis con disponibilidad solar
        - Sabe cuántos vehículos están cargando y cuántos faltan
        - Recibe señales de urgencia y oportunidad
        """
        obs = np.zeros(self.OBS_DIM, dtype=np.float32)
        h = hour_idx % self.HOURS_PER_YEAR
        hour_24 = h % 24
        day_of_year = (h // 24) % 365

        # ================================================================
        # [0-7] ENERGÍA DEL SISTEMA (8 features)
        # ================================================================
        solar_kw = float(self.solar_hourly[h])
        mall_kw = float(self.mall_hourly[h])
        bess_soc = float(self.bess_soc_hourly[h])
        
        # Calcular balance energético
        ev_demand_estimate = float(np.sum(self.chargers_hourly[h]))
        total_demand = mall_kw + ev_demand_estimate
        solar_surplus = max(0.0, solar_kw - total_demand)
        grid_import_needed = max(0.0, total_demand - solar_kw)
        
        # BESS energía disponible (SOC × capacidad máx × eficiencia)
        bess_energy_available = bess_soc * BESS_MAX_KWH * 0.90  # 90% eficiencia
        
        obs[0] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)                    # Solar norm
        obs[1] = np.clip(mall_kw / MALL_MAX_KW, 0.0, 1.0)                      # Mall demand
        obs[2] = np.clip(bess_soc, 0.0, 1.0)                                   # BESS SOC
        obs[3] = np.clip(bess_energy_available / BESS_MAX_KWH, 0.0, 1.0)       # BESS disponible
        obs[4] = np.clip(solar_surplus / SOLAR_MAX_KW, 0.0, 1.0)               # Solar excedente
        obs[5] = np.clip(grid_import_needed / 500.0, 0.0, 1.0)                 # Grid import
        obs[6] = np.clip((solar_kw - total_demand) / SOLAR_MAX_KW + 0.5, 0.0, 1.0)  # Balance
        obs[7] = np.clip(1.0 - ev_demand_estimate / (self.NUM_CHARGERS * CHARGER_MAX_KW), 0.0, 1.0)  # Capacidad libre

        # ================================================================
        # [8-45] DEMANDA POR SOCKET (38 features)
        # ================================================================
        if self.chargers_hourly.shape[1] >= self.NUM_CHARGERS:
            raw_demands = self.chargers_hourly[h, :self.NUM_CHARGERS]
        else:
            raw_demands = np.zeros(self.NUM_CHARGERS, dtype=np.float32)
            raw_demands[:self.chargers_hourly.shape[1]] = self.chargers_hourly[h]
        
        obs[8:46] = np.clip(raw_demands / CHARGER_MAX_KW, 0.0, 1.0)

        # ================================================================
        # [46-83] POTENCIA ACTUAL POR SOCKET (38 features)
        # ================================================================
        # Potencia = 50-80% de demanda según hora (eficiencia variable)
        efficiency_factor = 0.7 if 6 <= hour_24 <= 22 else 0.5
        obs[46:84] = obs[8:46] * efficiency_factor

        # ================================================================
        # [84-121] OCUPACIÓN POR SOCKET (38 features)
        # ================================================================
        # Basado en demanda: si hay demanda > 0.1, está ocupado
        occupancy = (raw_demands > 0.1).astype(np.float32)
        obs[84:122] = occupancy

        # ================================================================
        # [122-137] ESTADO DE VEHÍCULOS (16 features) - CRÍTICO PARA APRENDIZAJE
        # ================================================================
        # Contar vehículos cargando (sockets ocupados)
        motos_sockets = occupancy[:30]  # Primeros 30 sockets = motos
        taxis_sockets = occupancy[30:]  # Últimos 8 sockets = mototaxis
        
        self.motos_charging_now = int(np.sum(motos_sockets))
        self.mototaxis_charging_now = int(np.sum(taxis_sockets))
        
        # Estimar vehículos en cola según hora pico
        if 6 <= hour_24 <= 22:
            self.motos_waiting = max(0, int(270 / 24 - self.motos_charging_now))  # ~11 motos/hora
            self.mototaxis_waiting = max(0, int(39 / 24 - self.mototaxis_charging_now))  # ~2 mototaxis/hora
        else:
            self.motos_waiting = 0
            self.mototaxis_waiting = 0
        
        # SOC promedio (basado en potencia entregada)
        motos_power = obs[46:76]  # Potencias motos
        taxis_power = obs[76:84]  # Potencias mototaxis
        self.motos_soc_avg = float(np.mean(motos_power)) if self.motos_charging_now > 0 else 0.0
        self.mototaxis_soc_avg = float(np.mean(taxis_power)) if self.mototaxis_charging_now > 0 else 0.0
        
        # Tiempo restante de carga (horas estimadas)
        # Moto: 3.5 kWh batería / 4.6 kW promedio = 0.76 horas
        # Mototaxi: 5.5 kWh batería / 4.6 kW promedio = 1.2 horas
        self.motos_time_remaining = (1.0 - self.motos_soc_avg) * 0.76
        self.mototaxis_time_remaining = (1.0 - self.mototaxis_soc_avg) * 1.2
        
        # Sockets disponibles
        motos_available = 30 - self.motos_charging_now
        taxis_available = 8 - self.mototaxis_charging_now
        
        # Progreso diario (resetea cada 24 horas)
        hour_in_day = h % 24
        if hour_in_day == 0:
            self.motos_charged_today = 0
            self.mototaxis_charged_today = 0
            self.daily_co2_avoided = 0.0
        
        # Estimar vehículos completados (acumulativo aproximado)
        vehicles_per_hour = max(1, self.motos_charging_now // 2)  # ~50% completan por hora
        taxis_per_hour = max(0, self.mototaxis_charging_now // 3)
        self.motos_charged_today += vehicles_per_hour
        self.mototaxis_charged_today += taxis_per_hour
        
        # Eficiencia y ratios
        total_ev_power = float(np.sum(raw_demands))
        solar_for_ev_ratio = min(1.0, solar_kw / max(1.0, total_ev_power)) if total_ev_power > 0 else 0.0
        charge_efficiency = float(np.sum(obs[46:84])) / max(1.0, float(np.sum(obs[8:46])))
        
        # CO2 potencial
        co2_potential = (motos_available + taxis_available) * 4.6 * CO2_FACTOR_IQUITOS  # kWh × factor
        
        obs[122] = self.motos_charging_now / 30.0                                # Motos cargando
        obs[123] = self.mototaxis_charging_now / 8.0                             # Mototaxis cargando
        obs[124] = np.clip(self.motos_waiting / 100.0, 0.0, 1.0)                 # Motos en cola
        obs[125] = np.clip(self.mototaxis_waiting / 20.0, 0.0, 1.0)              # Mototaxis en cola
        obs[126] = self.motos_soc_avg                                            # SOC promedio motos
        obs[127] = self.mototaxis_soc_avg                                        # SOC promedio mototaxis
        obs[128] = np.clip(self.motos_time_remaining / 2.0, 0.0, 1.0)            # Tiempo restante motos
        obs[129] = np.clip(self.mototaxis_time_remaining / 2.0, 0.0, 1.0)        # Tiempo restante taxis
        obs[130] = motos_available / 30.0                                        # Sockets motos libres
        obs[131] = taxis_available / 8.0                                         # Sockets taxis libres
        obs[132] = np.clip(self.motos_charged_today / 270.0, 0.0, 1.0)           # Motos cargadas hoy
        obs[133] = np.clip(self.mototaxis_charged_today / 39.0, 0.0, 1.0)        # Taxis cargados hoy
        obs[134] = np.clip(charge_efficiency, 0.0, 1.0)                          # Eficiencia carga
        obs[135] = solar_for_ev_ratio                                            # Ratio solar→EV
        obs[136] = np.clip(self.daily_co2_avoided / 500.0, 0.0, 1.0)             # CO2 evitado hoy
        obs[137] = np.clip(co2_potential / 100.0, 0.0, 1.0)                      # CO2 potencial

        # ================================================================
        # [138-143] TIME FEATURES (6 features)
        # ================================================================
        obs[138] = float(hour_24) / 24.0                                         # Hora
        obs[139] = float(day_of_year % 7) / 7.0                                  # Día semana
        obs[140] = float((day_of_year // 30) % 12) / 12.0                        # Mes
        obs[141] = 1.0 if 6 <= hour_24 <= 22 else 0.0                            # Hora pico
        obs[142] = float(self.context.co2_factor_kg_per_kwh)                     # Factor CO2
        obs[143] = 0.15                                                          # Tarifa

        # ================================================================
        # [144-155] COMUNICACIÓN INTER-SISTEMA (12 features) - SEÑALES DE COORDINACIÓN
        # ================================================================
        # BESS puede suministrar a EVs?
        bess_can_supply = 1.0 if bess_energy_available > total_ev_power else bess_energy_available / max(1.0, total_ev_power)
        
        # Solar suficiente para EV?
        solar_sufficient = 1.0 if solar_kw >= total_ev_power else solar_kw / max(1.0, total_ev_power)
        
        # Grid necesario?
        grid_needed_ratio = grid_import_needed / max(1.0, total_ev_power) if total_ev_power > 0 else 0.0
        
        # Prioridad motos vs mototaxis (motos tienen prioridad si hay más esperando)
        priority_motos = self.motos_waiting / max(1, self.motos_waiting + self.mototaxis_waiting) if (self.motos_waiting + self.mototaxis_waiting) > 0 else 0.5
        
        # Urgencia de carga
        total_waiting = self.motos_waiting + self.mototaxis_waiting
        total_capacity = motos_available + taxis_available
        urgency = total_waiting / max(1, total_capacity) if total_capacity > 0 else 0.0
        
        # Oportunidad solar
        solar_opportunity = solar_surplus / max(1.0, total_ev_power) if total_ev_power > 0 else 1.0
        
        # BESS debería cargar? (solar alto, demanda baja)
        should_charge_bess = 1.0 if (solar_surplus > 100 and bess_soc < 0.8) else 0.0
        
        # BESS debería descargar? (solar bajo, demanda alta, SOC alto)
        should_discharge_bess = 1.0 if (solar_kw < total_demand * 0.5 and bess_soc > 0.3) else 0.0
        
        # Potencial reducción CO2 si cargamos más
        co2_reduction_potential = (motos_available + taxis_available) * CHARGER_MEAN_KW * CO2_FACTOR_IQUITOS / 100.0
        
        # Saturación del sistema
        saturation = (self.motos_charging_now + self.mototaxis_charging_now) / self.NUM_CHARGERS
        
        # Eficiencia sistema completo
        total_input = solar_kw + bess_energy_available / 10.0  # Energía disponible
        total_output = total_ev_power  # Energía usada
        system_eff = min(1.0, total_output / max(1.0, total_input))
        
        # Meta diaria (270 motos + 39 mototaxis = 309 vehículos/día)
        daily_target = 309
        daily_progress = (self.motos_charged_today + self.mototaxis_charged_today) / daily_target
        
        obs[144] = np.clip(bess_can_supply, 0.0, 1.0)                            # BESS→EV
        obs[145] = np.clip(solar_sufficient, 0.0, 1.0)                           # Solar→EV
        obs[146] = np.clip(grid_needed_ratio, 0.0, 1.0)                          # Grid necesario
        obs[147] = priority_motos                                                 # Prioridad motos
        obs[148] = np.clip(urgency, 0.0, 1.0)                                    # Urgencia
        obs[149] = np.clip(solar_opportunity, 0.0, 1.0)                          # Oportunidad solar
        obs[150] = should_charge_bess                                            # BESS cargar
        obs[151] = should_discharge_bess                                         # BESS descargar
        obs[152] = np.clip(co2_reduction_potential, 0.0, 1.0)                    # CO2 potencial
        obs[153] = saturation                                                     # Saturación
        obs[154] = system_eff                                                     # Eficiencia
        obs[155] = np.clip(daily_progress, 0.0, 1.0)                             # Progreso meta

        return obs

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset para nuevo episodio."""
        # seed y options son parte de la API Gymnasium pero no se usan aquí
        del seed, options  # Marcar como usados para evitar warnings
        self.step_count = 0
        self.episode_num += 1
        self.episode_reward = 0.0
        self.episode_co2_avoided = 0.0
        self.episode_solar_kwh = 0.0
        self.episode_grid_import = 0.0
        self.episode_ev_satisfied = 0.0
        
        # [v5.3] RESET ESTADO DE VEHÍCULOS
        self.motos_charging_now = 0
        self.mototaxis_charging_now = 0
        self.motos_waiting = 0
        self.mototaxis_waiting = 0
        self.motos_soc_avg = 0.0
        self.mototaxis_soc_avg = 0.0
        self.motos_time_remaining = 0.0
        self.mototaxis_time_remaining = 0.0
        self.motos_charged_today = 0
        self.mototaxis_charged_today = 0
        self.daily_co2_avoided = 0.0
        self.episode_ev_energy_charged_kwh = 0.0  # NUEVO: Total energía cargada en el episodio
        self.episode_bess_discharged_kwh = 0.0   # NUEVO: Total descargado BESS
        self.episode_bess_charged_kwh = 0.0      # NUEVO: Total cargado en BESS
        
        # [v5.3] RESET COMUNICACIÓN INTER-SISTEMA
        self.bess_available_kwh = 0.0
        self.solar_surplus_kwh = 0.0
        self.current_grid_import = 0.0
        self.system_efficiency = 0.0
        
        # [v5.5] RESET SOC TRACKERS - cambiar a SUM en lugar de MAX
        self.episode_motos_10_sum = 0.0  # Total acumulado, no max de una hora
        self.episode_motos_20_sum = 0.0
        self.episode_motos_30_sum = 0.0
        self.episode_motos_50_sum = 0.0
        self.episode_motos_70_sum = 0.0
        self.episode_motos_80_sum = 0.0
        self.episode_motos_100_sum = 0.0
        
        self.episode_taxis_10_sum = 0.0  # Total acumulado, no max de una hora
        self.episode_taxis_20_sum = 0.0
        self.episode_taxis_30_sum = 0.0
        self.episode_taxis_50_sum = 0.0
        self.episode_taxis_70_sum = 0.0
        self.episode_taxis_80_sum = 0.0
        self.episode_taxis_100_sum = 0.0

        obs = self._make_observation(0)
        return obs, {}

    def render(self):
        """Render method (required by Gymnasium Env base class)."""
        return None

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Ejecuta un paso de SIMULACION (1 hora).

        Implementa el protocolo de paso de Gymnasium. El agente envía setpoints
        de potencia normalizados que son procesados a través del sistema de energía.

        Referencias:
          - Gymnasium Protocol: https://gymnasium.farama.org/api/core/
          - Energy system dynamics from CityLearn v2
        """
        self.step_count += 1
        h = (self.step_count - 1) % self.HOURS_PER_YEAR

        # DATOS REALES (OE2 timeseries)
        solar_kw = float(self.solar_hourly[h])
        mall_kw = float(self.mall_hourly[h])
        charger_demand = self.chargers_hourly[h].astype(np.float32)
        bess_soc = np.clip(float(self.bess_soc_hourly[h]), 0.0, 1.0)

        # PROCESAR ACCION (39-dim OE2: 1 BESS + 38 sockets)
        bess_action = np.clip(action[0], 0.0, 1.0)  # BESS control
        charger_setpoints = np.clip(action[1:self.ACTION_DIM], 0.0, 1.0)

        # CALCULAR ENERGIA (balance de carga)
        # Usar max_power real de cada socket (del 5to dataset OE2)
        # para escalar setpoints a potencia efectiva
        charger_power_effective = charger_setpoints * self.charger_max_power[:38]
        ev_charging_kwh = float(np.sum(np.minimum(charger_power_effective, charger_demand)))
        total_demand_kwh = mall_kw + ev_charging_kwh
        
        # BESS power (positivo = descarga, negativo = carga)
        bess_power_kw = (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW
        
        # Separar motos y mototaxis (v5.2: 15 chargers motos × 2 sockets = 30, 4 chargers mototaxis × 2 = 8)
        # Chargers 0-14 = motos (30 sockets), Chargers 15-18 = mototaxis (8 sockets)
        motos_demand = float(np.sum(charger_demand[:30] * charger_setpoints[:30]))
        mototaxis_demand = float(np.sum(charger_demand[30:] * charger_setpoints[30:]))
        
        # CONTEO VEHICULOS CARGANDO (sockets con setpoint > 50%)
        motos_charging = int(np.sum(charger_setpoints[:30] > 0.5))
        mototaxis_charging = int(np.sum(charger_setpoints[30:] > 0.5))

        # GRID BALANCE (importador vs exportador)
        net_demand = total_demand_kwh - bess_power_kw  # BESS descarga reduce demanda
        grid_import_kwh = max(0.0, net_demand - solar_kw)
        grid_export_kwh = max(0.0, solar_kw - net_demand)

        # CO2 CALCULATIONS (Iquitos factor: 0.4521 kg CO2/kWh) - MISMO FLUJO QUE SAC/A2C
        # Factor CO2 gasolina para motos/mototaxis: ~2.31 kg CO2/litro
        GASOLINA_KG_CO2_PER_LITRO_PPO = 2.31
        MOTO_LITROS_PER_100KM_PPO = 2.0
        MOTOTAXI_LITROS_PER_100KM_PPO = 3.0
        MOTO_KM_PER_KWH_PPO = 50.0
        MOTOTAXI_KM_PER_KWH_PPO = 30.0
        
        # Usar proporción real de sockets motos/mototaxis (30 motos + 8 mototaxis = 38)
        moto_ratio_ppo = 30.0 / 38.0
        mototaxi_ratio_ppo = 8.0 / 38.0
        
        # CO2 DIRECTO: Emisiones evitadas por usar EV en lugar de gasolina (MISMO QUE SAC/A2C)
        motos_energy_ppo = ev_charging_kwh * moto_ratio_ppo
        mototaxis_energy_ppo = ev_charging_kwh * mototaxi_ratio_ppo
        
        km_motos_ppo = motos_energy_ppo * MOTO_KM_PER_KWH_PPO
        km_mototaxis_ppo = mototaxis_energy_ppo * MOTOTAXI_KM_PER_KWH_PPO
        
        litros_evitados_motos_ppo = km_motos_ppo * MOTO_LITROS_PER_100KM_PPO / 100.0
        litros_evitados_mototaxis_ppo = km_mototaxis_ppo * MOTOTAXI_LITROS_PER_100KM_PPO / 100.0
        
        co2_avoided_direct_kg = (litros_evitados_motos_ppo + litros_evitados_mototaxis_ppo) * GASOLINA_KG_CO2_PER_LITRO_PPO
        
        # CO2 INDIRECTO: SOLAR + BESS CON PEAK SHAVING (MISMO QUE SAC/A2C)
        co2_grid_kg = grid_import_kwh * CO2_FACTOR_IQUITOS
        
        solar_avoided = min(solar_kw, total_demand_kwh)
        
        # BESS descargando con peak shaving (solo descarga positiva)
        bess_discharge_benefit = max(0.0, bess_power_kw)
        
        if mall_kw > 2000.0:
            # En pico: BESS reemplaza 100% + bonus por reducción de pico diesel
            peak_shaving_factor = 1.0 + (mall_kw - 2000.0) / max(1.0, mall_kw) * 0.5
        else:
            # Baseline: BESS aún ayuda con factor reducido
            peak_shaving_factor = 0.5 + (mall_kw / 2000.0) * 0.5
        
        bess_co2_benefit = bess_discharge_benefit * peak_shaving_factor
        
        co2_avoided_indirect_kg = (solar_avoided + bess_co2_benefit) * CO2_FACTOR_IQUITOS
        co2_avoided_total_kg = co2_avoided_indirect_kg + co2_avoided_direct_kg

        # EV SATISFACTION - MÉTODO REALISTA (similar a SAC)
        # Basado en cuánta carga se está entregando vs la demanda
        if float(np.sum(charger_demand)) > 0.1:
            # Ratio de carga efectiva: cuánto se está cargando vs demanda total
            charge_ratio = ev_charging_kwh / max(1.0, float(np.sum(charger_demand)))
            # EV SOC aumenta con la carga efectiva (baseline 80% + bonus por carga)
            ev_soc_avg = np.clip(0.80 + 0.20 * charge_ratio, 0.0, 1.0)
        else:
            # Sin demanda EV, usar baseline alto (asume EVs ya cargados)
            ev_soc_avg = 0.95
        
        # [OK] SIMULAR CARGA DE VEHICULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
        h = (self.step_count - 1) % self.HOURS_PER_YEAR
        scenario = self.scenarios_by_hour[h]
        
        # v5.6 CORREGIDO: USAR POTENCIA TOTAL DISPONIBLE DEL SISTEMA
        # No solo la potencia controlada por el agente, sino:
        # Solar + BESS + Red (potencia total para cargar vehículos)
        # Esto es más realista: el simulador ve potencia total disponible
        actual_controlled_power_kw = float(np.sum(charger_power_effective[:38]))  # Potencia controlada
        solar_available_kw = max(0.0, solar_kw - mall_kw)  # Solar disponible después de mall
        bess_available_kw = max(0.0, bess_power_kw) if bess_power_kw > 0 else 0.0  # BESS descargando
        grid_available_kw = 500.0  # Capacidad máxima de grid para importar (conservador)
        
        # Potencia TOTAL disponible para carga de vehículos
        total_available_power_kw = actual_controlled_power_kw + solar_available_kw + bess_available_kw + grid_available_kw
        
        # Asegurar un mínimo realista (al menos 50 kW para cargar algo)
        available_power_kw = max(50.0, total_available_power_kw)
        
        # [DEBUG] Imprimir potencias cada 100 steps
        if self.step_count % 100 == 0:
            print(f"[PPO-POWER-DEBUG] Step {self.step_count}: ctrl={actual_controlled_power_kw:.1f}, solar={solar_available_kw:.1f}, bess={bess_available_kw:.1f}, grid={grid_available_kw:.1f}, total={available_power_kw:.1f} kW")
        charging_result = self.vehicle_simulator.simulate_hourly_charge(scenario, available_power_kw)
        
        # Extraer conteos por SOC (valores puede ser int o float según vehicle_simulator)
        motos_10 = charging_result.get('motos_10_percent_charged', 0)  # type: ignore
        motos_20 = charging_result.get('motos_20_percent_charged', 0)  # type: ignore
        motos_30 = charging_result.get('motos_30_percent_charged', 0)  # type: ignore
        motos_50 = charging_result.get('motos_50_percent_charged', 0)  # type: ignore
        motos_70 = charging_result.get('motos_70_percent_charged', 0)  # type: ignore
        motos_80 = charging_result.get('motos_80_percent_charged', 0)  # type: ignore
        motos_100 = charging_result.get('motos_100_percent_charged', 0)  # type: ignore
        
        taxis_10 = charging_result.get('mototaxis_10_percent_charged', 0)  # type: ignore
        taxis_20 = charging_result.get('mototaxis_20_percent_charged', 0)  # type: ignore
        taxis_30 = charging_result.get('mototaxis_30_percent_charged', 0)  # type: ignore
        taxis_50 = charging_result.get('mototaxis_50_percent_charged', 0)  # type: ignore
        taxis_70 = charging_result.get('mototaxis_70_percent_charged', 0)  # type: ignore
        taxis_80 = charging_result.get('mototaxis_80_percent_charged', 0)  # type: ignore
        taxis_100 = charging_result.get('mototaxis_100_percent_charged', 0)  # type: ignore
        
        # [DEBUG] Mostrar conteos cada 500 steps
        if self.step_count % 500 == 0 and (motos_10 + motos_20 + motos_30 + motos_50 + motos_70 + motos_80 + motos_100) > 0:
            print(f"[SOC-COUNT] Step {self.step_count}: motos=[{int(motos_10)},{int(motos_20)},{int(motos_30)},{int(motos_50)},{int(motos_70)},{int(motos_80)},{int(motos_100)}], taxis=[{int(taxis_10)},{int(taxis_20)},{int(taxis_30)},{int(taxis_50)},{int(taxis_70)},{int(taxis_80)},{int(taxis_100)}]")
        
        # v5.5 CORREGIDO: REGISTRAR MÁXIMO SIMULTÁNEO (no acumular)
        # Estos son conteos de vehículos por SOC, no energía
        self.episode_motos_10_max = max(self.episode_motos_10_max, int(motos_10))
        self.episode_motos_20_max = max(self.episode_motos_20_max, int(motos_20))
        self.episode_motos_30_max = max(self.episode_motos_30_max, int(motos_30))
        self.episode_motos_50_max = max(self.episode_motos_50_max, int(motos_50))
        self.episode_motos_70_max = max(self.episode_motos_70_max, int(motos_70))
        self.episode_motos_80_max = max(self.episode_motos_80_max, int(motos_80))
        self.episode_motos_100_max = max(self.episode_motos_100_max, int(motos_100))
        
        self.episode_taxis_10_max = max(self.episode_taxis_10_max, int(taxis_10))
        self.episode_taxis_20_max = max(self.episode_taxis_20_max, int(taxis_20))
        self.episode_taxis_30_max = max(self.episode_taxis_30_max, int(taxis_30))
        self.episode_taxis_50_max = max(self.episode_taxis_50_max, int(taxis_50))
        self.episode_taxis_70_max = max(self.episode_taxis_70_max, int(taxis_70))
        self.episode_taxis_80_max = max(self.episode_taxis_80_max, int(taxis_80))
        self.episode_taxis_100_max = max(self.episode_taxis_100_max, int(taxis_100))
        
        # Acumular energía EV y BESS
        self.episode_ev_energy_charged_kwh += ev_charging_kwh
        if bess_power_kw > 0:
            self.episode_bess_discharged_kwh += bess_power_kw
        
        # [v5.5] BONUS REWARD BASADO EN ENERGÍA CARGADA vs META DIARIA
        # Penalidad si hay demanda pero no se carga al 100%
        total_100_percent = motos_100 + taxis_100
        total_all_chargers = scenario.total_vehicles
        
        # Si no hay demanda, no penalizar; si hay demanda, premiar carga completa
        if total_all_chargers > 0:
            completion_ratio = total_100_percent / max(1, total_all_chargers)
            # Reward bonus: +0.5 si todo se carga al 100%, -0.2 si nada se carga
            ev_completion_bonus = (completion_ratio - 0.5) * 0.4  # Rango [-0.2, +0.2]
        else:
            ev_completion_bonus = 0.0

        # ====================================================================
        # REWARD GRANULAR POR CONTROL INDIVIDUAL DE SOCKETS Y BESS
        # ====================================================================
        # v5.4: SIMPLIFICADO - socket/BESS control es secundario
        # El agente aprenderá las estrategias individuales implícitamente
        # desde el bonus de "vehículos 100% cargados"
        
        # Socket efficiency y BESS control rewards deshabilitados (v5.4)
        # para reducir ruido en la señal de reward
        socket_efficiency_reward = 0.0  # v5.4: Disabled for clarity
        bess_control_reward = 0.0       # v5.4: Disabled for clarity

        # CALCULAR RECOMPENSA MULTIOBJETIVO
        try:
            reward_val, components = self.reward_calc.compute(
                grid_import_kwh=grid_import_kwh,
                grid_export_kwh=grid_export_kwh,
                solar_generation_kwh=solar_kw,
                ev_charging_kwh=ev_charging_kwh,
                ev_soc_avg=ev_soc_avg,
                bess_soc=bess_soc,
                hour=h % 24,
                ev_demand_kwh=50.0
            )
            
            # AGREGAR BONUS POR EV SATISFACTION (igual que SAC)
            # ev_soc_avg está en [0,1], convertir a [-1,1] y ponderar
            ev_bonus = (2.0 * ev_soc_avg - 1.0)  # Escala [-1, 1]
            
            # ================================================================
            # REWARD COMPOSITION v5.5: BASADO EN ENERGÍA CARGADA (más científico)
            # ================================================================
            # OBJETIVO ÚNICO: Maximizar energía entregada a vehículos
            # 
            # Meta diaria: 270 motos × 3.5 kWh + 39 mototaxis × 5.5 kWh = 1,160 kWh/día
            # Promedio por hora: 1,160 / 24 ≈ 48 kWh/hora
            # Bonus: (ev_energy / 48) normalizado, máx +1.0 si cargamos 48+ kWh/hora
            # ================================================================
            
            # BONUS POR ENERGÍA CARGADA (PRIMARIO - v5.5)
            # Este es el indicador más directo del éxito de la misión
            EV_ENERGY_GOAL_KWH_PER_HOUR = 48.0  # Meta base: 1,160 kWh/día ÷ 24 horas
            energy_charging_ratio = np.clip(ev_charging_kwh / EV_ENERGY_GOAL_KWH_PER_HOUR, 0.0, 1.5)
            energy_charging_bonus = (energy_charging_ratio - 0.5) * 1.2  # [-0.6, +0.9] rango
            
            # Secundario: Ocupación de sockets (indica potencial de carga)
            vehicles_charging_now = motos_charging + mototaxis_charging
            vehicles_charging_ratio = vehicles_charging_now / self.NUM_CHARGERS  # [0, 1]
            vehicles_charging_bonus = vehicles_charging_ratio * 0.40  # Secundaria: +0 a +0.4
            
            # Terciario: Carga completa (calidad de carga)
            if total_all_chargers > 0:
                completion_100_ratio = total_100_percent / max(1, total_all_chargers)
                # v5.4: AUMENTADO - bonus escalonado: +0.42 si 100%, -0.126 si 0%
                vehicles_100_bonus = (completion_100_ratio - 0.3) * 0.6  # [-0.18, +0.42]
            else:
                vehicles_100_bonus = 0.0
                
            # 3. BONUS POR CO2 EVITADO (directo + indirecto)
            # Normalizado: 500 kg CO2/hora sería excelente (toda la capacidad con solar)
            co2_bonus = np.clip(co2_avoided_total_kg / 100.0, -0.1, 0.2)  # [-0.1, +0.2]
            
            # 4. PENALIDAD POR GRID IMPORT ALTO
            # Si importamos mucho del grid, no estamos usando solar para EVs
            grid_penalty = -np.clip(grid_import_kwh / 500.0, 0.0, 0.15)  # [0, -0.15]
            
            # 5. BONUS POR USAR SOLAR PARA CARGAR EVs
            # Si el solar va directo a EVs, maximizamos reducción CO2 indirecto
            solar_used_for_ev = min(solar_kw, ev_charging_kwh)  # kWh solar→EV
            solar_ev_ratio = solar_used_for_ev / max(1.0, solar_kw) if solar_kw > 10 else 0.0
            solar_ev_bonus = solar_ev_ratio * 0.1  # Hasta +0.1
            
            # ================================================================
            # COMPOSICIÓN FINAL DEL REWARD v5.5 - ENERGÍA CARGADA ES PRIMARIA
            # ================================================================
            # OBJETIVO ÚNICO: Maximizar energía entregada a vehículos (1,160 kWh/día target)
            # 
            # Pesos:
            # - 60% Energía cargada (PRIMARY - indicator directo de éxito)
            # - 25% Ocupación sockets (indica potencial disponible)
            # - 12% CO2 evitado (beneficio ambiental)
            # - 3% Solar→EV (preferencia por solar vs grid)
            # 
            # Esto es más científico y menos ruidoso que contar
            # vehículos individuales.
            # ================================================================
            reward_val = (
                energy_charging_bonus * 0.60 +         # PRIMARY: energía cargada
                vehicles_charging_bonus * 0.25 +       # SECONDARY: ocupación sockets
                co2_bonus * 0.12 +                     # TERTIARY: CO2 beneficio
                solar_ev_bonus * 0.03 +                # QUATERNARY: solar preference
                reward_val * 0.0                       # Baseline multiobjetivo (zero)
                # Eliminada: grid_penalty para simplificar
            )
            
            # Mantener en rango estable para PPO [-1, 1]
            reward_val = float(np.clip(reward_val, -1.0, 1.0))
            
        except (ValueError, KeyError, AttributeError, TypeError) as exc:
            logger.warning("Error en reward computation hora %d: %s", h, exc)
            reward_val = -10.0
            components = {'co2_avoided_total_kg': co2_avoided_total_kg}

        # TRACKING (acumulador de métricas del episodio)
        self.episode_reward += float(reward_val)
        self.episode_co2_avoided += co2_avoided_total_kg
        self.episode_solar_kwh += solar_kw
        self.episode_grid_import += grid_import_kwh
        self.episode_ev_satisfied += ev_soc_avg
        
        # [v5.3] TRACKING DIARIO (para observaciones de comunicación)
        self.daily_co2_avoided += co2_avoided_total_kg
        self.motos_charging_now = motos_charging
        self.mototaxis_charging_now = mototaxis_charging
        self.bess_available_kwh = bess_soc * BESS_MAX_KWH * 0.90
        self.solar_surplus_kwh = max(0.0, solar_kw - total_demand_kwh)
        self.current_grid_import = grid_import_kwh

        # SIGUIENTE OBSERVACION
        obs = self._make_observation(self.step_count)

        # TERMINACION (episodio completo = 1 año)
        terminated = self.step_count >= self.max_steps
        truncated = False  # No truncate (let episode complete)

        # INFO DICT COMPLETO (para DetailedLoggingCallback) - COLUMNAS ESTÁNDAR SAC/A2C/PPO
        info: Dict[str, Any] = {
            'step': self.step_count,
            'hour': h % 24,
            'hour_of_year': h,
            # Energía - NOMBRES ESTÁNDAR COMPATIBLES
            'solar_kw': solar_kw,  # CORRECCIÓN: cambiar de solar_generation_kwh
            'ev_charging_kw': ev_charging_kwh,  # CORRECCIÓN: cambiar de ev_charging_kwh
            'grid_import_kw': grid_import_kwh,  # CORRECCIÓN: cambiar de grid_import_kwh
            'grid_export_kwh': grid_export_kwh,
            'mall_demand_kw': mall_kw,  # CORRECCIÓN: cambiar de mall_demand_kwh
            'total_demand_kwh': total_demand_kwh,
            # BESS
            'bess_soc': bess_soc,
            'bess_power_kw': bess_power_kw,
            'bess_action': float(bess_action),
            'bess_control_reward': bess_control_reward,
            # CO2
            'co2_grid_kg': co2_grid_kg,
            'co2_avoided_indirect_kg': co2_avoided_indirect_kg,
            'co2_avoided_direct_kg': co2_avoided_direct_kg,
            'co2_avoided_total_kg': co2_avoided_total_kg,
            # EV breakdown
            'motos_power_kw': motos_demand,
            'mototaxis_power_kw': mototaxis_demand,
            'motos_charging': motos_charging,
            'mototaxis_charging': mototaxis_charging,
            'ev_soc_avg': ev_soc_avg,
            # v5.3: MÉTRICAS DE CARGA DE VEHÍCULOS (CRÍTICAS)
            'vehicles_charging_now': vehicles_charging_now,     # Total vehículos cargando
            'vehicles_charging_ratio': vehicles_charging_ratio, # Ocupación sockets [0,1]
            'vehicles_100_percent': total_100_percent,          # Cargados al 100%
            'vehicles_total_scenario': total_all_chargers,      # Total en escenario
            'vehicles_charging_bonus': vehicles_charging_bonus, # Reward por ocupación
            'vehicles_100_bonus': vehicles_100_bonus,           # Reward por completados
            'co2_bonus': float(co2_bonus),                      # Reward por CO2
            'grid_penalty': float(grid_penalty),                # Penalidad grid
            'solar_ev_bonus': solar_ev_bonus,                   # Reward solar→EV
            'solar_used_for_ev_kwh': solar_used_for_ev,         # kWh solar→EV
            # v5.3: CONTROL GRANULAR POR SOCKET
            'socket_efficiency_reward': socket_efficiency_reward,
            # [v5.5] VEHICULOS CARGADOS POR SOC - usar SUM acumulado
            'motos_10_percent': self.episode_motos_10_sum,
            'motos_20_percent': self.episode_motos_20_sum,
            'motos_30_percent': self.episode_motos_30_sum,
            'motos_50_percent': self.episode_motos_50_sum,
            'motos_70_percent': self.episode_motos_70_sum,
            'motos_80_percent': self.episode_motos_80_sum,
            'motos_100_percent': self.episode_motos_100_sum,
            'taxis_10_percent': self.episode_taxis_10_sum,
            'taxis_20_percent': self.episode_taxis_20_sum,
            'taxis_30_percent': self.episode_taxis_30_sum,
            'taxis_50_percent': self.episode_taxis_50_sum,
            'taxis_70_percent': self.episode_taxis_70_sum,
            'taxis_80_percent': self.episode_taxis_80_sum,
            'taxis_100_percent': self.episode_taxis_100_sum,
            # v5.3: ESTADO DEL SISTEMA (comunicación)
            'motos_charged_today': self.motos_charged_today,
            'mototaxis_charged_today': self.mototaxis_charged_today,
            'daily_co2_avoided_kg': self.daily_co2_avoided,
            # Acumulados episodio
            'episode_reward_cumulative': float(self.episode_reward),
            'episode_co2_avoided_cumulative': float(self.episode_co2_avoided),
        }

        if terminated:
            info['episode'] = {
                'r': float(self.episode_reward),
                'l': int(self.step_count)
            }

        return obs, float(reward_val), terminated, truncated, info


# ============================================================================
# DETAILED LOGGING CALLBACK - Para tracking paso a paso y generación de archivos
# ============================================================================
from stable_baselines3.common.callbacks import BaseCallback


class DetailedLoggingCallback(BaseCallback):
    """
    Callback para tracking detallado del entrenamiento PPO.
    
    Genera:
    - trace_records: registro paso a paso de todas las métricas
    - timeseries_records: series temporales por hora/episodio
    - episode metrics: acumuladores por episodio para training_evolution
    """

    def __init__(self, env_ref: CityLearnEnvironment, output_dir: Path, verbose: int = 1):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.output_dir = output_dir
        self.step_log_freq = 1000  # Cada 1000 pasos
        
        # CARGAR DATOS REALES DE BESS (dataset OE2 v5.4 - VINCULADO A BASELINES)
        # IMPORTANTE: Usar bess_simulation_hourly.csv (mismo que baselines)
        bess_real_path = Path('data/oe2/bess/bess_simulation_hourly.csv')
        bess_alt_path = Path('data/oe2/bess/bess_ano_2024.csv')  # Fallback
        
        if bess_real_path.exists():
            self.bess_real_df = pd.read_csv(bess_real_path)
            print(f'  [BESS REAL] Cargado (BASELINE): {len(self.bess_real_df)} horas de {bess_real_path.name}')
        elif bess_alt_path.exists():
            self.bess_real_df = pd.read_csv(bess_alt_path)
            print(f'  [BESS REAL] Cargado (FALLBACK): {len(self.bess_real_df)} horas de {bess_alt_path.name}')
        else:
            self.bess_real_df = None
            print(f'  [BESS REAL] ADVERTENCIA: No encontrado en {bess_real_path} ni {bess_alt_path}')

        # Acumuladores por episodio (COMPLETO - Similar A2C)
        self.episode_rewards: list[float] = []
        self.episode_co2_grid: list[float] = []
        self.episode_co2_avoided_indirect: list[float] = []
        self.episode_co2_avoided_direct: list[float] = []
        self.episode_solar_kwh: list[float] = []
        self.episode_ev_charging: list[float] = []
        self.episode_grid_import: list[float] = []
        # [OK] NUEVAS: Estabilidad, costos, motos/mototaxis
        self.episode_grid_stability: list[float] = []
        self.episode_cost_usd: list[float] = []
        self.episode_motos_charged: list[int] = []
        self.episode_mototaxis_charged: list[int] = []
        self.episode_bess_discharge_kwh: list[float] = []
        self.episode_bess_charge_kwh: list[float] = []
        # [OK] NUEVAS: Progreso de control
        self.episode_avg_socket_setpoint: list[float] = []
        self.episode_socket_utilization: list[float] = []
        self.episode_bess_action_avg: list[float] = []
        # [OK] NUEVAS: Componentes de reward
        self.episode_r_solar: list[float] = []
        self.episode_r_cost: list[float] = []
        self.episode_r_ev: list[float] = []
        self.episode_r_grid: list[float] = []
        self.episode_r_co2: list[float] = []

        # TRACE: registro paso a paso
        self.trace_records: list[dict[str, Any]] = []

        # TIMESERIES: registro horario por episodio
        self.timeseries_records: list[dict[str, Any]] = []

        # Tracking ACTUAL (COMPLETO)
        self.current_episode = 0
        self.episode_reward = 0.0  # [OK] AGREGADO: acumulador de reward del episodio
        self.ep_co2_grid = 0.0
        self.ep_co2_avoided_indirect = 0.0
        self.ep_co2_avoided_direct = 0.0
        self.ep_solar = 0.0
        self.ep_ev = 0.0
        self.ep_grid = 0.0
        self.ep_reward = 0.0
        self.ep_steps = 0
        # [OK] NUEVOS acumuladores
        self.ep_stability_sum = 0.0
        self.ep_stability_count = 0
        self.ep_cost_usd = 0.0
        
        # [OK] TRACKING DE VEHICULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
        self.episode_motos_10_max: float = 0
        self.episode_motos_20_max: float = 0
        self.episode_motos_30_max: float = 0
        self.episode_motos_50_max: float = 0
        self.episode_motos_70_max: float = 0
        self.episode_motos_80_max: float = 0
        self.episode_motos_100_max: int = 0
        
        self.episode_taxis_10_max: int = 0
        self.episode_taxis_20_max: int = 0
        self.episode_taxis_30_max: int = 0
        self.episode_taxis_50_max: int = 0
        self.episode_taxis_70_max: int = 0
        self.episode_taxis_80_max: int = 0
        self.episode_taxis_100_max: int = 0
        
        self.ep_motos_charged_max = 0
        self.ep_mototaxis_charged_max = 0
        self.ep_bess_discharge = 0.0
        self.ep_bess_charge = 0.0
        self.prev_bess_soc = 0.5  # SOC inicial 50%
        self.ep_socket_setpoint_sum = 0.0
        self.ep_socket_active_count = 0
        self.ep_bess_action_sum = 0.0
        # [OK] NUEVOS acumuladores reward components
        self.ep_r_solar_sum = 0.0
        self.ep_r_cost_sum = 0.0
        self.ep_r_ev_sum = 0.0
        self.ep_r_grid_sum = 0.0
        self.ep_r_co2_sum = 0.0

    def _on_init(self) -> None:
        """Initialize callback after model is set. Called by BaseCallback."""
        if not hasattr(self, 'episode_reward'):
            self.episode_reward = 0.0
        if not hasattr(self, 'ep_reward'):
            self.ep_reward = 0.0

    def _on_step(self) -> bool:
        # Obtener info del último step
        infos = self.locals.get('infos', [{}])
        info = infos[0] if infos else {}

        # Acumular métricas básicas - NOMBRES ESTÁNDAR COMPATIBLES
        self.ep_co2_grid += info.get('co2_grid_kg', 0)
        self.ep_co2_avoided_indirect += info.get('co2_avoided_indirect_kg', 0)
        self.ep_co2_avoided_direct += info.get('co2_avoided_direct_kg', 0)
        self.ep_solar += info.get('solar_kw', info.get('solar_generation_kwh', 0))  # Fallback para compatibilidad
        self.ep_ev += info.get('ev_charging_kw', info.get('ev_charging_kwh', 0))  # Fallback para compatibilidad
        self.ep_grid += info.get('grid_import_kw', info.get('grid_import_kwh', 0))  # Fallback para compatibilidad
        self.ep_steps += 1
        
        # [OK] NUEVAS MÉTRICAS: Estabilidad, costos, motos/mototaxis
        # Estabilidad: calcular ratio de variación
        grid_import = info.get('grid_import_kw', info.get('grid_import_kwh', 0.0))  # Compatibilidad
        grid_export = info.get('grid_export_kwh', 0.0) if 'grid_export_kwh' in info else 0.0
        peak_demand_limit = 450.0  # kW límite típico
        stability = 1.0 - min(1.0, abs(grid_import - grid_export) / peak_demand_limit)
        self.ep_stability_sum += stability
        self.ep_stability_count += 1
        
        # Costo: tarifa × (import - export)
        tariff_usd = 0.15  # USD/kWh tarifa Iquitos
        cost_step = (grid_import - grid_export * 0.5) * tariff_usd
        self.ep_cost_usd += max(0.0, cost_step)
        
        # Motos y mototaxis (máximo por episodio)
        motos = info.get('motos_charging', 0)
        mototaxis = info.get('mototaxis_charging', 0)
        self.ep_motos_charged_max = max(self.ep_motos_charged_max, motos)
        self.ep_mototaxis_charged_max = max(self.ep_mototaxis_charged_max, mototaxis)
        
        # BESS (descarga/carga) - DATOS REALES del dataset OE2
        # Usa flujos reales de bess_ano_2024.csv en lugar de calcular
        hour_of_year = info.get('hour_of_year', self.ep_steps % 8760)
        
        if self.bess_real_df is not None and hour_of_year < len(self.bess_real_df):
            # USAR DATOS REALES DEL DATASET
            bess_row = self.bess_real_df.iloc[hour_of_year]
            bess_charge_real = float(bess_row.get('bess_charge_kwh', 0.0))
            bess_discharge_real = float(bess_row.get('bess_discharge_kwh', 0.0))
            self.ep_bess_charge += bess_charge_real
            self.ep_bess_discharge += bess_discharge_real
            # También trackear destino de descarga
            self.ep_bess_to_mall = getattr(self, 'ep_bess_to_mall', 0.0) + float(bess_row.get('bess_to_mall_kwh', 0.0))
            self.ep_bess_to_ev = getattr(self, 'ep_bess_to_ev', 0.0) + float(bess_row.get('bess_to_ev_kwh', 0.0))
        else:
            # FALLBACK: usar info del environment si no hay dataset
            bess_power = info.get('bess_power_kw', 0.0)
            if bess_power > 0:
                self.ep_bess_discharge += bess_power
            else:
                self.ep_bess_charge += abs(bess_power)
        
        # Progreso de control de sockets (desde acciones)
        actions = self.locals.get('actions', None)
        if actions is not None and len(actions) > 0:
            action = actions[0] if len(actions[0].shape) > 0 else actions
            if len(action) >= 39:  # v5.2: 1 BESS + 38 sockets
                bess_action = float(action[0])
                socket_setpoints = action[1:39]  # v5.2: 38 sockets
                self.ep_bess_action_sum += bess_action
                self.ep_socket_setpoint_sum += float(np.mean(socket_setpoints))
                self.ep_socket_active_count += int(np.sum(socket_setpoints > 0.1))
        
        # [OK] NUEVAS: Acumular componentes de reward desde info
        self.ep_r_solar_sum += info.get('r_solar', 0.0)
        self.ep_r_cost_sum += info.get('r_cost', 0.0)
        self.ep_r_ev_sum += info.get('r_ev', 0.0)
        self.ep_r_grid_sum += info.get('r_grid', 0.0)
        self.ep_r_co2_sum += info.get('r_co2', 0.0)
        
        # [OK] ACTUALIZAR MAXIMOS DE VEHICULOS POR SOC (desde environment)
        # v5.5 CORREGIDO: Ya se está calculando el máximo en step(), no en callback
        # self.episode_motos_10_max = max(self.episode_motos_10_max, info.get('motos_10_percent', 0))
        # self.episode_motos_20_max = max(self.episode_motos_20_max, info.get('motos_20_percent', 0))
        # self.episode_motos_30_max = max(self.episode_motos_30_max, info.get('motos_30_percent', 0))
        # self.episode_motos_50_max = max(self.episode_motos_50_max, info.get('motos_50_percent', 0))
        # self.episode_motos_70_max = max(self.episode_motos_70_max, info.get('motos_70_percent', 0))
        # self.episode_motos_80_max = max(self.episode_motos_80_max, info.get('motos_80_percent', 0))
        # self.episode_motos_100_max = max(self.episode_motos_100_max, info.get('motos_100_percent', 0))
        # 
        # self.episode_taxis_10_max = max(self.episode_taxis_10_max, info.get('taxis_10_percent', 0))
        # self.episode_taxis_20_max = max(self.episode_taxis_20_max, info.get('taxis_20_percent', 0))
        # self.episode_taxis_30_max = max(self.episode_taxis_30_max, info.get('taxis_30_percent', 0))
        # self.episode_taxis_50_max = max(self.episode_taxis_50_max, info.get('taxis_50_percent', 0))
        # self.episode_taxis_70_max = max(self.episode_taxis_70_max, info.get('taxis_70_percent', 0))
        # self.episode_taxis_80_max = max(self.episode_taxis_80_max, info.get('taxis_80_percent', 0))
        # self.episode_taxis_100_max = max(self.episode_taxis_100_max, info.get('taxis_100_percent', 0))
        
        # [OK] IMPORTANTE: Acumular reward total del step
        rewards = self.locals.get('rewards', [0.0])
        reward_val = float(rewards[0]) if rewards else 0.0
        self.episode_reward += reward_val  # [OK] AGREGADO: acumular reward total del episodio

        # TRACE: guardar cada paso
        rewards = self.locals.get('rewards', [0.0])
        reward_val = float(rewards[0]) if rewards else 0.0
        trace_record = {
            'timestep': self.num_timesteps,
            'episode': self.current_episode,
            'step_in_episode': self.ep_steps,
            'hour': info.get('hour', 0),
            'reward': reward_val,
            'co2_grid_kg': info.get('co2_grid_kg', 0),
            'co2_avoided_indirect_kg': info.get('co2_avoided_indirect_kg', 0),
            'co2_avoided_direct_kg': info.get('co2_avoided_direct_kg', 0),
            'solar_generation_kwh': info.get('solar_generation_kwh', 0),
            'ev_charging_kwh': info.get('ev_charging_kwh', 0),
            'grid_import_kwh': info.get('grid_import_kwh', 0),
            'bess_power_kw': info.get('bess_power_kw', 0),
            'motos_power_kw': info.get('motos_power_kw', 0),
            'mototaxis_power_kw': info.get('mototaxis_power_kw', 0),
            'motos_charging': info.get('motos_charging', 0),
            'mototaxis_charging': info.get('mototaxis_charging', 0),
        }
        self.trace_records.append(trace_record)

        # TIMESERIES: guardar por hora (cada 1 hora = 1 step) - COLUMNAS ESTÁNDAR SAC/A2C/PPO
        ts_record = {
            'timestep': self.num_timesteps,
            'episode': self.current_episode,
            'hour': self.ep_steps - 1,
            'solar_kw': info.get('solar_kw', 0),  # Nombre estándar compartido
            'ev_charging_kw': info.get('ev_charging_kw', 0),  # Nombre estándar compartido
            'grid_import_kw': info.get('grid_import_kw', 0),  # Nombre estándar compartido
            'bess_power_kw': info.get('bess_power_kw', 0),  # Ya estándar
            'bess_soc': info.get('bess_soc', 0.0),
            'mall_demand_kw': info.get('mall_demand_kw', 0),  # Nombre estándar
            'co2_avoided_total_kg': info.get('co2_avoided_total_kg', 0),
            'motos_charging': info.get('motos_charging', 0),
            'mototaxis_charging': info.get('mototaxis_charging', 0),
            'reward': reward_val,
        }
        self.timeseries_records.append(ts_record)

        # Detectar fin de episodio
        dones = self.locals.get('dones', [False])
        if dones[0]:
            self.ep_reward = self.episode_reward  # [OK] FIXED: usar reward acumulado del callback, no del env
            self._log_episode_summary()
            self._reset_episode_tracking()
            self.current_episode += 1

        # Log de progreso cada N pasos
        if self.num_timesteps % self.step_log_freq == 0:
            self._log_progress()

        return True

    def _log_progress(self) -> None:
        """Mostrar progreso durante el episodio."""
        ep_num = self.current_episode
        pct = (self.ep_steps / 8760) * 100
        co2_net = max(0, self.ep_co2_grid - self.ep_co2_avoided_indirect - self.ep_co2_avoided_direct)

        print(f'    Steps: {self.num_timesteps:>7,} | Ep: {ep_num:>2} | '
              f'Progreso: {pct:>5.1f}% | '
              f'CO2_grid: {self.ep_co2_grid:>8,.0f} kg | '
              f'CO2_evitado: {(self.ep_co2_avoided_indirect + self.ep_co2_avoided_direct):>8,.0f} kg', flush=True)

    def _log_episode_summary(self) -> None:
        """Resumen completo al finalizar episodio con TODAS las métricas A2C.
        
        TERMINOLOGÍA ACLARADA (2026-02-08 MEJORADO - SIN DOUBLE-COUNTING):
        =======================================================================
        CO2_GRID: Emisiones generadas por importar del grid térmico Iquitos
                  (factor 0.4521 kg CO₂/kWh)
        
        CO2_EVITADO_INDIRECTO: Solar + BESS que van al grid (30% de renewable)
                  Reducen importación del grid térmico
                  (renewable_to_grid_kwh × 0.4521)
        
        CO2_EVITADO_DIRECTO: EVs cargados con energía renovable (70% de renewable)
                  Evitan combustión de VEHICULOS (gasolina)
                  (renewable_to_evs_kwh × 2.146 kg CO₂/kWh equivalente)
        
        REDUCCIÓN_TOTAL: CO2_EVITADO_INDIRECTO + CO2_EVITADO_DIRECTO
                  (Lo que el RL logra vs baseline SIN CONTROL)
        
        CO2_NETO: Grid import - Reducción total (NUNCA negativo)
                  Métrica de desempeño: menor = mejor control del agente
        
        PAPERS REFERENCIAS:
        [1] Liu et al. (2022) - Multi-objective EV charging optimization
        [2] Messagie et al. (2014) - EV lifecycle emissions (2.146 kg CO₂/kWh)
        [3] IVL Swedish Battery Report (2023) - Battery manufacturing CO₂
        [4] NREL (2023) - Dynamic grid CO₂ factors
        [5] Aryan et al. (2025) - LCA for EVs in developing countries
        """
        co2_avoided_total = self.ep_co2_avoided_indirect + self.ep_co2_avoided_direct
        co2_net = max(0, self.ep_co2_grid - co2_avoided_total)

        # Guardar en listas para training_evolution
        self.episode_rewards.append(self.ep_reward)
        self.episode_co2_grid.append(self.ep_co2_grid)
        self.episode_co2_avoided_indirect.append(self.ep_co2_avoided_indirect)
        self.episode_co2_avoided_direct.append(self.ep_co2_avoided_direct)
        self.episode_solar_kwh.append(self.ep_solar)
        self.episode_ev_charging.append(self.ep_ev)
        self.episode_grid_import.append(self.ep_grid)
        # [OK] NUEVAS métricas por episodio
        avg_stability = self.ep_stability_sum / max(1, self.ep_stability_count)
        self.episode_grid_stability.append(avg_stability)
        self.episode_cost_usd.append(self.ep_cost_usd)
        self.episode_motos_charged.append(self.ep_motos_charged_max)
        self.episode_mototaxis_charged.append(self.ep_mototaxis_charged_max)
        self.episode_bess_discharge_kwh.append(self.ep_bess_discharge)
        self.episode_bess_charge_kwh.append(self.ep_bess_charge)
        # Promedios de control por episodio
        steps_in_ep = max(1, self.ep_steps)
        self.episode_avg_socket_setpoint.append(self.ep_socket_setpoint_sum / steps_in_ep)
        self.episode_socket_utilization.append(self.ep_socket_active_count / (38.0 * steps_in_ep))
        self.episode_bess_action_avg.append(self.ep_bess_action_sum / steps_in_ep)
        # Reward components promedios
        self.episode_r_solar.append(self.ep_r_solar_sum / steps_in_ep)
        self.episode_r_cost.append(self.ep_r_cost_sum / steps_in_ep)
        self.episode_r_ev.append(self.ep_r_ev_sum / steps_in_ep)
        self.episode_r_grid.append(self.ep_r_grid_sum / steps_in_ep)
        self.episode_r_co2.append(self.ep_r_co2_sum / steps_in_ep)

        print()
        print(f'  ================================================================')
        print(f'  EPISODIO {self.current_episode + 1} COMPLETADO')
        print(f'  ================================================================')
        print(f'    Reward Total (acumulado):  {self.ep_reward:>12,.2f}')
        print()
        print(f'  CO2 CONTABILIDAD (SIN DOUBLE-COUNTING):')
        print(f'    Grid Import CO2:           {self.ep_co2_grid:>12,.0f} kg')
        print(f'    - Reducido Indirecto:      {self.ep_co2_avoided_indirect:>12,.0f} kg (solar/BESS -> grid avoidance)')
        print(f'    - Reducido Directo:        {self.ep_co2_avoided_direct:>12,.0f} kg (EV renewable -> avoid combustion)')
        print(f'    = Reducción Total:         {co2_avoided_total:>12,.0f} kg')
        print(f'    CO2 Neto (Grid - Reducido):{co2_net:>12,.0f} kg')
        print()
        print(f'  ENERGIA:')
        print(f'    Solar Aprovechado:         {self.ep_solar:>12,.0f} kWh')
        print(f'    EV Cargado:                {self.ep_ev:>12,.0f} kWh')
        print(f'    Grid Import:               {self.ep_grid:>12,.0f} kWh')
        print()
        print(f'  FLOTA MOVILIDAD:')
        print(f'    Motos cargadas (max):      {self.ep_motos_charged_max:>12,} / 112 (2,685 diarias)')
        print(f'    Mototaxis cargados (max):  {self.ep_mototaxis_charged_max:>12,} / 16 (388 diarias)')
        print()
        print(f'  [OK] MÁXIMO SIMULTÁNEO DE VEHÍCULOS POR NIVEL DE CARGA (SOC):')
        print(f'    Motos:    10%-{self.episode_motos_10_max:>2} veh | 20%-{self.episode_motos_20_max:>2} veh | 30%-{self.episode_motos_30_max:>2} veh | 50%-{self.episode_motos_50_max:>2} veh | 70%-{self.episode_motos_70_max:>2} veh | 80%-{self.episode_motos_80_max:>2} veh | 100%-{self.episode_motos_100_max:>2} veh')
        print(f'    Taxis:    10%-{self.episode_taxis_10_max:>2} veh | 20%-{self.episode_taxis_20_max:>2} veh | 30%-{self.episode_taxis_30_max:>2} veh | 50%-{self.episode_taxis_50_max:>2} veh | 70%-{self.episode_taxis_70_max:>2} veh | 80%-{self.episode_taxis_80_max:>2} veh | 100%-{self.episode_taxis_100_max:>2} veh')
        print()
        print(f'  BESS ALMACENAMIENTO:')
        print(f'    Descarga:                  {self.ep_bess_discharge:>12,.0f} kWh')
        print(f'    Carga:                     {self.ep_bess_charge:>12,.0f} kWh')
        print(f'  ================================================================')
        print()

    def _reset_episode_tracking(self) -> None:
        """Reset acumuladores para siguiente episodio - COMPLETO."""
        self.episode_reward = 0.0  # [OK] AGREGADO: reset del reward acumulado
        self.ep_co2_grid = 0.0
        self.ep_co2_avoided_indirect = 0.0
        self.ep_co2_avoided_direct = 0.0
        self.ep_solar = 0.0
        self.ep_ev = 0.0
        self.ep_grid = 0.0
        self.ep_reward = 0.0
        self.ep_steps = 0
        # [OK] Reset nuevos acumuladores
        self.ep_stability_sum = 0.0
        self.ep_stability_count = 0
        self.ep_cost_usd = 0.0
        
        # [v5.5 CORREGIDO] RESET TRACKING DE VEHICULOS POR SOC - máximo por episodio
        self.episode_motos_10_max = 0
        self.episode_motos_20_max = 0
        self.episode_motos_30_max = 0
        self.episode_motos_50_max = 0
        self.episode_motos_70_max = 0
        self.episode_motos_80_max = 0
        self.episode_motos_100_max = 0
        
        self.episode_taxis_10_max = 0
        self.episode_taxis_20_max = 0
        self.episode_taxis_30_max = 0
        self.episode_taxis_50_max = 0
        self.episode_taxis_70_max = 0
        self.episode_taxis_80_max = 0
        self.episode_taxis_100_max = 0
        
        self.ep_motos_charged_max = 0
        self.ep_mototaxis_charged_max = 0
        self.ep_bess_discharge = 0.0
        self.ep_bess_charge = 0.0
        self.prev_bess_soc = 0.5  # Reset SOC inicial 50%
        self.ep_socket_setpoint_sum = 0.0
        self.ep_socket_active_count = 0
        self.ep_bess_action_sum = 0.0
        # [OK] Reset componentes de reward
        self.ep_r_solar_sum = 0.0
        self.ep_r_cost_sum = 0.0
        self.ep_r_ev_sum = 0.0
        self.ep_r_grid_sum = 0.0
        self.ep_r_co2_sum = 0.0
        
        # [v5.5 CORREGIDO] RESET CALLBACK TRACKING VARIABLES (máximo simultáneo de vehículos)
        self.episode_motos_10_max = 0
        self.episode_motos_20_max = 0
        self.episode_motos_30_max = 0
        self.episode_motos_50_max = 0
        self.episode_motos_70_max = 0
        self.episode_motos_80_max = 0
        self.episode_motos_100_max = 0
        
        self.episode_taxis_10_max = 0.0
        self.episode_taxis_20_max = 0.0
        self.episode_taxis_30_max = 0.0
        self.episode_taxis_50_max = 0.0
        self.episode_taxis_70_max = 0.0
        self.episode_taxis_80_max = 0.0
        self.episode_taxis_100_max = 0


# ============================================================================
# PPO METRICS CALLBACK - Métricas específicas de PPO para diagnóstico
# ============================================================================

class PPOMetricsCallback(BaseCallback):
    """
    Callback para loguear métricas específicas de PPO durante el entrenamiento.
    
    MÉTRICAS CLAVE [Schulman et al. 2017]:
    ======================================
    1. approx_kl: KL divergence aproximada entre política nueva y vieja
       - Si KL > 0.02 frecuentemente → LR muy alto o demasiadas epochs
       - Si KL → 0 → política no está aprendiendo
       
    2. clip_fraction: % de samples donde se aplicó el clipping
       - Si > 0.3 frecuentemente → updates muy agresivos
       - Si → 0 → clip_range muy grande (no está limitando)
       
    3. entropy: Entropía de la política (exploración)
       - Si cae muy rápido → ent_coef muy bajo o reward shaping agresivo
       - Típico: decrece gradualmente durante entrenamiento
       
    4. policy_loss, value_loss: Losses del actor y crítico
       
    5. explained_variance: Qué tan bien el value function predice returns
       - ~1.0 = perfecto, 0 = no mejor que random, <0 = peor que random
       - Si ~0 o negativo → crítico está fallando, revisar arquitectura
       
    6. advantage_mean, advantage_std: Estadísticas del advantage (post-normalización)
       - Si normalize_advantage=True, mean ≈ 0 y std ≈ 1
       
    Señales de problema típicas:
    ----------------------------
    - KL muy alto + clip_fraction alta → LR alto, demasiadas epochs, batch pequeño
    - Entropy colapsa temprano → ent_coef muy bajo o determinismo prematuro
    - Explained variance negativa → crítico fallando
    """
    
    def __init__(
        self,
        log_freq: int = 2048,  # Cada N steps (típico = n_steps)
        eval_freq: int = 8760,  # Cada episodio para eval deterministic
        output_dir: Optional[Path] = None,  # Directorio para guardar gráficas
        verbose: int = 1
    ):
        super().__init__(verbose)
        self.log_freq = log_freq
        self.eval_freq = eval_freq
        self.output_dir = output_dir or Path('outputs/ppo_training')
        
        # Historial de métricas (con steps para eje X)
        self.steps_history: list[int] = []  # NUEVO: timesteps para eje X
        self.kl_history: list[float] = []
        self.clip_fraction_history: list[float] = []
        self.entropy_history: list[float] = []
        self.policy_loss_history: list[float] = []
        self.value_loss_history: list[float] = []
        self.explained_var_history: list[float] = []
        self.eval_returns: list[float] = []
        
        # Contadores de warnings
        self.high_kl_count: int = 0
        self.high_clip_count: int = 0
        self.entropy_collapse_count: int = 0
        self.bad_critic_count: int = 0
        
        # ========================================================================
        # DETECCIÓN ROBUSTA DE PROBLEMAS v2.0
        # ========================================================================
        
        # Señal combinada: KL alto + clip_fraction alta simultáneamente
        self.combined_kl_clip_count: int = 0
        
        # Detección de colapso temprano de entropy
        self._initial_entropy: Optional[float] = None  # Entropy en primeros steps
        self._entropy_baseline_samples: int = 0  # Samples para calcular baseline
        self._entropy_baseline_sum: float = 0.0
        self.early_entropy_collapse_count: int = 0
        
        # Explained variance negativa persistente
        self.consecutive_negative_ev_count: int = 0
        self.total_negative_ev_count: int = 0
        
        # Umbrales adaptativos (se ajustan durante entrenamiento)
        self._kl_warning_threshold: float = 0.03
        self._clip_warning_threshold: float = 0.30
        self._entropy_collapse_threshold: float = 0.5  # 50% del valor inicial
        
        # Correcciones automáticas aplicadas
        self.auto_corrections_applied: list[str] = []
        self._lr_reduction_count: int = 0
        self._max_lr_reductions: int = 3  # Máximo 3 reducciones de LR
        
        # Resumen de problemas para reporte final
        self._problem_summary: Dict[str, int] = {
            'kl_warnings': 0,
            'clip_warnings': 0,
            'combined_kl_clip': 0,
            'entropy_collapse': 0,
            'early_entropy_collapse': 0,
            'negative_explained_var': 0,
            'consecutive_negative_ev': 0,
        }
        
        # Flag para primer log
        self._first_log_done: bool = False
        
        # ========================================================================
        # KPIs CityLearn (estándar para evaluación de control en microgrids)
        # ========================================================================
        
        # Steps para KPIs (puede diferir de steps_history)
        self.kpi_steps_history: list[int] = []
        
        # 1. Electricity Consumption (net) - kWh neto consumido del grid
        self.electricity_consumption_history: list[float] = []
        
        # 2. Electricity Cost - USD total
        self.electricity_cost_history: list[float] = []
        
        # 3. Carbon Emissions - kg CO2 total
        self.carbon_emissions_history: list[float] = []
        
        # 4. Ramping - kW diferencia absoluta entre timesteps consecutivos
        self.ramping_history: list[float] = []
        
        # 5. Average Daily Peak - kW promedio de picos diarios
        self.avg_daily_peak_history: list[float] = []
        
        # 6. (1 - Load Factor) - Medida de eficiencia de uso
        self.one_minus_load_factor_history: list[float] = []
        
        # Acumuladores para calcular KPIs por ventana de evaluación
        self._kpi_window_size = 24  # Calcular KPIs cada 24 horas (1 día)
        self._kpi_grid_imports: list[float] = []
        self._kpi_grid_exports: list[float] = []
        self._kpi_costs: list[float] = []
        self._kpi_emissions: list[float] = []
        self._kpi_loads: list[float] = []  # Para ramping y load factor
        self._prev_load: float = 0.0  # Para calcular ramping
        self._kpi_ramping_sum: float = 0.0
        self._kpi_ramping_count: int = 0
    
    def _on_step(self) -> bool:
        """Ejecutado en cada step. Loguea métricas periódicamente."""
        
        # Solo loguear cada log_freq steps
        if self.num_timesteps % self.log_freq != 0:
            return True
        
        # Obtener métricas de PPO desde el logger de SB3
        ppo_metrics = self._get_ppo_metrics()
        
        if ppo_metrics:
            self._log_ppo_metrics(ppo_metrics)
            self._check_warning_signals(ppo_metrics)
        
        # KPIs CityLearn - Recolectar datos para evaluación
        self._collect_kpi_data()
        
        # Eval deterministic cada eval_freq
        if self.num_timesteps % self.eval_freq == 0 and self.num_timesteps > 0:
            eval_return = self._eval_deterministic()
            if eval_return is not None:
                self.eval_returns.append(eval_return)
                if self.verbose > 0:
                    print(f'    [EVAL] Deterministic return: {eval_return:.2f}')
        
        return True
    
    def _get_ppo_metrics(self) -> Dict[str, float]:
        """Extrae métricas específicas de PPO desde el modelo/logger."""
        metrics: Dict[str, float] = {}
        
        try:
            # SB3 guarda métricas en el logger durante el update
            # Acceder via model.logger o locals
            if hasattr(self.model, 'logger') and self.model.logger is not None:
                log = self.model.logger.name_to_value
                
                # Métricas estándar de PPO en SB3
                metrics['approx_kl'] = log.get('train/approx_kl', 0.0)
                metrics['clip_fraction'] = log.get('train/clip_fraction', 0.0)
                metrics['entropy_loss'] = log.get('train/entropy_loss', 0.0)
                metrics['policy_loss'] = log.get('train/policy_gradient_loss', 0.0)
                metrics['value_loss'] = log.get('train/value_loss', 0.0)
                metrics['explained_variance'] = log.get('train/explained_variance', 0.0)
                metrics['learning_rate'] = log.get('train/learning_rate', 0.0)
                
                # Calcular entropy real (entropy_loss es negativo en SB3)
                if metrics['entropy_loss'] != 0:
                    metrics['entropy'] = -metrics['entropy_loss']
                else:
                    metrics['entropy'] = 0.0
                    
        except (AttributeError, KeyError, TypeError):
            pass
        
        return metrics
    
    def _log_ppo_metrics(self, metrics: Dict[str, float]) -> None:
        """Loguea métricas de PPO al historial y a consola. Salta primer reporte incompleto."""
        
        approx_kl = metrics.get('approx_kl', 0.0)
        clip_fraction = metrics.get('clip_fraction', 0.0)
        entropy = metrics.get('entropy', 0.0)
        policy_loss = metrics.get('policy_loss', 0.0)
        value_loss = metrics.get('value_loss', 0.0)
        explained_var = metrics.get('explained_variance', 0.0)
        
        # CRÍTICO: Skip primer reporte (step 2,048) porque métricas no están calculadas aún
        # El primer update completo ocurre DESPUÉS de n_steps=2,048, entonces en step 4,096+
        # Detectar si todas las métricas son cero (incompletas)
        all_metrics_zero = (approx_kl == 0.0 and clip_fraction == 0.0 and entropy == 0.0 and 
                           policy_loss == 0.0 and value_loss == 0.0 and explained_var == 0.0)
        
        # Solo guardar/reportar si las métricas son VÁLIDAS (no están todas en cero)
        if not all_metrics_zero:
            # Guardar en historial
            self.steps_history.append(self.num_timesteps)  # NUEVO: guardar step actual
            self.kl_history.append(approx_kl)
            self.clip_fraction_history.append(clip_fraction)
            self.entropy_history.append(entropy)
            self.policy_loss_history.append(policy_loss)
            self.value_loss_history.append(value_loss)
            self.explained_var_history.append(explained_var)
            
            # Imprimir métricas (verbose)
            if self.verbose > 0 and (not self._first_log_done or self.num_timesteps % (self.log_freq * 4) == 0):
                print(f'    [PPO] Step {self.num_timesteps:>7,}:')
                print(f'           KL: {approx_kl:.4f} | Clip%: {clip_fraction*100:.1f}% | Entropy: {entropy:.3f}')
                print(f'           Policy L: {policy_loss:.4f} | Value L: {value_loss:.4f} | Expl.Var: {explained_var:.3f}')
                self._first_log_done = True
        else:
            # Métrica incompleta (primer batch), omitir reporte
            pass
    
    def _check_warning_signals(self, metrics: Dict[str, float]) -> None:
        """
        Detecta señales típicas de problemas en PPO con correcciones robustas.
        
        DETECCIÓN ROBUSTA v2.0:
        =======================
        1. Señal combinada KL + clip_fraction (más severa que individual)
        2. Colapso TEMPRANO de entropy (comparado con baseline)
        3. Explained variance negativa PERSISTENTE (consecutiva)
        4. Correcciones automáticas opcionales (reducción de LR)
        
        Referencias:
        - [Schulman et al. 2017] PPO paper original
        - [Henderson et al. 2018] Deep RL That Matters - diagnóstico de problemas
        """
        
        approx_kl = metrics.get('approx_kl', 0.0)
        clip_fraction = metrics.get('clip_fraction', 0.0)
        entropy = metrics.get('entropy', 0.0)
        explained_var = metrics.get('explained_variance', 0.0)
        
        # ====================================================================
        # PASO 0: Establecer baseline de entropy (primeros 5 updates)
        # ====================================================================
        if self._entropy_baseline_samples < 5 and entropy > 0:
            self._entropy_baseline_sum += entropy
            self._entropy_baseline_samples += 1
            if self._entropy_baseline_samples == 5:
                self._initial_entropy = self._entropy_baseline_sum / 5
                print(f'    [PPO INFO] Entropy baseline establecido: {self._initial_entropy:.4f}')
        
        # ====================================================================
        # 1. SEÑAL COMBINADA: KL alto + clip_fraction alta (MÁS SEVERA)
        # ====================================================================
        kl_high = approx_kl > self._kl_warning_threshold
        clip_high = clip_fraction > self._clip_warning_threshold
        
        if kl_high and clip_high:
            self.combined_kl_clip_count += 1
            self._problem_summary['combined_kl_clip'] += 1
            
            if self.combined_kl_clip_count <= 5 or self.combined_kl_clip_count % 10 == 0:
                print(f'    ⚠️  [PPO CRITICAL] KL alto ({approx_kl:.4f}) + Clip alto ({clip_fraction*100:.1f}%) '
                      f'(count: {self.combined_kl_clip_count})')
                print(f'        → PROBLEMA SEVERO: Updates demasiado agresivos')
                print(f'        → Acción: Reducir LR, reducir n_epochs, o aumentar batch_size')
            
            # Corrección automática: reducir LR si ocurre >5 veces
            if self.combined_kl_clip_count >= 5 and self._lr_reduction_count < self._max_lr_reductions:
                self._apply_lr_reduction('combined_kl_clip')
        
        # 1b. Warnings individuales (menos severos)
        elif kl_high:
            self.high_kl_count += 1
            self._problem_summary['kl_warnings'] += 1
            if self.high_kl_count <= 3 or self.high_kl_count % 10 == 0:
                print(f'    ⚠️  [PPO WARNING] KL alto: {approx_kl:.4f} > {self._kl_warning_threshold} '
                      f'(count: {self.high_kl_count})')
        
        elif clip_high:
            self.high_clip_count += 1
            self._problem_summary['clip_warnings'] += 1
            if self.high_clip_count <= 3 or self.high_clip_count % 10 == 0:
                print(f'    ⚠️  [PPO WARNING] Clip fraction alto: {clip_fraction*100:.1f}% > {self._clip_warning_threshold*100:.0f}% '
                      f'(count: {self.high_clip_count})')
        
        # ====================================================================
        # 2. COLAPSO TEMPRANO DE ENTROPY (comparado con baseline)
        # ====================================================================
        if self._initial_entropy is not None and self._initial_entropy > 0:
            entropy_ratio = entropy / self._initial_entropy
            training_progress = self.num_timesteps / 87600  # Normalizado a 10 episodios
            
            # Colapso temprano = entropy cae >50% cuando aún estamos en <30% del entrenamiento
            if entropy_ratio < self._entropy_collapse_threshold and training_progress < 0.3:
                self.early_entropy_collapse_count += 1
                self._problem_summary['early_entropy_collapse'] += 1
                
                if self.early_entropy_collapse_count <= 3 or self.early_entropy_collapse_count % 10 == 0:
                    print(f'    ⚠️  [PPO CRITICAL] Entropy colapsó TEMPRANO: {entropy:.4f} '
                          f'({entropy_ratio*100:.0f}% del baseline {self._initial_entropy:.4f})')
                    print(f'        → Progreso: {training_progress*100:.0f}% | Colapso en <30% del entrenamiento')
                    print(f'        → Acción: AUMENTAR ent_coef (actual muy bajo) o revisar reward shaping')
            
            # Colapso general (cualquier momento)
            elif entropy < 0.1:
                self.entropy_collapse_count += 1
                self._problem_summary['entropy_collapse'] += 1
                if self.entropy_collapse_count <= 3 or self.entropy_collapse_count % 10 == 0:
                    print(f'    ⚠️  [PPO WARNING] Entropy muy baja: {entropy:.4f} < 0.1 '
                          f'(count: {self.entropy_collapse_count})')
        
        # ====================================================================
        # 3. EXPLAINED VARIANCE NEGATIVA PERSISTENTE
        # ====================================================================
        if explained_var < 0.0:
            self.consecutive_negative_ev_count += 1
            self.total_negative_ev_count += 1
            self._problem_summary['negative_explained_var'] += 1
            
            # Alerta escalada según severidad
            if self.consecutive_negative_ev_count >= 5:
                self._problem_summary['consecutive_negative_ev'] += 1
                if self.consecutive_negative_ev_count == 5 or self.consecutive_negative_ev_count % 10 == 0:
                    print(f'    ⚠️  [PPO CRITICAL] Explained variance NEGATIVA PERSISTENTE: {explained_var:.3f}')
                    print(f'        → {self.consecutive_negative_ev_count} updates CONSECUTIVOS con EV < 0')
                    print(f'        → Crítico prediciendo PEOR que random de forma CONSISTENTE')
                    print(f'        → Acción URGENTE: Revisar arquitectura del crítico, reducir vf_coef, verificar returns')
            elif self.total_negative_ev_count <= 3 or self.total_negative_ev_count % 10 == 0:
                print(f'    ⚠️  [PPO WARNING] Explained variance negativa: {explained_var:.3f} '
                      f'(total: {self.total_negative_ev_count})')
        else:
            # Reset contador consecutivo si EV es positiva
            if self.consecutive_negative_ev_count > 0:
                self.consecutive_negative_ev_count = 0
    
    def _apply_lr_reduction(self, reason: str) -> None:
        """
        Aplica reducción automática de learning rate como corrección.
        
        NOTA: Esta es una corrección conservadora. El LR se reduce a 50%
        del valor actual, máximo 3 veces durante el entrenamiento.
        """
        if self._lr_reduction_count >= self._max_lr_reductions:
            return
        
        try:
            if hasattr(self.model, 'lr_schedule') and callable(self.model.lr_schedule):
                # Para SB3, el LR se maneja via schedule, no podemos modificarlo directamente
                # pero sí podemos registrar que se necesita ajuste
                self._lr_reduction_count += 1
                correction_msg = f'LR reduction #{self._lr_reduction_count} suggested (reason: {reason})'
                self.auto_corrections_applied.append(correction_msg)
                print(f'    🔧 [AUTO-CORRECTION] {correction_msg}')
                print(f'        → Recomendación: Reiniciar con LR reducido (actual × 0.5)')
            else:
                self._lr_reduction_count += 1
                self.auto_corrections_applied.append(f'LR reduction suggested #{self._lr_reduction_count}')
        except Exception as e:
            print(f'    [WARNING] No se pudo aplicar corrección automática: {e}')
    
    def _print_problem_summary(self) -> None:
        """
        Imprime resumen de problemas detectados durante el entrenamiento.
        Llamar al final del entrenamiento.
        """
        print('\n' + '=' * 80)
        print('RESUMEN DE PROBLEMAS DETECTADOS (PPO)')
        print('=' * 80)
        
        total_problems = sum(self._problem_summary.values())
        
        if total_problems == 0:
            print('  ✅ No se detectaron problemas significativos durante el entrenamiento')
        else:
            print(f'  Total de eventos problemáticos: {total_problems}')
            print()
            
            # Problemas críticos (combinados)
            if self._problem_summary['combined_kl_clip'] > 0:
                print(f'  ❌ CRÍTICO - KL + Clip altos simultáneamente: {self._problem_summary["combined_kl_clip"]} veces')
                print(f'      → Solución: Reducir learning_rate a 1e-4, reducir n_epochs a 5')
            
            if self._problem_summary['early_entropy_collapse'] > 0:
                print(f'  ❌ CRÍTICO - Entropy colapsó TEMPRANO: {self._problem_summary["early_entropy_collapse"]} veces')
                print(f'      → Solución: Aumentar ent_coef a 0.02-0.05')
            
            if self._problem_summary['consecutive_negative_ev'] > 0:
                print(f'  ❌ CRÍTICO - Explained variance negativa PERSISTENTE: {self._problem_summary["consecutive_negative_ev"]} bloques')
                print(f'      → Solución: Revisar arquitectura net_arch, reducir vf_coef a 0.25')
            
            # Problemas moderados
            if self._problem_summary['kl_warnings'] > 0:
                print(f'  ⚠️  KL divergence alto: {self._problem_summary["kl_warnings"]} veces')
            
            if self._problem_summary['clip_warnings'] > 0:
                print(f'  ⚠️  Clip fraction alto: {self._problem_summary["clip_warnings"]} veces')
            
            if self._problem_summary['entropy_collapse'] > 0:
                print(f'  ⚠️  Entropy bajo (<0.1): {self._problem_summary["entropy_collapse"]} veces')
            
            if self._problem_summary['negative_explained_var'] > 0:
                print(f'  ⚠️  Explained variance negativa: {self._problem_summary["negative_explained_var"]} veces')
        
        # Correcciones aplicadas
        if self.auto_corrections_applied:
            print()
            print('  🔧 Correcciones sugeridas durante entrenamiento:')
            for correction in self.auto_corrections_applied:
                print(f'      - {correction}')
        
        # Recomendaciones finales basadas en patrones
        print()
        print('  RECOMENDACIONES PARA SIGUIENTE ENTRENAMIENTO:')
        if self._problem_summary['combined_kl_clip'] > 5:
            print('    1. learning_rate: 3e-4 → 1e-4 (reducir agresividad)')
        if self._problem_summary['early_entropy_collapse'] > 3:
            print('    2. ent_coef: 0.01 → 0.03 (aumentar exploración)')
        if self._problem_summary['consecutive_negative_ev'] > 2:
            print('    3. net_arch: [256,256] → [128,128] (simplificar crítico)')
            print('    4. vf_coef: 0.5 → 0.25 (reducir peso del value loss)')
        if total_problems == 0:
            print('    ✓ Hiperparámetros actuales funcionan bien')
        
        print('=' * 80 + '\n')
    
    def _eval_deterministic(self) -> Optional[float]:
        """Ejecuta evaluación determinística (sin exploración)."""
        try:
            env = self.training_env.envs[0] if hasattr(self.training_env, 'envs') else self.training_env
            
            obs, _ = env.reset()
            total_reward = 0.0
            done = False
            steps = 0
            max_steps = 1000  # Limit para eval rápido
            
            while not done and steps < max_steps:
                action, _ = self.model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, _ = env.step(action)
                total_reward += float(reward)
                done = terminated or truncated
                steps += 1
            
            return total_reward
            
        except (AttributeError, TypeError, ValueError):
            return None
    
    def _collect_kpi_data(self) -> None:
        """
        Recolectar datos para KPIs CityLearn de evaluación.
        
        KPIs estándar CityLearn calculados sobre carga neta agregada:
        1. Electricity consumption (net) - kWh
        2. Electricity cost - USD
        3. Carbon emissions - kg CO2
        4. Ramping - kW (variabilidad de carga)
        5. Average daily peak - kW
        6. (1 - Load Factor) - eficiencia de uso
        """
        # Obtener infos del environment
        infos = self.locals.get('infos', [{}])
        if not infos:
            return
        
        info = infos[0] if isinstance(infos, list) else infos
        
        # Extraer métricas del step actual
        grid_import = info.get('grid_import_kwh', 0.0)
        grid_export = info.get('grid_export_kwh', 0.0)
        cost = info.get('cost_usd', info.get('cost_soles', 0.0) * 0.27)  # Convertir soles a USD aprox
        co2 = info.get('co2_grid_kg', grid_import * 0.4521)  # Factor Iquitos
        
        # Carga neta total (para ramping y load factor)
        mall_demand = info.get('mall_demand_kwh', info.get('mall_demand_kw', 0.0))
        ev_demand = info.get('ev_charging_kwh', info.get('ev_demand_kw', 0.0))
        solar_gen = info.get('solar_generation_kwh', info.get('solar_kw', 0.0))
        net_load = mall_demand + ev_demand - solar_gen + grid_import - grid_export
        
        # Acumular datos
        self._kpi_grid_imports.append(grid_import)
        self._kpi_grid_exports.append(grid_export)
        self._kpi_costs.append(cost)
        self._kpi_emissions.append(co2)
        self._kpi_loads.append(max(0, net_load))  # Solo carga positiva
        
        # Calcular ramping (diferencia con step anterior)
        if self._prev_load > 0:
            ramping = abs(net_load - self._prev_load)
            self._kpi_ramping_sum += ramping
            self._kpi_ramping_count += 1
        self._prev_load = net_load
        
        # Calcular KPIs cada _kpi_window_size steps (24 horas = 1 día)
        if len(self._kpi_loads) >= self._kpi_window_size:
            self._calculate_and_store_kpis()
    
    def _calculate_and_store_kpis(self) -> None:
        """
        Calcular y almacenar KPIs para la ventana actual.
        
        Fórmulas estándar CityLearn:
        - Net consumption = sum(imports) - sum(exports)
        - Ramping = mean(|load[t] - load[t-1]|)
        - Load Factor = mean(load) / max(load)
        - (1 - Load Factor) = 1 - (mean/max)
        """
        if len(self._kpi_loads) == 0:
            return
        
        # Guardar step actual
        self.kpi_steps_history.append(self.num_timesteps)
        
        # 1. Net electricity consumption (kWh)
        net_consumption = sum(self._kpi_grid_imports) - sum(self._kpi_grid_exports)
        self.electricity_consumption_history.append(net_consumption)
        
        # 2. Electricity cost (USD)
        total_cost = sum(self._kpi_costs)
        self.electricity_cost_history.append(total_cost)
        
        # 3. Carbon emissions (kg CO2)
        total_co2 = sum(self._kpi_emissions)
        self.carbon_emissions_history.append(total_co2)
        
        # 4. Ramping (kW promedio)
        avg_ramping = self._kpi_ramping_sum / max(1, self._kpi_ramping_count)
        self.ramping_history.append(avg_ramping)
        
        # 5. Average daily peak (kW)
        daily_peak = max(self._kpi_loads) if self._kpi_loads else 0.0
        self.avg_daily_peak_history.append(daily_peak)
        
        # 6. (1 - Load Factor)
        avg_load = np.mean(self._kpi_loads) if self._kpi_loads else 0.0
        peak_load = max(self._kpi_loads) if self._kpi_loads else 1.0
        load_factor = avg_load / max(peak_load, 0.001)
        one_minus_lf = 1.0 - load_factor
        self.one_minus_load_factor_history.append(one_minus_lf)
        
        # Reset acumuladores para siguiente ventana
        self._kpi_grid_imports.clear()
        self._kpi_grid_exports.clear()
        self._kpi_costs.clear()
        self._kpi_emissions.clear()
        self._kpi_loads.clear()
        self._kpi_ramping_sum = 0.0
        self._kpi_ramping_count = 0
    
    def _generate_kpi_graphs(self) -> None:
        """
        Generar gráficos de KPIs CityLearn vs Training Steps para PPO.
        
        GRÁFICOS GENERADOS:
        1. Electricity Consumption (net) vs Steps
        2. Electricity Cost vs Steps
        3. Carbon Emissions vs Steps
        4. Ramping vs Steps
        5. Average Daily Peak vs Steps
        6. (1 - Load Factor) vs Steps
        7. Dashboard KPIs combinado 2×3
        """
        
        if len(self.kpi_steps_history) < 2:
            print('     ⚠️ Insuficientes datos para gráficos KPIs (< 2 puntos)')
            return
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Función helper para suavizado
        def smooth(data: list[float], window: int = 5) -> np.ndarray:
            """Rolling mean para suavizar curvas."""
            if len(data) < window:
                return np.array(data)
            return pd.Series(data).rolling(window=window, min_periods=1).mean().values
        
        steps = np.array(self.kpi_steps_history)
        steps_k = steps / 1000.0  # En miles
        
        # ====================================================================
        # GRÁFICO 1: ELECTRICITY CONSUMPTION vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            consumption = np.array(self.electricity_consumption_history)
            ax.plot(steps_k, consumption, 'b-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps_k, smooth(list(consumption)), 'b-', linewidth=2, label='Smoothed')
            
            # Línea de tendencia
            if len(steps) > 2:
                z = np.polyfit(steps, consumption, 1)
                p = np.poly1d(z)
                ax.plot(steps_k, p(steps), 'r--', alpha=0.7, label=f'Trend (slope={z[0]:.4f})')
            
            ax.set_xlabel('Training Steps (K)')
            ax.set_ylabel('Net Electricity Consumption (kWh/day)')
            ax.set_title('PPO: Electricity Consumption vs Training Steps\n(Lower = better grid independence)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            # Anotar mejora si existe
            if len(consumption) > 1:
                improvement = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}% vs inicio', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_electricity_consumption.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_electricity_consumption.png')
        except Exception as e:
            print(f'     ❌ Error en consumption graph: {e}')
        
        # ====================================================================
        # GRÁFICO 2: ELECTRICITY COST vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            cost = np.array(self.electricity_cost_history)
            ax.plot(steps_k, cost, 'g-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps_k, smooth(list(cost)), 'g-', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps (K)')
            ax.set_ylabel('Electricity Cost (USD/day)')
            ax.set_title('PPO: Electricity Cost vs Training Steps\n(Lower = better cost efficiency)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar mejora
            if len(cost) > 1:
                improvement = (cost[0] - cost[-1]) / max(cost[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}% vs inicio', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_electricity_cost.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_electricity_cost.png')
        except Exception as e:
            print(f'     ❌ Error en cost graph: {e}')
        
        # ====================================================================
        # GRÁFICO 3: CARBON EMISSIONS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            emissions = np.array(self.carbon_emissions_history)
            ax.plot(steps_k, emissions, 'brown', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps_k, smooth(list(emissions)), 'brown', linewidth=2, label='Smoothed')
            
            # Baseline sin control
            if len(emissions) > 0:
                baseline = emissions[0]
                ax.axhline(y=baseline, color='gray', linestyle='--', alpha=0.5, label=f'Baseline ({baseline:.1f} kg)')
            
            ax.set_xlabel('Training Steps (K)')
            ax.set_ylabel('Carbon Emissions (kg CO₂/day)')
            ax.set_title('PPO: Carbon Emissions vs Training Steps\n(Lower = better environmental impact)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar reducción CO2
            if len(emissions) > 1:
                reduction = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                color = 'green' if reduction > 0 else 'red'
                ax.annotate(f'{"↓" if reduction > 0 else "↑"} {abs(reduction):.1f}% CO₂', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_carbon_emissions.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_carbon_emissions.png')
        except Exception as e:
            print(f'     ❌ Error en emissions graph: {e}')
        
        # ====================================================================
        # GRÁFICO 4: RAMPING vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ramping = np.array(self.ramping_history)
            ax.plot(steps_k, ramping, 'purple', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps_k, smooth(list(ramping)), 'purple', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps (K)')
            ax.set_ylabel('Average Ramping (kW)')
            ax.set_title('PPO: Load Ramping vs Training Steps\n(Lower = more stable grid operation)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar mejora en estabilidad
            if len(ramping) > 1:
                improvement = (ramping[0] - ramping[-1]) / max(ramping[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}% ramping', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_ramping.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_ramping.png')
        except Exception as e:
            print(f'     ❌ Error en ramping graph: {e}')
        
        # ====================================================================
        # GRÁFICO 5: AVERAGE DAILY PEAK vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            peak = np.array(self.avg_daily_peak_history)
            ax.plot(steps_k, peak, 'red', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps_k, smooth(list(peak)), 'red', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps (K)')
            ax.set_ylabel('Daily Peak Demand (kW)')
            ax.set_title('PPO: Average Daily Peak vs Training Steps\n(Lower = better peak shaving)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar reducción de pico
            if len(peak) > 1:
                reduction = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                color = 'green' if reduction > 0 else 'red'
                ax.annotate(f'{"↓" if reduction > 0 else "↑"} {abs(reduction):.1f}% peak', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_daily_peak.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_daily_peak.png')
        except Exception as e:
            print(f'     ❌ Error en peak graph: {e}')
        
        # ====================================================================
        # GRÁFICO 6: (1 - LOAD FACTOR) vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            one_minus_lf = np.array(self.one_minus_load_factor_history)
            ax.plot(steps_k, one_minus_lf, 'orange', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps_k, smooth(list(one_minus_lf)), 'orange', linewidth=2, label='Smoothed')
            
            # Zona ideal (< 0.3 = buen load factor > 0.7)
            ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7, label='Target (LF > 0.7)')
            ax.fill_between(steps_k, 0, 0.3, alpha=0.1, color='green')
            
            ax.set_xlabel('Training Steps (K)')
            ax.set_ylabel('(1 - Load Factor)')
            ax.set_title('PPO: (1 - Load Factor) vs Training Steps\n(Lower = better load distribution, 0 = constant load)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)
            
            # Anotar mejora
            if len(one_minus_lf) > 1:
                improvement = (one_minus_lf[0] - one_minus_lf[-1]) / max(one_minus_lf[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}%', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_load_factor.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_load_factor.png')
        except Exception as e:
            print(f'     ❌ Error en load factor graph: {e}')
        
        # ====================================================================
        # GRÁFICO 7: DASHBOARD KPIs COMBINADO 2×3
        # ====================================================================
        try:
            fig, axes = plt.subplots(2, 3, figsize=(16, 10))
            
            # 1. Electricity Consumption (top-left)
            ax = axes[0, 0]
            consumption = np.array(self.electricity_consumption_history)
            ax.plot(steps_k, smooth(list(consumption)), 'b-', linewidth=2)
            ax.set_title('Net Consumption (kWh/day)')
            ax.set_xlabel('Steps (K)')
            ax.grid(True, alpha=0.3)
            
            # 2. Electricity Cost (top-center)
            ax = axes[0, 1]
            cost = np.array(self.electricity_cost_history)
            ax.plot(steps_k, smooth(list(cost)), 'g-', linewidth=2)
            ax.set_title('Cost (USD/day)')
            ax.set_xlabel('Steps (K)')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 3. Carbon Emissions (top-right)
            ax = axes[0, 2]
            emissions = np.array(self.carbon_emissions_history)
            ax.plot(steps_k, smooth(list(emissions)), 'brown', linewidth=2)
            ax.set_title('CO₂ Emissions (kg/day)')
            ax.set_xlabel('Steps (K)')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 4. Ramping (bottom-left)
            ax = axes[1, 0]
            ramping = np.array(self.ramping_history)
            ax.plot(steps_k, smooth(list(ramping)), 'purple', linewidth=2)
            ax.set_title('Ramping (kW)')
            ax.set_xlabel('Steps (K)')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 5. Daily Peak (bottom-center)
            ax = axes[1, 1]
            peak = np.array(self.avg_daily_peak_history)
            ax.plot(steps_k, smooth(list(peak)), 'red', linewidth=2)
            ax.set_title('Daily Peak (kW)')
            ax.set_xlabel('Steps (K)')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 6. (1 - Load Factor) (bottom-right)
            ax = axes[1, 2]
            one_minus_lf = np.array(self.one_minus_load_factor_history)
            ax.plot(steps_k, smooth(list(one_minus_lf)), 'orange', linewidth=2)
            ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7)
            ax.fill_between(steps_k, 0, 0.3, alpha=0.1, color='green')
            ax.set_title('(1 - Load Factor)')
            ax.set_xlabel('Steps (K)')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)
            
            # Calcular mejoras para título
            improvements = []
            if len(consumption) > 1:
                imp = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                if imp > 0:
                    improvements.append(f'Cons: {imp:.1f}%↓')
            if len(emissions) > 1:
                imp = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'CO₂: {imp:.1f}%↓')
            if len(peak) > 1:
                imp = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'Peak: {imp:.1f}%↓')
            
            title = 'CityLearn KPIs Dashboard - PPO Training'
            if improvements:
                title += f'\n✅ Improvements: {", ".join(improvements)}'
            
            fig.suptitle(title, fontsize=14, fontweight='bold')
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            plt.savefig(self.output_dir / 'kpi_dashboard.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_dashboard.png')
            
        except Exception as e:
            print(f'     ❌ Error en KPI dashboard: {e}')
        
        print(f'     📁 Gráficos KPIs guardados en: {self.output_dir}')
    
    def on_training_end(self) -> None:
        """Resumen final de métricas PPO y generación de gráficas."""
        if self.verbose > 0 and len(self.kl_history) > 0:
            print()
            print('  ================================================================')
            print('  RESUMEN MÉTRICAS PPO')
            print('  ================================================================')
            print(f'    KL divergence:        mean={np.mean(self.kl_history):.4f}, '
                  f'max={np.max(self.kl_history):.4f}')
            print(f'    Clip fraction:        mean={np.mean(self.clip_fraction_history)*100:.1f}%, '
                  f'max={np.max(self.clip_fraction_history)*100:.1f}%')
            print(f'    Entropy:              mean={np.mean(self.entropy_history):.3f}, '
                  f'final={self.entropy_history[-1]:.3f}')
            print(f'    Explained variance:   mean={np.mean(self.explained_var_history):.3f}, '
                  f'final={self.explained_var_history[-1]:.3f}')
            print('  ================================================================')
        
        # NUEVO v2.0: Imprimir resumen de problemas detectados con recomendaciones
        self._print_problem_summary()
        
        # Generar gráficas de diagnóstico PPO
        if len(self.kl_history) > 1:
            self._generate_ppo_graphs()
        
        # Generar gráficas de KPIs CityLearn
        if len(self.kpi_steps_history) > 1:
            print('\n  📊 Generando gráficos KPIs CityLearn...')
            self._generate_kpi_graphs()
    
    def _generate_ppo_graphs(self) -> None:
        """
        Genera gráficas de diagnóstico para PPO.
        
        GRÁFICAS GENERADAS:
        ===================
        1. KL Divergence vs Steps
           - Si sube mucho → updates agresivos / inestabilidad
           - Línea roja en 0.02 (target_kl típico)
           - Línea naranja en 0.03 (warning threshold)
        
        2. Clip Fraction vs Steps
           - Alto sostenido (>30%) → LR alto, muchas epochs, batch pequeño
           - El "clip" está recortando demasiado
        
        3. Entropy vs Steps
           - Si cae a 0 muy temprano → política colapsa (poca exploración)
           - Debería decrecer gradualmente, NO colapsar
        
        4. Value Loss y Explained Variance vs Steps
           - Explained variance cerca de 1 es bueno
           - ~0 o negativa indica crítico malo
        
        Referencias:
          [1] Schulman et al. (2017) PPO paper
          [2] OpenAI Spinning Up: https://spinningup.openai.com/en/latest/algorithms/ppo.html
          [3] CleanRL PPO implementation metrics
        """
        try:
            # Crear directorio si no existe
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Convertir a arrays numpy
            steps = np.array(self.steps_history)
            kl = np.array(self.kl_history)
            clip_frac = np.array(self.clip_fraction_history) * 100  # Convertir a %
            entropy = np.array(self.entropy_history)
            value_loss = np.array(self.value_loss_history)
            explained_var = np.array(self.explained_var_history)
            policy_loss = np.array(self.policy_loss_history)
            
            # Escala de steps (K = miles)
            steps_k = steps / 1000.0
            
            # ================================================================
            # FIGURA 1: KL Divergence vs Steps
            # ================================================================
            fig1, ax1 = plt.subplots(figsize=(10, 6))
            ax1.plot(steps_k, kl, 'b-', linewidth=1.5, label='Approx KL', alpha=0.8)
            
            # Smoothing con media móvil si hay suficientes puntos
            if len(kl) >= 10:
                window = min(10, len(kl) // 3)
                kl_smooth = pd.Series(kl).rolling(window=window, center=True).mean()
                ax1.plot(steps_k, kl_smooth, 'b-', linewidth=2.5, label='KL (smooth)', alpha=1.0)
            
            # Líneas de referencia
            ax1.axhline(y=0.02, color='orange', linestyle='--', linewidth=2, label='Target KL (0.02)')
            ax1.axhline(y=0.03, color='red', linestyle='--', linewidth=2, label='Warning (0.03)')
            
            ax1.set_xlabel('Steps (K)', fontsize=12)
            ax1.set_ylabel('KL Divergence', fontsize=12)
            ax1.set_title('PPO: KL Divergence vs Training Steps\n'
                         '(Si sube mucho → updates agresivos / inestabilidad)', fontsize=14)
            ax1.legend(loc='upper right')
            ax1.grid(True, alpha=0.3)
            ax1.set_ylim(bottom=0)
            
            # Guardar
            kl_path = self.output_dir / 'ppo_kl_divergence.png'
            fig1.tight_layout()
            fig1.savefig(kl_path, dpi=150, bbox_inches='tight')
            plt.close(fig1)
            print(f'    [GRAPH] KL Divergence: {kl_path}')
            
            # ================================================================
            # FIGURA 2: Clip Fraction vs Steps
            # ================================================================
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            ax2.plot(steps_k, clip_frac, 'g-', linewidth=1.5, label='Clip Fraction %', alpha=0.8)
            
            # Smoothing
            if len(clip_frac) >= 10:
                window = min(10, len(clip_frac) // 3)
                clip_smooth = pd.Series(clip_frac).rolling(window=window, center=True).mean()
                ax2.plot(steps_k, clip_smooth, 'g-', linewidth=2.5, label='Clip (smooth)', alpha=1.0)
            
            # Líneas de referencia
            ax2.axhline(y=30, color='red', linestyle='--', linewidth=2, label='Warning (30%)')
            ax2.axhline(y=20, color='orange', linestyle='--', linewidth=2, label='Typical max (20%)')
            
            ax2.set_xlabel('Steps (K)', fontsize=12)
            ax2.set_ylabel('Clip Fraction (%)', fontsize=12)
            ax2.set_title('PPO: Clip Fraction vs Training Steps\n'
                         '(Alto sostenido >30% → LR alto, muchas epochs, batch pequeño)', fontsize=14)
            ax2.legend(loc='upper right')
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim(0, 100)
            
            clip_path = self.output_dir / 'ppo_clip_fraction.png'
            fig2.tight_layout()
            fig2.savefig(clip_path, dpi=150, bbox_inches='tight')
            plt.close(fig2)
            print(f'    [GRAPH] Clip Fraction: {clip_path}')
            
            # ================================================================
            # FIGURA 3: Entropy vs Steps
            # ================================================================
            fig3, ax3 = plt.subplots(figsize=(10, 6))
            ax3.plot(steps_k, entropy, 'm-', linewidth=1.5, label='Entropy', alpha=0.8)
            
            # Smoothing
            if len(entropy) >= 10:
                window = min(10, len(entropy) // 3)
                entropy_smooth = pd.Series(entropy).rolling(window=window, center=True).mean()
                ax3.plot(steps_k, entropy_smooth, 'm-', linewidth=2.5, label='Entropy (smooth)', alpha=1.0)
            
            # Línea de referencia
            ax3.axhline(y=0.1, color='red', linestyle='--', linewidth=2, label='Collapse warning (0.1)')
            
            # Indicar zona peligrosa
            ax3.axhspan(0, 0.1, alpha=0.2, color='red', label='Zona de colapso')
            
            ax3.set_xlabel('Steps (K)', fontsize=12)
            ax3.set_ylabel('Entropy', fontsize=12)
            ax3.set_title('PPO: Entropy vs Training Steps\n'
                         '(Si cae a ~0 temprano → política colapsa, poca exploración)', fontsize=14)
            ax3.legend(loc='upper right')
            ax3.grid(True, alpha=0.3)
            ax3.set_ylim(bottom=0)
            
            entropy_path = self.output_dir / 'ppo_entropy.png'
            fig3.tight_layout()
            fig3.savefig(entropy_path, dpi=150, bbox_inches='tight')
            plt.close(fig3)
            print(f'    [GRAPH] Entropy: {entropy_path}')
            
            # ================================================================
            # FIGURA 4: Value Loss y Explained Variance vs Steps
            # ================================================================
            fig4, (ax4a, ax4b) = plt.subplots(2, 1, figsize=(10, 10), sharex=True)
            
            # 4a: Value Loss
            ax4a.plot(steps_k, value_loss, 'r-', linewidth=1.5, label='Value Loss', alpha=0.8)
            if len(value_loss) >= 10:
                window = min(10, len(value_loss) // 3)
                vl_smooth = pd.Series(value_loss).rolling(window=window, center=True).mean()
                ax4a.plot(steps_k, vl_smooth, 'r-', linewidth=2.5, label='Value Loss (smooth)', alpha=1.0)
            
            ax4a.set_ylabel('Value Loss', fontsize=12)
            ax4a.set_title('PPO: Value Loss vs Training Steps', fontsize=14)
            ax4a.legend(loc='upper right')
            ax4a.grid(True, alpha=0.3)
            
            # 4b: Explained Variance
            ax4b.plot(steps_k, explained_var, 'c-', linewidth=1.5, label='Explained Variance', alpha=0.8)
            if len(explained_var) >= 10:
                window = min(10, len(explained_var) // 3)
                ev_smooth = pd.Series(explained_var).rolling(window=window, center=True).mean()
                ax4b.plot(steps_k, ev_smooth, 'c-', linewidth=2.5, label='Expl.Var (smooth)', alpha=1.0)
            
            # Líneas de referencia
            ax4b.axhline(y=1.0, color='green', linestyle='--', linewidth=2, label='Perfecto (1.0)')
            ax4b.axhline(y=0.0, color='orange', linestyle='--', linewidth=2, label='Random (0.0)')
            
            # Zona de crítico malo
            ax4b.axhspan(-1, 0, alpha=0.2, color='red', label='Crítico malo (<0)')
            
            ax4b.set_xlabel('Steps (K)', fontsize=12)
            ax4b.set_ylabel('Explained Variance', fontsize=12)
            ax4b.set_title('PPO: Explained Variance vs Training Steps\n'
                          '(Cerca de 1 = bueno, ~0 o negativo = crítico fallando)', fontsize=14)
            ax4b.legend(loc='lower right')
            ax4b.grid(True, alpha=0.3)
            ax4b.set_ylim(-0.5, 1.1)
            
            value_path = self.output_dir / 'ppo_value_metrics.png'
            fig4.tight_layout()
            fig4.savefig(value_path, dpi=150, bbox_inches='tight')
            plt.close(fig4)
            print(f'    [GRAPH] Value Metrics: {value_path}')
            
            # ================================================================
            # FIGURA 5 (BONUS): Dashboard combinado
            # ================================================================
            fig5, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            # KL (top-left)
            axes[0, 0].plot(steps_k, kl, 'b-', linewidth=1.5, alpha=0.7)
            axes[0, 0].axhline(y=0.02, color='orange', linestyle='--')
            axes[0, 0].axhline(y=0.03, color='red', linestyle='--')
            axes[0, 0].set_ylabel('KL Divergence')
            axes[0, 0].set_title('KL Divergence')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Clip Fraction (top-right)
            axes[0, 1].plot(steps_k, clip_frac, 'g-', linewidth=1.5, alpha=0.7)
            axes[0, 1].axhline(y=30, color='red', linestyle='--')
            axes[0, 1].set_ylabel('Clip Fraction (%)')
            axes[0, 1].set_title('Clip Fraction')
            axes[0, 1].grid(True, alpha=0.3)
            axes[0, 1].set_ylim(0, 100)
            
            # Entropy (bottom-left)
            axes[1, 0].plot(steps_k, entropy, 'm-', linewidth=1.5, alpha=0.7)
            axes[1, 0].axhline(y=0.1, color='red', linestyle='--')
            axes[1, 0].axhspan(0, 0.1, alpha=0.2, color='red')
            axes[1, 0].set_xlabel('Steps (K)')
            axes[1, 0].set_ylabel('Entropy')
            axes[1, 0].set_title('Entropy')
            axes[1, 0].grid(True, alpha=0.3)
            
            # Explained Variance (bottom-right)
            axes[1, 1].plot(steps_k, explained_var, 'c-', linewidth=1.5, alpha=0.7)
            axes[1, 1].axhline(y=1.0, color='green', linestyle='--')
            axes[1, 1].axhline(y=0.0, color='orange', linestyle='--')
            axes[1, 1].axhspan(-0.5, 0, alpha=0.2, color='red')
            axes[1, 1].set_xlabel('Steps (K)')
            axes[1, 1].set_ylabel('Explained Variance')
            axes[1, 1].set_title('Explained Variance')
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].set_ylim(-0.5, 1.1)
            
            fig5.suptitle('PPO Training Diagnostics Dashboard', fontsize=16, fontweight='bold')
            
            dashboard_path = self.output_dir / 'ppo_dashboard.png'
            fig5.tight_layout()
            fig5.savefig(dashboard_path, dpi=150, bbox_inches='tight')
            plt.close(fig5)
            print(f'    [GRAPH] Dashboard: {dashboard_path}')
            
            print(f'  [OK] 5 gráficas PPO generadas en: {self.output_dir}')
            
        except Exception as e:
            print(f'  [WARNING] Error generando gráficas PPO: {e}')
            import traceback
            traceback.print_exc()


def main():
    """
    Entrenamiento principal con error handling robusto.

    Pipeline completo:
    1. Configurar device (GPU/CPU)
    2. Cargar rewards multiobjetivo
    3. Cargar datos OE2 (timeseries reales)
    4. Crear environment Gymnasium
    5. Entrenar PPO con stable-baselines3
    6. Validar con episodios determinísticos

    Referencias:
      [1] Schulman et al. (2017) "Proximal Policy Optimization Algorithms"
      [2] Stable-Baselines3: https://stable-baselines3.readthedocs.io/
      [3] CityLearn v2 Documentation
    """

    HOURS_PER_YEAR: int = 8760
    NUM_EPISODES: int = 10  # 10 episodios = 87,600 timesteps para entrenamiento robusto
    TOTAL_TIMESTEPS: int = NUM_EPISODES * HOURS_PER_YEAR

    # ========================================================================
    # PRE-PASO: VALIDAR DATASETS OE2 Y LIMPIAR CHECKPOINTS
    # ========================================================================
    oe2_summary = validate_oe2_datasets()  # Valida los 5 archivos OE2 obligatorios
    clean_checkpoints_ppo()

    print('='*80)
    print('ENTRENAR PPO - MULTIOBJETIVO CON DATOS REALES - {} EPISODIOS'.format(NUM_EPISODES))
    print('='*80)
    print('Inicio: {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print()

    # ========================================================================
    # PASO 1: CONFIGURACION Y DISPOSITIVO
    # ========================================================================
    try:
        # Determinar device: CUDA si disponible, sino CPU
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu'

        if device == 'cuda':
            gpu_name: str = torch.cuda.get_device_name(0)
            gpu_memory: float = torch.cuda.get_device_properties(0).total_memory / 1e9
            cuda_version: Optional[str] = getattr(torch.version, 'cuda', None)  # type: ignore
            print('GPU DISPONIBLE: {}'.format(gpu_name))
            print('  RAM: {:.1f} GB'.format(gpu_memory))
            print('  CUDA: {}'.format(cuda_version))
            print()

        ppo_config: PPOConfig = PPOConfig(device=device)
        # Usar directorios globales
        checkpoint_dir = CHECKPOINT_DIR
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        output_dir = OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Device: %s | Batch: %d | Epochs: %d", device, ppo_config.batch_size, ppo_config.n_epochs)

    except (RuntimeError, AttributeError, ValueError) as exc:
        logger.error("ERROR en configuracion: %s", exc)
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # PASO 2: CARGAR CONFIG Y REWARDS
    # ========================================================================
    try:
        print('[PASO 1] Cargar configuracion y contexto OE2')
        print('-'*80)

        with open('configs/default.yaml', 'r', encoding='utf-8') as f:
            _ = yaml.safe_load(f)  # Validate YAML syntax
        logger.info("Config validado: default.yaml OK")

        reward_weights = create_iquitos_reward_weights("co2_focus")
        context: IquitosContext = IquitosContext()
        reward_calc: MultiObjectiveReward = MultiObjectiveReward(weights=reward_weights, context=context)

        print('  REWARD WEIGHTS (ACTUALIZADOS 2026-02-07):')
        print('    CO2 grid (0.50): Minimizar importacion grid')
        print('    Solar (0.20): Autoconsumo PV')
        print('    EV satisfaction (0.30): SOC 90% (PRIORIDAD MAXIMA)')
        print('    Cost (0.10): Minimizar costo')
        print('    Grid stability (0.05): Suavizar picos')
        if reward_weights is not None:
            print('  [Valores cargados: CO2={:.2f}, Solar={:.2f}, EV={:.2f}, Cost={:.2f}, Grid={:.2f}]'.format(
                reward_weights.co2, reward_weights.solar, reward_weights.ev_satisfaction,
                reward_weights.cost, reward_weights.grid_stability))
        print()

    except (ImportError, FileNotFoundError, ValueError) as exc:
        logger.error("ERROR cargando rewards: %s", exc)
        traceback.print_exc()
        sys.exit(1)


    # ========================================================================
    # PASO 3: CARGAR DATOS REALES OE2
    # ========================================================================
    try:
        print('[PASO 2] Cargar datos OE2 ({} horas = 1 ano)'.format(HOURS_PER_YEAR))
        print('-'*80)

        # ====================================================================
        # SOLAR - RUTA REAL OE2 v5.5
        # ====================================================================
        solar_path: Path = Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
        if not solar_path.exists():
            raise FileNotFoundError(f"OBLIGATORIO: Solar CSV REAL no encontrado: {solar_path}")
        
        df_solar = pd.read_csv(solar_path)
        # Columnasvalidas: pv_generation_kwh > ac_power_kw > potencia_kw
        if 'pv_generation_kwh' in df_solar.columns:
            col = 'pv_generation_kwh'
        elif 'ac_power_kw' in df_solar.columns:
            col = 'ac_power_kw'
        elif 'potencia_kw' in df_solar.columns:
            col = 'potencia_kw'
        else:
            raise KeyError(f"Solar CSV debe tener 'pv_generation_kwh' o 'ac_power_kw'. Columnas: {list(df_solar.columns)}")
        
        solar_hourly = np.asarray(df_solar[col].values, dtype=np.float32)
        if len(solar_hourly) != HOURS_PER_YEAR:
            raise ValueError(f"Solar: {len(solar_hourly)} horas != {HOURS_PER_YEAR}")
        logger.info("[SYNC A2C] Solar: columna='%s' | %.0f kWh/año (8760h) | Path: %s", col, float(np.sum(solar_hourly)), solar_path.name)

        # ====================================================================
        # CHARGERS (38 sockets) - DATOS REALES DIRECTOS
        # ====================================================================
        # Priorizar archivo con 38 sockets reales, fallback a 19 chargers expandido
        charger_real_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
        charger_csv_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
        
        if charger_real_path.exists():
            # Archivo real con 38 sockets + timestamp
            df_chargers = pd.read_csv(charger_real_path)
            # Extraer SOLO las columnas de potencia de los sockets (socket_*_charger_power_kw)
            power_cols = [c for c in df_chargers.columns if 'charger_power_kw' in c.lower()]
            if len(power_cols) == 0:
                # Si no hay columnas charger_power_kw, intentar con todas las numéricas excepto tiempo
                data_cols = [c for c in df_chargers.columns if 'timestamp' not in c.lower() and 'time' not in c.lower() and 'type' not in c.lower() and 'vehicle' not in c.lower() and '_soc_' not in c.lower() and '_battery_' not in c.lower()]
                # Filtrar solo columnas numéricas
                power_cols = []
                for col in data_cols:
                    try:
                        _ = pd.to_numeric(df_chargers[col], errors='coerce').dropna()
                        if len(_) > 0:
                            power_cols.append(col)
                    except:
                        pass
            
            if len(power_cols) > 0:
                chargers_hourly = df_chargers[power_cols].values.astype(np.float32)
                if chargers_hourly.shape[0] != HOURS_PER_YEAR:
                    raise ValueError(f"Chargers real debe tener {HOURS_PER_YEAR} filas, tiene {chargers_hourly.shape[0]}")
                n_sockets = chargers_hourly.shape[1]
                total_demand = float(np.sum(chargers_hourly))
                logger.info("Chargers REALES (socket power columns): %d sockets | Demanda anual: %.0f kWh", 
                            n_sockets, total_demand)
            else:
                raise ValueError("No se encontraron columnas de potencia de sockets en chargers CSV")
        elif charger_csv_path.exists():
            df_chargers = pd.read_csv(charger_csv_path)
            # CSV contiene 38 columnas directas (19 chargers × 2 sockets cada uno) - OE2 v5.2
            chargers_raw = df_chargers.values.astype(np.float32)  # (8760, 19)
            if chargers_raw.shape[0] != HOURS_PER_YEAR:
                raise ValueError(f"Chargers CSV debe tener {HOURS_PER_YEAR} filas, tiene {chargers_raw.shape[0]}")
            # Expandir: cada charger tiene 2 sockets, distribuir demanda (v5.2)
            n_charger_units = chargers_raw.shape[1]  # 19
            chargers_hourly = np.zeros((HOURS_PER_YEAR, n_charger_units * 2), dtype=np.float32)
            for i in range(n_charger_units):
                # Distribuir demanda del charger entre sus 2 sockets (v5.2)
                for s in range(2):
                    socket_idx = i * 2 + s
                    # Socket recibe 50% de la demanda base (balanced)
                    chargers_hourly[:, socket_idx] = chargers_raw[:, i] * 0.5
            n_sockets = chargers_hourly.shape[1]  # 38
            total_demand = float(np.sum(chargers_hourly))
            logger.info("Chargers REALES: %d chargers x 4 = %d sockets | Demanda anual: %.0f kWh", 
                        n_charger_units, n_sockets, total_demand)
        else:
            # NO hay fallback sintético - archivos OE2 son obligatorios
            raise FileNotFoundError(
                f"OBLIGATORIO: Ningún archivo de chargers encontrado.\n"
                f"  Esperado (prioridad 1): {charger_real_path}\n"
                f"  Esperado (prioridad 2): {charger_csv_path}\n"
                "Ejecutar generación OE2 primero."
            )

        # ====================================================================
        # CHARGER STATISTICS (potencia máxima/media por socket) - 5to dataset OE2
        # ====================================================================
        charger_stats_path = Path('data/oe2/chargers/chargers_real_statistics.csv')
        charger_max_power: Optional[np.ndarray] = None
        charger_mean_power: Optional[np.ndarray] = None
        
        if charger_stats_path.exists():
            df_stats = pd.read_csv(charger_stats_path)
            if len(df_stats) >= 38:
                charger_max_power = df_stats['max_power_kw'].values[:38].astype(np.float32)
                charger_mean_power = df_stats['mean_power_kw'].values[:38].astype(np.float32)
                min_pwr = float(charger_max_power.min())
                max_pwr = float(charger_max_power.max())
                mean_pwr = float(charger_mean_power.mean())
                logger.info("Charger STATS (5to OE2): max_power=%.2f-%.2f kW, mean_power=%.2f kW", 
                            min_pwr, max_pwr, mean_pwr)
            else:
                logger.warning("Charger STATS: %d filas < 38, usando valores por defecto", len(df_stats))
        else:
            logger.warning("Charger STATS: archivo no encontrado, usando valores por defecto")

        # ====================================================================
        # MALL DEMAND - EXACTAMENTE IGUAL A A2C
        # ====================================================================
        mall_path = Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')
        if not mall_path.exists():
            # Fallback (mismo que A2C)
            mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
            if not mall_path.exists():
                raise FileNotFoundError(f"OBLIGATORIO: Mall CSV no encontrado (esperado: data/interim/oe2/demandamallkwh/demandamallhorakwh.csv)")
        
        # Intentar cargar con diferentes separadores (compatibilidad A2C)
        try:
            df_mall = pd.read_csv(mall_path, sep=';', encoding='utf-8')
        except Exception:
            df_mall = pd.read_csv(mall_path, encoding='utf-8')
        
        col = df_mall.columns[-1]
        mall_data = np.asarray(df_mall[col].values[:HOURS_PER_YEAR], dtype=np.float32)
        if len(mall_data) < HOURS_PER_YEAR:
            pad_width = ((0, HOURS_PER_YEAR - len(mall_data)),)
            mall_hourly = np.pad(mall_data, pad_width, mode='wrap')
        else:
            mall_hourly = mall_data
        logger.info("[SYNC A2C] Mall: %.0f kWh/año (promedio %.1f kW/h) | Path: %s", float(np.sum(mall_hourly)), float(np.mean(mall_hourly)), mall_path.name)

        # ====================================================================
        # BESS SOC - EXACTAMENTE IGUAL A A2C (con fallbacks idénticos)
        # ====================================================================
        bess_paths = [
            Path('data/oe2/bess/bess_ano_2024.csv'),
            Path('data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv'),
            Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv'),
        ]
        bess_path = next((p for p in bess_paths if p.exists()), None)
        
        if bess_path is None:
            raise FileNotFoundError(
                f"OBLIGATORIO: Ningún archivo BESS encontrado.\n"
                f"  Esperados: {[str(p) for p in bess_paths]}\n"
                "Ejecutar generación OE2 primero."
            )

        df_bess = pd.read_csv(bess_path, encoding='utf-8')
        soc_cols = [c for c in df_bess.columns if 'soc' in c.lower()]
        if not soc_cols:
            raise KeyError(f"BESS CSV debe tener columna 'soc'. Columnas: {list(df_bess.columns)}")
        
        bess_soc_raw = np.asarray(df_bess[soc_cols[0]].values[:HOURS_PER_YEAR], dtype=np.float32)
        # Normalizar si está en [0,100] en lugar de [0,1]
        bess_soc = (bess_soc_raw / 100.0 if float(np.max(bess_soc_raw)) > 1.0 else bess_soc_raw)
        logger.info("[SYNC A2C] BESS: SOC media %.1f%% | Path: %s", float(np.mean(bess_soc)) * 100.0, bess_path.name)

        print()

    except (FileNotFoundError, KeyError, ValueError, pd.errors.ParserError) as exc:
        logger.error("ERROR cargando datos OE2: %s", exc)
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # PASO 4: CREAR ENVIRONMENT
    # ========================================================================
    try:
        print('[PASO 3] Crear environment Gymnasium')
        print('-'*80)

        env: CityLearnEnvironment = CityLearnEnvironment(
            reward_calc=reward_calc,
            context=context,
            solar_kw=solar_hourly,
            chargers_kw=chargers_hourly,
            mall_kw=mall_hourly,
            bess_soc=bess_soc,
            charger_max_power_kw=charger_max_power,
            charger_mean_power_kw=charger_mean_power,
            max_steps=HOURS_PER_YEAR
        )
        
        # ====================================================================
        # VECNORMALIZE WRAPPER (CRÍTICO para resolver Explained Variance negativo)
        # ====================================================================
        # Engstrom 2020 "Implementation Matters": "VecNormalize es ESENCIAL
        # para PPO. Sin él, el value function no puede aprender returns de
        # diferentes magnitudes."
        #
        # Normaliza:
        # - Observaciones: running mean/std → todas las features en ~N(0,1)
        # - Returns: running mean/std → value targets en rango aprendible
        # ====================================================================
        env_base = env  # Guardar referencia al env base para logging
        vec_env = DummyVecEnv([lambda: env])  # Envolver en VecEnv
        env = VecNormalize(
            vec_env,
            norm_obs=True,      # Normalizar observaciones (running mean/std)
            norm_reward=True,   # Normalizar rewards/returns (CRÍTICO para EV)
            clip_obs=10.0,      # Clip observaciones a [-10, 10]
            clip_reward=5.0,    # REDUCIDO v5.3: 10.0 es muy agresivo, 5.0 permite más margen
            gamma=ppo_config.gamma,  # Mismo gamma para return normalization
        )
        logger.info("VecNormalize aplicado: norm_obs=True, norm_reward=True (gamma=%.2f)", ppo_config.gamma)

        logger.info("Environment creado:")
        logger.info("  Observation: %s", str(env.observation_space.shape))
        logger.info("  Action: %s", str(env.action_space.shape))
        logger.info("  Timesteps/episodio: %d (1 ano completo)", HOURS_PER_YEAR)
        print()

    except (ValueError, AttributeError, TypeError) as exc:
        logger.error("ERROR creando environment: %s", exc)
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # PASO 5: CREAR Y ENTRENAR PPO CON STABLE-BASELINES3
    # ========================================================================
    # Referencia: [Schulman et al. 2017] PPO es un algoritmo on-policy que ACTUALiza
    # la política usando experiencia recolectada en el episodio ACTUAL, realizando
    # múltiples pasos de gradiente con clipping para estabilidad.

    try:
        print('[PASO 4] Crear agente PPO')
        print('-'*80)

        # ====================================================================
        # LEARNING RATE SCHEDULE (Engstrom 2020: "CRÍTICO para PPO")
        # ====================================================================
        # LR annealing lineal: decrece de LR_initial → 0 durante el entrenamiento
        # Esto previene "desaprendizaje" al final del entrenamiento y estabiliza
        # la convergencia del value function.
        #
        # Fórmula: lr(t) = lr_initial * (1 - t/total_timesteps)
        # ====================================================================
        total_timesteps_planned = NUM_EPISODES * HOURS_PER_YEAR
        initial_lr = ppo_config.learning_rate
        
        def linear_lr_schedule(progress_remaining: float) -> float:
            """
            Learning rate schedule lineal (Engstrom 2020, Schulman 2017).
            
            Args:
                progress_remaining: 1.0 al inicio, 0.0 al final
            
            Returns:
                Learning rate actual = initial_lr * progress_remaining
            """
            return initial_lr * progress_remaining
        
        logger.info("LR Schedule habilitado: %.2e → 0 (lineal sobre %d timesteps)", 
                    initial_lr, total_timesteps_planned)

        model: PPO = PPO(
            'MlpPolicy',
            env,
            learning_rate=linear_lr_schedule,  # SCHEDULE en vez de valor fijo
            n_steps=ppo_config.n_steps,
            batch_size=ppo_config.batch_size,
            n_epochs=ppo_config.n_epochs,
            gamma=ppo_config.gamma,
            gae_lambda=ppo_config.gae_lambda,
            clip_range=ppo_config.clip_range,
            clip_range_vf=ppo_config.clip_range_vf,  # NUEVO: Clip range para value function
            ent_coef=ppo_config.ent_coef,
            vf_coef=ppo_config.vf_coef,
            max_grad_norm=ppo_config.max_grad_norm,
            target_kl=ppo_config.target_kl,  # NUEVO: Early stop si KL > target
            normalize_advantage=ppo_config.normalize_advantage,
            device=device,
            policy_kwargs=ppo_config.policy_kwargs,
            verbose=0
        )

        logger.info("PPO creado: LR=schedule(%.2e→0), n_steps=%d, target_kl=%s, device=%s", 
                    initial_lr, ppo_config.n_steps, ppo_config.target_kl, device)
        print('  Hiperparametros PPO v5.0 [Papers: Schulman 2017, Engstrom 2020, Andrychowicz 2021]:')
        print('    Learning Rate:     {:.6f} → 0 (schedule lineal, CRÍTICO)'.format(initial_lr))
        print('    N Steps (rollout): {}  (más contexto = mejor value function)'.format(ppo_config.n_steps))
        print('    Batch Size:        {}  (minibatch dentro del rollout)'.format(ppo_config.batch_size))
        print('    Epochs per update: {}  (3-10, mas = sample efficiency pero overfitting)'.format(ppo_config.n_epochs))
        print('    Gamma:             {}  (REDUCIDO para episodios de 8760 pasos)'.format(ppo_config.gamma))
        print('    Clip Range (eps):  {}  (0.1-0.3, limita cambio de politica)'.format(ppo_config.clip_range))
        print('    GAE Lambda:        {}  (0.9-0.97, bias-variance tradeoff)'.format(ppo_config.gae_lambda))
        print('    Entropy Coef:      {}  (0.0-0.02, promueve exploracion)'.format(ppo_config.ent_coef))
        print('    Value Coef:        {}  (peso del value loss)'.format(ppo_config.vf_coef))
        print('    Max Grad Norm:     {}  (gradient clipping)'.format(ppo_config.max_grad_norm))
        print('    Target KL:         {}  (early stop si KL >, ESTABILIDAD)'.format(ppo_config.target_kl))
        print('    Clip Range VF:     {}  (DESHABILITADO - daña EV según Andrychowicz 2021)'.format(ppo_config.clip_range_vf))
        print('    Normalize Adv:     {}  (normalizar advantages)'.format(ppo_config.normalize_advantage))
        # Arquitectura separada Actor/Critic
        pi_arch = ppo_config.policy_kwargs['net_arch']['pi']
        vf_arch = ppo_config.policy_kwargs['net_arch']['vf']
        print('    Actor Network:     {} (policy)'.format(pi_arch))
        print('    Critic Network:    {} (value function, MÁS GRANDE)'.format(vf_arch))
        print('    VecNormalize:      norm_obs=True, norm_reward=True (CLAVE para EV)')
        print()

        # ====================================================================
        # ENTRENAMIENTO
        # ====================================================================
        print('[PASO 5] ENTRENAMIENTO CON DATOS REALES OE2')
        print('-'*80)

        speed_est: float = 1100.0 if device == 'cuda' else 70.0
        duration_est: float = TOTAL_TIMESTEPS / (speed_est * 60.0)

        print('  CONFIGURACION:')
        print('    Episodios: {} x {} horas = {:,} timesteps'.format(NUM_EPISODES, HOURS_PER_YEAR, TOTAL_TIMESTEPS))
        print('    Datos: 100% REALES (OE2 Iquitos)')
        print('    Device: {}'.format(device.upper()))
        print('    Duracion est.: ~{:.1f} minutos'.format(duration_est))
        print()
        print('  REWARD WEIGHTS (ACTUALIZADOS 2026-02-08 - LOG SAC):')
        print('    CO2 grid (0.35): Minimizar importacion grid')
        print('    Solar (0.20): Autoconsumo PV')
        print('    EV satisfaction (0.30): SOC 90%')
        print('    Cost (0.10): Minimizar costo')
        print('    Grid stability (0.05): Suavizar picos')
        print()
        print('  Iniciando entrenamiento...')
        print()

        # CALLBACKS: Checkpoint + DetailedLogging + PPOMetrics
        checkpoint_callback: CheckpointCallback = CheckpointCallback(
            save_freq=2000,
            save_path=str(checkpoint_dir),
            name_prefix='ppo_model',
            verbose=0
        )
        
        # DetailedLoggingCallback para tracking de dominio (CO2, solar, EVs)
        # NOTA: Usar env_base (raw) para acceder a métricas, env es VecNormalize
        logging_callback = DetailedLoggingCallback(
            env_ref=env_base,  # Raw environment (no VecNormalize)
            output_dir=output_dir,
            verbose=1
        )
        
        # NUEVO: PPOMetricsCallback para metricas especificas de PPO
        # Loguea: KL, clip_fraction, entropy, policy/value loss, explained_variance
        # Genera graficas de diagnostico al final del entrenamiento
        ppo_metrics_callback = PPOMetricsCallback(
            log_freq=ppo_config.n_steps,  # Loguear cada update (despues de rollout)
            eval_freq=HOURS_PER_YEAR,  # Eval deterministic cada episodio
            output_dir=output_dir,  # Directorio para guardar graficas
            verbose=1
        )
        
        # Combinar callbacks
        from stable_baselines3.common.callbacks import CallbackList
        callbacks = CallbackList([checkpoint_callback, logging_callback, ppo_metrics_callback])

        t_start: float = time.time()
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=callbacks,
            progress_bar=True,
            reset_num_timesteps=False
        )
        elapsed = time.time() - t_start

        # Guardar modelo final
        final_path: Path = checkpoint_dir / 'ppo_final.zip'
        model.save(str(final_path))

        speed_achieved: float = float(TOTAL_TIMESTEPS / elapsed)
        logger.info("Entrenamiento exitoso: %.1f min (speed: %.0f steps/s)", elapsed / 60.0, speed_achieved)
        logger.info("Modelo guardado: %s", str(final_path))
        print()
        print('Entrenamiento completado: {:.1f} min ({:.0f} steps/s)'.format(elapsed / 60.0, speed_achieved))
        print()

    except (RuntimeError, ValueError, OSError, AttributeError) as exc:
        logger.error("ERROR en entrenamiento: %s", exc)
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # PASO 6: VALIDACION - EPISODIOS DETERMINÍSTICOS
    # ========================================================================
    # Evaluación con acciones determinísticas (sin aleatoriedad) para medir
    # performance real del agente entrenado. Referencias:
    # [Schulman et al. 2017] recomienda validación en ambiente sin exploración.

    NUM_VALIDATION_EPISODES: int = 10

    try:
        print('[PASO 6] VALIDACION - {} EPISODIOS DETERMINISICOS'.format(NUM_VALIDATION_EPISODES))
        print('-'*80)

        val_metrics: Dict[str, list] = {
            'reward': [],
            'co2_avoided': [],
            'solar_kwh': [],
            'grid_import': [],
        }

        for ep_num in range(NUM_VALIDATION_EPISODES):
            # VecNormalize no soporta seed en reset(), usar reset sin argumentos
            obs = env.reset()
            done: bool = False
            episode_steps: int = 0
            
            # Acumuladores por episodio - se resetean cada episodio
            episode_reward_acc: float = 0.0
            episode_co2_acc: float = 0.0
            episode_solar_acc: float = 0.0  
            episode_grid_acc: float = 0.0

            while not done:
                # Deterministic=True: usar la acción con máxima probabilidad
                action, _ = model.predict(obs, deterministic=True)
                # VecNormalize usa API vieja: 4 valores (obs, reward, done, info)
                obs, reward, done, info = env.step(action)
                
                # Acumular reward (puede ser array)
                step_reward = float(reward[0]) if hasattr(reward, '__len__') else float(reward)
                episode_reward_acc += step_reward
                
                # Extraer métricas del info dict (VecEnv devuelve lista de info dicts)
                step_info = info[0] if isinstance(info, (list, tuple)) else info
                
                # Acumular métricas del step
                if isinstance(step_info, dict):
                    # CO2 evitado total (kg)
                    if 'co2_avoided_total_kg' in step_info:
                        episode_co2_acc += float(step_info['co2_avoided_total_kg'])
                    elif 'co2_avoided' in step_info:
                        episode_co2_acc += float(step_info['co2_avoided'])
                    
                    # Solar generado (kWh) - NOMBRES ESTÁNDAR COMPATIBLES
                    if 'solar_kw' in step_info:
                        episode_solar_acc += float(step_info['solar_kw'])
                    elif 'solar_generation_kwh' in step_info:
                        episode_solar_acc += float(step_info['solar_generation_kwh'])
                    elif 'solar_kwh' in step_info:
                        episode_solar_acc += float(step_info['solar_kwh'])
                    
                    # Grid import (kWh) - NOMBRES ESTÁNDAR COMPATIBLES
                    if 'grid_import_kw' in step_info:
                        episode_grid_acc += float(step_info['grid_import_kw'])
                    elif 'grid_import_kwh' in step_info:
                        episode_grid_acc += float(step_info['grid_import_kwh'])
                
                # done puede ser array en VecEnv
                if hasattr(done, '__len__'):
                    done = done[0]
                episode_steps += 1

            # Guardar métricas del episodio completo
            val_metrics['reward'].append(episode_reward_acc)
            val_metrics['co2_avoided'].append(episode_co2_acc)
            val_metrics['solar_kwh'].append(episode_solar_acc)
            val_metrics['grid_import'].append(episode_grid_acc)

            logger.info("  Episodio %d/%d: %d steps | R=%8.1f | CO2=%10.0f kg | Solar=%10.0f kWh",
                       ep_num + 1, NUM_VALIDATION_EPISODES, episode_steps,
                       episode_reward_acc,
                       episode_co2_acc,
                       episode_solar_acc)

        print()
        print('='*80)
        print('RESULTADOS FINALES - ENTRENAMIENTO Y VALIDACION')
        print('='*80)

        # Calcular estadísticas
        reward_mean: float = float(np.mean(val_metrics['reward'])) if val_metrics['reward'] else 0.0
        reward_std: float = float(np.std(val_metrics['reward'])) if len(val_metrics['reward']) > 1 else 0.0
        co2_mean: float = float(np.mean(val_metrics['co2_avoided'])) if val_metrics['co2_avoided'] else 0.0
        solar_mean: float = float(np.mean(val_metrics['solar_kwh'])) if val_metrics['solar_kwh'] else 0.0
        grid_mean: float = float(np.mean(val_metrics['grid_import'])) if val_metrics['grid_import'] else 0.0

        print()
        print('ENTRENAMIENTO:')
        print('  Total timesteps: {:,}'.format(TOTAL_TIMESTEPS))
        print('  Duracion: {:.1f} minutos ({:.0f} steps/s)'.format(elapsed / 60.0, speed_achieved))
        print('  Device: {}'.format(device.upper()))
        print()
        print('VALIDACION ({} episodios):'.format(NUM_VALIDATION_EPISODES))
        print('  Reward promedio:        {:12.2f} ± {:.2f}'.format(reward_mean, reward_std))
        print('  CO2 evitado (kg):       {:12.0f}'.format(co2_mean))
        print('  Solar aprovechado (kWh):  {:12.0f}'.format(solar_mean))
        print('  Grid import (kWh):      {:12.0f}'.format(grid_mean))
        print()

        # ====================================================================
        # GUARDAR METRICAS EN JSON
        # ====================================================================
        summary: Dict[str, Any] = {
            'timestamp': datetime.now().isoformat(),
            'agent': 'PPO',
            'project': 'pvbesscar',
            'location': 'Iquitos, Peru',
            'co2_factor_kg_per_kwh': CO2_FACTOR_IQUITOS,
            'training': {
                'total_timesteps': int(TOTAL_TIMESTEPS),
                'episodes': int(NUM_EPISODES),
                'duration_seconds': float(elapsed),
                'speed_steps_per_second': float(speed_achieved),
                'device': str(device),
                'hyperparameters': {
                    'learning_rate': ppo_config.learning_rate,
                    'n_steps': ppo_config.n_steps,
                    'batch_size': ppo_config.batch_size,
                    'n_epochs': ppo_config.n_epochs,
                    'gamma': ppo_config.gamma,
                    'gae_lambda': ppo_config.gae_lambda,
                    'clip_range': ppo_config.clip_range,
                    'ent_coef': ppo_config.ent_coef,
                    'vf_coef': ppo_config.vf_coef,
                }
            },
            'validation': {
                'num_episodes': int(NUM_VALIDATION_EPISODES),
                'mean_reward': float(reward_mean),
                'std_reward': float(reward_std),
                'mean_co2_avoided_kg': float(co2_mean),
                'mean_solar_kwh': float(solar_mean),
                'mean_grid_import_kwh': float(grid_mean),
            },
            'training_evolution': {
                'episode_rewards': logging_callback.episode_rewards,
                'episode_co2_grid': logging_callback.episode_co2_grid,
                'episode_co2_avoided_indirect': logging_callback.episode_co2_avoided_indirect,
                'episode_co2_avoided_direct': logging_callback.episode_co2_avoided_direct,
                'episode_solar_kwh': logging_callback.episode_solar_kwh,
                'episode_ev_charging': logging_callback.episode_ev_charging,
                'episode_grid_import': logging_callback.episode_grid_import,
                # [OK] NUEVAS métricas de evolución
                'episode_grid_stability': logging_callback.episode_grid_stability,
                'episode_cost_usd': logging_callback.episode_cost_usd,
                'episode_motos_charged': logging_callback.episode_motos_charged,
                'episode_mototaxis_charged': logging_callback.episode_mototaxis_charged,
                'episode_bess_discharge_kwh': logging_callback.episode_bess_discharge_kwh,
                'episode_bess_charge_kwh': logging_callback.episode_bess_charge_kwh,
                'episode_avg_socket_setpoint': logging_callback.episode_avg_socket_setpoint,
                'episode_socket_utilization': logging_callback.episode_socket_utilization,
                'episode_bess_action_avg': logging_callback.episode_bess_action_avg,
            },
            # [OK] NUEVAS secciones de métricas detalladas (como A2C)
            'summary_metrics': {
                'total_co2_avoided_indirect_kg': float(sum(logging_callback.episode_co2_avoided_indirect)),
                'total_co2_avoided_direct_kg': float(sum(logging_callback.episode_co2_avoided_direct)),
                'total_co2_avoided_kg': float(sum(logging_callback.episode_co2_avoided_indirect) + sum(logging_callback.episode_co2_avoided_direct)),
                'total_cost_usd': float(sum(logging_callback.episode_cost_usd)),
                'avg_grid_stability': float(np.mean(logging_callback.episode_grid_stability)) if logging_callback.episode_grid_stability else 0.0,
                'max_motos_charged': int(max(logging_callback.episode_motos_charged)) if logging_callback.episode_motos_charged else 0,
                'max_mototaxis_charged': int(max(logging_callback.episode_mototaxis_charged)) if logging_callback.episode_mototaxis_charged else 0,
                'total_bess_discharge_kwh': float(sum(logging_callback.episode_bess_discharge_kwh)),
                'total_bess_charge_kwh': float(sum(logging_callback.episode_bess_charge_kwh)),
            },
            'control_progress': {
                'avg_socket_setpoint_evolution': logging_callback.episode_avg_socket_setpoint,
                'socket_utilization_evolution': logging_callback.episode_socket_utilization,
                'bess_action_evolution': logging_callback.episode_bess_action_avg,
                'description': 'Evolución del aprendizaje de control por episodio',
            },
            'reward_components_avg': {
                'r_solar': float(np.mean(logging_callback.episode_r_solar)) if logging_callback.episode_r_solar else 0.0,
                'r_cost': float(np.mean(logging_callback.episode_r_cost)) if logging_callback.episode_r_cost else 0.0,
                'r_ev': float(np.mean(logging_callback.episode_r_ev)) if logging_callback.episode_r_ev else 0.0,
                'r_grid': float(np.mean(logging_callback.episode_r_grid)) if logging_callback.episode_r_grid else 0.0,
                'r_co2': float(np.mean(logging_callback.episode_r_co2)) if logging_callback.episode_r_co2 else 0.0,
                'episode_r_solar': logging_callback.episode_r_solar,
                'episode_r_cost': logging_callback.episode_r_cost,
                'episode_r_ev': logging_callback.episode_r_ev,
                'episode_r_grid': logging_callback.episode_r_grid,
                'episode_r_co2': logging_callback.episode_r_co2,
                'description': 'Componentes de reward promedio por episodio',
            },
            'vehicle_charging': {
                'motos_total': 112,
                'mototaxis_total': 16,
                'motos_charged_per_episode': logging_callback.episode_motos_charged,
                'mototaxis_charged_per_episode': logging_callback.episode_mototaxis_charged,
                'description': 'Conteo real de VEHICULOS cargados (setpoint > 50%)',
            },
            'model_path': str(final_path),
        }

        # Función para convertir numpy types a Python types (JSON serializable)
        def convert_to_native_types(obj):
            """Convertir numpy/pandas types a tipos nativos de Python."""
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.floating, np.float32, np.float64)):
                return float(obj) if isinstance(obj, (np.floating, np.float32, np.float64)) else int(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_native_types(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_native_types(item) for item in obj]
            return obj
        
        # Convertir summary a tipos nativos
        summary = convert_to_native_types(summary)
        
        metrics_file: Path = output_dir / 'ppo_training_summary.json'
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # ========== GUARDAR 3 ARCHIVOS DE SALIDA ==========
        print('  GUARDANDO ARCHIVOS DE SALIDA:')

        # 1. result_ppo.json - Resumen completo del entrenamiento
        result_file = output_dir / 'result_ppo.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f'    [OK] {result_file}')

        # 2. timeseries_ppo.csv - Series temporales por hora
        timeseries_file = output_dir / 'timeseries_ppo.csv'
        if logging_callback.timeseries_records:
            df_timeseries = pd.DataFrame(logging_callback.timeseries_records)
            df_timeseries.to_csv(timeseries_file, index=False, encoding='utf-8')
            print(f'    [OK] {timeseries_file} ({len(df_timeseries):,} registros)')
        else:
            print(f'    [WARN] {timeseries_file} - sin datos')

        # 3. trace_ppo.csv - Trazabilidad paso a paso
        trace_file = output_dir / 'trace_ppo.csv'
        if logging_callback.trace_records:
            df_trace = pd.DataFrame(logging_callback.trace_records)
            df_trace.to_csv(trace_file, index=False, encoding='utf-8')
            print(f'    [OK] {trace_file} ({len(df_trace):,} registros)')
        else:
            print(f'    [WARN] {trace_file} - sin datos')
        
        print()
        logger.info("Archivos generados en: %s", str(output_dir))

        print('='*80)
        print('ENTRENAMIENTO PPO COMPLETADO EXITOSAMENTE')
        print('='*80)
        print()

    except (RuntimeError, ValueError, OSError, AttributeError, KeyError) as exc:
        logger.error("ERROR en validacion: %s", exc)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

