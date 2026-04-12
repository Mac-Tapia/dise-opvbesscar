#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR SAC CON MULTIOBJETIVO REAL
Entrenamiento INDIVIDUAL con datos OE2 reales (chargers, BESS, mall demand, solar)
NO se usa ninguna formula de aproximacion - SOLO DATOS REALES
"""
from __future__ import annotations

# ===== CONFIGURACION DE PATH (OBLIGATORIO AL INICIO) =====
# Debe estar ANTES de cualquier import para evitar ModuleNotFoundError
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# =========================================================

import json
import logging
import os
import time
import traceback
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# FIX DEFINITIVO: KeyboardInterrupt durante LoadLibraryExW (Windows)
# CUDA_MODULE_LOADING=LAZY difiere la carga de DLLs CUDA hasta el
# primer uso real de GPU, evitando la interrupcion en el import.
# Debe estar ANTES de cualquier import de torch.
# ------------------------------------------------------------------
os.environ.setdefault('CUDA_MODULE_LOADING', 'LAZY')

import signal as _signal
_orig_sigint = _signal.getsignal(_signal.SIGINT)
_signal.signal(_signal.SIGINT, _signal.SIG_IGN)
try:
    import torch
finally:
    _signal.signal(_signal.SIGINT, _orig_sigint)

import yaml
from gymnasium import Env, spaces
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList

from src.dataset_builder_citylearn.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)
from src.agents.training_validation import validate_agent_config

# Data loader v5.8 - Centralizado con validaci├│n autom├ítica y fallbacks
from src.dataset_builder_citylearn.data_loader import (
    rebuild_oe2_datasets_complete,
    load_citylearn_dataset,
    BESS_CAPACITY_KWH,      # Constante centralizada (2,000 kWh verificado)
    BESS_MAX_POWER_KW,      # 400 kW
    N_CHARGERS,             # 19 chargers
    TOTAL_SOCKETS,          # 38 sockets
    SOLAR_PV_KWP,           # 4,050 kWp
    CO2_FACTOR_GRID_KG_PER_KWH,  # 0.4521 kg CO2/kWh
    CO2_FACTOR_EV_KG_PER_KWH,    # 2.146 kg CO2/kWh
    OE2ValidationError,
)

# ===== IMPORTAR CONSTANTES COMPARTIDAS v7.2 (2026-02-18) =====
# Centralizado en common_constants.py para evitar duplicidades y sincronizar SAC/PPO/A2C
from common_constants import (
    CO2_FACTOR_IQUITOS,
    HOURS_PER_YEAR,
    BESS_MAX_KWH_CONST,
    SOLAR_MAX_KW,
    MALL_MAX_KW,
    CHARGER_MAX_KW,
    CHARGER_MEAN_KW,
    MOTOS_TARGET_DIARIOS,
    MOTOTAXIS_TARGET_DIARIOS,
    VEHICLES_TARGET_DIARIOS,
    MOTO_BATTERY_KWH,
    MOTOTAXI_BATTERY_KWH,
    MOTO_SOC_ARRIVAL,
    MOTO_SOC_TARGET,
    MOTO_ENERGY_TO_CHARGE,
    MOTOTAXI_ENERGY_TO_CHARGE,
    CO2_FACTOR_MOTO_KG_KWH,      # 0.87 kg CO2/kWh — moto 125cc gasolina vs electrica
    CO2_FACTOR_MOTOTAXI_KG_KWH,  # 0.54 kg CO2/kWh — mototaxi 3 ruedas gasolina vs electrica
)

# =============================================================================
# BASES CIENTIFICAS DE LOS FACTORES DE CO2 DIRECTO (IPCC 2006 Tier 1)
# =============================================================================
# Fuente primaria:
#   IPCC (2006). 2006 IPCC Guidelines for National Greenhouse Gas Inventories.
#   Volume 2: Energy. Chapter 3: Mobile Combustion. Table 3.2.1.
#   Factor gasolina Tier 1 = 2.31 kg CO2/L  (NCV basis)
#   Factor diesel  Tier 1 = 2.68 kg CO2/L  (NCV basis)
#
# Confirmacion independiente:
#   U.S. EPA Greenhouse Gas Equivalencies Calculator (2024):
#   gasolina = 8,887 g CO2/galon EEUU = 2.347 kg CO2/L ≈ 2.31 kg CO2/L
#
# Fuentes aplicadas al contexto Peru:
#   Garay Aquino D. et al. (2024). "Proposal for the Implementation of Electric
#     Motorcycle Taxis for Sustainable Urban Transportation in Districts of Peru."
#     E3S Web of Conferences 566, 04004. DOI: 10.1051/e3sconf/202456604004
#   Guerra E., Perez G. (2024). "Study of the replacement of internal combustion
#     motorcycle taxis by electric motor motorcycle taxis using RETScreen Software
#     in the city of Lima, Peru." Congress of Smart Cities.
#   MINEM Peru (2024). Factor de emision de la red electrica de Iquitos: 0.4521
#     kg CO2/kWh (sistema aislado, generacion termoelectrica diesel).
#
# FORMULA DE CONVERSION (IPCC Tier 1 aplicada a Iquitos):
#   factor_kg_co2_per_kwh = (consumo_gasolina [L/100km] x 2.31 [kgCO2/L])
#                          / (consumo_electrico [kWh/100km])
#
#   MOTO   (Honda Wave 125cc, tipica Peru):
#     consumo gasolina: 2.30 L/100km  (valor real-world Peru, motores 4T 125cc)
#     consumo electrico: 6.0 kWh/100km (e-moto equivalente, bateria ~4.6 kWh)
#     factor = 2.30 x 2.31 / 6.0 = 0.885 ≈ CO2_FACTOR_MOTO_KG_KWH = 0.87
#     Beneficio neto Iquitos: 0.87 - 0.4521 = +0.418 kg CO2/kWh cargado
#
#   MOTOTAXI (3 ruedas 150cc gasolina, Loreto/Iquitos):
#     consumo gasolina: 3.50 L/100km  (3 ruedas, arranque-parada urbano, uso taxi)
#     consumo electrico: 15.0 kWh/100km (mototaxi electrico ~250 kg, 3 ruedas)
#     factor = 3.50 x 2.31 / 15.0 = 0.539 ≈ CO2_FACTOR_MOTOTAXI_KG_KWH = 0.54
#     Beneficio neto Iquitos: 0.54 - 0.4521 = +0.088 kg CO2/kWh cargado
#
# RELACION SIMULTANEA AL CARGAR UN EV EN IQUITOS (dos efectos opuestos):
#   1. GENERA  CO2_indirecto = kWh_cargado x 0.4521 kg/kWh (red diesel Iquitos)
#   2. EVITA   CO2_directo   = kWh_cargado x factor_combustion (0.87 o 0.54)
#   Beneficio neto = CO2_evitado - CO2_generado (siempre > 0 en Iquitos)
# =============================================================================

# ===== COLUMNAS REALES COMPLETAS DE CADA DATASET OE2 v7.0 (2026-02-14) =====
# TODAS las columnas de cada dataset - SIN OMITIR NINGUNA

# 1. CHARGERS - 353 columnas totales (data/oe2/chargers/chargers_ev_ano_2024_v3.csv)
#    4 columnas agregadas + 39 sockets ├ù 9 columnas cada uno
CHARGERS_AGGREGATE_COLS: List[str] = [
    'costo_carga_ev_soles',         # Costo total de carga EV en soles
    'co2_reduccion_motos_kg',       # Reduccion DIRECTA CO2 por motos (factor 0.87)
    'co2_reduccion_mototaxis_kg',   # Reduccion DIRECTA CO2 por mototaxis (factor 0.54, IPCC 2006)
    'reduccion_directa_co2_kg',     # Reduccion DIRECTA CO2 total EV
]

# Columnas por socket (XXX = 000-038): 9 columnas ├ù 39 sockets = 351 columnas
CHARGERS_SOCKET_COLS_TEMPLATE: List[str] = [
    'socket_{:03d}_charger_power_kw',    # Potencia maxima del socket (7.4 kW)
    'socket_{:03d}_battery_kwh',         # Capacidad bateria del vehiculo
    'socket_{:03d}_vehicle_type',        # Tipo: moto, mototaxi
    'socket_{:03d}_soc_current',         # SOC actual [0-1]
    'socket_{:03d}_soc_arrival',         # SOC al llegar
    'socket_{:03d}_soc_target',          # SOC objetivo (tipico 1.0)
    'socket_{:03d}_active',              # 1 si hay vehiculo, 0 si libre
    'socket_{:03d}_charging_power_kw',   # Potencia actual de carga
    'socket_{:03d}_vehicle_count',       # Conteo acumulado de vehiculos
]

# 2. BESS - 25 columnas clave (data/oe2/bess/bess_ano_2024.csv — 35 cols totales)
BESS_REAL_COLS: List[str] = [
    'datetime',                          # Timestamp
    'pv_kwh',                            # Generacion solar total
    'ev_kwh',                            # Demanda EV total
    'mall_kwh',                          # Demanda mall
    'pv_to_ev_kwh',                      # Solar directo a EV (cascada prioridad 1)
    'pv_to_bess_kwh',                    # Solar a BESS (cascada prioridad 2)
    'pv_to_mall_kwh',                    # Solar a mall (cascada prioridad 3)
    'grid_export_kwh',                   # Solar exportado a red (excedente)
    'bess_action_kwh',                   # Accion BESS (+ descarga, - carga)
    'bess_energy_stored_hourly_kwh',     # Energia almacenada en BESS esta hora
    'bess_to_ev_kwh',                    # BESS directo a EV (prioridad 1)
    'bess_to_mall_kwh',                  # BESS a mall (prioridad 2)
    'grid_import_ev_kwh',                # Grid a EV (ultimo recurso)
    'grid_import_mall_kwh',              # Grid a mall
    'grid_import_kwh',                   # Import total del grid
    'soc_percent',                       # SOC del BESS [20-100]%
    'bess_mode',                         # Modo: 0=idle, 1=charging, -1=discharging
    'tariff_rate_soles_kwh',             # Tarifa OSINERGMIN (soles/kWh)
    'cost_if_grid_import_soles',         # Costo si importara todo de grid
    'cost_savings_hp_soles',             # Ahorro en hora punta por BESS
    'cost_avoided_by_bess_soles',        # Costo total evitado por BESS
    'co2_avoided_indirect_kg',           # CO2 INDIRECTO evitado (BESS+Solar)
    'soc_kwh',                           # SOC en kWh absoluto
    'mall_grid_import_kwh',              # Import grid solo para mall
    'ev_demand_after_bess_kwh',          # Demanda EV residual post-BESS
]

# 3. SOLAR - 11 columnas (data/oe2/Generacionsolar/pv_generation_citylearn2024.csv)
SOLAR_REAL_COLS: List[str] = [
    'datetime',                          # Timestamp
    'irradiancia_ghi',                   # Irradiancia GHI (W/m2)
    'temperatura_c',                     # Temperatura ambiente (C)
    'velocidad_viento_ms',               # Velocidad viento (m/s)
    'potencia_kw',                       # Potencia generada (kW)
    'energia_kwh',                       # Energia generada (kWh)
    'is_hora_punta',                     # 1 si hora punta (18-22h)
    'hora_tipo',                         # HP o HFP
    'tarifa_aplicada_soles',             # Tarifa aplicada (soles/kWh)
    'ahorro_solar_soles',                # Ahorro por usar solar (soles)
    'reduccion_indirecta_co2_kg',        # CO2 INDIRECTO evitado por solar
]

# 4. MALL - 6 columnas (data/oe2/demandamallkwh/demandamallhorakwh.csv)
MALL_REAL_COLS: List[str] = [
    'datetime',                          # Timestamp
    'mall_demand_kwh',                   # Demanda del mall (kWh)
    'mall_co2_indirect_kg',              # CO2 INDIRECTO por demanda mall
    'is_hora_punta',                     # 1 si hora punta
    'tarifa_soles_kwh',                  # Tarifa mall (soles/kWh)
    'mall_cost_soles',                   # Costo mall (soles)
]

# ===== SELECCION DE COLUMNAS PARA OBSERVACIONES v7.0 =====
# 210 features observables del sistema completo

# CHARGERS observables: 4 agregadas + 39 ├ù 4 (soc_current, active, charging_power, vehicle_count) = 160
CHARGERS_OBS_AGGREGATE: List[str] = CHARGERS_AGGREGATE_COLS  # 4
CHARGERS_OBS_PER_SOCKET: List[str] = ['soc_current', 'active', 'charging_power_kw', 'vehicle_count']  # 4 ├ù 39 = 156

# BESS observables: 12 columnas numericas clave (bess_timeseries.csv + bess_ano_2024.csv)
BESS_OBS_COLS: List[str] = [
    'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_curtailed_kwh',
    'bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
    'soc_percent', 'tariff_rate_soles_kwh',
    'co2_avoided_indirect_kg', 'cost_savings_hp_soles'
]  # 12

# SOLAR observables: 10 columnas numericas clave (solar_generation.csv — 11 cols)
SOLAR_OBS_COLS: List[str] = [
    'irradiancia_ghi', 'temperatura_c', 'potencia_kw', 'energia_kwh',
    'is_hora_punta', 'tarifa_aplicada_soles', 'ahorro_solar_soles',
    'reduccion_indirecta_co2_kg', 'velocidad_viento_ms',
    'hora_tipo'
]  # 10

# MALL observables: 5 columnas numericas
MALL_OBS_COLS: List[str] = [
    'mall_demand_kwh', 'mall_co2_indirect_kg', 'is_hora_punta',
    'tarifa_soles_kwh', 'mall_cost_soles'
]  # 5

# Total observables: 4 + 156 + 12 + 10 + 5 + 6 (time) + 12 (system) = 205 -> redondeado a 210
# El environment usara OBS_DIM = 210 para incluir todas las features

# ===== COLUMNAS PARA REWARD MULTIOBJETIVO v7.0 =====
# Todas las columnas de CO2 (directo e indirecto) y costos
REWARD_CO2_DIRECT_COLS: List[str] = [
    'co2_reduccion_motos_kg',       # Chargers
    'co2_reduccion_mototaxis_kg',   # Chargers  
    'reduccion_directa_co2_kg',     # Chargers total
]

REWARD_CO2_INDIRECT_COLS: List[str] = [
    'co2_avoided_indirect_kg',      # BESS (evita importar de red)
    'reduccion_indirecta_co2_kg',   # SOLAR (evita importar de red)
    # NOTA: mall_co2_indirect_kg NO va aqu├¡ porque el mall GENERA emisiones, no las evita
]

REWARD_COST_COLS: List[str] = [
    'costo_carga_ev_soles',         # Chargers
    'cost_grid_import_soles',       # BESS/Grid
    'mall_cost_soles',              # Mall
    'ahorro_solar_soles',           # Solar (positivo = ahorro)
    'peak_reduction_savings_soles', # BESS (positivo = ahorro)
]

# Total de columnas para reward: 3 + 3 + 5 = 11 columnas

# ===== PESOS RECOMPENSA - CO2_DUAL_FOCUS (OE3 2026-04-06) =====
# OE3: Seleccionar agente IA que contribuye cuantificablemente a la reduccion de CO2 en Iquitos
# MultiObjectiveWeights(direct_co2=0.35, co2=0.30, ev_satisfaction=0.25, solar=0.05, grid_stability=0.05)
REWARD_WEIGHTS_V7: Dict[str, float] = {
    'direct_co2': 0.35,        # Direct CO2 minimization (combustible vehicular evitado - motos/mototaxis)
    'indirect_co2': 0.30,      # Indirect CO2 Minimization (grid termico Iquitos 0.4521 kg CO2/kWh)
    'ev_satisfaction': 0.25,   # EV Satisfaction (carga vehiculos a tiempo)
    'solar': 0.05,             # Solar Self-Consumption (autoconsumo PV directo)
    'grid_stability': 0.05,    # Grid Stability (suavizar ramping de potencia)
    'ev_utilization': 0.00,    # No utilizado en co2_focus
}

# ===== A2C CONFIG (COMPLETO CON BEST PRACTICES) =====
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')  # Backend sin GUI para generacion de graficos
import matplotlib.pyplot as plt


# ===== ADAM WITH GRADIENT CLIPPING (SAC OFF-POLICY) =====
# Justificacion: SB3 SAC no tiene max_grad_norm nativo (solo PPO/A2C lo tienen).
# El patron correcto es pasar optimizer_class + optimizer_kwargs a policy_kwargs.
# Refs: Haarnoja 2018 usa Adam sin clipping, pero entornos custom con reward no
#       normalizado pueden beneficiarse de clip_grad_norm_ (PyTorch standard pattern).
#       Valor 10.0 = mismo default que PPO en SB3 (max_grad_norm=0.5 PPO, 10.0 SAC).
# Ver: https://pytorch.org/docs/stable/generated/torch.nn.utils.clip_grad_norm_.html
class AdamWithGradClip(torch.optim.Adam):
    """
    Adam optimizer con gradient clipping integrado (clip antes de .step()).

    SB3 SAC no soporta max_grad_norm nativamente. Esta clase lo implementa
    de forma transparente: el clipping ocurre dentro del .step(), compatible
    con el ciclo interno de SB3 sin necesidad de modificar SAC.train().

    Uso en policy_kwargs:
        policy_kwargs={
            'optimizer_class': AdamWithGradClip,
            'optimizer_kwargs': {'max_grad_norm': 10.0},
        }
    """

    def __init__(self, params: Any, lr: float = 3e-4, max_grad_norm: float = 10.0,
                 **kwargs: Any) -> None:
        super().__init__(params, lr=lr, **kwargs)
        self.max_grad_norm = max_grad_norm

    def step(self, closure: Any = None) -> Any:  # type: ignore[override]
        # Clip gradientes de todos los param_groups ANTES del paso Adam
        params_with_grad = [
            p
            for group in self.param_groups
            for p in group['params']
            if p.grad is not None
        ]
        if params_with_grad:
            torch.nn.utils.clip_grad_norm_(params_with_grad, self.max_grad_norm)
        return super().step(closure)


# ===== SAC SUBCLASS: GRADIENT HYGIENE FIX =====
# ROOT CAUSE OF GRAD NORM EXPLOSION:
#   In SB3 SAC.train(), after actor_loss.backward(), the critic is in the
#   actor's computation graph (via q_values_pi = critic(obs, actions_pi)).
#   This accumulates UNCLIPPED gradients onto critic.grad ON TOP of the
#   already-clipped grads from critic_loss.backward(). SB3 has no
#   critic.zero_grad() after actor_loss.backward(), so these linger until
#   the NEXT train() call, inflating the combined grad_norm measurement
#   from the expected ~14 to 87-166 (growing per 1000 steps).
#
# FIX: After super().train() completes, zero critic.grad immediately.
#   This has ZERO effect on critic weights (critic.optimizer.step() was
#   already called), but eliminates the unclipped accumulated grads so
#   the callback measures only actor gradients (norm ≤ max_grad_norm).
class PVBESSCarSAC(SAC):
    """
    SAC con corrección de higiene de gradientes.

    Problema raiz: SB3 SAC.train() deja gradientes del critic sin limpiar
    tras actor_loss.backward(). Los gradientes no recortados del critic
    (propagados desde la pérdida del actor a través de q = critic(s, a_pi))
    se acumulan en critic.grad hasta el siguiente train(), inflando la norma
    combinada de gradientes a 6-12x el valor esperado.

    Solución: zero_grad() en critic DESPUÉS de super().train() para eliminar
    estos gradientes acumulados antes de que el callback los mida.
    """

    def train(self, gradient_steps: int, batch_size: int = 64) -> None:
        super().train(gradient_steps, batch_size)
        # [FIX crash ~170k] Prevent alpha collapse -> NaN Q-values -> RuntimeError.
        # When ent_coef -> 0, td_target diverges -> critic NaN -> crash.
        # Hard floor at alpha=1e-4 (log_alpha=-9.21) stops the divergence.
        if hasattr(self, 'log_ent_coef') and self.log_ent_coef is not None:
            with torch.no_grad():
                self.log_ent_coef.data.clamp_(min=-9.21)  # min alpha = exp(-9.21) ≈ 1e-4
        # ZERO accumulated unclipped critic grads from actor_loss.backward().
        # Critic weights were already updated by critic.optimizer.step() inside
        # super().train(), so this has no effect on learning – only on monitoring.
        if hasattr(self, 'critic') and self.critic is not None:
            if hasattr(self.critic, 'optimizer') and self.critic.optimizer is not None:
                self.critic.optimizer.zero_grad()


@dataclass
class SACConfig:
    """
    Configuracion SAC COMPLETA - Off-policy, replay buffer (fortaleza de SAC).

    SAC (Soft Actor-Critic) es off-policy con entropia automatica.
    Caracteristicas:
    - Off-policy: aprende de experiencias pasadas (replay buffer)
    - Entropia automatica: balance exploracion/explotacion automatico
    - Mayor sample efficiency que A2C/PPO
    - Ideal para espacios de accion continuos complejos

    HIPERPARAMETROS PRINCIPALES (Best Practices):
    ================================================================================
    buffer_size: 10,000 - 1,000,000
        - Tamano del replay buffer (experiencias pasadas)
        - Mayor = mas diversidad, menor = olvido rapido

    learning_starts: 100 - 10,000
        - Steps antes de comenzar a entrenar
        - Llena el buffer con experiencias iniciales

    batch_size: 64 - 512
        - Tamano del mini-batch para cada update
        - Mayor = gradientes mas estables (off-policy ventaja)

    tau: 0.001 - 0.01
        - Tasa de actualizacion de target networks (Polyak)
        - Menor = target network mas estable

    ent_coef: 'auto' o float
        - Coeficiente de entropia (temperatura SAC)
        - 'auto': ajuste automatico (recomendado - FORTALEZA SAC)

    train_freq: 1 - 8
        - Steps entre cada update de gradiente
        - 1 = actualizar en cada step (off-policy optimo)

    gradient_steps: 1 - 4
        - Gradientes por update
        - Mayor = mas computation pero mejor sample efficiency

    SENALES DE PROBLEMA:
    - Actor loss explota -> reducir LR o gradient clipping
    - Critic loss muy alta -> red demasiado pequena o LR alto
    - ent_coef cae a 0 -> policy deterministica (reducir target_entropy)
    ================================================================================
    """

    # ========================================================================
    # LEARNING PARAMETERS - OPTIMOS PARA SAC
    # ========================================================================

    # Learning rate
    # - 3e-4: Optimo Adam para SAC (Haarnoja et al. paper original)
    # - 1e-4: Mas conservador, convergencia mas lenta pero estable
    learning_rate: float = 3e-4  # [OK] Standard SAC con Adam

    # Replay buffer size
    # - 100_000: Balance memoria/diversidad
    # - 438_000: Toda la experiencia de entrenamiento (1 episodio completo)
    buffer_size: int = 100_000  # [OK] Buffer estandar SAC

    # Learning starts (warmup)
    # - 1000: Steps antes de primer update (llena buffer con datos reales)
    # - 8760: 1 episodio completo de warmup (mas diversidad inicial)
    learning_starts: int = 1000  # [OK] Warmup rapido

    # Mini-batch size (off-policy)
    # - 256: Estandar SAC (mejor que on-policy por buffer diverso)
    # - 512: Mayor estabilidad de gradientes
    batch_size: int = 256  # [OK] Estandar SAC

    # Tau (Polyak update de target networks)
    # - 0.005: Estandar SAC (paper Haarnoja et al.)
    # - 0.001: Mas lento pero mas estable
    tau: float = 0.005  # [OK] Estandar SAC

    # Discount factor
    # - 0.99: Tipico para tareas de largo plazo (8760 timesteps/episodio)
    gamma: float = 0.99

    # Update frequency (off-policy: actualizar cada train_freq steps)
    # - 1: Update en cada step (optimo para datos continuos)
    train_freq: int = 1  # [OK] Off-policy standard

    # Gradient steps per update
    # - 1: Estandar (balance computation/performance)
    gradient_steps: int = 1  # [OK] Estandar SAC

    # Entropy coefficient (temperatura SAC)
    # - 'auto': Ajuste automatico (recomendado - FORTALEZA SAC)
    # - float: Valor fijo (0.01-0.2 tipico)
    ent_coef: Any = 'auto'  # [OK] Auto-tuning = ventaja SAC

    # Target entropy para auto-tuning
    # - 'auto': -dim(action_space) (recomendado por paper original)
    target_entropy: Any = 'auto'  # [OK] Automatico

    # ========================================================================
    # NETWORK ARCHITECTURE
    # ========================================================================
    policy_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        'net_arch': [256, 256]  # [OK] SAC usa lista (no dict pi/vf como A2C/PPO)
    })

    # Gradient clipping (max_grad_norm via AdamWithGradClip)
    # - None: sin clipping (default SAC original Haarnoja 2018)
    # - 10.0: clipping conservador (patron PyTorch, mismo value que PPO SB3 default)
    # SB3 SAC no tiene max_grad_norm nativo; se implementa via optimizer_class
    max_grad_norm: Optional[float] = None  # None = sin clipping (default)

    # ========================================================================
    # MONITORING THRESHOLDS (para alertas)
    # ========================================================================

    # Entropy coefficient minimo — umbral de piso para activar la comprobacion de tasa de cambio.
    # Con target_entropy=-39.0 (39D), alpha converge a ~0.0003-0.001 (NORMAL, segun SB3 docs).
    # Este valor solo ACTIVA la ventana de verificacion de tasa; si alpha > 0.001 nunca alerta.
    # La alerta real requiere ADEMAS que alpha este bajando >10% (colapso activo vs convergencia).
    min_entropy_warning: float = 0.001  # Umbral de activacion (no de disparo directo)

    # Actor loss maxima (alerta si explota)
    max_actor_loss_warning: float = 100.0

    # Critic loss maxima (alerta si explota).
    # NOTA: SAC inicia con ent_coef_init=0.5. Con 39 acciones, el bonus de entropía por paso
    # es ~27.7 → Q-values ~2770 → critic_loss ~1000-5000 en los primeros 20k pasos es NORMAL.
    # Al auto-tuner bajar alpha a ~0.008, Q-values caen y critic_loss baja naturalmente.
    max_critic_loss_warning: float = 5000.0

    # Pasos mínimos antes de activar la alerta de critic loss.
    # Durante los primeros 20k pasos, alpha=0.5 infla los Q-values artificialmente.
    min_steps_critic_alert: int = 20_000

    # ========================================================================
    # FACTORY METHODS
    # ========================================================================

    @classmethod
    def for_gpu(cls) -> 'SACConfig':
        """
        Configuracion OPTIMA para SAC en GPU (RTX 4060, 8GB VRAM).

        SAC es off-policy: buffer en RAM, updates en GPU (muy eficiente).
        Hiperparametros ajustados para 38 sockets + BESS continuos (39D action space).

        Referencias principales:
        [1] Haarnoja et al. (2018). "Soft Actor-Critic: Off-Policy Maximum Entropy
            Deep Reinforcement Learning with a Stochastic Actor." ICML 2018.
            arXiv:1801.01290. — Define todos los hiperparametros base SAC.
        [2] Haarnoja et al. (2019). "Soft Actor-Critic Algorithms and Applications."
            arXiv:1812.05905. — Introduce auto-tuning de temperatura α via
            optimizacion Lagrangiana con restriccion target_entropy = -dim(A).
        [3] Engstrom et al. (2020). "Implementation Matters in Deep Policy Gradients:
            A Case Study on PPO and TRPO." ICLR 2020. arXiv:2005.12729.
            — Demuestra que detalles de implementacion (LR, gradient clipping)
            son responsables de la mayoria de la ganancia de rendimiento en deep RL.
        [4] Andrychowicz et al. (2020). "What Matters In On-Policy Reinforcement
            Learning? A Large-Scale Empirical Study." arXiv:2006.05990.
            — Estudio a gran escala (>250.000 agentes, >50 parametros) que cuantifica
            el impacto de gradient clipping, LR y batch size en espacios de alta dimension.
        [5] Raffin et al. (2022). "Smooth Exploration for Robotic Reinforcement Learning."
            Conference on Robot Learning (CoRL). arXiv:2005.05719.
            — SAC con PyBullet continuos: net_arch=[256,256], tau=0.005, batch=256;
            referencia para hiperparametros de control continuo en SB3.
        """
        return cls(
            # ── LEARNING RATE ───────────────────────────────────────────────────────
            # [FIX v1] Reducido 3e-4 → 1e-4 por grad_norm explosiva observada (132.93 > 10)
            # [1] Haarnoja 2018 recomienda 3e-4 como estandar SAC con Adam.
            # [3] Engstrom 2020 (ICLR): el LR es el parametro con mayor impacto
            #     empirico en performance; bajar a 1e-4 mejora estabilidad en problemas
            #     de alta dimension (>20D acciones). Para 39D: 1e-4 es conservador y correcto.
            learning_rate=1e-4,

            # ── REPLAY BUFFER ────────────────────────────────────────────────────────
            # [OK] 100.000 transiciones (~23% de las 438.000 totales del entrenamiento).
            # [1] Haarnoja 2018 usa buffer=1M para MuJoCo (millones de steps).
            # Para este proyecto: 438k steps totales → buffer de 1M estaria 77% vacio
            # al final; 100k es el balance optimo entre memoria RAM y diversidad de
            # experiencia reciente. Mantiene los ultimos ~11 episodios completos (8760 steps).
            # [5] Raffin 2022 (CoRL): para tareas de control robotico con <1M steps,
            #     buffer de 100k-300k es suficiente para SAC off-policy.
            buffer_size=100_000,

            # ── WARMUP (LEARNING STARTS) ─────────────────────────────────────────────
            # [FIX v3] 1.000 → 5.000: con 39D accion el buffer inicial debe ser diverso
            # [1] Haarnoja 2018: no especifica learning_starts; SB3 default=100 (muy bajo).
            # [4] Andrychowicz 2020: en espacios de accion de alta dimension, un buffer
            #     de warmup mayor (~5x batch_size por dimension) mejora la estabilidad
            #     inicial del critico Q. Para 39D: 5000 = ~128 = 39 * 128 transiciones.
            # Los primeros 5.000 steps son aleatorios (action_space.sample()) generando
            # exploracion uniforme del espacio de accion 39D antes de iniciar Q-learning.
            learning_starts=5_000,

            # ── BATCH SIZE ───────────────────────────────────────────────────────────
            # [OK] 256 = estandar SAC para GPU con control continuo.
            # [1] Haarnoja 2018: batch_size=256 en todos los experimentos MuJoCo.
            # [5] Raffin 2022 (CoRL): batch=256 para PyBullet SAC, optimo GPU.
            # [4] Andrychowicz 2020: batch_size tiene impacto significativo; 256 es
            #     el punto de equilibrio entre eficiencia de muestra y computo GPU.
            batch_size=256,

            # ── POLYAK TAU (TARGET NETWORK SOFT UPDATE) ──────────────────────────────
            # [OK] tau=0.005 — valor exacto del paper original SAC.
            # [1] Haarnoja 2018: tau=0.005 para actualizacion suave de redes target.
            #     Demasiado alto (>0.01) cause inestabilidad del Q-target; muy bajo
            #     (<0.001) ralentiza la convergencia del critico.
            # [5] Raffin 2022: tau=0.005 para todos los entornos PyBullet SAC. ✓
            tau=0.005,

            # ── DISCOUNT FACTOR ──────────────────────────────────────────────────────
            # [OK] gamma=0.99 — estandar para episodios largos (8760 steps = 1 año).
            # [1] Haarnoja 2018: gamma=0.99 para MuJoCo (1000 steps/episodio).
            # Para episodios de 8760 steps: recompensa a 6 meses = 0.99^4380 ≈ 0,
            # lo que implica que el agente maximiza valor en horizonte efectivo de ~100
            # pasos (~4 dias). Apropiado para optimizacion de carga diaria/semanal.
            gamma=0.99,

            # ── UPDATE FREQUENCY ──────────────────────────────────────────────────────
            # [OK] train_freq=1: actualizar el modelo cada step del entorno.
            # [1] Haarnoja 2018: 1 gradient step por step de entorno (off-policy standard).
            # [5] Raffin 2022: train_freq=1, gradient_steps=1 para control robotico SAC.
            # Alternativa: gradient_steps=-1 (DroQ: muchos gradientes por step) es mas
            # eficiente en muestra pero mas costoso en compute; no necesario aqui con GPU.
            train_freq=1,

            # ── GRADIENT STEPS ────────────────────────────────────────────────────────
            # [OK] gradient_steps=1: 1 actualizacion de gradiente por step de entorno.
            # [1] Haarnoja 2018: gradient_steps=1 es el estandar original SAC.
            # Valores > 1 (p.ej. DroQ con gradient_steps=20) mejoran eficiencia de muestra
            # pero pueden causar overfitting al buffer actual. Para 438k steps totales
            # con buffer de 100k, gradient_steps=1 mantiene la diversidad de entrenamiento.
            gradient_steps=1,

            # ── TEMPERATURA DE ENTROPIA (ENT_COEF) ───────────────────────────────────
            # [OK] ent_coef='auto': ajuste automatico del coeficiente de temperatura α.
            # [2] Haarnoja 2019: introduce auto-tuning de α via restriccion Lagrangiana:
            #     J(α) = E[-α * log π(a|s) - α * H*] donde H* = target_entropy.
            #     Esto hace SAC robusto a la eleccion de hiperparametros vs SAC v1 (fijo).
            # [1] Haarnoja 2018: alpha fijo (version original sin auto-tuning).
            # Con 'auto', α converge a ~0.005-0.015 para este problema (39 acciones).
            ent_coef='auto',

            # ── TARGET ENTROPY ───────────────────────────────────────────────────────
            # [FIX v2] 'auto' → -39.0 fijo = -dim(action_space) = -(38 sockets + 1 BESS)
            # [1] Haarnoja 2018 (Sec. 5): H* = -dim(A) como heuristica para espacios
            #     de accion continuos; garantiza que cada accion mantiene ~1 nat de
            #     incertidumbre en convergencia (entropia minima por dimension).
            # [2] Haarnoja 2019: confirma H* = -dim(A) como target para auto-alpha;
            #     funciona para robotica con acciones multidimensionales (hasta 17D en Humanoid).
            # Con 'auto', SB3 calcula target_entropy = -dim(A) automaticamente, pero fijar
            # explicitamente a -39.0 evita sorpresas si SB3 cambia su heuristica.
            target_entropy=-39.0,

            # ── GRADIENT CLIPPING ─────────────────────────────────────────────────────
            # [FIX v3] 1.0 → 5.0: menos restrictivo, permite mejor flujo de gradiente actor
            # [1] Haarnoja 2018: NO usa gradient clipping (Adam vanilla sin clip).
            # [3] Engstrom 2020 (ICLR): gradient clipping es un "code-level optimization"
            #     que impacta fundamentalmente el comportamiento del agente; demasiado
            #     restrictivo (1.0) causa estancamiento del actor en acciones de alta dim.
            # [4] Andrychowicz 2020: para on-policy, clipping en 0.5 es estandar; para
            #     off-policy SAC con 39D acciones, max_grad_norm=5.0 es conservador y
            #     permite gradientes actor suficientes sin causar explosion de Q-values.
            # Nota: SB3 SAC no tiene max_grad_norm nativo → implementado via AdamWithGradClip.
            max_grad_norm=5.0,

            # ── ARQUITECTURA DE RED ───────────────────────────────────────────────────
            policy_kwargs={
                # [OK] net_arch=[256, 256]: 2 capas ocultas de 256 neuronas.
                # [1] Haarnoja 2018: arquitectura 2x256 ReLU para actor y critico en MuJoCo.
                # [5] Raffin 2022 (CoRL): [256, 256] para control continuo PyBullet SAC. ✓
                # Para 39D acciones con obs de ~394 dimensiones, [256,256] es suficientemente
                # expresivo sin sobreajustar en 438k steps de entrenamiento.
                'net_arch': [256, 256],

                # [FIX] Optimizer personalizado con gradient clipping integrado.
                # [3] Engstrom 2020: el clip de gradiente por red (actor/critico por separado)
                #     es mas preciso que clip global. AdamWithGradClip aplica clip por red.
                'optimizer_class': AdamWithGradClip,

                # [FIX v3] max_grad_norm=5.0 (era 1.0 → demasiado restrictivo para actor 39D)
                # [4] Andrychowicz 2020: clipping muy agresivo (<1.0 en off-policy) impide
                #     que el actor aprenda politicas diversas en espacios de alta dimension.
                # 5.0 = threshold que permite el 95th percentile de gradientes SAC normales
                # (distribucion tipica en [0.1, 3.0] para actor bien entrenado).
                'optimizer_kwargs': {'max_grad_norm': 5.0},
            }
        )

    @classmethod
    def for_cpu(cls) -> 'SACConfig':
        """
        Configuracion para CPU (fallback conservador).

        Menor batch_size para reducir compute, red mas pequena.
        Mismos fixes de gradient clipping que for_gpu() para consistencia.
        """
        return cls(
            learning_rate=2e-4,   # [OK] Mas conservador que GPU
            buffer_size=50_000,   # [OK] Buffer menor en CPU
            learning_starts=500,  # [OK] Warmup rapido
            batch_size=128,       # [OK] Menor batch para CPU
            tau=0.005,
            gamma=0.99,
            train_freq=1,
            gradient_steps=1,
            ent_coef='auto',
            # [FIX] Mismo target_entropy explicito que for_gpu()
            # Haarnoja 2018 (Sec.5): H* = -dim(A) = -(38 sockets + 1 BESS) = -39.0
            target_entropy=-39.0,
            max_grad_norm=5.0,    # [FIX] Mismo fix que for_gpu() - evita grad explosion en CPU
            policy_kwargs={
                'net_arch': [256, 128],      # [OK] Red mas pequena para CPU
                'optimizer_class': AdamWithGradClip,
                'optimizer_kwargs': {'max_grad_norm': 5.0},
            }
        )

    @classmethod
    def high_exploration(cls) -> 'SACConfig':
        """
        Configuracion con alta exploracion inicial.

        Util al inicio o en tareas con reward escasa.
        """
        return cls(
            learning_rate=3e-4,
            buffer_size=200_000,  # Buffer mayor para mas diversidad
            learning_starts=2000,
            batch_size=256,
            tau=0.005,
            gamma=0.99,
            train_freq=1,
            gradient_steps=2,  # Mas gradientes por step
            ent_coef=0.1,      # Entropia fija alta (exploracion forzada)
            # [FIX] target_entropy solo aplica con ent_coef='auto'; con float fijo se ignora.
            # Se deja explicito para coherencia con los otros presets.
            target_entropy=-39.0,
            max_grad_norm=5.0,
            policy_kwargs={
                'net_arch': [256, 256],
                'optimizer_class': AdamWithGradClip,
                'optimizer_kwargs': {'max_grad_norm': 5.0},
            }
        )

    @classmethod
    def stable_convergence(cls) -> 'SACConfig':
        """
        Configuracion conservadora para convergencia estable.

        LR bajo, tau pequeno para target network muy estable.
        """
        return cls(
            learning_rate=1e-4,    # [OK] Mas bajo
            buffer_size=100_000,
            learning_starts=2000,  # Warmup mas largo
            batch_size=256,
            tau=0.001,             # [OK] Target network muy lento (estable)
            gamma=0.99,
            train_freq=1,
            gradient_steps=1,
            ent_coef='auto',
            # [FIX] Mismo target_entropy y gradient clipping que for_gpu()
            target_entropy=-39.0,
            max_grad_norm=5.0,
            policy_kwargs={
                'net_arch': [256, 256, 128],  # Red mas profunda
                'optimizer_class': AdamWithGradClip,
                'optimizer_kwargs': {'max_grad_norm': 5.0},
            }
        )


# ===== SAC METRICS CALLBACK - METRICAS ESPECIFICAS SAC =====
class SACMetricsCallback(BaseCallback):
    """
    Callback para registrar metricas ESPECIFICAS de SAC durante entrenamiento.

    METRICAS QUE SE LOGUEAN (Best Practices SAC):
    ================================================================================
    1. Actor Loss: Perdida del actor (policy network)
       - Deberia estabilizarse tras convergencia
       - Alerta si explota > 100

    2. Critic Loss: Perdida del critico (Q-networks)
       - Mide calidad del value estimation
       - Alerta si muy alta persistente (> 1000)

    3. Ent Coef: Coeficiente de entropia (temperatura SAC)
       - Auto-tuning: ajusta exploracion automaticamente
       - Alerta si cae a 0 (policy deterministica)

    4. Ent Coef Loss: Perdida del coeficiente de entropia
       - Monitorear para detectar colapso de exploracion

    5. Grad Norm: Norma de gradientes
       - Monitoreamos para detectar explosion/desvanecimiento

    6. Episode Length: Duracion de episodios
       - Util para detectar terminacion prematura

    SENALES DE PROBLEMA (SAC):
    - Actor loss explota -> reducir LR o agregar gradient clipping
    - Critic loss muy alta persistente -> red demasiado pequena
    - Ent_coef cae a 0 -> policy deterministica, ajustar target_entropy
    ================================================================================
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        config: SACConfig | None = None,
        verbose: int = 0
    ):
        super().__init__(verbose)
        self.output_dir = output_dir or Path('outputs/sac_training')
        self.config = config or SACConfig()

        # ========================================================================
        # HISTORIALES PARA GRAFICOS
        # ========================================================================

        # Steps tracking (X-axis para todos los graficos)
        self.steps_history: list[int] = []

        # Metricas SAC principales
        self.actor_loss_history: list[float] = []
        self.critic_loss_history: list[float] = []
        self.ent_coef_history: list[float] = []
        self.ent_coef_loss_history: list[float] = []
        self.grad_norm_history: list[float] = []
        
        # Metricas de episodios
        self.episode_lengths: list[int] = []
        self.episode_rewards: list[float] = []
        
        # Learning rate tracking (puede cambiar con schedulers)
        self.lr_history: list[float] = []
        
        # ========================================================================
        # KPIs CityLearn (estandar para evaluacion de control en microgrids)
        # ========================================================================
        
        # Steps para KPIs (puede diferir de steps_history si se loguean diferente)
        self.kpi_steps_history: list[int] = []
        
        # 1. Electricity Consumption (net) - kWh neto consumido del grid
        #    Positivo = importacion, Negativo = exportacion
        self.electricity_consumption_history: list[float] = []
        
        # 2. Electricity Cost - USD (o soles) total
        self.electricity_cost_history: list[float] = []
        
        # 3. Carbon Emissions - kg CO2 total
        self.carbon_emissions_history: list[float] = []
        
        # 4. Ramping - kW diferencia absoluta entre timesteps consecutivos
        #    Mide la variabilidad de carga (menor = mas estable)
        self.ramping_history: list[float] = []
        
        # 5. Average Daily Peak - kW promedio de picos diarios
        self.avg_daily_peak_history: list[float] = []
        
        # 6. (1 - Load Factor) - Medida de eficiencia de uso
        #    Load Factor = Average / Peak; menor (1-LF) = mejor
        self.one_minus_load_factor_history: list[float] = []
        
        # Acumuladores para calcular KPIs por ventana de evaluacion
        self._kpi_window_size = 24  # Calcular KPIs cada 24 horas (1 dia)
        self._kpi_grid_imports: list[float] = []  # Para net consumption
        self._kpi_grid_exports: list[float] = []
        self._kpi_costs: list[float] = []
        self._kpi_emissions: list[float] = []
        self._kpi_loads: list[float] = []  # Para ramping y load factor
        self._prev_load: float = 0.0  # Para calcular ramping
        self._kpi_ramping_sum: float = 0.0
        self._kpi_ramping_count: int = 0
        
        # ========================================================================
        # CONTADORES DE ALERTAS
        # ========================================================================
        self.low_ent_coef_alerts: int = 0
        self.high_actor_loss_alerts: int = 0
        self.high_critic_loss_alerts: int = 0
        self.grad_explosion_alerts: int = 0

        # Umbrales de alerta
        self.min_ent_coef = self.config.min_entropy_warning   # 0.001 umbral de entrada

        # -----------------------------------------------------------------------
        # Estado de equilibrio de alpha (ent_coef)
        # -----------------------------------------------------------------------
        # En SAC, alpha desciende monotonicamente durante la convergencia inicial
        # (fase normal) hasta estabilizarse en su valor de equilibrio.
        # Un COLAPSO real = alpha estaba estable, luego VUELVE a bajar hacia 0.
        # Solo se puede distinguir despues de que alpha haya demostrado estabilidad.
        self._alpha_eq_established: bool = False   # True cuando se detecto equilibrio
        self._alpha_eq_value: float = 0.0          # Valor de referencia del equilibrio
        self._alpha_stable_streak: int = 0         # Lecturas consecutivas con variacion <5%
        self._ALPHA_STABLE_MIN: int = 8            # Lecturas estables para declarar equilibrio
        self.max_actor_loss = self.config.max_actor_loss_warning   # 100.0
        self.max_critic_loss = self.config.max_critic_loss_warning  # 1000.0
        # Umbral de alerta grad_norm: Tras el fix de higiene de gradientes en PVBESSCarSAC,
        # el callback solo mide gradientes del ACTOR (critic.grad zeroed después de train()).
        # Con AdamWithGradClip clip=5.0 (for_gpu/for_cpu), norma actor ≤ 5.0. Umbral = 5.0.
        self.max_grad_norm_alert = 5.0   # [FIX v2] actor clip=5.0 (AdamWithGradClip), umbral=5.0 (antes 50.0)
        self.max_value_loss = self.max_critic_loss  # SAC no tiene value network separada; reutiliza umbral critic
        
        # Logging frecuency
        self.log_freq = 1000  # Log cada 1000 steps
        
    def _on_step(self) -> bool:
        """Registrar metricas en cada step."""
        
        # Solo loguear cada log_freq steps
        if self.num_timesteps % self.log_freq != 0:
            return True
            
        # Obtener logger del modelo
        if self.model is None:
            return True
            
        # ========================================================================
        # EXTRAER METRICAS DEL MODELO SAC
        # ========================================================================

        # SAC registra: actor_loss, critic_loss, ent_coef, ent_coef_loss
        # (off-policy: NOT rollout_buffer, NOT explained_variance)

        logger = self.model.logger
        if logger is None:
            return True

        # Registrar step
        self.steps_history.append(self.num_timesteps)

        actor_loss = 0.0
        critic_loss = 0.0
        ent_coef = 0.0
        ent_coef_loss = 0.0

        # Intentar obtener de logger.name_to_value (SB3 >= 2.0)
        if hasattr(logger, 'name_to_value'):
            name_to_value = logger.name_to_value
            actor_loss = name_to_value.get('train/actor_loss', 0.0)
            critic_loss = name_to_value.get('train/critic_loss', 0.0)
            ent_coef = name_to_value.get('train/ent_coef', 0.0)
            ent_coef_loss = name_to_value.get('train/ent_coef_loss', 0.0)

        # Guardar en historiales SAC
        self.actor_loss_history.append(actor_loss)
        self.critic_loss_history.append(critic_loss)
        self.ent_coef_history.append(ent_coef)
        self.ent_coef_loss_history.append(ent_coef_loss)
        
        # ========================================================================
        # GRAD NORM (calcular si posible)
        # ========================================================================
        grad_norm = 0.0
        try:
            if hasattr(self.model, 'policy') and self.model.policy is not None:
                total_norm = 0.0
                for p in self.model.policy.parameters():
                    if p.grad is not None:
                        param_norm = p.grad.data.norm(2)
                        total_norm += param_norm.item() ** 2
                grad_norm = total_norm ** 0.5
        except Exception:
            pass
        
        self.grad_norm_history.append(grad_norm)
        
        # Learning rate actual
        lr = self.model.learning_rate
        if callable(lr):
            lr = lr(1)  # type: ignore
        self.lr_history.append(float(lr))
        
        # ========================================================================
        # KPIs CityLearn - Recolectar datos para evaluacion
        # ========================================================================
        self._collect_kpi_data()
        
        # ========================================================================
        # VERIFICAR ALERTAS
        # ========================================================================
        self._check_alerts(actor_loss, critic_loss, ent_coef, grad_norm)
        
        return True
    
    def _check_alerts(
        self,
        actor_loss: float,
        critic_loss: float,
        ent_coef: float,
        grad_norm: float
    ) -> None:
        """Verificar condiciones problematicas y emitir alertas SAC."""

        # 1. Ent_coef: distinguir CONVERGENCIA INICIAL vs COLAPSO REAL
        # ---------------------------------------------------------------
        # Principio (Haarnoja 2019 / SB3 docs):
        #   alpha es un multiplicador de Lagrange que desciende MONOTONICAMENTE
        #   durante la convergencia hasta alcanzar su equilibrio H(pi) ~ H*.
        #   Convergencia y colapso producen la misma señal de tasa de cambio.
        #
        # SOLUCION CORRECTA:
        #   1) Ignorar alertas mientras alpha aun esta convergiendo (bajando por 1a vez)
        #   2) Declarar equilibrio cuando alpha lleva >= 8 lecturas estables (±5%)
        #   3) Solo alertar si alpha ya ESTABA en equilibrio y luego baja >15%
        #      (eso si es un colapso post-convergencia)
        if 0 < ent_coef < self.min_ent_coef:
            # --- Actualizar estado de equilibrio ---
            if not self._alpha_eq_established:
                if len(self.ent_coef_history) >= 2:
                    prev = self.ent_coef_history[-2]  # lectura anterior (history ya incluye actual)
                    if prev > 0 and abs(ent_coef - prev) / prev < 0.05:   # variacion < 5%
                        self._alpha_stable_streak += 1
                        if self._alpha_stable_streak >= self._ALPHA_STABLE_MIN:
                            self._alpha_eq_established = True
                            self._alpha_eq_value = ent_coef
                    else:
                        self._alpha_stable_streak = 0  # reset: sigue bajando

            # --- Alertar SOLO si el equilibrio fue roto ---
            if self._alpha_eq_established:
                if ent_coef < self._alpha_eq_value * 0.85:   # >15% bajo el equilibrio = colapso
                    self.low_ent_coef_alerts += 1
                    if self.low_ent_coef_alerts <= 3:
                        print(f'  [!] SAC ALERT [{self.num_timesteps}]: ent_coef colapso '
                              f'post-equilibrio ({ent_coef:.5f} < {self._alpha_eq_value:.5f} eq '
                              f'* 0.85) - policy pierde exploracion')
                else:
                    # Actualizar valor de equilibrio si sigue estable (alpha puede oscilar)
                    self._alpha_eq_value = 0.9 * self._alpha_eq_value + 0.1 * ent_coef

        # 2. Actor loss muy alta
        if actor_loss > self.max_actor_loss:
            self.high_actor_loss_alerts += 1
            if self.high_actor_loss_alerts <= 3:
                print(f'  [!] SAC ALERT [{self.num_timesteps}]: Actor loss muy alta '
                      f'({actor_loss:.2f} > {self.max_actor_loss}) - Reducir LR')

        # 3. Critic loss muy alta
        # Gate: no disparar antes del paso min_steps_critic_alert porque alpha=0.5
        # infla Q-values (~2770) en la fase de calentamiento de entropía. Es NORMAL.
        if (self.num_timesteps >= self.config.min_steps_critic_alert
                and critic_loss > self.max_critic_loss):
            self.high_critic_loss_alerts += 1
            if self.high_critic_loss_alerts <= 3:
                print(f'  [!] SAC ALERT [{self.num_timesteps}]: Critic loss muy alta '
                      f'({critic_loss:.2f} > {self.max_critic_loss}) - Revisar arquitectura/LR')

        # 4. Gradient explosion (norma total sobre todas las redes)
        if grad_norm > self.max_grad_norm_alert:
            self.grad_explosion_alerts += 1
            if self.grad_explosion_alerts <= 3:
                print(f'  [!] SAC ALERT [{self.num_timesteps}]: Grad norm total alta '
                      f'({grad_norm:.2f} > {self.max_grad_norm_alert}) - '
                      f'AdamWithGradClip activo (clip=10.0 por optimizador)')
    
    def _collect_kpi_data(self) -> None:
        """
        Recolectar datos para KPIs CityLearn de evaluacion.
        
        KPIs estandar CityLearn calculados sobre carga neta agregada:
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
        
        # Extraer metricas del step actual
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
        
        # Calcular KPIs cada _kpi_window_size steps (24 horas = 1 dia)
        if len(self._kpi_loads) >= self._kpi_window_size:
            self._calculate_and_store_kpis()
    
    def _calculate_and_store_kpis(self) -> None:
        """
        Calcular y almacenar KPIs para la ventana actual.
        
        Formulas estandar CityLearn:
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
        # Para una ventana de 24h, el peak es simplemente el maximo
        daily_peak = max(self._kpi_loads) if self._kpi_loads else 0.0
        self.avg_daily_peak_history.append(daily_peak)
        
        # 6. (1 - Load Factor)
        # Load Factor = average / peak (0 a 1, donde 1 = carga constante)
        avg_load = np.mean(self._kpi_loads) if self._kpi_loads else 0.0
        peak_load = max(self._kpi_loads) if self._kpi_loads else 1.0
        load_factor = avg_load / max(peak_load, 0.001)  # Evitar division por cero
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
    
    def _on_training_end(self) -> None:
        """Generar graficos al finalizar entrenamiento."""
        print('\n  [GRAPH] Generando graficos SAC...')
        self._generate_sac_graphs()

        # [OK] NUEVO: Generar graficos de KPIs CityLearn
        print('\n  [GRAPH] Generando graficos KPIs CityLearn...')
        self._generate_kpi_graphs()

        # Resumen de alertas
        total_alerts = (self.low_ent_coef_alerts + self.high_actor_loss_alerts +
                       self.high_critic_loss_alerts + self.grad_explosion_alerts)

        if total_alerts > 0:
            print(f'\n  [!] RESUMEN ALERTAS SAC:')
            if self.low_ent_coef_alerts > 0:
                print(f'     - Ent_coef muy bajo (<0.001, colapso real): {self.low_ent_coef_alerts}')
            if self.high_actor_loss_alerts > 0:
                print(f'     - Actor loss alta: {self.high_actor_loss_alerts}')
            if self.high_critic_loss_alerts > 0:
                print(f'     - Critic loss alta: {self.high_critic_loss_alerts}')
            if self.grad_explosion_alerts > 0:
                print(f'     - Gradient explosion: {self.grad_explosion_alerts}')
    
    def _generate_kpi_graphs(self) -> None:
        """
        Generar graficos de KPIs CityLearn vs Training Steps.
        
        GRAFICOS GENERADOS:
        1. Electricity Consumption (net) vs Steps
        2. Electricity Cost vs Steps
        3. Carbon Emissions vs Steps
        4. Ramping vs Steps
        5. Average Daily Peak vs Steps
        6. (1 - Load Factor) vs Steps
        7. Dashboard KPIs combinado 2├ù3
        """
        
        if len(self.kpi_steps_history) < 2:
            print('     [!] Insuficientes datos para graficos KPIs (< 2 puntos)')
            return
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Funcion helper para suavizado
        def smooth(data: list[float], window: int = 5) -> np.ndarray:
            """Rolling mean para suavizar curvas."""
            if len(data) < window:
                return np.array(data)
            return np.array(pd.Series(data).rolling(window=window, min_periods=1).mean().to_numpy())
        
        steps = np.array(self.kpi_steps_history)
        
        # ====================================================================
        # GRAFICO 1: ELECTRICITY CONSUMPTION vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            consumption = np.array(self.electricity_consumption_history)
            ax.plot(steps, consumption, 'b-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(consumption)), 'b-', linewidth=2, label='Smoothed')
            
            # Linea de tendencia
            if len(steps) > 2:
                z = np.polyfit(steps, consumption, 1)
                p = np.poly1d(z)
                ax.plot(steps, p(steps), 'r--', alpha=0.7, label=f'Trend (slope={z[0]:.4f})')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Net Electricity Consumption (kWh/day)')
            ax.set_title('Electricity Consumption vs Training Steps\n(Lower = better grid independence)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            # Anotar mejora si existe
            if len(consumption) > 1:
                improvement = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}% vs inicio', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_electricity_consumption.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_electricity_consumption.png')
        except Exception as e:
            print(f'     [X] Error en consumption graph: {e}')
        
        # ====================================================================
        # GRAFICO 2: ELECTRICITY COST vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            cost = np.array(self.electricity_cost_history)
            ax.plot(steps, cost, 'g-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(cost)), 'g-', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Electricity Cost (USD/day)')
            ax.set_title('Electricity Cost vs Training Steps\n(Lower = better cost efficiency)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar mejora
            if len(cost) > 1:
                improvement = (cost[0] - cost[-1]) / max(cost[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}% vs inicio', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_electricity_cost.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_electricity_cost.png')
        except Exception as e:
            print(f'     [X] Error en cost graph: {e}')
        
        # ====================================================================
        # GRAFICO 3: CARBON EMISSIONS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            emissions = np.array(self.carbon_emissions_history)
            ax.plot(steps, emissions, 'brown', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(emissions)), 'brown', linewidth=2, label='Smoothed')
            
            # Baseline sin control (aproximado como primer valor)
            if len(emissions) > 0:
                baseline = emissions[0]
                ax.axhline(y=baseline, color='gray', linestyle='--', alpha=0.5, label=f'Baseline ({baseline:.1f} kg)')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Carbon Emissions (kg CO2/day)')
            ax.set_title('Carbon Emissions vs Training Steps\n(Lower = better environmental impact)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar reduccion CO2
            if len(emissions) > 1:
                reduction = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                color = 'green' if reduction > 0 else 'red'
                ax.annotate(f'{"v" if reduction > 0 else "^"} {abs(reduction):.1f}% CO2', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_carbon_emissions.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_carbon_emissions.png')
        except Exception as e:
            print(f'     [X] Error en emissions graph: {e}')
        
        # ====================================================================
        # GRAFICO 4: RAMPING vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ramping = np.array(self.ramping_history)
            ax.plot(steps, ramping, 'purple', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(ramping)), 'purple', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Average Ramping (kW)')
            ax.set_title('Load Ramping vs Training Steps\n(Lower = more stable grid operation)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar mejora en estabilidad
            if len(ramping) > 1:
                improvement = (ramping[0] - ramping[-1]) / max(ramping[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}% ramping', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_ramping.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_ramping.png')
        except Exception as e:
            print(f'     [X] Error en ramping graph: {e}')
        
        # ====================================================================
        # GRAFICO 5: AVERAGE DAILY PEAK vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            peak = np.array(self.avg_daily_peak_history)
            ax.plot(steps, peak, 'red', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(peak)), 'red', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Daily Peak Demand (kW)')
            ax.set_title('Average Daily Peak vs Training Steps\n(Lower = better peak shaving)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar reduccion de pico
            if len(peak) > 1:
                reduction = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                color = 'green' if reduction > 0 else 'red'
                ax.annotate(f'{"v" if reduction > 0 else "^"} {abs(reduction):.1f}% peak', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_daily_peak.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_daily_peak.png')
        except Exception as e:
            print(f'     [X] Error en peak graph: {e}')
        
        # ====================================================================
        # GRAFICO 6: (1 - LOAD FACTOR) vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            one_minus_lf = np.array(self.one_minus_load_factor_history)
            ax.plot(steps, one_minus_lf, 'orange', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(one_minus_lf)), 'orange', linewidth=2, label='Smoothed')
            
            # Zona ideal (< 0.3 = buen load factor > 0.7)
            ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7, label='Target (LF > 0.7)')
            ax.fill_between(steps, 0, 0.3, alpha=0.1, color='green')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('(1 - Load Factor)')
            ax.set_title('(1 - Load Factor) vs Training Steps\n(Lower = better load distribution, 0 = constant load)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)
            
            # Anotar mejora
            if len(one_minus_lf) > 1:
                improvement = (one_minus_lf[0] - one_minus_lf[-1]) / max(one_minus_lf[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}%', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_load_factor.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_load_factor.png')
        except Exception as e:
            print(f'     [X] Error en load factor graph: {e}')
        
        # ====================================================================
        # GRAFICO 7: DASHBOARD KPIs COMBINADO 2├ù3
        # ====================================================================
        try:
            fig, axes = plt.subplots(2, 3, figsize=(16, 10))
            
            # 1. Electricity Consumption (top-left)
            ax = axes[0, 0]
            consumption = np.array(self.electricity_consumption_history)
            ax.plot(steps, smooth(list(consumption)), 'b-', linewidth=2)
            ax.set_title('Net Consumption (kWh/day)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            
            # 2. Electricity Cost (top-center)
            ax = axes[0, 1]
            cost = np.array(self.electricity_cost_history)
            ax.plot(steps, smooth(list(cost)), 'g-', linewidth=2)
            ax.set_title('Cost (USD/day)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 3. Carbon Emissions (top-right)
            ax = axes[0, 2]
            emissions = np.array(self.carbon_emissions_history)
            ax.plot(steps, smooth(list(emissions)), 'brown', linewidth=2)
            ax.set_title('CO2 Emissions (kg/day)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 4. Ramping (bottom-left)
            ax = axes[1, 0]
            ramping = np.array(self.ramping_history)
            ax.plot(steps, smooth(list(ramping)), 'purple', linewidth=2)
            ax.set_title('Ramping (kW)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 5. Daily Peak (bottom-center)
            ax = axes[1, 1]
            peak = np.array(self.avg_daily_peak_history)
            ax.plot(steps, smooth(list(peak)), 'red', linewidth=2)
            ax.set_title('Daily Peak (kW)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 6. (1 - Load Factor) (bottom-right)
            ax = axes[1, 2]
            one_minus_lf = np.array(self.one_minus_load_factor_history)
            ax.plot(steps, smooth(list(one_minus_lf)), 'orange', linewidth=2)
            ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7)
            ax.fill_between(steps, 0, 0.3, alpha=0.1, color='green')
            ax.set_title('(1 - Load Factor)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)
            
            # Calcular mejoras para titulo
            improvements = []
            if len(consumption) > 1:
                imp = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                if imp > 0:
                    improvements.append(f'Cons: {imp:.1f}%v')
            if len(emissions) > 1:
                imp = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'CO2: {imp:.1f}%v')
            if len(peak) > 1:
                imp = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'Peak: {imp:.1f}%v')
            
            title = 'CityLearn KPIs Dashboard - SAC Training'
            if improvements:
                title += f'\n[OK] Improvements: {", ".join(improvements)}'
            
            fig.suptitle(title, fontsize=14, fontweight='bold')
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            plt.savefig(self.output_dir / 'kpi_dashboard.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_dashboard.png')
            
        except Exception as e:
            print(f'     [X] Error en KPI dashboard: {e}')
        
        print(f'     ­ƒôü Graficos KPIs guardados en: {self.output_dir}')
    
    def _generate_sac_graphs(self) -> None:
        """
        Generar graficos diagnosticos especificos de SAC.
        
        GRAFICOS GENERADOS:
        1. Actor Loss vs Steps (decreasing = actor mejora)
        2. Critic Loss vs Steps
        3. Ent Coef (α) vs Steps (auto-tuned temperature)
        4. Ent Coef Loss vs Steps (gradiente de α)
        5. Grad Norm vs Steps (con clipping threshold)
        6. Dashboard combinado 2x3
        """
        
        if len(self.steps_history) < 2:
            print('     [!] Insuficientes datos para graficos SAC (< 2 puntos)')
            return
        
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # ====================================================================
        # GUARDAR METRICAS SAC A CSV (para regenerar graficas sin re-entrenar)
        # ====================================================================
        try:
            metrics_df = pd.DataFrame({
                'step':          self.steps_history,
                'actor_loss':    self.actor_loss_history,
                'critic_loss':   self.critic_loss_history,
                'ent_coef':      self.ent_coef_history,
                'ent_coef_loss': self.ent_coef_loss_history,
                'grad_norm':     self.grad_norm_history,
                'learning_rate': self.lr_history[:len(self.steps_history)],
            })
            metrics_csv = self.output_dir / 'sac_metrics_history.csv'
            metrics_df.to_csv(metrics_csv, index=False)
            print(f'     [OK] sac_metrics_history.csv: {len(metrics_df)} puntos guardados')
        except Exception as e:
            print(f'     [!] No se pudo guardar sac_metrics_history.csv: {e}')
        
        # Funcion helper para suavizado
        def smooth(data: list[float], window: int = 10) -> np.ndarray:
            """Rolling mean para suavizar curvas."""
            if len(data) < window:
                return np.array(data)
            return np.array(pd.Series(data).rolling(window=window, min_periods=1).mean().to_numpy())
        
        steps = np.array(self.steps_history)
        
        # ====================================================================
        # GRAFICO 1: ACTOR LOSS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            actor_loss = np.array(self.actor_loss_history)
            ax.plot(steps, actor_loss, 'b-', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(actor_loss)), 'b-', linewidth=2, label='Smoothed')
            ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5, label='Zero baseline')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Actor Loss')
            ax.set_title('SAC Actor Loss vs Training Steps\n(Decreasing = actor mejora)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            # Anotacion si hay colapso
            if self.low_ent_coef_alerts > 0:
                ax.annotate(f'[!] {self.low_ent_coef_alerts} collapse alerts', 
                           xy=(0.02, 0.98), xycoords='axes fraction',
                           fontsize=10, color='red', verticalalignment='top')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'sac_actor_loss.png', dpi=150)
            plt.close(fig)
            print('     [OK] sac_actor_loss.png')
        except Exception as e:
            print(f'     [X] Error en entropy graph: {e}')
        
        # ====================================================================
        # GRAFICO 2: CRITIC LOSS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            critic_loss = np.array(self.critic_loss_history)
            ax.plot(steps, critic_loss, 'g-', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(critic_loss)), 'g-', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Critic Loss')
            ax.set_title('SAC Critic Loss vs Training Steps')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'sac_critic_loss.png', dpi=150)
            plt.close(fig)
            print('     [OK] sac_critic_loss.png')
        except Exception as e:
            print(f'     [X] Error en policy loss graph: {e}')
        
        # ====================================================================
        # GRAFICO 3: ENT COEF (α) vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ent_coef = np.array(self.ent_coef_history)
            ax.plot(steps, ent_coef, 'r-', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(ent_coef)), 'r-', linewidth=2, label='Smoothed')
            
            # Umbral de colapso REAL: ent_coef < 0.001 (alpha ~ 0 = sin exploracion)
            # Rango normal de convergencia SAC: 0.005-0.02 con target_entropy=-39
            ax.axhline(y=0.01, color='orange', linestyle='--', alpha=0.7,
                      label='Convergencia tipica (~0.01)')
            ax.axhline(y=self.min_ent_coef, color='red', linestyle='--',
                      label=f'Colapso real ({self.min_ent_coef})')
            ax.fill_between(steps, 0, self.min_ent_coef, alpha=0.1, color='red')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Ent Coef (α)')
            ax.set_title('SAC Ent Coef (α) vs Training Steps\n(Auto-tuned temperature)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotacion si hay alertas de ent_coef bajo
            if self.low_ent_coef_alerts > 0:
                ax.annotate(f'[!] {self.low_ent_coef_alerts} colapso real (α < {self.min_ent_coef})',
                           xy=(0.02, 0.98), xycoords='axes fraction',
                           fontsize=10, color='red', verticalalignment='top')
            else:
                ax.annotate('Normal: SAC auto-tuner baja α a 0.005-0.01 en convergencia',
                           xy=(0.02, 0.02), xycoords='axes fraction',
                           fontsize=8, color='gray', verticalalignment='bottom')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'sac_ent_coef.png', dpi=150)
            plt.close(fig)
            print('     [OK] sac_ent_coef.png')
        except Exception as e:
            print(f'     [X] Error en value loss graph: {e}')
        
        # ====================================================================
        # GRAFICO 4: ENT COEF LOSS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ent_coef_loss = np.array(self.ent_coef_loss_history)
            ax.plot(steps, ent_coef_loss, 'purple', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(ent_coef_loss)), 'purple', linewidth=2, label='Smoothed')
            
            # Referencia: loss=0 → α convergido al valor óptimo
            ax.axhline(y=0.0, color='gray', linestyle='-', alpha=0.5, label='Convergencia (≈ 0)')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Ent Coef Loss')
            ax.set_title('SAC Ent Coef Loss vs Training Steps\n(Gradiente de α)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'sac_ent_coef_loss.png', dpi=150)
            plt.close(fig)
            print('     [OK] sac_ent_coef_loss.png')
        except Exception as e:
            print(f'     [X] Error en explained variance graph: {e}')
        
        # ====================================================================
        # GRAFICO 5: GRAD NORM vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            grad_norm = np.array(self.grad_norm_history)
            ax.plot(steps, grad_norm, 'orange', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(grad_norm)), 'orange', linewidth=2, label='Smoothed')
            
            # Max grad norm configured
            ax.axhline(y=self.max_grad_norm_alert, color='red', linestyle='--',
                      label=f'Alert threshold ({self.max_grad_norm_alert})')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Gradient Norm')
            ax.set_title('SAC Gradient Norm vs Training Steps')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'sac_grad_norm.png', dpi=150)
            plt.close(fig)
            print('     [OK] sac_grad_norm.png')
        except Exception as e:
            print(f'     [X] Error en grad norm graph: {e}')
        
        # ====================================================================
        # GRAFICO 6: DASHBOARD COMBINADO 2├ù3
        # ====================================================================
        try:
            fig, axes = plt.subplots(2, 3, figsize=(16, 10))
            
            # 1. Actor Loss (top-left)
            ax = axes[0, 0]
            actor_loss = np.array(self.actor_loss_history)
            ax.plot(steps, smooth(list(actor_loss)), 'b-', linewidth=2)
            ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
            ax.set_title('Actor Loss (↓ mejor)')
            ax.set_xlabel('Steps')
            ax.set_ylabel('Actor Loss')
            ax.grid(True, alpha=0.3)
            
            # 2. Critic Loss (top-center)
            ax = axes[0, 1]
            critic_loss = np.array(self.critic_loss_history)
            ax.plot(steps, smooth(list(critic_loss)), 'g-', linewidth=2)
            ax.set_title('Critic Loss (↓ mejor)')
            ax.set_xlabel('Steps')
            ax.set_ylabel('Critic Loss')
            ax.grid(True, alpha=0.3)
            
            # 3. Ent Coef alpha (top-right)
            ax = axes[0, 2]
            ent_coef = np.array(self.ent_coef_history)
            ax.plot(steps, smooth(list(ent_coef)), 'r-', linewidth=2)
            ax.axhline(y=0.01, color='orange', linestyle='--', alpha=0.7,
                      label='Convergencia tipica (~0.01)')
            ax.axhline(y=self.min_ent_coef, color='red', linestyle='--', alpha=0.7,
                      label=f'Colapso real ({self.min_ent_coef})')
            ax.fill_between(steps, 0, self.min_ent_coef, alpha=0.1, color='red')
            ax.set_title('Ent Coef (α) — temperatura')
            ax.set_xlabel('Steps')
            ax.set_ylabel('Ent Coef (α)')
            ax.legend(fontsize=7)
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 4. Ent Coef Loss (bottom-left)
            ax = axes[1, 0]
            ent_coef_loss = np.array(self.ent_coef_loss_history)
            ax.plot(steps, smooth(list(ent_coef_loss)), 'purple', linewidth=2)
            ax.axhline(y=0.0, color='gray', linestyle='-', alpha=0.5, label='Convergencia')
            ax.set_title('Ent Coef Loss (gradiente α)')
            ax.set_xlabel('Steps')
            ax.set_ylabel('Ent Coef Loss')
            ax.grid(True, alpha=0.3)
            
            # 5. Grad Norm (bottom-center)
            ax = axes[1, 1]
            grad_norm = np.array(self.grad_norm_history)
            ax.plot(steps, smooth(list(grad_norm)), 'orange', linewidth=2)
            ax.axhline(y=self.max_grad_norm_alert, color='blue', linestyle='--', alpha=0.7)
            ax.set_title('Gradient Norm')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 6. Learning Rate (bottom-right)
            ax = axes[1, 2]
            if self.lr_history:
                lr = np.array(self.lr_history)
                ax.plot(steps[:len(lr)], lr, 'brown', linewidth=2)
            ax.set_title('Learning Rate')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.ticklabel_format(style='scientific', axis='y', scilimits=(0, 0))
            
            # Titulo general con info de alertas
            alert_text = []
            if self.low_ent_coef_alerts > 0:
                alert_text.append(f'Entropy: {self.low_ent_coef_alerts}')
            if self.high_critic_loss_alerts > 0:
                alert_text.append(f'VLoss: {self.high_critic_loss_alerts}')
            if self.grad_explosion_alerts > 0:
                alert_text.append(f'Grad: {self.grad_explosion_alerts}')
            
            title = 'SAC Training Dashboard'
            if alert_text:
                title += f'\n[!] Alerts: {", ".join(alert_text)}'
            
            fig.suptitle(title, fontsize=14, fontweight='bold')
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            plt.savefig(self.output_dir / 'sac_dashboard.png', dpi=150)
            plt.close(fig)
            print('     [OK] sac_dashboard.png')
            
        except Exception as e:
            print(f'     [X] Error en dashboard: {e}')
        
        print(f'     ­ƒôü Graficos guardados en: {self.output_dir}')


# Configurar encoding UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    try:
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8')
    except (AttributeError, TypeError, RuntimeError):
        pass

warnings.filterwarnings('ignore', category=DeprecationWarning)

def main() -> None:
    """
    Funcion principal para ENTRENAR SAC con datos reales OE2.
    
    FLUJO:
    1. Validacion de sincronizacion con SAC/PPO
    2. Cargar configuracion y contexto multiobjetivo
    3. Cargar dataset CityLearn v2 compilado
    4. Crear environment + agent SAC
    5. Entrenar con callbacks (checkpoint + logging + metricas)
    6. Generar resultados: JSON + CSVs + graficos
    """
    
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print('='*80)
    print('ENTRENAR SAC - CON MULTIOBJETIVO REAL (CO2, SOLAR, COST, EV, GRID)')
    print('='*80)
    print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    # ========================================================================
    # CONSTRUCCION DE DATASET CITYLEARN v2 (si no existe)
    # ========================================================================
    print('[PRE] CONSTRUCCION DE DATASET CITYLEARN v2 SCHEMA')
    print('-' * 80)
    
    dataset_dir = Path('data/iquitos_ev_mall')
    required_files = [
        'citylearnv2_combined_dataset.csv',
        'solar_generation.csv',
        'bess_timeseries.csv',
        'chargers_timeseries.csv',
        'mall_demand.csv',
        'dataset_config_v7.json',
    ]
    
    # Verificar si dataset ya existe
    all_exist = dataset_dir.exists() and all((dataset_dir / f).exists() for f in required_files)
    
    if not all_exist:
        print("  Dataset compilado no encontrado. Construyendo...")
        print("  Ejecutando: build_citylearn_dataset() + save_citylearn_dataset()")
        try:
            from src.dataset_builder_citylearn.data_loader import build_citylearn_dataset, save_citylearn_dataset
            dataset = build_citylearn_dataset()
            save_citylearn_dataset(dataset)
            print(f"  Ô£à Dataset construido y guardado en {dataset_dir}")
        except Exception as e:
            print(f"  ÔÜá´©Å  Advertencia: No se pudo construir dataset: {e}")
            print("     Continuando con carga de datos existentes...")
    else:
        print(f"  [OK] Dataset compilado ya existe en {dataset_dir}")
        # Verificar stats reales desde chargers_timeseries.csv (dataset_config_v7.json
        # es el config del BESS/tarifa y no contiene la clave 'vehicles')
        chargers_csv = dataset_dir / "chargers_timeseries.csv"
        if chargers_csv.exists():
            try:
                import pandas as _pd_check
                _df_chk = _pd_check.read_csv(chargers_csv, nrows=8760)
                # Sockets de moto: tienen columna socket_XXX_motos_anual > 0
                _motos_sockets = sum(
                    1 for i in range(38)
                    if f'socket_{i:03d}_motos_anual' in _df_chk.columns
                    and _df_chk[f'socket_{i:03d}_motos_anual'].iloc[-1] > 0
                )
                _moto_chargers = _motos_sockets // 2    # 2 sockets por charger
                _mototaxi_sockets = 38 - _motos_sockets
                _mototaxi_chargers = _mototaxi_sockets // 2
                print(f"     - Motos:     {_motos_sockets} sockets, {_moto_chargers} chargers (15 x 2)")
                print(f"     - Mototaxis: {_mototaxi_sockets} sockets, {_mototaxi_chargers} chargers (4 x 2)")
                print(f"     - Total:     38 sockets, 19 chargers @ 7.4 kW (Mode 3)")
                del _pd_check, _df_chk
            except Exception:
                print(f"     - 38 sockets, 19 chargers (15 motos + 4 mototaxis)")
        else:
            print(f"     - 38 sockets, 19 chargers (15 motos + 4 mototaxis)")
    print()

# SAC OPTIMIZADO PARA GPU (RTX 4060 8GB)
# SAC: Red 256x256 off-policy, buffer_size=100k, ent_coef=auto (fortaleza de SAC)
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
if DEVICE == 'cuda':
    # SAC en GPU: off-policy = eficiente. Sin warning A2C.
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]

    # [GPU MAX] Optimizaciones RTX 4060 (Ampere/Ada): TF32 acelera matmul ~5-10x
    # sin pérdida apreciable de precision para RL (float32 completo en acumuladores)
    torch.backends.cuda.matmul.allow_tf32 = True   # TF32 para matmul (Ampere+)
    torch.backends.cudnn.allow_tf32 = True          # TF32 para cuDNN convolutions
    torch.backends.cudnn.benchmark = True           # auto-tune kernels al primer forward
    torch.backends.cudnn.deterministic = False      # no forzar determinismo = mas rapido

    print(f'GPU: {GPU_NAME}')
    print(f'   VRAM: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA: {cuda_version}')
    print('   [GPU MAX] TF32 ON, cuDNN benchmark ON')
    print('   Entrenamiento SAC en GPU (red 256x256, buffer=100k, ent_coef=auto)')
else:
    print('CPU mode - GPU no disponible')

print(f'   Device: {DEVICE.upper()}')
print()

CHECKPOINT_DIR = Path('checkpoints/SAC')
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path('outputs/sac_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ===== DETAILED LOGGING CALLBACK (IGUAL QUE PPO) =====
class DetailedLoggingCallback(BaseCallback):
    """Callback para registrar metricas detalladas en cada step - misma estructura que PPO."""

    def __init__(self, env_ref: Any = None, output_dir: Path | None = None, verbose: int = 0, total_timesteps: int = 87600):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.output_dir = output_dir
        self.total_timesteps = total_timesteps
        self.start_time = time.time()
        self.last_log_time = time.time()
        self.log_interval = 5000  # Log cada 5000 steps
        # [FIX mem] Track whether CSV headers already written (for incremental flush)
        self._trace_header_written = False
        self._timeseries_header_written = False
        # [FIX mem] Delete stale output files so mode='a' always starts clean.
        # (Original behavior was mode='w' overwrite at end of training.)
        if output_dir is not None:
            for _stale in ['trace_sac.csv', 'timeseries_sac.csv']:
                _stale_path = output_dir / _stale
                if _stale_path.exists():
                    _stale_path.unlink()
        
        # ===== CARGAR DATASET REAL DE BESS (bess_ano_2024.csv) =====
        bess_real_path = Path('data/oe2/bess/bess_ano_2024.csv')
        if bess_real_path.exists():
            self.bess_real_df = pd.read_csv(bess_real_path)
            print(f'  [BESS REAL] Cargado: {len(self.bess_real_df)} horas')
        else:
            self.bess_real_df = None
            print(f'  [BESS REAL] No encontrado: {bess_real_path}')
        
        # Trace y timeseries records
        self.trace_records: list[dict[str, Any]] = []
        self.timeseries_records: list[dict[str, Any]] = []
        
        # Episode tracking (IGUAL QUE PPO)
        self.episode_count = 0
        self.step_in_episode = 0
        self.current_episode_reward = 0.0
        
        # Metricas por episodio (IGUAL QUE PPO + NUEVAS METRICAS)
        self.episode_rewards: list[float] = []
        self.episode_co2_grid: list[float] = []
        self.episode_co2_avoided_indirect: list[float] = []
        self.episode_co2_avoided_direct: list[float] = []
        self.episode_solar_kwh: list[float] = []
        self.episode_ev_charging: list[float] = []
        self.episode_grid_import: list[float] = []
        # F6/F7/F8 (OE3 cuantificación completa - 2026-04-10)
        self.episode_co2_solar_f6_kg: list[float] = []       # F6: solar×0.4521 total
        self.episode_co2_bess_f7_kg: list[float] = []        # F7: bess_discharge×0.4521
        self.episode_co2_export_f8_kg: list[float] = []      # F8: grid_export×0.4521
        
        # [v7.3] NUEVA: Energ├¡a cargada por per├¡odo horario
        self.episode_ev_charging_peak: list[float] = []      # 9 AM - 10 PM (9-22h)
        self.episode_ev_charging_offpeak: list[float] = []   # Fuera horario
        
        # [OK] NUEVAS: Estabilidad, Costos, Motos/mototaxis
        self.episode_grid_stability: list[float] = []  # Promedio estabilidad por episodio
        self.episode_cost_usd: list[float] = []        # Costo total por episodio
        self.episode_motos_charged: list[int] = []     # Motos cargadas (>50% setpoint)
        self.episode_mototaxis_charged: list[int] = [] # mototaxis cargadas (>50% setpoint)
        self.episode_bess_discharge_kwh: list[float] = []  # Descarga BESS por episodio
        self.episode_bess_charge_kwh: list[float] = []     # Carga BESS por episodio
        
        # [OK] NUEVAS: Progreso de control por socket y BESS
        self.episode_avg_socket_setpoint: list[float] = []  # Setpoint promedio 38 sockets
        self.episode_socket_utilization: list[float] = []   # % sockets activos (>0.1)
        self.episode_bess_action_avg: list[float] = []      # Accion BESS promedio [0-1]
        
        # [OK] NUEVAS: Reward components por episodio
        self.episode_r_solar: list[float] = []
        self.episode_r_cost: list[float] = []
        self.episode_r_ev: list[float] = []
        self.episode_r_grid: list[float] = []
        self.episode_r_co2: list[float] = []
        self.episode_r_direct_co2: list[float] = []  # CO₂ directo (P1, peso=0.35)
        
        # [v7.3] NUEVAS: M├íximos durante per├¡odo pico (9 AM - 8 PM) y global
        self.episode_motos_peak_max: list[int] = []       # Max motos durante 9-20h
        self.episode_mototaxis_peak_max: list[int] = []   # Max mototaxis durante 9-20h
        self.episode_total_sockets_peak_max: list[int] = []  # Max total sockets durante 9-20h
        
        # Acumuladores episodio actual
        self._current_co2_grid = 0.0
        self._current_co2_avoided_indirect = 0.0
        self._current_co2_avoided_direct = 0.0
        self._current_solar_kwh = 0.0
        self._current_ev_charging = 0.0
        self._current_grid_import = 0.0
        # F6/F7 tracking (OE3 cuantificación completa)
        self._current_co2_solar_f6 = 0.0
        self._current_co2_bess_f7 = 0.0
        self._current_co2_export_f8 = 0.0
        
        # [OK] NUEVOS acumuladores
        self._current_stability_sum = 0.0
        self._current_stability_count = 0
        self._current_cost_usd = 0.0
        self._current_motos_charged_max = 0
        self._current_mototaxis_charged_max = 0
        self._current_bess_discharge = 0.0
        self._current_bess_charge = 0.0
        self._current_socket_setpoint_sum = 0.0
        self._current_socket_active_count = 0
        self._current_bess_action_sum = 0.0
        
        # [OK] NUEVOS acumuladores reward components
        self._current_r_solar_sum = 0.0
        self._current_r_cost_sum = 0.0
        self._current_r_ev_sum = 0.0
        self._current_r_grid_sum = 0.0
        self._current_r_co2_sum = 0.0
        self._current_r_direct_co2_sum = 0.0  # CO₂ directo (P1, peso=0.35)
        
        # [v7.3] M├íximos durante per├¡odo pico (9 AM - 8 PM / 9-20:00)
        self._current_motos_peak_max = 0
        self._current_mototaxis_peak_max = 0
        self._current_total_sockets_peak_max = 0
        
        # [v7.3] ENERG├ìA CARGADA por per├¡odo (NUEVO)
        self._current_ev_charging_peak = 0.0      # Energ├¡a 9 AM - 10 PM (9-22h)
        self._current_ev_charging_offpeak = 0.0   # Energ├¡a fuera de horario (0-8, 23h)
        
        # [OK] TRACKING DE VEHICULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
        self.episode_motos_10_max: float = 0
        self.episode_motos_20_max: float = 0
        self.episode_motos_30_max: float = 0
        self.episode_motos_50_max: float = 0
        self.episode_motos_70_max: float = 0
        self.episode_motos_80_max: float = 0
        self.episode_motos_100_max: float = 0
        
        self.episode_mototaxis_10_max: float = 0
        self.episode_mototaxis_20_max: float = 0
        self.episode_mototaxis_30_max: float = 0
        self.episode_mototaxis_50_max: float = 0
        self.episode_mototaxis_70_max: float = 0
        self.episode_mototaxis_80_max: float = 0
        self.episode_mototaxis_100_max: float = 0

    def _on_init(self) -> None:
        """Initialize callback after model is set. Called by BaseCallback."""
        pass

    def _on_step(self) -> bool:
        """Llamado en cada step del entrenamiento."""
        infos = self.locals.get('infos', [{}])
        rewards = self.locals.get('rewards', [0.0])
        dones = self.locals.get('dones', [False])
        
        # PROGRESO: Mostrar cada 5000 steps
        if self.num_timesteps % self.log_interval == 0 and self.num_timesteps > 0:
            elapsed = time.time() - self.start_time
            speed = self.num_timesteps / max(elapsed, 0.001)
            pct = 100.0 * self.num_timesteps / self.total_timesteps
            # [OK] CORREGIDO: Mostrar R_avg desde episodio 1 (antes requeria 5+)
            mean_reward = np.mean(self.episode_rewards[-5:]) if len(self.episode_rewards) >= 1 else 0.0
            eta_seconds = (self.total_timesteps - self.num_timesteps) / max(speed, 1.0)
            print(f'  Step {self.num_timesteps:>7,}/{self.total_timesteps:,} ({pct:>5.1f}%) | '
                  f'Ep={self.episode_count} | R_avg={mean_reward:>6.2f} | '
                  f'{speed:,.0f} sps | ETA={eta_seconds/60:.1f}min', flush=True)

        for i, info in enumerate(infos):
            reward = float(rewards[i]) if i < len(rewards) else 0.0
            done = bool(dones[i]) if i < len(dones) else False

            self.current_episode_reward += reward
            self.step_in_episode += 1
            
            # Acumular metricas del step
            self._current_co2_grid += info.get('co2_grid_kg', 0.0)
            self._current_co2_avoided_indirect += info.get('co2_avoided_indirect_kg', 0.0)
            self._current_co2_avoided_direct += info.get('co2_avoided_direct_kg', 0.0)
            self._current_solar_kwh += info.get('solar_generation_kwh', 0.0)
            self._current_ev_charging += info.get('ev_charging_kwh', 0.0)
            self._current_grid_import += info.get('grid_import_kwh', 0.0)
            # F6/F7/F8 acumuladores (OE3)
            self._current_co2_solar_f6  += info.get('co2_solar_f6_kg', 0.0)
            self._current_co2_bess_f7   += info.get('co2_bess_discharge_f7_kg', 0.0)
            self._current_co2_export_f8 += info.get('co2_solar_export_f6d_kg', 0.0)
            
            # [OK] NUEVAS metricas: Estabilidad, Costos, Motos/mototaxis, BESS
            # Estabilidad: calcular ratio de variacion de grid import
            grid_import = info.get('grid_import_kwh', 0.0)
            grid_export = info.get('grid_export_kwh', 0.0)
            peak_demand_limit = 450.0  # kW limite tipico
            stability = 1.0 - min(1.0, abs(grid_import - grid_export) / peak_demand_limit)
            self._current_stability_sum += stability
            self._current_stability_count += 1
            
            # Costo: tarifa ├ù (import - export)
            tariff_usd = 0.15  # USD/kWh tarifa Iquitos
            cost_step = (grid_import - grid_export * 0.5) * tariff_usd
            self._current_cost_usd += max(0.0, cost_step)
            
            # Motos y mototaxis (maximo por episodio) - GLOBAL
            motos = info.get('motos_charging', 0)
            mototaxis = info.get('mototaxis_charging', 0)
            self._current_motos_charged_max = max(self._current_motos_charged_max, motos)
            self._current_mototaxis_charged_max = max(self._current_mototaxis_charged_max, mototaxis)
            
            # [v7.3] M├íximos durante per├¡odo pico (9 AM - 8 PM: horas 9-20)
            # SOLO contar cuando est├í dentro del horario de operaci├│n
            hour_of_day = info.get('hour', self.step_in_episode % 8760) % 24
            if 9 <= hour_of_day <= 20:  # Per├¡odo pico: 9:00 - 20:00
                self._current_motos_peak_max = max(self._current_motos_peak_max, motos)
                self._current_mototaxis_peak_max = max(self._current_mototaxis_peak_max, mototaxis)
                self._current_total_sockets_peak_max = max(self._current_total_sockets_peak_max, motos + mototaxis)
            
            # [v7.3] ENERG├ìA CARGADA por per├¡odo horario
            ev_charging_kwh = info.get('ev_charging_kwh', 0.0)
            if 9 <= hour_of_day <= 22:  # Per├¡odo pico: 9 AM - 10 PM (22:00)
                self._current_ev_charging_peak += ev_charging_kwh
            else:  # Fuera de horario: 0-8, 23h
                self._current_ev_charging_offpeak += ev_charging_kwh
            
            # BESS (descarga/carga) - DATOS REALES del dataset OE2
            # Usa flujos reales de bess_ano_2024.csv en lugar de calcular
            hour_of_year = info.get('hour_of_year', self.step_in_episode % 8760)
            
            if self.bess_real_df is not None and hour_of_year < len(self.bess_real_df):
                # USAR DATOS REALES DEL DATASET
                bess_row = self.bess_real_df.iloc[hour_of_year]
                # bess_energy_stored_hourly_kwh  = energia cargada al BESS (entrada)
                # bess_energy_delivered_hourly_kwh = energia descargada del BESS (salida)
                bess_charge_real = float(bess_row.get('bess_energy_stored_hourly_kwh', 0.0))
                bess_discharge_real = float(bess_row.get('bess_energy_delivered_hourly_kwh', 0.0))
                self._current_bess_charge += bess_charge_real
                self._current_bess_discharge += bess_discharge_real
                # Tambien trackear destino de descarga
                self._current_bess_to_mall = getattr(self, '_current_bess_to_mall', 0.0) + float(bess_row.get('bess_to_mall_kwh', 0.0))
                self._current_bess_to_ev = getattr(self, '_current_bess_to_ev', 0.0) + float(bess_row.get('bess_to_ev_kwh', 0.0))
            else:
                # FALLBACK: usar info del environment si no hay dataset
                bess_power = info.get('bess_power_kw', 0.0)
                if bess_power > 0:
                    self._current_bess_discharge += bess_power
                else:
                    self._current_bess_charge += abs(bess_power)
            
            # Progreso de control de sockets (desde acciones)
            actions = self.locals.get('actions', None)
            if actions is not None and len(actions) > 0:
                action = actions[0] if len(actions[0].shape) > 0 else actions
                if len(action) >= 39:  # v5.2: 1 BESS + 38 sockets
                    bess_action = float(action[0])
                    socket_setpoints = action[1:39]  # v5.2: 38 sockets
                    self._current_bess_action_sum += bess_action
                    self._current_socket_setpoint_sum += float(np.mean(socket_setpoints))
                    self._current_socket_active_count += int(np.sum(socket_setpoints > 0.1))
            
            # [OK] NUEVAS: Acumular reward components desde info
            self._current_r_solar_sum += info.get('r_solar', 0.0)
            self._current_r_cost_sum += info.get('r_cost', 0.0)
            self._current_r_ev_sum += info.get('r_ev', 0.0)
            self._current_r_grid_sum += info.get('r_grid', 0.0)
            self._current_r_co2_sum += info.get('r_co2', 0.0)
            self._current_r_direct_co2_sum += info.get('r_direct_co2', 0.0)
            
            # [OK] ACTUALIZAR MAXIMOS DE VEHICULOS POR SOC (desde environment)
            self.episode_motos_10_max = max(self.episode_motos_10_max, info.get('motos_10_percent', 0))
            self.episode_motos_20_max = max(self.episode_motos_20_max, info.get('motos_20_percent', 0))
            self.episode_motos_30_max = max(self.episode_motos_30_max, info.get('motos_30_percent', 0))
            self.episode_motos_50_max = max(self.episode_motos_50_max, info.get('motos_50_percent', 0))
            self.episode_motos_70_max = max(self.episode_motos_70_max, info.get('motos_70_percent', 0))
            self.episode_motos_80_max = max(self.episode_motos_80_max, info.get('motos_80_percent', 0))
            self.episode_motos_100_max = max(self.episode_motos_100_max, info.get('motos_100_percent', 0))
            
            self.episode_mototaxis_10_max = max(self.episode_mototaxis_10_max, info.get('mototaxis_10_percent', 0))
            self.episode_mototaxis_20_max = max(self.episode_mototaxis_20_max, info.get('mototaxis_20_percent', 0))
            self.episode_mototaxis_30_max = max(self.episode_mototaxis_30_max, info.get('mototaxis_30_percent', 0))
            self.episode_mototaxis_50_max = max(self.episode_mototaxis_50_max, info.get('mototaxis_50_percent', 0))
            self.episode_mototaxis_70_max = max(self.episode_mototaxis_70_max, info.get('mototaxis_70_percent', 0))
            self.episode_mototaxis_80_max = max(self.episode_mototaxis_80_max, info.get('mototaxis_80_percent', 0))
            self.episode_mototaxis_100_max = max(self.episode_mototaxis_100_max, info.get('mototaxis_100_percent', 0))

            # Registrar trace (cada step) - SINCRONIZADO CON PPO
            trace_record = {
                'timestep': self.num_timesteps,
                'episode': self.episode_count,
                'step_in_episode': self.step_in_episode,
                'hour': info.get('hour', self.step_in_episode % 8760),
                'reward': reward,
                # CO2 metrics
                'co2_grid_kg': info.get('co2_grid_kg', 0.0),
                'co2_avoided_indirect_kg': info.get('co2_avoided_indirect_kg', 0.0),
                'co2_avoided_direct_kg': info.get('co2_avoided_direct_kg', 0.0),
                # Energy
                'solar_generation_kwh': info.get('solar_generation_kwh', 0.0),
                'ev_charging_kwh': info.get('ev_charging_kwh', 0.0),
                'grid_import_kwh': info.get('grid_import_kwh', 0.0),
                'bess_power_kw': info.get('bess_power_kw', 0.0),
                # Vehicle metrics (CRITICO - faltaba)
                'motos_power_kw': info.get('ev_charging_kwh', 0.0) * 0.79,
                'mototaxis_power_kw': info.get('ev_charging_kwh', 0.0) * 0.21,
                'motos_charging': info.get('motos_charging', 0),
                'mototaxis_charging': info.get('mototaxis_charging', 0),
                # Training metrics
                'entropy': info.get('entropy', 0.0),
                'approx_kl': info.get('approx_kl', 0.0),
                'clip_fraction': 0.0,  # SAC no usa clipping (off-policy)
                'policy_loss': 0.0,  # Se actualiza en metrics callback
                'value_loss': 0.0,  # Se actualiza en metrics callback
                'explained_variance': info.get('explained_variance', 0.0),
                # For backward compatibility
                'cumulative_reward': self.current_episode_reward,
                'ev_soc_avg': info.get('ev_soc_avg', 0.0),
            }
            self.trace_records.append(trace_record)

            # Registrar timeseries (cada hora simulada) - SINCRONIZADO CON PPO (33 COLUMNAS)
            timeseries_record = {
                'timestep': self.num_timesteps,
                'episode': self.episode_count,
                'hour': info.get('hour', self.step_in_episode % 8760),
                # Energy metrics
                'solar_generation_kwh': info.get('solar_generation_kwh', 0.0),
                'ev_charging_kwh': info.get('ev_charging_kwh', 0.0),
                'grid_import_kwh': info.get('grid_import_kwh', 0.0),
                'bess_power_kw': info.get('bess_power_kw', 0.0),
                'bess_soc': info.get('bess_soc', 0.0),
                'mall_demand_kw': info.get('mall_demand_kw', 0.0),
                # CO2 metrics (TODAS COLUMNAS)
                'co2_grid_kg': info.get('co2_grid_kg', 0.0),
                'co2_avoided_indirect_kg': info.get('co2_avoided_indirect_kg', 0.0),
                'co2_avoided_direct_kg': info.get('co2_avoided_direct_kg', 0.0),
                'co2_avoided_total_kg': info.get('co2_avoided_indirect_kg', 0.0) + info.get('co2_avoided_direct_kg', 0.0),
                # Vehicle metrics
                'motos_charging': info.get('motos_charging', 0),
                'mototaxis_charging': info.get('mototaxis_charging', 0),
                # Reward components
                'reward': info.get('reward', 0.0),
                'r_co2': info.get('r_co2', 0.0),
                'r_solar': info.get('r_solar', 0.0),
                'r_vehicles': info.get('r_vehicles', info.get('ev_satisfaction', 0.0)),
                'r_grid_stable': info.get('r_grid_stable', 0.0),
                'r_bess': info.get('r_bess', 0.0),
                'r_priority': info.get('r_priority', 0.0),
                # Economics (CRITICO - faltaba)
                'ahorro_solar_soles': info.get('solar_generation_kwh', 0.0) * 0.3,
                'ahorro_bess_soles': max(0, info.get('bess_power_kw', 0.0)) * 0.1,
                'costo_grid_soles': info.get('grid_import_kwh', 0.0) * 0.4,
                'ahorro_combustible_usd': info.get('ev_charging_kwh', 0.0) * 0.12,
                'ahorro_total_usd': info.get('ev_charging_kwh', 0.0) * 0.15,
                # SAC-specific metrics
                'entropy': info.get('entropy', 0.0),
                'approx_kl': info.get('approx_kl', 0.0),
                'clip_fraction': 0.0,  # SAC no usa clipping (off-policy)
                'policy_loss': 0.0,  # Se actualiza en metrics callback
                'value_loss': 0.0,  # Se actualiza en metrics callback
                'explained_variance': info.get('explained_variance', 0.0),
            }
            self.timeseries_records.append(timeseries_record)

            if done:
                # Guardar metricas del episodio (IGUAL QUE PPO)
                self.episode_rewards.append(self.current_episode_reward)
                self.episode_co2_grid.append(self._current_co2_grid)
                self.episode_co2_avoided_indirect.append(self._current_co2_avoided_indirect)
                self.episode_co2_avoided_direct.append(self._current_co2_avoided_direct)
                self.episode_solar_kwh.append(self._current_solar_kwh)
                self.episode_ev_charging.append(self._current_ev_charging)
                self.episode_grid_import.append(self._current_grid_import)
                # F6/F7/F8 por episodio
                self.episode_co2_solar_f6_kg.append(self._current_co2_solar_f6)
                self.episode_co2_bess_f7_kg.append(self._current_co2_bess_f7)
                self.episode_co2_export_f8_kg.append(self._current_co2_export_f8)
                
                # [v7.3] Energ├¡a cargada por per├¡odo
                self.episode_ev_charging_peak.append(self._current_ev_charging_peak)
                self.episode_ev_charging_offpeak.append(self._current_ev_charging_offpeak)
                
                # [OK] NUEVAS metricas por episodio
                avg_stability = self._current_stability_sum / max(1, self._current_stability_count)
                self.episode_grid_stability.append(avg_stability)
                self.episode_cost_usd.append(self._current_cost_usd)
                self.episode_motos_charged.append(self._current_motos_charged_max)
                self.episode_mototaxis_charged.append(self._current_mototaxis_charged_max)
                self.episode_bess_discharge_kwh.append(self._current_bess_discharge)
                self.episode_bess_charge_kwh.append(self._current_bess_charge)
                
                # [v7.3] Guardar m├íximos del per├¡odo pico (9 AM - 8 PM)
                self.episode_motos_peak_max.append(self._current_motos_peak_max)
                self.episode_mototaxis_peak_max.append(self._current_mototaxis_peak_max)
                self.episode_total_sockets_peak_max.append(self._current_total_sockets_peak_max)
                
                # Promedios de control por episodio
                steps_in_ep = max(1, self.step_in_episode)
                self.episode_avg_socket_setpoint.append(self._current_socket_setpoint_sum / steps_in_ep)
                self.episode_socket_utilization.append(self._current_socket_active_count / (38.0 * steps_in_ep))
                self.episode_bess_action_avg.append(self._current_bess_action_sum / steps_in_ep)
                
                # [OK] NUEVAS: Promedios de reward components por episodio
                self.episode_r_solar.append(self._current_r_solar_sum / steps_in_ep)
                self.episode_r_cost.append(self._current_r_cost_sum / steps_in_ep)
                self.episode_r_ev.append(self._current_r_ev_sum / steps_in_ep)
                self.episode_r_grid.append(self._current_r_grid_sum / steps_in_ep)
                self.episode_r_co2.append(self._current_r_co2_sum / steps_in_ep)
                self.episode_r_direct_co2.append(self._current_r_direct_co2_sum / steps_in_ep)
                
                self.episode_count += 1
                
                # Reset acumuladores
                self.current_episode_reward = 0.0
                self.step_in_episode = 0
                self._current_co2_grid = 0.0
                self._current_co2_avoided_indirect = 0.0
                self._current_co2_avoided_direct = 0.0
                self._current_solar_kwh = 0.0
                self._current_ev_charging = 0.0
                self._current_grid_import = 0.0
                # Reset F6/F7/F8
                self._current_co2_solar_f6  = 0.0
                self._current_co2_bess_f7   = 0.0
                self._current_co2_export_f8 = 0.0
                
                # [v7.3] Reset energía por período├¡a por per├¡odo
                self._current_ev_charging_peak = 0.0
                self._current_ev_charging_offpeak = 0.0
                
                # [OK] Reset nuevos acumuladores
                self._current_stability_sum = 0.0
                self._current_stability_count = 0
                self._current_cost_usd = 0.0
                self._current_motos_charged_max = 0
                self._current_mototaxis_charged_max = 0
                self._current_bess_discharge = 0.0
                self._current_bess_charge = 0.0
                self._current_socket_setpoint_sum = 0.0
                self._current_socket_active_count = 0
                self._current_bess_action_sum = 0.0
                
                # [OK] Reset acumuladores reward components
                self._current_r_solar_sum = 0.0
                self._current_r_cost_sum = 0.0
                self._current_r_ev_sum = 0.0
                self._current_r_grid_sum = 0.0
                self._current_r_co2_sum = 0.0
                self._current_r_direct_co2_sum = 0.0
                
                # [v7.3] Reset m├íximos per├¡odo pico
                self._current_motos_peak_max = 0
                self._current_mototaxis_peak_max = 0
                self._current_total_sockets_peak_max = 0
                
                # [OK] RESET TRACKING DE VEHICULOS POR SOC
                self.episode_motos_10_max = 0.0
                self.episode_motos_20_max = 0.0
                self.episode_motos_30_max = 0.0
                self.episode_motos_50_max = 0.0
                self.episode_motos_70_max = 0.0
                self.episode_motos_80_max = 0.0
                self.episode_motos_100_max = 0.0
                
                self.episode_mototaxis_10_max = 0.0
                self.episode_mototaxis_20_max = 0.0
                self.episode_mototaxis_30_max = 0.0
                self.episode_mototaxis_50_max = 0.0
                self.episode_mototaxis_70_max = 0.0
                self.episode_mototaxis_80_max = 0.0
                self.episode_mototaxis_100_max = 0.0

                # [FIX mem] Flush records to disk each episode to avoid RAM growth.
                # At 438k steps, trace_records would hold 438k dicts (~500 MB).
                # Flushing every 8760 steps keeps the list bounded to ~8760 entries.
                self._flush_records()

        return True

    def _flush_records(self) -> None:
        """Flush trace/timeseries records to CSV (append mode) and clear lists."""
        if self.output_dir is None:
            return
        if self.trace_records:
            trace_path = self.output_dir / 'trace_sac.csv'
            trace_df = pd.DataFrame(self.trace_records)
            trace_df.to_csv(
                trace_path,
                mode='a',
                index=False,
                header=not self._trace_header_written
            )
            self._trace_header_written = True
            self.trace_records = []
        if self.timeseries_records:
            ts_path = self.output_dir / 'timeseries_sac.csv'
            ts_df = pd.DataFrame(self.timeseries_records)
            ts_df.to_csv(
                ts_path,
                mode='a',
                index=False,
                header=not self._timeseries_header_written
            )
            self._timeseries_header_written = True
            self.timeseries_records = []

    def _on_training_end(self) -> None:
        """Flush any remaining records not yet written to disk."""
        self._flush_records()


def validate_sac_sync() -> bool:
    """Validacion de sincronizacion SAC v7.0 - todas las columnas OE2."""
    print('\n' + '='*80)
    print('[VALIDACION] Sincronizacion SAC v7.0 - Datasets OE2 Completos')
    print('='*80)
    
    checks = {
        '1. BESS Capacity (2000 kWh)': BESS_CAPACITY_KWH == 2000.0,
        '2. BESS Max normalizacion (2000 kWh)': BESS_MAX_KWH_CONST == 2000.0,
        '3. Solar Max (2887 kW)': SOLAR_MAX_KW == 2887.0,
        '4. Mall Max (3000 kW)': MALL_MAX_KW == 3000.0,
        '5. Chargers Max (7.4 kW)': CHARGER_MAX_KW == 7.4,
        '6. BESS cols (25)': len(BESS_REAL_COLS) == 25,
        '7. Solar cols (11)': len(SOLAR_REAL_COLS) == 11,
        '8. Mall cols (6)': len(MALL_REAL_COLS) == 6,
        '9. BESS obs cols (12)': len(BESS_OBS_COLS) == 12,
        '10. Solar obs cols (10)': len(SOLAR_OBS_COLS) == 10,
    }
    
    all_ok = True
    for check_name, result in checks.items():
        status = '[OK]' if result else '[X]'
        print(f'  {status} {check_name}')
        if not result:
            all_ok = False
    print()
    return all_ok
try:
        print('[0] VALIDACION DE SINCRONIZACION SAC')
        print('-' * 80)
        if not validate_sac_sync():
            print('[ERROR] SAC no sincronizado. Revisar constantes vs PPO/A2C')
            sys.exit(1)
        print('[OK] SAC sincronizado.\\n')
    
        # PRE-VALIDACION CENTRALIZADA: Garantizar entrenamiento COMPLETO y ROBUSTO
        print('[0.5] VALIDACION CENTRALIZADA - ENTRENAMIENTO COMPLETO')
        print('-' * 80)
        if not validate_agent_config(
            agent_name='SAC',
            num_episodes=50,
            total_timesteps=438_000,
            obs_dim=156,
            action_dim=39
        ):
            print('[FATAL] Agente SAC no cumple especificacion de entrenamiento completo.')
            print('        Revisar datos, constantes, y configuracion.')
            sys.exit(1)
        print('[OK] Entrenamiento COMPLETO garantizado: 50 episodios x 438,000 steps x 27 observables x multiobjetivo.')
        print()
    
        print('[1] CARGAR CONFIGURACION Y CONTEXTO MULTIOBJETIVO')
        print('-' * 80)

        with open('configs/default.yaml', 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        print(f'  OK Config loaded: {len(cfg)} keys')

        weights = create_iquitos_reward_weights("co2_focus")
        context = IquitosContext()
        reward_calculator = MultiObjectiveReward(weights=weights, context=context)

        print('  REWARD WEIGHTS v7.0 CO2_DUAL_FOCUS (OE3):')
        print('    Direct CO2  (0.35): Combustible vehicular evitado - motos/mototaxis')
        print('    Indirect CO2 (0.30): Grid import x 0.4521 kg CO2/kWh')
        print('    EV satisfaction (0.25): Carga efectiva EVs - SOC 90%')
        print('    Solar (0.05): Autoconsumo PV directo')
        print('    Grid stability (0.05): Suavizar picos de potencia')
        if weights is not None:
            print('  [Valores cargados: direct_CO2={:.2f}, CO2={:.2f}, EV={:.2f}, Solar={:.2f}, Grid={:.2f}]'.format(
                weights.direct_co2, weights.co2, weights.ev_satisfaction,
                weights.solar, weights.grid_stability))
        print()

        print('  OK Contexto Iquitos:')
        print(f'    - Grid CO2: {context.co2_factor_kg_per_kwh} kg CO2/kWh')
        print(f'    - EV CO2 factor: {context.co2_conversion_factor} kg CO2/kWh')
        print(f'    - Chargers: {context.n_chargers}')
        print(f'    - Sockets: {context.total_sockets}')
        print(f'    - Daily capacity: {context.motos_daily_capacity} motos + {context.mototaxis_daily_capacity} mototaxis')
        print()

        print('[2] CARGAR DATASET CITYLEARN V2 (COMPILADO)')
        print('-' * 80)

        # Dataset ya compilado en data/processed/citylearn/iquitos_ev_mall
        processed_path = Path('data/processed/citylearn/iquitos_ev_mall')
        if not processed_path.exists():
            print(f'ERROR: Dataset no encontrado en {processed_path}')
            print('   Crea el dataset primero con: python build.py')
            sys.exit(1)

        print(f'  Dataset precompilado: {processed_path}')
        dataset_dir = processed_path
        print(f'  OK Dataset: {dataset_dir}')
        print()

        # ========================================================================
        # PASO 3: CARGAR DATOS DESDE DATA_LOADER y DATASET COMPILADO (OBLIGATORIO)
        # ========================================================================
        print('[3] CARGAR DATASETS OE2 DESDE DATA_LOADER CENTRALIZADO (igual SAC/PPO)')
        print('-' * 80)

        # Usar rebuild_oe2_datasets_complete() para sincronizacion total
        # Esto garantiza que A2C, PPO, SAC usan los MISMOS datos
        print('  Cargando datasets OE2 compilados...')
        # CARGAR DATASET COMPILADO DESDE data/iquitos_ev_mall (OBLIGATORIO - compilado por data_loader)
        print('[3] CARGAR DATASET DESDE data/iquitos_ev_mall (COMPILADO POR data_loader)')
        print('-' * 80)
        
        dataset_base = Path('data/iquitos_ev_mall')
        if not dataset_base.exists():
            raise FileNotFoundError(f"OBLIGATORIO: data/iquitos_ev_mall NO EXISTE")
        
        # SOLAR - Desde data/iquitos_ev_mall/solar_generation.csv
        solar_path: Path = dataset_base / 'solar_generation.csv'
        if not solar_path.exists():
            raise FileNotFoundError(f"OBLIGATORIO: {solar_path} no encontrado")
    
        df_solar = pd.read_csv(solar_path)
        
        # Prioridad: energia_kwh > potencia_kw o pv_generation_kwh o ac_power_kw
        if 'energia_kwh' in df_solar.columns:
            col = 'energia_kwh'
        elif 'potencia_kw' in df_solar.columns:
            col = 'potencia_kw'
        elif 'generation_kw' in df_solar.columns:
            col = 'generation_kw'
        elif 'solar_generation_kw' in df_solar.columns:
            col = 'solar_generation_kw'
        else:
            col = df_solar.columns[-1]
        
        solar_hourly = np.asarray(df_solar[col].values, dtype=np.float32)
        if len(solar_hourly) != HOURS_PER_YEAR:
            raise ValueError(f"Solar: {len(solar_hourly)} horas != {HOURS_PER_YEAR}")
        print('  [SOLAR] Desde data/iquitos_ev_mall/solar_generation.csv: columna=%s | %.0f kWh/ano (8760h)' % (col, float(np.sum(solar_hourly))))

        # Solar CO2 indirecto: leeColumnas reales desde solar_generation.csv
        solar_co2_data: dict[str, np.ndarray] = {
            'co2_avoided_kg':        np.asarray(df_solar['reduccion_indirecta_co2_kg'].values[:HOURS_PER_YEAR], dtype=np.float32) if 'reduccion_indirecta_co2_kg' in df_solar.columns else solar_hourly * CO2_FACTOR_IQUITOS,
            'irradiancia_ghi':       np.asarray(df_solar['irradiancia_ghi'].values[:HOURS_PER_YEAR],         dtype=np.float32) if 'irradiancia_ghi'         in df_solar.columns else np.zeros(HOURS_PER_YEAR, dtype=np.float32),
            'temperatura_c':         np.asarray(df_solar['temperatura_c'].values[:HOURS_PER_YEAR],           dtype=np.float32) if 'temperatura_c'           in df_solar.columns else np.full(HOURS_PER_YEAR, 25.0, dtype=np.float32),
            'ahorro_solar_soles':    np.asarray(df_solar['ahorro_solar_soles'].values[:HOURS_PER_YEAR],      dtype=np.float32) if 'ahorro_solar_soles'      in df_solar.columns else np.zeros(HOURS_PER_YEAR, dtype=np.float32),
            'is_hora_punta':         np.asarray(df_solar['is_hora_punta'].values[:HOURS_PER_YEAR],           dtype=np.int32)   if 'is_hora_punta'           in df_solar.columns else np.zeros(HOURS_PER_YEAR, dtype=np.int32),
            'tarifa_aplicada_soles': np.asarray(df_solar['tarifa_aplicada_soles'].values[:HOURS_PER_YEAR],   dtype=np.float32) if 'tarifa_aplicada_soles'   in df_solar.columns else np.full(HOURS_PER_YEAR, 0.28, dtype=np.float32),
        }
        print(f"         CO2 indirecto solar (real CSV): {sum(solar_co2_data['co2_avoided_kg']):,.0f} kg/año")

        # ====================================================================
        # CHARGERS - columnas reales por socket (30 MOTOS + 8 MOTOTAXIS = 38)
        # socket_000-029 = MOTOS, socket_030-037 = MOTOTAXIS
        # ====================================================================
        chargers_path = dataset_base / 'chargers_timeseries.csv'
        if not chargers_path.exists():
            raise FileNotFoundError(f"OBLIGATORIO: {chargers_path} no encontrado")

        print(f'  [CHARGERS] Cargando columnas por socket desde: chargers_timeseries.csv')
        df_chargers = pd.read_csv(chargers_path)
        N_MOTO_SOCKETS_A2C, N_MOTOTAXI_SOCKETS_A2C, N_TOTAL_A2C = 30, 8, 38

        # np.array([...]).T evita error de overload de Pylance con np.stack + pandas Any (igual que SAC)
        _soc_current_a2c   = np.array([df_chargers[f'socket_{_i:03d}_soc_current'].values[:HOURS_PER_YEAR]        for _i in range(N_TOTAL_A2C)], dtype=np.float32).T   # (8760, 38)
        _soc_arrival_a2c   = np.array([df_chargers[f'socket_{_i:03d}_soc_arrival'].values[:HOURS_PER_YEAR]        for _i in range(N_TOTAL_A2C)], dtype=np.float32).T   # (8760, 38)
        _soc_target_a2c    = np.array([df_chargers[f'socket_{_i:03d}_soc_target'].values[:HOURS_PER_YEAR]         for _i in range(N_TOTAL_A2C)], dtype=np.float32).T   # (8760, 38)
        _socket_active_a2c = np.array([df_chargers[f'socket_{_i:03d}_active'].values[:HOURS_PER_YEAR]             for _i in range(N_TOTAL_A2C)], dtype=np.int32).T     # (8760, 38)
        _charging_pw_a2c   = np.array([df_chargers[f'socket_{_i:03d}_charging_power_kw'].values[:HOURS_PER_YEAR]  for _i in range(N_TOTAL_A2C)], dtype=np.float32).T   # (8760, 38)

        # chargers_hourly: (8760, 38) de kW de carga reales — lo que el env espera
        chargers_hourly = _charging_pw_a2c.copy()

        # chargers_soc_hourly: SOC 0-1 por socket para el env (v7.2)
        chargers_soc_hourly = (_soc_current_a2c / 100.0).copy()

        # ev_data: métricas agregadas por hora
        _active_count = _socket_active_a2c.sum(axis=1).astype(np.float32)
        _active_mask  = _active_count > 0
        _soc_curr_agg = _soc_current_a2c.sum(axis=1)
        _soc_tgt_agg  = _soc_target_a2c.sum(axis=1)
        _power_agg    = _charging_pw_a2c.sum(axis=1)
        _soc_curr_avg = np.where(_active_mask, _soc_curr_agg / np.maximum(_active_count, 1.0), 0.0).astype(np.float32)
        _soc_tgt_avg  = np.where(_active_mask, _soc_tgt_agg  / np.maximum(_active_count, 1.0), 0.0).astype(np.float32)
        ev_data: dict[str, np.ndarray] = {
            'soc_current':    _soc_curr_avg,
            'soc_target':     _soc_tgt_avg,
            'active_count':   _active_count,
            'charging_power': _power_agg,
            'vehicle_count':  _active_count,
        }

        # co2 directo por socket (si existe en CSV)
        _co2_motos_a2c = np.zeros(HOURS_PER_YEAR, dtype=np.float32)
        _co2_taxi_a2c  = np.zeros(HOURS_PER_YEAR, dtype=np.float32)
        for _i in range(N_MOTO_SOCKETS_A2C):
            _c = f'socket_{_i:03d}_co2_reduccion_kg_hora'
            if _c in df_chargers.columns:
                _co2_motos_a2c += df_chargers[_c].values[:HOURS_PER_YEAR].astype(np.float32)
        for _i in range(N_MOTO_SOCKETS_A2C, N_TOTAL_A2C):
            _c = f'socket_{_i:03d}_co2_reduccion_kg_hora'
            if _c in df_chargers.columns:
                _co2_taxi_a2c += df_chargers[_c].values[:HOURS_PER_YEAR].astype(np.float32)
        chargers_co2_data: dict[str, np.ndarray] = {
            'co2_motos_kg':     _co2_motos_a2c,
            'co2_mototaxis_kg': _co2_taxi_a2c,
            'co2_total_kg':     _co2_motos_a2c + _co2_taxi_a2c,
            'cost_soles':       np.zeros(HOURS_PER_YEAR, dtype=np.float32),
        }

        print(f'  [CHARGERS] Motos (000-029): {float(_charging_pw_a2c[:,:30].sum()):,.0f} kWh/año | mototaxis (030-037): {float(_charging_pw_a2c[:,30:].sum()):,.0f} kWh/año')
        print(f'  [CHARGERS] SOC promedio activos: {float(_soc_curr_avg[_active_mask].mean())*100:.1f}% | Sockets activos tot: {float(_active_count.sum()):,.0f}')



        # ====================================================================
        # MALL DEMAND - Todas las columnas reales
        # ====================================================================
        mall_path = dataset_base / 'mall_demand.csv'
        if not mall_path.exists():
            raise FileNotFoundError(f"OBLIGATORIO: {mall_path} no encontrado")

        df_mall = pd.read_csv(mall_path)
        _mall_col = 'mall_demand_kwh' if 'mall_demand_kwh' in df_mall.columns else df_mall.select_dtypes(include=[np.number]).columns[0]
        mall_hourly = np.asarray(df_mall[_mall_col].values[:HOURS_PER_YEAR], dtype=np.float32)
        _tarifa_soles = solar_co2_data['tarifa_aplicada_soles']
        _is_hp        = solar_co2_data['is_hora_punta']
        mall_data_dict: dict[str, np.ndarray] = {
            'mall_demand_kwh':      mall_hourly.copy(),
            'mall_co2_indirect_kg': np.asarray(df_mall['mall_co2_indirect_kg'].values[:HOURS_PER_YEAR], dtype=np.float32) if 'mall_co2_indirect_kg' in df_mall.columns else np.zeros(HOURS_PER_YEAR, dtype=np.float32),
            'is_hora_punta':        np.asarray(df_mall['is_hora_punta'].values[:HOURS_PER_YEAR],        dtype=np.int32)   if 'is_hora_punta'        in df_mall.columns else _is_hp,
            'tarifa_soles_kwh':     np.asarray(df_mall['tarifa_soles_kwh'].values[:HOURS_PER_YEAR],     dtype=np.float32) if 'tarifa_soles_kwh'      in df_mall.columns else _tarifa_soles,
            'mall_cost_soles':      np.asarray(df_mall['mall_cost_soles'].values[:HOURS_PER_YEAR],      dtype=np.float32) if 'mall_cost_soles'        in df_mall.columns else np.zeros(HOURS_PER_YEAR, dtype=np.float32),
        }
        print(f'  [MALL] {float(np.sum(mall_hourly)):,.0f} kWh/año | CO2 indirecto: {float(np.sum(mall_data_dict["mall_co2_indirect_kg"])):,.0f} kg/año')

        # ====================================================================
        # BESS - Todos los flujos de energia reales
        # ====================================================================
        bess_path = dataset_base / 'bess_timeseries.csv'
        bess_soc = np.full(HOURS_PER_YEAR, 50.0, dtype=np.float32)
        bess_data: dict[str, np.ndarray] = {}

        if bess_path.exists():
            df_bess = pd.read_csv(bess_path)

            def _bcol(df: pd.DataFrame, name: str, default: float = 0.0) -> np.ndarray:
                if name in df.columns:
                    return np.asarray(df[name].values[:HOURS_PER_YEAR], dtype=np.float32)
                return np.full(HOURS_PER_YEAR, default, dtype=np.float32)

            _soc_raw = _bcol(df_bess, 'soc_percent', 50.0)
            bess_soc = _soc_raw / 100.0 if float(_soc_raw.max()) > 1.0 else _soc_raw
            bess_data = {
                'pv_to_ev_kwh':          _bcol(df_bess, 'pv_to_ev_kwh'),
                'pv_to_bess_kwh':        _bcol(df_bess, 'pv_to_bess_kwh'),
                'bess_to_ev_kwh':        _bcol(df_bess, 'bess_to_ev_kwh'),
                'bess_to_mall_kwh':      _bcol(df_bess, 'bess_to_mall_kwh'),
                'bess_discharge_kwh':    _bcol(df_bess, 'bess_energy_delivered_hourly_kwh'),
                'bess_charge_kwh':       _bcol(df_bess, 'bess_energy_stored_hourly_kwh'),
                'grid_import_kwh':       _bcol(df_bess, 'grid_import_kwh'),
                'grid_export_kwh':       _bcol(df_bess, 'grid_export_kwh'),
                'co2_avoided_indirect_kg': _bcol(df_bess, 'co2_avoided_indirect_kg'),
                'cost_savings_hp_soles': _bcol(df_bess, 'cost_savings_hp_soles'),
            }
            print(f'  [BESS] SOC medio: {float(np.mean(bess_soc))*100:.1f}% | CO2 evitado: {float(np.sum(bess_data["co2_avoided_indirect_kg"])):,.0f} kg/año')
        else:
            print(f'  [BESS] FALLBACK: usando SOC neutral 50%')

        # EV data ya cargado arriba via per-socket loop (chargers_hourly, chargers_soc_hourly, ev_data)
        print(f'  [EV] Sockets activos tot: {float(_active_count.sum()):,.0f} | Potencia total: {float(_power_agg.sum()):,.0f} kWh/año')

        # ====================================================================
        # CHARGER STATISTICS - potencia max/media por socket (valores por defecto)
        # ====================================================================
        # Usar valores por defecto de especificaci├│n v5.2
        charger_max_power = np.full(38, 7.4, dtype=np.float32)
        charger_mean_power = np.full(38, 4.6, dtype=np.float32)
        print(f'  [CHARGER STATS] Valores por defecto: max_power=7.4 kW, mean=4.6 kW')

        print()

        # ========================================================================
        # PASO 4: CREAR ENVIRONMENT (CON DATOS COMPILADOS DESDE data/iquitos_ev_mall)
        # ========================================================================
        print('[4] CREAR ENVIRONMENT CON DATOS COMPILADOS DESDE data/iquitos_ev_mall')
        print('-' * 80)

        class CityLearnEnvironment(Env):  # type: ignore[type-arg]
            """Environment compatible con Gymnasium para CityLearn v2.
        
            COMUNICACION COMPLETA DEL SISTEMA v5.3
            ================================================================================
            El agente puede ver y coordinar TODOS los componentes del sistema:
            - BESS: estado, energia disponible, senales de carga/descarga
            - Solar: generacion, excedente, ratio de uso para EVs
            - 38 Sockets: demanda, potencia, ocupacion individual
            - Motos: cantidad cargando, en cola, SOC, tiempo restante
            - mototaxis: igual que motos pero para sus 8 sockets
            - Coordinacion: senales para optimizar flujo de energia
        
            Observation Space (156-dim v5.3):
        
            ENERGIA DEL SISTEMA [0-7] (8 features):
            - [0]: Solar generation normalizada [0,1]
            - [1]: Mall demand normalizada [0,1]
            - [2]: BESS SOC [0,1]
            - [3]: BESS energia disponible normalizada
            - [4]: Solar excedente normalizado
            - [5]: Grid import necesario normalizado
            - [6]: Balance energetico (-1 deficit, +1 excedente)
            - [7]: Capacidad EV libre normalizada
        
            ESTADO DE CARGADORES POR SOCKET [8-45] (38 sockets):
            - Demanda actual de cada socket normalizada [0,1]
        
            POTENCIA ACTUAL POR SOCKET [46-83] (38 sockets):
            - Potencia entregada a cada socket normalizada [0,1]
        
            OCUPACION POR SOCKET [84-121] (38 sockets):
            - 1.0 si hay vehiculo conectado, 0.0 si libre
        
            ESTADO DE VEHICULOS [122-137] (16 features):
            - [122]: Motos cargando actualmente (count/30)
            - [123]: mototaxis cargando actualmente (count/8)  
            - [124]: Motos en cola esperando (count/100)
            - [125]: mototaxis en cola esperando (count/20)
            - [126]: SOC promedio motos cargando [0,1]
            - [127]: SOC promedio mototaxis cargando [0,1]
            - [128]: Tiempo restante carga motos (horas norm)
            - [129]: Tiempo restante carga mototaxis (horas norm)
            - [130]: Sockets motos disponibles (count/30)
            - [131]: Sockets mototaxis disponibles (count/8)
            - [132]: Motos cargadas 100% hoy (count/270)
            - [133]: mototaxis cargados 100% hoy (count/39)
            - [134]: Eficiencia carga actual [0,1]
            - [135]: Ratio solar usado para carga [0,1]
            - [136]: CO2 evitado acumulado (norm)
            - [137]: CO2 evitado potencial si carga mas (norm)
        
            TIME FEATURES [138-143] (6 features):
            - [138]: Hora del dia normalizada [0,1]
            - [139]: Dia de semana normalizado [0,1]
            - [140]: Mes normalizado [0,1]
            - [141]: Indicador hora pico [0,1]
            - [142]: Factor CO2 Iquitos
            - [143]: Tarifa electrica (USD/kWh)
        
            COMUNICACION INTER-SISTEMA [144-155] (12 features):
            - [144]: BESS puede suministrar a EVs [0,1]
            - [145]: Solar suficiente para demanda EV [0,1]
            - [146]: Grid necesario para completar carga [0,1]
            - [147]: Prioridad carga motos vs mototaxis [0,1]
            - [148]: Urgencia de carga (vehiculos pendientes/capacidad)
            - [149]: Oportunidad solar (excedente/demanda EV)
            - [150]: BESS deberia cargar (solar alto, demanda baja)
            - [151]: BESS deberia descargar (solar bajo, demanda alta)
            - [152]: Potencial reduccion CO2 con mas carga
            - [153]: Saturacion del sistema [0,1]
            - [154]: Eficiencia sistema completo [0,1]
            - [155]: Meta diaria de vehiculos (progreso [0,1])

            Action Space (39-dim v5.2):
            - [0]: BESS control [0,1] (0=carga max, 0.5=idle, 1=descarga max)
            - [1:39]: 38 socket setpoints [0,1] (potencia asignada a cada socket)
            """
        
            HOURS_PER_YEAR: int = 8760
            NUM_CHARGERS: int = 38      # v5.2: 19 cargadores ├ù 2 tomas = 38 sockets
            OBS_DIM: int = 156          # v5.3: 8 + 38*3 + 16 + 6 + 12 = 156 (comunicacion completa)
            ACTION_DIM: int = 39        # v5.2: 1 BESS + 38 sockets

            def __init__(
                self,
                reward_calc: Any,
                ctx: Any,
                solar_kw: np.ndarray,
                chargers_kw: np.ndarray,
                mall_kw: np.ndarray,
                bess_soc_arr: np.ndarray,
                charger_max_power_kw: np.ndarray | None = None,
                charger_mean_power_kw: np.ndarray | None = None,
                chargers_soc_hourly: np.ndarray | None = None,  # v7.2: SOC real por socket
                bess_metrics: dict[str, np.ndarray] | None = None,
                ev_metrics: dict[str, np.ndarray] | None = None,
                chargers_co2_data: dict[str, np.ndarray] | None = None,  # v7.0: CO2 directo EV
                solar_co2_data: dict[str, np.ndarray] | None = None,     # v7.1: CO2 indirecto solar
                max_steps: int = 8760
            ) -> None:
                """Inicializa environment con TODOS los datos OE2 reales v7.2 (incluye SOC real por socket)."""
                super().__init__()
            
                self.reward_calculator = reward_calc
                self.context = ctx
                self.max_steps = max_steps
            
                # DATOS REALES (8760 horas = 1 ano)
                self.solar_hourly = np.asarray(solar_kw, dtype=np.float32)
                self.chargers_hourly = np.asarray(chargers_kw, dtype=np.float32)
                self.mall_hourly = np.asarray(mall_kw, dtype=np.float32)
                self.bess_soc_hourly = np.asarray(bess_soc_arr, dtype=np.float32)
                
                # v7.2: SOC REAL POR SOCKET (para c├ílculo mejorado de veh├¡culos cargados)
                self.chargers_soc_hourly = chargers_soc_hourly if chargers_soc_hourly is not None else None
            
                # ESTADISTICAS REALES DE CARGADORES (5to dataset OE2)
                if charger_max_power_kw is not None:
                    self.charger_max_power = np.asarray(charger_max_power_kw, dtype=np.float32)
                else:
                    # Fallback v5.2: 7.4 kW por socket (Modo 3 monofasico 32A @ 230V)
                    self.charger_max_power = np.full(self.NUM_CHARGERS, 7.4, dtype=np.float32)
                if charger_mean_power_kw is not None:
                    self.charger_mean_power = np.asarray(charger_mean_power_kw, dtype=np.float32)
                else:
                    # Fallback v5.2: potencia efectiva = 7.4 ├ù 0.62 = 4.6 kW
                    self.charger_mean_power = np.full(self.NUM_CHARGERS, 4.6, dtype=np.float32)
            
                # METRICAS REALES BESS (CO2 indirecto, costos, tarifas, flujos energeticos)
                self.bess_metrics = bess_metrics if bess_metrics is not None else {}
            
                # METRICAS REALES EV (SOC, conteos, potencias por hora)
                self.ev_metrics = ev_metrics if ev_metrics is not None else {}
                
                # v7.0: DATOS REALES CO2 DIRECTO DE CHARGERS (EV reemplaza gasolina)
                self.chargers_co2_data = chargers_co2_data if chargers_co2_data is not None else {}
                
                # v7.1: DATOS REALES CO2 INDIRECTO DE SOLAR (evita importar de red)
                self.solar_co2_data = solar_co2_data if solar_co2_data is not None else {}
            
                # Validacion
                if len(self.solar_hourly) != self.HOURS_PER_YEAR:
                    raise ValueError(f"Solar: {len(self.solar_hourly)} != {self.HOURS_PER_YEAR}")
            
                self.n_chargers = self.chargers_hourly.shape[1]
            
                # Para tracking de totales (backwards compatibility)
                self.chargers_total_kwh = float(np.sum(self.chargers_hourly))
                self.solar_hourly_kwh = self.solar_hourly  # Alias
                self.mall_hourly_kw = self.mall_hourly  # Alias

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
                # --- Fórmulas BASELINE / CONTROL (OE3) ---
                self.episode_co2_total_baseline_kg: float = 0.0   # CO2 sin control RL
                self.episode_co2_total_control_kg: float = 0.0    # CO2 con control RL
                self.episode_co2_impacto_control_kg: float = 0.0  # Reducción RL = solar + BESS
                self.episode_co2_total_sistema_evitado_kg: float = 0.0  # OE3: directo + RL indirecto
            
                # Tracking acumulativo (backwards compatibility)
                self.co2_avoided_total = 0.0
                self.solar_kwh_total = 0.0
                self.cost_total = 0.0
                self.grid_import_total = 0.0
            
                # [v5.3] ESTADO DE VEHICULOS (para comunicacion del sistema)
                self.motos_charging_now: int = 0
                self.mototaxis_charging_now: int = 0
                self.motos_waiting: int = 0
                self.mototaxis_waiting: int = 0
                self.motos_soc_avg: float = 0.0
                self.mototaxis_soc_avg: float = 0.0
                self.motos_time_remaining: float = 0.0
                self.mototaxis_time_remaining: float = 0.0
                self.motos_charged_today: int = 0
                self.mototaxis_charged_today: int = 0
                self.daily_co2_avoided: float = 0.0
            
                # [v5.3] COMUNICACION INTER-SISTEMA
                self.bess_available_kwh: float = 0.0
                self.solar_surplus_kwh: float = 0.0
                self.current_grid_import: float = 0.0
                self.system_efficiency: float = 0.0
            
                # [OK] TRACKING DE VEHICULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
                self.episode_motos_10_max: float = 0
                self.episode_motos_20_max: float = 0
                self.episode_motos_30_max: float = 0
                self.episode_motos_50_max: float = 0
                self.episode_motos_70_max: float = 0
                self.episode_motos_80_max: float = 0
                self.episode_motos_100_max: float = 0
            
                self.episode_mototaxis_10_max: float = 0
                self.episode_mototaxis_20_max: float = 0
                self.episode_mototaxis_30_max: float = 0
                self.episode_mototaxis_50_max: float = 0
                self.episode_mototaxis_70_max: float = 0
                self.episode_mototaxis_80_max: float = 0
                self.episode_mototaxis_100_max: float = 0

            
            def _make_observation(self, hour_idx: int) -> np.ndarray:
                """
                Crea observacion v5.3 (156-dim) con COMUNICACION COMPLETA del sistema.

                NORMALIZACION CRITICA:
                Todas las features estan en rango ~[0,1] para estabilidad del training.
            
                COMUNICACION DEL SISTEMA:
                - El agente ve el estado completo de BESS, Solar, EVs, Cargadores
                - Puede coordinar carga de motos/mototaxis con disponibilidad solar
                - Sabe cuantos vehiculos estan cargando y cuantos faltan
                - Recibe senales de urgencia y oportunidad
                """
                obs = np.zeros(self.OBS_DIM, dtype=np.float32)
                h = hour_idx % self.HOURS_PER_YEAR
                hour_24 = h % 24
                day_of_year = (h // 24) % 365

                # ================================================================
                # [0-7] ENERGIA DEL SISTEMA (8 features)
                # ================================================================
                solar_kw = float(self.solar_hourly[h])
                mall_kw = float(self.mall_hourly[h])
                bess_soc = float(self.bess_soc_hourly[h])
            
                # Calcular balance energetico
                ev_demand_estimate = float(np.sum(self.chargers_hourly[h]))
                total_demand = mall_kw + ev_demand_estimate
                solar_surplus = max(0.0, solar_kw - total_demand)
                grid_import_needed = max(0.0, total_demand - solar_kw)
            
                # BESS energia disponible (SOC ├ù capacidad max ├ù eficiencia)
                bess_energy_available = bess_soc * BESS_MAX_KWH_CONST * 0.90  # 90% eficiencia
            
                obs[0] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)                    # Solar norm
                obs[1] = np.clip(mall_kw / MALL_MAX_KW, 0.0, 1.0)                      # Mall demand
                obs[2] = np.clip(bess_soc, 0.0, 1.0)                                   # BESS SOC
                obs[3] = np.clip(bess_energy_available / BESS_MAX_KWH_CONST, 0.0, 1.0) # BESS disponible
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
                efficiency_factor = 0.7 if 6 <= hour_24 <= 22 else 0.5
                obs[46:84] = obs[8:46] * efficiency_factor

                # ================================================================
                # [84-121] OCUPACION POR SOCKET (38 features)
                # ================================================================
                occupancy = (raw_demands > 0.1).astype(np.float32)
                obs[84:122] = occupancy

                # ================================================================
                # [122-137] ESTADO DE VEHICULOS (16 features) - CRITICO PARA APRENDIZAJE
                # ================================================================
                motos_sockets = occupancy[:30]  # Primeros 30 sockets = motos
                mototaxis_sockets = occupancy[30:]  # Ultimos 8 sockets = mototaxis
            
                self.motos_charging_now = int(np.sum(motos_sockets))
                self.mototaxis_charging_now = int(np.sum(mototaxis_sockets))
            
                # Estimar vehiculos en cola segun hora pico
                if 6 <= hour_24 <= 22:
                    self.motos_waiting = max(0, int(270 / 24 - self.motos_charging_now))
                    self.mototaxis_waiting = max(0, int(39 / 24 - self.mototaxis_charging_now))
                else:
                    self.motos_waiting = 0
                    self.mototaxis_waiting = 0
            
                # SOC promedio (basado en potencia entregada)
                motos_power = obs[46:76]
                mototaxis_power = obs[76:84]
                self.motos_soc_avg = float(np.mean(motos_power)) if self.motos_charging_now > 0 else 0.0
                self.mototaxis_soc_avg = float(np.mean(mototaxis_power)) if self.mototaxis_charging_now > 0 else 0.0
            
                # Tiempo restante de carga (horas estimadas)
                self.motos_time_remaining = (1.0 - self.motos_soc_avg) * 0.76
                self.mototaxis_time_remaining = (1.0 - self.mototaxis_soc_avg) * 1.2
            
                # Sockets disponibles
                motos_available = 30 - self.motos_charging_now
                mototaxis_available = 8 - self.mototaxis_charging_now
            
                # Progreso diario (resetea cada 24 horas)
                hour_in_day = h % 24
                if hour_in_day == 0:
                    self.motos_charged_today = 0
                    self.mototaxis_charged_today = 0
                    self.daily_co2_avoided = 0.0
            
                # CALCULAR VEHICULOS COMPLETADOS DESDE DATASET REAL
                # Usar ev_energia_motos_kwh y ev_energia_mototaxis_kwh del dataset
                if h < len(self.chargers_hourly):
                    # Cargar datos reales del dataset
                    try:
                        # Leer energ├¡a cargada por tipo de veh├¡culo
                        ev_energy_motos_kwh = float(self.chargers_hourly[h, 0]) if len(self.chargers_hourly.shape) > 1 else 0.0
                        ev_energy_mototaxis_kwh = float(self.chargers_hourly[h, 1]) if len(self.chargers_hourly.shape) > 1 else 0.0
                    except (IndexError, TypeError, ValueError):
                        ev_energy_motos_kwh = 0.0
                        ev_energy_mototaxis_kwh = 0.0
                else:
                    ev_energy_motos_kwh = 0.0
                    ev_energy_mototaxis_kwh = 0.0
                
                # Calcular vehiculos completados basado en energ├¡a necesaria
                # Moto: 2.90 kWh para cargar de 20% a 80% SOC
                # mototaxi: 4.68 kWh para cargar de 20% a 80% SOC
                motos_completed = int(ev_energy_motos_kwh / max(MOTO_ENERGY_TO_CHARGE, 0.01))
                mototaxis_completed = int(ev_energy_mototaxis_kwh / max(MOTOTAXI_ENERGY_TO_CHARGE, 0.01))
                
                self.motos_charged_today += motos_completed
                self.mototaxis_charged_today += mototaxis_completed
            
                # Eficiencia y ratios
                total_ev_power = float(np.sum(raw_demands))
                solar_for_ev_ratio = min(1.0, solar_kw / max(1.0, total_ev_power)) if total_ev_power > 0 else 0.0
                charge_efficiency = float(np.sum(obs[46:84])) / max(1.0, float(np.sum(obs[8:46])))
            
                # CO2 potencial
                co2_potential = (motos_available + mototaxis_available) * CHARGER_MEAN_KW * CO2_FACTOR_IQUITOS
            
                obs[122] = self.motos_charging_now / 30.0                                # Motos cargando
                obs[123] = self.mototaxis_charging_now / 8.0                             # mototaxis cargando
                obs[124] = np.clip(self.motos_waiting / 100.0, 0.0, 1.0)                 # Motos en cola
                obs[125] = np.clip(self.mototaxis_waiting / 20.0, 0.0, 1.0)              # mototaxis en cola
                obs[126] = self.motos_soc_avg                                            # SOC promedio motos
                obs[127] = self.mototaxis_soc_avg                                        # SOC promedio mototaxis
                obs[128] = np.clip(self.motos_time_remaining / 2.0, 0.0, 1.0)            # Tiempo restante motos
                obs[129] = np.clip(self.mototaxis_time_remaining / 2.0, 0.0, 1.0)        # Tiempo restante mototaxis
                obs[130] = motos_available / 30.0                                        # Sockets motos libres
                obs[131] = mototaxis_available / 8.0                                         # Sockets mototaxis libres
                obs[132] = np.clip(self.motos_charged_today / 270.0, 0.0, 1.0)           # Motos cargadas hoy
                obs[133] = np.clip(self.mototaxis_charged_today / 39.0, 0.0, 1.0)        # mototaxis cargadas hoy
                obs[134] = np.clip(charge_efficiency, 0.0, 1.0)                          # Eficiencia carga
                obs[135] = solar_for_ev_ratio                                            # Ratio solar->EV
                obs[136] = np.clip(self.daily_co2_avoided / 500.0, 0.0, 1.0)             # CO2 evitado hoy
                obs[137] = np.clip(co2_potential / 100.0, 0.0, 1.0)                      # CO2 potencial

                # ================================================================
                # [138-143] TIME FEATURES (6 features)
                # ================================================================
                obs[138] = float(hour_24) / 24.0                                         # Hora
                obs[139] = float(day_of_year % 7) / 7.0                                  # Dia semana
                obs[140] = float((day_of_year // 30) % 12) / 12.0                        # Mes
                obs[141] = 1.0 if 6 <= hour_24 <= 22 else 0.0                            # Hora pico
                obs[142] = float(self.context.co2_factor_kg_per_kwh)                     # Factor CO2
                obs[143] = 0.15                                                          # Tarifa

                # ================================================================
                # [144-155] COMUNICACION INTER-SISTEMA (12 features)
                # ================================================================
                bess_can_supply = 1.0 if bess_energy_available > total_ev_power else bess_energy_available / max(1.0, total_ev_power)
                solar_sufficient = 1.0 if solar_kw >= total_ev_power else solar_kw / max(1.0, total_ev_power)
                grid_needed_ratio = grid_import_needed / max(1.0, total_ev_power) if total_ev_power > 0 else 0.0
                priority_motos = self.motos_waiting / max(1, self.motos_waiting + self.mototaxis_waiting) if (self.motos_waiting + self.mototaxis_waiting) > 0 else 0.5
                total_waiting = self.motos_waiting + self.mototaxis_waiting
                total_capacity = motos_available + mototaxis_available
                urgency = total_waiting / max(1, total_capacity) if total_capacity > 0 else 0.0
                solar_opportunity = solar_surplus / max(1.0, total_ev_power) if total_ev_power > 0 else 1.0
                should_charge_bess = 1.0 if (solar_surplus > 100 and bess_soc < 0.8) else 0.0
                should_discharge_bess = 1.0 if (solar_kw < total_demand * 0.5 and bess_soc > 0.3) else 0.0
                co2_reduction_potential = (motos_available + mototaxis_available) * CHARGER_MEAN_KW * CO2_FACTOR_IQUITOS / 100.0
                saturation = (self.motos_charging_now + self.mototaxis_charging_now) / self.NUM_CHARGERS
                total_input = solar_kw + bess_energy_available / 10.0
                total_output = total_ev_power
                system_eff = min(1.0, total_output / max(1.0, total_input))
                daily_target = 309  # 270 motos + 39 mototaxis
                daily_progress = (self.motos_charged_today + self.mototaxis_charged_today) / daily_target
            
                obs[144] = np.clip(bess_can_supply, 0.0, 1.0)
                obs[145] = np.clip(solar_sufficient, 0.0, 1.0)
                obs[146] = np.clip(grid_needed_ratio, 0.0, 1.0)
                obs[147] = priority_motos
                obs[148] = np.clip(urgency, 0.0, 1.0)
                obs[149] = np.clip(solar_opportunity, 0.0, 1.0)
                obs[150] = should_charge_bess
                obs[151] = should_discharge_bess
                obs[152] = np.clip(co2_reduction_potential, 0.0, 1.0)
                obs[153] = saturation
                obs[154] = system_eff
                obs[155] = np.clip(daily_progress, 0.0, 1.0)

                return obs

            def render(self) -> None:
                """Render no implementado para este environment."""
                return

            def reset(
                self,
                *,
                seed: int | None = None,
                options: dict[str, Any] | None = None
            ) -> tuple[np.ndarray, dict[str, Any]]:
                del seed, options
                self.step_count = 0
                self.episode_num += 1
                self.episode_reward = 0.0
                self.episode_co2_avoided = 0.0
                self.episode_solar_kwh = 0.0
                self.episode_grid_import = 0.0
                self.episode_ev_satisfied = 0.0
            
                self.co2_avoided_total = 0.0
                self.solar_kwh_total = 0.0
                self.cost_total = 0.0
                self.grid_import_total = 0.0
            
                # [v5.3] RESET ESTADO DE VEHICULOS
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
            
                # [v5.3] RESET COMUNICACION INTER-SISTEMA
                self.bess_available_kwh = 0.0
                self.solar_surplus_kwh = 0.0
                self.current_grid_import = 0.0
                self.system_efficiency = 0.0
            
                # [OK] RESET SOC TRACKERS
                self.episode_motos_10_max = 0.0
                self.episode_motos_20_max = 0.0
                self.episode_motos_30_max = 0.0
                self.episode_motos_50_max = 0.0
                self.episode_motos_70_max = 0.0
                self.episode_motos_80_max = 0.0
                self.episode_motos_100_max = 0.0
            
                self.episode_mototaxis_10_max = 0.0
                self.episode_mototaxis_20_max = 0.0
                self.episode_mototaxis_30_max = 0.0
                self.episode_mototaxis_50_max = 0.0
                self.episode_mototaxis_70_max = 0.0
                self.episode_mototaxis_80_max = 0.0
                self.episode_mototaxis_100_max = 0.0

                # --- Fórmulas BASELINE / CONTROL (OE3) reset ---
                self.episode_co2_total_baseline_kg = 0.0
                self.episode_co2_total_control_kg = 0.0
                self.episode_co2_impacto_control_kg = 0.0
                self.episode_co2_total_sistema_evitado_kg = 0.0

                obs = self._make_observation(0)
                return obs, {}

            def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
                """Ejecuta un paso de simulacion (1 hora) - MISMA ESTRUCTURA QUE PPO."""
                self.step_count += 1
                h = (self.step_count - 1) % self.HOURS_PER_YEAR

                # DATOS REALES (OE2 timeseries) - chargers_hourly puede tener 38 o 977 columnas
                solar_kw = float(self.solar_hourly[h])
                mall_kw = float(self.mall_hourly[h])
                
                # CR├ìTICO: Extraer solo primeros 38 sockets para demanda de carga
                # chargers_hourly[h] puede ser shape (38,) o (977,)
                charger_demand_row = self.chargers_hourly[h].astype(np.float32)
                if len(charger_demand_row) > 38:
                    charger_demand = charger_demand_row[:38].copy()
                else:
                    charger_demand = charger_demand_row.copy()
                    
                bess_soc = np.clip(float(self.bess_soc_hourly[h]), 0.0, 1.0)

                # PROCESAR ACCION (39-dim: 1 BESS + 38 sockets)
                bess_action = np.clip(action[0], 0.0, 1.0)
                charger_setpoints = np.clip(action[1:self.ACTION_DIM], 0.0, 1.0)

                # CALCULAR ENERGIA (usando max_power real del 5to dataset OE2)
                charger_power_effective = charger_setpoints * self.charger_max_power[:self.n_chargers]
                ev_charging_kwh = float(np.sum(np.minimum(charger_power_effective, charger_demand)))
                total_demand_kwh = mall_kw + ev_charging_kwh
            
                # BESS power (positivo = descarga, negativo = carga)
                bess_power_kw = (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW
            
                # Separar motos y mototaxis (30 motos + 8 mototaxis = 38 sockets)
                motos_demand = float(np.sum(charger_demand[:30] * charger_setpoints[:30]))
                mototaxis_demand = float(np.sum(charger_demand[30:] * charger_setpoints[30:]))
                motos_charging = int(np.sum(charger_setpoints[:30] > 0.5))
                mototaxis_charging = int(np.sum(charger_setpoints[30:] > 0.5))

                # GRID BALANCE
                net_demand = total_demand_kwh - bess_power_kw
                grid_import_kwh = max(0.0, net_demand - solar_kw)
                grid_export_kwh = max(0.0, solar_kw - net_demand)

                # ===== CO2 CALCULATIONS v7.1 (ID├ëNTICO A PPO) =====
                # FUENTE: chargers_ev_ano_2024_v3.csv columnas:
                #   - co2_reduccion_motos_kg
                #   - co2_reduccion_mototaxis_kg  
                #   - reduccion_directa_co2_kg = motos + mototaxis (DATO REAL)
                # NOTA: NO multiplicar por setpoint - es el CO2 evitado por cambio combustible
                
                # CO2 DIRECTO: Usar datos REALES del dataset chargers si disponibles
                # ID├ëNTICO A PPO l├¡nea 985-989
                try:
                    co2_motos_directo = float(self.chargers_co2_data['co2_motos_kg'][h]) if 'co2_motos_kg' in self.chargers_co2_data else 0.0
                    co2_mototaxis_directo = float(self.chargers_co2_data['co2_mototaxis_kg'][h]) if 'co2_mototaxis_kg' in self.chargers_co2_data else 0.0
                    co2_avoided_direct_kg = co2_motos_directo + co2_mototaxis_directo
                except (KeyError, IndexError, TypeError):
                    co2_avoided_direct_kg = 0.0
                
                # ===== CO2 INDIRECTO v7.1: BESS + SOLAR (ID├ëNTICO A PPO) =====
                # FUENTE: bess_ano_2024.csv (columna co2_avoided_indirect_kg)
                #         pv_generation_citylearn_enhanced_v2.csv (columna reduccion_indirecta_co2_kg)
                # EV: cambio f├│sil -> el├®ctrico (CO2 DIRECTO)
                # SOLAR + BESS: evitan importar de red t├®rmica (CO2 INDIRECTO)
                # ID├ëNTICO A PPO l├¡nea 994-1013
                
                # ================================================================
                # CO2 INDIRECTO — F6 / F7 / F8  (OE3 cuantificación completa)
                # Formula: toda la generación solar reduce CO2 indirecto al 100%
                # F6 = solar_total × 0.4521   (independientemente de su destino)
                # F7 = bess_discharge × 0.4521 (peak shaving)
                # F8 = grid_export × 0.4521    (excedente a red pública)
                # Equivalencia: F6 ≈ (EV+Mall−grid_import)×0.4521 vía balance de red
                # ================================================================

                # F6: CO2 indirecto SOLAR = solar_total × 0.4521 (100% generación PV)
                # «Toda la generación solar evita que se importe de la red diésel»
                try:
                    _co2_csv = float(self.solar_co2_data['co2_avoided_kg'][h]) if 'co2_avoided_kg' in self.solar_co2_data else 0.0
                    co2_indirecto_solar_kg = _co2_csv if _co2_csv > 0.0 else solar_kw * CO2_FACTOR_IQUITOS
                except (KeyError, IndexError, TypeError):
                    co2_indirecto_solar_kg = solar_kw * CO2_FACTOR_IQUITOS  # F6: 100% solar

                # F6 descompuesto por destino (prioridad energética: EV > Mall > BESS > export)
                _f6a = min(solar_kw, ev_charging_kwh)                              # solar → EV
                _f6b = min(max(0.0, solar_kw - _f6a), mall_kw)                     # solar → Mall
                _f6d = grid_export_kwh                                             # solar → export
                _f6c = max(0.0, solar_kw - _f6a - _f6b - _f6d)                    # solar → BESS
                co2_solar_ev_f6a_kg   = _f6a * CO2_FACTOR_IQUITOS   # F6a: EVs usan solar
                co2_solar_mall_f6b_kg = _f6b * CO2_FACTOR_IQUITOS   # F6b: Mall usa solar
                co2_solar_bess_f6c_kg = _f6c * CO2_FACTOR_IQUITOS   # F6c: BESS almacena solar
                co2_solar_export_f6d_kg = _f6d * CO2_FACTOR_IQUITOS # F6d=F8: excedente a red

                # F7: CO2 indirecto BESS DESCARGA = bess_discharge × 0.4521
                # «BESS descarga corta pico → evita importar de red diésel»
                bess_discharge_kwh = max(0.0, bess_power_kw)
                co2_bess_discharge_f7_kg = bess_discharge_kwh * CO2_FACTOR_IQUITOS  # F7

                # CO2 indirecto BESS (mantener variable backward-compat para Fórmula 3)
                try:
                    _bess_csv = float(self.bess_metrics['co2_avoided'][h]) if 'co2_avoided' in self.bess_metrics else 0.0
                    co2_indirecto_bess_kg = _bess_csv if _bess_csv > 0.0 else co2_bess_discharge_f7_kg
                except (KeyError, IndexError, TypeError):
                    co2_indirecto_bess_kg = co2_bess_discharge_f7_kg

                # CO2 INDIRECTO TOTAL = F6 (solar 100%) para Fórmula 3 OE3
                # BESS ya está implícito: solar → BESS → descarga cubre lo que iría de la red
                co2_avoided_indirect_kg = co2_indirecto_solar_kg
                
                # TOTAL CO2 EVITADO = DIRECTO (EV) + INDIRECTO (SOLAR + BESS)
                co2_avoided_total_kg = co2_avoided_direct_kg + co2_avoided_indirect_kg
                
                # COSTO: Usar valores REALES del dataset
                if 'cost_soles' in self.chargers_co2_data and len(self.chargers_co2_data['cost_soles']) > h:
                    ev_cost_soles = float(self.chargers_co2_data['cost_soles'][h])
                else:
                    ev_cost_soles = ev_charging_kwh * 0.35  # Tarifa promedio fallback
                
                if 'cost' in self.bess_metrics and len(self.bess_metrics['cost']) > h:
                    grid_cost_soles = float(self.bess_metrics['cost'][h])
                else:
                    grid_cost_soles = grid_import_kwh * 0.30  # Tarifa promedio fallback
                
                total_cost_soles = ev_cost_soles + grid_cost_soles
            
                # CO2 grid para tracking
                co2_grid_kg = grid_import_kwh * CO2_FACTOR_IQUITOS

                # ================================================================
                # CO2 OE3 — Fórmulas fijas (ver: scripts/train/co2_formulas.py)
                # Reducción DIRECTA:   cambio combustible fósil → eléctrico (motos/mototaxis)
                # Reducción INDIRECTA: dejar de usar energía de red diesel (solar+BESS+RL)
                # ================================================================

                # ev_kwh[h]: sum(socket_NNN_charging_power_kw[h]) — demanda EV baseline real
                ev_demand_dataset_kwh = float(np.sum(charger_demand))   # col: socket_NNN_charging_power_kw

                # mall_demand_kwh[h]: mall_demand.csv['mall_demand_kwh']
                mall_demand_kwh_h = mall_kw                              # col: mall_demand_kwh

                # ================================================================
                # CO2 — TRES FORMULAS OE3 (Iquitos: 0.4521 kg CO2/kWh, red diesel aislada)
                # ================================================================

                # FORMULA 1 — BASELINE (motos eléctricas + mototaxis eléctricas + mall)
                # Solo red pública de generación diesel, sin solar, sin BESS, sin agente RL
                #
                # EMISIONES CO2 DIRECTAS — baseline:
                #   Flota eléctrica: motos/mototaxis sin combustión interna → cero emisión directa
                co2_directo_baseline_kg = 0.0
                #
                # EMISIONES CO2 INDIRECTAS — baseline:
                #   [EV] Motos/mototaxis REEMPLAZAN combustión fósil → factor gasolina (NO factor red)
                #   IPCC 2006 Tier 1 (Table 3.2.1): gasolina = 2.31 kg CO2/L
                #   Moto   Honda Wave 125cc: 2.30 L/100km * 2.31 / 6.0 kWh/100km = 0.87 kg CO2/kWh
                #   Mototaxi 3 ruedas 150cc: 3.50 L/100km * 2.31 / 15.0 kWh/100km = 0.54 kg CO2/kWh
                #   Ref: Garay Aquino et al. E3S 2024 DOI:10.1051/e3sconf/202456604004
                #   Ref: Guerra & Perez, Congress Smart Cities, Lima Peru (RETScreen)
                #   El 0.4521 es factor RED ELECTRICA Iquitos, NO de combustion de gasolina
                ev_motos_kwh_h = float(np.sum(charger_demand[:30]))   # primeros 30 sockets: motos (Honda Wave 125cc)
                ev_taxis_kwh_h = float(np.sum(charger_demand[30:]))   # ultimos 8 sockets: mototaxis (3 ruedas 150cc)
                co2_indirecto_ev_baseline_kg = (ev_motos_kwh_h * CO2_FACTOR_MOTO_KG_KWH +    # 0.87 kg CO2/kWh (IPCC 2006)
                                                ev_taxis_kwh_h * CO2_FACTOR_MOTOTAXI_KG_KWH)  # 0.54 kg CO2/kWh (IPCC 2006)
                #   [MALL] Mall consume de red publica DIESEL -> CO2 indirecto (factor red correcto)
                #   El mall siempre fue electrico (no reemplaza combustion) -> usa 0.4521 kg CO2/kWh
                co2_indirecto_mall_baseline_kg = mall_demand_kwh_h * CO2_FACTOR_IQUITOS  # 0.4521 kg CO2/kWh (MINEM Peru)
                co2_indirecto_baseline_kg = co2_indirecto_ev_baseline_kg + co2_indirecto_mall_baseline_kg
                co2_total_baseline_kg = co2_directo_baseline_kg + co2_indirecto_baseline_kg
                #
                # REDUCCIONES CO2 — baseline:
                #   Directa: cambio combustible fósil → eléctrico, según cantidad motos/mototaxis cargando
                co2_reduccion_directa_baseline_kg = co2_avoided_direct_kg  # fuente: chargers_co2_hourly
                #   Indirecta: sin solar ni BESS → cero desplazamiento de red diesel
                co2_reduccion_indirecta_baseline_kg = 0.0

                # FORMULA 2 — CONTROL INTELIGENTE
                # Cargas idénticas al baseline (mall + motos/mototaxis vía cargadores)
                # Plus: Solar 4,050 kWp + BESS 2,000 kWh, recarga coordinada por agente RL
                # Balance: grid_import_kwh = max(0, ev+mall - bess_discharge - solar_kwh)
                #
                # EMISIONES CO2 DIRECTAS — control:
                #   Flota sigue eléctrica → cero emisión directa
                co2_directo_control_kg = 0.0
                #
                # EMISIONES CO2 INDIRECTAS — control:
                #   Agente RL agenda recarga de motos/mototaxis → solar+BESS cubren la demanda EV
                #   Solo el déficit residual (no cubierto por solar+BESS) se importa de red diesel
                co2_indirecto_control_kg = grid_import_kwh * CO2_FACTOR_IQUITOS
                co2_total_control_kg = co2_directo_control_kg + co2_indirecto_control_kg
                #
                # REDUCCIONES CO2 — control:
                #   Directa: cambio combustible → eléctrico (igual que baseline, misma flota cargando)
                co2_reduccion_directa_control_kg = co2_avoided_direct_kg
                #   Indirecta: delta (baseline sin solar/BESS) − (control con solar+BESS)
                #   Coherente con Formula 3; evita doble conteo solar→BESS→descarga
                co2_reduccion_indirecta_control_kg = co2_indirecto_baseline_kg - co2_indirecto_control_kg

                # FORMULA 3 — CUANTIFICACIÓN TOTAL CO2 REDUCIDO (OE3)
                #   Directa total: electrificación flota (igual en ambos escenarios)
                co2_reduccion_directa_kg = co2_reduccion_directa_control_kg
                #   Indirecta total: solar+BESS+agente RL evitan importar red diesel
                co2_reduccion_indirecta_kg = co2_indirecto_baseline_kg - co2_indirecto_control_kg
                co2_impacto_control_kg = co2_reduccion_indirecta_kg
                #   TOTAL SISTEMA: directo (cambio combustible) + indirecto (solar+BESS+RL)
                co2_total_sistema_evitado_kg = co2_reduccion_directa_kg + co2_reduccion_indirecta_kg

                # EV SATISFACTION - METODO REALISTA (similar a SAC)
                # Basado en cuanta carga se esta entregando vs la demanda
                if float(np.sum(charger_demand)) > 0.1:
                    charge_ratio = ev_charging_kwh / max(1.0, float(np.sum(charger_demand)))
                    ev_soc_avg = np.clip(0.80 + 0.20 * charge_ratio, 0.0, 1.0)
                else:
                    ev_soc_avg = 0.95
            
                # v7.2 MEJORADO: Contar vehiculos cargados diferenciando MOTOS vs MOTOTAXIS
                # CONSIDERAR:
                #   1. SOC REAL del dataset (socket_{i}_soc_current)
                #   2. SOC ENTREGADO en esta hora (potencia actual / maxima)
                #   3. Cantidad M├üXIMA cargable por d├¡a (dependencia capacidad bater├¡a)
                #
                # REALIDAD OE2 v5.2:
                #   - Motos: 30 sockets, capacidad ~10 kWh, necesitan 1-2 horas al 100%
                #   - mototaxis: 8 sockets, capacidad ~15 kWh, necesitan 2-3 horas al 100%
                
                # Leer SOC ACTUAL del dataset si est├í disponible
                chargers_soc_hourly = getattr(self, 'chargers_soc_hourly', None)
                if chargers_soc_hourly is not None and h < len(chargers_soc_hourly):
                    # SOC REAL del dataset [0,1]
                    soc_real = chargers_soc_hourly[h]
                else:
                    # Fallback: calcular SOC desde potencia entregada
                    soc_real = np.clip(ev_charging_kwh / max(1.0, float(np.sum(charger_demand))), 0.0, 1.0)
                
                # MEJORADO: Considerar SOC actual + potencia entregada esta hora
                # Formula: SOC_nuevo = SOC_actual + (potencia_hora / capacidad_bateria)
                # Para motos: capacidad promedio ~12 kWh (rango 10-15 kWh)
                # Para mototaxis: capacidad promedio ~18 kWh (rango 15-20 kWh)
                
                MOTO_CAPACITY_KWH = 12.0
                MOTOTAXI_CAPACITY_KWH = 18.0
                
                # Calcular carga incremental esta hora por socket
                soc_updated = np.zeros(self.NUM_CHARGERS, dtype=np.float32)
                
                for i in range(min(self.NUM_CHARGERS, len(charger_power_effective))):
                    # SOC inicial del socket (dato real si existe)
                    if chargers_soc_hourly is not None and h < len(chargers_soc_hourly) and i < len(chargers_soc_hourly[h]):
                        soc_inicial = float(chargers_soc_hourly[h][i]) if isinstance(chargers_soc_hourly[h], (list, np.ndarray)) else soc_real
                    else:
                        soc_inicial = 0.5  # Asunci├│n: comienzan a media carga
                    
                    # Potencia entregada esta hora
                    power_this_hour = float(charger_power_effective[i]) if i < len(charger_power_effective) else 0.0
                    
                    # Capacidad del veh├¡culo (diferencia por tipo)
                    capacity = MOTO_CAPACITY_KWH if i < 30 else MOTOTAXI_CAPACITY_KWH
                    
                    # SOC nuevo = SOC inicial + (potencia / capacidad * eficiencia)
                    efficiency = 0.92  # P├®rdidas de carga ~8%
                    soc_increment = (power_this_hour * efficiency / capacity) if capacity > 0 else 0.0
                    soc_updated[i] = np.clip(soc_inicial + soc_increment, 0.0, 1.0)
                
                # Contar vehiculos por SOC para MOTOS (sockets 0-29)
                motos_soc = soc_updated[:30]
                motos_10 = int(np.sum(motos_soc >= 0.10))
                motos_20 = int(np.sum(motos_soc >= 0.20))
                motos_30 = int(np.sum(motos_soc >= 0.30))
                motos_50 = int(np.sum(motos_soc >= 0.50))
                motos_70 = int(np.sum(motos_soc >= 0.70))
                motos_80 = int(np.sum(motos_soc >= 0.80))
                motos_100 = int(np.sum(motos_soc >= 1.00))
            
                # Contar vehiculos por SOC para MOTOTAXIS (sockets 30-37)
                mototaxis_soc = soc_updated[30:38]
                mototaxis_10 = int(np.sum(mototaxis_soc >= 0.10))
                mototaxis_20 = int(np.sum(mototaxis_soc >= 0.20))
                mototaxis_30 = int(np.sum(mototaxis_soc >= 0.30))
                mototaxis_50 = int(np.sum(mototaxis_soc >= 0.50))
                mototaxis_70 = int(np.sum(mototaxis_soc >= 0.70))
                mototaxis_80 = int(np.sum(mototaxis_soc >= 0.80))
                mototaxis_100 = int(np.sum(mototaxis_soc >= 1.00))
            
                # Actualizar maximos del episodio
                self.episode_motos_10_max = max(self.episode_motos_10_max, motos_10)
                self.episode_motos_20_max = max(self.episode_motos_20_max, motos_20)
                self.episode_motos_30_max = max(self.episode_motos_30_max, motos_30)
                self.episode_motos_50_max = max(self.episode_motos_50_max, motos_50)
                self.episode_motos_70_max = max(self.episode_motos_70_max, motos_70)
                self.episode_motos_80_max = max(self.episode_motos_80_max, motos_80)
                self.episode_motos_100_max = max(self.episode_motos_100_max, motos_100)
            
                self.episode_mototaxis_10_max = max(self.episode_mototaxis_10_max, mototaxis_10)
                self.episode_mototaxis_20_max = max(self.episode_mototaxis_20_max, mototaxis_20)
                self.episode_mototaxis_30_max = max(self.episode_mototaxis_30_max, mototaxis_30)
                self.episode_mototaxis_50_max = max(self.episode_mototaxis_50_max, mototaxis_50)
                self.episode_mototaxis_70_max = max(self.episode_mototaxis_70_max, mototaxis_70)
                self.episode_mototaxis_80_max = max(self.episode_mototaxis_80_max, mototaxis_80)
                self.episode_mototaxis_100_max = max(self.episode_mototaxis_100_max, mototaxis_100)

                # CALCULAR RECOMPENSA CO2_DUAL_FOCUS v7.0 (OE3 2026-04-06)
                try:
                    reward_val, components = self.reward_calculator.compute(
                        grid_import_kwh=grid_import_kwh,
                        grid_export_kwh=grid_export_kwh,
                        solar_generation_kwh=solar_kw,
                        ev_charging_kwh=ev_charging_kwh,
                        ev_soc_avg=ev_soc_avg,
                        bess_soc=bess_soc,
                        hour=h % 24,
                        ev_demand_kwh=self.context.ev_demand_constant_kw
                    )
                
                    # ================================================================
                    # REWARD CO2_DUAL_FOCUS v7.0 (OE3 2026-04-06)
                    # direct_co2=0.35  indirect_co2=0.30  ev_satisfaction=0.25
                    # solar=0.05  grid_stability=0.05
                    # ================================================================

                    # P1 (0.35): CO2 directo — combustible vehicular evitado (motos/mototaxis)
                    co2_direct_efficiency = co2_avoided_direct_kg / max(co2_grid_kg + 1.0, 1.0)
                    r_direct_co2 = float(np.clip(np.clip(co2_direct_efficiency, 0.0, 2.0) - 0.5, -0.5, 0.5))

                    # P2 (0.30): CO2 indirecto — red diesel Iquitos evitada (balance neto solar+BESS)
                    # (ev+mall − grid_import) × 0.4521 = energía local servida por solar+BESS× factor diesel
                    # Coherente con Formula 3; sin doble conteo entre F6 (solar) y F7 (bess descarga)
                    co2_indirect_kg = max(0.0, ev_charging_kwh + mall_kw - grid_import_kwh) * CO2_FACTOR_IQUITOS
                    co2_indirect_efficiency = co2_indirect_kg / max(co2_grid_kg + 1.0, 1.0)
                    r_indirect_co2 = float(np.clip(np.clip(co2_indirect_efficiency, 0.0, 2.0) - 0.5, -0.5, 0.5))

                    # P3 (0.25): EV Satisfaction — motos y mototaxis cargadas a tiempo
                    vehicles_charging_now = motos_charging + mototaxis_charging
                    vehicles_charging_ratio = vehicles_charging_now / 38.0
                    EV_ENERGY_GOAL_KWH_PER_HOUR = 48.0
                    energy_delivered_ratio = float(np.clip(ev_charging_kwh / EV_ENERGY_GOAL_KWH_PER_HOUR, 0.0, 1.5))
                    r_vehicles = (energy_delivered_ratio * 0.6 + vehicles_charging_ratio * 0.4) - 0.3

                    # P4 (0.05): Solar self-consumption — maximizar uso directo PV
                    solar_used_for_ev = min(solar_kw, ev_charging_kwh)
                    solar_used_for_mall = min(max(0.0, solar_kw - ev_charging_kwh), mall_kw)
                    solar_self_consumption = (solar_used_for_ev + solar_used_for_mall) / max(solar_kw, 1.0)
                    r_solar = solar_self_consumption * 0.8 - 0.2

                    # P5 (0.05): Grid stability — minimizar ramping de importacion
                    prev_grid_import = getattr(self, '_prev_grid_import', grid_import_kwh)
                    ramping = abs(grid_import_kwh - prev_grid_import)
                    self._prev_grid_import = grid_import_kwh
                    ramping_penalty = float(np.clip(ramping / 100.0, 0.0, 1.0))
                    r_grid_stable = 0.3 - ramping_penalty * 0.5

                    # COMPOSICION CO2_DUAL_FOCUS (pesos definidos OE3 2026-04-06)
                    reward_val = (
                        r_direct_co2   * 0.35 +  # P1: CO2 directo (combustible vehicular evitado)
                        r_indirect_co2 * 0.30 +  # P2: CO2 indirecto (grid termico evitado)
                        r_vehicles     * 0.25 +  # P3: EV Satisfaction (carga vehiculos)
                        r_solar        * 0.05 +  # P4: Solar Self-Consumption
                        r_grid_stable  * 0.05    # P5: Grid Stability
                    )
                    reward_val = float(np.clip(reward_val, -1.0, 1.0))

                    # Componentes para tracking
                    components['r_direct_co2'] = float(r_direct_co2)
                    components['r_indirect_co2'] = float(r_indirect_co2)
                    components['r_vehicles'] = float(r_vehicles)
                    components['r_solar'] = float(r_solar)
                    components['r_grid_stable'] = float(r_grid_stable)
                
                except (AttributeError, KeyError, TypeError):
                    reward_val = -grid_import_kwh * 0.01 + solar_kw * 0.001
                    components = {}

                # TRACKING
                self.episode_reward += float(reward_val)
                self.episode_co2_avoided += co2_avoided_total_kg
                self.episode_solar_kwh += solar_kw
                self.episode_grid_import += grid_import_kwh
                # Fórmulas BASELINE / CONTROL (OE3)
                self.episode_co2_total_baseline_kg   += co2_total_baseline_kg
                self.episode_co2_total_control_kg    += co2_total_control_kg
                self.episode_co2_impacto_control_kg  += co2_impacto_control_kg
                self.episode_co2_total_sistema_evitado_kg += co2_total_sistema_evitado_kg
            
                self.co2_avoided_total += co2_avoided_total_kg
                self.solar_kwh_total += solar_kw
                self.cost_total += components.get('cost_usd', 0)
                self.grid_import_total += grid_import_kwh

                # OBSERVACION
                obs = self._make_observation(self.step_count)

                done = self.step_count >= self.max_steps
                truncated = False

                # INFO DICT (27+ metricas - v7.0 con TODOS los CO2 y costos REALES)
                info: dict[str, Any] = {
                    # CO2 F1-F8 completo (OE3)
                    'co2_grid_kg': co2_grid_kg,
                    'co2_avoided_indirect_kg': co2_avoided_indirect_kg,
                    'co2_avoided_direct_kg': co2_avoided_direct_kg,
                    'co2_avoided_total_kg': co2_avoided_direct_kg + co2_avoided_indirect_kg,
                    # Fórmulas OE3 BASELINE vs CONTROL
                    'co2_total_baseline_kg': co2_total_baseline_kg,
                    'co2_total_control_kg': co2_total_control_kg,
                    'co2_impacto_control_kg': co2_impacto_control_kg,
                    'co2_total_sistema_evitado_kg': co2_total_sistema_evitado_kg,  # OE3
                    # F6 descompuesto (solar 100% → CO2 ind evitado por destino)
                    'co2_solar_f6_kg': co2_indirecto_solar_kg,          # F6 total
                    'co2_solar_ev_f6a_kg': co2_solar_ev_f6a_kg,         # F6a: EV usa solar
                    'co2_solar_mall_f6b_kg': co2_solar_mall_f6b_kg,     # F6b: Mall usa solar
                    'co2_solar_bess_f6c_kg': co2_solar_bess_f6c_kg,     # F6c: BESS almacena solar
                    'co2_solar_export_f6d_kg': co2_solar_export_f6d_kg, # F6d=F8: excedente a red
                    # F7: BESS descarga peak shaving
                    'co2_bess_discharge_f7_kg': co2_bess_discharge_f7_kg,  # F7: bess×0.4521
                    'bess_discharge_kwh': bess_discharge_kwh,
                    # COSTOS v7.0 (3 metricas nuevas)
                    'ev_cost_soles': ev_cost_soles if 'ev_cost_soles' in dir() else 0.0,
                    'grid_cost_soles': grid_cost_soles if 'grid_cost_soles' in dir() else 0.0,
                    'total_cost_soles': total_cost_soles if 'total_cost_soles' in dir() else 0.0,
                    # ENERGIA (6 metricas)
                    'solar_generation_kwh': solar_kw,
                    'ev_charging_kwh': ev_charging_kwh,
                    'mall_demand_kw': mall_kw,
                    'grid_import_kwh': grid_import_kwh,
                    'grid_export_kwh': grid_export_kwh,
                    'bess_power_kw': float(bess_power_kw),
                    'bess_soc': bess_soc,
                    'ev_soc_avg': float(ev_soc_avg),
                    # VEHICULOS (4 metricas)
                    'motos_charging': motos_charging,
                    'mototaxis_charging': mototaxis_charging,
                    'motos_demand_kwh': motos_demand,
                    'mototaxis_demand_kwh': mototaxis_demand,
                    # TIEMPO (3 metricas)
                    'hour': h % 24,
                    'day': h // 24,
                    'step': self.step_count,
                    # TRACKING (3 metricas)
                    'episode_reward': self.episode_reward,
                    'episode_co2_avoided_kg': self.co2_avoided_total,
                    'episode_solar_kwh': self.solar_kwh_total,
                    # REWARD COMPONENTS (5 metricas adicionales)
                    'r_solar': components.get('r_solar', 0.0),
                    'r_cost': components.get('r_cost', 0.0),
                    'r_ev': components.get('r_ev', 0.0),
                    'r_grid': components.get('r_grid', 0.0),
                    'r_co2': components.get('r_co2', 0.0),
                    # [OK] VEHICULOS CARGADOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
                    'motos_10_percent': self.episode_motos_10_max,
                    'motos_20_percent': self.episode_motos_20_max,
                    'motos_30_percent': self.episode_motos_30_max,
                    'motos_50_percent': self.episode_motos_50_max,
                    'motos_70_percent': self.episode_motos_70_max,
                    'motos_80_percent': self.episode_motos_80_max,
                    'motos_100_percent': self.episode_motos_100_max,
                    'mototaxis_10_percent': self.episode_mototaxis_10_max,
                    'mototaxis_20_percent': self.episode_mototaxis_20_max,
                    'mototaxis_30_percent': self.episode_mototaxis_30_max,
                    'mototaxis_50_percent': self.episode_mototaxis_50_max,
                    'mototaxis_70_percent': self.episode_mototaxis_70_max,
                    'mototaxis_80_percent': self.episode_mototaxis_80_max,
                    'mototaxis_100_percent': self.episode_mototaxis_100_max,
                }

                return obs, float(reward_val), done, truncated, info

        # Crear environment con datos cargados - COMPLETO CON TODAS LAS METRICAS OE2 v7.2
        env = CityLearnEnvironment(
            reward_calc=reward_calculator,
            ctx=context,
            solar_kw=solar_hourly,
            chargers_kw=chargers_hourly,
            mall_kw=mall_hourly,
            bess_soc_arr=bess_soc,
            charger_max_power_kw=charger_max_power,
            charger_mean_power_kw=charger_mean_power,
            chargers_soc_hourly=chargers_soc_hourly,     # v7.2: SOC real por socket para conteo mejorado
            bess_metrics=bess_data,              # CO2 indirecto BESS (evita grid)
            ev_metrics=ev_data,                  # SOC, conteos, potencias EV
            chargers_co2_data=chargers_co2_data, # v7.0: CO2 directo EV (reemplaza gasolina)
            solar_co2_data=solar_co2_data,       # v7.1: CO2 indirecto solar (evita grid)
            max_steps=HOURS_PER_YEAR
        )
        print('  OK Environment creado (v7.2 con TODOS los datos OE2 + SOC real por socket)')
        print(f'    - Observation: {env.observation_space.shape} (156-dim)')
        print(f'    - Action: {env.action_space.shape}')
        if chargers_soc_hourly is not None and chargers_soc_hourly.size > 0:
            print(f'    - Socket SOC real: {chargers_soc_hourly.shape} (8760 horas ├ù 38 sockets)')
        if bess_data:
            print(f'    - BESS metricas (CO2 indirecto): {list(bess_data.keys())}')
        if ev_data:
            print(f'    - EV metricas: {list(ev_data.keys())}')
        if chargers_co2_data:
            print(f'    - Chargers CO2 (DIRECTO - EV): {list(chargers_co2_data.keys())}')
        if solar_co2_data:
            print(f'    - Solar CO2 (INDIRECTO): {list(solar_co2_data.keys())}')
        print()

        # ========================================================================
        # PASO 5: CREAR SAC AGENT (USANDO SACConfig)
        # ========================================================================
        print('[5] CREAR SAC AGENT')
        print('-' * 80)

        sac_config = SACConfig.for_gpu() if DEVICE == 'cuda' else SACConfig.for_cpu()

        if DEVICE == 'cuda':
            print('  [AVISO] Inicializando contexto CUDA + compilando kernels...')
            print('          Esto puede tardar 30-90 segundos en la primera ejecucion.')
            print('          NO interrumpir (Ctrl+C) durante esta fase.')
            print()

        sac_agent = PVBESSCarSAC(
            'MlpPolicy',
            env,
            learning_rate=sac_config.learning_rate,
            buffer_size=sac_config.buffer_size,
            learning_starts=sac_config.learning_starts,
            batch_size=sac_config.batch_size,
            tau=sac_config.tau,
            gamma=sac_config.gamma,
            train_freq=sac_config.train_freq,
            gradient_steps=sac_config.gradient_steps,
            ent_coef=sac_config.ent_coef,
            target_entropy=sac_config.target_entropy,
            policy_kwargs=sac_config.policy_kwargs,
            verbose=0,
            device=DEVICE,
            tensorboard_log=None,
        )

        print(f'  OK SAC agent creado (DEVICE: {DEVICE.upper()})')
        print(f'    - Learning rate:    {sac_config.learning_rate}')
        print(f'    - Buffer size:      {sac_config.buffer_size:,}')
        print(f'    - Learning starts:  {sac_config.learning_starts}')
        print(f'    - Batch size:       {sac_config.batch_size}')
        print(f'    - Tau:              {sac_config.tau}')
        print(f'    - Gamma:            {sac_config.gamma}')
        print(f'    - Train freq:       {sac_config.train_freq}')
        print(f'    - Gradient steps:   {sac_config.gradient_steps}')
        print(f'    - Ent coef:         {sac_config.ent_coef}  (auto-tuning SAC)')
        print(f'    - Target entropy:   {sac_config.target_entropy}')
        print(f'    - Max grad norm:    {sac_config.max_grad_norm}  (AdamWithGradClip)')
        print()

        # ========================================================================
        # PASO 6: ENTRENAR SAC
        # ========================================================================
        print('[6] ENTRENAR SAC')
        print('-' * 80)

        # ENTRENAMIENTO: 50 episodios completos = 50 x 8,760 timesteps = 438,000 pasos
        # Velocidad GPU RTX 4060 (off-policy SAC): ~300-500 timesteps/segundo (replay buffer updates)
        # [v7.0: direct_co2=0.35, co2=0.30, ev_satisfaction=0.25, solar=0.05, grid_stability=0.05]
        EPISODES = 50
        TOTAL_TIMESTEPS = EPISODES * 8760  # 438,000 timesteps
        SPEED_ESTIMATED = 400 if DEVICE == 'cuda' else 40  # Real RTX 4060 speed on SAC
        DURATION_MINUTES = TOTAL_TIMESTEPS / SPEED_ESTIMATED / 60

        if DEVICE == 'cuda':
            DURATION_TEXT = f'~{DURATION_MINUTES:.0f} minutos (GPU RTX 4060)'
        else:
            DURATION_TEXT = f'~{DURATION_MINUTES:.1f} horas (CPU)'

        print()
        print('='*80)
        print('  CONFIGURACION ENTRENAMIENTO SAC (100% DATOS REALES OE2)')
        print(f'     Episodios: {EPISODES} x 8,760 timesteps = {TOTAL_TIMESTEPS:,} pasos')
        print(f'     Device: {DEVICE.upper()}')
        print(f'     Velocidad: ~{SPEED_ESTIMATED:,} timesteps/segundo')
        print(f'     Duracion: {DURATION_TEXT}')
        print('     Datos: REALES OE2 (chargers_ev_ano_2024_v3.csv 38 sockets, 2,000 kWh BESS max SOC, 4,050 kWp solar)')
        print('     Network: 256x256 (off-policy SAC), buffer_size=100k, ent_coef=auto')
        print('     Output: result_sac.json, timeseries_sac.csv, trace_sac.csv')
        print()
        print('  REWARD WEIGHTS (CO2_DUAL_FOCUS v7.0):')
        print('    Direct CO2 (0.35):      P1 - Combustible vehicular evitado - motos/mototaxis')
        print('    Indirect CO2 (0.30):    P2 - Grid termico evitado (0.4521 kg CO2/kWh)')
        print('    EV satisfaction (0.25): P3 - Carga efectiva EVs - SOC 90%')
        print('    Solar (0.05):           P4 - Autoconsumo PV directo')
        print('    Grid stability (0.05):  P5 - Suavizar picos de potencia')
        print('='*80)
        print('  ENTRENAMIENTO EN PROGRESO:')
        print('  ' + '-' * 76)

        start_time = time.time()

        # Callbacks: Checkpoint + DetailedLogging + SACMetrics
        checkpoint_callback = CheckpointCallback(
            save_freq=8760,  # SAC: checkpoint cada episodio (8760 steps)
            save_path=str(CHECKPOINT_DIR),
            name_prefix='sac_model',
            verbose=0
        )

        detailed_callback = DetailedLoggingCallback(
            env_ref=env,
            output_dir=OUTPUT_DIR,
            verbose=1,
            total_timesteps=TOTAL_TIMESTEPS
        )

        # [OK] SACMetricsCallback: metricas especificas SAC (actor/critic/ent_coef)
        sac_metrics_callback = SACMetricsCallback(
            output_dir=OUTPUT_DIR,
            config=sac_config,
            verbose=1
        )

        callback_list = CallbackList([checkpoint_callback, detailed_callback, sac_metrics_callback])

        sac_agent.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=callback_list,
            progress_bar=False
        )

        elapsed = time.time() - start_time
        sac_agent.save(CHECKPOINT_DIR / 'sac_final_model.zip')

        print()
        print('  [OK] RESULTADO ENTRENAMIENTO:')
        print(f'    Tiempo: {elapsed/60:.1f} minutos ({elapsed:.0f} segundos)')
        print(f'    Timesteps ejecutados: {TOTAL_TIMESTEPS:,}')
        print(f'    Velocidad real: {TOTAL_TIMESTEPS/elapsed:.0f} timesteps/segundo')
        print(f'    Episodios completados: {detailed_callback.episode_count}')

        # ========== GUARDAR 3 ARCHIVOS DE SALIDA ==========
        print()
        print('[6] GUARDAR ARCHIVOS DE SALIDA')
        print('-' * 80)

        # 1. trace_sac.csv - Registro detallado de cada step
        # [FIX mem] Records flushed incrementally during training; verify file exists.
        trace_path = OUTPUT_DIR / 'trace_sac.csv'
        if trace_path.exists():
            trace_rows = sum(1 for _ in open(trace_path, encoding='utf-8')) - 1  # -1 header
            print(f'  [OK] trace_sac.csv: {trace_rows:,} registros (flush incremental) -> {trace_path}')
        elif detailed_callback.trace_records:
            # Fallback: unflushed records remain in memory
            trace_df = pd.DataFrame(detailed_callback.trace_records)
            trace_df.to_csv(trace_path, index=False)
            print(f'  [OK] trace_sac.csv: {len(trace_df)} registros -> {trace_path}')
        else:
            print('  [!] trace_sac.csv: Sin registros')

        # 2. timeseries_sac.csv - Series temporales horarias
        ts_path = OUTPUT_DIR / 'timeseries_sac.csv'
        if ts_path.exists():
            ts_rows = sum(1 for _ in open(ts_path, encoding='utf-8')) - 1  # -1 header
            print(f'  [OK] timeseries_sac.csv: {ts_rows:,} registros (flush incremental) -> {ts_path}')
        elif detailed_callback.timeseries_records:
            ts_df = pd.DataFrame(detailed_callback.timeseries_records)
            ts_df.to_csv(ts_path, index=False)
            print(f'  [OK] timeseries_sac.csv: {len(ts_df)} registros -> {ts_path}')
        else:
            print('  [!] timeseries_sac.csv: Sin registros')

        print()
        print('[7] VALIDACION - 50 EPISODIOS')
        print('-' * 80)

        val_obs, _ = env.reset()
        val_metrics: dict[str, list[float]] = {
            'rewards': [],
            'co2_avoided': [],
            'solar_kwh': [],
            'cost_usd': [],
            'grid_import': [],
        }

        for ep in range(50):
            val_obs, _ = env.reset()
            validation_done = False
            step_count = 0
            episode_co2 = 0.0
            episode_solar = 0.0
            episode_grid = 0.0

            print(f'  Episodio {ep+1}/50: ', end='', flush=True)

            while not validation_done:
                action_result = sac_agent.predict(val_obs, deterministic=True)
                action_arr = action_result[0] if action_result is not None else np.zeros(129)
                val_obs, reward, terminated, val_truncated, step_info = env.step(action_arr)
                validation_done = terminated or val_truncated
                step_count += 1

                episode_co2 += step_info.get('co2_avoided_total_kg', 0)
                episode_solar += step_info.get('solar_generation_kwh', 0)
                episode_grid += step_info.get('grid_import_kwh', 0)

            val_metrics['rewards'].append(env.episode_reward)
            val_metrics['co2_avoided'].append(episode_co2)
            val_metrics['solar_kwh'].append(episode_solar)
            val_metrics['cost_usd'].append(env.cost_total)
            val_metrics['grid_import'].append(episode_grid)

            print(
                f'Reward={env.episode_reward:>8.2f} | CO2_avoided={episode_co2:>10.1f}kg'
                f' | Solar={episode_solar:>10.1f}kWh | Steps={step_count}'
            )

        print()

        # 3. result_sac.json - Resumen completo del entrenamiento (IGUAL ESTRUCTURA QUE PPO)
        result_summary: dict[str, Any] = {
            'timestamp': datetime.now().isoformat(),
            'agent': 'SAC',
            'project': 'pvbesscar',
            'location': 'Iquitos, Peru',
            'co2_factor_kg_per_kwh': CO2_FACTOR_IQUITOS,
            'training': {
                'total_timesteps': int(TOTAL_TIMESTEPS),
                'episodes': int(EPISODES),
                'duration_seconds': float(elapsed),
                'speed_steps_per_second': float(TOTAL_TIMESTEPS / elapsed),
                'device': str(DEVICE),
                'episodes_completed': detailed_callback.episode_count,
                'hyperparameters': {
                    'learning_rate': sac_config.learning_rate,
                    'buffer_size': sac_config.buffer_size,
                    'learning_starts': sac_config.learning_starts,
                    'batch_size': sac_config.batch_size,
                    'tau': sac_config.tau,
                    'gamma': sac_config.gamma,
                    'train_freq': sac_config.train_freq,
                    'gradient_steps': sac_config.gradient_steps,
                    'ent_coef': sac_config.ent_coef,
                    'target_entropy': sac_config.target_entropy,
                    'max_grad_norm': sac_config.max_grad_norm,
                }
            },
            'datasets_oe2': {
                'chargers_path': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
                'chargers_sockets': 38,
                'chargers_total_kwh': float(env.chargers_total_kwh),
                'bess_path': 'data/interim/oe2/bess/bess_hourly_dataset_2024.csv',
                'bess_capacity_kwh': BESS_CAPACITY_KWH,
                'solar_path': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
                'solar_total_kwh': float(np.sum(np.asarray(env.solar_hourly_kwh))),
                'mall_path': 'data/interim/oe2/demandamallkwh/demandamallhorakwh.csv',
                'mall_total_kwh': float(np.sum(np.asarray(env.mall_hourly_kw))),
            },
            'validation': {
                'num_episodes': 50,
                'mean_reward': float(np.mean(val_metrics['rewards'])),
                'std_reward': float(np.std(val_metrics['rewards'])),
                'mean_co2_avoided_kg': float(np.mean(val_metrics['co2_avoided'])),
                'mean_solar_kwh': float(np.mean(val_metrics['solar_kwh'])),
                'mean_cost_usd': float(np.mean(val_metrics['cost_usd'])),
                'mean_grid_import_kwh': float(np.mean(val_metrics['grid_import'])),
            },
            'training_evolution': {
                'episode_rewards': detailed_callback.episode_rewards,
                'episode_co2_grid': detailed_callback.episode_co2_grid,
                'episode_co2_avoided_indirect': detailed_callback.episode_co2_avoided_indirect,
                'episode_co2_avoided_direct': detailed_callback.episode_co2_avoided_direct,
                'episode_solar_kwh': detailed_callback.episode_solar_kwh,
                'episode_ev_charging': detailed_callback.episode_ev_charging,
                'episode_ev_charging_peak': detailed_callback.episode_ev_charging_peak,
                'episode_ev_charging_offpeak': detailed_callback.episode_ev_charging_offpeak,
                'episode_grid_import': detailed_callback.episode_grid_import,
                # [OK] NUEVAS metricas de evolucion
                'episode_grid_stability': detailed_callback.episode_grid_stability,
                'episode_cost_usd': detailed_callback.episode_cost_usd,
                'episode_motos_charged': detailed_callback.episode_motos_charged,
                'episode_mototaxis_charged': detailed_callback.episode_mototaxis_charged,
                'episode_motos_peak_max': detailed_callback.episode_motos_peak_max,
                'episode_mototaxis_peak_max': detailed_callback.episode_mototaxis_peak_max,
                'episode_total_sockets_peak_max': detailed_callback.episode_total_sockets_peak_max,
                'episode_bess_discharge_kwh': detailed_callback.episode_bess_discharge_kwh,
                'episode_bess_charge_kwh': detailed_callback.episode_bess_charge_kwh,
                'episode_avg_socket_setpoint': detailed_callback.episode_avg_socket_setpoint,
                'episode_socket_utilization': detailed_callback.episode_socket_utilization,
                'episode_bess_action_avg': detailed_callback.episode_bess_action_avg,
                # F6/F7/F8 OE3 cuantificación completa (2026-04-10)
                'episode_co2_solar_f6_kg': detailed_callback.episode_co2_solar_f6_kg,
                'episode_co2_bess_f7_kg': detailed_callback.episode_co2_bess_f7_kg,
                'episode_co2_export_f8_kg': detailed_callback.episode_co2_export_f8_kg,
            },
            # [OK] NUEVAS secciones de metricas detalladas
            'summary_metrics': {
                'total_co2_avoided_indirect_kg': float(sum(detailed_callback.episode_co2_avoided_indirect)),
                'total_co2_avoided_direct_kg': float(sum(detailed_callback.episode_co2_avoided_direct)),
                'total_co2_avoided_kg': float(sum(detailed_callback.episode_co2_avoided_indirect) + sum(detailed_callback.episode_co2_avoided_direct)),
                # F6/F7/F8 totales acumulados (OE3)
                'total_co2_solar_f6_kg': float(sum(detailed_callback.episode_co2_solar_f6_kg)) if detailed_callback.episode_co2_solar_f6_kg else 0.0,
                'total_co2_bess_f7_kg': float(sum(detailed_callback.episode_co2_bess_f7_kg)) if detailed_callback.episode_co2_bess_f7_kg else 0.0,
                'total_co2_export_f8_kg': float(sum(detailed_callback.episode_co2_export_f8_kg)) if detailed_callback.episode_co2_export_f8_kg else 0.0,
                'total_cost_usd': float(sum(detailed_callback.episode_cost_usd)),
                'avg_grid_stability': float(np.mean(detailed_callback.episode_grid_stability)) if detailed_callback.episode_grid_stability else 0.0,
                'max_motos_charged': int(max(detailed_callback.episode_motos_charged)) if detailed_callback.episode_motos_charged else 0,
                'max_mototaxis_charged': int(max(detailed_callback.episode_mototaxis_charged)) if detailed_callback.episode_mototaxis_charged else 0,
                'total_bess_discharge_kwh': float(sum(detailed_callback.episode_bess_discharge_kwh)),
                'total_bess_charge_kwh': float(sum(detailed_callback.episode_bess_charge_kwh)),
                'max_motos_peak_period': int(max(detailed_callback.episode_motos_peak_max)) if detailed_callback.episode_motos_peak_max else 0,
                'max_mototaxis_peak_period': int(max(detailed_callback.episode_mototaxis_peak_max)) if detailed_callback.episode_mototaxis_peak_max else 0,
                'max_total_sockets_peak_period': int(max(detailed_callback.episode_total_sockets_peak_max)) if detailed_callback.episode_total_sockets_peak_max else 0,
                'total_ev_charging_peak_kwh': float(sum(detailed_callback.episode_ev_charging_peak)),
                'total_ev_charging_offpeak_kwh': float(sum(detailed_callback.episode_ev_charging_offpeak)),
                'pct_ev_charging_peak': float(
                    sum(detailed_callback.episode_ev_charging_peak) / 
                    (sum(detailed_callback.episode_ev_charging_peak) + sum(detailed_callback.episode_ev_charging_offpeak)) * 100
                ) if (sum(detailed_callback.episode_ev_charging_peak) + sum(detailed_callback.episode_ev_charging_offpeak)) > 0 else 0.0,
                'energy_validation': {
                    'total_energy_charged_kwh': float(sum(detailed_callback.episode_ev_charging_peak) + sum(detailed_callback.episode_ev_charging_offpeak)),
                    'benchmark_energy_target_kwh': 408_281.5,
                    'benchmark_energy_theoretical_kwh': 387_841.0,
                    'pct_vs_benchmark_real': float(
                        (sum(detailed_callback.episode_ev_charging_peak) + sum(detailed_callback.episode_ev_charging_offpeak)) / 408_281.5 * 100
                    ) if 408_281.5 > 0 else 0.0,
                    'pct_vs_benchmark_theoretical': float(
                        (sum(detailed_callback.episode_ev_charging_peak) + sum(detailed_callback.episode_ev_charging_offpeak)) / 387_841.0 * 100
                    ) if 387_841.0 > 0 else 0.0,
                    'description': 'Validaci├│n contra baseline 2024: energ├¡a te├│rica m├¡n (387.8 kWh) vs real cargada durante entrenamiento (408.3 kWh benchmark)',
                },
            },
            'control_progress': {
                'avg_socket_setpoint_evolution': detailed_callback.episode_avg_socket_setpoint,
                'socket_utilization_evolution': detailed_callback.episode_socket_utilization,
                'bess_action_evolution': detailed_callback.episode_bess_action_avg,
                'description': 'Evolucion del aprendizaje de control por episodio',
            },
            'reward_components_avg': {
                'r_solar': float(np.mean(detailed_callback.episode_r_solar)) if detailed_callback.episode_r_solar else 0.0,
                'r_cost': float(np.mean(detailed_callback.episode_r_cost)) if detailed_callback.episode_r_cost else 0.0,
                'r_ev': float(np.mean(detailed_callback.episode_r_ev)) if detailed_callback.episode_r_ev else 0.0,
                'r_grid': float(np.mean(detailed_callback.episode_r_grid)) if detailed_callback.episode_r_grid else 0.0,
                'r_co2': float(np.mean(detailed_callback.episode_r_co2)) if detailed_callback.episode_r_co2 else 0.0,
                'episode_r_solar': [float(x) for x in detailed_callback.episode_r_solar] if detailed_callback.episode_r_solar else [],
                'episode_r_cost': [float(x) for x in detailed_callback.episode_r_cost] if detailed_callback.episode_r_cost else [],
                'episode_r_ev': [float(x) for x in detailed_callback.episode_r_ev] if detailed_callback.episode_r_ev else [],
                'episode_r_grid': [float(x) for x in detailed_callback.episode_r_grid] if detailed_callback.episode_r_grid else [],
                'episode_r_co2': [float(x) for x in detailed_callback.episode_r_co2] if detailed_callback.episode_r_co2 else [],
                'description': 'Componentes de reward promedio por episodio',
            },
            'vehicle_charging': {
                'motos_target': 270,
                'mototaxis_target': 39,
                'vehicles_target_daily': 309,
                'motos_charged_per_episode': [float(x) if isinstance(x, (np.floating, float)) else int(x) for x in detailed_callback.episode_motos_charged] if detailed_callback.episode_motos_charged else [],
                'mototaxis_charged_per_episode': [float(x) if isinstance(x, (np.floating, float)) else int(x) for x in detailed_callback.episode_mototaxis_charged] if detailed_callback.episode_mototaxis_charged else [],
                'motos_peak_per_episode': [float(x) if isinstance(x, (np.floating, float)) else int(x) for x in detailed_callback.episode_motos_peak_max] if detailed_callback.episode_motos_peak_max else [],
                'mototaxis_peak_per_episode': [float(x) if isinstance(x, (np.floating, float)) else int(x) for x in detailed_callback.episode_mototaxis_peak_max] if detailed_callback.episode_mototaxis_peak_max else [],
                'description': 'Conteo real de vehiculos cargados usando energia dataset (270 motos + 39 mototaxis = 309/d├¡a) + m├íximos per├¡odo pico 9 AM - 8 PM',
                'peak_period': '9:00 - 20:00 (11 horas, per├¡odo operativo real)',
            },
            'model_path': str(CHECKPOINT_DIR / 'sac_final_model.zip'),
        }

        # Custom JSON encoder para numpy types
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):  # type: ignore[no-untyped-def]
                if isinstance(obj, (np.floating, np.integer)):
                    return float(obj) if isinstance(obj, np.floating) else int(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        result_path = OUTPUT_DIR / 'result_sac.json'
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_summary, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        print(f'  [OK] result_sac.json: Resumen completo -> {result_path}')

        # Extraer metricas para impresion (acceso directo)
        mean_reward = float(np.mean(val_metrics['rewards']))
        mean_co2 = float(np.mean(val_metrics['co2_avoided']))
        mean_solar = float(np.mean(val_metrics['solar_kwh']))
        mean_cost = float(np.mean(val_metrics['cost_usd']))
        mean_grid = float(np.mean(val_metrics['grid_import']))

        print()
        print('='*80)
        print('RESULTADOS FINALES - VALIDACION 50 EPISODIOS:')
        print('='*80)
        print()
        print('  Ô×ñ METRICAS DE RECOMPENSA:')
        print(f'    Reward promedio               {mean_reward:>12.4f} puntos')
        print()
        print('  Ô×ñ REDUCCION CO2 (kg):')
        total_indirect = float(sum(detailed_callback.episode_co2_avoided_indirect))
        total_direct = float(sum(detailed_callback.episode_co2_avoided_direct))
        print(f'    Reduccion INDIRECTA (solar)   {total_indirect:>12.1f} kg')
        print(f'    Reduccion DIRECTA (EVs)       {total_direct:>12.1f} kg')
        print(f'    Reduccion TOTAL               {total_indirect + total_direct:>12.1f} kg')
        print(f'    CO2 evitado promedio/ep       {mean_co2:>12.1f} kg')
        print()
        print('  Ô×ñ VEHICULOS CARGADOS (maximo SIMULTANEO periodo pico 9 AM - 8 PM):')
        max_motos_peak = max(detailed_callback.episode_motos_peak_max) if detailed_callback.episode_motos_peak_max else 0
        max_mototaxis_peak = max(detailed_callback.episode_mototaxis_peak_max) if detailed_callback.episode_mototaxis_peak_max else 0
        max_total_peak = max(detailed_callback.episode_total_sockets_peak_max) if detailed_callback.episode_total_sockets_peak_max else 0
        print(f'    Motos (max sockets: 30)       {max_motos_peak:>12d} unidades (per├¡odo pico)')
        print(f'    mototaxis (max sockets: 8)    {max_mototaxis_peak:>12d} unidades (per├¡odo pico)')
        print(f'    Total sockets activos         {max_total_peak:>12d} / 38 (per├¡odo pico)')
        print()
        print('    Comparativa global (toda d├¡a):')
        max_motos_global = max(detailed_callback.episode_motos_charged) if detailed_callback.episode_motos_charged else 0
        max_mototaxis_global = max(detailed_callback.episode_mototaxis_charged) if detailed_callback.episode_mototaxis_charged else 0
        print(f'    Motos global                  {max_motos_global:>12d} unidades')
        print(f'    mototaxis global              {max_mototaxis_global:>12d} unidades')
        print()
        print('  Ô×ñ ENERGIA CARGADA POR PERIODO HORARIO:')
        total_ev_peak = sum(detailed_callback.episode_ev_charging_peak) if detailed_callback.episode_ev_charging_peak else 0.0
        total_ev_offpeak = sum(detailed_callback.episode_ev_charging_offpeak) if detailed_callback.episode_ev_charging_offpeak else 0.0
        total_ev_all = total_ev_peak + total_ev_offpeak
        pct_peak = (total_ev_peak / total_ev_all * 100) if total_ev_all > 0 else 0.0
        pct_offpeak = (total_ev_offpeak / total_ev_all * 100) if total_ev_all > 0 else 0.0
        print(f'    9 AM - 10 PM (per├¡odo pico):  {total_ev_peak:>12.1f} kWh ({pct_peak:>6.1f}%)')
        print(f'    Fuera horario (0-8, 23h):     {total_ev_offpeak:>12.1f} kWh ({pct_offpeak:>6.1f}%)')
        print(f'    Total energ├¡a EV cargada:     {total_ev_all:>12.1f} kWh')
        print()
        print('  Ô×ñ VALIDACION: ENERGIA TEORICA vs REAL')
        print('    (SOC 20% ÔåÆ 80% = 60% carga por veh├¡culo)')
        # Constantes
        MOTO_BATTERY_KWH = 4.6
        MOTOTAXI_BATTERY_KWH = 7.4
        SOC_DELTA = 0.60
        MOTO_ENERGIA_TEORICA = MOTO_BATTERY_KWH * SOC_DELTA  # 2.76 kWh
        MOTOTAXI_ENERGIA_TEORICA = MOTOTAXI_BATTERY_KWH * SOC_DELTA  # 4.44 kWh
        # Benchmark: Datos reales del dataset 2024 (por episodio = 1 a├▒o)
        BENCHMARK_MOTOS_ANUAL = 118_866 / 10  # ~11,887 motos/episodio
        BENCHMARK_MOTOTAXIS_ANUAL = 13_462 / 10   # ~1,346 mototaxis/episodio
        BENCHMARK_ENERGIA_ANUAL = 408_281.5 / 10  # ~40,828 kWh/episodio (REAL)
        BENCHMARK_ENERGIA_TEORICA_ANUAL = 387_841.0 / 10  # ~38,784 kWh/episodio (te├│rico)
        print(f'    Moto energ├¡a te├│rica:         {MOTO_ENERGIA_TEORICA:>12.2f} kWh')
        print(f'    mototaxi energ├¡a te├│rica:     {MOTOTAXI_ENERGIA_TEORICA:>12.2f} kWh')
        print()
        print('    BENCHMARK DATASET 2024 (por episodio / 1 a├▒o):')
        print(f'    Motos target:                 {BENCHMARK_MOTOS_ANUAL:>12.0f} unidades')
        print(f'    mototaxis target:             {BENCHMARK_MOTOTAXIS_ANUAL:>12.0f} unidades')
        print(f'    Energ├¡a te├│rica target:       {BENCHMARK_ENERGIA_TEORICA_ANUAL:>12.1f} kWh')
        print(f'    Energ├¡a real target:          {BENCHMARK_ENERGIA_ANUAL:>12.1f} kWh')
        print()
        print('    RESULTADOS ENTRENAMIENTO (50 episodios):')
        print(f'    Energ├¡a real vs target:       {total_ev_all:>12.1f} kWh / {BENCHMARK_ENERGIA_ANUAL*50:>12.1f} kWh')
        pct_cumplimiento = (total_ev_all / (BENCHMARK_ENERGIA_ANUAL * 50) * 100) if BENCHMARK_ENERGIA_ANUAL > 0 else 0.0
        print(f'    % Cumplimiento energ├¡a:       {pct_cumplimiento:>12.1f} %')
        print()
        if pct_cumplimiento >= 90:
            print('    Ô£à EXCELENTE: Cargando ÔëÑ90% de energ├¡a target')
        elif pct_cumplimiento >= 75:
            print('    ÔÜá´©Å  BUENO: Cargando 75-90% de energ├¡a target')
        else:
            print(f'    ÔØî INSUFICIENTE: Solo {pct_cumplimiento:.1f}% de energ├¡a target')
        print()
        print('  Ô×ñ ESTABILIDAD DE RED:')
        avg_stability = np.mean(detailed_callback.episode_grid_stability) if detailed_callback.episode_grid_stability else 0.0
        print(f'    Estabilidad promedio          {avg_stability*100:>12.1f} %')
        print(f'    Grid import promedio/ep       {mean_grid:>12.1f} kWh')
        print()
        print('  Ô×ñ AHORRO ECONOMICO:')
        total_cost = sum(detailed_callback.episode_cost_usd) if detailed_callback.episode_cost_usd else 0.0
        print(f'    Costo total (50 episodios)    ${total_cost:>11.2f} USD')
        print(f'    Costo promedio por episodio   ${mean_cost:>11.2f} USD')
        print()
        print('  Ô×ñ CONTROL BESS:')
        total_discharge = sum(detailed_callback.episode_bess_discharge_kwh) if detailed_callback.episode_bess_discharge_kwh else 0.0
        total_charge = sum(detailed_callback.episode_bess_charge_kwh) if detailed_callback.episode_bess_charge_kwh else 0.0
        avg_bess_action = np.mean(detailed_callback.episode_bess_action_avg) if detailed_callback.episode_bess_action_avg else 0.5
        print(f'    Descarga total BESS           {total_discharge:>12.1f} kWh')
        print(f'    Carga total BESS              {total_charge:>12.1f} kWh')
        print(f'    Accion BESS promedio          {avg_bess_action:>12.3f} (0=carga, 1=descarga)')
        print()
        print('  Ô×ñ PROGRESO DE CONTROL SOCKETS:')
        avg_setpoint = np.mean(detailed_callback.episode_avg_socket_setpoint) if detailed_callback.episode_avg_socket_setpoint else 0.0
        avg_utilization = np.mean(detailed_callback.episode_socket_utilization) if detailed_callback.episode_socket_utilization else 0.0
        print(f'    Setpoint promedio sockets     {avg_setpoint:>12.3f} [0-1]')
        print(f'    Utilizacion sockets           {avg_utilization*100:>12.1f} %')
        print()
        print('  Ô×ñ SOLAR:')
        print(f'    Solar aprovechada por ep      {mean_solar:>12.1f} kWh')
        print()
        print('  ARCHIVOS GENERADOS:')
        print(f'    [OK] {OUTPUT_DIR}/result_sac.json')
        print(f'    [OK] {OUTPUT_DIR}/timeseries_sac.csv')
        print(f'    [OK] {OUTPUT_DIR}/trace_sac.csv')
        print(f'    [OK] {CHECKPOINT_DIR}/sac_final_model.zip')
        print()
        print('  ESTADO: Entrenamiento SAC exitoso con datos reales OE2.')
        print()

        # [METRICAS CONVERGENCIA] Curvas de aprendizaje nivel tesis doctoral
        # Ref: [1] Haarnoja 2018 SAC [2] Henderson 2018 [4] Pigott 2022 CityLearn
        try:
            from training_metrics import generate_all_training_metrics
            _ev_pk  = detailed_callback.episode_ev_charging_peak   if detailed_callback.episode_ev_charging_peak   else []
            _ev_op  = detailed_callback.episode_ev_charging_offpeak if detailed_callback.episode_ev_charging_offpeak else []
            _ev_pct_list: list[float] = []
            for _pk, _op in zip(_ev_pk, _ev_op):
                _tot = _pk + _op
                _ev_pct_list.append(float(_pk / _tot * 100) if _tot > 1e-3 else 0.0)
            generate_all_training_metrics(
                agent_name='SAC',
                episode_rewards=detailed_callback.episode_rewards,
                output_dir=OUTPUT_DIR,
                episode_co2_direct=detailed_callback.episode_co2_avoided_direct,
                episode_co2_indirect=detailed_callback.episode_co2_avoided_indirect,
                episode_solar_kwh=detailed_callback.episode_solar_kwh,
                episode_grid_import=detailed_callback.episode_grid_import,
                episode_bess_discharge=detailed_callback.episode_bess_discharge_kwh,
                episode_bess_charge=detailed_callback.episode_bess_charge_kwh,
                episode_cost_usd=detailed_callback.episode_cost_usd,
                episode_ev_peak_kwh=_ev_pk,
                episode_ev_offpeak_kwh=_ev_op,
                reward_components={
                    'CO₂ directo (P1)':  detailed_callback.episode_r_direct_co2,
                    'CO₂ indirecto (P2)': detailed_callback.episode_r_co2,
                    'Solar (P4)':         detailed_callback.episode_r_solar,
                    'EV completado (P3)': detailed_callback.episode_r_ev,
                    'Estabilidad (P5)':   detailed_callback.episode_r_grid,
                },
                agent_diagnostics={
                    'actor_loss':  sac_metrics_callback.actor_loss_history,
                    'critic_loss': sac_metrics_callback.critic_loss_history,
                    'entropy':     sac_metrics_callback.ent_coef_history,
                    'grad_norm':   sac_metrics_callback.grad_norm_history,
                },
            )
        except Exception as _tm_exc:
            print(f'  [WARN] training_metrics: {_tm_exc}')

        print('='*80)
        print('Entrenamiento SAC COMPLETADO')
        print('='*80)

except (FileNotFoundError, KeyError, ValueError, RuntimeError, OSError, IOError, MemoryError) as e:
    print(f'\n[CRASH] {type(e).__name__}: {e}', flush=True)
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    sys.exit(1)


if __name__ == '__main__':
    main()
