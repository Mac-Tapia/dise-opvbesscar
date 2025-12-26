"""
Funciones de recompensa multiobjetivo y multicriterio para agentes RL.

Objetivos optimizados:
1. Minimizar emisiones de CO₂
2. Minimizar costo eléctrico
3. Maximizar autoconsumo solar
4. Maximizar satisfacción de carga de EVs
5. Minimizar picos de demanda (estabilidad de red)

Basado en el contexto de Iquitos:
- Factor emisión: 0.45 kg CO₂/kWh (central térmica)
- Tarifa: 0.20 USD/kWh
- 31 chargers x 4 sockets = 124 puntos de carga
- 1030 vehículos (900 motos + 130 mototaxis)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class MultiObjectiveWeights:
    """Pesos para función de recompensa multiobjetivo."""
    co2: float = 0.35              # Minimizar emisiones CO₂
    cost: float = 0.25             # Minimizar costo eléctrico  
    solar: float = 0.20            # Maximizar autoconsumo solar
    ev_satisfaction: float = 0.15  # Maximizar satisfacción carga EV
    grid_stability: float = 0.05   # Minimizar picos de demanda
    
    def __post_init__(self):
        total = self.co2 + self.cost + self.solar + self.ev_satisfaction + self.grid_stability
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Pesos multiobjetivo no suman 1.0 (suma={total:.3f}), normalizando...")
            self.co2 /= total
            self.cost /= total
            self.solar /= total
            self.ev_satisfaction /= total
            self.grid_stability /= total
    
    def as_dict(self) -> Dict[str, float]:
        return {
            "co2": self.co2,
            "cost": self.cost,
            "solar": self.solar,
            "ev_satisfaction": self.ev_satisfaction,
            "grid_stability": self.grid_stability,
        }


@dataclass
class IquitosContext:
    """Contexto específico de Iquitos para cálculos multiobjetivo."""
    # Factor de emisión (central térmica aislada)
    co2_factor_kg_per_kwh: float = 0.45
    
    # Tarifa eléctrica
    tariff_usd_per_kwh: float = 0.20
    
    # Configuración de chargers (OE2)
    n_chargers: int = 31
    sockets_per_charger: int = 4
    charger_power_kw: float = 2.14
    
    # Flota EV
    n_motos: int = 900
    n_mototaxis: int = 130
    
    # Límites operacionales
    peak_demand_limit_kw: float = 200.0
    ev_soc_target: float = 0.90
    bess_soc_min: float = 0.10
    bess_soc_max: float = 0.90
    
    # Horas pico Iquitos
    peak_hours: Tuple[int, ...] = (18, 19, 20, 21)


class MultiObjectiveReward:
    """Calcula recompensa multiobjetivo para control de carga EV + BESS.
    
    Función de recompensa compuesta:
    R = w_co2 * R_co2 + w_cost * R_cost + w_solar * R_solar + 
        w_ev * R_ev + w_grid * R_grid
    
    Donde cada R_i está normalizado a [-1, 1] o [0, 1].
    """
    
    def __init__(
        self, 
        weights: Optional[MultiObjectiveWeights] = None,
        context: Optional[IquitosContext] = None,
    ):
        self.weights = weights or MultiObjectiveWeights()
        self.context = context or IquitosContext()
        
        # Historial para normalización adaptativa
        self._reward_history: List[Dict[str, float]] = []
        self._max_history = 1000
    
    def compute(
        self,
        grid_import_kwh: float,
        grid_export_kwh: float,
        solar_generation_kwh: float,
        ev_charging_kwh: float,
        ev_soc_avg: float,
        bess_soc: float,
        hour: int,
        ev_demand_kwh: float = 0.0,
    ) -> Tuple[float, Dict[str, float]]:
        """Calcula recompensa multiobjetivo.
        
        Args:
            grid_import_kwh: Energía importada de red (kWh)
            grid_export_kwh: Energía exportada a red (kWh)
            solar_generation_kwh: Generación solar (kWh)
            ev_charging_kwh: Energía entregada a EVs (kWh)
            ev_soc_avg: SOC promedio de EVs conectados [0-1]
            bess_soc: SOC del BESS [0-1]
            hour: Hora del día [0-23]
            ev_demand_kwh: Demanda de carga EV solicitada (kWh)
            
        Returns:
            Tuple de (recompensa_total, dict_componentes)
        """
        components = {}
        
        # 1. Recompensa CO₂ (minimizar)
        co2_kg = grid_import_kwh * self.context.co2_factor_kg_per_kwh
        # Normalizar según demanda típica del sistema (mall + EVs)
        # OE2: Mall ~420 kWh/h pico, EVs ~37 kWh/h promedio
        co2_baseline = 500.0  # kWh típico por hora para el sistema completo
        r_co2 = 1.0 - 2.0 * min(1.0, grid_import_kwh / co2_baseline)
        components["r_co2"] = r_co2
        components["co2_kg"] = co2_kg
        
        # 2. Recompensa Costo (minimizar)
        cost_usd = (grid_import_kwh - grid_export_kwh) * self.context.tariff_usd_per_kwh
        cost_baseline = 100.0  # USD típico por hora (500 kWh * 0.20 USD/kWh)
        r_cost = 1.0 - 2.0 * min(1.0, max(0, cost_usd) / cost_baseline)
        components["r_cost"] = r_cost
        components["cost_usd"] = cost_usd
        
        # 3. Recompensa Autoconsumo Solar (maximizar)
        if solar_generation_kwh > 0:
            solar_used = min(solar_generation_kwh, ev_charging_kwh + (grid_import_kwh * 0.5))
            self_consumption_ratio = solar_used / solar_generation_kwh
            r_solar = 2.0 * self_consumption_ratio - 1.0  # [0,1] -> [-1,1]
        else:
            r_solar = 0.0  # Sin solar, neutral
        components["r_solar"] = r_solar
        components["solar_kwh"] = solar_generation_kwh
        
        # 4. Recompensa Satisfacción EV (maximizar)
        # SOC cercano al objetivo = bueno
        ev_satisfaction = min(1.0, ev_soc_avg / self.context.ev_soc_target)
        r_ev = 2.0 * ev_satisfaction - 1.0
        # Bonus si se está cargando con solar
        if solar_generation_kwh > 0 and ev_charging_kwh > 0:
            solar_ev_ratio = min(1.0, ev_charging_kwh / solar_generation_kwh)
            r_ev += 0.2 * solar_ev_ratio
        r_ev = np.clip(r_ev, -1.0, 1.0)
        components["r_ev"] = r_ev
        components["ev_soc_avg"] = ev_soc_avg
        
        # 5. Recompensa Estabilidad de Red (minimizar picos)
        is_peak = hour in self.context.peak_hours
        demand_ratio = grid_import_kwh / max(1.0, self.context.peak_demand_limit_kw)
        
        if is_peak:
            # En hora pico, penalizar fuertemente alta demanda
            r_grid = 1.0 - 3.0 * min(1.0, demand_ratio)
        else:
            # Fuera de pico, más tolerante
            r_grid = 1.0 - 1.5 * min(1.0, demand_ratio)
        r_grid = np.clip(r_grid, -1.0, 1.0)
        components["r_grid"] = r_grid
        components["is_peak"] = float(is_peak)
        
        # Recompensa total ponderada
        reward = (
            self.weights.co2 * r_co2 +
            self.weights.cost * r_cost +
            self.weights.solar * r_solar +
            self.weights.ev_satisfaction * r_ev +
            self.weights.grid_stability * r_grid
        )
        
        components["reward_total"] = reward
        
        # Guardar historial
        self._reward_history.append(components)
        if len(self._reward_history) > self._max_history:
            self._reward_history.pop(0)
        
        return reward, components
    
    def get_pareto_metrics(self) -> Dict[str, float]:
        """Retorna métricas para análisis de Pareto."""
        if not self._reward_history:
            return {}
        
        metrics = {}
        for key in ["r_co2", "r_cost", "r_solar", "r_ev", "r_grid", "reward_total"]:
            values = [h.get(key, 0) for h in self._reward_history]
            metrics[f"{key}_mean"] = np.mean(values)
            metrics[f"{key}_std"] = np.std(values)
            metrics[f"{key}_min"] = np.min(values)
            metrics[f"{key}_max"] = np.max(values)
        
        # Métricas agregadas
        co2_total = sum(h.get("co2_kg", 0) for h in self._reward_history)
        cost_total = sum(h.get("cost_usd", 0) for h in self._reward_history)
        metrics["co2_total_kg"] = co2_total
        metrics["cost_total_usd"] = cost_total
        
        return metrics
    
    def reset_history(self):
        """Reinicia historial de recompensas."""
        self._reward_history = []


class CityLearnMultiObjectiveWrapper:
    """Wrapper para integrar recompensa multiobjetivo con CityLearn.
    
    Reemplaza la función de recompensa default de CityLearn con
    nuestra función multiobjetivo.
    """
    
    def __init__(
        self,
        env: Any,
        weights: Optional[MultiObjectiveWeights] = None,
        context: Optional[IquitosContext] = None,
    ):
        self.env = env
        self.reward_fn = MultiObjectiveReward(weights, context)
        self._last_obs = None
    
    def reset(self, **kwargs):
        """Reset environment."""
        obs, info = self.env.reset(**kwargs)
        self._last_obs = obs
        self.reward_fn.reset_history()
        return obs, info
    
    def step(self, action):
        """Step con recompensa multiobjetivo."""
        obs, original_reward, terminated, truncated, info = self.env.step(action)
        
        # Extraer métricas del ambiente
        buildings = getattr(self.env, "buildings", [])
        
        grid_import: float = 0.0
        grid_export: float = 0.0
        solar_gen: float = 0.0
        ev_charging: float = 0.0
        ev_soc_sum: float = 0.0
        ev_count: int = 0
        bess_soc: float = 0.5
        
        for b in buildings:
            # Grid
            net_elec = getattr(b, "net_electricity_consumption", [0])
            if hasattr(net_elec, '__len__') and len(net_elec) > 0:
                last_net = float(net_elec[-1])
                if last_net > 0:
                    grid_import += last_net
                else:
                    grid_export += abs(last_net)
            
            # Solar
            solar = getattr(b, "solar_generation", [0])
            if hasattr(solar, '__len__') and len(solar) > 0:
                solar_gen += float(solar[-1])
            
            # BESS
            storage = getattr(b, "electrical_storage", None)
            if storage:
                soc = getattr(storage, "soc", [0.5])
                if hasattr(soc, '__len__') and len(soc) > 0:
                    bess_soc = float(soc[-1])
                elif isinstance(soc, (int, float)):
                    bess_soc = float(soc)
                else:
                    bess_soc = 0.5
            
            # EVs
            ev_storage = getattr(b, "electric_vehicle_storage", None)
            if ev_storage:
                ev_elec = getattr(ev_storage, "electricity_consumption", [0])
                if hasattr(ev_elec, '__len__') and len(ev_elec) > 0:
                    ev_charging += float(ev_elec[-1])
                ev_soc = getattr(ev_storage, "soc", [0.5])
                if hasattr(ev_soc, '__len__') and len(ev_soc) > 0:
                    ev_soc_sum += float(ev_soc[-1])
                    ev_count += 1
        
        # Hora actual
        hour = 12
        if isinstance(obs, (list, tuple)) and len(obs) > 0:
            flat_obs = np.array(obs).ravel()
            if len(flat_obs) > 2:
                hour = int(flat_obs[2]) % 24
        
        ev_soc_avg = ev_soc_sum / max(1, ev_count)
        
        # Calcular recompensa multiobjetivo
        multi_reward, components = self.reward_fn.compute(
            grid_import_kwh=grid_import,
            grid_export_kwh=grid_export,
            solar_generation_kwh=solar_gen,
            ev_charging_kwh=ev_charging,
            ev_soc_avg=ev_soc_avg,
            bess_soc=bess_soc,
            hour=hour,
        )
        
        # Agregar componentes a info
        info["multi_objective"] = components
        info["original_reward"] = original_reward
        
        self._last_obs = obs
        return obs, multi_reward, terminated, truncated, info
    
    def __getattr__(self, name):
        """Delegar atributos no definidos al env original."""
        return getattr(self.env, name)


def create_iquitos_reward_weights(
    priority: str = "balanced"
) -> MultiObjectiveWeights:
    """Crea pesos predefinidos para diferentes prioridades.
    
    Args:
        priority: "balanced", "co2_focus", "cost_focus", "ev_focus", "solar_focus"
        
    Returns:
        MultiObjectiveWeights configurado
    """
    presets = {
        "balanced": MultiObjectiveWeights(
            co2=0.35, cost=0.25, solar=0.20, ev_satisfaction=0.15, grid_stability=0.05
        ),
        "co2_focus": MultiObjectiveWeights(
            co2=0.50, cost=0.15, solar=0.20, ev_satisfaction=0.10, grid_stability=0.05
        ),
        "cost_focus": MultiObjectiveWeights(
            co2=0.20, cost=0.45, solar=0.15, ev_satisfaction=0.15, grid_stability=0.05
        ),
        "ev_focus": MultiObjectiveWeights(
            co2=0.25, cost=0.20, solar=0.15, ev_satisfaction=0.35, grid_stability=0.05
        ),
        "solar_focus": MultiObjectiveWeights(
            co2=0.25, cost=0.15, solar=0.40, ev_satisfaction=0.15, grid_stability=0.05
        ),
    }
    
    if priority not in presets:
        logger.warning(f"Prioridad '{priority}' no reconocida, usando 'balanced'")
        priority = "balanced"
    
    return presets[priority]
