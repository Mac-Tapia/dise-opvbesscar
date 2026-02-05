"""Metrics extraction for CityLearn episodes."""

from __future__ import annotations

from typing import Any, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class EpisodeMetricsAccumulator:
    """Acumulador de métricas durante un episodio completo.

    Mantiene un registro continuo de:
    - Energía del grid
    - Generación solar
    - Recompensas
    - Emisiones de CO2
    - Cargas de EV
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Resetea todos los acumuladores para nuevo episodio."""
        self.grid_import_kwh = 0.0
        self.solar_generation_kwh = 0.0
        self.reward_sum = 0.0
        self.step_count = 0
        self.co2_grid_kg = 0.0
        self.co2_direct_avoided_kg = 0.0
        self.co2_indirect_avoided_kg = 0.0
        self.motos_cargadas = 0
        self.mototaxis_cargadas = 0
        self.co2_intensity_grid = 0.4521  # kg CO2/kWh (Iquitos)

    def accumulate(self, step_metrics: dict[str, float], reward: float = 0.0):
        """Acumula métricas de un step.

        Args:
            step_metrics: Diccionario con grid_kWh, solar_kWh, co2_kg, etc.
            reward: Recompensa del step
        """
        self.grid_import_kwh += float(step_metrics.get("grid_kWh", 0.0))
        self.solar_generation_kwh += float(step_metrics.get("solar_kWh", 0.0))
        self.reward_sum += float(reward)
        self.step_count += 1

        # CO2
        grid_value = float(step_metrics.get("grid_kWh", 0.0))
        if grid_value > 0:
            self.co2_grid_kg += grid_value * self.co2_intensity_grid

    def get_episode_metrics(self) -> dict[str, float]:
        """Retorna métricas acumuladas del episodio.

        Returns:
            Diccionario con todas las métricas
        """
        total_avoided = self.co2_direct_avoided_kg + self.co2_indirect_avoided_kg
        net_co2 = self.co2_grid_kg - total_avoided

        return {
            "grid_import_kwh": self.grid_import_kwh,
            "solar_generation_kwh": self.solar_generation_kwh,
            "co2_grid_kg": self.co2_grid_kg,
            "co2_direct_avoided_kg": self.co2_direct_avoided_kg,
            "co2_indirect_avoided_kg": self.co2_indirect_avoided_kg,
            "co2_total_avoided_kg": total_avoided,
            "co2_net_kg": net_co2,
            "reward_avg": self.reward_sum / max(1, self.step_count),
            "reward_sum": self.reward_sum,
            "motos_cargadas": self.motos_cargadas,
            "mototaxis_cargadas": self.mototaxis_cargadas,
            "step_count": self.step_count
        }

    def log_episode_metrics(self, agent_name: str, episode: int, reward: float, length: int, step: int):
        """Loguea métricas del episodio.

        Args:
            agent_name: Nombre del agente
            episode: Número de episodio
            reward: Recompensa total
            length: Duración en steps
            step: Global step count
        """
        metrics = self.get_episode_metrics()

        logger.info(
            f"[{agent_name}] Episode {episode} | Reward={reward:.4f} | "
            f"Steps={length} | Grid={metrics['grid_import_kwh']:.1f} kWh | "
            f"CO2={metrics['co2_grid_kg']:.1f} kg | "
            f"GlobalStep={step}"
        )


def extract_step_metrics(
    env: Any,
    step_num: int,
    observation: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """Extrae métricas de un step del ambiente.

    Args:
        env: CityLearn environment
        step_num: Número del step actual
        observation: Observación actual (opcional)

    Returns:
        Diccionario con métricas del step
    """
    metrics: Dict[str, float] = {
        "grid_kWh": 0.0,
        "solar_kWh": 0.0,
        "co2_kg": 0.0,
        "motos_charged": 0,
        "mototaxis_charged": 0,
        "bess_soc": 0.0,
    }

    try:
        buildings = getattr(env, "buildings", [])
        if not buildings:
            return metrics

        for building in buildings:
            try:
                # Grid
                net_elec = getattr(building, "net_electricity_consumption", None)
                if net_elec and isinstance(net_elec, (list, tuple)) and net_elec:
                    val = net_elec[-1] if net_elec else 0
                    if val is not None:
                        metrics["grid_kWh"] += float(max(0.0, val))

                # Solar
                solar = getattr(building, "solar_generation", None)
                if solar and isinstance(solar, (list, tuple)) and solar:
                    val = solar[-1] if solar else 0
                    if val is not None:
                        metrics["solar_kWh"] += float(max(0.0, val))

                # BESS SOC
                storage = getattr(building, "electrical_storage", None)
                if storage:
                    soc = getattr(storage, "state_of_charge", None)
                    if soc is not None:
                        metrics["bess_soc"] = float(soc) * 100.0

                # CO2
                if metrics["grid_kWh"] > 0:
                    metrics["co2_kg"] = metrics["grid_kWh"] * 0.4521

            except (AttributeError, IndexError, TypeError):
                pass

    except Exception as e:
        logger.debug(f"Error extracting metrics: {e}")

    return metrics
