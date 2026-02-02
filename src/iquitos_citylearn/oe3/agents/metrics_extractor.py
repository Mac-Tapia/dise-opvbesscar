"""
================================================================================
METRICS EXTRACTOR - Extracción ROBUSTA de métricas de CityLearn
================================================================================

Este módulo centraliza la extracción de métricas del ambiente CityLearn.
Los callbacks de SAC, PPO y A2C DEBEN usar estas funciones para garantizar
consistencia y corrección en el logging de métricas.

PROBLEMA RESUELTO:
- Los callbacks anteriores NO capturaban datos solares (siempre 0.0)
- Los valores de grid eran incorrectos (acumulación infinita)
- No se reseteaban las métricas por episodio correctamente

SOLUCIÓN:
- Extracción centralizada desde CityLearn energy_simulation (datos CSV)
- Fallback a valores de la observación (394-dim) si no hay energy_simulation
- Funciones de utilidad para normalizar y validar datos

USO EN CALLBACKS:
    from iquitos_citylearn.oe3.agents.metrics_extractor import extract_step_metrics

    # En _on_step():
    metrics = extract_step_metrics(self.training_env, self.n_calls)
    self.grid_energy_sum += metrics['grid_import_kwh']
    self.solar_energy_sum += metrics['solar_generation_kwh']

FECHA: 2026-02-02
AUTOR: GitHub Copilot
================================================================================
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Factores de CO₂ para Iquitos (constantes globales)
CO2_GRID_FACTOR_KG_PER_KWH = 0.4521  # Central térmica aislada
CO2_EV_FACTOR_KG_PER_KWH = 2.146     # Conversión directa (EVs vs combustión)
EV_DEMAND_CONSTANT_KW = 50.0        # Demanda constante de cargadores (workaround CityLearn)


def get_unwrapped_env(env: Any) -> Any:
    """Desenvuelve el environment hasta llegar al CityLearnEnv base.

    Args:
        env: Environment wrapped (puede ser VecEnv, Monitor, etc.)

    Returns:
        Environment base de CityLearn
    """
    # Si es VecEnv de SB3, extraer el primer env
    if hasattr(env, 'envs') and len(env.envs) > 0:
        env = env.envs[0]

    # Desenvolver iterativamente
    max_depth = 10
    for _ in range(max_depth):
        if hasattr(env, 'unwrapped'):
            env = env.unwrapped
            break
        elif hasattr(env, 'env'):
            env = env.env
        else:
            break

    return env


def extract_step_metrics(
    training_env: Any,
    time_step: int,
    obs: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Extrae métricas del paso actual desde CityLearn.

    MÉTODO ROBUSTO: Intenta múltiples fuentes de datos:
    1. energy_simulation (datos del CSV - PREFERIDO)
    2. Propiedades del building (solar_generation, net_electricity_consumption)
    3. Observación (394-dim vector)
    4. Fallback a valores por defecto

    Args:
        training_env: Environment de training (puede estar wrapped)
        time_step: Paso actual de la simulación (0-8759)
        obs: Observación actual (opcional, 394-dim)

    Returns:
        Dict con métricas:
        - grid_import_kwh: Energía importada del grid (kWh)
        - grid_export_kwh: Energía exportada al grid (kWh)
        - solar_generation_kwh: Generación solar (kWh)
        - ev_demand_kwh: Demanda de cargadores EV (kWh)
        - mall_demand_kwh: Demanda del mall (kWh)
        - bess_soc: SOC del BESS (0-1)
        - hour: Hora del día (0-23)
        - source: Fuente de los datos ('energy_simulation', 'building', 'observation', 'fallback')
    """
    # Usar Dict[str, Any] para permitir valores float y string
    metrics: Dict[str, Any] = {
        'grid_import_kwh': 0.0,
        'grid_export_kwh': 0.0,
        'solar_generation_kwh': 0.0,
        'ev_demand_kwh': EV_DEMAND_CONSTANT_KW,  # Default
        'mall_demand_kwh': 100.0,  # Default
        'bess_soc': 0.5,  # Default
        'hour': float(time_step % 24),
        'source': 'fallback',
    }

    # Desenvolver environment
    env = get_unwrapped_env(training_env)

    # Obtener buildings
    buildings = getattr(env, 'buildings', None)
    if not buildings or len(buildings) == 0:
        logger.debug("[METRICS] No buildings found, using fallback values")
        return metrics

    b = buildings[0]
    t = time_step % 8760  # Asegurar índice válido

    # ========================================================================
    # MÉTODO 1: energy_simulation (datos del CSV - MÁS CONFIABLE)
    # ========================================================================
    energy_sim = getattr(b, 'energy_simulation', None)
    if energy_sim is not None:
        try:
            # Solar generation (datos del CSV)
            solar_arr = getattr(energy_sim, 'solar_generation', None)
            if solar_arr is not None and hasattr(solar_arr, '__len__') and len(solar_arr) > t:
                val = float(solar_arr[t])
                # CityLearn reporta solar como valores negativos a veces
                metrics['solar_generation_kwh'] = abs(val) if val < 0 else val
                metrics['source'] = 'energy_simulation'

            # Non-shiftable load (mall demand)
            load_arr = getattr(energy_sim, 'non_shiftable_load', None)
            if load_arr is not None and hasattr(load_arr, '__len__') and len(load_arr) > t:
                metrics['mall_demand_kwh'] = float(load_arr[t])

            logger.debug(
                "[METRICS] energy_simulation t=%d: solar=%.2f, mall=%.2f",
                t, metrics['solar_generation_kwh'], metrics['mall_demand_kwh']
            )

        except (IndexError, TypeError, ValueError) as e:
            logger.debug("[METRICS] energy_simulation extraction error: %s", e)

    # ========================================================================
    # MÉTODO 2: Propiedades del building (datos de runtime)
    # ========================================================================
    if metrics['source'] == 'fallback':
        try:
            # Solar generation
            solar_gen = getattr(b, 'solar_generation', None)
            if solar_gen is not None:
                if isinstance(solar_gen, (list, tuple, np.ndarray)) and len(solar_gen) > 0:
                    val = float(solar_gen[-1])  # Último valor registrado
                    metrics['solar_generation_kwh'] = abs(val) if val < 0 else val
                    metrics['source'] = 'building'
                elif isinstance(solar_gen, (int, float)):
                    metrics['solar_generation_kwh'] = abs(float(solar_gen))
                    metrics['source'] = 'building'

            # Net electricity consumption (grid)
            net_elec = getattr(b, 'net_electricity_consumption', None)
            if net_elec is not None:
                if isinstance(net_elec, (list, tuple, np.ndarray)) and len(net_elec) > 0:
                    val = float(net_elec[-1])
                    if val > 0:
                        metrics['grid_import_kwh'] = val
                    else:
                        metrics['grid_export_kwh'] = abs(val)

            # BESS SOC
            es = getattr(b, 'electrical_storage', None)
            if es is not None:
                soc = getattr(es, 'soc', None) or getattr(es, 'state_of_charge', None)
                if soc is not None:
                    if isinstance(soc, (list, tuple, np.ndarray)) and len(soc) > 0:
                        soc_val = float(soc[-1])
                    else:
                        soc_val = float(soc)
                    # Normalizar a 0-1
                    metrics['bess_soc'] = soc_val if soc_val <= 1.0 else soc_val / 100.0

        except (IndexError, TypeError, ValueError, AttributeError) as e:
            logger.debug("[METRICS] building extraction error: %s", e)

    # ========================================================================
    # MÉTODO 3: Observación (394-dim vector)
    # ========================================================================
    if obs is not None and metrics['source'] == 'fallback':
        try:
            obs_arr = np.asarray(obs, dtype=float).ravel()

            if len(obs_arr) >= 394:
                # Estructura CityLearn 394-dim:
                # obs[0] = solar_generation
                # obs[2] = BESS SOC (0-1)
                # obs[3] = mall_demand
                # obs[4:132] = 128 charger demands
                metrics['solar_generation_kwh'] = abs(float(obs_arr[0]))
                metrics['bess_soc'] = float(obs_arr[2])
                metrics['mall_demand_kwh'] = float(obs_arr[3])

                charger_demands = obs_arr[4:132]
                metrics['ev_demand_kwh'] = float(np.sum(np.maximum(charger_demands, 0.0)))

                metrics['source'] = 'observation'

            elif len(obs_arr) >= 132:
                # Observación parcial
                metrics['solar_generation_kwh'] = abs(float(obs_arr[0])) if len(obs_arr) > 0 else 0.0
                metrics['bess_soc'] = float(obs_arr[2]) if len(obs_arr) > 2 else 0.5
                metrics['mall_demand_kwh'] = float(obs_arr[3]) if len(obs_arr) > 3 else 100.0

                if len(obs_arr) > 4:
                    charger_demands = obs_arr[4:min(132, len(obs_arr))]
                    metrics['ev_demand_kwh'] = float(np.sum(np.maximum(charger_demands, 0.0)))

                metrics['source'] = 'observation_partial'

        except (TypeError, ValueError, IndexError) as e:
            logger.debug("[METRICS] observation extraction error: %s", e)

    # ========================================================================
    # CALCULAR GRID IMPORT (si no se obtuvo directamente)
    # ========================================================================
    if metrics['grid_import_kwh'] == 0.0 and metrics['source'] != 'fallback':
        # Grid = demanda total - solar
        total_demand = metrics['mall_demand_kwh'] + metrics['ev_demand_kwh']
        grid_needed = max(0.0, total_demand - metrics['solar_generation_kwh'])
        metrics['grid_import_kwh'] = grid_needed

        # Si hay excedente solar, es exportación
        if metrics['solar_generation_kwh'] > total_demand:
            metrics['grid_export_kwh'] = metrics['solar_generation_kwh'] - total_demand

    # Validación de rangos
    metrics['solar_generation_kwh'] = max(0.0, min(5000.0, metrics['solar_generation_kwh']))
    metrics['grid_import_kwh'] = max(0.0, min(10000.0, metrics['grid_import_kwh']))
    metrics['bess_soc'] = max(0.0, min(1.0, metrics['bess_soc']))

    return metrics


def calculate_co2_metrics(
    grid_import_kwh: float,
    solar_generation_kwh: float,
    ev_demand_kwh: float,
) -> Dict[str, float]:
    """Calcula métricas de CO₂ para un step.

    Args:
        grid_import_kwh: Energía importada del grid (kWh)
        solar_generation_kwh: Generación solar total (kWh)
        ev_demand_kwh: Demanda de cargadores EV (kWh)

    Returns:
        Dict con métricas de CO₂:
        - co2_grid_kg: Emisiones por importación de grid
        - co2_indirect_avoided_kg: Emisiones evitadas por usar solar
        - co2_direct_avoided_kg: Emisiones evitadas por EVs (vs combustión)
        - co2_net_kg: Balance neto de CO₂
    """
    # CO₂ por importación de grid
    co2_grid_kg = grid_import_kwh * CO2_GRID_FACTOR_KG_PER_KWH

    # CO₂ INDIRECTO evitado: solar generado evita importar del grid térmico
    co2_indirect_avoided_kg = solar_generation_kwh * CO2_GRID_FACTOR_KG_PER_KWH

    # CO₂ DIRECTO evitado: EVs cargados evitan combustión
    # ev_demand_kwh * km_per_kwh * (galones_evitados/km) * kg_co2/galón
    # Simplificado: ev_demand_kwh * factor_directo
    co2_direct_avoided_kg = ev_demand_kwh * CO2_EV_FACTOR_KG_PER_KWH

    # Balance neto
    co2_net_kg = co2_grid_kg - co2_indirect_avoided_kg - co2_direct_avoided_kg

    return {
        'co2_grid_kg': co2_grid_kg,
        'co2_indirect_avoided_kg': co2_indirect_avoided_kg,
        'co2_direct_avoided_kg': co2_direct_avoided_kg,
        'co2_net_kg': co2_net_kg,
    }


class EpisodeMetricsAccumulator:
    """Acumulador de métricas por episodio.

    Uso:
        accumulator = EpisodeMetricsAccumulator()

        # En cada step:
        metrics = extract_step_metrics(env, step)
        accumulator.accumulate(metrics)

        # Al final del episodio:
        episode_metrics = accumulator.get_episode_metrics()
        accumulator.reset()
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Reinicia acumuladores para nuevo episodio."""
        self.grid_import_kwh = 0.0
        self.grid_export_kwh = 0.0
        self.solar_generation_kwh = 0.0
        self.ev_demand_kwh = 0.0
        self.mall_demand_kwh = 0.0
        self.step_count = 0
        self.reward_sum = 0.0
        self.reward_count = 0
        self._rewards_window: list[float] = []
        self._window_size = 200  # Ventana móvil para reward promedio

        # Contadores de vehículos
        self.motos_cargadas = 0
        self.mototaxis_cargadas = 0

        # CO₂ acumulado
        self.co2_grid_kg = 0.0
        self.co2_indirect_avoided_kg = 0.0
        self.co2_direct_avoided_kg = 0.0

    def accumulate(self, metrics: Dict[str, float], reward: Optional[float] = None):
        """Acumula métricas de un step.

        Args:
            metrics: Dict retornado por extract_step_metrics()
            reward: Recompensa del step (opcional)
        """
        self.grid_import_kwh += metrics.get('grid_import_kwh', 0.0)
        self.grid_export_kwh += metrics.get('grid_export_kwh', 0.0)
        self.solar_generation_kwh += metrics.get('solar_generation_kwh', 0.0)
        self.ev_demand_kwh += metrics.get('ev_demand_kwh', EV_DEMAND_CONSTANT_KW)
        self.mall_demand_kwh += metrics.get('mall_demand_kwh', 100.0)
        self.step_count += 1

        if reward is not None:
            self.reward_sum += reward
            self.reward_count += 1
            self._rewards_window.append(reward)
            if len(self._rewards_window) > self._window_size:
                self._rewards_window.pop(0)

        # Calcular CO₂
        co2 = calculate_co2_metrics(
            metrics.get('grid_import_kwh', 0.0),
            metrics.get('solar_generation_kwh', 0.0),
            metrics.get('ev_demand_kwh', EV_DEMAND_CONSTANT_KW),
        )
        self.co2_grid_kg += co2['co2_grid_kg']
        self.co2_indirect_avoided_kg += co2['co2_indirect_avoided_kg']
        self.co2_direct_avoided_kg += co2['co2_direct_avoided_kg']

        # Contar vehículos (80% motos 2kW, 20% mototaxis 3kW)
        ev_demand = metrics.get('ev_demand_kwh', EV_DEMAND_CONSTANT_KW)
        self.motos_cargadas += int((ev_demand * 0.80) / 2.0)
        self.mototaxis_cargadas += int((ev_demand * 0.20) / 3.0)

    def get_reward_avg(self) -> float:
        """Retorna reward promedio de la ventana móvil."""
        if len(self._rewards_window) > 0:
            return sum(self._rewards_window) / len(self._rewards_window)
        return 0.0

    def get_episode_metrics(self) -> Dict[str, float]:
        """Retorna métricas acumuladas del episodio."""
        return {
            'grid_import_kwh': self.grid_import_kwh,
            'grid_export_kwh': self.grid_export_kwh,
            'solar_generation_kwh': self.solar_generation_kwh,
            'ev_demand_kwh': self.ev_demand_kwh,
            'mall_demand_kwh': self.mall_demand_kwh,
            'step_count': self.step_count,
            'reward_sum': self.reward_sum,
            'reward_avg': self.get_reward_avg(),
            'motos_cargadas': self.motos_cargadas,
            'mototaxis_cargadas': self.mototaxis_cargadas,
            'co2_grid_kg': self.co2_grid_kg,
            'co2_indirect_avoided_kg': self.co2_indirect_avoided_kg,
            'co2_direct_avoided_kg': self.co2_direct_avoided_kg,
            'co2_net_kg': self.co2_grid_kg - self.co2_indirect_avoided_kg - self.co2_direct_avoided_kg,
            'co2_total_avoided_kg': self.co2_indirect_avoided_kg + self.co2_direct_avoided_kg,
        }

    def log_step_metrics(self, agent_name: str, step: int, episode: int):
        """Loguea métricas del paso actual."""
        logger.info(
            "[%s] paso %d | ep~%d | grid_kWh=%.1f | solar_kWh=%.1f | "
            "co2_grid=%.1f | co2_indirect=%.1f | co2_direct=%.1f | "
            "motos=%d | mototaxis=%d | reward_avg=%.4f",
            agent_name, step, episode,
            self.grid_import_kwh, self.solar_generation_kwh,
            self.co2_grid_kg, self.co2_indirect_avoided_kg, self.co2_direct_avoided_kg,
            self.motos_cargadas, self.mototaxis_cargadas,
            self.get_reward_avg(),
        )

    def log_episode_metrics(self, agent_name: str, episode: int, episode_reward: float, episode_length: int, global_step: int):
        """Loguea métricas finales del episodio."""
        metrics = self.get_episode_metrics()
        logger.info(
            "[%s] ep %d | reward=%.4f | len=%d | step=%d | "
            "grid_kWh=%.1f | solar_kWh=%.1f | "
            "co2_grid=%.1f | co2_indirect=%.1f | co2_direct=%.1f | co2_net=%.1f | "
            "motos=%d | mototaxis=%d",
            agent_name, episode, episode_reward, episode_length, global_step,
            metrics['grid_import_kwh'], metrics['solar_generation_kwh'],
            metrics['co2_grid_kg'], metrics['co2_indirect_avoided_kg'],
            metrics['co2_direct_avoided_kg'], metrics['co2_net_kg'],
            metrics['motos_cargadas'], metrics['mototaxis_cargadas'],
        )
