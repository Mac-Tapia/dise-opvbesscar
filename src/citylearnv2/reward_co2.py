"""
reward_co2.py — IquitosCO2Reward
Función de recompensa multi-objetivo CO₂ para CityLearn v2.

Hereda de citylearn.reward_function.RewardFunction y es compatible con
cualquier agente de CityLearn (native SAC) o SB3 (PPO, A2C via wrapper).

Pesos OE3 v7.0 CO2_DUAL_FOCUS:
  r_indirect_co2   : 0.30  — minimizar importación de red (0.4521 kg CO₂/kWh)
  r_solar          : 0.25  — maximizar autoconsumo solar
  r_bess_util      : 0.20  — penalizar SOC muy bajo/alto (evitar ciclos innecesarios)
  r_grid_stable    : 0.15  — penalizar cambios bruscos de red

Nota: r_direct_co2 (motos/mototaxis) no puede calcularse en el modelo
CityLearn simplificado porque la demanda EV está dentro de non_shiftable_load.
Se incorpora el factor de CO₂ neto EV (0.4521 kg red - 0.87/0.54 kg gasolina)
como constante en el factor GRID.
"""
from __future__ import annotations

from typing import Any, List, Mapping, Union

import numpy as np

from citylearn.reward_function import RewardFunction

# Factores de CO₂ Iquitos (IPCC 2006 Tier 1 + MINEM 2024)
_CO2_GRID_KG_PER_KWH: float = 0.4521    # Red aislada Iquitos (diesel)
_BESS_SOC_TARGET: float = 0.50          # SOC ideal para flexibilidad
_BESS_SOC_MIN: float = 0.20             # DoD 80%


class IquitosCO2Reward(RewardFunction):
    """Recompensa multi-objetivo CO₂ para Iquitos PV-BESS-EV en CityLearn v2.

    Parameters
    ----------
    env_metadata : Mapping[str, Any]
        Metadatos del entorno provistos por CityLearnEnv.
    w_co2 : float
        Peso para reducción CO₂ indirecto (importación de red). Default 0.40.
    w_solar : float
        Peso para autoconsumo solar. Default 0.25.
    w_bess : float
        Peso para utilización BESS. Default 0.20.
    w_grid_stable : float
        Peso para estabilidad de red. Default 0.15.
    co2_factor : float
        Factor de emisión de la red en kg CO₂/kWh. Default 0.4521.
    **kwargs
        Parámetros adicionales para la clase base.
    """

    def __init__(
        self,
        env_metadata: Mapping[str, Any],
        w_co2: float = 0.40,
        w_solar: float = 0.25,
        w_bess: float = 0.20,
        w_grid_stable: float = 0.15,
        co2_factor: float = _CO2_GRID_KG_PER_KWH,
        **kwargs: Any,
    ) -> None:
        super().__init__(env_metadata, **kwargs)
        # Normalizar pesos
        total = w_co2 + w_solar + w_bess + w_grid_stable
        self.w_co2 = w_co2 / total
        self.w_solar = w_solar / total
        self.w_bess = w_bess / total
        self.w_grid_stable = w_grid_stable / total
        self.co2_factor = co2_factor
        self._prev_net_consumption: float = 0.0

    def reset(self) -> None:
        """Reinicia variables acumuladas al inicio de cada episodio."""
        self._prev_net_consumption = 0.0

    def calculate(
        self, observations: List[Mapping[str, Union[int, float]]]
    ) -> List[float]:
        """Calcula la recompensa multi-objetivo CO₂.

        Parameters
        ----------
        observations : list[dict]
            Lista de observaciones por edificio en el paso actual.
            Con central_agent=True, tiene 1 elemento.

        Returns
        -------
        list[float]
            Recompensa escalar (lista de 1 elemento para central_agent=True).
        """
        obs = observations[0]

        # --- Extraer observaciones disponibles ---
        net_consumption = float(obs.get("net_electricity_consumption", 0.0))
        solar_gen = float(obs.get("solar_generation", 0.0))
        non_shiftable_load = float(obs.get("non_shiftable_load", 1.0))
        soc = float(obs.get("electrical_storage_soc", 0.50))

        # --- r_indirect_co2: penalizar importación de red ---
        # net_consumption > 0 → importación; cortar en 0 para solo penalizar importación
        grid_import = max(net_consumption, 0.0)
        # Normalizado por una demanda típica máxima (mall+EV peak ≈ 350 kWh/h)
        max_demand_hourly = 350.0
        r_co2 = -np.clip(grid_import / max_demand_hourly, 0.0, 1.0)

        # --- r_solar: maximizar autoconsumo solar ---
        # solar_gen en kWh; non_shiftable_load en kWh
        if solar_gen > 0.001:
            # Fracción de solar efectivamente usada (no exportada)
            # solar exportado = max(solar_gen - non_shiftable_load + grid_import, 0)
            solar_used = solar_gen - max(-net_consumption, 0.0)  # exportación = neg net_cons
            solar_self_consumption = np.clip(solar_used / solar_gen, 0.0, 1.0)
            r_solar = solar_self_consumption - 0.3  # baseline 30%
        else:
            r_solar = 0.0

        # --- r_bess_util: penalizar SOC muy lejos del rango óptimo [0.3, 0.8] ---
        soc_deviation = abs(soc - _BESS_SOC_TARGET)
        r_bess = -np.clip(soc_deviation, 0.0, 0.5)  # max penalización 0.5

        # --- r_grid_stable: penalizar cambios bruscos en consumo de red ---
        delta_consumption = abs(net_consumption - self._prev_net_consumption)
        r_grid_stable = -np.clip(delta_consumption / max_demand_hourly, 0.0, 1.0)
        self._prev_net_consumption = net_consumption

        # --- Recompensa combinada ---
        reward_val = (
            self.w_co2 * r_co2
            + self.w_solar * r_solar
            + self.w_bess * r_bess
            + self.w_grid_stable * r_grid_stable
        )

        # Escalar para rango entrenamiento SB3 / CityLearn-SAC
        reward_val = float(np.clip(reward_val, -1.0, 1.0))

        if self.central_agent:
            return [reward_val]
        else:
            return [reward_val] * len(observations)
