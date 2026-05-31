#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
train_a2c_citylearn.py — A2C SB3 sobre CityLearn v2 (PyTorch)
=======================================================================
Entrenamiento del agente A2C usando stable-baselines3 A2C con
StableBaselines3Wrapper(CityLearnEnv) — entorno nativo CityLearn v2.

Agente: stable_baselines3.A2C (Advantage Actor-Critic, PyTorch)
Entorno: IquitosEVChargingWrapper(CityLearnEnv) — obs_dim=19, action_dim=3
Reward : CO2_DUAL_FOCUS v8.1 — pesos en src/citylearnv2/ev_charging_wrapper.py:
         direct=0.20 + indirect=0.30 + ev_complete=0.35 + bess_solar=0.07
         + solar=0.04 + grid_stable=0.02 + cost=0.02  (suma=1.00)

Diferencias con PPO:
  - A2C: on-policy, sin replay buffer, actualización paso a paso
  - Más rápido por paso pero mayor varianza
  - n_steps más pequeño para actualizaciones frecuentes

Uso:
    python scripts/train/train_a2c_citylearn.py
    python scripts/train/train_a2c_citylearn.py --timesteps 8760  # smoke test

Checkpoints: checkpoints/A2C_CityLearn/a2c_<steps>_steps.zip
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

# CUDA lazy loading
os.environ.setdefault("CUDA_MODULE_LOADING", "LAZY")
import signal as _signal
_orig = _signal.getsignal(_signal.SIGINT)
_signal.signal(_signal.SIGINT, _signal.SIG_IGN)
try:
    import torch
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
from stable_baselines3 import A2C
from stable_baselines3.common.callbacks import (
    BaseCallback,
    CallbackList,
    CheckpointCallback,
)
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

# Módulo local CityLearn v2
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

TOTAL_TIMESTEPS: int = 8_760 * 50   # 50 episodios × 8760 h/año = 438,000 steps
CHECKPOINT_EVERY_STEPS: int = 8_760  # guardar cada 1 episodio completo
CHECKPOINT_DIR: Path = _PROJECT_ROOT / "checkpoints" / "A2C_CityLearn"
LOG_DIR: Path = _PROJECT_ROOT / "logs" / "training" / "a2c_citylearn"
RESULTS_DIR: Path = _PROJECT_ROOT / "outputs" / "a2c_training"
TENSORBOARD_DIR: Path = _PROJECT_ROOT / "logs" / "tensorboard" / "a2c_citylearn"

_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── GPU optimizations ────────────────────────────────────────────────────────
# TF32 acelera matmul ~5-10x en Ampere/Ada (RTX 30xx/40xx) sin perdida de precision
if _DEVICE == "cuda":
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.benchmark = True       # auto-tune kernels al primer forward
    torch.backends.cudnn.deterministic = False   # no forzar determinismo = mas rapido
    _gpu_name = torch.cuda.get_device_name(0)
    _gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    _cuda_ver: str | None = getattr(torch.version, "cuda", None)
    print(f"GPU: {_gpu_name}")
    print(f"   VRAM: {_gpu_mem_gb:.1f} GB | CUDA: {_cuda_ver}")
    print("   [GPU MAX] TF32 ON | cuDNN benchmark ON | deterministic OFF")
else:
    print("CPU mode -- GPU no disponible, entrenamiento mas lento")
# ─────────────────────────────────────────────────────────────────────────────

# Hiperparámetros A2C optimizados para sistema Iquitos PV-BESS-EV
# A2C: on-policy, sin buffer, actualizaciones frecuentes (menor varianza que PPO)
# Refs: Mnih et al 2016 A3C; SB3 A2C documentation
A2C_HYPERPARAMS: dict = {
    "policy": "MlpPolicy",
    # n_steps=512: rollout corto para A2C (mejor varianza que n_steps=2048)
    # A2C actualiza cada 512 steps (~1/17 episodio); mucho más gradientes por ep
    "n_steps": 512,
    # gamma=0.90: compromiso entre 0.88 (PPO) y 0.99 (SAC off-policy)
    # A2C es on-policy pero con rollouts cortos, horizonte efectivo ~5 pasos
    "gamma": 0.90,
    # gae_lambda=0.95: estimación del advantage (Schulman 2017)
    "gae_lambda": 0.95,      # Cambiado de 1.0 (TD puro) a 0.95 (GAE estándar)
    "ent_coef": 0.01,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    # lr=7e-4: A2C requiere lr más alto que PPO (actualizaciones más frecuentes)
    "learning_rate": 7e-4,
    "policy_kwargs": {
        # Red más grande para reward multi-objetivo (igual a PPO)
        "net_arch": dict(
            pi=[256, 256, 128],   # Actor
            vf=[512, 512, 256],   # Critic
        ),
        "activation_fn": torch.nn.Tanh,  # Tanh para salidas acotadas
    },
    "verbose": 1,
    "device": _DEVICE,
}

# ===================== LOGGING =====================

LOG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / f"a2c_citylearn_{_ts}.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ===================== CALLBACKS =====================


class CO2MetricsCallback(BaseCallback):
    """Registra métricas de CO₂ y solar cada N steps."""

    def __init__(self, log_every_steps: int = 8760, verbose: int = 0) -> None:
        super().__init__(verbose)
        self._log_every = log_every_steps
        self._step_rewards: list[float] = []
        self._ep_metrics: list[dict] = []
        self._last_log_step: int = 0

    def _on_step(self) -> bool:
        if "rewards" in self.locals:
            r = self.locals["rewards"]
            self._step_rewards.append(float(np.mean(r)))

        # Loguear cada episodio completo
        if (self.num_timesteps - self._last_log_step) >= self._log_every:
            if self._step_rewards:
                window_reward = float(np.sum(self._step_rewards))
                self._step_rewards.clear()
                ep_num = self.num_timesteps // self._log_every

                self.logger.record("train/window_reward_sum", window_reward)
                log.info(
                    "Ep~%d | steps=%d | reward_sum=%.4f",
                    ep_num, self.num_timesteps, window_reward,
                )
                self._ep_metrics.append({
                    "timestep": self.num_timesteps,
                    "episode": ep_num,
                    "reward_sum": window_reward,
                })
            self._last_log_step = self.num_timesteps

        return True

    def get_metrics(self) -> list[dict]:
        return self._ep_metrics


class EVMetricsCallback(BaseCallback):
    """Callback que registra métricas de EV y CO₂ durante el entrenamiento A2C.

    Implementa las 3 Fórmulas OE3 + F6/F7/F8 (solar + BESS):

    FÓRMULA 1 — BASELINE (sin solar, sin BESS, sin agente RL):
        CO₂_base = EV_motos×0.87 + EV_mototaxis×0.54 + Mall×0.4521

    FÓRMULA 2 — CONTROL INTELIGENTE (con solar+BESS+agente RL):
        CO₂_ctrl = grid_import × 0.4521  (solo importación residual)

    FÓRMULA 3 — REDUCCIÓN NETA OE3:
        CO₂_directa  = EV_cargados×0.87 + EV_taxi_cargados×0.54
        CO₂_indirecta = Fórmula1 − Fórmula2
        CO₂_total    = directa + indirecta

    F6 (solar, por fase dispatcher):
        F6a: solar → EVs  |  F6b: solar → Mall
        F6c: solar → BESS |  F6d: solar → export (=F8)

    F7: BESS descarga → desplaza red diesel (kWh × 0.4521)
    """

    def __init__(self, log_freq: int = 8760, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.log_freq = log_freq
        # ── Acumuladores EV ──────────────────────────────────────────────
        self._ep_ev_motos_kwh: float = 0.0
        self._ep_ev_mototaxis_kwh: float = 0.0
        self._ep_ev_motos_demand_kwh: float = 0.0
        self._ep_ev_mototaxis_demand_kwh: float = 0.0
        self._ep_debt_violations: int = 0
        # ── Acumuladores balance energético ───────────────────────────────
        self._ep_solar_kwh: float = 0.0
        self._ep_bess_discharge_kwh: float = 0.0
        self._ep_bess_charge_kwh: float = 0.0
        self._ep_grid_import_kwh: float = 0.0
        self._ep_mall_kwh: float = 0.0
        # ── Acumuladores F6 (solar por fase) ──────────────────────────────
        self._ep_co2_f6a_kg: float = 0.0   # F6a: solar → EVs
        self._ep_co2_f6b_kg: float = 0.0   # F6b: solar → Mall
        self._ep_co2_f6c_kg: float = 0.0   # F6c: solar → BESS
        self._ep_co2_f6d_kg: float = 0.0   # F6d=F8: solar → export
        self._ep_co2_f6_total_kg: float = 0.0
        # ── Acumuladores F7 (BESS descarga) ──────────────────────────────
        self._ep_co2_f7_kg: float = 0.0
        # ── Acumuladores 3 fórmulas OE3 ──────────────────────────────────
        # ── Historiales por episodio (para gráficas) ────────────────────
        self._episodes: list[int] = []
        self._hist_ev_motos_kwh: list[float] = []
        self._hist_ev_mototaxis_kwh: list[float] = []
        self._hist_ev_motos_demand_kwh: list[float] = []
        self._hist_ev_mototaxis_demand_kwh: list[float] = []
        self._hist_debt_violations: list[float] = []
        self._hist_solar_kwh: list[float] = []
        self._hist_bess_discharge_kwh: list[float] = []
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
        # ── KPI tracking (ventana 24 pasos = 1 día) ────────────────────
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
        # ── Trace/timeseries step-level (sincronizado con train_a2c.py) ──
        self.trace_records: list[dict] = []
        self.timeseries_records: list[dict] = []
        self._step_in_ep: int = 0
        self._ep_count: int = 0
        self._ep_co2_baseline_kg: float = 0.0
        self._ep_co2_control_kg: float = 0.0
        self._ep_co2_directa_kg: float = 0.0
        self._ep_co2_indirecta_kg: float = 0.0
        self._ep_co2_neta_kg: float = 0.0
        self._ep_co2_sinproyecto_kg: float = 0.0
        self._ep_co2_sinproyecto_mall_kg: float = 0.0
        self._ep_co2_sinproyecto_combustion_kg: float = 0.0
        # ── Historiales por episodio (para gráficas) ────────────────────
        self._episodes: list[int] = []
        self._hist_ev_motos_kwh: list[float] = []
        self._hist_ev_mototaxis_kwh: list[float] = []
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
        # ── KPI tracking (ventana 24 pasos = 1 día) ────────────────────
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

    def _reset_ep(self) -> None:
        self._ep_ev_motos_kwh = 0.0
        self._ep_ev_mototaxis_kwh = 0.0
        self._ep_ev_motos_demand_kwh = 0.0
        self._ep_ev_mototaxis_demand_kwh = 0.0
        self._ep_debt_violations = 0
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
        if self.locals.get("infos"):
            for info in self.locals["infos"]:
                # EV
                self._ep_ev_motos_kwh            += info.get("ev_motos_actual_kwh", 0.0)
                self._ep_ev_mototaxis_kwh        += info.get("ev_mototaxis_actual_kwh", 0.0)
                self._ep_ev_motos_demand_kwh     += info.get("ev_motos_demand_kwh", 0.0)
                self._ep_ev_mototaxis_demand_kwh += info.get("ev_mototaxis_demand_kwh", 0.0)
                if info.get("penalty_debt_frac", 0.0) > 0.1:
                    self._ep_debt_violations += 1
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

                # ── KPI ventana 24h ───────────────────────────────────
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

                # ── Trace/timeseries step-level ───────────────────────────
                self._step_in_ep += 1
                _rew = float(self.locals["rewards"][0]) if self.locals.get("rewards") is not None else 0.0
                _ev_kwh = _ev
                self.trace_records.append({
                    "timestep":            self.n_calls,
                    "episode":             self._ep_count,
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
                    "motos_charging":      info.get("motos_charging", 0),
                    "mototaxis_charging":  info.get("mototaxis_charging", 0),
                })
                self.timeseries_records.append({
                    "timestep":            self.n_calls,
                    "episode":             self._ep_count,
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

        # Calcular KPI por ventana de 24h
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

        # ── Log intra-episodio cada 10% del episodio (~876 pasos ≈ 36 días) ────────
        _INTRA_FREQ = max(1, self.log_freq // 10)
        if (
            0 < self._step_in_ep < self.log_freq
            and self._step_in_ep % _INTRA_FREQ == 0
        ):
            _pct_ep  = self._step_in_ep / self.log_freq * 100.0
            _scale   = self.log_freq / self._step_in_ep
            _f0_ann  = self._ep_co2_sinproyecto_kg * _scale
            _f1_ann  = self._ep_co2_baseline_kg    * _scale
            _f2_ann  = self._ep_co2_control_kg     * _scale
            _f0f2_pct = (
                (_f0_ann - _f2_ann) / _f0_ann * 100.0
                if _f0_ann > 0.0 else 0.0
            )
            _cur_ep = self.n_calls // self.log_freq + 1
            log.info(
                "[CO₂ %5.1f%%ep] Ep %d │ F0=%.0f │ F1=%.0f │ F2(A2C)=%.0f kg/año (★proyectado) "
                "│ vs F0: -%.1f%%",
                _pct_ep, _cur_ep, _f0_ann, _f1_ann, _f2_ann, _f0f2_pct,
            )

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
            log.info("─" * 70)
            _bess_d_ep1   = self._hist_bess_discharge_kwh[0] if self._hist_bess_discharge_kwh else self._ep_bess_discharge_kwh
            _bess_c_ep1   = self._hist_bess_charge_kwh[0]    if self._hist_bess_charge_kwh    else self._ep_bess_charge_kwh
            _grid_ep1     = self._hist_grid_import_kwh[0]    if self._hist_grid_import_kwh    else self._ep_grid_import_kwh
            _f6a_ep1      = self._hist_co2_f6a_kg[0]         if self._hist_co2_f6a_kg         else self._ep_co2_f6a_kg
            _f6c_ep1      = self._hist_co2_f6c_kg[0]         if self._hist_co2_f6c_kg         else self._ep_co2_f6c_kg
            _bess_net     = self._ep_bess_discharge_kwh - self._ep_bess_charge_kwh
            _bess_net_ep1 = _bess_d_ep1 - _bess_c_ep1
            def _dlt(cur: float, ep1: float) -> str:
                return f"{cur - ep1:+.0f}"
            log.info(
                "Ep %d │ BALANCE ENERGÉTICO ANUAL (kWh) — [CSV]=fijo │ [A2C]=decisión agente",
                ep_num,
            )
            log.info(
                "  [CSV] Solar      = %9.0f kWh │ Mall         = %9.0f kWh",
                self._ep_solar_kwh, self._ep_mall_kwh,
            )
            log.info(
                "  [CSV] EV motos demanda  =%9.0f kWh │ EV mototaxis demanda  =%9.0f kWh  (estocástico ±15%%/día)",
                self._ep_ev_motos_demand_kwh, self._ep_ev_mototaxis_demand_kwh,
            )
            log.info(
                "  [A2C] EV motos entregado=%9.0f kWh Δ=%+.0f kWh │ mototaxis entregado=%9.0f kWh Δ=%+.0f kWh │ debt_viols=%d",
                self._ep_ev_motos_kwh,
                self._ep_ev_motos_kwh - self._ep_ev_motos_demand_kwh,
                self._ep_ev_mototaxis_kwh,
                self._ep_ev_mototaxis_kwh - self._ep_ev_mototaxis_demand_kwh,
                self._ep_debt_violations,
            )
            log.info(
                "  [A2C] BESS_disch = %9.0f kWh │ BESS_carga   = %9.0f kWh │ BESS_neto= %+.0f kWh",
                self._ep_bess_discharge_kwh, self._ep_bess_charge_kwh, _bess_net,
            )
            log.info(
                "  [A2C] BESS_disch Δ vs Ep1 = %s kWh │ BESS_carga Δ = %s kWh │ BESS_neto Δ = %s kWh",
                _dlt(self._ep_bess_discharge_kwh, _bess_d_ep1),
                _dlt(self._ep_bess_charge_kwh, _bess_c_ep1),
                _dlt(_bess_net, _bess_net_ep1),
            )
            log.info(
                "  [A2C] Grid_import= %9.0f kWh │ Δ vs Ep1 = %s kWh",
                self._ep_grid_import_kwh, _dlt(self._ep_grid_import_kwh, _grid_ep1),
            )
            log.info(
                "  [A2C] F6a(solar→EV)= %.0f kg CO₂ Δ=%s │ F6c(solar→BESS)= %.0f kg CO₂ Δ=%s",
                self._ep_co2_f6a_kg, _dlt(self._ep_co2_f6a_kg, _f6a_ep1),
                self._ep_co2_f6c_kg, _dlt(self._ep_co2_f6c_kg, _f6c_ep1),
            )
            log.info(
                "  [FIS] NOTA: Grid_import anual cambia lento porque "
                "BESS_neto≈0 (energía conservada). El agente mejora CUÁNDO "
                "se usa la energía (peak-shaving), no el total kWh anual.",
            )
            log.info("═" * 70)
            log.info("Ep %d │ TABLA CO₂ vs ESTADO ACTUAL — OE2/OE3 PVBESSCAR", ep_num)
            log.info(
                "  [NOTA] F0/F1 son REFERENCIAS DETERMINISTAS (mismo perfil CSV/año). "
                "Solo F2 varía con las decisiones del agente A2C."
            )
            log.info(
                "  F0 SIN PROYECTO │ %10.0f kg/año │ REFERENCIA fija"
                " (1,385 motos+200 mototaxis ICE/día — OE2: 900+130 punta=65%%)",
                self._ep_co2_sinproyecto_kg,
            )
            log.info(
                "  F1 BASELINE     │ %10.0f kg/año │ vs F0: -%6.1f%%"
                " │ REFERENCIA fija (sin solar, sin BESS, sin RL)",
                self._ep_co2_baseline_kg, f0_vs_baseline_pct,
            )
            _f2_ep1 = self._hist_co2_control_kg[0] if self._hist_co2_control_kg else self._ep_co2_control_kg
            _f2_delta = _f2_ep1 - self._ep_co2_control_kg
            _f2_delta_pct = _f2_delta / _f2_ep1 * 100.0 if _f2_ep1 > 0.0 else 0.0
            _trend_sym = "▼" if _f2_delta > 0.0 else ("▲" if _f2_delta < 0.0 else "═")
            log.info(
                "  F2 CTRL A2C     │ %10.0f kg/año │ vs F0: -%6.1f%%"
                " │ %s vs Ep1: %+.0f kg (%+.2f%%)",
                self._ep_co2_control_kg, f0_vs_ctrl_pct,
                _trend_sym, -_f2_delta, -_f2_delta_pct,
            )
            log.info(
                "  Grid_import: %.0f kWh/año → principal palanca de F2"
                " │ BESS_disch: %.0f kWh/año",
                self._ep_grid_import_kwh, self._ep_bess_discharge_kwh,
            )
            log.info(
                "  NETA F0→F2: %.0f kg/año evitados (%.1f%%)"
                " │ directa: %.0f kg │ indirecta: %.0f kg",
                self._ep_co2_sinproyecto_kg - self._ep_co2_control_kg,
                f0_vs_ctrl_pct,
                self._ep_co2_directa_kg, self._ep_co2_indirecta_kg,
            )
            log.info("─" * 70)

            # ── TensorBoard ─────────────────────────────────────────────────────────────
            self.logger.record("ev/motos_kwh", self._ep_ev_motos_kwh)
            self.logger.record("ev/mototaxis_kwh", self._ep_ev_mototaxis_kwh)
            self.logger.record("ev/debt_violations", self._ep_debt_violations)
            self.logger.record("energy/solar_kwh", self._ep_solar_kwh)
            self.logger.record("energy/bess_discharge_kwh", self._ep_bess_discharge_kwh)
            self.logger.record("energy/grid_import_kwh", self._ep_grid_import_kwh)
            self.logger.record("energy/mall_kwh", self._ep_mall_kwh)
            self.logger.record("co2/f6_total_kg", self._ep_co2_f6_total_kg)
            self.logger.record("co2/f6a_ev_kg", self._ep_co2_f6a_kg)
            self.logger.record("co2/f6b_mall_kg", self._ep_co2_f6b_kg)
            self.logger.record("co2/f6c_bess_kg", self._ep_co2_f6c_kg)
            self.logger.record("co2/f6d_export_kg", self._ep_co2_f6d_kg)
            self.logger.record("co2/f7_bess_kg", self._ep_co2_f7_kg)
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

            # ── Historia por episodio ──────────────────────────────
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

            # ── Flush periódico cada 5 episodios — protege contra pérdida de datos ──
            _FLUSH_EVERY = 5
            if ep_num % _FLUSH_EVERY == 0 and ep_num > 0:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                if self.trace_records:
                    _tp = self.output_dir / "trace_a2c.csv"
                    _hdr = not _tp.exists()
                    pd.DataFrame(self.trace_records).to_csv(_tp, mode="a", index=False, header=_hdr)
                    self.trace_records = []
                    log.info("[DATA] trace_a2c.csv: flush ep%d (%d pasos)", ep_num, ep_num * 8760)
                if self.timeseries_records:
                    _tsp = self.output_dir / "timeseries_a2c.csv"
                    _hdr = not _tsp.exists()
                    pd.DataFrame(self.timeseries_records).to_csv(_tsp, mode="a", index=False, header=_hdr)
                    self.timeseries_records = []
                    log.info("[DATA] timeseries_a2c.csv: flush ep%d", ep_num)

            self._reset_ep()

        return True

    def on_training_end(self) -> None:
        """Genera todas las gráficas al finalizar el entrenamiento A2C."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # ── Flush final trace/timeseries ──────────────────────────────────────────
        if self.trace_records:
            _tp = self.output_dir / "trace_a2c.csv"
            _hdr = not _tp.exists()
            pd.DataFrame(self.trace_records).to_csv(_tp, mode="a", index=False, header=_hdr)
            self.trace_records = []
            log.info("[DATA] trace_a2c.csv: flush final")
        if self.timeseries_records:
            _tsp = self.output_dir / "timeseries_a2c.csv"
            _hdr = not _tsp.exists()
            pd.DataFrame(self.timeseries_records).to_csv(_tsp, mode="a", index=False, header=_hdr)
            self.timeseries_records = []
            log.info("[DATA] timeseries_a2c.csv: flush final")
        if len(self._episodes) > 1:
            log.info("[GRAPH] Generando gráficas de episodios OE3 A2C...")
            self._generate_ev_plots()
        if len(self._kpi_steps_history) > 1:
            log.info("[GRAPH] Generando gráficas KPI diarios A2C...")
            self._generate_kpi_graphs()
        log.info("[GRAPH] ✓ Gráficas A2C guardadas en: %s", self.output_dir)

    # ─────────────────────────────────────────────────────────────────────
    # Plotting helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _smooth(data: list[float], window: int = 5) -> list[float]:
        """Suavizado con media móvil."""
        if len(data) < 2:
            return data
        return pd.Series(data).rolling(window=window, min_periods=1).mean().tolist()

    def _generate_ev_plots(self) -> None:
        """Genera 3 dashboards de métricas OE3 por episodio."""
        eps = self._episodes
        sm = self._smooth

        # ── Dashboard 1: CO₂ reducción OE3 ────────────────────────
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("A2C — CO₂ Reducción OE3 por Episodio", fontsize=14, fontweight="bold")
        ax = axes[0, 0]
        ax.plot(eps, self._hist_co2_baseline_kg, "b-", alpha=0.3, label="Baseline")
        ax.plot(eps, sm(self._hist_co2_baseline_kg), "b-", linewidth=2)
        ax.plot(eps, self._hist_co2_control_kg, "r-", alpha=0.3, label="Control")
        ax.plot(eps, sm(self._hist_co2_control_kg), "r-", linewidth=2)
        ax.set_title("CO₂ Baseline vs Control (kg/año)"); ax.set_xlabel("Episodio"); ax.set_ylabel("kg CO₂")
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
        ax = axes[0, 1]
        ax.plot(eps, self._hist_co2_neta_kg, "g-", alpha=0.3)
        ax.plot(eps, sm(self._hist_co2_neta_kg), "g-", linewidth=2)
        ax.set_title("CO₂ Neta Evitada OE3 (kg/año)"); ax.set_xlabel("Episodio"); ax.set_ylabel("kg CO₂")
        ax.grid(True, alpha=0.3)
        ax = axes[0, 2]
        ax.plot(eps, self._hist_reduccion_pct, "purple", alpha=0.3)
        ax.plot(eps, sm(self._hist_reduccion_pct), "purple", linewidth=2)
        ax.axhline(y=0, color="k", linestyle="--", alpha=0.5)
        ax.set_title("% Reducción CO₂ OE3"); ax.set_xlabel("Episodio"); ax.set_ylabel("%")
        ax.grid(True, alpha=0.3)
        ax = axes[1, 0]
        ax.plot(eps, sm(self._hist_co2_directa_kg), "orange", linewidth=2, label="Directa")
        ax.plot(eps, sm(self._hist_co2_indirecta_kg), "brown", linewidth=2, label="Indirecta")
        ax.set_title("CO₂ Directa vs Indirecta (kg/año)"); ax.set_xlabel("Episodio"); ax.set_ylabel("kg CO₂")
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
        ax = axes[1, 1]
        ax.stackplot(eps, self._hist_co2_f6a_kg, self._hist_co2_f6b_kg,
                     self._hist_co2_f6c_kg, self._hist_co2_f6d_kg,
                     labels=["F6a EV", "F6b Mall", "F6c BESS", "F6d Export"],
                     colors=["#2ca02c", "#1f77b4", "#ff7f0e", "#9467bd"], alpha=0.7)
        ax.set_title("CO₂ por Fase Solar F6 (kg/año)"); ax.set_xlabel("Episodio"); ax.set_ylabel("kg CO₂")
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
        ax = axes[1, 2]
        ax.plot(eps, sm(self._hist_co2_f7_kg), "teal", linewidth=2, label="F7 BESS")
        ax.set_title("CO₂ Evitado BESS F7 (kg/año)"); ax.set_xlabel("Episodio"); ax.set_ylabel("kg CO₂")
        ax.legend(); ax.grid(True, alpha=0.3)
        plt.tight_layout()
        p = self.output_dir / "a2c_co2_oe3_episodios.png"
        fig.savefig(str(p), dpi=120, bbox_inches="tight"); plt.close(fig)
        log.info("[GRAPH] Guardado: %s", p)

        # ── Dashboard 2: Balance energético ────────────────────────
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("A2C — Balance Energético por Episodio", fontsize=14, fontweight="bold")
        panels = [
            (axes[0, 0], sm(self._hist_solar_kwh), "gold", "Solar PV", "Generación Solar (kWh/año)"),
            (axes[0, 1], sm(self._hist_bess_discharge_kwh), "orange", "BESS descarga", "BESS Descarga (kWh/año)"),
            (axes[0, 2], sm(self._hist_grid_import_kwh), "red", "Grid import", "Importación Red (kWh/año)"),
            (axes[1, 0], sm(self._hist_mall_kwh), "gray", "Mall", "Demanda Mall (kWh/año)"),
        ]
        for ax, data, color, label, title in panels:
            ax.plot(eps, data, color=color, linewidth=2, label=label)
            ax.set_title(title); ax.set_xlabel("Episodio"); ax.set_ylabel("kWh")
            ax.legend(); ax.grid(True, alpha=0.3)
        ax = axes[1, 1]
        ax.plot(eps, sm(self._hist_ev_motos_kwh), "blue", linewidth=2, label="Motos")
        ax.plot(eps, sm(self._hist_ev_mototaxis_kwh), "cyan", linewidth=2, label="Mototaxis")
        ax.set_title("Carga EV (kWh/año)"); ax.set_xlabel("Episodio"); ax.set_ylabel("kWh")
        ax.legend(); ax.grid(True, alpha=0.3)
        ax = axes[1, 2]
        ax.stackplot(eps, self._hist_solar_kwh, self._hist_bess_discharge_kwh,
                     labels=["Solar", "BESS"], colors=["gold", "orange"], alpha=0.7)
        ax.plot(eps, sm(self._hist_grid_import_kwh), "r-", linewidth=2, label="Grid")
        ax.set_title("Solar+BESS vs Importación"); ax.set_xlabel("Episodio"); ax.set_ylabel("kWh/año")
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
        plt.tight_layout()
        p = self.output_dir / "a2c_balance_energetico_episodios.png"
        fig.savefig(str(p), dpi=120, bbox_inches="tight"); plt.close(fig)
        log.info("[GRAPH] Guardado: %s", p)

        # ── Dashboard 3: EV & operación ───────────────────────────
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle("A2C — Métricas EV por Episodio", fontsize=14, fontweight="bold")
        axes[0].plot(eps, sm(self._hist_ev_motos_kwh), "blue", linewidth=2, label="Motos")
        axes[0].plot(eps, sm(self._hist_ev_mototaxis_kwh), "cyan", linewidth=2, label="Mototaxis")
        axes[0].set_title("Energía Cargada EV (kWh/año)"); axes[0].set_xlabel("Episodio")
        axes[0].legend(); axes[0].grid(True, alpha=0.3)
        axes[1].plot(eps, self._hist_debt_violations, "red", linewidth=2, marker="o", ms=4)
        axes[1].set_title("Violaciones Deuda EV"); axes[1].set_xlabel("Episodio")
        axes[1].set_ylabel("nº violaciones"); axes[1].grid(True, alpha=0.3)
        axes[2].plot(eps, sm(self._hist_reduccion_pct), "purple", linewidth=2)
        axes[2].axhline(y=0, color="k", linestyle="--", alpha=0.5)
        axes[2].fill_between(eps, [max(v, 0) for v in sm(self._hist_reduccion_pct)],
                             alpha=0.2, color="green")
        axes[2].set_title("% Reducción CO₂ OE3"); axes[2].set_xlabel("Episodio")
        axes[2].set_ylabel("%"); axes[2].grid(True, alpha=0.3)
        plt.tight_layout()
        p = self.output_dir / "a2c_ev_metricas_episodios.png"
        fig.savefig(str(p), dpi=120, bbox_inches="tight"); plt.close(fig)
        log.info("[GRAPH] Guardado: %s", p)

        # ── CSV histórico ────────────────────────────────────────────
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
        csv_p = self.output_dir / "a2c_episodios_history.csv"
        df.to_csv(str(csv_p), index=False)
        log.info("[GRAPH] CSV histórico: %s", csv_p)

    def _generate_kpi_graphs(self) -> None:
        """Genera 7 gráficas KPI CityLearn + dashboard."""
        steps_k = [s / 1000.0 for s in self._kpi_steps_history]
        sm = self._smooth

        def _save(fig: _mpl_fig.Figure, name: str) -> None:
            p = self.output_dir / name
            fig.savefig(str(p), dpi=120, bbox_inches="tight")
            plt.close(fig)
            log.info("[KPI] Guardado: %s", p)

        for data, name, label, color in [
            (self._elec_consumption_history, "kpi_electricity_consumption.png", "Consumo Elec. (kWh/día)", "blue"),
            (self._elec_cost_history, "kpi_electricity_cost.png", "Costo Elec. (USD/día)", "green"),
            (self._carbon_emissions_history, "kpi_carbon_emissions.png", "Emisiones CO₂ (kg/día)", "brown"),
            (self._ramping_history, "kpi_ramping.png", "Ramping (kW)", "purple"),
            (self._avg_daily_peak_history, "kpi_daily_peak.png", "Pico Diario (kW)", "red"),
        ]:
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(steps_k, data, color=color, alpha=0.4, label="Raw")
            ax.plot(steps_k, sm(data), color=color, linewidth=2, label="Suavizado")
            ax.set_ylim(bottom=0)
            ax.set_title(f"A2C KPI: {label}")
            ax.set_xlabel("Miles de pasos"); ax.set_ylabel(label)
            ax.legend(); ax.grid(True, alpha=0.3)
            _save(fig, name)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self._one_minus_lf_history, "orange", alpha=0.4, label="1-LF raw")
        _lf_sm = sm(self._one_minus_lf_history)
        ax.plot(steps_k, _lf_sm, "orange", linewidth=2, label="Suavizado")
        ax.axhline(y=0.3, color="green", linestyle="--", alpha=0.7, label="Objetivo < 0.3")
        ax.fill_between(steps_k, _lf_sm, 0.3, where=[v < 0.3 for v in _lf_sm], alpha=0.2, color="green")
        ax.set_ylim(0, 1); ax.set_title("A2C KPI: 1 − Load Factor")
        ax.set_xlabel("Miles de pasos"); ax.legend(); ax.grid(True, alpha=0.3)
        _save(fig, "kpi_load_factor.png")

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("A2C — Dashboard KPI CityLearn", fontsize=14, fontweight="bold")
        kpi_list = [
            (self._elec_consumption_history, "Consumo elec. (kWh/día)", "blue"),
            (self._elec_cost_history, "Costo elec. (USD/día)", "green"),
            (self._carbon_emissions_history, "Emisiones CO₂ (kg/día)", "brown"),
            (self._ramping_history, "Ramping (kW)", "purple"),
            (self._avg_daily_peak_history, "Pico diario (kW)", "red"),
            (self._one_minus_lf_history, "1 − Load Factor", "orange"),
        ]
        for idx, (data, title, color) in enumerate(kpi_list):
            ax = axes[idx // 3][idx % 3]
            ax.plot(steps_k, sm(data), color=color, linewidth=2)
            ax.set_title(title); ax.set_xlabel("Miles pasos"); ax.grid(True, alpha=0.3)
        plt.tight_layout()
        _save(fig, "kpi_dashboard.png")


# ===================== A2C DIAGNOSTICS CALLBACK =====================

class A2CDiagnosticsCallback(BaseCallback):
    """Registra métricas internas del optimizador A2C para gráficas diagnósticas."""

    def __init__(self, output_dir: Path, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.output_dir = output_dir
        self.steps_history: list[int] = []
        self.entropy_history: list[float] = []
        self.policy_loss_history: list[float] = []
        self.value_loss_history: list[float] = []
        self.explained_var_history: list[float] = []
        self.grad_norm_history: list[float] = []

    def _on_step(self) -> bool:
        return True

    def _on_rollout_end(self) -> None:
        """Leer métricas del logger SB3 tras cada rollout."""
        try:
            kv = self.model.logger.name_to_value
            ent = kv.get("train/entropy_loss", None)
            ploss = kv.get("train/policy_gradient_loss", None)
            vloss = kv.get("train/value_loss", None)
            ev = kv.get("train/explained_variance", None)
            gn = kv.get("train/grad_norm", None)
            if ent is not None or vloss is not None:
                self.steps_history.append(self.num_timesteps)
                self.entropy_history.append(float(ent) if ent is not None else 0.0)
                self.policy_loss_history.append(float(ploss) if ploss is not None else 0.0)
                self.value_loss_history.append(float(vloss) if vloss is not None else 0.0)
                self.explained_var_history.append(float(ev) if ev is not None else 0.0)
                self.grad_norm_history.append(float(gn) if gn is not None else 0.0)
        except Exception:
            pass

    def on_training_end(self) -> None:
        """Genera gráficas diagnósticas A2C."""
        if len(self.steps_history) < 2:
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        steps_k = [s / 1000.0 for s in self.steps_history]
        sm = lambda data, w=5: pd.Series(data).rolling(window=w, min_periods=1).mean().tolist()

        def _save(fig: _mpl_fig.Figure, name: str) -> None:
            p = self.output_dir / name
            fig.savefig(str(p), dpi=120, bbox_inches="tight")
            plt.close(fig)
            log.info("[A2C-DIAG] Guardado: %s", p)

        # Entropy
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self.entropy_history, "purple", alpha=0.4, label="Entropy raw")
        ax.plot(steps_k, sm(self.entropy_history), "purple", linewidth=2, label="Suavizado")
        ax.axhline(y=0.1, color="red", linestyle="--", alpha=0.7, label="Colapso < 0.1")
        ax.axhspan(ymin=float("-inf"), ymax=0.1, alpha=0.1, color="red")
        ax.set_title("A2C: Entropía"); ax.set_xlabel("Miles pasos"); ax.set_ylabel("Entropía")
        ax.legend(); ax.grid(True, alpha=0.3)
        _save(fig, "a2c_entropy.png")

        # Policy loss
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self.policy_loss_history, "green", alpha=0.4, label="Policy loss raw")
        ax.plot(steps_k, sm(self.policy_loss_history), "green", linewidth=2, label="Suavizado")
        ax.set_title("A2C: Policy Loss"); ax.set_xlabel("Miles pasos"); ax.set_ylabel("Loss")
        ax.legend(); ax.grid(True, alpha=0.3)
        _save(fig, "a2c_policy_loss.png")

        # Value loss
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self.value_loss_history, "red", alpha=0.4, label="Value loss raw")
        ax.plot(steps_k, sm(self.value_loss_history), "red", linewidth=2, label="Suavizado")
        ax.set_title("A2C: Value Loss"); ax.set_xlabel("Miles pasos"); ax.set_ylabel("Loss")
        ax.legend(); ax.grid(True, alpha=0.3)
        _save(fig, "a2c_value_loss.png")

        # Explained variance
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(steps_k, self.explained_var_history, "teal", alpha=0.4, label="EV raw")
        ax.plot(steps_k, sm(self.explained_var_history), "teal", linewidth=2, label="Suavizado")
        ax.axhline(y=0.5, color="green", linestyle="--", alpha=0.7, label="Objetivo > 0.5")
        ax.fill_between(steps_k, [max(v, 0.5) for v in sm(self.explained_var_history)],
                        0.5, alpha=0.15, color="green")
        ax.set_ylim(-1, 1.1); ax.set_title("A2C: Explained Variance")
        ax.set_xlabel("Miles pasos"); ax.legend(); ax.grid(True, alpha=0.3)
        _save(fig, "a2c_explained_variance.png")

        # Grad norm
        if any(v > 0 for v in self.grad_norm_history):
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(steps_k, self.grad_norm_history, "orange", alpha=0.4, label="Grad norm raw")
            ax.plot(steps_k, sm(self.grad_norm_history), "orange", linewidth=2, label="Suavizado")
            ax.set_title("A2C: Grad Norm"); ax.set_xlabel("Miles pasos"); ax.set_ylabel("Norma gradiente")
            ax.legend(); ax.grid(True, alpha=0.3)
            _save(fig, "a2c_grad_norm.png")

        # Dashboard 2×3
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("A2C — Diagnósticos del Optimizador", fontsize=14, fontweight="bold")
        for ax, data, title, color in [
            (axes[0, 0], self.entropy_history, "Entropía", "purple"),
            (axes[0, 1], self.policy_loss_history, "Policy Loss", "green"),
            (axes[0, 2], self.value_loss_history, "Value Loss", "red"),
            (axes[1, 0], self.explained_var_history, "Explained Variance", "teal"),
            (axes[1, 1], self.grad_norm_history, "Grad Norm", "orange"),
        ]:
            ax.plot(steps_k, sm(data), color=color, linewidth=2)
            ax.set_title(title); ax.set_xlabel("Miles pasos"); ax.grid(True, alpha=0.3)
        axes[1, 2].axis("off")
        plt.tight_layout()
        _save(fig, "a2c_dashboard.png")

        # CSV
        df = pd.DataFrame({
            "timestep": self.steps_history,
            "entropy": self.entropy_history,
            "policy_loss": self.policy_loss_history,
            "value_loss": self.value_loss_history,
            "explained_variance": self.explained_var_history,
            "grad_norm": self.grad_norm_history,
        })
        csv_p = self.output_dir / "a2c_diagnostics_history.csv"
        df.to_csv(str(csv_p), index=False)
        log.info("[A2C-DIAG] CSV: %s", csv_p)


# ===================== CONVERGENCIA Y ROBUSTEZ ESTOCÁSTICA =====================


class ConvergenceRewardsCallback(BaseCallback):
    """Registra recompensas acumuladas por episodio y métricas de robustez estocástica.

    Genera en tiempo real (al finalizar cada episodio):
      1. Curva de convergencia: reward por episodio + media móvil ± σ
      2. Análisis de varianza: CV rolling, tendencia R², estabilidad
      3. Comparación robustez: primeros N vs últimos N episodios
      4. Histograma de recompensas (últimos episodios con ajuste normal)
    """

    WINDOW = 5
    LAST_N = 10
    PALETTE = {
        "raw":  "#aec7e8",
        "mean": "#1f77b4",
        "band": "#1f77b4",
        "conv": "#2ca02c",
        "var":  "#d62728",
    }

    def __init__(self, output_dir: Path, agent_name: str = "a2c",
                 ep_len: int = 8760, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.output_dir = output_dir
        self.agent_name = agent_name.lower()
        self.ep_len = ep_len
        self._ep_rewards: list[float] = []
        self._ep_numbers: list[int] = []
        self._ep_timesteps: list[int] = []
        self._acc_reward: float = 0.0
        self._acc_steps: int = 0

    @staticmethod
    def _smooth(data: list[float], window: int = 5) -> np.ndarray:
        return pd.Series(data).rolling(window=window, min_periods=1).mean().values  # type: ignore[return-value]

    @staticmethod
    def _rolling_std(data: list[float], window: int = 5) -> np.ndarray:
        return pd.Series(data).rolling(window=window, min_periods=1).std().fillna(0.0).values  # type: ignore[return-value]

    @staticmethod
    def _rolling_cv(data: list[float], window: int = 5) -> np.ndarray:
        s = pd.Series(data)
        rm = s.rolling(window=window, min_periods=1).mean()
        rs = s.rolling(window=window, min_periods=1).std().fillna(0.0)
        return (rs / rm.abs().clip(lower=1e-9) * 100.0).values  # type: ignore[return-value]

    @staticmethod
    def _trend_r2(values: list[float]) -> float:
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
        if len(values) < self.WINDOW + 1:
            return None
        roll = self._smooth(values, self.WINDOW)
        target = float(roll.max()) * threshold
        hits = np.where(roll >= target)[0]
        return int(hits[0]) + 1 if len(hits) else None

    def _on_step(self) -> bool:
        self._acc_reward += float(self.locals["rewards"][0])
        self._acc_steps += 1
        for info in (self.locals.get("infos") or []):
            ep_info = info.get("episode")
            if ep_info is not None:
                ep_num = len(self._ep_rewards) + 1
                self._ep_rewards.append(float(ep_info.get("r", self._acc_reward)))
                self._ep_numbers.append(ep_num)
                self._ep_timesteps.append(self.num_timesteps)
                self._acc_reward = 0.0
                self._acc_steps = 0
                self._log_metrics(ep_num, self._ep_rewards[-1])
                if ep_num >= 2:
                    self._save_convergence_figure()
            elif self._acc_steps >= self.ep_len:
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
        n = len(self._ep_rewards)
        window_data = self._ep_rewards[-min(self.WINDOW, n):]
        roll_mean = float(np.mean(window_data))
        roll_std  = float(np.std(window_data))
        roll_cv   = roll_std / max(abs(roll_mean), 1e-9) * 100.0
        r2 = self._trend_r2(self._ep_rewards)
        log.info(
            "[CONV] Ep %3d | reward=%9.2f | \u03bc(w%d)=%9.2f | \u03c3=%7.2f | CV=%.1f%% | R\u00b2=%.4f",
            ep_num, ep_reward, min(self.WINDOW, n), roll_mean, roll_std, roll_cv, r2,
        )
        self.logger.record("convergence/episode_reward", ep_reward)
        self.logger.record("convergence/rolling_mean", roll_mean)
        self.logger.record("convergence/rolling_std",  roll_std)
        self.logger.record("convergence/rolling_cv_pct", roll_cv)
        self.logger.record("convergence/trend_r2", r2 if not np.isnan(r2) else 0.0)

    def _save_convergence_figure(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ag = self.agent_name
        eps  = self._ep_numbers
        rews = self._ep_rewards
        n    = len(rews)
        roll_mean = self._smooth(rews, self.WINDOW)
        roll_std  = self._rolling_std(rews, self.WINDOW)
        roll_cv   = self._rolling_cv(rews, self.WINDOW)
        ncols = 2 if n < 5 else (4 if n >= self.LAST_N else 3)
        fig = plt.figure(figsize=(6 * ncols, 5))
        gs  = gridspec.GridSpec(1, ncols, figure=fig, wspace=0.35)
        fig.suptitle(
            f"{ag.upper()} \u2014 Curvas de Convergencia y Robustez Estoc\u00e1stica\n"
            f"pvbesscar | {n} episodio(s) completados | pasos={self._ep_timesteps[-1]:,}",
            fontsize=11, fontweight="bold",
        )
        # Panel 1: Curva de convergencia
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(eps, rews, color=self.PALETTE["raw"], alpha=0.6,
                 linewidth=1, marker="o", markersize=3, label="Recompensa ep.")
        ax1.plot(eps, roll_mean, color=self.PALETTE["mean"],
                 linewidth=2.5, label=f"Media m\u00f3vil (w={self.WINDOW})")
        ax1.fill_between(eps, roll_mean - roll_std, roll_mean + roll_std,
                         alpha=0.20, color=self.PALETTE["band"], label="\u00b11\u03c3")
        if n >= 3:
            x = np.arange(n, dtype=float)
            c = np.polyfit(x, rews, 1)
            r2 = self._trend_r2(rews)
            ax1.plot(eps, np.polyval(c, x), "k--", linewidth=1.5, alpha=0.7,
                     label=f"Tendencia (R\u00b2={r2:.3f})")
        conv_ep = self._convergence_episode(rews)
        if conv_ep and conv_ep <= n:
            ax1.axvline(conv_ep, color=self.PALETTE["conv"], linestyle="--",
                        linewidth=1.5, label=f"Convergencia ep. {conv_ep}")
        ax1.set_xlabel("Episodio", fontsize=9); ax1.set_ylabel("Recompensa acumulada", fontsize=9)
        ax1.set_title("Curva de Convergencia", fontsize=10, fontweight="bold")
        ax1.legend(fontsize=7); ax1.grid(True, alpha=0.3); ax1.tick_params(labelsize=8)
        # Panel 2: CV rolling
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.plot(eps, roll_cv, color=self.PALETTE["var"], linewidth=2)
        ax2.fill_between(eps, roll_cv, alpha=0.15, color=self.PALETTE["var"])
        ax2.axhline(10.0, color="green",  linestyle="--", linewidth=1.2, alpha=0.8, label="CV<10%")
        ax2.axhline(20.0, color="orange", linestyle="--", linewidth=1.0, alpha=0.7, label="CV=20%")
        ax2.set_xlabel("Episodio", fontsize=9); ax2.set_ylabel("Coef. Variaci\u00f3n (%)", fontsize=9)
        ax2.set_title("Varianza Relativa Rolling (CV)", fontsize=10, fontweight="bold")
        ax2.legend(fontsize=7); ax2.grid(True, alpha=0.3)
        ax2.tick_params(labelsize=8); ax2.set_ylim(bottom=0)
        # Panel 3: Histograma
        if n >= 5 and ncols >= 3:
            ax3 = fig.add_subplot(gs[0, 2])
            last_n = rews[-min(self.LAST_N, n):]
            ax3.hist(last_n, bins=min(10, len(last_n)), density=True,
                     color=self.PALETTE["mean"], alpha=0.7, edgecolor="white")
            if len(last_n) >= 3:
                mu_h, sig_h = float(np.mean(last_n)), float(np.std(last_n))
                xs = np.linspace(min(last_n), max(last_n), 100)
                from scipy.stats import norm as _norm
                ax3.plot(xs, _norm.pdf(xs, mu_h, sig_h), "k--", linewidth=1.5,
                         label=f"N({mu_h:.0f}, {sig_h:.0f})")
                ax3.set_title(
                    f"Distribuci\u00f3n \u00daltimos {len(last_n)} Ep.\n"
                    f"\u03bc={mu_h:.1f} \u03c3={sig_h:.1f} CV={sig_h/max(abs(mu_h),1e-9)*100:.1f}%",
                    fontsize=9, fontweight="bold",
                )
            ax3.set_xlabel("Recompensa", fontsize=9); ax3.set_ylabel("Densidad", fontsize=9)
            ax3.legend(fontsize=7); ax3.grid(True, alpha=0.3); ax3.tick_params(labelsize=8)
        # Panel 4: Robustez primeros vs últimos
        if n >= self.LAST_N and ncols >= 4:
            ax4 = fig.add_subplot(gs[0, 3])
            first_n = rews[: self.LAST_N]; last_n = rews[-self.LAST_N:]
            cats  = [f"Primeros\n{self.LAST_N} ep.", f"\u00daltimos\n{self.LAST_N} ep."]
            means = [float(np.mean(first_n)), float(np.mean(last_n))]
            stds  = [float(np.std(first_n)),  float(np.std(last_n))]
            cvs   = [s / max(abs(m), 1e-9) * 100 for m, s in zip(means, stds)]
            ax4.bar(cats, means, color=["#d62728", "#2ca02c"], alpha=0.75, width=0.5, zorder=3)
            ax4.errorbar([0, 1], means, yerr=stds, fmt="none", ecolor="black",
                         elinewidth=2, capsize=10, capthick=2, zorder=4)
            for i, (m, cv) in enumerate(zip(means, cvs)):
                ax4.text(i, max(means) + max(stds) * 0.55,
                         f"{m:+.0f}\nCV={cv:.1f}%", ha="center", fontsize=8, fontweight="bold")
            ax4.set_title(f"Robustez: Primeros vs \u00daltimos {self.LAST_N} ep.",
                          fontsize=9, fontweight="bold")
            ax4.set_ylabel("Recompensa media", fontsize=9)
            ax4.grid(True, alpha=0.3, axis="y"); ax4.tick_params(labelsize=8)
        out_path = self.output_dir / f"{ag}_convergencia_recompensas.png"
        fig.savefig(str(out_path), dpi=130, bbox_inches="tight")
        plt.close(fig)

    def on_training_end(self) -> None:
        n = len(self._ep_rewards)
        if n < 2:
            log.info("[CONV] Insuficientes episodios (%d)", n)
            return
        ag = self.agent_name
        self._save_convergence_figure()
        rews    = self._ep_rewards
        r2      = self._trend_r2(rews)
        conv_ep = self._convergence_episode(rews)
        last_n  = rews[-min(self.LAST_N, n):]
        first_n = rews[: min(self.LAST_N, n)]
        mu_f, sig_f = float(np.mean(first_n)), float(np.std(first_n))
        mu_l, sig_l = float(np.mean(last_n)),  float(np.std(last_n))
        cv_l = sig_l / max(abs(mu_l), 1e-9) * 100.0
        stability = float(1.0 - cv_l / 100.0)
        log.info("\u2550" * 70)
        log.info("[CONV] ROBUSTEZ ESTOC\u00c1STICA FINAL \u2014 %s (%d episodios)", ag.upper(), n)
        log.info("  Primeros %d ep.: \u03bc=%8.2f  \u03c3=%7.2f  CV=%.1f%%",
                 len(first_n), mu_f, sig_f, sig_f/max(abs(mu_f),1e-9)*100)
        log.info("  \u00daltimos  %d ep.: \u03bc=%8.2f  \u03c3=%7.2f  CV=%.1f%%  StabIdx=%.4f",
                 len(last_n), mu_l, sig_l, cv_l, stability)
        log.info("  Tendencia lineal: R\u00b2=%.4f | Ep. convergencia: %s", r2, conv_ep)
        log.info("\u2550" * 70)
        # CSV
        df = pd.DataFrame({
            "episodio":        self._ep_numbers,
            "timestep":        self._ep_timesteps,
            "reward":          rews,
            "rolling_mean":    self._smooth(rews, self.WINDOW).tolist(),
            "rolling_std":     self._rolling_std(rews, self.WINDOW).tolist(),
            "rolling_cv_pct":  self._rolling_cv(rews, self.WINDOW).tolist(),
        })
        csv_path = self.output_dir / f"{ag}_convergencia_episodios.csv"
        df.to_csv(str(csv_path), index=False, encoding="utf-8-sig")
        log.info("[CONV] CSV: %s", csv_path)
        # JSON robustez
        robustness = {
            "n_episodes":          n,
            "episode_rewards":     rews,
            "mean_reward":         float(np.mean(rews)),
            "std_reward":          float(np.std(rews)),
            "final_mean_reward":   mu_l,
            "final_std_reward":    sig_l,
            "final_cv_pct":        cv_l,
            "stability_index":     stability,
            "trend_r2":            r2 if not np.isnan(r2) else 0.0,
            "convergence_episode": conv_ep,
            "trend_improving":     bool(r2 > 0.3 and mu_l > mu_f),
            "best_episode":        int(np.argmax(rews)) + 1,
            "best_reward":         float(max(rews)),
        }
        rob_path = self.output_dir / f"{ag}_robustez_estocastica.json"
        with open(rob_path, "w", encoding="utf-8") as _f:
            json.dump(robustness, _f, indent=2, ensure_ascii=False)
        log.info("[CONV] JSON robustez: %s", rob_path)


# ===================== ENTRENAMIENTO =====================


def load_or_create_a2c(env) -> tuple[A2C, int]:
    """Carga el último checkpoint A2C (con VecNormalize) o crea modelo nuevo."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    zips = sorted(CHECKPOINT_DIR.glob("a2c_*_steps.zip"))
    if zips:
        latest = zips[-1]
        try:
            model = A2C.load(
                str(latest),
                env=env,
                device=_DEVICE,
            )
            steps_done = model.num_timesteps
            log.info("Checkpoint A2C cargado: %s (%d steps)", latest, steps_done)
            return model, steps_done
        except Exception as e:
            log.warning("Error cargando %s: %s — creando nuevo", latest, e)

    log.info("Creando nuevo agente A2C (SB3, PyTorch)...")
    model = A2C(env=env, tensorboard_log=str(TENSORBOARD_DIR), **A2C_HYPERPARAMS)
    return model, 0


def train(total_timesteps: int = TOTAL_TIMESTEPS, rebuild_schema: bool = False) -> None:
    """Loop principal de entrenamiento A2C en CityLearn v2."""
    log.info("=" * 70)
    log.info("A2C SB3 + IquitosEVChargingWrapper — Iquitos PV-BESS-EV")
    log.info("PyTorch: %s | CUDA: %s | Device: %s", torch.__version__, torch.cuda.is_available(), A2C_HYPERPARAMS["device"])
    log.info("Total timesteps: {:,} ({} ep × 8760 h)".format(total_timesteps, total_timesteps // 8760))
    log.info("Acción: 3D [bess(-1→+1), ev_motos_frac(0→1), ev_mototaxis_frac(0→1)]")
    log.info("Obs: 19D (CityLearn 12D + EV state 5D + tarifa 2D) — incluye electricity_pricing")
    log.info("=" * 70)

    # 1. Construir schema si es necesario
    if rebuild_schema:
        log.info("Reconstruyendo schema CityLearn v2 y ev_demand.csv...")
        build_citylearn_schema()

    # 2. Crear entorno SB3-compatible con control EV + VecNormalize
    # VecNormalize: normaliza obs y returns (crítico para on-policy con ep 8760 steps)
    log.info("Inicializando IquitosEVChargingWrapper(CityLearnEnv) + VecNormalize...")
    vec_env = DummyVecEnv([lambda: create_iquitos_env_for_sb3()])
    vecnorm_path = CHECKPOINT_DIR / "vecnormalize.pkl"
    if vecnorm_path.exists():
        env = VecNormalize.load(str(vecnorm_path), vec_env)
        env.training = True
        log.info("VecNormalize cargado desde: %s", vecnorm_path)
    else:
        env = VecNormalize(
            vec_env,
            norm_obs=True,
            norm_reward=True,
            clip_obs=10.0,
            clip_reward=10.0,
        )
    log.info("Entorno: obs=%s | action=%s", env.observation_space, env.action_space)

    # 2b. Validar configuración del agente
    log.info("Validando configuración del agente A2C...")
    if not validate_agent_config("A2C", num_episodes=total_timesteps // 8760,
                                  total_timesteps=total_timesteps, obs_dim=19, action_dim=3):
        log.warning("[WARN] validate_agent_config reportó advertencia — continúa entrenamiento")

    # 3. Cargar o crear modelo A2C
    model, steps_done = load_or_create_a2c(env)
    remaining_steps = max(total_timesteps - steps_done, 0)

    if remaining_steps == 0:
        log.info("Ya completado el objetivo de %d timesteps.", total_timesteps)
        return

    log.info("Pasos restantes: {:,}".format(remaining_steps))

    # 4. Callbacks
    checkpoint_cb = CheckpointCallback(
        save_freq=CHECKPOINT_EVERY_STEPS,
        save_path=str(CHECKPOINT_DIR),
        name_prefix="a2c",
        save_replay_buffer=False,
        save_vecnormalize=True,   # guardar VecNormalize con cada checkpoint
    )
    metrics_cb = CO2MetricsCallback(log_every_steps=CHECKPOINT_EVERY_STEPS)
    ev_metrics_cb = EVMetricsCallback(log_freq=8760, verbose=1)
    ev_metrics_cb.output_dir = RESULTS_DIR
    a2c_diag_cb = A2CDiagnosticsCallback(output_dir=RESULTS_DIR, verbose=0)
    convergence_cb = ConvergenceRewardsCallback(
        output_dir=RESULTS_DIR, agent_name="a2c", ep_len=8760, verbose=0
    )

    # 5. Entrenar
    t0 = time.time()
    model.learn(
        total_timesteps=remaining_steps,
        callback=CallbackList([checkpoint_cb, metrics_cb, ev_metrics_cb, a2c_diag_cb, convergence_cb]),
        reset_num_timesteps=False,
        tb_log_name=f"a2c_{_ts}",
    )
    elapsed = time.time() - t0

    # 6. Guardar modelo final
    final_path = CHECKPOINT_DIR / "a2c_final"
    model.save(str(final_path))
    env.save(str(CHECKPOINT_DIR / "vecnormalize.pkl"))  # guardar stats VecNormalize
    log.info("Modelo final guardado: %s.zip | VecNormalize: %s", final_path, CHECKPOINT_DIR / "vecnormalize.pkl")

    # 7. Validación post-entrenamiento (10 episodios determinísticos)
    log.info("=" * 70)
    log.info("VALIDACIÓN POST-ENTRENAMIENTO A2C — 10 episodios determinísticos")
    log.info("=" * 70)
    N_VAL = 10
    val_rewards: list[float] = []
    val_co2_avoided: list[float] = []
    val_solar: list[float] = []
    val_grid: list[float] = []
    env.training = False
    env.norm_reward = False
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
    env.training = True
    env.norm_reward = True
    log.info("  Validación: reward_mean=%.2f ± %.2f | CO2_mean=%.1f kg | solar_mean=%.1f kWh",
             float(np.mean(val_rewards)), float(np.std(val_rewards)),
             float(np.mean(val_co2_avoided)), float(np.mean(val_solar)))

    # 8. Guardar result_a2c.json (misma estructura que train_a2c.py)
    log.info("Guardando result_a2c.json...")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    class _NumpyEncoder(json.JSONEncoder):
        def default(self, obj: Any) -> Any:
            if isinstance(obj, (np.floating, np.integer)):
                return float(obj) if isinstance(obj, np.floating) else int(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    _ep_cb = ev_metrics_cb
    result_summary: dict[str, Any] = {
        "timestamp":   _ts,
        "agent":       "A2C",
        "project":     "pvbesscar",
        "location":    "Iquitos, Peru",
        "co2_factor_kg_per_kwh": 0.4521,
        "training": {
            "total_timesteps":    int(model.num_timesteps),
            "episodes":           int(model.num_timesteps // 8760),
            "duration_seconds":   float(elapsed),
            "speed_steps_per_second": float(model.num_timesteps / max(elapsed, 1)),
            "device":             A2C_HYPERPARAMS["device"],
            "episodes_completed": len(_ep_cb._episodes),
            "hyperparameters":    {k: str(v) for k, v in A2C_HYPERPARAMS.items()},
        },
        "infrastructure": {
            "pv_kwp":            4162,
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
            "hist_reduccion_pct":         _ep_cb._hist_reduccion_pct,
        },
        "summary_metrics": {
            "total_co2_directa_kg":    float(sum(_ep_cb._hist_co2_directa_kg)),
            "total_co2_indirecta_kg":  float(sum(_ep_cb._hist_co2_indirecta_kg)),
            "total_co2_neta_kg":       float(sum(_ep_cb._hist_co2_neta_kg)),
            "total_solar_kwh":         float(sum(_ep_cb._hist_solar_kwh)),
            "total_grid_import_kwh":   float(sum(_ep_cb._hist_grid_import_kwh)),
            "total_ev_kwh":            float(sum(_ep_cb._hist_ev_motos_kwh) + sum(_ep_cb._hist_ev_mototaxis_kwh)),
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
            "trace":       str(RESULTS_DIR / "trace_a2c.csv"),
            "timeseries":  str(RESULTS_DIR / "timeseries_a2c.csv"),
            "result":      str(RESULTS_DIR / "result_a2c.json"),
        },
    }
    result_path = RESULTS_DIR / "result_a2c.json"
    with open(result_path, "w", encoding="utf-8") as _f:
        json.dump(result_summary, _f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)
    log.info("[OK] result_a2c.json → %s", result_path)

    # 9. Verificar archivos de salida
    _trace_path = RESULTS_DIR / "trace_a2c.csv"
    _ts_path    = RESULTS_DIR / "timeseries_a2c.csv"
    if _trace_path.exists():
        _rows = sum(1 for _ in open(_trace_path, encoding="utf-8")) - 1
        log.info("[OK] trace_a2c.csv: %d registros → %s", _rows, _trace_path)
    else:
        log.warning("[!] trace_a2c.csv no generado")
    if _ts_path.exists():
        _rows = sum(1 for _ in open(_ts_path, encoding="utf-8")) - 1
        log.info("[OK] timeseries_a2c.csv: %d registros → %s", _rows, _ts_path)
    else:
        log.warning("[!] timeseries_a2c.csv no generado")

    log.info("=" * 70)
    log.info("ENTRENAMIENTO A2C COMPLETADO en %.1f s", elapsed)
    log.info("Pasos totales: %d  |  Episodios: %d", model.num_timesteps, len(_ep_cb._episodes))
    log.info("  [OK] %s", result_path)
    log.info("  [OK] %s", _trace_path)
    log.info("  [OK] %s", _ts_path)
    log.info("  [OK] %s.zip", final_path)
    log.info("=" * 70)


# ===================== MAIN =====================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A2C CityLearn v2 - Iquitos PV-BESS-EV")
    parser.add_argument("--timesteps", type=int, default=TOTAL_TIMESTEPS,
                        help="Total timesteps (default: 438000 = 50 ep × 8760 h)")
    parser.add_argument("--rebuild-schema", action="store_true",
                        help="Regenerar CSVs y schema aunque ya existan")
    args = parser.parse_args()

    try:
        train(total_timesteps=args.timesteps, rebuild_schema=args.rebuild_schema)
    except KeyboardInterrupt:
        log.info("Entrenamiento interrumpido por usuario.")
    except Exception as exc:
        log.error("Error fatal: %s", exc, exc_info=True)
        sys.exit(1)
