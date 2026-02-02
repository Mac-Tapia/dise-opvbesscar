# 🔧 IMPLEMENTACIÓN: FIX #2 - Integrar MultiObjectiveReward en SAC
# src/iquitos_citylearn/oe3/agents/sac.py - WRAPPER MULTIOBJETIVO

import numpy as np
import gymnasium as gym
from typing import Any, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MultiObjectiveRewardWrapper(gym.Wrapper):
    """Wrapper que INTEGRA MultiObjectiveReward.compute() en el loop de training.

    Este wrapper REEMPLAZA el reward genérico de CityLearn con:
    - r_co2: Minimización de CO₂ indirecto (maximizar solar)
    - r_solar: Autoconsumo solar directo
    - r_cost: Minimización de costo eléctrico
    - r_ev: Satisfacción de carga de vehículos
    - r_grid: Estabilidad de red (minimizar picos)

    El reward final es una combinación ponderada:
    r_final = w_co2*r_co2 + w_solar*r_solar + w_cost*r_cost + w_ev*r_ev + w_grid*r_grid

    CRÍTICO: Este wrapper debe aplicarse DESPUÉS de CityLearnWrapper
    pero ANTES de Monitor.
    """

    def __init__(
        self,
        env: Any,
        reward_fn: Any,  # MultiObjectiveReward instance
        log_interval_steps: int = 100,
    ):
        """Inicializa wrapper multiobjetivo.

        Args:
            env: Env base (CityLearnWrapper)
            reward_fn: Instancia de MultiObjectiveReward
            log_interval_steps: Cada cuántos steps loguear componentes
        """
        super().__init__(env)
        self.reward_fn = reward_fn
        self.log_interval_steps = log_interval_steps
        self._step_counter = 0

        # Accumuladores para estadísticas
        self._episode_rewards = []
        self._episode_components = {
            "r_co2": [],
            "r_solar": [],
            "r_cost": [],
            "r_ev": [],
            "r_grid": [],
            "co2_grid_kg": [],
            "co2_avoided_kg": [],
        }

    def reset(self, **kwargs):
        """Reset environment y contadores."""
        obs, info = self.env.reset(**kwargs)
        self._episode_rewards = []
        for key in self._episode_components:
            self._episode_components[key] = []
        self._step_counter = 0
        return obs, info

    def step(self, action: np.ndarray) -> Tuple[Any, float, bool, bool, Dict]:
        """Step environment y CALCULAR reward multiobjetivo.

        Proceso:
        1. env.step(action) → obs, reward_original, terminated, truncated, info
        2. Extraer métricas del environment (grid, solar, EV, BESS, hora)
        3. reward_fn.compute() → r_co2, r_solar, r_cost, r_ev, r_grid, componentes
        4. Reward final = weighted sum de componentes
        5. Loguear componentes cada log_interval_steps
        6. Retornar (obs, reward_final, terminated, truncated, info_enriquecido)
        """
        # ✅ PASO 1: Step environment
        try:
            obs, reward_original, terminated, truncated, info = self.env.step(action)
        except Exception as e:
            logger.error(f"Error en env.step: {e}, retornando reward=0")
            obs = self.env.reset()[0]  # Reset and return safe obs
            return obs, 0.0, True, False, {"error": str(e)}

        # ✅ PASO 2: Extraer métricas para reward multiobjetivo
        metrics = self._extract_metrics_from_env()

        # ✅ PASO 3: Calcular reward multiobjetivo
        try:
            reward_multi, components = self.reward_fn.compute(
                grid_import_kwh=metrics["grid_import"],
                grid_export_kwh=metrics["grid_export"],
                solar_generation_kwh=metrics["solar_generation"],
                ev_charging_kwh=metrics["ev_charging"],
                ev_soc_avg=metrics["ev_soc_avg"],
                bess_soc=metrics["bess_soc"],
                hour=metrics["hour"],
                ev_demand_kwh=metrics["ev_demand"],
            )
        except Exception as e:
            logger.error(f"Error calculando reward multiobjetivo: {e}, usando reward_original")
            reward_multi = reward_original
            components = {}

        # ✅ PASO 4: Guardar componentes para logging
        self._episode_rewards.append(reward_multi)
        for key in ["r_co2", "r_solar", "r_cost", "r_ev", "r_grid",
                    "co2_grid_kg", "co2_avoided_indirect_kg"]:
            if key in components:
                self._episode_components[key].append(components[key])

        # ✅ PASO 5: Logging periódico
        self._step_counter += 1
        if self._step_counter % self.log_interval_steps == 0:
            self._log_components(components)

        # ✅ PASO 6: Enriquecer info con componentes multiobjetivo
        info["multi_objective"] = components
        info["reward_multi"] = reward_multi
        info["reward_original"] = reward_original

        # Agregar componentes como top-level keys para fácil acceso
        for key in ["r_co2", "r_solar", "r_cost", "r_ev", "r_grid"]:
            if key in components:
                info[key] = components[key]

        return obs, reward_multi, terminated, truncated, info

    def _extract_metrics_from_env(self) -> Dict[str, float]:
        """Extrae todas las métricas necesarias del environment.

        Métricas extraídas:
        - grid_import: Energía importada de la red (kWh)
        - grid_export: Energía exportada a la red (kWh)
        - solar_generation: Generación solar disponible (kWh)
        - ev_charging: Energía entregada a EVs (kWh)
        - ev_soc_avg: SOC promedio de EVs [0-1]
        - bess_soc: SOC del BESS [0-1]
        - hour: Hora del día [0-23]
        - ev_demand: Demanda EV total (kWh)

        Retorna:
            Dict con todas las métricas, con defaults seguro si faltan
        """
        metrics = {
            "grid_import": 0.0,
            "grid_export": 0.0,
            "solar_generation": 0.0,
            "ev_charging": 0.0,
            "ev_soc_avg": 0.5,
            "bess_soc": 0.5,
            "hour": 12,
            "ev_demand": 50.0,  # Demanda constante OE2
        }

        try:
            # ✅ Extraer por building
            buildings = getattr(self.env, "buildings", []) or getattr(self.env.env, "buildings", [])

            for building in buildings:
                # Grid import/export (net electricity consumption)
                net_elec = getattr(building, "net_electricity_consumption", None) or []
                if net_elec and len(net_elec) > 0:
                    net_val = float(net_elec[-1])
                    metrics["grid_import"] += max(0.0, net_val)
                    metrics["grid_export"] += max(0.0, -net_val)

                # Solar generation
                solar_gen = getattr(building, "solar_generation", None) or []
                if solar_gen and len(solar_gen) > 0:
                    metrics["solar_generation"] += max(0.0, float(solar_gen[-1]))

                # EV charging (puede estar en EV storage o chargers)
                ev_storage = getattr(building, "electric_vehicle_storage", None)
                if ev_storage:
                    ev_elec = getattr(ev_storage, "electricity_consumption", None) or []
                    if ev_elec and len(ev_elec) > 0:
                        metrics["ev_charging"] += max(0.0, float(ev_elec[-1]))

                    ev_soc = getattr(ev_storage, "state_of_charge", None) or []
                    if ev_soc and len(ev_soc) > 0:
                        metrics["ev_soc_avg"] = float(ev_soc[-1])

                # BESS SOC
                bess = getattr(building, "electrical_storage", None)
                if bess:
                    bess_soc = getattr(bess, "state_of_charge", None) or []
                    if bess_soc and len(bess_soc) > 0:
                        metrics["bess_soc"] = float(bess_soc[-1])

            # ✅ Extraer hora del día
            time_step = getattr(self.env, "time_step", 0) or getattr(self.env.env, "time_step", 0)
            metrics["hour"] = int(time_step % 24)

        except Exception as e:
            logger.debug(f"Error extrayendo métricas (usando defaults): {e}")

        return metrics

    def _log_components(self, components: Dict[str, float]):
        """Loguea componentes multiobjetivo cada log_interval_steps."""
        msg = f"[STEP {self._step_counter}] "

        # Componentes de reward
        if "r_co2" in components:
            msg += f"r_co2={components['r_co2']:.4f} "
        if "r_solar" in components:
            msg += f"r_solar={components['r_solar']:.4f} "
        if "r_cost" in components:
            msg += f"r_cost={components['r_cost']:.4f} "
        if "r_ev" in components:
            msg += f"r_ev={components['r_ev']:.4f} "
        if "r_grid" in components:
            msg += f"r_grid={components['r_grid']:.4f} "
        if "reward_total" in components:
            msg += f"| TOTAL={components['reward_total']:.4f}"

        # Métricas CO₂
        if "co2_grid_kg" in components:
            msg += f" | CO₂_grid={components['co2_grid_kg']:.1f}kg "
        if "co2_avoided_indirect_kg" in components:
            msg += f"CO₂_avoided={components['co2_avoided_indirect_kg']:.1f}kg"

        logger.info(msg)

    def get_episode_stats(self) -> Dict[str, float]:
        """Retorna estadísticas del episodio actual."""
        stats = {}

        if self._episode_rewards:
            stats["reward_mean"] = float(np.mean(self._episode_rewards))
            stats["reward_std"] = float(np.std(self._episode_rewards))
            stats["reward_min"] = float(np.min(self._episode_rewards))
            stats["reward_max"] = float(np.max(self._episode_rewards))

        for key in ["r_co2", "r_solar", "r_cost", "r_ev", "r_grid"]:
            values = self._episode_components.get(key, [])
            if values:
                stats[f"{key}_mean"] = float(np.mean(values))
                stats[f"{key}_std"] = float(np.std(values))

        return stats


def create_sac_with_multiobjectve_training(
    env: Any,
    sac_config: "SACConfig",
    use_multiobjectve: bool = True,
    multiobjectve_priority: str = "balanced",
    log_interval_steps: int = 100,
) -> Tuple[Any, Optional["MultiObjectiveReward"]]:
    """Factory para crear environment wrapper con multiobjetivo.

    Retorna:
        (env_wrapped, reward_fn)
    donde env_wrapped puede pasarse directamente a SAC.learn()
    """

    if not use_multiobjectve:
        logger.info("[SAC] Multiobjetivo DESHABILITADO, entrenando con rewards genéricos")
        return env, None

    # ✅ Importar reward framework
    try:
        from ..rewards import MultiObjectiveReward, MultiObjectiveWeights, IquitosContext
    except ImportError as e:
        logger.warning(f"No se pudo importar MultiObjectiveReward: {e}")
        return env, None

    # ✅ Crear pesos desde config
    weights = MultiObjectiveWeights(
        co2=sac_config.weight_co2,
        solar=sac_config.weight_solar,
        cost=sac_config.weight_cost,
        ev_satisfaction=sac_config.weight_ev_satisfaction,
        grid_stability=sac_config.weight_grid_stability,
    )

    # ✅ Crear contexto Iquitos
    context = IquitosContext(
        co2_factor_kg_per_kwh=sac_config.co2_target_kg_per_kwh,
        co2_conversion_factor=sac_config.co2_conversion_factor,
        tariff_usd_per_kwh=sac_config.cost_target_usd_per_kwh,
        ev_demand_constant_kw=sac_config.ev_demand_constant_kw,
        ev_soc_target=sac_config.ev_soc_target,
        peak_demand_limit_kw=sac_config.peak_demand_limit_kw,
    )

    # ✅ Crear reward function
    reward_fn = MultiObjectiveReward(weights, context)

    # ✅ Crear wrapper multiobjetivo
    env_wrapped = MultiObjectiveRewardWrapper(
        env,
        reward_fn,
        log_interval_steps=log_interval_steps,
    )

    logger.info("[SAC] Multiobjetivo HABILITADO")
    logger.info(f"  - CO₂ weight: {weights.co2:.2f}")
    logger.info(f"  - Solar weight: {weights.solar:.2f}")
    logger.info(f"  - Cost weight: {weights.cost:.2f}")
    logger.info(f"  - EV weight: {weights.ev_satisfaction:.2f}")
    logger.info(f"  - Grid weight: {weights.grid_stability:.2f}")
    logger.info(f"  - CO₂ factor: {context.co2_factor_kg_per_kwh:.4f} kg/kWh")

    return env_wrapped, reward_fn
