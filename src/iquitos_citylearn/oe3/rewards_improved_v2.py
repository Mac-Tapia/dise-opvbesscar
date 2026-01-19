"""
Función de recompensa MEJORADA V2 - Con énfasis en CO2/pico y penalizaciones normalizadas.

Cambios respecto a V1:
1. MÁS PESO A CO₂ EN HORA PICO: Penalización 2x durante 18-21h
2. PENALIZACIÓN DE POTENCIA PICO: Adicional -0.5 a -1.0 si excedes límite
3. RECOMPENSAS NORMALIZADAS: Todos los componentes clipeados a [-1, 1]
4. MEJOR ESCALADO: Baselines realistas por hora
5. OBSERVABLES ENRIQUECIDOS: Flags pico, SOC, reserva, colas, FV
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class ImprovedWeights:
    """Pesos para función de recompensa mejorada V2.
    
    CAMBIOS:
    - CO₂ AUMENTADO a 0.55 (primary objective)
    - Penalización de pico EXPLÍCITA
    - Grid stability REDUCIDO (implícito en CO₂ pico)
    - Entropy coef: FIJO en 0.01 (no 0.02) para más exploración controlada
    """
    co2_priority: float = 0.55              # PRIMARY: Minimizar CO₂ (térmica)
    solar_secondary: float = 0.20           # SECONDARY: autoconsumo limpio
    cost_reduced: float = 0.10              # REDUCIDO: no es bottleneck
    ev_satisfaction: float = 0.10           # Básica
    grid_stability: float = 0.05            # REDUCIDO (cubierto por CO₂)
    
    # Penalizaciones explícitas (aplicadas POR SEPARADO)
    peak_power_penalty_weight: float = 0.30   # Exceso potencia en pico
    soc_reserve_penalty_weight: float = 0.20  # Déficit SOC pre-pico
    import_peak_penalty_weight: float = 0.25  # Importación en pico
    fairness_penalty_weight: float = 0.10     # Desequilibrio playas
    
    # Hiperparámetros RL
    entropy_coef_fixed: float = 0.01           # FIJO: exploración controlada
    learning_rate: float = 2.0e-4              # TIER 2: base
    learning_rate_peak_adjust: float = 1.5e-4 # REDUCIDO en pico para estabilidad
    
    def __post_init__(self):
        # Normalizar pesos base
        base_weights = [
            self.co2_priority,
            self.solar_secondary,
            self.cost_reduced,
            self.ev_satisfaction,
            self.grid_stability,
        ]
        total = sum(base_weights)
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Pesos no suman 1.0 (suma={total:.3f}), normalizando...")
            factor = 1.0 / total
            self.co2_priority *= factor
            self.solar_secondary *= factor
            self.cost_reduced *= factor
            self.ev_satisfaction *= factor
            self.grid_stability *= factor


@dataclass
class IquitosContextV2:
    """Contexto mejorado de Iquitos."""
    # Emisiones
    co2_factor_kg_per_kwh: float = 0.45
    
    # Operación
    tariff_usd_per_kwh: float = 0.20
    
    # Horas críticas
    peak_hours: Tuple[int, ...] = (18, 19, 20, 21)
    pre_peak_hours: Tuple[int, ...] = (16, 17)
    valley_hours: Tuple[int, ...] = (9, 10, 11, 12)
    
    # Límites
    peak_demand_limit_kw: float = 150.0      # Límite HARD en pico
    normal_demand_limit_kw: float = 200.0    # Límite suave fuera pico
    ev_soc_target: float = 0.90
    bess_soc_target_prepeak: float = 0.85    # SOC meta antes de pico
    bess_soc_target_normal: float = 0.60
    bess_soc_min: float = 0.10
    
    # Baselines
    import_baseline_offpeak_kwh: float = 130.0
    import_baseline_peak_kwh: float = 250.0


class ImprovedMultiObjectiveReward:
    """Recompensa multiobjetivo V2 con énfasis en pico y normalización."""
    
    def __init__(
        self,
        weights: Optional[ImprovedWeights] = None,
        context: Optional[IquitosContextV2] = None,
    ):
        self.weights = weights or ImprovedWeights()
        self.context = context or IquitosContextV2()
        self._reward_history: List[Dict[str, float]] = []
        self._max_history = 1000
        
        # Estadísticas para normalización adaptativa
        self._reward_mean = 0.0
        self._reward_std = 1.0
        
    def compute(
        self,
        grid_import_kwh: float,
        grid_export_kwh: float,
        solar_generation_kwh: float,
        ev_charging_kwh: float,
        ev_soc_avg: float,
        bess_soc: float,
        hour: int,
        ev_power_motos_kw: float = 0.0,
        ev_power_mototaxis_kw: float = 0.0,
        grid_import_power_kw: float = 0.0,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Computa recompensa multiobjetivo MEJORADA V2.
        
        CAMBIOS:
        - Énfasis en CO₂ en hora pico (2x penalización)
        - Penalización explícita de potencia pico
        - Normalización correcta de todos los componentes
        - Observables enriquecidos con flags
        
        Returns:
            (reward_total, dict_componentes)
        """
        components = {}
        is_peak = hour in self.context.peak_hours
        is_pre_peak = hour in self.context.pre_peak_hours
        is_valley = hour in self.context.valley_hours
        
        # ===== COMPONENT 1: CO₂ =====
        # MÁS PESO EN HORA PICO
        co2_kg = grid_import_kwh * self.context.co2_factor_kg_per_kwh
        
        if is_peak:
            # DURANTE PICO: Penalizar 2x más fuerte
            baseline = self.context.import_baseline_peak_kwh
            r_co2 = 1.0 - 2.5 * min(1.0, grid_import_kwh / baseline)  # Rango [-1.5, 1]
        else:
            # FUERA PICO: Más tolerante
            baseline = self.context.import_baseline_offpeak_kwh
            r_co2 = 1.0 - 1.2 * min(1.0, grid_import_kwh / baseline)  # Rango [-0.2, 1]
        
        r_co2 = np.clip(r_co2, -1.0, 1.0)  # NORMALIZAR [-1, 1]
        components["r_co2"] = r_co2
        components["co2_kg"] = co2_kg
        
        # ===== COMPONENT 2: COSTO =====
        cost_usd = (grid_import_kwh - grid_export_kwh) * self.context.tariff_usd_per_kwh
        
        if is_peak:
            # En pico, costo es 1.5x
            cost_adjusted = cost_usd * 1.5
        else:
            cost_adjusted = cost_usd
        
        cost_baseline = 50.0
        r_cost = 1.0 - 1.5 * min(1.0, max(0, cost_adjusted) / cost_baseline)
        r_cost = np.clip(r_cost, -1.0, 1.0)  # NORMALIZAR
        components["r_cost"] = r_cost
        components["cost_usd"] = cost_usd
        
        # ===== COMPONENT 3: AUTOCONSUMO SOLAR =====
        if solar_generation_kwh > 0.01:
            solar_used = min(solar_generation_kwh, ev_charging_kwh)
            self_consumption_ratio = solar_used / solar_generation_kwh
            r_solar = 2.0 * self_consumption_ratio - 1.0
        else:
            r_solar = 0.0
        r_solar = np.clip(r_solar, -1.0, 1.0)  # NORMALIZAR
        components["r_solar"] = r_solar
        components["solar_kwh"] = solar_generation_kwh
        
        # ===== COMPONENT 4: SATISFACCIÓN EV =====
        ev_satisfaction = min(1.0, ev_soc_avg / self.context.ev_soc_target)
        r_ev = 2.0 * ev_satisfaction - 1.0
        r_ev = np.clip(r_ev, -1.0, 1.0)  # NORMALIZAR
        components["r_ev"] = r_ev
        components["ev_soc_avg"] = ev_soc_avg
        
        # ===== COMPONENT 5: ESTABILIDAD RED =====
        # REDUCIDO porque está cubierto por CO₂ en pico
        demand_ratio = grid_import_power_kw / max(1.0, self.context.normal_demand_limit_kw)
        r_grid = 1.0 - 1.5 * min(1.0, demand_ratio)
        r_grid = np.clip(r_grid, -1.0, 1.0)  # NORMALIZAR
        components["r_grid"] = r_grid
        
        # ===== RECOMPENSA BASE PONDERADA =====
        reward_base = (
            self.weights.co2_priority * r_co2 +
            self.weights.cost_reduced * r_cost +
            self.weights.solar_secondary * r_solar +
            self.weights.ev_satisfaction * r_ev +
            self.weights.grid_stability * r_grid
        )
        components["reward_base"] = reward_base
        
        # ===== PENALIZACIONES EXPLÍCITAS =====
        total_penalty = 0.0
        
        # 1. Penalidad por potencia en pico
        if is_peak:
            ev_power_total = ev_power_motos_kw + ev_power_mototaxis_kw
            if ev_power_total > self.context.peak_demand_limit_kw:
                power_excess_ratio = (ev_power_total - self.context.peak_demand_limit_kw) / self.context.peak_demand_limit_kw
                r_peak_power = -min(1.0, power_excess_ratio)  # [-1, 0]
                total_penalty += self.weights.peak_power_penalty_weight * r_peak_power
                components["r_peak_power_penalty"] = r_peak_power
            else:
                components["r_peak_power_penalty"] = 0.0
        else:
            components["r_peak_power_penalty"] = 0.0
        
        # 2. Penalidad por SOC insuficiente pre-pico
        if is_pre_peak:
            soc_target_prepeak = self.context.bess_soc_target_prepeak
            if bess_soc < soc_target_prepeak:
                soc_deficit = (soc_target_prepeak - bess_soc) / soc_target_prepeak
                r_soc_reserve = -min(1.0, soc_deficit)  # [-1, 0]
                total_penalty += self.weights.soc_reserve_penalty_weight * r_soc_reserve
                components["r_soc_reserve_penalty"] = r_soc_reserve
            else:
                components["r_soc_reserve_penalty"] = 0.0
        else:
            components["r_soc_reserve_penalty"] = 0.0
        
        # 3. Penalidad por importación en pico
        if is_peak and grid_import_kwh > 100.0:
            import_excess = min(1.0, (grid_import_kwh - 100.0) / 150.0)
            r_import_peak = -import_excess  # [-1, 0]
            total_penalty += self.weights.import_peak_penalty_weight * r_import_peak
            components["r_import_peak_penalty"] = r_import_peak
        else:
            components["r_import_peak_penalty"] = 0.0
        
        # 4. Penalidad por desequilibrio fairness entre playas
        ev_powers = [ev_power_motos_kw, ev_power_mototaxis_kw]
        if any(p > 0 for p in ev_powers):
            max_p = max(ev_powers)
            min_p = min(p for p in ev_powers if p > 0)
            if min_p > 0:
                fairness_ratio = max_p / min_p
                if fairness_ratio > 1.5:  # Threshold
                    fairness_excess = (fairness_ratio - 1.5) / 1.5
                    r_fairness = -min(1.0, fairness_excess)  # [-1, 0]
                    total_penalty += self.weights.fairness_penalty_weight * r_fairness
                    components["r_fairness_penalty"] = r_fairness
                else:
                    components["r_fairness_penalty"] = 0.0
            else:
                components["r_fairness_penalty"] = 0.0
        else:
            components["r_fairness_penalty"] = 0.0
        
        # ===== RECOMPENSA TOTAL NORMALIZADA =====
        reward_total = reward_base + total_penalty
        reward_total = np.clip(reward_total, -1.0, 1.0)  # NORMALIZAR FINAL
        
        components["reward_total"] = reward_total
        components["is_peak"] = float(is_peak)
        components["is_pre_peak"] = float(is_pre_peak)
        components["is_valley"] = float(is_valley)
        components["hour"] = float(hour)
        components["total_penalty"] = total_penalty
        
        # Guardar historial
        self._reward_history.append(components)
        if len(self._reward_history) > self._max_history:
            self._reward_history.pop(0)
        
        # Actualizar estadísticas
        self._update_stats(reward_total)
        
        return reward_total, components
    
    def _update_stats(self, reward: float):
        """Actualiza media/std para normalización adaptativa."""
        if len(self._reward_history) < 2:
            return
        
        rewards = [r["reward_total"] for r in self._reward_history[-100:]]
        self._reward_mean = float(np.mean(rewards))
        self._reward_std = max(float(np.std(rewards)), 0.1)  # Evitar std=0
    
    def get_recommended_lr(self, hour: int) -> float:
        """Retorna LR recomendado según hora."""
        if hour in self.context.peak_hours:
            return self.weights.learning_rate_peak_adjust
        return self.weights.learning_rate
    
    def get_entropy_coef(self) -> float:
        """Retorna coef entropía (fijo)."""
        return self.weights.entropy_coef_fixed
