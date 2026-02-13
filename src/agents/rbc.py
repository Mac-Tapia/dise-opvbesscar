from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
import logging

# Importar pesos multiobjetivo desde fuente única
from ..rewards import create_iquitos_reward_weights

logger = logging.getLogger(__name__)


@dataclass
class RBCConfig:
    """Configuración para controlador basado en reglas.

    Parámetros multicriterio para optimización de:
    - Emisiones CO₂
    - Costo eléctrico
    - Autoconsumo solar
    - Satisfacción de carga EV
    - Estabilidad de red
    """
    # Umbrales de SOC para BESS
    soc_min: float = 0.1
    soc_max: float = 0.9

    # Umbrales de precio/carbono para decisiones
    price_threshold_low: float = 0.3  # Percentil bajo (cargar)
    price_threshold_high: float = 0.7  # Percentil alto (descargar)

    # Prioridades de carga EV
    ev_priority_solar: bool = True  # Priorizar carga con solar
    ev_max_rate: float = 1.0  # Tasa máxima de carga EV
    ev_min_rate: float = 0.2  # Tasa mínima de carga EV

    # ✅ Configuración de chargers (OE3 ACTUAL - 2026-02-04: 32 chargers = 128 sockets)
    # Detalle: 28 chargers @ 2kW (motos) + 4 chargers @ 3kW (mototaxis)
    # ⚠️  LEGACY (OE2): Solo 20 motos + 3 mototaxis totales → DEPRECATED
    # ACTUAL (OE3): 112 motos + 16 mototaxis = 128 simultáneos en 32 chargers × 4 sockets
    n_chargers: int = 32                        # 32 chargers físicos
    sockets_per_charger: int = 4                # 4 sockets por charger = 128 total
    charger_power_kw: float = 2.125  # Promedio ponderado: (28×2 + 4×3)/32 = 68/32 = 2.125 kW

    # Hora pico (para Iquitos: 18-22h)
    peak_hours: tuple = (18, 19, 20, 21)

    # Estrategia de distribución de carga
    load_balancing: str = "round_robin"  # "round_robin", "solar_priority", "sequential"

    # === MULTIOBJETIVO / MULTICRITERIO ===
    # NOTA: Los pesos multiobjetivo se configuran en rewards.py vía:
    #   create_iquitos_reward_weights(priority) donde priority = "balanced", "co2_focus", etc.
    # Ver: src/iquitos_citylearn/oe3/rewards.py línea 634+
    # NO duplicar pesos aquí - usar rewards.py como fuente única de verdad

    # Umbrales operacionales (NO son pesos multiobjetivo)
    ev_soc_target: float = 0.90        # SOC objetivo para EVs
    grid_peak_limit_kw: float = 200.0  # Límite de demanda pico


class BasicRBCAgent:
    """Controlador RBC robusto para gestión de carga EV + BESS en Iquitos.

    Controla 32 cargadores (28 motos @ 2kW + 4 mototaxis @ 3kW = 68 kW simultánea).
    Observable: 128 sockets (4 por cargador) con control individual de potencia [0, max_kw].

    Reglas implementadas:
    1. PV→EV: Cargar al máximo cuando hay exceso solar (máxima prioridad)
    2. PV→BESS: Acumular exceso solar si SOC < 95% (segunda prioridad)
    3. BESS→EV: Descargar batería en hora pico (18-22h) si SOC > min_soc (tercera prioridad)
    4. BESS→Grid: Vender exceso cuando SOC > 95% (cuarta prioridad)
    5. Grid→EV: Importar solo si deficit después de BESS descarga (última prioridad)

    Objetivo: Minimizar importación grid y emisiones CO₂ (0.4521 kg CO₂/kWh en Iquitos)
    """

    def __init__(self, env: Any, config: Optional[RBCConfig] = None):
        self.env = env
        self.config = config or RBCConfig()

        # Cargar pesos multiobjetivo desde fuente única (rewards.py)
        self._weights = create_iquitos_reward_weights("co2_focus")

        self._setup_action_space()
        self._charger_usage = np.zeros(self.config.n_chargers)  # Tracking de uso
        self._step_count = 0

    def _setup_action_space(self):
        """Configura espacios de acción."""
        self.action_space = getattr(self.env, "action_space", None)
        self.action_names = getattr(self.env, "action_names", None)

        if self.action_space is None:
            raise ValueError("env debe exponer action_space")

        self._subspaces: list[Any] = list(self.action_space) if isinstance(self.action_space, list) else [self.action_space]  # type: ignore[assignment]
        self._subnames: list[Any] = list(self.action_names) if self.action_names else [[]]  # type: ignore[assignment]

        # Identificar índices de acciones EV y BESS
        self._ev_indices: list[list[int]] = []  # type: ignore[assignment]
        self._bess_indices: list[list[int]] = []
        self._charger_indices: list[list[int]] = []  # Índices específicos por charger

        for names in self._subnames:
            ev_idx = [i for i, n in enumerate(names) if "electric_vehicle" in str(n).lower()]
            bess_idx = [i for i, n in enumerate(names) if "storage" in str(n).lower() and "electric_vehicle" not in str(n).lower()]
            # Detectar chargers individuales (charger_mall_1, charger_mall_2, etc.)
            charger_idx = [i for i, n in enumerate(names) if "charger" in str(n).lower()]

            self._ev_indices.append(ev_idx)
            self._bess_indices.append(bess_idx)
            self._charger_indices.append(charger_idx)

        n_ev_actions = sum(len(idx) for idx in self._ev_indices)
        n_charger_actions = sum(len(idx) for idx in self._charger_indices)
        logger.info(f"RBC configurado: {n_ev_actions} acciones EV, {n_charger_actions} acciones charger")

    def _distribute_charging_load(self, available_power: float, n_active_chargers: int) -> np.ndarray:
        """Distribuye la carga entre chargers según estrategia.

        Args:
            available_power: Potencia disponible (kW)
            n_active_chargers: Número de chargers a activar

        Returns:
            Array de tasas de carga [0-1] para cada charger
        """
        rates = np.zeros(self.config.n_chargers)

        if n_active_chargers <= 0 or available_power <= 0:
            return rates

        power_per_charger = self.config.charger_power_kw * self.config.sockets_per_charger
        max_chargers = min(n_active_chargers, int(available_power / power_per_charger) + 1)

        if self.config.load_balancing == "round_robin":
            # Rotar chargers activos para distribuir desgaste
            start_idx = self._step_count % self.config.n_chargers
            active_indices = [(start_idx + i) % self.config.n_chargers for i in range(max_chargers)]
            for idx in active_indices:
                rates[idx] = min(1.0, available_power / (max_chargers * power_per_charger))

        elif self.config.load_balancing == "solar_priority":
            # Priorizar chargers más cercanos al inversor solar (índices bajos)
            for i in range(min(max_chargers, self.config.n_chargers)):
                rates[i] = min(1.0, available_power / (max_chargers * power_per_charger))

        else:  # sequential
            # Llenar chargers en orden secuencial
            remaining_power = available_power
            for i in range(self.config.n_chargers):
                if remaining_power <= 0:
                    break
                charge_rate = min(1.0, remaining_power / power_per_charger)
                rates[i] = charge_rate
                remaining_power -= charge_rate * power_per_charger

        return rates

    def predict(self, observations: Any, deterministic: bool = True) -> list[list[float]]:
        """Genera acciones basadas en reglas multicriterio para 128 cargadores.

        Criterios de decisión (ponderados):
        1. CO₂: Reducir carga cuando factor de emisión alto
        2. Costo: Reducir carga de red cuando tarifa alta
        3. Solar: Maximizar carga durante exceso solar
        4. EV: Asegurar SOC objetivo antes de salida
        5. Grid: Evitar picos de demanda
        """
        self._step_count += 1
        obs_dict = self._parse_observations(observations)

        hour = obs_dict.get("hour", 12)
        solar_gen = obs_dict.get("solar_generation", 0)
        load = obs_dict.get("non_shiftable_load", 0)
        soc = obs_dict.get("electrical_storage_soc", 0.5)
        carbon = obs_dict.get("carbon_intensity", 0.5)

        # Exceso solar disponible (kW)
        solar_excess = max(0, solar_gen - load)
        is_peak = hour in self.config.peak_hours

        # Calcular cuántos chargers activar según condiciones
        power_per_charger = self.config.charger_power_kw * self.config.sockets_per_charger

        # === LÓGICA MULTICRITERIO ===
        # Puntaje de carga: valor alto = cargar más, bajo = reducir carga
        # Pesos cargados desde rewards.py (fuente única)
        charge_score = 0.0

        # Criterio 1: Solar (maximizar autoconsumo)
        if solar_excess > 0:
            solar_score = min(1.0, solar_excess / (power_per_charger * self.config.n_chargers))
            charge_score += self._weights.solar * solar_score
        else:
            charge_score -= self._weights.solar * 0.3  # Penalización sin solar

        # Criterio 2: CO₂ (minimizar emisiones)
        co2_threshold_high = 0.6  # Umbral operacional (no es peso)
        if carbon < co2_threshold_high:
            charge_score += self._weights.co2 * (1 - carbon)
        else:
            charge_score -= self._weights.co2 * 0.5  # Reducir carga con alto CO₂

        # Criterio 3: Grid stability (evitar picos)
        if is_peak:
            charge_score -= self._weights.grid_stability * 0.8
        else:
            charge_score += self._weights.grid_stability * 0.5

        # Criterio 4: BESS SOC (usar BESS si disponible en pico)
        if is_peak and soc > self.config.soc_min:
            charge_score += self._weights.ev_satisfaction * 0.3
        elif soc < self.config.soc_min:
            charge_score -= self._weights.ev_satisfaction * 0.2

        # Criterio 5: Costo (asumir costo correlacionado con hora pico)
        if not is_peak:
            charge_score += self._weights.cost * 0.5
        else:
            charge_score -= self._weights.cost * 0.3

        # Convertir puntaje a número de chargers y tasa
        # charge_score está en rango ~[-1, 1], mapear a [0.2, 1.0] de chargers
        normalized_score = (charge_score + 1.0) / 2.0  # [0, 1]
        charger_fraction = 0.2 + 0.8 * normalized_score  # [0.2, 1.0]

        n_active = int(self.config.n_chargers * charger_fraction)
        n_active = max(1, min(self.config.n_chargers, n_active))

        # Tasa de carga basada en disponibilidad solar
        if solar_excess > 0 and self.config.ev_priority_solar:
            base_rate = min(self.config.ev_max_rate, 0.5 + 0.5 * normalized_score)
            available_power = solar_excess + soc * 50  # Solar + BESS disponible
        else:
            base_rate = self.config.ev_min_rate + (self.config.ev_max_rate - self.config.ev_min_rate) * normalized_score
            available_power = power_per_charger * n_active

        # Distribuir carga entre chargers
        charger_rates = self._distribute_charging_load(available_power, n_active)

        actions: list[list[float]] = []
        charger_idx_global = 0

        for idx, (sp, ev_idx, bess_idx, ch_idx) in enumerate(zip(
            self._subspaces, self._ev_indices, self._bess_indices, self._charger_indices
        )):
            action = np.zeros(sp.shape[0], dtype=float)

            # Acciones EV genéricas
            for i in ev_idx:
                action[i] = base_rate

            # Acciones específicas por charger
            for i in ch_idx:
                if charger_idx_global < len(charger_rates):
                    action[i] = charger_rates[charger_idx_global]
                    charger_idx_global += 1

            # Acciones BESS (multicriterio) - usando pesos de rewards.py
            co2_threshold_high = 0.6  # Umbral operacional
            for i in bess_idx:
                if solar_excess > 0 and soc < self.config.soc_max:
                    # Cargar BESS con exceso solar (objetivo: maximizar autoconsumo)
                    bess_charge = min(1.0, solar_excess / 100)
                    action[i] = bess_charge * self._weights.solar
                elif is_peak and soc > self.config.soc_min:
                    # Descargar en hora pico (objetivo: reducir grid, estabilidad)
                    discharge_rate = -0.5 * (self._weights.grid_stability + self._weights.cost)
                    action[i] = max(-1.0, discharge_rate)
                elif carbon > co2_threshold_high and soc > self.config.soc_min:
                    # Descargar cuando alto carbono (objetivo: reducir CO₂)
                    action[i] = -0.3 * self._weights.co2
                else:
                    action[i] = 0.0

            # Clip a límites
            low = np.array(getattr(sp, "low", -1.0), dtype=float)
            high = np.array(getattr(sp, "high", 1.0), dtype=float)
            action = np.clip(action, low, high)

            actions.append(action.tolist())

        return actions

    def _parse_observations(self, observations: Any) -> dict[str, float]:
        """Extrae observaciones relevantes."""
        obs_dict: dict[str, float] = {}

        if isinstance(observations, dict):
            for k, v in observations.items():
                if isinstance(v, (int, float)):
                    obs_dict[k] = float(v)
                elif isinstance(v, (list, np.ndarray)) and len(v) > 0:
                    obs_dict[k] = float(v[0]) if len(v) == 1 else float(np.mean(v))
        elif isinstance(observations, (list, tuple)) and len(observations) > 0:
            # Asumir orden estándar CityLearn
            obs_names = ["month", "day_type", "hour", "outdoor_dry_bulb_temperature",
                        "outdoor_relative_humidity", "diffuse_solar_irradiance",
                        "direct_solar_irradiance", "carbon_intensity",
                        "non_shiftable_load", "solar_generation"]
            flat = np.array(observations).ravel()
            for i, name in enumerate(obs_names):
                if i < len(flat):
                    obs_dict[name] = float(flat[i])

        return obs_dict

    def learn(self, episodes: int = 0):
        """RBC no requiere entrenamiento."""
        logger.info("RBC no requiere entrenamiento (rule-based)")


def make_basic_ev_rbc(env: Any, config: Optional[RBCConfig] = None) -> BasicRBCAgent:
    """Crea agente RBC robusto.

    Intenta usar CityLearn's RBC primero, fallback a implementación propia.
    """
    # Intentar CityLearn RBC
    try:
        from citylearn.agents.rbc import BasicElectricVehicleRBC_ReferenceController  # type: ignore
        try:
            return BasicElectricVehicleRBC_ReferenceController(env)  # type: ignore
        except TypeError:
            return BasicElectricVehicleRBC_ReferenceController(env=env)  # type: ignore
    except Exception as e:
        logger.info("CityLearn RBC no disponible (%s), usando implementación propia", e)

    # Fallback a implementación propia
    return BasicRBCAgent(env, config)  # type: ignore
