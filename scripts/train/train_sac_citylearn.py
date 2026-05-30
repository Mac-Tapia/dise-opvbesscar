#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
train_sac_citylearn.py -- SAC SB3 sobre entorno Iquitos EV (PyTorch)
=======================================================================
Entrena SAC (Soft Actor-Critic) con stable-baselines3 en el entorno
IquitosEVChargingWrapper(CityLearnEnv) para control real de cargadores.

ESPACIO DE ACCIÓN (3D):
  action[0]  bess_action       ∈ [-1,+1]  -- BESS dispatch
  action[1]  ev_motos_frac     ∈ [0, 1]   -- fracción carga motos (15 carg x 30 sockets)
  action[2]  ev_mototaxis_frac ∈ [0, 1]   -- fracción carga mototaxis (4 carg x 8 sockets)

OBJETIVO OE3: reducción cuantificable de CO2 en Iquitos mediante
gestión inteligente de recarga de motos y mototaxis eléctricas.
REWARD: CO2_DUAL_FOCUS v7.2 (indirect 45% + ev_complete 25% + direct 10%
        + solar 5% + stability 5% + cost 10% OSINERGMIN)

Agente: stable_baselines3.SAC (off-policy, buffer replay, mejor para
        recompensas asimétricas -- óptimo para este problema)
Entorno: IquitosEVChargingWrapper -> obs_dim=18, action_dim=3

Uso:
    python scripts/train/train_sac_citylearn.py
    python scripts/train/train_sac_citylearn.py --timesteps 8760  # 1 año
    python scripts/train/train_sac_citylearn.py --rebuild-schema  # regenerar datos

Checkpoints: checkpoints/SAC_CityLearn/sac_<steps>_steps.zip
=======================================================================
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

# PROJECT ROOT en sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Forzar UTF-8 en stdout/stderr para que Tee-Object y redirección de PowerShell
# no garble los caracteres españoles (ñ) y especiales (CO2, ->).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# CUDA lazy loading
os.environ.setdefault("CUDA_MODULE_LOADING", "LAZY")
import signal as _signal
_orig = _signal.getsignal(_signal.SIGINT)
_signal.signal(_signal.SIGINT, _signal.SIG_IGN)
try:
    import torch
    # Inicializar CUDA dentro del bloque SIGINT-bloqueado:
    # torch.cuda.is_available() carga libcuda.so/nvml (~2-3s) y falla con
    # KeyboardInterrupt si hay señal pendiente al salir del try anterior.
    _CUDA_AVAILABLE: bool = torch.cuda.is_available()
finally:
    _signal.signal(_signal.SIGINT, _orig)

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.figure as _mpl_fig
from matplotlib import gridspec

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# SB3
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import (
    BaseCallback,
    CallbackList,
    CheckpointCallback,
)
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

# Módulo local CityLearn v2 con wrapper EV
from src.citylearnv2.env_factory import create_iquitos_env_for_sb3
from src.citylearnv2.schema_builder import build_citylearn_schema
from src.agents.training_validation import validate_agent_config

# UTF-8 fix (Windows)
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
except (AttributeError, TypeError, RuntimeError):
    pass

# ===================== CONFIGURACIÓN =====================

TOTAL_TIMESTEPS: int = 8_760 * 50    # 50 episodios x 8760 h/año = 438,000 steps
CHECKPOINT_EVERY_STEPS: int = 8_760  # 1 episodio completo por checkpoint
CHECKPOINT_DIR: Path = _PROJECT_ROOT / "checkpoints" / "SAC_CityLearn"
LOG_DIR: Path = _PROJECT_ROOT / "logs" / "training" / "sac_citylearn"
RESULTS_DIR: Path = _PROJECT_ROOT / "outputs" / "sac_training"
TENSORBOARD_DIR: Path = _PROJECT_ROOT / "logs" / "tensorboard" / "sac_citylearn"

_DEVICE = "cuda" if _CUDA_AVAILABLE else "cpu"

# GPU optimizations (igual que train_sac.py v7.2 -- RTX 4060/Ampere)
if _DEVICE == "cuda":
    _gpu_name = torch.cuda.get_device_name(0)
    _gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    _cuda_ver: str | None = getattr(torch.version, "cuda", None)  # type: ignore[attr-defined]
    # TF32 acelera matmul ~5-10x en Ampere/Ada sin pérdida apreciable de precisión
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.benchmark = True     # auto-tune kernels al primer forward
    torch.backends.cudnn.deterministic = False  # no forzar determinismo = más rápido
    print(f"GPU: {_gpu_name}")
    print(f"   VRAM: {_gpu_mem_gb:.1f} GB | CUDA: {_cuda_ver}")
    print("   [GPU MAX] TF32 ON, cuDNN benchmark ON")
else:
    print("CPU mode -- GPU no disponible")


class AdamWithGradClip(torch.optim.Adam):
    """Adam con gradient clipping integrado (SAC no tiene max_grad_norm nativo).

    SB3 SAC no soporta max_grad_norm. Esta clase lo implementa dentro del
    .step(), compatible con el ciclo interno de SB3.
    Refs: Haarnoja 2018; torch.nn.utils.clip_grad_norm_ documentation.
    """

    def __init__(self, params: Any, lr: float = 3e-4,
                 max_grad_norm: float = 10.0, **kwargs: Any) -> None:
        super().__init__(params, lr=lr, **kwargs)
        self.max_grad_norm = max_grad_norm

    def step(self, closure: Any = None) -> Any:  # type: ignore[override]
        params_with_grad = [
            p for group in self.param_groups for p in group['params']
            if p.grad is not None
        ]
        if params_with_grad:
            torch.nn.utils.clip_grad_norm_(params_with_grad, self.max_grad_norm)
        return super().step(closure)


class PVBESSCarSAC(SAC):
    """SAC con corrección de higiene de gradientes y prevención de alpha collapse.

    FIX 1 -- Alpha collapse -> NaN Q-values -> RuntimeError crash al ~170k steps:
        Cuando ent_coef -> 0, el td_target diverge -> Q-values NaN -> crash.
        Se clampea log_ent_coef a min=-9.21 (alpha_min = exp(-9.21) ~ 1e-4).
        Refs: Haarnoja 2019 auto-tuning; SB3 issue #1024.

    FIX 2 -- Gradient hygiene (actor_loss.backward() acumula grads en el critic):
        SB3 SAC llama actor_loss.backward() mientras el critic optimizer aún
        tiene grads del paso anterior. Esto infla grad_norm de ~14 a 87-166.
        Se zera el optimizer del critic DESPUÉS de train() del padre.
        Refs: PyTorch docs (zero_grad); SB3 SAC train() source.
    """

    def train(self, gradient_steps: int, batch_size: int = 64) -> None:
        super().train(gradient_steps, batch_size)
        # FIX 1: alpha collapse -> floor en alpha = 1e-4 (log_alpha = -9.21)
        if hasattr(self, 'log_ent_coef') and self.log_ent_coef is not None:
            with torch.no_grad():
                self.log_ent_coef.data.clamp_(min=-9.21)
        # FIX 2: gradient hygiene -- zerar grads del critic acumulados por actor backprop
        if hasattr(self, 'critic') and self.critic is not None:
            if hasattr(self.critic, 'optimizer') and self.critic.optimizer is not None:
                self.critic.optimizer.zero_grad()


# Hiperparámetros SAC optimizados v8.0 (config sac_config.yaml)
# Refs: Haarnoja et al 2018, Raffin 2022, Engstrom 2020, Andrychowicz 2020
SAC_HYPERPARAMS: dict[str, Any] = {
    "policy": "MlpPolicy",
    # [FIX v1] 3e-4 → 1e-4: grad_norm explosiva 132.93 > 10; Engstrom 2020 recomienda
    # 1e-4 para alta dimension (39D obs). Para 3D accion + 18D obs: 1e-4 optimo.
    "learning_rate": 5e-5,
    # [FIX] 200k → 100k: buffer de 1M excesivo para 438k steps totales;
    # 100k mantiene ~11 episodios completos (8760 steps). Raffin 2022: 100k suficiente.
    "buffer_size": 100_000,
    # Warmup de un año completo para que el replay buffer vea estacionalidad,
    # perfiles EV estocásticos y operación PV-BESS antes de updates fuertes.
    "learning_starts": 8_760,
    "batch_size": 256,
    "tau": 0.005,
    "gamma": 0.99,
    "train_freq": 1,
    "gradient_steps": 1,
    "ent_coef": "auto",
    # [FIX v2] "auto" → -3.0: wrapper expone 3D al agente (bess, motos_frac, mototaxis_frac)
    # Haarnoja 2018 Sec.5: H* = -dim(A) como heuristica. "auto" → -39.0 causaba
    # alpha→0 y policy determinista prematura (alpha collapse).
    "target_entropy": -3.0,
    "policy_kwargs": {
        # [FIX] [256,256,128] → [256,256]: arquitectura estandar SAC (Haarnoja 2018).
        # Para obs 18D + 3D accion, [256,256] suficientemente expresivo sin sobreajuste.
        "net_arch": [256, 256],
        "optimizer_class": AdamWithGradClip,
        # [FIX v3] 10.0 → 5.0: conservador vs sin clipping. Engstrom 2020: gradient
        # clipping impacta fundamentalmente en alta dimension.
        "optimizer_kwargs": {"max_grad_norm": 5.0},
    },
    "verbose": 1,
    "device": _DEVICE,
}

# ===================== LOGGING =====================

LOG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(_fmt)

_file_handler = logging.FileHandler(LOG_DIR / f"sac_citylearn_{_ts}.log", encoding="utf-8")
_file_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_stream_handler, _file_handler])
log = logging.getLogger(__name__)


# ===================== CALLBACKS =====================


class EVMetricsCallback(BaseCallback):
    """Callback que registra métricas de EV y CO2 durante el entrenamiento.

    Implementa las 3 Fórmulas OE3 + F6/F7/F8 (solar + BESS):

    FÓRMULA 1 -- BASELINE (sin solar, sin BESS, sin agente RL):
        CO2_base = EV_motosx0.87 + EV_mototaxisx0.54 + Mallx0.4521

    FÓRMULA 2 -- CONTROL INTELIGENTE (con solar+BESS+agente RL):
        CO2_ctrl = grid_import x 0.4521  (solo importación residual)

    FÓRMULA 3 -- REDUCCIÓN NETA OE3:
        CO2_directa  = EV_cargadosx0.87 + EV_taxi_cargadosx0.54
        CO2_indirecta = Fórmula1 - Fórmula2
        CO2_total    = directa + indirecta

    F6 (solar, por fase dispatcher):
        F6a: solar -> EVs  |  F6b: solar -> Mall
        F6c: solar -> BESS |  F6d: solar -> export (=F8)

    F7: BESS descarga -> desplaza red diesel (kWh x 0.4521)
    """

    def __init__(self, log_freq: int = 8760, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.log_freq = log_freq
        # -- Acumuladores EV ----------------------------------------------
        self._ep_ev_motos_kwh: float = 0.0
        self._ep_ev_mototaxis_kwh: float = 0.0
        self._ep_ev_motos_demand_kwh: float = 0.0
        self._ep_ev_mototaxis_demand_kwh: float = 0.0
        self._ep_debt_violations: int = 0
        self._ep_motos_cargadas: float = 0.0      # vehículos (sum motos_cargadas_hora)
        self._ep_mototaxis_cargadas: float = 0.0  # vehículos (sum mototaxis_cargadas_hora)
        # -- Acumuladores fuentes de energía → cargadores EV (dispatch real) --
        self._ep_dispatch_pv_to_ev_kwh: float = 0.0    # PV directo → cargadores
        self._ep_dispatch_bess_to_ev_kwh: float = 0.0  # BESS → cargadores
        self._ep_dispatch_grid_to_ev_kwh: float = 0.0  # Red → cargadores
        # -- Acumuladores balance energético -------------------------------
        self._ep_solar_kwh: float = 0.0
        self._ep_bess_discharge_kwh: float = 0.0
        self._ep_bess_charge_kwh: float = 0.0
        self._ep_grid_import_kwh: float = 0.0
        self._ep_mall_kwh: float = 0.0
        # -- Acumuladores F6 (solar por fase) ------------------------------
        self._ep_co2_f6a_kg: float = 0.0   # F6a: solar -> EVs
        self._ep_co2_f6b_kg: float = 0.0   # F6b: solar -> Mall
        self._ep_co2_f6c_kg: float = 0.0   # F6c: solar -> BESS
        self._ep_co2_f6d_kg: float = 0.0   # F6d=F8: solar -> export
        self._ep_co2_f6_total_kg: float = 0.0
        # -- Acumuladores F7 (BESS descarga) ------------------------------
        self._ep_co2_f7_kg: float = 0.0
        # -- Acumuladores 3 fórmulas OE3 + F0 sin proyecto ----------------
        self._ep_co2_baseline_kg: float = 0.0
        self._ep_co2_control_kg: float = 0.0
        self._ep_co2_directa_kg: float = 0.0
        self._ep_co2_indirecta_kg: float = 0.0
        self._ep_co2_neta_kg: float = 0.0
        self._ep_co2_sinproyecto_kg: float = 0.0
        self._ep_co2_sinproyecto_mall_kg: float = 0.0
        self._ep_co2_sinproyecto_combustion_kg: float = 0.0
        # -- Historiales por episodio (para gráficas) ----------------------
        self._episodes: list[int] = []
        self._hist_ev_motos_kwh: list[float] = []
        self._hist_ev_mototaxis_kwh: list[float] = []
        self._hist_ev_motos_demand_kwh: list[float] = []
        self._hist_ev_mototaxis_demand_kwh: list[float] = []
        self._hist_debt_violations: list[float] = []
        self._hist_solar_kwh: list[float] = []
        self._hist_bess_discharge_kwh: list[float] = []
        self._hist_bess_charge_kwh: list[float] = []
        self._hist_grid_import_kwh: list[float] = []
        self._hist_mall_kwh: list[float] = []
        self._hist_co2_f6a_kg: list[float] = []
        self._hist_co2_f6b_kg: list[float] = []
        self._hist_co2_f6c_kg: list[float] = []
        self._hist_co2_f6d_kg: list[float] = []
        self._hist_co2_f7_kg: list[float] = []
        self._hist_co2_baseline_kg: list[float] = []
        self._hist_co2_control_kg: list[float] = []
        self._hist_co2_directa_kg: list[float] = []
        self._hist_co2_indirecta_kg: list[float] = []
        self._hist_co2_neta_kg: list[float] = []
        self._hist_reduccion_pct: list[float] = []
        self._hist_co2_sinproyecto_kg: list[float] = []
        # -- KPI tracking (ventana 24 pasos = 1 día) -----------------------
        self._kpi_steps_history: list[int] = []
        self._elec_consumption_history: list[float] = []
        self._elec_cost_history: list[float] = []
        self._carbon_emissions_history: list[float] = []
        self._ramping_history: list[float] = []
        self._avg_daily_peak_history: list[float] = []
        self._one_minus_lf_history: list[float] = []
        self._kpi_win_grid_imports: list[float] = []
        self._kpi_win_costs: list[float] = []
        self._kpi_win_emissions: list[float] = []
        self._kpi_win_loads: list[float] = []
        self._kpi_prev_load: float = 0.0
        self._kpi_ramping_sum: float = 0.0
        self._kpi_ramping_count: int = 0
        self._kpi_window_size: int = 24
        self.output_dir: Path = RESULTS_DIR
        # -- Trace/timeseries step-level (sincronizado con train_sac.py) --
        self.trace_records: list[dict[str, Any]] = []
        self.timeseries_records: list[dict[str, Any]] = []
        self._step_in_ep: int = 0
        self._ep_count: int = 0

    def _reset_ep(self) -> None:
        self._ep_ev_motos_kwh = 0.0
        self._ep_ev_mototaxis_kwh = 0.0
        self._ep_ev_motos_demand_kwh = 0.0
        self._ep_ev_mototaxis_demand_kwh = 0.0
        self._ep_debt_violations = 0
        self._ep_motos_cargadas = 0.0
        self._ep_mototaxis_cargadas = 0.0
        self._ep_dispatch_pv_to_ev_kwh = 0.0
        self._ep_dispatch_bess_to_ev_kwh = 0.0
        self._ep_dispatch_grid_to_ev_kwh = 0.0
        self._ep_solar_kwh = 0.0
        self._ep_bess_discharge_kwh = 0.0
        self._ep_bess_charge_kwh = 0.0
        self._ep_grid_import_kwh = 0.0
        self._ep_mall_kwh = 0.0
        self._ep_co2_f6a_kg = 0.0
        self._ep_co2_f6b_kg = 0.0
        self._ep_co2_f6c_kg = 0.0
        self._ep_co2_f6d_kg = 0.0
        self._ep_co2_f6_total_kg = 0.0
        self._ep_co2_f7_kg = 0.0
        self._ep_co2_baseline_kg = 0.0
        self._ep_co2_control_kg = 0.0
        self._ep_co2_directa_kg = 0.0
        self._ep_co2_indirecta_kg = 0.0
        self._ep_co2_neta_kg = 0.0
        self._ep_co2_sinproyecto_kg = 0.0
        self._ep_co2_sinproyecto_mall_kg = 0.0
        self._ep_co2_sinproyecto_combustion_kg = 0.0

    def _on_step(self) -> bool:
        # Leer info del entorno sobre dispatch EV + balance energético + CO2
        if self.locals.get("infos"):
            for info in self.locals["infos"]:
                # EV
                self._ep_ev_motos_kwh            += info.get("ev_motos_actual_kwh", 0.0)
                self._ep_ev_mototaxis_kwh        += info.get("ev_mototaxis_actual_kwh", 0.0)
                self._ep_ev_motos_demand_kwh     += info.get("ev_motos_demand_kwh", 0.0)
                self._ep_ev_mototaxis_demand_kwh += info.get("ev_mototaxis_demand_kwh", 0.0)
                if info.get("penalty_debt_frac", 0.0) > 0.1:
                    self._ep_debt_violations += 1
                self._ep_motos_cargadas     += info.get("chr_motos_hora", 0.0)
                self._ep_mototaxis_cargadas += info.get("chr_mototaxis_hora", 0.0)
                # Fuentes de energía → cargadores EV (dispatch real del agente)
                self._ep_dispatch_pv_to_ev_kwh   += info.get("dispatch_pv_to_ev_kwh", 0.0)
                self._ep_dispatch_bess_to_ev_kwh += info.get("dispatch_bess_to_ev_kwh", 0.0)
                self._ep_dispatch_grid_to_ev_kwh += info.get("dispatch_grid_to_ev_kwh", 0.0)
                # Balance energético
                self._ep_solar_kwh         += info.get("solar_generation_kwh", 0.0)
                self._ep_bess_discharge_kwh += info.get("bess_discharge_kwh", 0.0)
                self._ep_bess_charge_kwh    += info.get("bess_charge_kwh", 0.0)
                self._ep_grid_import_kwh    += info.get("grid_import_kwh", 0.0)
                self._ep_mall_kwh           += info.get("mall_demand_kwh", 0.0)
                # F6 (solar por fase)
                self._ep_co2_f6a_kg     += info.get("co2_solar_ev_f6a_kg", 0.0)
                self._ep_co2_f6b_kg     += info.get("co2_solar_mall_f6b_kg", 0.0)
                self._ep_co2_f6c_kg     += info.get("co2_solar_bess_f6c_kg", 0.0)
                self._ep_co2_f6d_kg     += info.get("co2_solar_export_f6d_kg", 0.0)
                self._ep_co2_f6_total_kg += info.get("co2_solar_f6_kg", 0.0)
                # F7 (BESS descarga)
                self._ep_co2_f7_kg      += info.get("co2_bess_discharge_f7_kg", 0.0)
                # 3 fórmulas OE3
                self._ep_co2_baseline_kg  += info.get("co2_total_baseline_kg", 0.0)
                self._ep_co2_control_kg   += info.get("co2_total_control_kg", 0.0)
                self._ep_co2_directa_kg   += info.get("co2_reduccion_directa_kg", 0.0)
                self._ep_co2_indirecta_kg += info.get("co2_reduccion_indirecta_kg", 0.0)
                self._ep_co2_neta_kg      += info.get("co2_total_sistema_evitado_kg", 0.0)
                # F0: situación actual sin proyecto (referencia OE2)
                self._ep_co2_sinproyecto_kg            += info.get("co2_total_sinproyecto_kg", 0.0)
                self._ep_co2_sinproyecto_mall_kg       += info.get("co2_sinproyecto_mall_kg", 0.0)
                self._ep_co2_sinproyecto_combustion_kg += info.get("co2_sinproyecto_combustion_kg", 0.0)

                # -- KPI ventana 24h ---------------------------------------
                _grid_imp = info.get("grid_import_kwh", 0.0)
                _sol = info.get("solar_generation_kwh", 0.0)
                _mall = info.get("mall_demand_kwh", 0.0)
                _ev = info.get("ev_motos_actual_kwh", 0.0) + info.get("ev_mototaxis_actual_kwh", 0.0)
                _net_load = max(0.0, _mall + _ev - _sol + _grid_imp)
                _cost = info.get("cost_soles", 0.0) * 0.27
                _co2_step = info.get("co2_total_control_kg", _grid_imp * 0.4521)
                self._kpi_win_grid_imports.append(_grid_imp)
                self._kpi_win_costs.append(_cost)
                self._kpi_win_emissions.append(_co2_step)
                self._kpi_win_loads.append(_net_load)
                if self._kpi_prev_load > 0:
                    self._kpi_ramping_sum += abs(_net_load - self._kpi_prev_load)
                    self._kpi_ramping_count += 1
                self._kpi_prev_load = _net_load

                # -- Trace/timeseries step-level ---------------------------
                self._step_in_ep += 1
                _rew = float(self.locals["rewards"][0]) if self.locals.get("rewards") is not None else 0.0
                _ev_kwh = info.get("ev_motos_actual_kwh", 0.0) + info.get("ev_mototaxis_actual_kwh", 0.0)
                self.trace_records.append({
                    "timestep":            self.n_calls,
                    "episode":             self._ep_count + 1,  # 1-indexed, igual al log
                    "step_in_episode":     self._step_in_ep,
                    "hour":                info.get("hour", self._step_in_ep % 8760),
                    "reward":              _rew,
                    "co2_grid_kg":         info.get("co2_total_control_kg", _grid_imp * 0.4521),
                    "co2_avoided_indirect_kg": info.get("co2_reduccion_indirecta_kg", 0.0),
                    "co2_avoided_direct_kg":   info.get("co2_reduccion_directa_kg", 0.0),
                    "solar_generation_kwh": _sol,
                    "ev_charging_kwh":     _ev_kwh,
                    "grid_import_kwh":     _grid_imp,
                    "bess_power_kw":       info.get("bess_power_kw", 0.0),
                    "motos_cargadas":      info.get("chr_motos_hora", 0.0),
                    "mototaxis_cargadas":  info.get("chr_mototaxis_hora", 0.0),
                    "debt_violation":      1 if info.get("penalty_debt_frac", 0.0) > 0.1 else 0,
                })
                self.timeseries_records.append({
                    "timestep":            self.n_calls,
                    "episode":             self._ep_count + 1,  # 1-indexed, igual al log
                    "hour":                info.get("hour", self._step_in_ep % 8760),
                    "solar_generation_kwh": _sol,
                    "ev_charging_kwh":     _ev_kwh,
                    "grid_import_kwh":     _grid_imp,
                    "bess_power_kw":       info.get("bess_power_kw", 0.0),
                    "bess_soc":            info.get("bess_soc", 0.0),
                    "mall_demand_kwh":     _mall,
                    "co2_grid_kg":         info.get("co2_total_control_kg", _grid_imp * 0.4521),
                    "co2_avoided_indirect_kg": info.get("co2_reduccion_indirecta_kg", 0.0),
                    "co2_avoided_direct_kg":   info.get("co2_reduccion_directa_kg", 0.0),
                    "reward":              _rew,
                    "r_co2":               info.get("r_co2", 0.0),
                    "r_solar":             info.get("r_solar", 0.0),
                    "r_vehicles":          info.get("r_vehicles", 0.0),
                    "r_grid_stable":       info.get("r_grid_stable", 0.0),
                    "motos_charging":      info.get("motos_charging", 0),
                    "mototaxis_charging":  info.get("mototaxis_charging", 0),
                })
        if len(self._kpi_win_loads) >= self._kpi_window_size:
            self._kpi_steps_history.append(self.n_calls)
            self._elec_consumption_history.append(sum(self._kpi_win_grid_imports))
            self._elec_cost_history.append(sum(self._kpi_win_costs))
            self._carbon_emissions_history.append(sum(self._kpi_win_emissions))
            _avg_r = self._kpi_ramping_sum / max(1, self._kpi_ramping_count)
            self._ramping_history.append(_avg_r)
            self._avg_daily_peak_history.append(max(self._kpi_win_loads))
            _avg_l = float(np.mean(self._kpi_win_loads))
            _pk = max(self._kpi_win_loads)
            self._one_minus_lf_history.append(1.0 - _avg_l / max(_pk, 0.001))
            self._kpi_win_grid_imports.clear()
            self._kpi_win_costs.clear()
            self._kpi_win_emissions.clear()
            self._kpi_win_loads.clear()
            self._kpi_ramping_sum = 0.0
            self._kpi_ramping_count = 0

        # -- Log intra-episodio cada 10% del episodio (~876 pasos ~ 36 días) --------
        # Proyecta los acumulados parciales a kg/año para seguimiento en tiempo real.
        # F0/F1 son referencias fijas (mismo perfil de demanda cada año -- correcto).
        # F2 varía según las decisiones del agente (grid_import real del SAC).
        _INTRA_FREQ = max(1, self.log_freq // 10)   # 876 steps = 10% del episodio
        if (
            0 < self._step_in_ep < self.log_freq
            and self._step_in_ep % _INTRA_FREQ == 0
        ):
            _pct_ep  = self._step_in_ep / self.log_freq * 100.0
            _scale   = self.log_freq / self._step_in_ep          # factor de anualización
            _f0_ann  = self._ep_co2_sinproyecto_kg * _scale
            _f1_ann  = self._ep_co2_baseline_kg    * _scale
            _f2_ann  = self._ep_co2_control_kg     * _scale
            _f0f2_pct = (
                (_f0_ann - _f2_ann) / _f0_ann * 100.0
                if _f0_ann > 0.0 else 0.0
            )
            _f0f2_txt = f"-{_f0f2_pct:.1f}%" if _f0f2_pct >= 0.0 else f"+{abs(_f0f2_pct):.1f}%"
            _cur_ep = self.n_calls // self.log_freq + 1
            log.info(
                "[CO2 %5.1f%%ep] Ep %d | F0=%.0f | F1=%.0f | F2(SAC)=%.0f kg/año (*proyectado) "
                "| vs F0: %s",
                _pct_ep, _cur_ep, _f0_ann, _f1_ann, _f2_ann, _f0f2_txt,
            )

        # Log cada episodio completo (8760 pasos)
        if self.n_calls % self.log_freq == 0 and self.n_calls > 0:
            ep_num = self.n_calls // self.log_freq
            reduccion_pct = (
                (self._ep_co2_sinproyecto_kg - self._ep_co2_control_kg)
                / self._ep_co2_sinproyecto_kg * 100.0
                if self._ep_co2_sinproyecto_kg > 0.0 else 0.0
            )
            f0_vs_ctrl_pct = (
                (self._ep_co2_sinproyecto_kg - self._ep_co2_control_kg)
                / self._ep_co2_sinproyecto_kg * 100.0
                if self._ep_co2_sinproyecto_kg > 0.0 else 0.0
            )
            f0_vs_baseline_pct = (
                (self._ep_co2_sinproyecto_kg - self._ep_co2_baseline_kg)
                / self._ep_co2_sinproyecto_kg * 100.0
                if self._ep_co2_sinproyecto_kg > 0.0 else 0.0
            )
            def _pct_reduction_text(pct: float) -> str:
                return f"-{pct:5.1f}%" if pct >= 0.0 else f"+{abs(pct):5.1f}%"
            log.info(
                "-" * 70
            )
            # -- Deltas vs Ep1 para variables del agente -------------------
            _bess_d_ep1    = self._hist_bess_discharge_kwh[0] if self._hist_bess_discharge_kwh else self._ep_bess_discharge_kwh
            _bess_c_ep1    = self._hist_bess_charge_kwh[0]    if self._hist_bess_charge_kwh    else self._ep_bess_charge_kwh
            _grid_ep1      = self._hist_grid_import_kwh[0]    if self._hist_grid_import_kwh    else self._ep_grid_import_kwh
            _f6a_ep1       = self._hist_co2_f6a_kg[0]         if self._hist_co2_f6a_kg         else self._ep_co2_f6a_kg
            _f6c_ep1       = self._hist_co2_f6c_kg[0]         if self._hist_co2_f6c_kg         else self._ep_co2_f6c_kg
            _bess_net      = self._ep_bess_discharge_kwh - self._ep_bess_charge_kwh
            _bess_net_ep1  = _bess_d_ep1 - _bess_c_ep1
            def _dlt(cur: float, ep1: float) -> str:
                d = cur - ep1
                return f"{d:+.0f}"

            log.info(
                "Ep %d | BALANCE ENERGÉTICO ANUAL (kWh) -- [CSV]=fijo | [SAC]=decisión agente",
                ep_num,
            )
            log.info(
                "  [CSV] Solar      = %9.0f kWh | Mall         = %9.0f kWh",
                self._ep_solar_kwh, self._ep_mall_kwh,
            )
            log.info(
                "  [CSV] EV motos demanda  =%9.0f kWh | EV mototaxis demanda  =%9.0f kWh  (estocástico ±15%%/día)",
                self._ep_ev_motos_demand_kwh, self._ep_ev_mototaxis_demand_kwh,
            )
            log.info(
                "  [SAC] EV motos entregado=%9.0f kWh d=%+.0f kWh | mototaxis entregado=%9.0f kWh d=%+.0f kWh | debt_viols=%d",
                self._ep_ev_motos_kwh,
                self._ep_ev_motos_kwh - self._ep_ev_motos_demand_kwh,
                self._ep_ev_mototaxis_kwh,
                self._ep_ev_mototaxis_kwh - self._ep_ev_mototaxis_demand_kwh,
                self._ep_debt_violations,
            )
            log.info(
                "  [SAC] Motos cargadas= %6.0f veh/año | Mototaxis cargadas= %6.0f veh/año | Total= %6.0f veh/año",
                self._ep_motos_cargadas, self._ep_mototaxis_cargadas,
                self._ep_motos_cargadas + self._ep_mototaxis_cargadas,
            )
            _ev_total_dispatch = (
                self._ep_dispatch_pv_to_ev_kwh
                + self._ep_dispatch_bess_to_ev_kwh
                + self._ep_dispatch_grid_to_ev_kwh
            )
            _pv_ev_pct  = 100.0 * self._ep_dispatch_pv_to_ev_kwh   / max(_ev_total_dispatch, 1.0)
            _bess_ev_pct = 100.0 * self._ep_dispatch_bess_to_ev_kwh / max(_ev_total_dispatch, 1.0)
            _grid_ev_pct = 100.0 * self._ep_dispatch_grid_to_ev_kwh / max(_ev_total_dispatch, 1.0)
            log.info(
                "  [SAC] Cargadores EV fuente: PV=%7.0f kWh(%4.1f%%) | BESS=%7.0f kWh(%4.1f%%) | Grid=%7.0f kWh(%4.1f%%)",
                self._ep_dispatch_pv_to_ev_kwh,  _pv_ev_pct,
                self._ep_dispatch_bess_to_ev_kwh, _bess_ev_pct,
                self._ep_dispatch_grid_to_ev_kwh, _grid_ev_pct,
            )
            log.info(
                "  [SAC] BESS_disch = %9.0f kWh | BESS_carga   = %9.0f kWh | BESS_neto= %+.0f kWh",
                self._ep_bess_discharge_kwh, self._ep_bess_charge_kwh, _bess_net,
            )
            log.info(
                "  [SAC] BESS_disch d vs Ep1 = %s kWh | BESS_carga d = %s kWh | BESS_neto d = %s kWh",
                _dlt(self._ep_bess_discharge_kwh, _bess_d_ep1),
                _dlt(self._ep_bess_charge_kwh, _bess_c_ep1),
                _dlt(_bess_net, _bess_net_ep1),
            )
            log.info(
                "  [SAC] Grid_import= %9.0f kWh | d vs Ep1 = %s kWh",
                self._ep_grid_import_kwh, _dlt(self._ep_grid_import_kwh, _grid_ep1),
            )
            log.info(
                "  [SAC] F6a(solar->EV)= %.0f kg CO2 d=%s | F6c(solar->BESS)= %.0f kg CO2 d=%s",
                self._ep_co2_f6a_kg, _dlt(self._ep_co2_f6a_kg, _f6a_ep1),
                self._ep_co2_f6c_kg, _dlt(self._ep_co2_f6c_kg, _f6c_ep1),
            )
            log.info(
                "  [FIS] NOTA: Grid_import anual cambia lento porque "
                "BESS_neto~0 (energía conservada). El agente mejora CUÁNDO "
                "se usa la energía (peak-shaving), no el total kWh anual.",
            )
            log.info("=" * 70)
            log.info("Ep %d | TABLA CO2 vs ESTADO ACTUAL -- OE2/OE3 PVBESSCAR", ep_num)
            log.info(
                "  [NOTA] F0/F1 usan la demanda EV estocástica del episodio "
                "(cantidad, SOC, llegada y permanencia). F2 además varía con SAC."
            )
            log.info(
                "  F0 SIN PROYECTO | %10.0f kg/año | referencia ICE estocástica"
                " equivalente a la demanda EV del episodio",
                self._ep_co2_sinproyecto_kg,
            )
            log.info(
                "  F1 BASELINE     | %10.0f kg/año | vs F0: %s"
                " | sin solar, sin BESS, sin RL",
                self._ep_co2_baseline_kg, _pct_reduction_text(f0_vs_baseline_pct),
            )
            # Comparativa F2 vs Ep1 y vs EpN-1 para ver aprendizaje acumulado e incremental
            _f2_ep1   = self._hist_co2_control_kg[0]  if self._hist_co2_control_kg  else self._ep_co2_control_kg
            _f2_epprv = self._hist_co2_control_kg[-1] if self._hist_co2_control_kg  else self._ep_co2_control_kg
            _f2_delta_ep1 = _f2_ep1   - self._ep_co2_control_kg   # + = mejor vs Ep1
            _f2_delta_prv = _f2_epprv - self._ep_co2_control_kg   # + = mejor vs Ep anterior
            _f2_delta_pct     = _f2_delta_ep1 / _f2_ep1   * 100.0 if _f2_ep1   > 0.0 else 0.0
            _f2_delta_prv_pct = _f2_delta_prv / _f2_epprv * 100.0 if _f2_epprv > 0.0 else 0.0
            _trend_sym = "▼" if _f2_delta_ep1 > 0.0 else ("▲" if _f2_delta_ep1 < 0.0 else "=")
            _prv_sym   = "▼" if _f2_delta_prv > 0.0 else ("▲" if _f2_delta_prv < 0.0 else "=")
            _prv_ep_num = ep_num - len(self._hist_co2_control_kg) + len(self._hist_co2_control_kg) - 1 + 1 if self._hist_co2_control_kg else ep_num
            # Número del episodio anterior correcto: episodio actual - 1
            _prev_ep_label = ep_num - 1 if self._hist_co2_control_kg else ep_num
            log.info(
                "  F2 CTRL SAC     | %10.0f kg/año | vs F0: %s"
                " | %s vs Ep1: %+.0f kg (%+.2f%%) | %s vs Ep%d: %+.0f kg (%+.2f%%)",
                self._ep_co2_control_kg, _pct_reduction_text(f0_vs_ctrl_pct),
                _trend_sym, -_f2_delta_ep1, -_f2_delta_pct,
                _prv_sym, _prev_ep_label, -_f2_delta_prv, -_f2_delta_prv_pct,
            )
            log.info(
                "  Grid_import: %.0f kWh/año -> principal palanca de F2"
                " | BESS_disch: %.0f kWh/año",
                self._ep_grid_import_kwh, self._ep_bess_discharge_kwh,
            )
            log.info(
                "  NETA F0->F2: %.0f kg/año evitados (%.1f%%)"
                " | directa: %.0f kg | indirecta: %.0f kg",
                self._ep_co2_sinproyecto_kg - self._ep_co2_control_kg,
                f0_vs_ctrl_pct,
                self._ep_co2_directa_kg, self._ep_co2_indirecta_kg,
            )
            log.info("-" * 70)

            # -- TensorBoard -----------------------------------------------
            # EV
            self.logger.record("ev/motos_kwh", self._ep_ev_motos_kwh)
            self.logger.record("ev/mototaxis_kwh", self._ep_ev_mototaxis_kwh)
            self.logger.record("ev/debt_violations", self._ep_debt_violations)
            # Balance energético
            self.logger.record("energy/solar_kwh", self._ep_solar_kwh)
            self.logger.record("energy/bess_discharge_kwh", self._ep_bess_discharge_kwh)
            self.logger.record("energy/grid_import_kwh", self._ep_grid_import_kwh)
            self.logger.record("energy/mall_kwh", self._ep_mall_kwh)
            # F6 fases solar
            self.logger.record("co2/f6_total_kg", self._ep_co2_f6_total_kg)
            self.logger.record("co2/f6a_ev_kg", self._ep_co2_f6a_kg)
            self.logger.record("co2/f6b_mall_kg", self._ep_co2_f6b_kg)
            self.logger.record("co2/f6c_bess_kg", self._ep_co2_f6c_kg)
            self.logger.record("co2/f6d_export_kg", self._ep_co2_f6d_kg)
            # F7 BESS
            self.logger.record("co2/f7_bess_kg", self._ep_co2_f7_kg)
            # 3 fórmulas OE3
            self.logger.record("co2/baseline_kg", self._ep_co2_baseline_kg)
            self.logger.record("co2/control_kg", self._ep_co2_control_kg)
            self.logger.record("co2/reduccion_directa_kg", self._ep_co2_directa_kg)
            self.logger.record("co2/reduccion_indirecta_kg", self._ep_co2_indirecta_kg)
            self.logger.record("co2/reduccion_neta_kg", self._ep_co2_neta_kg)
            self.logger.record("co2/reduccion_pct", reduccion_pct)
            # F0: situación actual sin proyecto & comparación vs F0 (OE3)
            self.logger.record("co2/sinproyecto_kg", self._ep_co2_sinproyecto_kg)
            self.logger.record("co2/f0_vs_ctrl_pct", f0_vs_ctrl_pct)
            self.logger.record("co2/f0_vs_baseline_pct", f0_vs_baseline_pct)
            # Ganancia incremental: F2 vs episodio anterior (señal de aprendizaje por ep)
            self.logger.record("co2/f2_delta_vs_prev_kg", float(-_f2_delta_prv))
            self.logger.record("co2/f2_delta_vs_ep1_kg",  float(-_f2_delta_ep1))

            # -- Historia por episodio -------------------------------------
            self._episodes.append(ep_num)
            self._hist_ev_motos_kwh.append(self._ep_ev_motos_kwh)
            self._hist_ev_mototaxis_kwh.append(self._ep_ev_mototaxis_kwh)
            self._hist_ev_motos_demand_kwh.append(self._ep_ev_motos_demand_kwh)
            self._hist_ev_mototaxis_demand_kwh.append(self._ep_ev_mototaxis_demand_kwh)
            self._hist_debt_violations.append(float(self._ep_debt_violations))
            self._hist_solar_kwh.append(self._ep_solar_kwh)
            self._hist_bess_discharge_kwh.append(self._ep_bess_discharge_kwh)
            self._hist_bess_charge_kwh.append(self._ep_bess_charge_kwh)
            self._hist_grid_import_kwh.append(self._ep_grid_import_kwh)
            self._hist_mall_kwh.append(self._ep_mall_kwh)
            self._hist_co2_f6a_kg.append(self._ep_co2_f6a_kg)
            self._hist_co2_f6b_kg.append(self._ep_co2_f6b_kg)
            self._hist_co2_f6c_kg.append(self._ep_co2_f6c_kg)
            self._hist_co2_f6d_kg.append(self._ep_co2_f6d_kg)
            self._hist_co2_f7_kg.append(self._ep_co2_f7_kg)
            self._hist_co2_baseline_kg.append(self._ep_co2_baseline_kg)
            self._hist_co2_control_kg.append(self._ep_co2_control_kg)
            self._hist_co2_directa_kg.append(self._ep_co2_directa_kg)
            self._hist_co2_indirecta_kg.append(self._ep_co2_indirecta_kg)
            self._hist_co2_neta_kg.append(self._ep_co2_neta_kg)
            self._hist_reduccion_pct.append(reduccion_pct)
            self._hist_co2_sinproyecto_kg.append(self._ep_co2_sinproyecto_kg)

            # Reset acumuladores del episodio
            self._reset_ep()

            # -- Flush incremental trace/timeseries al disco ---------------
            self.output_dir.mkdir(parents=True, exist_ok=True)
            if self.trace_records:
                _tp = self.output_dir / "trace_sac.csv"
                _hdr = not _tp.exists()
                pd.DataFrame(self.trace_records).to_csv(_tp, mode="a", index=False, header=_hdr)
                self.trace_records = []
            if self.timeseries_records:
                _tsp = self.output_dir / "timeseries_sac.csv"
                _hdr = not _tsp.exists()
                pd.DataFrame(self.timeseries_records).to_csv(_tsp, mode="a", index=False, header=_hdr)
                self.timeseries_records = []
            self._ep_count += 1
            self._step_in_ep = 0

        return True

    def on_training_end(self) -> None:
        """Genera todas las gráficas al finalizar el entrenamiento SAC."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # -- Flush final trace/timeseries (registros no guardados aún) ----
        if self.trace_records:
            _tp = self.output_dir / "trace_sac.csv"
            _hdr = not _tp.exists()
            pd.DataFrame(self.trace_records).to_csv(_tp, mode="a", index=False, header=_hdr)
            self.trace_records = []
            log.info("[DATA] trace_sac.csv: flush final -> %s", _tp)
        if self.timeseries_records:
            _tsp = self.output_dir / "timeseries_sac.csv"
            _hdr = not _tsp.exists()
            pd.DataFrame(self.timeseries_records).to_csv(_tsp, mode="a", index=False, header=_hdr)
            self.timeseries_records = []
            log.info("[DATA] timeseries_sac.csv: flush final -> %s", _tsp)
        if len(self._episodes) > 1:
            log.info("[GRAPH] Generando gráficas de episodios OE3 SAC...")
            self._generate_ev_plots()
        if len(self._kpi_steps_history) > 1:
            log.info("[GRAPH] Generando gráficas KPI diarios SAC...")
            self._generate_kpi_graphs()
        log.info("[GRAPH] OK Gráficas SAC guardadas en: %s", self.output_dir)

    # ----------------------------------------------------------------------
    # Plotting helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _smooth(data: list[float], window: int = 5) -> list[float]:
        """Suavizado con media móvil (pandas rolling)."""
        if len(data) < 2:
            return data
        s = pd.Series(data)
        return s.rolling(window=window, min_periods=1).mean().tolist()

    def _generate_ev_plots(self) -> None:
        """Genera 3 dashboards de métricas OE3 por episodio."""
        eps = self._episodes
        sm = self._smooth

        # -- Dashboard 1: CO2 reducción OE3 -------------------------------
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("SAC -- CO2 Reducción OE3 por Episodio", fontsize=14, fontweight="bold")

        ax = axes[0, 0]
        ax.plot(eps, self._hist_co2_baseline_kg, "b-", alpha=0.3, label="Baseline (raw)")
        ax.plot(eps, sm(self._hist_co2_baseline_kg), "b-", linewidth=2, label="Baseline (suavizado)")
        ax.plot(eps, self._hist_co2_control_kg, "r-", alpha=0.3, label="Control (raw)")
        ax.plot(eps, sm(self._hist_co2_control_kg), "r-", linewidth=2, label="Control (suavizado)")
        ax.set_title("CO2 Baseline vs Control (kg/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kg CO2/año")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        ax = axes[0, 1]
        ax.plot(eps, self._hist_co2_neta_kg, "g-", alpha=0.3)
        ax.plot(eps, sm(self._hist_co2_neta_kg), "g-", linewidth=2, label="CO2 neta evitada")
        ax.set_title("CO2 Neta Evitada OE3 (kg/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kg CO2 evitado")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[0, 2]
        ax.plot(eps, self._hist_reduccion_pct, "purple", alpha=0.3)
        ax.plot(eps, sm(self._hist_reduccion_pct), "purple", linewidth=2, label="% Reducción")
        ax.axhline(y=0, color="k", linestyle="--", alpha=0.5)
        ax.set_title("% Reducción CO2 OE3")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("%")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[1, 0]
        ax.plot(eps, self._hist_co2_directa_kg, "orange", alpha=0.3, label="Directa (raw)")
        ax.plot(eps, sm(self._hist_co2_directa_kg), "orange", linewidth=2, label="Directa")
        ax.plot(eps, self._hist_co2_indirecta_kg, "brown", alpha=0.3, label="Indirecta (raw)")
        ax.plot(eps, sm(self._hist_co2_indirecta_kg), "brown", linewidth=2, label="Indirecta")
        ax.set_title("CO2 Directa vs Indirecta (kg/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kg CO2")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        ax = axes[1, 1]
        ax.stackplot(
            eps,
            self._hist_co2_f6a_kg,
            self._hist_co2_f6b_kg,
            self._hist_co2_f6c_kg,
            self._hist_co2_f6d_kg,
            labels=["F6a EV", "F6b Mall", "F6c BESS", "F6d Export"],
            colors=["#2ca02c", "#1f77b4", "#ff7f0e", "#9467bd"],
            alpha=0.7,
        )
        ax.set_title("CO2 Evitado por Fase Solar F6 (kg/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kg CO2")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        ax = axes[1, 2]
        ax.plot(eps, self._hist_co2_f7_kg, "teal", alpha=0.3, label="F7 BESS (raw)")
        ax.plot(eps, sm(self._hist_co2_f7_kg), "teal", linewidth=2, label="F7 BESS")
        ax.set_title("CO2 Evitado BESS F7 (kg/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kg CO2")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        p = self.output_dir / "sac_co2_oe3_episodios.png"
        fig.savefig(str(p), dpi=120, bbox_inches="tight")
        plt.close(fig)
        log.info("[GRAPH] Guardado: %s", p)

        # -- Dashboard 2: Balance energético -------------------------------
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("SAC -- Balance Energético por Episodio", fontsize=14, fontweight="bold")

        ax = axes[0, 0]
        ax.plot(eps, sm(self._hist_solar_kwh), "gold", linewidth=2, label="Solar PV")
        ax.set_title("Generación Solar (kWh/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kWh")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[0, 1]
        ax.plot(eps, sm(self._hist_bess_discharge_kwh), "orange", linewidth=2, label="BESS descarga")
        ax.set_title("BESS Descarga (kWh/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kWh")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[0, 2]
        ax.plot(eps, sm(self._hist_grid_import_kwh), "red", linewidth=2, label="Grid import")
        ax.set_title("Importación de Red (kWh/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kWh")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[1, 0]
        ax.plot(eps, sm(self._hist_ev_motos_kwh), "blue", linewidth=2, label="Motos EV")
        ax.plot(eps, sm(self._hist_ev_mototaxis_kwh), "cyan", linewidth=2, label="Mototaxis EV")
        ax.set_title("Carga EV Motos + Mototaxis (kWh/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kWh")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[1, 1]
        ax.plot(eps, sm(self._hist_mall_kwh), "gray", linewidth=2, label="Mall")
        ax.set_title("Demanda Mall (kWh/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kWh")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[1, 2]
        ax.stackplot(
            eps,
            self._hist_solar_kwh,
            self._hist_bess_discharge_kwh,
            labels=["Solar", "BESS descarga"],
            colors=["gold", "orange"],
            alpha=0.7,
        )
        ax.plot(eps, sm(self._hist_grid_import_kwh), "r-", linewidth=2, label="Grid import")
        ax.set_title("Energía: Solar + BESS vs Importación")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kWh/año")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        p = self.output_dir / "sac_balance_energetico_episodios.png"
        fig.savefig(str(p), dpi=120, bbox_inches="tight")
        plt.close(fig)
        log.info("[GRAPH] Guardado: %s", p)

        # -- Dashboard 3: EV & operación -----------------------------------
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle("SAC -- Métricas EV por Episodio", fontsize=14, fontweight="bold")

        ax = axes[0]
        ax.plot(eps, sm(self._hist_ev_motos_kwh), "blue", linewidth=2, label="Motos")
        ax.plot(eps, sm(self._hist_ev_mototaxis_kwh), "cyan", linewidth=2, label="Mototaxis")
        ax.set_title("Energía Cargada EV (kWh/año)")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("kWh")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[1]
        ax.plot(eps, self._hist_debt_violations, "red", linewidth=2, marker="o", ms=4)
        ax.set_title("Violaciones de Deuda EV")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("nº violaciones")
        ax.grid(True, alpha=0.3)

        ax = axes[2]
        ax.plot(eps, sm(self._hist_reduccion_pct), "purple", linewidth=2)
        ax.axhline(y=0, color="k", linestyle="--", alpha=0.5)
        ax.fill_between(
            eps,
            [max(v, 0) for v in sm(self._hist_reduccion_pct)],
            alpha=0.2,
            color="green",
            label="Reducción positiva",
        )
        ax.set_title("% Reducción CO2 OE3")
        ax.set_xlabel("Episodio")
        ax.set_ylabel("%")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        p = self.output_dir / "sac_ev_metricas_episodios.png"
        fig.savefig(str(p), dpi=120, bbox_inches="tight")
        plt.close(fig)
        log.info("[GRAPH] Guardado: %s", p)

        # -- CSV histórico -------------------------------------------------
        df = pd.DataFrame({
            "episodio": self._episodes,
            "co2_baseline_kg": self._hist_co2_baseline_kg,
            "co2_control_kg": self._hist_co2_control_kg,
            "co2_directa_kg": self._hist_co2_directa_kg,
            "co2_indirecta_kg": self._hist_co2_indirecta_kg,
            "co2_neta_kg": self._hist_co2_neta_kg,
            "reduccion_pct": self._hist_reduccion_pct,
            "solar_kwh": self._hist_solar_kwh,
            "bess_discharge_kwh": self._hist_bess_discharge_kwh,
            "grid_import_kwh": self._hist_grid_import_kwh,
            "mall_kwh": self._hist_mall_kwh,
            "ev_motos_kwh": self._hist_ev_motos_kwh,
            "ev_mototaxis_kwh": self._hist_ev_mototaxis_kwh,
            "debt_violations": self._hist_debt_violations,
            "co2_f6a_kg": self._hist_co2_f6a_kg,
            "co2_f6b_kg": self._hist_co2_f6b_kg,
            "co2_f6c_kg": self._hist_co2_f6c_kg,
            "co2_f6d_kg": self._hist_co2_f6d_kg,
            "co2_f7_kg": self._hist_co2_f7_kg,
        })
        csv_p = self.output_dir / "sac_episodios_history.csv"
        df.to_csv(str(csv_p), index=False)
        log.info("[GRAPH] CSV histórico: %s", csv_p)

    def _generate_kpi_graphs(self) -> None:
        """Genera 7 gráficas KPI de CityLearn + dashboard."""
        steps = self._kpi_steps_history
        steps_k = [s / 1000.0 for s in steps]
        sm = self._smooth

        def _save_fig(fig: _mpl_fig.Figure, name: str) -> None:
            p = self.output_dir / name
            fig.savefig(str(p), dpi=120, bbox_inches="tight")
            plt.close(fig)
            log.info("[KPI] Guardado: %s", p)

        # 1. Electricidad consumida
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self._elec_consumption_history, "b-", alpha=0.4, label="Raw")
        ax.plot(steps_k, sm(self._elec_consumption_history), "b-", linewidth=2, label="Suavizado")
        if len(steps_k) > 10:
            z = np.polyfit(steps_k, self._elec_consumption_history, 1)
            ax.plot(steps_k, np.polyval(z, steps_k), "b--", alpha=0.8, label="Tendencia")
        ax.set_title("KPI: Consumo Electricidad (kWh/día)")
        ax.set_xlabel("Miles de pasos")
        ax.set_ylabel("kWh")
        ax.legend()
        ax.grid(True, alpha=0.3)
        _save_fig(fig, "kpi_electricity_consumption.png")

        # 2. Costo electricidad
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self._elec_cost_history, "g-", alpha=0.4, label="Raw")
        ax.plot(steps_k, sm(self._elec_cost_history), "g-", linewidth=2, label="Suavizado")
        ax.set_ylim(bottom=0)
        ax.set_title("KPI: Costo Electricidad (USD/día)")
        ax.set_xlabel("Miles de pasos")
        ax.set_ylabel("USD")
        ax.legend()
        ax.grid(True, alpha=0.3)
        _save_fig(fig, "kpi_electricity_cost.png")

        # 3. Emisiones CO2
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self._carbon_emissions_history, "brown", alpha=0.4, label="Raw")
        ax.plot(steps_k, sm(self._carbon_emissions_history), "brown", linewidth=2, label="Suavizado")
        if self._carbon_emissions_history:
            baseline = self._carbon_emissions_history[0]
            ax.axhline(y=baseline, color="gray", linestyle="--", alpha=0.7, label=f"Inicio: {baseline:.2f}")
        ax.set_title("KPI: Emisiones CO2 (kg/día)")
        ax.set_xlabel("Miles de pasos")
        ax.set_ylabel("kg CO2")
        ax.legend()
        ax.grid(True, alpha=0.3)
        _save_fig(fig, "kpi_carbon_emissions.png")

        # 4. Ramping
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self._ramping_history, "purple", alpha=0.4, label="Raw")
        ax.plot(steps_k, sm(self._ramping_history), "purple", linewidth=2, label="Suavizado")
        ax.set_ylim(bottom=0)
        ax.set_title("KPI: Ramping de Red (kW promedio)")
        ax.set_xlabel("Miles de pasos")
        ax.set_ylabel("kW")
        ax.legend()
        ax.grid(True, alpha=0.3)
        _save_fig(fig, "kpi_ramping.png")

        # 5. Pico diario
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self._avg_daily_peak_history, "red", alpha=0.4, label="Raw")
        ax.plot(steps_k, sm(self._avg_daily_peak_history), "red", linewidth=2, label="Suavizado")
        ax.set_ylim(bottom=0)
        ax.set_title("KPI: Demanda Pico Diaria (kW)")
        ax.set_xlabel("Miles de pasos")
        ax.set_ylabel("kW")
        ax.legend()
        ax.grid(True, alpha=0.3)
        _save_fig(fig, "kpi_daily_peak.png")

        # 6. (1 - Load Factor)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self._one_minus_lf_history, "orange", alpha=0.4, label="1 - LF (raw)")
        _lf_sm = sm(self._one_minus_lf_history)
        ax.plot(steps_k, _lf_sm, "orange", linewidth=2, label="Suavizado")
        ax.axhline(y=0.3, color="green", linestyle="--", alpha=0.7, label="Objetivo dif < 0.3")
        ax.fill_between(steps_k, _lf_sm, 0.3,
                        where=[v < 0.3 for v in _lf_sm], alpha=0.2, color="green")
        ax.set_ylim(0, 1)
        ax.set_title("KPI: (1 - Factor de Carga)")
        ax.set_xlabel("Miles de pasos")
        ax.set_ylabel("1 - LF")
        ax.legend()
        ax.grid(True, alpha=0.3)
        _save_fig(fig, "kpi_load_factor.png")

        # 7. Dashboard 2x3
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("SAC -- Dashboard KPI CityLearn", fontsize=14, fontweight="bold")
        kpi_data = [
            (self._elec_consumption_history, "Consumo elec. (kWh/día)", "blue"),
            (self._elec_cost_history, "Costo elec. (USD/día)", "green"),
            (self._carbon_emissions_history, "Emisiones CO2 (kg/día)", "brown"),
            (self._ramping_history, "Ramping (kW)", "purple"),
            (self._avg_daily_peak_history, "Pico diario (kW)", "red"),
            (self._one_minus_lf_history, "1 - Load Factor", "orange"),
        ]
        for idx, (data, title, color) in enumerate(kpi_data):
            ax = axes[idx // 3][idx % 3]
            ax.plot(steps_k, sm(data), color=color, linewidth=2)
            ax.set_title(title)
            ax.set_xlabel("Miles pasos")
            ax.grid(True, alpha=0.3)
        plt.tight_layout()
        _save_fig(fig, "kpi_dashboard.png")


# ===================== SAC DIAGNOSTICS CALLBACK =====================

class SACDiagnosticsCallback(BaseCallback):
    """Registra métricas internas del optimizador SAC para gráficas diagnósticas."""

    def __init__(self, output_dir: Path, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.output_dir = output_dir
        self.steps_history: list[int] = []
        self.actor_loss_history: list[float] = []
        self.critic_loss_history: list[float] = []
        self.ent_coef_history: list[float] = []
        self.ent_coef_loss_history: list[float] = []

    def _on_step(self) -> bool:
        try:
            kv = self.model.logger.name_to_value
            actor = kv.get("train/actor_loss", None)
            critic = kv.get("train/critic_loss", None)
            ent = kv.get("train/ent_coef", None)
            ent_l = kv.get("train/ent_coef_loss", None)
            if actor is not None:
                self.steps_history.append(self.num_timesteps)
                self.actor_loss_history.append(float(actor))
                self.critic_loss_history.append(float(critic) if critic is not None else 0.0)
                self.ent_coef_history.append(float(ent) if ent is not None else 0.0)
                self.ent_coef_loss_history.append(float(ent_l) if ent_l is not None else 0.0)
        except Exception:
            pass
        return True

    def on_training_end(self) -> None:
        """Genera gráficas diagnósticas SAC."""
        if len(self.steps_history) < 2:
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        steps_k = [s / 1000.0 for s in self.steps_history]
        sm = lambda data, w=10: pd.Series(data).rolling(window=w, min_periods=1).mean().tolist()

        def _save(fig: _mpl_fig.Figure, name: str) -> None:
            p = self.output_dir / name
            fig.savefig(str(p), dpi=120, bbox_inches="tight")
            plt.close(fig)
            log.info("[SAC-DIAG] Guardado: %s", p)

        # Actor loss
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self.actor_loss_history, "blue", alpha=0.3, label="Raw")
        ax.plot(steps_k, sm(self.actor_loss_history), "blue", linewidth=2, label="Suavizado")
        ax.axhline(y=0, color="k", linestyle="--", alpha=0.5)
        ax.set_title("SAC: Actor Loss"); ax.set_xlabel("Miles pasos"); ax.set_ylabel("Loss")
        ax.legend(); ax.grid(True, alpha=0.3)
        _save(fig, "sac_actor_loss.png")

        # Critic loss
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self.critic_loss_history, "green", alpha=0.3, label="Raw")
        ax.plot(steps_k, sm(self.critic_loss_history), "green", linewidth=2, label="Suavizado")
        ax.set_title("SAC: Critic Loss"); ax.set_xlabel("Miles pasos"); ax.set_ylabel("Loss")
        ax.legend(); ax.grid(True, alpha=0.3)
        _save(fig, "sac_critic_loss.png")

        # Entropy coef
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self.ent_coef_history, "red", alpha=0.3, label="Ent coef raw")
        ax.plot(steps_k, sm(self.ent_coef_history), "red", linewidth=2, label="Suavizado")
        ax.set_title("SAC: Entropy Coefficient"); ax.set_xlabel("Miles pasos"); ax.set_ylabel("a")
        ax.legend(); ax.grid(True, alpha=0.3)
        _save(fig, "sac_ent_coef.png")

        # Entropy coef loss
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self.ent_coef_loss_history, "purple", alpha=0.3, label="Ent coef loss raw")
        ax.plot(steps_k, sm(self.ent_coef_loss_history), "purple", linewidth=2, label="Suavizado")
        ax.axhline(y=0, color="k", linestyle="--", alpha=0.5)
        ax.set_title("SAC: Entropy Coef Loss"); ax.set_xlabel("Miles pasos"); ax.set_ylabel("Loss")
        ax.legend(); ax.grid(True, alpha=0.3)
        _save(fig, "sac_ent_coef_loss.png")

        # Dashboard 2x2
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("SAC -- Diagnósticos del Optimizador", fontsize=14, fontweight="bold")
        for ax, data, title, color in [
            (axes[0, 0], self.actor_loss_history, "Actor Loss", "blue"),
            (axes[0, 1], self.critic_loss_history, "Critic Loss", "green"),
            (axes[1, 0], self.ent_coef_history, "Entropy Coef (a)", "red"),
            (axes[1, 1], self.ent_coef_loss_history, "Entropy Coef Loss", "purple"),
        ]:
            ax.plot(steps_k, sm(data), color=color, linewidth=2)
            ax.set_title(title); ax.set_xlabel("Miles pasos"); ax.grid(True, alpha=0.3)
        plt.tight_layout()
        _save(fig, "sac_dashboard.png")

        # CSV
        df = pd.DataFrame({
            "timestep": self.steps_history,
            "actor_loss": self.actor_loss_history,
            "critic_loss": self.critic_loss_history,
            "ent_coef": self.ent_coef_history,
            "ent_coef_loss": self.ent_coef_loss_history,
        })
        csv_p = self.output_dir / "sac_diagnostics_history.csv"
        df.to_csv(str(csv_p), index=False)
        log.info("[SAC-DIAG] CSV: %s", csv_p)


# ===================== CONVERGENCE & ROBUSTNESS CALLBACK =====================


class ConvergenceRewardsCallback(BaseCallback):
    """Registra recompensas acumuladas por episodio y métricas de robustez estocástica.

    Genera en tiempo real (al finalizar cada episodio):
      1. Curva de convergencia: reward por episodio + media móvil ± s
      2. Análisis de varianza: CV rolling, tendencia R2, estabilidad
      3. Comparación robustez: primers N vs últimos N episodios
      4. Histograma de recompensas (últimos episodios con ajuste normal)

    Las figuras se guardan en outputs/sac_training/ con nombre fijo para que
    se sobreescriban cada episodio (ver «en vivo» el progreso).

    Fuentes de datos:
      - self.locals["infos"][0].get("episode") -> Monitor wraps env y añade
        {"episode": {"r": reward, "l": length, "t": elapsed}} al info dict
        cuando un episodio termina (estándar SB3).
    """

    WINDOW = 5      # media móvil
    LAST_N = 10     # episodios «plateau» para métricas de robustez final
    PALETTE = {
        "raw":    "#aec7e8",
        "mean":   "#1f77b4",
        "band":   "#1f77b4",
        "conv":   "#2ca02c",
        "var":    "#d62728",
    }

    def __init__(self, output_dir: Path, ep_len: int = 8760, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.output_dir = output_dir
        self.ep_len = ep_len
        # -- Historiales --------------------------------------------------
        self._ep_rewards: list[float] = []
        self._ep_numbers: list[int] = []
        self._ep_timesteps: list[int] = []
        # -- Acumulador del episodio actual (fallback si Monitor no activo) -
        self._acc_reward: float = 0.0
        self._acc_steps: int = 0

    @staticmethod
    def _smooth(data: list[float], window: int = 5) -> np.ndarray:
        s = pd.Series(data)
        return s.rolling(window=window, min_periods=1).mean().values  # type: ignore[return-value]

    @staticmethod
    def _rolling_std(data: list[float], window: int = 5) -> np.ndarray:
        s = pd.Series(data)
        return s.rolling(window=window, min_periods=1).std().fillna(0.0).values  # type: ignore[return-value]

    @staticmethod
    def _rolling_cv(data: list[float], window: int = 5) -> np.ndarray:
        """Coeficiente de variación (%): s/u x 100, sign-safe."""
        s = pd.Series(data)
        rm = s.rolling(window=window, min_periods=1).mean()
        rs = s.rolling(window=window, min_periods=1).std().fillna(0.0)
        cv = (rs / rm.abs().clip(lower=1e-9)) * 100.0
        return cv.values  # type: ignore[return-value]

    @staticmethod
    def _trend_r2(values: list[float]) -> float:
        """R2 de regresión lineal (OLS) de los valores; NaN si n < 3."""
        if len(values) < 3:
            return float("nan")
        x = np.arange(len(values), dtype=float)
        y = np.array(values, dtype=float)
        c = np.polyfit(x, y, 1)
        y_hat = np.polyval(c, x)
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        ss_res = float(np.sum((y - y_hat) ** 2))
        return 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    def _convergence_episode(self, values: list[float], threshold: float = 0.95) -> int | None:
        """Primer episodio donde la media móvil supera threshold x max(media móvil)."""
        if len(values) < self.WINDOW + 1:
            return None
        roll = self._smooth(values, self.WINDOW)
        target = float(roll.max()) * threshold
        hits = np.where(roll >= target)[0]
        return int(hits[0]) + 1 if len(hits) else None

    def _on_step(self) -> bool:
        """Captura reward de episodio terminado vía info['episode'] (Monitor SB3)."""
        self._acc_reward += float(self.locals["rewards"][0])
        self._acc_steps += 1

        infos = self.locals.get("infos") or []
        for info in infos:
            ep_info = info.get("episode")
            if ep_info is not None:
                # Monitor registra el reward total del episodio terminado
                ep_reward = float(ep_info.get("r", self._acc_reward))
                ep_num = len(self._ep_rewards) + 1
                self._ep_rewards.append(ep_reward)
                self._ep_numbers.append(ep_num)
                self._ep_timesteps.append(self.num_timesteps)
                # Reset acumulador fallback
                self._acc_reward = 0.0
                self._acc_steps = 0
                # Log y figura en cada nuevo episodio
                self._log_metrics(ep_num, ep_reward)
                if ep_num >= 2:
                    self._save_convergence_figure()
            else:
                # Fallback: episodio por longitud fija (sin Monitor)
                if self._acc_steps >= self.ep_len:
                    ep_num = len(self._ep_rewards) + 1
                    self._ep_rewards.append(self._acc_reward)
                    self._ep_numbers.append(ep_num)
                    self._ep_timesteps.append(self.num_timesteps)
                    self._log_metrics(ep_num, self._acc_reward)
                    self._acc_reward = 0.0
                    self._acc_steps = 0
                    if ep_num >= 2:
                        self._save_convergence_figure()
        return True

    def _log_metrics(self, ep_num: int, ep_reward: float) -> None:
        """Imprime métricas de varianza/robustez para el episodio actual."""
        n = len(self._ep_rewards)
        window_data = self._ep_rewards[-min(self.WINDOW, n):]
        roll_mean = float(np.mean(window_data))
        roll_std = float(np.std(window_data))
        roll_cv = roll_std / max(abs(roll_mean), 1e-9) * 100.0
        r2 = self._trend_r2(self._ep_rewards)
        log.info(
            "[CONV] Ep %3d | reward=%9.2f | u(w%d)=%9.2f | s=%7.2f | CV=%.1f%% | R2=%.4f",
            ep_num, ep_reward, min(self.WINDOW, n), roll_mean, roll_std, roll_cv, r2,
        )
        # TensorBoard
        self.logger.record("convergence/episode_reward", ep_reward)
        self.logger.record("convergence/rolling_mean", roll_mean)
        self.logger.record("convergence/rolling_std", roll_std)
        self.logger.record("convergence/rolling_cv_pct", roll_cv)
        self.logger.record("convergence/trend_r2", r2 if not np.isnan(r2) else 0.0)

    def _save_convergence_figure(self) -> None:
        """Genera y guarda la figura de convergencia + varianza (sobreescribe)."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        eps = self._ep_numbers
        rews = self._ep_rewards
        n = len(rews)

        roll_mean = self._smooth(rews, self.WINDOW)
        roll_std = self._rolling_std(rews, self.WINDOW)
        roll_cv = self._rolling_cv(rews, self.WINDOW)

        ncols = 2 if n < 5 else (4 if n >= self.LAST_N else 3)
        fig = plt.figure(figsize=(6 * ncols, 5))
        gs = gridspec.GridSpec(1, ncols, figure=fig, wspace=0.35)
        fig.suptitle(
            f"SAC -- Curvas de Convergencia y Robustez Estocástica\n"
            f"pvbesscar | {n} episodio(s) completados | "
            f"pasos={self._ep_timesteps[-1]:,}",
            fontsize=11, fontweight="bold",
        )

        # -- Panel 1: Curva de convergencia -----------------------------
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(eps, rews, color=self.PALETTE["raw"], alpha=0.6,
                 linewidth=1, marker="o", markersize=3, label="Recompensa ep.")
        ax1.plot(eps, roll_mean, color=self.PALETTE["mean"],
                 linewidth=2.5, label=f"Media móvil (w={self.WINDOW})")
        ax1.fill_between(
            eps,
            roll_mean - roll_std,
            roll_mean + roll_std,
            alpha=0.20, color=self.PALETTE["band"], label="±1s",
        )
        # Línea de tendencia
        if n >= 3:
            x = np.arange(n, dtype=float)
            c = np.polyfit(x, rews, 1)
            trend_line = np.polyval(c, x)
            r2 = self._trend_r2(rews)
            ax1.plot(eps, trend_line, "k--", linewidth=1.5, alpha=0.7,
                     label=f"Tendencia (R2={r2:.3f})")
        # Marcador de convergencia
        conv_ep = self._convergence_episode(rews)
        if conv_ep and conv_ep <= n:
            ax1.axvline(conv_ep, color=self.PALETTE["conv"],
                        linestyle="--", linewidth=1.5,
                        label=f"Convergencia ep. {conv_ep}")
        ax1.set_xlabel("Episodio", fontsize=9)
        ax1.set_ylabel("Recompensa acumulada", fontsize=9)
        ax1.set_title("Curva de Convergencia", fontsize=10, fontweight="bold")
        ax1.legend(fontsize=7)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(labelsize=8)

        # -- Panel 2: CV rolling (varianza relativa) ------------------
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.plot(eps, roll_cv, color=self.PALETTE["var"],
                 linewidth=2, label="CV rolling (%)")
        ax2.fill_between(eps, roll_cv, alpha=0.15, color=self.PALETTE["var"])
        ax2.axhline(10.0, color="green", linestyle="--", linewidth=1.2,
                    alpha=0.8, label="Umbral estabilidad (CV<10%)")
        ax2.axhline(20.0, color="orange", linestyle="--", linewidth=1.0,
                    alpha=0.7, label="CV=20%")
        ax2.set_xlabel("Episodio", fontsize=9)
        ax2.set_ylabel("Coef. Variación (%)", fontsize=9)
        ax2.set_title("Varianza Relativa Rolling (CV)", fontsize=10, fontweight="bold")
        ax2.legend(fontsize=7)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(labelsize=8)
        ax2.set_ylim(bottom=0)

        # -- Panel 3: Histograma (si >= 5 episodios) ------------------
        if n >= 5 and ncols >= 3:
            ax3 = fig.add_subplot(gs[0, 2])
            last_n = rews[-min(self.LAST_N, n):]
            ax3.hist(last_n, bins=min(10, len(last_n)), density=True,
                     color=self.PALETTE["mean"], alpha=0.7, edgecolor="white")
            if len(last_n) >= 3:
                mu_h, sig_h = float(np.mean(last_n)), float(np.std(last_n))
                xs = np.linspace(min(last_n), max(last_n), 100)
                from scipy.stats import norm as _norm
                ax3.plot(xs, _norm.pdf(xs, mu_h, sig_h), "k--",
                         linewidth=1.5, label=f"Normal N({mu_h:.0f}, {sig_h:.0f})")
                ax3.set_title(
                    f"Distribución Últimos {len(last_n)} Ep.\n"
                    f"u={mu_h:.1f} s={sig_h:.1f} CV={sig_h/max(abs(mu_h),1e-9)*100:.1f}%",
                    fontsize=9, fontweight="bold",
                )
            else:
                ax3.set_title(f"Distribución Últimos {len(last_n)} Ep.", fontsize=9)
            ax3.set_xlabel("Recompensa acumulada", fontsize=9)
            ax3.set_ylabel("Densidad", fontsize=9)
            ax3.legend(fontsize=7)
            ax3.grid(True, alpha=0.3)
            ax3.tick_params(labelsize=8)

        # -- Panel 4: Comparación primeros vs últimos (si >= LAST_N) --
        if n >= self.LAST_N and ncols >= 4:
            ax4 = fig.add_subplot(gs[0, 3])
            first_n = rews[: self.LAST_N]
            last_n = rews[-self.LAST_N:]
            cats = [f"Primeros\n{self.LAST_N} ep.", f"Últimos\n{self.LAST_N} ep."]
            means = [float(np.mean(first_n)), float(np.mean(last_n))]
            stds = [float(np.std(first_n)), float(np.std(last_n))]
            cvs = [s / max(abs(m), 1e-9) * 100 for m, s in zip(means, stds)]
            bars = ax4.bar(cats, means,
                           color=["#d62728", "#2ca02c"], alpha=0.75, width=0.5, zorder=3)
            ax4.errorbar([0, 1], means, yerr=stds,
                         fmt="none", ecolor="black", elinewidth=2,
                         capsize=10, capthick=2, zorder=4)
            for i, (m, cv) in enumerate(zip(means, cvs)):
                sign = "+" if m >= 0 else ""
                ax4.text(i, max(means) + max(stds) * 0.55,
                         f"{sign}{m:.0f}\nCV={cv:.1f}%",
                         ha="center", fontsize=8, fontweight="bold")
            ax4.set_title(
                f"Robustez: Primeros vs Últimos {self.LAST_N} ep.",
                fontsize=9, fontweight="bold",
            )
            ax4.set_ylabel("Recompensa media", fontsize=9)
            ax4.grid(True, alpha=0.3, axis="y")
            ax4.tick_params(labelsize=8)

        out_path = self.output_dir / "sac_convergencia_recompensas.png"
        fig.savefig(str(out_path), dpi=130, bbox_inches="tight")
        plt.close(fig)

    def on_training_end(self) -> None:
        """Genera figura final completa + CSV de estadísticas por episodio."""
        n = len(self._ep_rewards)
        if n < 2:
            log.info("[CONV] Insuficientes episodios para generar figuras finales (%d)", n)
            return

        # Forzar figura final con todos los paneles disponibles
        self._save_convergence_figure()
        log.info("[CONV] Figura final convergencia: sac_convergencia_recompensas.png")

        # -- Métricas de robustez final ---------------------------------
        rews = self._ep_rewards
        r2 = self._trend_r2(rews)
        conv_ep = self._convergence_episode(rews)
        last_n = rews[-min(self.LAST_N, n):]
        first_n = rews[: min(self.LAST_N, n)]
        mu_f, sig_f = float(np.mean(first_n)), float(np.std(first_n))
        mu_l, sig_l = float(np.mean(last_n)), float(np.std(last_n))
        cv_f = sig_f / max(abs(mu_f), 1e-9) * 100.0
        cv_l = sig_l / max(abs(mu_l), 1e-9) * 100.0
        stability = float(1.0 - cv_l / 100.0)   # 0->1 (1=perfecto)

        log.info("=" * 70)
        log.info("[CONV] ROBUSTEZ ESTOCÁSTICA FINAL -- SAC (%d episodios)", n)
        log.info("  Primeros %d ep.: u=%8.2f  s=%7.2f  CV=%.1f%%", len(first_n), mu_f, sig_f, cv_f)
        log.info("  Últimos  %d ep.: u=%8.2f  s=%7.2f  CV=%.1f%%  StabIdx=%.4f", len(last_n), mu_l, sig_l, cv_l, stability)
        log.info("  Tendencia lineal: R2=%.4f | Episodio convergencia: %s", r2, conv_ep)
        log.info("=" * 70)

        # -- CSV por episodio ------------------------------------------
        roll_mean = self._smooth(rews, self.WINDOW)
        roll_std = self._rolling_std(rews, self.WINDOW)
        roll_cv = self._rolling_cv(rews, self.WINDOW)

        df = pd.DataFrame({
            "episodio":      self._ep_numbers,
            "timestep":      self._ep_timesteps,
            "reward":        rews,
            "rolling_mean":  roll_mean.tolist(),
            "rolling_std":   roll_std.tolist(),
            "rolling_cv_pct": roll_cv.tolist(),
        })
        # Append métricas globales al CSV
        csv_path = self.output_dir / "sac_convergencia_episodios.csv"
        df.to_csv(str(csv_path), index=False, encoding="utf-8-sig")
        log.info("[CONV] CSV convergencia: %s", csv_path)

        # -- JSON de robustez -----------------------------------------
        robustness = {
            "n_episodes":           n,
            "episode_rewards":      rews,
            "mean_reward":          float(np.mean(rews)),
            "std_reward":           float(np.std(rews)),
            "cv_reward":            float(np.std(rews) / max(abs(np.mean(rews)), 1e-9)),
            "final_mean_reward":    mu_l,
            "final_std_reward":     sig_l,
            "final_cv_pct":         cv_l,
            "stability_index":      stability,
            "trend_r2":             r2 if not np.isnan(r2) else 0.0,
            "convergence_episode":  conv_ep,
            "trend_improving":      bool(r2 > 0.3 and mu_l > mu_f),
            "best_episode":         int(np.argmax(rews)) + 1,
            "best_reward":          float(max(rews)),
        }
        rob_path = self.output_dir / "sac_robustez_estocastica.json"
        with open(rob_path, "w", encoding="utf-8") as _f:
            json.dump(robustness, _f, indent=2, ensure_ascii=False)
        log.info("[CONV] JSON robustez: %s", rob_path)


# ===================== ENTRENAMIENTO =====================


def _make_env(rebuild: bool = False):
    """Factoria de entorno para DummyVecEnv."""
    def _factory():
        return create_iquitos_env_for_sb3(rebuild=rebuild)
    return _factory


def train(total_timesteps: int = TOTAL_TIMESTEPS, rebuild_schema: bool = False) -> None:
    """Loop principal de entrenamiento SAC SB3 en entorno Iquitos EV."""
    log.info("=" * 70)
    log.info("SAC SB3 -- Iquitos PV-BESS-EV + Control Cargadores")
    log.info("PyTorch: %s | CUDA: %s | Device: %s",
             torch.__version__, torch.cuda.is_available(),
             "cuda" if torch.cuda.is_available() else "cpu")
    log.info("Timesteps: %d (%d ep × 8760 h)", total_timesteps, total_timesteps // 8760)
    log.info("Acción: [bess(-1->+1), motos_frac(0->1), mototaxis_frac(0->1)]")
    log.info("Obs: 18D (CityLearn 11D + EV state 5D + tarifa 2D)")
    log.info("=" * 70)

    # 1. Reconstruir schema si se pide
    if rebuild_schema:
        log.info("Reconstruyendo schema y ev_demand.csv desde datos OE2...")
        build_citylearn_schema()

    # 2. Crear entorno vectorizado
    log.info("Inicializando IquitosEVChargingWrapper(CityLearnEnv)...")
    env = DummyVecEnv([_make_env(rebuild=False)])

    # 2b. Validar configuración del agente
    log.info("Validando configuración del agente SAC...")
    if not validate_agent_config("SAC", num_episodes=total_timesteps // 8760,
                                  total_timesteps=total_timesteps, obs_dim=18, action_dim=3):
        log.warning("[WARN] validate_agent_config reportó advertencia -- continúa entrenamiento")

    # 3. Cargar checkpoint o crear agente nuevo
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    existing_ckpts = sorted(CHECKPOINT_DIR.glob("sac_*_steps.zip"))
    model: SAC

    if existing_ckpts:
        latest_ckpt = existing_ckpts[-1]
        log.info("Cargando checkpoint: %s", latest_ckpt)
        try:
            model = PVBESSCarSAC.load(latest_ckpt, env=env, device="auto")
            start_steps = model.num_timesteps
            log.info("Reanudando desde paso %d", start_steps)
        except Exception as e:
            log.warning("Error cargando checkpoint: %s -- iniciando nuevo", e)
            model = PVBESSCarSAC(
                env=env,
                tensorboard_log=str(TENSORBOARD_DIR),
                **SAC_HYPERPARAMS,
            )
    else:
        log.info("Creando agente PVBESSCarSAC nuevo...")
        model = PVBESSCarSAC(
            env=env,
            tensorboard_log=str(TENSORBOARD_DIR),
            **SAC_HYPERPARAMS,
        )

    log.info(
        "Parámetros del modelo: %d",
        sum(p.numel() for p in model.policy.parameters()),
    )

    # 4. Callbacks
    checkpoint_cb = CheckpointCallback(
        save_freq=CHECKPOINT_EVERY_STEPS,
        save_path=str(CHECKPOINT_DIR),
        name_prefix="sac",
        save_replay_buffer=True,
        verbose=1,
    )
    ev_metrics_cb = EVMetricsCallback(log_freq=8760, verbose=1)
    ev_metrics_cb.output_dir = RESULTS_DIR
    sac_diag_cb = SACDiagnosticsCallback(output_dir=RESULTS_DIR, verbose=0)
    convergence_cb = ConvergenceRewardsCallback(
        output_dir=RESULTS_DIR, ep_len=8760, verbose=0
    )
    callbacks = CallbackList([checkpoint_cb, ev_metrics_cb, sac_diag_cb, convergence_cb])

    # 5. Entrenamiento
    log.info("Iniciando entrenamiento SAC...")
    t0 = time.time()
    model.learn(
        total_timesteps=total_timesteps,
        callback=callbacks,
        reset_num_timesteps=False,  # acumular pasos si es resume
        tb_log_name=f"sac_{_ts}",
        progress_bar=False,
    )
    elapsed = time.time() - t0

    # 6. Guardar modelo final
    final_path = CHECKPOINT_DIR / "sac_final"
    model.save(str(final_path))
    log.info("Modelo final guardado: %s.zip", final_path)

    # 7. Validación post-entrenamiento (10 episodios determinísticos)
    log.info("=" * 70)
    log.info("VALIDACIÓN POST-ENTRENAMIENTO SAC -- 10 episodios determinísticos")
    log.info("=" * 70)
    N_VAL = 10
    val_rewards: list[float] = []
    val_co2_avoided: list[float] = []
    val_solar: list[float] = []
    val_grid: list[float] = []
    _val_env_raw = create_iquitos_env_for_sb3()
    for ep_v in range(N_VAL):
        obs_v, _ = _val_env_raw.reset()
        done_v = False
        ep_rew = 0.0
        ep_co2 = 0.0
        ep_sol = 0.0
        ep_grid = 0.0
        while not done_v:
            act_v, _ = model.predict(obs_v[np.newaxis], deterministic=True)
            obs_v, rew_v, term_v, trunc_v, info_v = _val_env_raw.step(act_v[0])
            done_v = bool(term_v) or bool(trunc_v)
            ep_rew += float(rew_v)
            ep_co2 += info_v.get("co2_reduccion_directa_kg", 0.0) + info_v.get("co2_reduccion_indirecta_kg", 0.0)
            ep_sol += info_v.get("solar_generation_kwh", 0.0)
            ep_grid += info_v.get("grid_import_kwh", 0.0)
        val_rewards.append(ep_rew)
        val_co2_avoided.append(ep_co2)
        val_solar.append(ep_sol)
        val_grid.append(ep_grid)
        log.info("  Val ep %2d/%d: reward=%8.2f | CO2_evitado=%7.1f kg | solar=%7.1f kWh",
                 ep_v + 1, N_VAL, ep_rew, ep_co2, ep_sol)
    _val_env_raw.close()
    log.info("  Validación: reward_mean=%.2f ± %.2f | CO2_mean=%.1f kg | solar_mean=%.1f kWh",
             float(np.mean(val_rewards)), float(np.std(val_rewards)),
             float(np.mean(val_co2_avoided)), float(np.mean(val_solar)))

    # 8. Guardar result_sac.json (misma estructura que train_sac.py)
    log.info("Guardando result_sac.json...")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _conv_cb = convergence_cb   # alias

    class _NumpyEncoder(json.JSONEncoder):
        def default(self, obj: Any) -> Any:
            if isinstance(obj, (np.floating, np.integer)):
                return float(obj) if isinstance(obj, np.floating) else int(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    _ep_cb = ev_metrics_cb   # alias corto
    result_summary: dict[str, Any] = {
        "timestamp":   _ts,
        "agent":       "SAC",
        "project":     "pvbesscar",
        "location":    "Iquitos, Peru",
        "co2_factor_kg_per_kwh": 0.4521,
        "training": {
            "total_timesteps":    int(model.num_timesteps),
            "episodes":           int(model.num_timesteps // 8760),
            "duration_seconds":   float(elapsed),
            "speed_steps_per_second": float(model.num_timesteps / max(elapsed, 1)),
            "device":             str("cuda" if torch.cuda.is_available() else "cpu"),
            "episodes_completed": len(_ep_cb._episodes),
            "hyperparameters":    {k: str(v) for k, v in SAC_HYPERPARAMS.items()},
        },
        "infrastructure": {
            "pv_kwp":            4050,
            "bess_kwh":          2000,
            "motos_chargers":    15,
            "mototaxis_chargers": 4,
            "total_sockets":     38,
        },
        "validation": {
            "num_episodes":         N_VAL,
            "mean_reward":          float(np.mean(val_rewards)),
            "std_reward":           float(np.std(val_rewards)),
            "mean_co2_avoided_kg":  float(np.mean(val_co2_avoided)),
            "mean_solar_kwh":       float(np.mean(val_solar)),
            "mean_grid_import_kwh": float(np.mean(val_grid)),
        },
        "training_evolution": {
            "episodes":                   _ep_cb._episodes,
            "episode_rewards":            _conv_cb._ep_rewards,
            "hist_solar_kwh":             _ep_cb._hist_solar_kwh,
            "hist_grid_import_kwh":       _ep_cb._hist_grid_import_kwh,
            "hist_bess_discharge_kwh":    _ep_cb._hist_bess_discharge_kwh,
            "hist_ev_motos_kwh":          _ep_cb._hist_ev_motos_kwh,
            "hist_ev_mototaxis_kwh":      _ep_cb._hist_ev_mototaxis_kwh,
            "hist_co2_directa_kg":        _ep_cb._hist_co2_directa_kg,
            "hist_co2_indirecta_kg":      _ep_cb._hist_co2_indirecta_kg,
            "hist_co2_neta_kg":           _ep_cb._hist_co2_neta_kg,
            "hist_co2_baseline_kg":       _ep_cb._hist_co2_baseline_kg,
            "hist_co2_control_kg":        _ep_cb._hist_co2_control_kg,
            "hist_co2_f6a_kg":            _ep_cb._hist_co2_f6a_kg,
            "hist_co2_f6b_kg":            _ep_cb._hist_co2_f6b_kg,
            "hist_co2_f6c_kg":            _ep_cb._hist_co2_f6c_kg,
            "hist_co2_f6d_kg":            _ep_cb._hist_co2_f6d_kg,
            "hist_co2_f7_kg":             _ep_cb._hist_co2_f7_kg,
            "hist_reduccion_pct":         _ep_cb._hist_reduccion_pct,
            "hist_debt_violations":       _ep_cb._hist_debt_violations,
        },
        "summary_metrics": {
            "total_co2_directa_kg":    float(sum(_ep_cb._hist_co2_directa_kg)),
            "total_co2_indirecta_kg":  float(sum(_ep_cb._hist_co2_indirecta_kg)),
            "total_co2_neta_kg":       float(sum(_ep_cb._hist_co2_neta_kg)),
            "total_solar_kwh":         float(sum(_ep_cb._hist_solar_kwh)),
            "total_grid_import_kwh":   float(sum(_ep_cb._hist_grid_import_kwh)),
            "total_ev_kwh":            float(sum(_ep_cb._hist_ev_motos_kwh) + sum(_ep_cb._hist_ev_mototaxis_kwh)),
            "total_bess_discharge_kwh": float(sum(_ep_cb._hist_bess_discharge_kwh)),
            "avg_reduccion_pct":       float(np.mean(_ep_cb._hist_reduccion_pct)) if _ep_cb._hist_reduccion_pct else 0.0,
        },
        "kpi_daily": {
            "steps":               _ep_cb._kpi_steps_history,
            "elec_consumption":    _ep_cb._elec_consumption_history,
            "elec_cost":           _ep_cb._elec_cost_history,
            "carbon_emissions":    _ep_cb._carbon_emissions_history,
            "ramping":             _ep_cb._ramping_history,
            "avg_daily_peak":      _ep_cb._avg_daily_peak_history,
            "one_minus_lf":        _ep_cb._one_minus_lf_history,
        },
        "output_files": {
            "model":       str(final_path) + ".zip",
            "trace":       str(RESULTS_DIR / "trace_sac.csv"),
            "timeseries":  str(RESULTS_DIR / "timeseries_sac.csv"),
            "result":      str(RESULTS_DIR / "result_sac.json"),
        },
    }
    result_path = RESULTS_DIR / "result_sac.json"
    with open(result_path, "w", encoding="utf-8") as _f:
        json.dump(result_summary, _f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)
    log.info("[OK] result_sac.json -> %s", result_path)

    # 9. Verificar archivos de salida
    _trace_path = RESULTS_DIR / "trace_sac.csv"
    _ts_path    = RESULTS_DIR / "timeseries_sac.csv"
    if _trace_path.exists():
        _rows = sum(1 for _ in open(_trace_path, encoding="utf-8")) - 1
        log.info("[OK] trace_sac.csv: %d registros -> %s", _rows, _trace_path)
    else:
        log.warning("[!] trace_sac.csv no generado (sin steps registrados)")
    if _ts_path.exists():
        _rows = sum(1 for _ in open(_ts_path, encoding="utf-8")) - 1
        log.info("[OK] timeseries_sac.csv: %d registros -> %s", _rows, _ts_path)
    else:
        log.warning("[!] timeseries_sac.csv no generado")

    log.info("=" * 70)
    log.info("ENTRENAMIENTO COMPLETADO en %.1f minutos", elapsed / 60)
    log.info("Pasos totales: %d  |  Episodios: %d", model.num_timesteps, len(_ep_cb._episodes))
    log.info("  [OK] %s", result_path)
    log.info("  [OK] %s", _trace_path)
    log.info("  [OK] %s", _ts_path)
    log.info("  [OK] %s.zip", final_path)
    log.info("=" * 70)


# ===================== MAIN =====================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SAC SB3 -- Iquitos PV-BESS-EV con control de cargadores EV"
    )
    parser.add_argument(
        "--timesteps", type=int, default=TOTAL_TIMESTEPS,
        help=f"Total de pasos de entrenamiento (default: {TOTAL_TIMESTEPS} = {TOTAL_TIMESTEPS // 8760} ep × 8760 h)"
    )
    parser.add_argument(
        "--rebuild-schema", action="store_true",
        help="Regenerar CSVs y ev_demand.csv desde datos OE2 aunque ya existan"
    )
    args = parser.parse_args()

    try:
        train(total_timesteps=args.timesteps, rebuild_schema=args.rebuild_schema)
    except KeyboardInterrupt:
        log.info("Entrenamiento interrumpido por usuario.")
    except Exception as exc:
        log.error("Error fatal: %s", exc, exc_info=True)
        sys.exit(1)
