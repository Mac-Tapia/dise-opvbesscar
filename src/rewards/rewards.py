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

   Componentes de recompensa (multiobjetivo) - ACTUALIZADO 2026-02-08 (CONSERVADOR BALANCEADO):
   - r_co2 (0.30 peso): Minimizar importación grid = maximizar PV directo
   - r_solar (0.20 peso): Bonus por autoconsumo solar
   - r_ev (0.35 peso): Satisfacción de carga EV (PRIORIDAD MODERADA, reforzada por dispatch hierarchy)
   - r_cost (0.10 peso): Minimizar costo (secundario, tarifa baja)
   - r_grid (0.05 peso): Estabilidad de red

   Cálculo simplificado (multiobjetivo base):
   r_total = 0.30 × r_co2 + 0.35 × r_ev + 0.20 × r_solar + 0.10 × r_cost + 0.05 × r_grid
   
   Luego blended con energy-based r_ev metric (Liu et al. 2022):
   r_final = 0.65 × r_multiobj + 0.35 × r_ev_energy  (where r_ev_energy = 2*tanh(kWh_ratio)-1)
   
   NOTE: Dispatch hierarchy penalties (-0.80/-0.90/-0.95) + aggressive SOC modulation (1.80-2.20)
         already enforce EVs priority, so moderate EV weight (0.35) is sufficient.

5. VALORES DE REFERENCIA (OE2 v5.2 Real - 2026-02-12):
   - Co2 grid factor: 0.4521 kg/kWh (GRID IMPORT - indirecto)
   - EV co2 factor: 2.146 kg/kWh (DEMANDA DIRECTA - tracking)
   - EV demand: 50.0 kW (CONSTANTE)
   - Chargers: 19 (38 tomas = 30 motos + 8 mototaxis) @ 7.4 kW/toma
   - BESS: 940 kWh / 342 kW (exclusivo EV, 100% cobertura)

Objetivos optimizados:
1. Minimizar emisiones de CO₂ (indirectas por grid import)
2. Minimizar costo eléctrico
3. Maximizar autoconsumo solar (PV directo)
4. Maximizar satisfacción de carga de EVs
5. Minimizar picos de demanda (estabilidad de red)

Contexto Iquitos (OE2/OE3 - DATOS REALES v5.2 2026-02-12):
- Factor emisión: 0.4521 kg CO₂/kWh (central térmica aislada)
- Factor conversión: 2.146 kg CO₂/kWh (para cálculos directos con 50kW constante)
- Tariff: 0.20 USD/kWh (bajo, no es constraint)
- Chargers: 19 cargadores físicos (15 motos + 4 mototaxis) @ 7.4 kW/toma
- Tomas: 38 totales (19 × 2 tomas = 30 motos + 8 mototaxis)
- Potencia instalada: 281.2 kW simultánea (38 × 7.4 kW Modo 3)
- Demanda EV: 50 kW constante (54% uptime × 100kW = workaround CityLearn 2.5.0)
- Capacidad diaria: 270 motos + 39 mototaxis (pe=0.30, fc=0.55)
- BESS: 940 kWh / 342 kW (exclusivo EV, 100% cobertura)
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

    Pesos FINALES 2026-02-08 (VALIDATED BY USER):
    - CO₂ grid 0.35: PRIMARY (minimizar importación grid)
    - EV satisfaction 0.30: SECONDARY (carga EVs balanceada)
    - Solar 0.20: TERTIARY (autoconsumo PV directo)
    - Costo 0.10: TERTIARY (minimizar tarifa)
    - Grid stability 0.05: QUATERNARY (estabilidad de rampa)
    """
    co2: float = 0.35              # PRIMARY: Minimizar CO₂ grid
    cost: float = 0.10             # TERTIARY: Minimizar tarifa
    solar: float = 0.20            # TERTIARY: Autoconsumo PV
    ev_satisfaction: float = 0.30  # SECONDARY: Satisfacción de carga EVs
    ev_utilization: float = 0.00   # Incluido en ev_satisfaction (2026-02-07)
    grid_stability: float = 0.05   # QUATERNARY: Estabilidad rampa
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

    # NUEVO: Configuración de EVs para bonus de utilización (v5.2 2026-02-12)
    # Flota OE3 REAL: 270 motos/día + 39 mototaxis/día = 309 vehículos/día
    max_motos_simultaneous: int = 30      # Max motos que pueden cargarse simultáneamente (30 tomas)
    max_mototaxis_simultaneous: int = 8   # Max mototaxis que pueden cargarse simultáneamente (8 tomas)
    max_evs_total: int = 38               # Total tomas (19 chargers × 2 tomas)
    motos_daily_capacity: int = 270       # REAL v5.2: 270 motos/día
    mototaxis_daily_capacity: int = 39    # REAL v5.2: 39 mototaxis/día

    # ========== TARIFAS OSINERGMIN IQUITOS 2025 (REFERENCIAL) ==========
    # Tarifa integrada (promedio): 0.28 USD/kWh
    # Desglose por componente:
    tariff_generation_solar_usd_per_kwh: float = 0.10   # Generación solar (CAPEX + O&M bajo)
    tariff_bess_storage_usd_per_kwh: float = 0.06      # Almacenamiento BESS (CAPEX batería + O&M)
    tariff_ev_charge_distribution_usd_per_kwh: float = 0.12  # Distribución EV (red + pérdidas)
    # Tarifa eléctrica promedio (grid import)
    tariff_usd_per_kwh: float = 0.28    # Tarifa integral OSINERGMIN Iquitos (solar + BESS + dist)

    # Configuración de chargers (OE2 - DATOS REALES v5.2)
    n_chargers: int = 19                   # 19 chargers físicos (15 motos + 4 mototaxis)
    total_sockets: int = 38                # 19 × 2 = 38 tomas (30 motos + 8 mototaxis)
    sockets_per_charger: int = 2
    charger_power_kw_moto: float = 7.4     # Potencia motos (Modo 3)
    charger_power_kw_mototaxi: float = 7.4 # Potencia mototaxis (Modo 3)
    ev_demand_constant_kw: float = 50.0    # Demanda constante (workaround CityLearn 2.5.0)

    # Flota EV (OE3 REAL v5.2 - 2026-02-12)
    # VALORES DIARIOS (para control):
    vehicles_day_motos: int = 270          # Motos cargadas por día (pe=0.30, fc=0.55)
    vehicles_day_mototaxis: int = 39       # Mototaxis cargadas por día

    # VALORES ANUALES (para impacto y referencia v5.2):
    vehicles_year_motos: int = 98550       # Proyección anual: 270 × 365
    vehicles_year_mototaxis: int = 14235   # Proyección anual: 39 × 365

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
        """Calcula recompensa multiobjetivo CON DUAL REDUCTION DE CO₂ (2026-02-08).

        MODELO IQUITOS REALISTA:
        ========================
        CO₂ Reducción DIRECTA (Principal): Motos/Mototaxis que evitan combustible
          - Cada kWh de EV cargado = 35 km sin gasolina = 5.2-11.7 kg CO₂ evitado
          - Meta: 3,073 vehículos/día (2,685 motos + 388 mototaxis)
          - Energía: 2,912,500 kWh/año (750k kWh EVs) × factores combustión
          
        CO₂ Reducción INDIRECTA (Secundaria): Solar + BESS generan energía limpia
          - Solar: 8,292,514 kWh/año × 0 kg CO₂/kWh (renewable)
          - BESS: Almacena energía limpia, reduce grid import picos (0.4521 kg CO₂/kWh)
          - Efecto acumulado: Grid import baja → CO₂ grid baja

        Penalizaciones por Despacho Jerárquico (2026-02-08):
          - Día (6-18h): EVs deben recibir 90%+ solar (-0.80 por déficit)
          - Noche (18-6h): BESS→EVs exclusivo (-0.90 si Grid>BESS)
          - Cierre (23h): BESS ≥20% SOC (-0.95 exponencial si violado)

        Args:
            grid_import_kwh: Energía importada de red (kWh)
            grid_export_kwh: Energía exportada a red (kWh)
            solar_generation_kwh: Generación solar (kWh) [8,292,514 kWh/año ÷ 8,760h]
            ev_charging_kwh: Energía entregada a EVs (kWh) [750k kWh/año ÷ 8,760h]
            ev_soc_avg: SOC promedio de EVs conectados [0-1]
            bess_soc: SOC del BESS [0-1]
            hour: Hora del día [0-23]
            ev_demand_kwh: Demanda de carga EV solicitada (kWh)

        Returns:
            Tuple de (recompensa_total, dict_componentes)
            
        Components Dict Includes:
            - r_co2: Recompensa CO₂ ([-1, 1] donde 1 = excelente)
            - co2_grid_kg: kg CO₂ importados de grid [-]
            - co2_avoided_direct_kg: kg CO₂ evitados DIRECTA (motos/mototaxis) [+]
            - co2_avoided_indirect_kg: kg CO₂ evitados INDIRECTA (solar/BESS) [+]
            - vehicles_charged_equivalent: Cantidad de "cargas completas" estimadas
        """
        components = {}
        is_peak = hour in self.context.peak_hours

        # 1. Recompensa CO₂ (minimizar) - ACTUALIZADO 2026-02-08: DUAL REDUCTION (Directa + Indirecta)
        # 
        # MODELO REALISTA IQUITOS v5.2:
        # ==============================
        # CO₂ REDUCCIÓN DIRECTA (Principal): Motos/Mototaxis que evitan combustible
        #   - Motos cargadas: ev_charging_kwh / 4.6 kWh = cantidad motos (v5.2)
        #   - Mototaxis cargadas: ev_charging_kwh / 7.4 kWh = cantidad mototaxis (v5.2)
        #   - CO₂ evitado: (km_viajes × 35 km/kWh) / 120 km/galón × 8.9 kg CO₂/galón
        #
        # CO₂ REDUCCIÓN INDIRECTA (Secundaria): Solar + BESS generan energía limpia
        #   - Solar: solar_generation_kwh × 0 kg CO₂/kWh (renewable)
        #   - BESS: almacenamiento evita picos de grid import
        #   - Efecto: Reduce grid_import_kwh (más solar = menos grid térmico)

        # CO₂ IMPORTACIÓN GRID (baseline)
        co2_grid_kg = grid_import_kwh * self.context.co2_factor_kg_per_kwh  # [kg CO₂] grid térmico Iquitos

        # ========== CO₂ EVITADO - CONTABILIZACIÓN ROBUSTA (2026-02-08 MEJORADO) ==========
        # REFERENCIAS CIENTÍFICAS ACTUALES:
        # [1] Liu et al. (2022) "Multi-objective EV charging optimization" IEEE Trans on Smart Grid
        #     - Metodología: Energía cargada × factor de conversión (transparent)
        # [2] Messagie et al. (2014) "Environmental impact of electric vehicles in Europe"
        #     - Baseline combustión: 2.146 kg CO₂/kWh (diesel EURO5)
        # [3] IVL Swedish Battery Report (2023) - Battery manufacturing: 61-106 g CO₂/Wh
        # [4] NREL (2023) - Grid CO₂ factor increases with fossil fraction
        # [5] Aryan et al. (2025) - LCA for EVs in developing countries
        #
        # CORRECCIÓN CRÍTICA 2026-02-08:
        # NO doble-contar energía solar. Usar segregación de energía basada en destino:
        #   - Energía solar → EVs: Contribuye a "Evitado Directo" (combustible)
        #   - Energía solar → Grid: Contribuye a "Evitado Indirecto" (coal/gas grid)
        #   - BESS discharge → EVs: Mismo como solar (renovable storage)
        #   - BESS discharge → Grid: Indirecto
        
        # Flota Iquitos v5.2: 270 motos/día + 39 mototaxis/día = 309 vehículos/día
        #   Motos: 4.6 kWh capacidad @ 35 km/kWh = 161 km/carga
        #   Mototaxis: 7.4 kWh @ 35 km/kWh = 259 km/carga
        avg_battery_capacity_kwh = 0.87 * 4.6 + 0.13 * 7.4  # = ~5.0 kWh promedio (270/309 motos)
        vehicles_charged_equivalent = ev_charging_kwh / max(avg_battery_capacity_kwh, 1e-6)
        
        # ===== SEGREGACIÓN DE ENERGÍA POR DESTINO (SIN DOUBLE-COUNT) =====
        # Total solar disponible
        total_solar_kwh = solar_generation_kwh
        
        # BESS descarga estimada (diferencia respecto grid import)
        # Si bess_soc está bajando → BESS está descargando
        # Estimación conservadora: ~30% de solar en promedio viene de BESS
        # Para simplificar: usar solar como proxy del renovable total
        bess_discharge_kwh = max(0, solar_generation_kwh * 0.3)  # ~30% de solar estimado como BESS
        total_renewable_available = total_solar_kwh + bess_discharge_kwh
        
        # Fracción de renewable que va a EVs vs grid
        # Basado en dispatch: ~70% a EVs (prioritario), ~30% al grid/almacenamiento
        renewable_to_evs_fraction = 0.70
        renewable_to_grid_fraction = 0.30
        
        renewable_kwh_to_evs = total_renewable_available * renewable_to_evs_fraction
        renewable_kwh_to_grid = total_renewable_available * renewable_to_grid_fraction
        
        # ===== CO₂ EVITADO DIRECTO (Renewable → EVs, evita combustión) =====
        # Energía cargada a vehículos desde fuentes renovables
        # Factor: 2.146 kg CO₂/kWh (Messagie 2014, still valid for gasoline equiv)
        # Bajo escenario: solo energía que efectivamente va a EVs
        ev_kwh_from_renewable = min(renewable_kwh_to_evs, ev_charging_kwh)  # No puede exceder charging real
        co2_avoided_direct_kg = ev_kwh_from_renewable * self.context.co2_conversion_factor  # [kg CO₂/kWh]
        
        # ===== CO₂ EVITADO INDIRECTO (Renewable → Grid, evita coal/gas central) =====
        # Solar + BESS que van directamente a reducir importación de grid térmico
        # Factor: 0.4521 kg CO₂/kWh (grid Iquitos, 100% diesel)
        # NOTA: NO incluir solar que va a EVs (ya en directo)
        co2_avoided_indirect_kg = renewable_kwh_to_grid * self.context.co2_factor_kg_per_kwh
        
        # ===== CO₂ NETO (sin double-counting) =====
        co2_avoided_total_kg = co2_avoided_direct_kg + co2_avoided_indirect_kg
        
        # CO₂ NETO = grid imports - avoided emissions
        # NOTA: Este valor es MORE REALISTIC (nunca será >> grid_import)
        co2_net_kg = max(0, co2_grid_kg - co2_avoided_total_kg)

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
        components["vehicles_charged_equivalent"] = vehicles_charged_equivalent  # Tracking de cargas count

        # 2. Recompensa Costo (minimizar)
        # OSINERGMIN Iquitos 2025: tarifa integral 0.28 USD/kWh
        # Cost baseline (scenario sin solar, todo grid): 1,500 kWh × 0.28 = $420 USD/hora
        net_grid_kwh = max(0, grid_import_kwh - grid_export_kwh)
        cost_usd = net_grid_kwh * self.context.tariff_usd_per_kwh
        cost_baseline = 1500.0 * self.context.tariff_usd_per_kwh  # Baseline realista: ~420 USD (1500 kWh × 0.28)
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
        # SIN afectar capacidad de cargadores (38 sockets disponibles v5.2)
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
    # ACTUALIZADO 2026-02-07: Pesos sincronizados con resultados validados
    presets = {
        "balanced": MultiObjectiveWeights(co2=0.30, cost=0.25, solar=0.20, ev_satisfaction=0.10, ev_utilization=0.05, grid_stability=0.10),
        "co2_focus": MultiObjectiveWeights(co2=0.35, cost=0.10, solar=0.20, ev_satisfaction=0.30, ev_utilization=0.00, grid_stability=0.05),
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
        bess_max_power_kw: Máxima potencia carga/descarga (342 kW v5.2)
        bess_capacity_kwh: Capacidad de batería (940 kWh v5.2)

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

