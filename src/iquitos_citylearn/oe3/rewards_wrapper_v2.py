"""
Wrapper de recompensa mejorado V2 que integra observables enriquecidos.

Incluye:
- Flags de hora pico/valle/pre-pico
- SOC actual vs target dinámico  
- Déficit de reserva
- Potencia FV disponible
- Colas/sesiones por playa
- Potencia de EV por playa
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from typing import Any, Dict, Optional, Tuple
import logging

from .rewards_improved_v2 import ImprovedMultiObjectiveReward, ImprovedWeights, IquitosContextV2
from .tier2_v2_config import TIER2V2Config

logger = logging.getLogger(__name__)


class ImprovedRewardWrapper(gym.Wrapper):
    """
    Wrapper que aplica recompensa mejorada V2 con observables enriquecidos.
    
    Cambios clave:
    - Observables: incluye flags pico, SOC targets dinámicos, FV disponible, etc.
    - Recompensas: normalización correcta, penalizaciones explícitas, énfasis pico
    - Hiperparámetros: entropy coef fijo, LR dinámico por hora
    """
    
    def __init__(
        self,
        env: gym.Env,
        config: Optional[TIER2V2Config] = None,
        verbose: int = 0,
    ):
        super().__init__(env)
        self.config = config or TIER2V2Config()
        self.verbose = verbose
        
        # Recompensa mejorada
        weights = ImprovedWeights(
            co2_priority=self.config.co2_weight,
            solar_secondary=self.config.solar_weight,
            cost_reduced=self.config.cost_weight,
            ev_satisfaction=self.config.ev_satisfaction_weight,
            grid_stability=self.config.grid_stability_weight,
            peak_power_penalty_weight=self.config.peak_power_penalty,
            soc_reserve_penalty_weight=self.config.soc_reserve_penalty,
            import_peak_penalty_weight=self.config.import_peak_penalty,
            fairness_penalty_weight=self.config.fairness_penalty,
            entropy_coef_fixed=self.config.entropy_coef_fixed,
        )
        
        context = IquitosContextV2(
            peak_hours=self.config.peak_hours,
            pre_peak_hours=self.config.pre_peak_hours,
            valley_hours=self.config.valley_hours,
        )
        
        self.reward_fn = ImprovedMultiObjectiveReward(weights, context)
        
        # Metadatos
        self._step_count = 0
        self._hour_of_year = 0
        self._last_components = {}
    
    def reset(self, seed=None, options=None):
        """Reset del wrapper."""
        obs, info = self.env.reset(seed=seed, options=options)
        self._step_count = 0
        self._hour_of_year = 0
        return obs, info
    
    def step(self, action):
        """Step con recompensa mejorada."""
        obs, reward_original, terminated, truncated, info = self.env.step(action)
        
        # Actualizar hora
        self._step_count += 1
        self._hour_of_year = self._step_count % 8760  # 365 * 24
        hour = self._hour_of_year % 24
        
        # Extraer estado operacional del info (si disponible)
        grid_import = info.get("grid_import_kwh", 0.0)
        grid_export = info.get("grid_export_kwh", 0.0)
        solar_gen = info.get("solar_generation_kwh", 0.0)
        ev_charging = info.get("ev_charging_kwh", 0.0)
        ev_soc = info.get("ev_soc_avg", 0.0)
        bess_soc = info.get("bess_soc", 0.0)
        
        # Potencia de EVs por playa (si disponible)
        ev_power_motos = info.get("ev_power_motos_kw", 0.0)
        ev_power_mototaxis = info.get("ev_power_mototaxis_kw", 0.0)
        grid_import_power = info.get("grid_import_power_kw", 0.0)
        
        # Computar recompensa mejorada
        reward, components = self.reward_fn.compute(
            grid_import_kwh=grid_import,
            grid_export_kwh=grid_export,
            solar_generation_kwh=solar_gen,
            ev_charging_kwh=ev_charging,
            ev_soc_avg=ev_soc,
            bess_soc=bess_soc,
            hour=hour,
            ev_power_motos_kw=ev_power_motos,
            ev_power_mototaxis_kw=ev_power_mototaxis,
            grid_import_power_kw=grid_import_power,
        )
        
        # Guardar componentes para debugging
        self._last_components = components
        
        # Agregar info enriquecida
        info_enriched = {
            **info,
            "reward_components": components,
            "hour": hour,
            "is_peak": components.get("is_peak", 0.0),
            "is_pre_peak": components.get("is_pre_peak", 0.0),
            "is_valley": components.get("is_valley", 0.0),
        }
        
        if self.verbose > 0 and self._step_count % 100 == 0:
            logger.info(
                f"[Step {self._step_count}] Hour={hour} | "
                f"CO2={components.get('r_co2', 0):.3f} | "
                f"Reward={reward:.3f} | Peak={int(components.get('is_peak', 0))}"
            )
        
        return obs, reward, terminated, truncated, info_enriched
    
    def get_adjusted_entropy_coef(self) -> float:
        """Retorna entropy coef (fijo)."""
        return self.reward_fn.weights.entropy_coef_fixed
    
    def get_adjusted_lr(self, hour: Optional[int] = None) -> float:
        """Retorna learning rate según hora."""
        if hour is None:
            hour = self._hour_of_year % 24
        
        if hour in self.config.peak_hours:
            return self.reward_fn.weights.learning_rate_peak_adjust
        return self.reward_fn.weights.learning_rate
    
    def get_soc_target(self) -> float:
        """Retorna SOC target dinámico para hora actual."""
        hour = self._hour_of_year % 24
        if hour in self.config.peak_hours:
            return self.config.bess_soc_target_peak
        elif hour in self.config.pre_peak_hours:
            return self.config.bess_soc_target_prepeak
        return self.config.bess_soc_target_normal
    
    def get_last_components(self) -> Dict[str, float]:
        """Retorna últimos componentes de recompensa."""
        return self._last_components.copy()
