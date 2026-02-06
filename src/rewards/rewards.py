"""
Funciones de recompensa multiobjetivo y multicriterio para agentes RL.

================================================================================
TRACKING REDUCCIONES DIRECTAS E INDIRECTAS DE CO₂ (2026-01-31)
================================================================================

DEFINICIONES CRÍTICAS:

1. CO₂ DIRECTO (Emisiones de demanda EV):
   - Demanda constante: 50 kW (13 horas/día = 9AM-10PM)
   - Factor de conversión: 2.146 kg CO₂/kWh
   - Representa: Combustión equivalente si fueran vehículos a gasolina
   - CO₂ directo acumulado/hora: 50 × 2.146 = 107.3 kg CO₂/h
   - CO₂ directo anual SIN control: 50 × 2.146 × 8760 = 938,460 kg CO₂/año
   - Tracking: Se accumula pero NO se reduce (es la baseline de demanda)
   - Propósito: Referencia para calcular reducciones indirectas

2. CO₂ INDIRECTO (Emisiones evitadas por solar directo):
   - Factor grid Iquitos: 0.4521 kg CO₂/kWh (central térmica aislada)
   - Reducción indirecta = Solar PV directo a EVs × 0.4521
   - Ejemplo: 100 kWh solar directo → 100 × 0.4521 = 45.21 kg CO₂ evitado
   - Propósito: Objetivo principal de optimización
   - Target: Maximizar PV directo para maximizar reducciones indirectas

3. ARQUITECTURA DE REDUCCIONES:

   Baseline (sin control):
   - CO₂ grid total: 50 kW × 8760 h × 0.4521 kg/kWh = 197,262 kg CO₂/año (indirecto)
   - CO₂ directo: 107.3 kg/h × 8760 h = 938,460 kg CO₂/año (tracking)
   - Total: ~1,135,722 kg CO₂/año

   Con RL (con control solar directo):
   - Solar PV directo: ~X kWh/año (optimizado por agente)
   - Reducción indirecta: X × 0.4521 kg CO₂/año evitado
   - Grid import reducido: (potencial - solar) × 0.4521
   - CO₂ directo: Sigue siendo 938,460 (demanda fija, tracking)
   - Beneficio neto: Mayor reducción indirecta por más PV directo

4. REWARD FUNCTION DESIGN:

   Componentes de recompensa (multiobjetivo):
   - r_co2 (0.50 peso): Minimizar importación grid = maximizar PV directo
   - r_solar (0.20 peso): Bonus por autoconsumo solar
   - r_cost (0.10 peso): Minimizar costo (secundario, tarifa baja)
   - r_ev (0.10 peso): Satisfacción de carga EV
   - r_grid (0.10 peso): Estabilidad de red

   Cálculo simplificado:
   r_total = 0.50 × r_co2 + 0.20 × r_solar + ...
   r_co2 = "reward por reducción indirecta" = f(solar_directo)

5. VALORES DE REFERENCIA (OE2 Real):
   - Co2 grid factor: 0.4521 kg/kWh (GRID IMPORT - indirecto)
   - EV co2 factor: 2.146 kg/kWh (DEMANDA DIRECTA - tracking)
   - EV demand: 50.0 kW (CONSTANTE)
   - Chargers: 32 (128 sockets = 112 motos + 16 mototaxis)
   - BESS: 4520 kWh / 2712 kW (NO controlable, dispatch automático)

Objetivos optimizados:
1. Minimizar emisiones de CO₂ (indirectas por grid import)
2. Minimizar costo eléctrico
3. Maximizar autoconsumo solar (PV directo)
4. Maximizar satisfacción de carga de EVs
5. Minimizar picos de demanda (estabilidad de red)

Contexto Iquitos (OE2/OE3 - DATOS REALES 2026-01-31):
- Factor emisión: 0.4521 kg CO₂/kWh (central térmica aislada)
- Factor conversión: 2.146 kg CO₂/kWh (para cálculos directos con 50kW constante)
- Tariff: 0.20 USD/kWh (bajo, no es constraint)
- Chargers: 32 cargadores físicos (28 motos @ 2kW + 4 mototaxis @ 3kW)
- Sockets: 128 totales (32 × 4 sockets = 112 motos + 16 mototaxis)
- Potencia instalada: 68 kW simultánea (28×2kW + 4×3kW)
- Demanda EV: 50 kW constante (54% uptime × 100kW = workaround CityLearn 2.5.0)
- Capacidad anual: 2,912 motos + 416 mototaxis (13h operación 9AM-10PM)
- BESS: 4,520 kWh / 2,712 kW (fijo, no controlable por agentes)
- Resultado OE3: Agente A2C -25.1% CO₂ (4,280,119 kg/año vs 5,710,257 kg/año baseline)

VINCULACIONES EN SISTEMA:
- config.yaml (SOURCE OF TRUTH): co2_grid_factor_kg_per_kwh, ev_co2_conversion_kg_per_kwh
- dataset_builder.py: Valida y carga datos
- rewards.py: Calcula CO₂ directo + indirecto
- agents: Optimizan para reducir CO₂ indirecto (maximizar PV directo)
- simulate.py: Acumula y reporta ambas reducciones
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple
import numpy as np
import logging
import gymnasium as gym

logger = logging.getLogger(__name__)


@dataclass
class MultiObjectiveWeights:
    """Pesos para función de recompensa multiobjetivo - REBALANCED PARA MÁXIMA PRIORIDAD EVCS.

    ✅ CAMBIO 2026-02-05: Realinear prioridades según arquitectura documentada
    Prioridad de despacho real (OE2):
    1. SOLAR → EVs (MÁXIMA PRIORIDAD)
    2. SOLAR EXCESO → BESS
    3. SOLAR EXCESO → MALL
    4. BESS → EVs (noche)
    5. GRID → Deficit

    Pesos actualizados para reflejar MÁXIMA PRIORIDAD en carga EV:
    - EV_SATISFACTION 0.30: TRIPLICADO (0.10 → 0.30) ← MÁXIMA PRIORIDAD
    - CO₂ 0.35: REDUCIDO (0.50 → 0.35) - EVs cargados desde solar ayudan
    - Solar 0.20: MANTENER (PV limpio es crítico)
    - Costo 0.10: REDUCIDO (tarifa baja, no es constraint)
    - Grid & EV utilization 0.05 total: baseline
    """
    co2: float = 0.35              # PRIMARY (reducido): Minimizar CO₂ grid
    cost: float = 0.10             # REDUCIDO: tarifa baja, no es constraint [ERA 0.15]
    solar: float = 0.20            # SECUNDARIO: autoconsumo solar limpio
    ev_satisfaction: float = 0.30  # ✅ TRIPLICADO: MÁXIMA PRIORIDAD [ERA 0.10 → 0.30]
    ev_utilization: float = 0.05   # Bonus por utilización máxima EVs (motos+mototaxis cargadas)
    grid_stability: float = 0.05   # Matches: báseline de operación
    peak_import_penalty: float = 0.00  # Dinámico en compute(), no como peso fijo
    operational_penalties: float = 0.0  # Penalizaciones operacionales (BESS, EV fairness)

    def __post_init__(self):
        # Normalizar pesos base (sin peak_import_penalty que se aplica por separado)
        base_weights = [self.co2, self.cost, self.solar, self.ev_satisfaction, self.ev_utilization, self.grid_stability]
        total = sum(base_weights)
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Pesos multiobjetivo no suman 1.0 (suma={total:.3f}), normalizando...")
            factor = 1.0 / total
            self.co2 *= factor
            self.cost *= factor
            self.solar *= factor
            self.ev_satisfaction *= factor
            self.ev_utilization *= factor
            self.grid_stability *= factor

    def as_dict(self) -> dict[str, float]:
        return {
            "co2": self.co2,
            "cost": self.cost,
            "solar": self.solar,
            "ev_satisfaction": self.ev_satisfaction,
            "ev_utilization": self.ev_utilization,
            "grid_stability": self.grid_stability,
            "peak_import_penalty": self.peak_import_penalty,
            "operational_penalties": self.operational_penalties,
        }


@dataclass
class IquitosContext:
    """Contexto específico de Iquitos para cálculos multiobjetivo - OE2 REAL 2026-01-31."""
    # Factor de emisión (central térmica aislada)
    co2_factor_kg_per_kwh: float = 0.4521  # Grid import CO₂ factor
    co2_conversion_factor: float = 2.146   # Para cálculo directo: 50kW × 2.146 = 107.3 kg/h

    # NUEVO: Configuración de EVs para bonus de utilización (2026-02-04)
    # Flota OE3 REAL: 2,685 motos/día + 388 mototaxis/día = 3,073 vehículos/día
    # Proyección anual: 979,759 motos/año + 141,520 mototaxis/año = 1,121,279 vehículos/año
    max_motos_simultaneous: int = 112     # Max motos que pueden cargarse simultáneamente (capacidad sockets)
    max_mototaxis_simultaneous: int = 16  # Max mototaxis que pueden cargarse simultáneamente (capacidad sockets)
    max_evs_total: int = 128              # Total sockets/chargers (32 chargers × 4 sockets)
    motos_daily_capacity: int = 2685      # REAL: 2,685 motos/día
    mototaxis_daily_capacity: int = 388   # REAL: 388 mototaxis/día

    # Tarifa eléctrica
    tariff_usd_per_kwh: float = 0.20

    # Configuración de chargers (OE2 - DATOS REALES)
    n_chargers: int = 32                   # 32 chargers físicos (28 motos + 4 mototaxis)
    total_sockets: int = 128               # 32 × 4 = 128 sockets (112 motos + 16 mototaxis)
    sockets_per_charger: int = 4
    charger_power_kw_moto: float = 2.0     # Potencia motos
    charger_power_kw_mototaxi: float = 3.0 # Potencia mototaxis
    ev_demand_constant_kw: float = 50.0    # Demanda constante (workaround CityLearn 2.5.0)

    # Flota EV (OE3 REAL - 2026-02-05)
    # VALORES DIARIOS (para control):
    vehicles_day_motos: int = 2685        # Motos cargadas por día
    vehicles_day_mototaxis: int = 388     # Mototaxis cargadas por día

    # VALORES ANUALES (para impacto y referencia):
    vehicles_year_motos: int = 657000      # Proyección anual: 1,800 × 365
    vehicles_year_mototaxis: int = 94900   # Proyección anual: 260 × 365

    # Límites operacionales
    peak_demand_limit_kw: float = 200.0
    ev_soc_target: float = 0.90
    bess_soc_min: float = 0.10
    bess_soc_max: float = 0.90

    # Horario de operación - OE3 IQUITOS
    operation_start_hour: int = 9      # 9 AM - Inicio de operación
    operation_end_hour: int = 22        # 10 PM (22:00) - Cierre de operación
    operation_duration_hours: int = 13  # 13 horas de operación (9 AM a 10 PM)

    # Horas pico Iquitos: 6 PM a 9 PM (18:00 a 21:00)
    peak_hours: Tuple[int, ...] = (18, 19, 20, 21)

    # Factores de emisiones evitadas (vehículos eléctricos vs combustión)
    km_per_kwh: float = 35.0           # Motos/mototaxis eléctricas: ~35 km/kWh
    km_per_gallon: float = 120.0        # Motos/mototaxis combustión: ~120 km/galón
    kgco2_per_gallon: float = 8.9       # Emisiones combustión: ~8.9 kg CO₂/galón


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
        # Usar presets centralizados como fallback (NO duplicar pesos aquí)
        # Ver create_iquitos_reward_weights() línea 634+ para definición única
        if weights is None:
            # Default: co2_focus (prioridad para Iquitos)
            weights = MultiObjectiveWeights()  # Usa defaults del dataclass
        self.weights = weights
        self.context = context or IquitosContext()

        # Historial para normalización adaptativa
        self._reward_history: list[dict[str, float]] = []
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
    ) -> tuple[float, dict[str, float]]:
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

        # 1. Recompensa CO₂ (minimizar) - TIER 1 FIX: Baselines Realistas + CO₂ EVITADO
        # CO₂ directo: importación de grid
        co2_grid_kg = grid_import_kwh * self.context.co2_factor_kg_per_kwh

        # CO₂ EVITADO - COMPONENTE 1: Solar que evita importación de grid (INDIRECTA)
        # Energía solar consumida → evita importar energía del grid térmico
        co2_avoided_indirect_kg = solar_generation_kwh * self.context.co2_factor_kg_per_kwh

        # CO₂ EVITADO - COMPONENTE 2: EVs que evitan combustión (DIRECTA) - CORREGIDA 2026-02-03
        # CRÍTICO: Solo contar EV cargada desde SOLAR, NO total EV demand
        # Razón: co2_grid_kg ya incluye EV del grid en grid_import
        # Si contamos EV total, hacemos doble conteo (grid CO₂ + EV CO₂)
        #
        # Aproximación: EV desde solar ≈ solar_generation (porque primero cubre demanda)
        # Luego cubre EV. Si hay exportación, entonces solar cubre más que demanda
        # Fórmula: ev_solar = min(ev_charging_kwh, max(0, solar_generation_kwh - demanda_base))
        # Simplificación: usar ratio de cobertura
        if ev_charging_kwh > 0 and solar_generation_kwh > 0:
            # Aproximación: EV cubierto por solar es proporcional a solar_generation
            # vs total demanda (mall + EV)
            # Usando heurística simple: si solar > mall demand, el excedente va a EV
            mall_baseline = 100.0  # kWh/hora típico (puede parametrizarse)
            excess_solar = max(0, solar_generation_kwh - mall_baseline)
            ev_covered = min(ev_charging_kwh, excess_solar)
            total_km = ev_covered * self.context.km_per_kwh
            gallons_avoided = total_km / max(self.context.km_per_gallon, 1e-9)
            co2_avoided_direct_kg = gallons_avoided * self.context.kgco2_per_gallon
        else:
            co2_avoided_direct_kg = 0.0

        # CO₂ EVITADO TOTAL = indirecta (solar) + directa (EVs)
        co2_avoided_total_kg = co2_avoided_indirect_kg + co2_avoided_direct_kg

        # CO₂ NETO = grid emissions - avoided emissions (puede ser negativo si evitamos más de lo que importamos)
        co2_net_kg = co2_grid_kg - co2_avoided_total_kg

        # Baselines basados en operación real Iquitos:
        # Off-peak: mall ~100 kW avg + chargers ~30 kW = 130 kWh/hora típico
        # Peak (18-21h): mall ~150 kW + chargers ~100 kW = 250 kWh/hora target
        co2_baseline_offpeak = 130.0  # kWh/hora típico off-peak
        co2_baseline_peak = 250.0     # kWh/hora target with BESS support en pico

        if is_peak:
            # En pico: penalizar fuertemente si superas target (usando CO₂ neto)
            # Bonus si CO₂ neto < 0 (evitamos más de lo que importamos)
            r_co2 = 1.0 - 2.0 * min(1.0, max(0, co2_net_kg) / (co2_baseline_peak * self.context.co2_factor_kg_per_kwh))
        else:
            # Off-peak: más tolerante pero aún penaliza exceso
            r_co2 = 1.0 - 1.0 * min(1.0, max(0, co2_net_kg) / (co2_baseline_offpeak * self.context.co2_factor_kg_per_kwh))

        r_co2 = np.clip(r_co2, -1.0, 1.0)
        components["r_co2"] = r_co2
        components["co2_grid_kg"] = co2_grid_kg
        components["co2_avoided_indirect_kg"] = co2_avoided_indirect_kg
        components["co2_avoided_direct_kg"] = co2_avoided_direct_kg
        components["co2_avoided_total_kg"] = co2_avoided_total_kg
        components["co2_net_kg"] = co2_net_kg

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

        # 4. Recompensa Satisfacción EV (maximizar) - ENHANCED para priorizar carga a 90% SOC
        # ✅ OBJETIVO: Maximizar carga de EVs a 90% SOC durante 9AM-10PM (Modo 3)
        # Estructura: Base (ev_satisfaction) + Hitos (80%, 88%) + Urgencia Temporal (20-21h)

        # 4.1 Base: Normalized SOC satisfaction
        ev_satisfaction = min(1.0, ev_soc_avg / self.context.ev_soc_target)  # [0, 1]
        r_ev = 2.0 * ev_satisfaction - 1.0  # [-1, 1]

        # 4.2 Hito de Carga 1: Penalidad para SOC muy bajo (<80%)
        if ev_soc_avg < 0.80:
            soc_deficit = 0.80 - ev_soc_avg
            deficit_penalty = -0.3 * min(1.0, soc_deficit / 0.20)  # [-0.3, 0]
            r_ev += deficit_penalty
            components["r_ev_soc_deficit"] = deficit_penalty
        else:
            components["r_ev_soc_deficit"] = 0.0

        # 4.3 Hito de Carga 2: Bonus para SOC cercano al target (88%+)
        if ev_soc_avg > 0.88:
            soc_buffer = ev_soc_avg - 0.88  # [0, 0.02+]
            completion_bonus = 0.2 * min(1.0, soc_buffer / 0.10)  # [0, 0.2]
            r_ev += completion_bonus
            components["r_ev_completion_bonus"] = completion_bonus
        else:
            components["r_ev_completion_bonus"] = 0.0

        # 4.4 Urgencia Temporal: PENALIZACIÓN FUERTE en última ventana de carga (8-10 PM)
        # Contexto: Mall cierra a las 10 PM. EVs deben estar listos antes de salir.
        if hour in [20, 21]:  # 8-10 PM critical window (horas 20, 21 = 8PM, 9PM)
            # En picos finales, MÁXIMA urgencia de completar carga
            if ev_soc_avg < 0.90:
                # PENALIZACIÓN FUERTE: evita que agents dejen EVs sin cargar al cierre
                final_window_penalty = -0.8 * min(1.0, (0.90 - ev_soc_avg) / 0.30)  # [-0.8, 0]
                r_ev += final_window_penalty
                components["r_ev_final_window_penalty"] = final_window_penalty
            else:
                # BONUS en ventana final si EV listo: asegura carga completa antes cierre
                final_window_bonus = 0.4  # Fuerte bonus por estar listo
                r_ev += final_window_bonus
                components["r_ev_final_window_penalty"] = final_window_bonus
        else:
            components["r_ev_final_window_penalty"] = 0.0

        # 4.5 Bonus por Solar directo a EVs: Maximizar PV autoconsumo en EV
        if solar_generation_kwh > 0 and ev_charging_kwh > 0:
            solar_ev_ratio = min(1.0, ev_charging_kwh / solar_generation_kwh)
            r_ev += 0.1 * solar_ev_ratio  # Bonus pequeño pero consistente

        # Normalizacion final
        r_ev = np.clip(r_ev, -1.0, 1.0)
        components["r_ev"] = r_ev
        components["r_ev_base"] = 2.0 * ev_satisfaction - 1.0
        components["ev_soc_avg"] = ev_soc_avg
        components["hour"] = float(hour)

        # 🟢 5. NUEVO: Recompensa por Utilización de EVs (maximizar motos+mototaxis cargadas)
        # ✅ OBJETIVO: Premiar cuando SAC carga máxima cantidad de motos y mototaxis
        # SIN afectar capacidad de cargadores (128 sockets disponibles)
        #
        # LÓGICA:
        # - EVs llegan con diferentes SOC (20-25%)
        # - Calcular ratio de utilización = ev_soc_avg / max_ev_capacity
        # - Bonus proporcional al ratio (hasta máximo 1.0)
        # - Bonus adicional si mantiene balance (no sobrecargar)

        # Heurística: Si ev_soc_avg > 0.75 y se están cargando EVs,
        # significa que el agente está manteniendo múltiples EVs en buen estado
        r_ev_utilization = 0.0
        if ev_soc_avg > 0.70:
            # Bonus por buen manejo de utilización
            # Máximo bonus cuando ev_soc_avg ≈ 0.85-0.90 (evita pasar 0.90)
            utilization_score = min(1.0, (ev_soc_avg - 0.70) / (0.90 - 0.70))  # [0, 1]
            r_ev_utilization = 2.0 * utilization_score - 1.0  # [-1, 1]

            # Penalización si supera 0.95 (indica que concentra carga en pocos EVs)
            if ev_soc_avg > 0.95:
                overcharge_penalty = -0.3 * min(1.0, (ev_soc_avg - 0.95) / 0.05)
                r_ev_utilization += overcharge_penalty
        else:
            # Penalización por utilización baja (EVs no están siendo cargados)
            underutilization_penalty = -0.2 * min(1.0, (0.70 - ev_soc_avg) / 0.30)
            r_ev_utilization = underutilization_penalty

        r_ev_utilization = np.clip(r_ev_utilization, -1.0, 1.0)
        components["r_ev_utilization"] = r_ev_utilization
        components["ev_utilization_score"] = float(ev_soc_avg)

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

        # Recompensa total ponderada - INCLUYE EV utilization bonus
        reward = (
            self.weights.co2 * r_co2 +
            self.weights.cost * r_cost +
            self.weights.solar * r_solar +
            self.weights.ev_satisfaction * r_ev +
            self.weights.ev_utilization * r_ev_utilization +
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
        operational_state: Optional[dict[str, Any]] = None,
    ) -> tuple[float, dict[str, float]]:
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

    def get_pareto_metrics(self) -> dict[str, float]:
        """Retorna métricas para análisis de Pareto."""
        if not self._reward_history:
            return {}

        metrics: dict[str, float] = {}
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
        try:
            obs, original_reward, terminated, truncated, info = self.env.step(action)
        except (KeyboardInterrupt, AttributeError, TypeError, Exception) as e:
            # Si falla el step del environment, retornar observación segura
            obs = np.zeros(394)  # 394-dim observation space (129 actions)
            original_reward = 0.0
            terminated = True
            truncated = False
            info = {}
            return obs, 0.0, terminated, truncated, info

        # Extraer métricas del ambiente (con manejo seguro de excepciones)
        buildings = []
        try:
            if hasattr(self.env, "buildings"):
                buildings = list(self.env.buildings) if self.env.buildings else []
        except (AttributeError, KeyboardInterrupt, Exception) as e:
            # Si falla el acceso a buildings, usar lista vacía
            buildings = []

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
        "balanced": MultiObjectiveWeights(co2=0.30, cost=0.25, solar=0.20, ev_satisfaction=0.10, ev_utilization=0.05, grid_stability=0.10),
        "co2_focus": MultiObjectiveWeights(co2=0.50, cost=0.15, solar=0.20, ev_satisfaction=0.08, ev_utilization=0.02, grid_stability=0.05),
        "cost_focus": MultiObjectiveWeights(co2=0.30, cost=0.35, solar=0.15, ev_satisfaction=0.10, ev_utilization=0.05, grid_stability=0.05),
        "ev_focus": MultiObjectiveWeights(co2=0.25, cost=0.15, solar=0.15, ev_satisfaction=0.25, ev_utilization=0.10, grid_stability=0.10),
        "solar_focus": MultiObjectiveWeights(co2=0.30, cost=0.15, solar=0.40, ev_satisfaction=0.08, ev_utilization=0.02, grid_stability=0.05),
    }
    return presets.get(priority, presets["co2_focus"])


def calculate_co2_reduction_indirect(solar_consumed_kw: float) -> float:
    """Calcula la reducción INDIRECTA de CO₂ por usar energía solar.

    CO₂ evitado = solar consumido × factor de emisión grid (térmica)

    Args:
        solar_consumed_kw: Energía solar consumida en este timestep (kW)

    Returns:
        CO₂ evitado en kg
    """
    co2_factor_grid = 0.4521  # kg CO₂/kWh (central térmica Iquitos)
    return solar_consumed_kw * co2_factor_grid


def calculate_co2_reduction_bess_discharge(
    bess_discharge_kw: float,
    is_nighttime: bool = False,
) -> float:
    """Calcula la reducción INDIRECTA de CO₂ por descargar BESS.

    Cuando el BESS descarga energía (almacenada del solar durante el día),
    evita importar de la red térmica. Esto es especialmente importante
    durante la noche cuando no hay generación solar.

    CO₂ evitado = energía descargada × factor de emisión grid

    Args:
        bess_discharge_kw: Energía descargada del BESS en este timestep (kW)
        is_nighttime: Si es horario nocturno (opcional, para ajustes futuros)

    Returns:
        CO₂ evitado en kg
    """
    co2_factor_grid = 0.4521  # kg CO₂/kWh (central térmica Iquitos)
    # Durante la noche, la descarga de BESS directamente reemplaza grid import
    # Durante el día, puede estar ayudando a cubrir picos
    return bess_discharge_kw * co2_factor_grid


def calculate_co2_reduction_direct(
    charger_soc_list: list[float],
    charger_types_list: list[str],
    co2_factor_moto: float = 2.5,
    co2_factor_mototaxi: float = 3.5,
    soc_threshold_full: float = 0.90,
) -> dict[str, float]:
    """Calcula la reducción DIRECTA de CO₂ por cargar vehículos eléctricos.

    CO₂ evitado = kWh cargado × km/kWh × (galones evitados/km) × kg CO₂/galón

    Args:
        charger_soc_list: Lista de SOC de cada charger [0-1]
        charger_types_list: Lista de tipos ("moto" o "mototaxi")
        co2_factor_moto: kg CO₂ evitado por moto completamente cargada
        co2_factor_mototaxi: kg CO₂ evitado por mototaxi completamente cargada
        soc_threshold_full: SOC mínimo para considerar "cargado" (0.90 = 90%)

    Returns:
        Dict con claves:
            - motos_cargadas: int
            - mototaxis_cargadas: int
            - co2_direct_total_kg: float
    """
    motos_cargadas = 0
    mototaxis_cargadas = 0
    co2_direct_total_kg = 0.0

    for soc, charger_type in zip(charger_soc_list, charger_types_list):
        if soc >= soc_threshold_full:
            if charger_type == "moto":
                motos_cargadas += 1
                co2_direct_total_kg += co2_factor_moto
            elif charger_type == "mototaxi":
                mototaxis_cargadas += 1
                co2_direct_total_kg += co2_factor_mototaxi

    return {
        "motos_cargadas": motos_cargadas,
        "mototaxis_cargadas": mototaxis_cargadas,
        "co2_direct_total_kg": co2_direct_total_kg,
    }


def calculate_solar_dispatch(
    solar_available_kw: float,
    ev_demand_kw: float,
    mall_demand_kw: float,
    bess_soc_pct: float,
    bess_max_power_kw: float,
    bess_capacity_kwh: float,
) -> dict:
    """Desglosar disponibilidad solar según 5 prioridades de despacho.

    PRIORIDADES DE DESPACHO (automáticas, NO agente RL):
    1. EV charging (demand constante 50 kW, 9AM-10PM)
    2. Mall loads (demanda no-desplazable, típicamente 100 kW)
    3. BESS charging (cargar batería si SOC < 80% y solar disponible)
    4. Grid export (vender solar excedente al grid)
    5. Grid import (comprar si falta)

    Args:
        solar_available_kw: Generación solar disponible (kW)
        ev_demand_kw: Demanda EV (típicamente 50 kW constante 9AM-10PM)
        mall_demand_kw: Demanda mall/no-desplazable (kW)
        bess_soc_pct: SOC de batería (0-100%)
        bess_max_power_kw: Máxima potencia carga/descarga (2712 kW)
        bess_capacity_kwh: Capacidad de batería (4520 kWh)

    Returns:
        dict: Desglose de despacho {
            'solar_to_ev': float,
            'solar_to_mall': float,
            'solar_to_bess': float,
            'solar_to_grid': float,
            'grid_to_ev': float,
            'grid_to_mall': float,
            'bess_to_ev': float,
            'bess_to_mall': float,
        }
    """
    solar_remaining = solar_available_kw
    dispatch = {
        "solar_to_ev": 0.0,
        "solar_to_mall": 0.0,
        "solar_to_bess": 0.0,
        "solar_to_grid": 0.0,
        "grid_to_ev": 0.0,
        "grid_to_mall": 0.0,
        "bess_to_ev": 0.0,
        "bess_to_mall": 0.0,
    }

    # PRIORIDAD 1: EV Charging (crítico)
    solar_to_ev = min(ev_demand_kw, solar_remaining)
    dispatch["solar_to_ev"] = solar_to_ev
    solar_remaining -= solar_to_ev

    # Si solar no cubre EV, usar grid
    if solar_to_ev < ev_demand_kw:
        dispatch["grid_to_ev"] = ev_demand_kw - solar_to_ev

    # PRIORIDAD 2: Mall loads
    solar_to_mall = min(mall_demand_kw, solar_remaining)
    dispatch["solar_to_mall"] = solar_to_mall
    solar_remaining -= solar_to_mall

    # Si solar no cubre mall, usar grid
    if solar_to_mall < mall_demand_kw:
        dispatch["grid_to_mall"] = mall_demand_kw - solar_to_mall

    # PRIORIDAD 3: BESS charging (si hay solar excedente y SOC < 80%)
    if solar_remaining > 0.0 and bess_soc_pct < 80.0:
        solar_to_bess = min(solar_remaining, bess_max_power_kw)
        dispatch["solar_to_bess"] = solar_to_bess
        solar_remaining -= solar_to_bess

    # PRIORIDAD 4: Grid export (solar excedente se vende al grid)
    dispatch["solar_to_grid"] = max(0.0, solar_remaining)

    return dispatch

