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
- 128 cargadores (112 motos @ 2kW + 16 mototaxis @ 3kW = 272 kW)
- Conteo pico: 900 motos + 130 mototaxis (19:00h, 19-oct-2025) → usado para dimensionar cargadores
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import logging
import gymnasium as gym

logger = logging.getLogger(__name__)


@dataclass
class MultiObjectiveWeights:
    """Pesos para función de recompensa multiobjetivo - TIER 1 FIXES APPLIED.

    Rebalanced para Iquitos (matriz térmica aislada):
    - CO₂ PRIMARY 0.50: minimizar importación grid
    - Solar SECONDARY 0.20: maximizar autoconsumo (FV limpio disponible)
    - Costo REDUCIDO 0.10: tarifa baja, no es constraint
    - Grid & EV 0.20 total: baseline de operación
    """
    co2: float = 0.50              # PRIMARY: Minimizar CO₂ (0.45 kg/kWh térmica)
    cost: float = 0.10             # REDUCIDO: costo no es bottleneck
    solar: float = 0.20            # SECUNDARIO: autoconsumo solar limpio
    ev_satisfaction: float = 0.10  # Satisfacción básica de carga
    grid_stability: float = 0.10   # REDUCIDO: implícito en CO₂+solar
    peak_import_penalty: float = 0.00  # Dinámico en compute(), no como peso fijo
    operational_penalties: float = 0.0  # Penalizaciones operacionales (BESS, EV fairness)

    def __post_init__(self):
        # Normalizar pesos base (sin peak_import_penalty que se aplica por separado)
        base_weights = [self.co2, self.cost, self.solar, self.ev_satisfaction, self.grid_stability]
        total = sum(base_weights)
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Pesos multiobjetivo no suman 1.0 (suma={total:.3f}), normalizando...")
            factor = 1.0 / total
            self.co2 *= factor
            self.cost *= factor
            self.solar *= factor
            self.ev_satisfaction *= factor
            self.grid_stability *= factor

    def as_dict(self) -> Dict[str, float]:
        return {
            "co2": self.co2,
            "cost": self.cost,
            "solar": self.solar,
            "ev_satisfaction": self.ev_satisfaction,
            "grid_stability": self.grid_stability,
            "peak_import_penalty": self.peak_import_penalty,
            "operational_penalties": self.operational_penalties,
        }


@dataclass
class IquitosContext:
    """Contexto específico de Iquitos para cálculos multiobjetivo."""
    # Factor de emisión (central térmica aislada)
    co2_factor_kg_per_kwh: float = 0.4521

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
        # Forzar pesos uniformizados si no se pasan explícitos
        if weights is None:
            weights = MultiObjectiveWeights(co2=0.50, cost=0.15, solar=0.20, ev_satisfaction=0.10, grid_stability=0.05)
        self.weights = weights
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

        MEJORADO: Penalizaciones más fuertes en horas pico (18-21h).

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
        is_peak = hour in self.context.peak_hours

        # 1. Recompensa CO₂ (minimizar) - TIER 1 FIX: Baselines Realistas
        co2_kg = grid_import_kwh * self.context.co2_factor_kg_per_kwh

        # Baselines basados en operación real Iquitos:
        # Off-peak: mall ~100 kW avg + chargers ~30 kW = 130 kWh/hora típico
        # Peak (18-21h): mall ~150 kW + chargers ~100 kW = 250 kWh/hora target
        co2_baseline_offpeak = 130.0  # kWh/hora típico off-peak
        co2_baseline_peak = 250.0     # kWh/hora target with BESS support en pico

        if is_peak:
            # En pico: penalizar fuertemente si superas target
            # Si importas 250 (target), reward = 1 - 2*(250/250) = -1 (penalty)
            # Si importas 100 (good), reward = 1 - 2*(100/250) = 0.2 (bonus)
            # Rango [-1, 1] con gradientes claros
            r_co2 = 1.0 - 2.0 * min(1.0, grid_import_kwh / co2_baseline_peak)
        else:
            # Off-peak: más tolerante pero aún penaliza exceso
            r_co2 = 1.0 - 1.0 * min(1.0, grid_import_kwh / co2_baseline_offpeak)

        r_co2 = np.clip(r_co2, -1.0, 1.0)
        components["r_co2"] = r_co2
        components["co2_kg"] = co2_kg

        # 2. Recompensa Costo (minimizar)
        cost_usd = (grid_import_kwh - grid_export_kwh) * self.context.tariff_usd_per_kwh
        cost_baseline = 100.0
        r_cost = 1.0 - 2.0 * min(1.0, max(0, cost_usd) / cost_baseline)
        r_cost = np.clip(r_cost, -1.0, 1.0)
        components["r_cost"] = r_cost
        components["cost_usd"] = cost_usd

        # 3. Recompensa Autoconsumo Solar (maximizar)
        if solar_generation_kwh > 0:
            solar_used = min(solar_generation_kwh, ev_charging_kwh + (grid_import_kwh * 0.5))
            self_consumption_ratio = solar_used / solar_generation_kwh
            r_solar = 2.0 * self_consumption_ratio - 1.0
        else:
            r_solar = 0.0
        r_solar = np.clip(r_solar, -1.0, 1.0)
        components["r_solar"] = r_solar
        components["solar_kwh"] = solar_generation_kwh

        # 4. Recompensa Satisfacción EV (maximizar) - REDUCIDA en peso
        ev_satisfaction = min(1.0, ev_soc_avg / self.context.ev_soc_target)
        r_ev = 2.0 * ev_satisfaction - 1.0
        if solar_generation_kwh > 0 and ev_charging_kwh > 0:
            solar_ev_ratio = min(1.0, ev_charging_kwh / solar_generation_kwh)
            r_ev += 0.1 * solar_ev_ratio  # Reducido bonus
        r_ev = np.clip(r_ev, -1.0, 1.0)
        components["r_ev"] = r_ev
        components["ev_soc_avg"] = ev_soc_avg

        # 5. Recompensa Estabilidad de Red (minimizar picos) - AHORA TIENE MAS PESO
        demand_ratio = grid_import_kwh / max(1.0, self.context.peak_demand_limit_kw)

        if is_peak:
            # En pico: Penalizar MUY fuertemente cualquier exceso
            # Si demand_ratio > 1.0 (exceso de limite), penalizacion es -2.0+
            r_grid = 1.0 - 4.0 * min(1.0, demand_ratio)
        else:
            # Fuera de pico: más tolerante
            r_grid = 1.0 - 2.0 * min(1.0, demand_ratio)
        r_grid = np.clip(r_grid, -1.0, 1.0)
        components["r_grid"] = r_grid
        components["is_peak"] = float(is_peak)

        # Penalizacion adicional por SOC bajo antes de pico - TIER 1 FIX: Normalizado correctamente
        pre_peak_hours = [16, 17]  # Horas 16-17 para preparar para 18-21h
        if hour in pre_peak_hours:
            soc_target_prepeak = 0.65  # Meta: 65% antes de pico
            if bess_soc < soc_target_prepeak:
                # Penalizar deficit (0 a -1)
                soc_deficit = soc_target_prepeak - bess_soc
                r_soc_reserve = 1.0 - (soc_deficit / soc_target_prepeak)  # [0, 1]
                components["r_soc_reserve"] = r_soc_reserve
            else:
                # Bonus si cumples target
                r_soc_reserve = 1.0
                components["r_soc_reserve"] = r_soc_reserve
        else:
            # Off pre-peak: sin penalización especial
            components["r_soc_reserve"] = 1.0

        soc_penalty = (components["r_soc_reserve"] - 1.0) * 0.5  # Escala [-0.5, 0]

        # Recompensa total ponderada - TIER 1 FIX: SOC penalty ahora ponderada
        reward = (
            self.weights.co2 * r_co2 +
            self.weights.cost * r_cost +
            self.weights.solar * r_solar +
            self.weights.ev_satisfaction * r_ev +
            self.weights.grid_stability * r_grid +
            0.10 * soc_penalty  # SOC penalty ponderada (0.10 weight)
        )

        # ✅ SAFETY FIX: Clipear y validar NaN/Inf
        reward = float(reward)  # Asegurar que es float
        if not np.isfinite(reward):
            logger.warning("[REWARD] NaN/Inf detected in reward: %.6e, clamping to -1.0", reward)
            reward = -1.0

        # Normalizar reward a [-1, 1] con clipping
        reward = np.clip(reward, -1.0, 1.0)
        components["reward_total"] = reward

        # Guardar historial
        self._reward_history.append(components)
        if len(self._reward_history) > self._max_history:
            self._reward_history.pop(0)

        return reward, components

    def compute_with_operational_penalties(
        self,
        grid_import_kwh: float,
        grid_export_kwh: float,
        solar_generation_kwh: float,
        ev_charging_kwh: float,
        ev_soc_avg: float,
        bess_soc: float,
        hour: int,
        ev_demand_kwh: float = 0.0,
        operational_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, Dict[str, float]]:
        """Computa recompensa multiobjetivo CON penalizaciones operacionales.

        Similar a compute() pero añade penalizaciones por:
        - Incumplimiento de reserva SOC pre-pico
        - Exceso de potencia en pico
        - Desequilibrio de fairness entre playas
        - Importación alta en hora pico

        Args:
            operational_state: Dict con claves opcionales:
                - bess_soc_target: SOC objetivo
                - is_peak_hour: bool
                - ev_power_motos_kw: potencia motos
                - ev_power_mototaxis_kw: potencia mototaxis
                - power_limit_total_kw: límite agregado
        """
        # Primero computar recompensa base
        reward_base, components = self.compute(
            grid_import_kwh=grid_import_kwh,
            grid_export_kwh=grid_export_kwh,
            solar_generation_kwh=solar_generation_kwh,
            ev_charging_kwh=ev_charging_kwh,
            ev_soc_avg=ev_soc_avg,
            bess_soc=bess_soc,
            hour=hour,
            ev_demand_kwh=ev_demand_kwh,
        )

        if operational_state is None or self.weights.operational_penalties <= 0:
            return reward_base, components

        # Computar penalizaciones operacionales
        penalties = {}

        # 1. Penalidad por reserva SOC incumplida
        soc_target = operational_state.get("bess_soc_target", 0.60)
        soc_deficit = max(0.0, soc_target - bess_soc)
        penalties["r_soc_reserve"] = -soc_deficit  # [-1, 0]

        # 2. Penalidad por potencia en pico
        is_peak = operational_state.get("is_peak_hour", False)
        if is_peak:
            power_total = (operational_state.get("ev_power_motos_kw", 0.0) +
                          operational_state.get("ev_power_mototaxis_kw", 0.0))
            power_limit = operational_state.get("power_limit_total_kw", 150.0)
            if power_total > power_limit:
                power_excess_ratio = (power_total - power_limit) / power_limit
                penalties["r_peak_power"] = -min(1.0, power_excess_ratio * 2.0)  # [-2, 0] -> [-1, 0]
            else:
                penalties["r_peak_power"] = 0.0
        else:
            penalties["r_peak_power"] = 0.0

        # 3. Penalidad por desequilibrio fairness
        power_motos = operational_state.get("ev_power_motos_kw", 0.0)
        power_mototaxis = operational_state.get("ev_power_mototaxis_kw", 0.0)
        if power_motos > 0 or power_mototaxis > 0:
            max_p = max(power_motos, power_mototaxis)
            min_p = min(power_motos, power_mototaxis)
            if min_p > 0:
                fairness_ratio = max_p / min_p
                fairness_penalty = -min(1.0, (fairness_ratio - 1.0) / 2.0)  # [-1, 0]
                penalties["r_fairness"] = fairness_penalty
            else:
                penalties["r_fairness"] = 0.0
        else:
            penalties["r_fairness"] = 0.0

        # 4. Penalidad por importación en pico
        if is_peak and grid_import_kwh > 50.0:
            import_excess = min(1.0, (grid_import_kwh - 50.0) / 100.0)
            penalties["r_import_peak"] = -import_excess * 0.8  # [-0.8, 0]
        else:
            penalties["r_import_peak"] = 0.0

        # Sumar penalizaciones
        r_operational = sum(penalties.values())
        r_operational = np.clip(r_operational, -1.0, 0.0)

        # Recompensa total ponderada incluyendo penalizaciones
        reward_total = (
            (1.0 - self.weights.operational_penalties) * reward_base +
            self.weights.operational_penalties * r_operational
        )

        # Agregar a componentes
        components["r_operational"] = r_operational
        components.update({f"r_penalty_{k}": v for k, v in penalties.items()})
        components["reward_total_with_penalties"] = reward_total

        return reward_total, components

    def get_pareto_metrics(self) -> Dict[str, float]:
        """Retorna métricas para análisis de Pareto."""
        if not self._reward_history:
            return {}

        metrics: Dict[str, float] = {}
        for key in ["r_co2", "r_cost", "r_solar", "r_ev", "r_grid", "reward_total"]:
            values = [h.get(key, 0) for h in self._reward_history]
            metrics[f"{key}_mean"] = float(np.mean(values))
            metrics[f"{key}_std"] = float(np.std(values))
            metrics[f"{key}_min"] = float(np.min(values))
            metrics[f"{key}_max"] = float(np.max(values))

        # Métricas agregadas
        co2_total: float = float(sum(h.get("co2_kg", 0) for h in self._reward_history))
        cost_total: float = float(sum(h.get("cost_usd", 0) for h in self._reward_history))
        metrics["co2_total_kg"] = co2_total
        metrics["cost_total_usd"] = cost_total

        return metrics

    def reset_history(self):
        """Reinicia historial de recompensas."""
        self._reward_history = []


class CityLearnMultiObjectiveWrapper(gym.Env):
    """Wrapper para integrar recompensa multiobjetivo con CityLearn.

    Reemplaza la función de recompensa default de CityLearn con
    nuestra función multiobjetivo. Hereda de gymnasium.Env para
    compatibilidad con stable-baselines3.
    """

    def __init__(
        self,
        env: Any,
        weights: Optional[MultiObjectiveWeights] = None,
        context: Optional[IquitosContext] = None,
    ):
        super().__init__()
        self.env = env
        self.reward_fn = MultiObjectiveReward(weights, context)
        self._last_obs = None

        # Copiar espacios de observation y action del env original
        self.observation_space = env.observation_space
        self.action_space = env.action_space
        self.metadata = getattr(env, 'metadata', {})

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
        buildings = getattr(self.env, "buildings", [])  # type: ignore[assignment]

        # Inicializar acumuladores para extraer métricas
        grid_import = 0.0
        grid_export = 0.0
        solar_gen = 0.0
        ev_charging = 0.0
        ev_soc_sum = 0.0
        ev_count = 0
        bess_soc = 0.5

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

    def close(self):
        """Close environment."""
        if hasattr(self.env, 'close'):
            self.env.close()


def create_iquitos_reward_weights(
    priority: str = "co2_focus"
) -> MultiObjectiveWeights:
    """Crea pesos predefinidos para diferentes prioridades.

    Args:
        priority: "balanced", "co2_focus", "cost_focus", "ev_focus", "solar_focus"

    Returns:
        MultiObjectiveWeights configurado
    """
    # Versión estándar (todos los casos ahora usan esto)
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

    return presets.get(priority, presets["balanced"])
