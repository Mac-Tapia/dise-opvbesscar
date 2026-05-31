"""
ev_charging_wrapper.py — IquitosEVChargingWrapper
=====================================================================
Wrapper Gymnasium sobre CityLearnEnv que amplía el espacio de acciones
para incluir el control de cargadores EV de motos y mototaxis.

OBJETIVO OE3: Seleccionar el agente IA para gestión de recarga de motos
y mototaxis que contribuye cuantificablemente a la reducción de CO₂ en
Iquitos (0.4521 kg CO₂/kWh, 0.87/0.54 kg CO₂/L gasolina).

INFRAESTRUCTURA v5.7:
  - Cargadores motos     : 15 × 2 sockets Modo 3 × 7.4 kW = 222 kW max simultáneo
  - Cargadores mototaxis : 4  × 2 sockets Modo 3 × 7.4 kW = 59.2 kW max simultáneo
  - Total EV             : 19 cargadores × 2 sockets = 38 sockets = 281.2 kW
  - BESS                 : 2,000 kWh / 400 kW, DoD 80%, efic. 95%
  - PV                   : 4,050 kWp (Iquitos, perfil PVGIS horario)

ESPACIO DE ACCIÓN EXTENDIDO (3D):
  action[0]  bess_action      ∈ [-1, +1]  — BESS: -1=descarga máx, +1=carga máx
  action[1]  ev_motos_frac    ∈ [0, 1]    — fracción de demanda motos a cargar AHORA
  action[2]  ev_mototaxis_frac ∈ [0, 1]   — fracción de demanda mototaxis a cargar AHORA

  El agente puede DIFERIR la carga EV (action < 1.0) para, por ejemplo,
  esperar la generación solar (peak 10:00-14:00 en Iquitos).
  La deuda diaria se penaliza si no se cumple antes del cierre del día (hora 23).

ESPACIO DE OBSERVACIÓN EXTENDIDO (19D = CityLearn 12D + EV 5D + tarifa 2D):
  [0-11]  obs CityLearn estándar (month, hour, day_type, temp, irr_diff, irr_dir,
          carbon_intensity, non_shiftable_load, solar_gen, bess_soc,
          net_electricity_consumption, electricity_pricing)
  — electricity_pricing: tarifa HP/HFP normalizada por CityLearn desde pricing.csv
  [12]  ev_motos_demand_norm    — demanda motos hora actual (normaliz. 0-1)
  [13]  ev_mototaxis_demand_norm — demanda mototaxis hora actual
  [14]  ev_motos_debt_norm      — energía motos pendiente del día (0-1)
  [15]  ev_mototaxis_debt_norm  — energía mototaxis pendiente del día (0-1)
  [16]  hour_sin                — sin(2π·hour/24), señal periódica para urgencia
  [17]  tarifa_norm             — (tarifa_total - HFP) / (HP - HFP) ∈ [0,1]; 0=HFP barato, 1=HP caro
  [18]  is_hora_punta           — {0,1} señal binaria del período tarifario OSINERGMIN

RECOMPENSA MULTI-OBJETIVO (CO2_DUAL_FOCUS v8.1 + EV estocástico):
  r_direct_co2    0.20  — CO₂ directo evitado: motos+mototaxis vs gasolina
  r_indirect_co2  0.30  — CO₂ indirecto: grid_import × co2_factor horario
  r_ev_complete   0.35  — completar carga EV sin deuda operativa
  r_bess_solar    0.07  — timing solar BESS (+bonus solar, -penalty nocturno)
  r_solar         0.04  — PV self-consumption
  r_grid_stable   0.02  — ramp smoothing
  r_cost          0.02  — costo OSINERGMIN HP/HFP

Uso:
    from src.citylearnv2.ev_charging_wrapper import IquitosEVChargingWrapper
    from src.citylearnv2.env_factory import create_iquitos_env

    env = create_iquitos_env()
    # → obs_dim = 19, action_dim = 3

Notas de diseño:
    - CityLearn tiene non_shiftable_load = mall_kwh (solo mall, sin EVs)
    - Este wrapper inyecta ev_dispatch en el balance energético cada paso
    - El balance real: mall + ev_dispatch + bess_net vs solar → grid_import
    - La reward se computa en el wrapper, NO la del CityLearnEnv interno
=====================================================================
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, SupportsFloat

import math
import gymnasium
import numpy as np
from gymnasium import spaces

from src.dimensionamiento.oe2._constants import (
    TARIFA_ENERGIA_HP_SOLES,
    TARIFA_ENERGIA_HFP_SOLES,
    HORA_INICIO_HP,
    HORA_FIN_HP,
)

logger = logging.getLogger(__name__)

# ── Rutas ─────────────────────────────────────────────────────────────────────
# El wrapper lee EXCLUSIVAMENTE de data/interim/citylearn_v2/ (datasets CityLearn v2).
# Los archivos OE2 en data/iquitos_ev_mall/ son la fuente primaria, pero son
# transformados por schema_builder.py antes del entrenamiento — NO se acceden
# directamente aquí. El flujo es:
#   OE2 raw → schema_builder.py → data/interim/citylearn_v2/ → wrapper
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CL_DATA_DIR        = _PROJECT_ROOT / "data" / "interim" / "citylearn_v2"
_ENERGY_SIM_CSV     = _CL_DATA_DIR / "energy_simulation.csv"       # CityLearn v2: mall demand + solar (columnas estándar)
_WEATHER_CSV        = _CL_DATA_DIR / "weather.csv"                  # CityLearn v2: temperatura, irradiancia
_TARIFFS_CSV        = _CL_DATA_DIR / "tariffs_osinergmin.csv"       # wrapper: HP/HFP OSINERGMIN + mall_cost
_EV_MOTOS_CSV       = _CL_DATA_DIR / "ev_charger_motos.csv"         # CityLearn v2: ChargerSimulation 30 sockets motos
_EV_MOTOTAXIS_CSV   = _CL_DATA_DIR / "ev_charger_mototaxis.csv"    # CityLearn v2: ChargerSimulation 8 sockets mototaxis
# Datasets individuales CityLearn (data/iquitos_ev_mall/) — generados por data_loader
_OE2_DATA_DIR         = _PROJECT_ROOT / "data" / "iquitos_ev_mall"
_BESS_CSV             = _OE2_DATA_DIR / "bess_timeseries.csv"
_CO2_EMISSIONS_CSV    = _OE2_DATA_DIR / "co2_emissions.csv"
_TARIFFS_IQTS_CSV     = _OE2_DATA_DIR / "tariffs_osinergmin.csv"

# ── Constantes del sistema Iquitos ──────────────────────────────────────────
CO2_GRID_KG_PER_KWH: float = 0.4521        # kg CO₂/kWh red aislada Iquitos (MINEM)
CO2_FACTOR_MOTO: float = 0.87              # kg CO₂/kWh moto gasolina 125cc (IPCC 2006)
CO2_FACTOR_MOTOTAXI: float = 0.54          # kg CO₂/kWh mototaxi 3 ruedas 150cc

# ── OE2 Dimensionamiento: Playa de Estacionamiento ───────────────────────────
# Fuente: Encuesta OE2 parking, mall apertura 9h-22h (13h), hora punta 18h-22h (4h)
# DISEÑO DE CARGADORES (ref. chargers.py v5.4+):
#   900 motos + 130 mototaxis = vehículos en HORA PUNTA (18h-22h, 4h)
#   → Punta representa 65% del tráfico diario total (9h-22h)
#   → Total diario real: 900/0.65 ≈ 1,385 motos/día | 130/0.65 ≈ 200 mototaxis/día

# ── Baterías EV: SOC mínimo y máximo (igual que BESS DoD 80%) ────────────────
# OE2 v5.7: los vehículos llegan con SOC_MIN (descargado en ruta) y se cargan
# hasta SOC_MAX. Límite inferior protege el ciclo de vida de la batería.
EV_MOTO_BAT_KWH: float      = 4.6    # capacidad batería moto 125cc (kWh)
EV_MOTOTAXI_BAT_KWH: float  = 7.4    # capacidad batería mototaxi 150cc (kWh)
EV_SOC_MIN: float = 0.20             # SOC mínimo EV — 20 % (llegada / fin descarga)
EV_SOC_MAX: float = 0.80             # SOC máximo EV — 80 % (objetivo de carga) → DoD 80 %
EV_SOC_ARRIVAL_MAX: float = 0.60     # SOC máximo de llegada — vehículo llega hasta 60% cargado
EV_CHARGER_KW: float = 7.4           # potencia por socket Modo 3

# Variabilidad operacional por episodio. La demanda EV no es fija: se remuestrean
# conteos, hora de llegada, SOC inicial y tiempo disponible de carga.
EV_STOCH_DAILY_SIGMA: float = 0.15
EV_STOCH_ARRIVAL_OFFSETS: tuple[int, int, int] = (-1, 0, 1)
EV_STOCH_ARRIVAL_PROBS: tuple[float, float, float] = (0.15, 0.70, 0.15)
EV_MOTO_DWELL_HOURS: tuple[float, float, float] = (0.50, 1.50, 4.00)
EV_MOTOTAXI_DWELL_HOURS: tuple[float, float, float] = (0.50, 1.00, 3.00)
EV_CHARGER_EFF: float = 0.95         # eficiencia cargador Modo 3 (OE2 chargers.py)

# Energía útil por visita: (SOC_MAX - SOC_MIN) × cap_bat / efic_cargador
OE2_MOTOS_PEAK_4H: int       = 900    # motos en hora punta 18h-22h (65% del tráfico diario)
OE2_MOTOTAXIS_PEAK_4H: int   = 130    # mototaxis en hora punta 18h-22h (65% del tráfico diario)
OE2_PEAK_FRACTION: float     = 0.65   # hora punta = 65% del total de vehículos diarios
OE2_MOTOS_DAILY: int         = round(OE2_MOTOS_PEAK_4H    / OE2_PEAK_FRACTION)  # = 1,385 motos/día total
OE2_MOTOTAXIS_DAILY: int     = round(OE2_MOTOTAXIS_PEAK_4H / OE2_PEAK_FRACTION) # = 200 mototaxis/día total
# Derivados explícitamente de EV_SOC_MIN/MAX para documentar el 20 % mínimo:
OE2_ENERGY_PER_MOTO_KWH: float     = round((EV_SOC_MAX - EV_SOC_MIN) * EV_MOTO_BAT_KWH    / EV_CHARGER_EFF, 3)  # ≈ 2.906 kWh
OE2_ENERGY_PER_MOTOTAXI_KWH: float = round((EV_SOC_MAX - EV_SOC_MIN) * EV_MOTOTAXI_BAT_KWH / EV_CHARGER_EFF, 3)  # ≈ 4.674 kWh

# ── F0 Emisiones Combustión FIJA: todo el parque ICE en estado actual (sin proyecto) ──
# Constante de módulo: calculada 1 vez al cargar el módulo, usada en cada step()
# CORRECCIÓN v2: 900 motos+130 mototaxis es el valor de HORA PUNTA (65% diario),
#   no el total diario. El total correcto es OE2_MOTOS_DAILY=1,385 y OE2_MOTOTAXIS_DAILY=200.
# Relación: Punta (18-22h, 4h) = 65% del total → 35% fuera punta (9-18h, 9h)
# Valores numéricos (ICE, sin proyecto):
#   Motos    : 1,385 veh/día × 2.906 kWh/visita × 0.87 kg/kWh = 3,502 kg CO₂/día
#   Mototaxis:   200 veh/día × 4.674 kWh/visita × 0.54 kg/kWh =   505 kg CO₂/día
#   Total    : 4,007 kg CO₂/día → 1,462,555 kg CO₂/año (solo combustión directa)
_F0_CO2_MOTOS_PER_DAY: float      = OE2_MOTOS_DAILY    * OE2_ENERGY_PER_MOTO_KWH     * CO2_FACTOR_MOTO
_F0_CO2_MOTOTAXIS_PER_DAY: float  = OE2_MOTOTAXIS_DAILY * OE2_ENERGY_PER_MOTOTAXI_KWH * CO2_FACTOR_MOTOTAXI
_F0_CO2_COMBUSTION_PER_DAY: float = _F0_CO2_MOTOS_PER_DAY + _F0_CO2_MOTOTAXIS_PER_DAY  # kg CO₂/día
_F0_CO2_COMBUSTION_ANNUAL: float  = _F0_CO2_COMBUSTION_PER_DAY * 365.0                  # kg CO₂/año
_F0_CO2_COMBUSTION_PER_H: float   = _F0_CO2_COMBUSTION_PER_DAY / 24.0                  # kg CO₂/hora (por timestep)

EV_MOTOS_MAX_KW: float = 222.0              # 15 carg × 2 sock × 7.4 kW
EV_MOTOTAXIS_MAX_KW: float = 59.2          # 4  carg × 2 sock × 7.4 kW
MAX_GRID_IMPORT_KW: float = 1500.0         # referencia de normalización: mall_peak(~1400kW)+EVs(~281kW)-solar_min(~0)=1681→1500 permite gradiente útil
MAX_CO2_DIRECT_PER_HOUR: float = 60.0      # kg CO₂/h máximo directo (estimado)

# ── Tarifas OSINERGMIN — Electro Oriente S.A., Iquitos (Res. N° 047-2024-OS/CD) ──
# Importadas de src/dimensionamiento/oe2/_constants.py (fuente única de verdad)
#   HP  (18-22h): 0.45 S/./kWh  |  HFP (resto): 0.28 S/./kWh
_HORAS_PUNTA_SET: frozenset[int] = frozenset(range(HORA_INICIO_HP, HORA_FIN_HP))
# Normalización costo: máximo teórico = importación máxima × tarifa HP
MAX_COST_PER_STEP_SOLES: float = MAX_GRID_IMPORT_KW * TARIFA_ENERGIA_HP_SOLES  # 1500 × 0.45 = 675 S/./h
BESS_SOC_MIN: float = 0.20                 # SOC mínimo BESS — 20% (DoD 80%), igual que EV_SOC_MIN
BESS_SOC_MAX: float = 1.00                 # SOC máximo BESS
BESS_MAX_KW: float = 400.0                 # Potencia máxima BESS (kW)
BESS_CAPACITY_KWH: float = 2000.0          # Capacidad energética BESS (kWh) — OE2 v5.3
BESS_EFF_ROUNDTRIP: float = 0.95           # Eficiencia round-trip lithium-ion (OE2 bess.py)

# Pesos de recompensa OE3 CO2_DUAL_FOCUS v8.1 (demanda EV estocástica + Modo 3)
# v8.1 prioriza cumplimiento EV para evitar políticas que reducen CO2 dejando
# deuda de carga; CO2 indirecta sigue siendo la palanca principal de F2.
#
# OBJETIVO OE3-1: Reducción CO2 DIRECTA (evitar combustión ICE motos/mototaxis)
#   _W_DIRECT_CO2 = 0.20  — r_direct_co2: beneficio por electrificación vehicular
#
# OBJETIVO OE3-2: Reducción CO2 INDIRECTA (minimizar importación red diesel Iquitos)
#   _W_INDIRECT_CO2 = 0.30 — r_indirect_co2: penaliza grid_import × co2_factor
#
# OBJETIVO OE3-3: Satisfacción/cantidad de carga EV (motos + mototaxis)
#   _W_EV_COMPLETE = 0.35  — completion ratio + penalización deuda diaria
#
# REGLA OPERACIONAL BESS: cargar con solar (6-18h), NO con diesel nocturno
#   _W_BESS_SOLAR = 0.07   — r_bess_solar: +bonus solar, -penalty carga nocturna
#
# SECUNDARIOS (suman 0.08):
#   _W_SOLAR = 0.04        — r_solar: autoconsumo PV (superpuesto con OE3-2)
#   _W_GRID_STABLE = 0.02  — r_grid_stable: suavizado de rampas
#   _W_COST = 0.02         — r_cost: OSINERGMIN (señal parcialmente en OE3-2)
#
# Suma: 0.20+0.30+0.35+0.07+0.04+0.02+0.02 = 1.00
_W_DIRECT_CO2: float   = 0.20   # OE3-1: CO2 directa (ICE vs EV)
_W_INDIRECT_CO2: float  = 0.30   # OE3-2: CO2 indirecta (grid × factor)
_W_EV_COMPLETE: float   = 0.35   # OE3-3: satisfacción/cantidad carga EV
_W_BESS_SOLAR: float    = 0.07   # regla op: BESS carga con solar (no diesel nocturno)
_W_SOLAR: float         = 0.04   # autoconsumo PV
_W_GRID_STABLE: float   = 0.02   # estabilidad red
_W_COST: float          = 0.02   # costo tarifario OSINERGMIN HP/HFP

# Umbral solar mínimo para considerar que hay generación aprovechable (kW)
_SOLAR_CHARGE_THRESHOLD_KW: float = 200.0  # ~5% de 4162 kWp DC diseño OE2 (≈208 kW; 200 kW conservador)


class IquitosEVChargingWrapper(gymnasium.Wrapper):
    """Wrapper sobre CityLearnEnv con control de cargadores EV (motos + mototaxis).

    Extiende el espacio de acciones de 1D (BESS) a 3D (BESS + motos + mototaxis)
    y añade observaciones del estado de carga EV al vector de obs de CityLearn.

    La recompensa multi-objetivo está alineada con el Objetivo Específico 3 (OE3)
    del proyecto PVBESSCAR: reducción cuantificable de CO₂ en Iquitos mediante
    gestión inteligente de recarga de motos y mototaxis eléctricas.

    Parameters
    ----------
    env : CityLearnEnv
        Entorno base CityLearn v2. Debe tener central_agent=True,
        1 edificio (IquitosEVMall), BESS activado.
        non_shiftable_load contiene solo la demanda del mall.
    ev_demand_csv : Path, optional
        Deprecado — ignorado. El wrapper lee de data/interim/citylearn_v2/.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        env: Any,
        ev_demand_csv: Path | None = None,
    ) -> None:
        super().__init__(env)

        # ── Cargar datasets CityLearn v2 (data/interim/citylearn_v2/) ──────────
        # Pipeline: OE2 raw → schema_builder.py → data/interim/citylearn_v2/ → aquí
        # Si los archivos no existen, regenerar con build_citylearn_schema().
        import pandas as _pd

        def _require(path: Path) -> _pd.DataFrame:
            if not path.exists():
                raise FileNotFoundError(
                    f"{path.name} no encontrado en {path.parent}. "
                    "Ejecuta: python -m src.citylearnv2.schema_builder"
                )
            return _pd.read_csv(path)

        # ── EV charger datasets (ChargerSimulation format + ev_demand_kwh) ────
        motos_df     = _require(_EV_MOTOS_CSV)
        mototaxis_df = _require(_EV_MOTOTAXIS_CSV)
        self._n = len(motos_df)

        # Perfil base anual (8760h) — inmutable; se aplica variación por episodio en reset()
        self._ev_motos_demand_base: np.ndarray    = motos_df["ev_demand_kwh"].to_numpy(dtype=np.float64)
        self._ev_mototaxis_demand_base: np.ndarray = mototaxis_df["ev_demand_kwh"].to_numpy(dtype=np.float64)
        self._ev_motos_demand    = self._ev_motos_demand_base.copy()
        self._ev_mototaxis_demand = self._ev_mototaxis_demand_base.copy()
        # CO₂ directo: energía EV × factor emisión combustible desplazado (base; reset() lo reemplaza)
        self._co2_motos: np.ndarray    = self._ev_motos_demand * CO2_FACTOR_MOTO
        self._co2_mototaxis: np.ndarray = self._ev_mototaxis_demand * CO2_FACTOR_MOTOTAXI
        # Referencia ICE per-cargador (estocástica por episodio); inicializada con base para seguridad
        self._co2_ref_motos_h: np.ndarray    = self._co2_motos.copy()
        self._co2_ref_mototaxis_h: np.ndarray = self._co2_mototaxis.copy()
        self._co2_ref_direct_h: np.ndarray   = self._co2_motos + self._co2_mototaxis

        # ChargerSimulation fields — usados para logging y métricas
        self._chr_motos_hora_base: np.ndarray = motos_df["vehicles_per_hour"].to_numpy(dtype=np.float64)
        self._chr_mototaxis_hora_base: np.ndarray = mototaxis_df["vehicles_per_hour"].to_numpy(dtype=np.float64)
        self._chr_motos_hora: np.ndarray    = self._chr_motos_hora_base.copy()
        self._chr_mototaxis_hora: np.ndarray = self._chr_mototaxis_hora_base.copy()
        self._chr_motos_active_sockets: np.ndarray = motos_df["active_sockets"].to_numpy(dtype=np.float64)
        self._chr_mototaxis_active_sockets: np.ndarray = mototaxis_df["active_sockets"].to_numpy(dtype=np.float64)
        self._chr_total_hora: np.ndarray    = self._chr_motos_hora + self._chr_mototaxis_hora
        self._chr_ev_total_kwh: np.ndarray  = self._ev_motos_demand + self._ev_mototaxis_demand
        self._chr_co2_directo: np.ndarray   = self._co2_motos + self._co2_mototaxis
        self._chr_co2_neto_hora: np.ndarray = self._chr_co2_directo
        self._ev_motos_arrival_soc: np.ndarray = np.full(self._n, EV_SOC_MIN, dtype=np.float64)
        self._ev_mototaxis_arrival_soc: np.ndarray = np.full(self._n, EV_SOC_MIN, dtype=np.float64)
        self._ev_motos_active_soc: np.ndarray = np.full(self._n, EV_SOC_MIN, dtype=np.float64)
        self._ev_mototaxis_active_soc: np.ndarray = np.full(self._n, EV_SOC_MIN, dtype=np.float64)
        self._ev_motos_charge_time_h: np.ndarray = np.zeros(self._n, dtype=np.float64)
        self._ev_mototaxis_charge_time_h: np.ndarray = np.zeros(self._n, dtype=np.float64)
        self._ev_motos_dwell_h: np.ndarray = np.zeros(self._n, dtype=np.float64)
        self._ev_mototaxis_dwell_h: np.ndarray = np.zeros(self._n, dtype=np.float64)
        # EV charger state (ChargerSimulation: 1=parked, 3=idle)
        self._chr_motos_state: np.ndarray   = motos_df["electric_vehicle_charger_state"].to_numpy(dtype=np.int32)
        self._chr_mototaxis_state: np.ndarray = mototaxis_df["electric_vehicle_charger_state"].to_numpy(dtype=np.int32)

        # Máximos del año para normalizar observaciones de deuda
        self._daily_motos_max: float = float(
            max(self._ev_motos_demand.reshape(365, 24).sum(axis=1).max(), 1.0)
        )
        self._daily_mototaxis_max: float = float(
            max(self._ev_mototaxis_demand.reshape(365, 24).sum(axis=1).max(), 1.0)
        )

        logger.info(
            "EV charger datasets cargados (CityLearn v2): motos=%.0f kWh/año | "
            "mototaxis=%.0f kWh/año | CO₂ directo=%.0f kg/año",
            self._ev_motos_demand.sum(),
            self._ev_mototaxis_demand.sum(),
            (self._co2_motos + self._co2_mototaxis).sum(),
        )

        # ── energy_simulation.csv — edificio: mall + solar + tarifas OSINERGMIN ─
        # Fuente: data/interim/citylearn_v2/energy_simulation.csv (generado por schema_builder)
        # Columnas requeridas por CityLearn v2 EnergySimulation + extensiones OSINERGMIN
        energy_sim = _require(_ENERGY_SIM_CSV)
        # solar_generation en W/kWp → kW total: debe usar el mismo kWp que schema_builder
        # Se lee automáticamente de OE2Metadata → CERTIFICACION_SOLAR_DATASET_2024.json
        try:
            from src.dimensionamiento.oe2.oe2_metadata import get_metadata as _gm
            _PV_KWP: float = _gm().pv_kwp_dc   # kWp DC real leído del JSON OE2
        except Exception:
            _PV_KWP: float = 4162.0             # fallback si OE2Metadata no disponible
        solar_gen_w_per_kwp = energy_sim["solar_generation"].to_numpy(dtype=np.float64)
        self._solar_kw: np.ndarray           = solar_gen_w_per_kwp * _PV_KWP / 1000.0
        self._solar_kwh: np.ndarray          = self._solar_kw                          # 1h timestep → kWh = kW
        self._solar_co2_indirect: np.ndarray = self._solar_kwh * CO2_GRID_KG_PER_KWH

        # Mall demand (non_shiftable_load = SOLO MALL, sin EVs)
        self._mall_kw: np.ndarray            = energy_sim["non_shiftable_load"].to_numpy(dtype=np.float64)

        # Tarifas OSINERGMIN (Electro Oriente, Res. N° 047-2024-OS/CD)
        # Archivo separado de energy_simulation.csv (CityLearn v2 rechaza columnas extra)
        tariffs = _require(_TARIFFS_CSV)
        self._mall_co2_indirect: np.ndarray  = tariffs["mall_co2_indirect_kg"].to_numpy(dtype=np.float64)
        self._mall_is_punta: np.ndarray      = tariffs["is_hora_punta"].to_numpy(dtype=np.float64)
        self._mall_tarifa: np.ndarray        = tariffs["tarifa_soles_kwh"].to_numpy(dtype=np.float64)
        self._mall_cost_soles: np.ndarray    = tariffs["mall_cost_soles"].to_numpy(dtype=np.float64)

        # ── weather.csv — temperatura e irradiancia ───────────────────────────
        weather = _require(_WEATHER_CSV)
        self._solar_ghi: np.ndarray   = (weather["diffuse_solar_irradiance"].to_numpy(dtype=np.float64)
                                          + weather["direct_solar_irradiance"].to_numpy(dtype=np.float64))
        self._solar_temp: np.ndarray  = weather["outdoor_dry_bulb_temperature"].to_numpy(dtype=np.float64)
        self._solar_viento: np.ndarray = np.zeros(self._n, dtype=np.float64)   # no en weather.csv
        self._solar_is_punta: np.ndarray = self._mall_is_punta                 # misma señal HP/HFP
        self._solar_tarifa: np.ndarray   = self._mall_tarifa                   # misma tarifa
        self._solar_ahorro: np.ndarray   = np.zeros(self._n, dtype=np.float64) # calculado en step()

        # ── co2_emissions.csv — factores horarios todo el sistema (diesel Iquitos + ICE vehículos)
        # Estacionalidad: lluviosa dic-may=0.43, seca jun-nov=0.47 kg CO₂/kWh
        # HP (18-23h): factor_mes × 1.35 | HFP: factor_mes × 0.908
        if _CO2_EMISSIONS_CSV.exists():
            co2_df = _pd.read_csv(_CO2_EMISSIONS_CSV)
            self._co2_factor: np.ndarray = co2_df["co2_factor_kg_kwh"].to_numpy(dtype=np.float64)
        else:
            from src.dimensionamiento.oe2._constants import (
                FACTOR_CO2_HP_KG_KWH, FACTOR_CO2_HFP_KG_KWH, HORA_INICIO_HP, HORA_FIN_HP
            )
            _hours_tmp = np.arange(8760) % 24
            _is_hp_tmp = (_hours_tmp >= HORA_INICIO_HP) & (_hours_tmp < HORA_FIN_HP)
            self._co2_factor = np.where(_is_hp_tmp, FACTOR_CO2_HP_KG_KWH, FACTOR_CO2_HFP_KG_KWH)
            logger.warning("co2_emissions.csv no encontrado — usando factores HP/HFP fijos (fallback)")

        # ── tariffs_osinergmin.csv — tarifas OSINERGMIN + mecanismo compensación SSAA ─
        # Pliego MT3 Electro Oriente — Res. N° 047-2024-OS/CD
        # Incluye: energía HP/HFP, cargo potencia, AAPP, mecanismo compensación, ahorro social
        if _TARIFFS_IQTS_CSV.exists():
            _tariffs_df = _pd.read_csv(_TARIFFS_IQTS_CSV)
            self._tarifa_energia: np.ndarray = _tariffs_df["tarifa_energia_soles_kwh"].to_numpy(dtype=np.float64)
            self._tarifa_total: np.ndarray   = _tariffs_df["tarifa_total_soles_kwh"].to_numpy(dtype=np.float64)
            self._mecanismo_comp: np.ndarray = _tariffs_df["mecanismo_compensacion_soles_kwh"].to_numpy(dtype=np.float64)
            self._ahorro_social: np.ndarray  = _tariffs_df["ahorro_social_kwh_evitado_soles"].to_numpy(dtype=np.float64)
        else:
            _hours_tmp2 = np.arange(8760) % 24
            _is_hp_tmp2 = (_hours_tmp2 >= HORA_INICIO_HP) & (_hours_tmp2 < HORA_FIN_HP)
            self._tarifa_energia = np.where(_is_hp_tmp2, TARIFA_ENERGIA_HP_SOLES, TARIFA_ENERGIA_HFP_SOLES)
            self._tarifa_total   = self._tarifa_energia + 0.0116
            self._mecanismo_comp = 0.75 - self._tarifa_energia
            self._ahorro_social  = self._tarifa_total + self._mecanismo_comp
            logger.warning("tariffs_osinergmin.csv no encontrado — usando tarifas fijas (fallback)")

        # ── bess_timeseries.csv — TODAS las columnas OE2 (27 columnas) ───
        if not _BESS_CSV.exists():
            raise FileNotFoundError(f"bess_timeseries.csv no encontrado en {_BESS_CSV}")
        bess_src = _pd.read_csv(_BESS_CSV)
        # Balance PV
        self._bess_pv_kwh: np.ndarray           = bess_src["pv_kwh"].to_numpy(dtype=np.float64)
        self._bess_ev_kwh: np.ndarray           = bess_src["ev_kwh"].to_numpy(dtype=np.float64)
        self._bess_mall_kwh: np.ndarray         = bess_src["mall_kwh"].to_numpy(dtype=np.float64)
        self._bess_load_kwh: np.ndarray         = bess_src["load_kwh"].to_numpy(dtype=np.float64)
        # Despacho PV
        self._bess_pv_to_ev: np.ndarray         = bess_src["pv_to_ev_kwh"].to_numpy(dtype=np.float64)
        self._bess_pv_to_bess: np.ndarray       = bess_src["pv_to_bess_kwh"].to_numpy(dtype=np.float64)
        self._bess_pv_to_mall: np.ndarray       = bess_src["pv_to_mall_kwh"].to_numpy(dtype=np.float64)
        # pv_curtailed_kwh no está en el CSV — se aproxima como excedente PV no usado
        _bess_pv = bess_src["pv_kwh"].to_numpy(dtype=np.float64)
        _bess_load = bess_src["load_kwh"].to_numpy(dtype=np.float64)
        self._bess_pv_curtailed: np.ndarray     = np.maximum(0.0, _bess_pv - _bess_load)
        # BESS operación
        self._bess_charge_kwh: np.ndarray       = bess_src["bess_charge_kwh"].to_numpy(dtype=np.float64)
        self._bess_discharge_kwh: np.ndarray    = bess_src["bess_discharge_kwh"].to_numpy(dtype=np.float64)
        self._bess_action_kwh: np.ndarray       = bess_src["bess_action_kwh"].to_numpy(dtype=np.float64)
        # bess_mode: categórico ('idle'=0, 'charge'=1, 'discharge'=-1)
        _mode_map = {"idle": 0, "charge": 1, "discharge": -1}
        self._bess_mode: np.ndarray             = bess_src["bess_mode"].map(_mode_map).fillna(0).to_numpy(dtype=np.int8)
        self._bess_to_ev: np.ndarray            = bess_src["bess_to_ev_kwh"].to_numpy(dtype=np.float64)
        self._bess_to_mall: np.ndarray          = bess_src["bess_to_mall_kwh"].to_numpy(dtype=np.float64)
        self._bess_peak_shaving: np.ndarray     = np.zeros(self._n, dtype=np.float64)   # not in CSV schema
        self._bess_total_disc: np.ndarray       = self._bess_discharge_kwh              # same metric, renamed
        # Red
        self._bess_grid_import_ev: np.ndarray   = bess_src["grid_import_ev_kwh"].to_numpy(dtype=np.float64)
        self._bess_grid_import_mall: np.ndarray = bess_src["grid_import_mall_kwh"].to_numpy(dtype=np.float64)
        self._grid_import_ref: np.ndarray       = np.nan_to_num(bess_src["grid_import_kwh"].to_numpy(dtype=np.float64), nan=0.0)
        self._bess_grid_export: np.ndarray      = bess_src["grid_export_kwh"].to_numpy(dtype=np.float64)
        # SOC
        self._bess_soc_ref: np.ndarray          = bess_src["soc_percent"].to_numpy(dtype=np.float64) / 100.0
        self._bess_soc_kwh: np.ndarray          = bess_src["soc_kwh"].to_numpy(dtype=np.float64)
        # CO₂ y economía — co2_avoided_indirect_kg fue renombrado a co2_avoided_kg
        self._bess_co2_avoided: np.ndarray      = bess_src["co2_avoided_kg"].to_numpy(dtype=np.float64)
        self._bess_cost_savings: np.ndarray     = bess_src["cost_savings_hp_soles"].to_numpy(dtype=np.float64)
        # Post-BESS — computed from available data (not in CSV schema)
        self._bess_ev_after: np.ndarray         = np.maximum(0.0, bess_src["ev_kwh"].to_numpy(dtype=np.float64) - self._bess_to_ev)
        self._bess_mall_after: np.ndarray       = np.maximum(0.0, bess_src["mall_kwh"].to_numpy(dtype=np.float64) - self._bess_to_mall)
        self._bess_load_after: np.ndarray       = self._bess_ev_after + self._bess_mall_after

        # ── Estadísticas acumuladas EV (derivadas de datos horarios) ─────────
        # Calculadas a partir de los arrays cargados de ev_charger_motos/mototaxis.csv
        # Los acumulados diario/mensual/anual se derivan de los horarios (no se guardan en CSV)
        self._chr_costo_soles: np.ndarray    = np.zeros(self._n, dtype=np.float64)  # computed in step()
        self._chr_co2_acum_diario: np.ndarray = np.zeros(self._n, dtype=np.float64)  # acumulado en step()
        self._chr_co2_por_vehiculo: np.ndarray = np.zeros(self._n, dtype=np.float64)
        self._chr_co2_acum_anual: np.ndarray = np.cumsum(self._chr_co2_directo)     # acumulado anual
        self._chr_ev_demand_kwh: np.ndarray  = self._chr_ev_total_kwh
        self._chr_is_punta: np.ndarray       = self._mall_is_punta                  # misma señal HP/HFP
        self._chr_tarifa: np.ndarray         = self._mall_tarifa                    # misma tarifa OSINERGMIN
        self._chr_co2_grid_kwh: np.ndarray   = np.zeros(self._n, dtype=np.float64)

        # Acumulados diario (reset cada 24h), mensual y anual — derivados de horarios
        _daily_motos   = self._chr_motos_hora.reshape(365, 24).cumsum(axis=1)
        _daily_moto    = np.hstack([_daily_motos[:, h] for h in range(24)]).reshape(self._n)
        self._chr_motos_diario: np.ndarray   = self._chr_motos_hora.reshape(365, 24).cumsum(axis=1).reshape(self._n)
        self._chr_mototaxis_diario: np.ndarray = self._chr_mototaxis_hora.reshape(365, 24).cumsum(axis=1).reshape(self._n)
        self._chr_total_diario: np.ndarray   = self._chr_motos_diario + self._chr_mototaxis_diario
        self._chr_motos_anual: np.ndarray    = np.full(self._n, self._chr_motos_hora.sum(), dtype=np.float64)
        self._chr_mototaxis_anual: np.ndarray = np.full(self._n, self._chr_mototaxis_hora.sum(), dtype=np.float64)
        self._chr_total_anual: np.ndarray    = self._chr_motos_anual + self._chr_mototaxis_anual
        # Mensual: acumulado por mes (simplificado con cumsum anual)
        self._chr_motos_mensual: np.ndarray  = np.cumsum(self._chr_motos_hora)
        self._chr_mototaxis_mensual: np.ndarray = np.cumsum(self._chr_mototaxis_hora)
        self._chr_total_mensual: np.ndarray  = self._chr_motos_mensual + self._chr_mototaxis_mensual

        # ── Sockets 2D: representación agregada (no hay datos per-socket en CL v2) ─
        # Los charger CSVs tienen datos agregados por tipo de flota.
        # Los arrays 2D se aproximan distribuyendo la demanda entre los sockets activos.
        _N_SOCKETS = 38
        _N_MOTOS   = 30   # socket_000 … socket_029
        _N_MOTOT   = 8    # socket_030 … socket_037
        _motos_act  = motos_df["active_sockets"].to_numpy(dtype=np.float32)
        _motot_act  = mototaxis_df["active_sockets"].to_numpy(dtype=np.float32)
        _motos_pw   = np.zeros((self._n, _N_MOTOS), dtype=np.float32)
        _motot_pw   = np.zeros((self._n, _N_MOTOT), dtype=np.float32)
        # Potencia por socket activo (distribución uniforme)
        _motos_pw_per = np.where(_motos_act > 0, self._ev_motos_demand.astype(np.float32) / np.maximum(_motos_act, 1), 0.0)
        _motot_pw_per = np.where(_motot_act > 0, self._ev_mototaxis_demand.astype(np.float32) / np.maximum(_motot_act, 1), 0.0)
        for i in range(_N_MOTOS):
            _motos_pw[:, i] = np.where(i < _motos_act, _motos_pw_per, 0.0)
        for i in range(_N_MOTOT):
            _motot_pw[:, i] = np.where(i < _motot_act, _motot_pw_per, 0.0)

        self._skt_charging_power: np.ndarray = np.hstack([_motos_pw, _motot_pw])   # (8760, 38)
        self._skt_charger_power: np.ndarray  = np.full((self._n, _N_SOCKETS), 7.4, dtype=np.float32)
        self._skt_battery_kwh: np.ndarray    = np.hstack([
            np.full((self._n, _N_MOTOS), 4.6, dtype=np.float32),
            np.full((self._n, _N_MOTOT), 7.4, dtype=np.float32),
        ])
        # SOC: motos cargándose van de 0.20 → 0.80 (EV_SOC_MIN → EV_SOC_MAX)
        self._skt_soc_arrival: np.ndarray  = np.full((self._n, _N_SOCKETS), 0.20, dtype=np.float32)
        self._skt_soc_target: np.ndarray   = np.full((self._n, _N_SOCKETS), 0.80, dtype=np.float32)
        _active_combined = np.hstack([
            np.column_stack([np.where(i < _motos_act, 1.0, 0.0).astype(np.float32) for i in range(_N_MOTOS)]),
            np.column_stack([np.where(i < _motot_act, 1.0, 0.0).astype(np.float32) for i in range(_N_MOTOT)]),
        ])
        self._skt_active: np.ndarray       = _active_combined
        self._skt_soc_current: np.ndarray  = np.where(
            _active_combined > 0, 0.50, 0.20
        ).astype(np.float32)   # aproximación: SOC medio durante carga

        # Validar longitudes (todos deben ser 8760)
        for _name, _arr in [
            ("mall_kw",         self._mall_kw),
            ("bess_soc_ref",    self._bess_soc_ref),
            ("grid_import_ref", self._grid_import_ref),
            ("chr_motos_hora",  self._chr_motos_hora),
        ]:
            if len(_arr) != self._n:
                raise ValueError(
                    f"Dataset CityLearn v2 '{_name}' tiene {len(_arr)} filas, "
                    f"esperado {self._n}. Ejecuta: python -m src.citylearnv2.schema_builder"
                )

        logger.info(
            "CityLearn v2 datasets cargados:\n"
            "  solar  : %.1f MWh/año | GHI_max=%.0f W/m²\n"
            "  mall   : %.1f MWh/año | costo=%.0f soles/año\n"
            "  BESS   : SOC_ref_avg=%.0f%% | grid_import=%.1f MWh/año\n"
            "  EV motos: %.0f kWh/año | EV mototaxis: %.0f kWh/año | CO₂_dir=%.0f kg/año",
            self._solar_kw.sum() / 1000,
            self._solar_ghi.max(),
            self._mall_kw.sum() / 1000,
            self._mall_cost_soles.sum(),
            self._bess_soc_ref.mean() * 100,
            self._grid_import_ref.sum() / 1000,
            self._ev_motos_demand.sum(),
            self._ev_mototaxis_demand.sum(),
            self._chr_co2_directo.sum(),
        )

        # ── Estado interno ────────────────────────────────────────────────
        self._t: int = 0                      # paso actual (0-8759)
        self._ev_motos_debt: float = 0.0      # kWh de motos pendientes en el día
        self._ev_mototaxis_debt: float = 0.0
        self._prev_grid_import: float = 0.0
        self._prev_bess_soc: float = 0.5      # SOC anterior (fracción) para delta real        # ── Redefinir espacios ────────────────────────────────────────────
        # Acción base CityLearn: Box([-1], [+1], shape=(1,)) → extendemos a 3D
        self.action_space = spaces.Box(
            low=np.array([-1.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

        # Observación base CityLearn + 5 dimensiones EV
        base_obs_space = self.env.observation_space
        # CityLearn con central_agent=True expone observation_space como lista
        if isinstance(base_obs_space, list):
            base_low = base_obs_space[0].low
            base_high = base_obs_space[0].high
        else:
            base_low = base_obs_space.low
            base_high = base_obs_space.high

        # ── Pre-calcular normalización para obs base CityLearn ────────────────
        # Las obs CityLearn tienen rangos físicos muy distintos (p.ej. net_kw
        # va de -3287 a +3054 kW). Normalizar a [-1, 1] acelera la convergencia
        # del NN SAC/PPO/A2C que no tiene normalización interna (MlpPolicy).
        self._obs_dim_base: int = int(base_low.shape[0])  # ← debe ir ANTES de obs_space
        self._base_obs_low: np.ndarray = base_low.astype(np.float32)
        self._base_obs_high: np.ndarray = base_high.astype(np.float32)
        _range = (self._base_obs_high - self._base_obs_low).astype(np.float32)
        # Dims constantes (high==low, ej. carbon_intensity=0.4521) → rango=1 para evitar /0
        self._base_obs_range: np.ndarray = np.where(_range > 1e-8, _range, 1.0).astype(np.float32)
        self._base_obs_const_mask: np.ndarray = (_range <= 1e-8)  # True donde la dim es constante

        # ev_obs: 5 dims EV + 2 dims tarifa OSINERGMIN (tarifa_norm, is_hora_punta)
        # [0-3] motos_norm, mototaxis_norm, motos_debt, mototaxis_debt ∈ [0, 1]
        # [4]   hour_sin ∈ [-1, 1]
        # [5]   tarifa_norm ∈ [0, 1]  — (tarifa_total - HFP) / (HP - HFP)
        # [6]   is_hora_punta ∈ {0, 1} — señal binaria explícita de período tarifario
        ev_low  = np.array([0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0], dtype=np.float32)
        ev_high = np.array([1.0, 1.0, 1.0, 1.0,  1.0, 1.0, 1.0], dtype=np.float32)

        # Obs space normalizado: base en [-1, 1]; dims extra en sus rangos propios
        self.observation_space = spaces.Box(
            low=np.concatenate([
                np.full(self._obs_dim_base, -1.0, dtype=np.float32),
                ev_low,
            ]),
            high=np.concatenate([
                np.full(self._obs_dim_base, 1.0, dtype=np.float32),
                ev_high,
            ]),
            dtype=np.float32,
        )

        # Rango tarifario para normalización (HP - HFP)
        self._tarifa_range: float = float(TARIFA_ENERGIA_HP_SOLES - TARIFA_ENERGIA_HFP_SOLES)  # 0.45-0.28=0.17

        logger.info(
            "IquitosEVChargingWrapper listo: obs_dim=%d (base=%d + ev=5 + tarifa=2), action_dim=3",
            self._obs_dim_base + 7,
            self._obs_dim_base,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sample_stochastic_fleet_episode(
        self,
        *,
        base_counts: np.ndarray,
        battery_kwh: float,
        max_sockets: int,
        dwell_hours: tuple[float, float, float],
        rng: np.random.Generator,
    ) -> dict[str, np.ndarray]:
        """Genera un perfil EV anual estocástico agregado a resolución horaria.

        Cada episodio remuestrea:
        - número de vehículos por hora a partir del perfil OE2;
        - hora efectiva de llegada con jitter horario;
        - SOC de llegada por vehículo;
        - tiempo disponible de permanencia/carga;
        - energía horaria requerida, limitada por tomas Modo 3 simultáneas.
        """
        demand = np.zeros(self._n, dtype=np.float64)
        arrivals = np.zeros(self._n, dtype=np.float64)
        active = np.zeros(self._n, dtype=np.float64)
        arrival_soc_sum = np.zeros(self._n, dtype=np.float64)
        active_soc_sum = np.zeros(self._n, dtype=np.float64)
        charge_time_sum = np.zeros(self._n, dtype=np.float64)
        dwell_sum = np.zeros(self._n, dtype=np.float64)

        offsets = np.array(EV_STOCH_ARRIVAL_OFFSETS, dtype=np.int32)
        offset_probs = np.array(EV_STOCH_ARRIVAL_PROBS, dtype=np.float64)
        daily_sigma = EV_STOCH_DAILY_SIGMA
        daily_mu = -0.5 * daily_sigma * daily_sigma

        for day in range(365):
            day_scale = float(rng.lognormal(mean=daily_mu, sigma=daily_sigma))
            day_start = day * 24
            for h in range(24):
                base_idx = day_start + h
                lam = max(float(base_counts[base_idx]) * day_scale, 0.0)
                if lam <= 1e-9:
                    continue

                n_ev = int(rng.poisson(lam))
                if n_ev <= 0:
                    continue

                arrival_hours = np.clip(
                    h + rng.choice(offsets, size=n_ev, p=offset_probs),
                    0,
                    23,
                )
                soc_arr = rng.triangular(
                    EV_SOC_MIN,
                    0.5 * (EV_SOC_MIN + EV_SOC_ARRIVAL_MAX),
                    EV_SOC_ARRIVAL_MAX,
                    size=n_ev,
                )
                dwell = rng.triangular(*dwell_hours, size=n_ev)
                energy_required = np.maximum(EV_SOC_MAX - soc_arr, 0.0) * battery_kwh / EV_CHARGER_EFF
                charge_time = energy_required / max(EV_CHARGER_KW, 1e-6)
                feasible_energy = np.minimum(energy_required, EV_CHARGER_KW * dwell)

                for arr_h, soc, stay_h, req_time_h, energy in zip(
                    arrival_hours, soc_arr, dwell, charge_time, feasible_energy
                ):
                    arr_idx = day_start + int(arr_h)
                    arrivals[arr_idx] += 1.0
                    arrival_soc_sum[arr_idx] += float(soc)
                    charge_time_sum[arr_idx] += float(req_time_h)
                    dwell_sum[arr_idx] += float(stay_h)

                    n_slots = max(1, int(math.ceil(float(stay_h))))
                    remaining = float(energy)
                    for slot_offset in range(n_slots):
                        slot_h = min(int(arr_h) + slot_offset, 23)
                        slot_idx = day_start + slot_h
                        slots_left = max(n_slots - slot_offset, 1)
                        # Modo 3: cada toma entrega hasta 7.4 kWh en un timestep horario.
                        slot_energy = min(EV_CHARGER_KW, remaining / slots_left)
                        if slot_energy <= 0.0:
                            break
                        demand[slot_idx] += slot_energy
                        active[slot_idx] += 1.0
                        active_soc_sum[slot_idx] += float(soc)
                        remaining -= slot_energy

        arrival_soc = np.divide(
            arrival_soc_sum,
            arrivals,
            out=np.full(self._n, EV_SOC_MIN, dtype=np.float64),
            where=arrivals > 0,
        )
        active_soc = np.divide(
            active_soc_sum,
            active,
            out=np.full(self._n, EV_SOC_MIN, dtype=np.float64),
            where=active > 0,
        )
        charge_time_h = np.divide(
            charge_time_sum,
            arrivals,
            out=np.zeros(self._n, dtype=np.float64),
            where=arrivals > 0,
        )
        dwell_h = np.divide(
            dwell_sum,
            arrivals,
            out=np.zeros(self._n, dtype=np.float64),
            where=arrivals > 0,
        )

        # Las tomas Modo 3 operan simultáneamente hasta el límite físico del patio.
        active_sockets = np.minimum(active, float(max_sockets))
        max_hourly_power = float(max_sockets) * EV_CHARGER_KW
        demand = np.minimum(demand, max_hourly_power)

        return {
            "demand": demand,
            "arrivals": arrivals,
            "active_sockets": active_sockets,
            "arrival_soc": arrival_soc,
            "active_soc": active_soc,
            "charge_time_h": charge_time_h,
            "dwell_h": dwell_h,
        }

    def _refresh_ev_derived_arrays(self) -> None:
        """Actualiza métricas dependientes del perfil EV estocástico del episodio."""
        self._co2_ref_motos_h = self._ev_motos_demand * CO2_FACTOR_MOTO
        self._co2_ref_mototaxis_h = self._ev_mototaxis_demand * CO2_FACTOR_MOTOTAXI
        self._co2_ref_direct_h = self._co2_ref_motos_h + self._co2_ref_mototaxis_h
        self._co2_motos = self._co2_ref_motos_h
        self._co2_mototaxis = self._co2_ref_mototaxis_h

        self._chr_total_hora = self._chr_motos_hora + self._chr_mototaxis_hora
        self._chr_ev_total_kwh = self._ev_motos_demand + self._ev_mototaxis_demand
        self._chr_co2_directo = self._co2_ref_direct_h
        self._chr_co2_neto_hora = self._chr_co2_directo
        self._chr_ev_demand_kwh = self._chr_ev_total_kwh
        self._chr_co2_acum_anual = np.cumsum(self._chr_co2_directo)
        self._chr_co2_acum_diario = self._chr_co2_directo.reshape(365, 24).cumsum(axis=1).reshape(self._n)
        self._chr_co2_por_vehiculo = np.divide(
            self._chr_co2_directo,
            self._chr_total_hora,
            out=np.zeros(self._n, dtype=np.float64),
            where=self._chr_total_hora > 0,
        )
        self._chr_co2_grid_kwh = self._chr_ev_total_kwh * self._co2_factor
        self._chr_costo_soles = self._chr_ev_total_kwh * self._mall_tarifa

        self._chr_motos_state = np.where(self._chr_motos_active_sockets > 0, 1, 3).astype(np.int32)
        self._chr_mototaxis_state = np.where(self._chr_mototaxis_active_sockets > 0, 1, 3).astype(np.int32)
        self._chr_motos_diario = self._chr_motos_hora.reshape(365, 24).cumsum(axis=1).reshape(self._n)
        self._chr_mototaxis_diario = self._chr_mototaxis_hora.reshape(365, 24).cumsum(axis=1).reshape(self._n)
        self._chr_total_diario = self._chr_motos_diario + self._chr_mototaxis_diario
        self._chr_motos_anual = np.full(self._n, self._chr_motos_hora.sum(), dtype=np.float64)
        self._chr_mototaxis_anual = np.full(self._n, self._chr_mototaxis_hora.sum(), dtype=np.float64)
        self._chr_total_anual = self._chr_motos_anual + self._chr_mototaxis_anual
        self._chr_motos_mensual = np.cumsum(self._chr_motos_hora)
        self._chr_mototaxis_mensual = np.cumsum(self._chr_mototaxis_hora)
        self._chr_total_mensual = self._chr_motos_mensual + self._chr_mototaxis_mensual

        self._daily_motos_max = float(max(self._ev_motos_demand.reshape(365, 24).sum(axis=1).max(), 1.0))
        self._daily_mototaxis_max = float(max(self._ev_mototaxis_demand.reshape(365, 24).sum(axis=1).max(), 1.0))

    def _refresh_socket_arrays(self) -> None:
        """Reconstruye el estado agregado de las 38 tomas Modo 3 simultáneas."""
        n_motos = 30
        n_mototaxis = 8
        n_sockets = n_motos + n_mototaxis

        motos_act = np.minimum(self._chr_motos_active_sockets, n_motos).astype(np.float32)
        motot_act = np.minimum(self._chr_mototaxis_active_sockets, n_mototaxis).astype(np.float32)

        motos_pw = np.zeros((self._n, n_motos), dtype=np.float32)
        motot_pw = np.zeros((self._n, n_mototaxis), dtype=np.float32)
        motos_pw_per = np.where(motos_act > 0, self._ev_motos_demand.astype(np.float32) / np.maximum(motos_act, 1.0), 0.0)
        motot_pw_per = np.where(motot_act > 0, self._ev_mototaxis_demand.astype(np.float32) / np.maximum(motot_act, 1.0), 0.0)
        motos_pw_per = np.minimum(motos_pw_per, EV_CHARGER_KW).astype(np.float32)
        motot_pw_per = np.minimum(motot_pw_per, EV_CHARGER_KW).astype(np.float32)

        for i in range(n_motos):
            motos_pw[:, i] = np.where(i < motos_act, motos_pw_per, 0.0)
        for i in range(n_mototaxis):
            motot_pw[:, i] = np.where(i < motot_act, motot_pw_per, 0.0)

        motos_active = np.column_stack([
            np.where(i < motos_act, 1.0, 0.0).astype(np.float32) for i in range(n_motos)
        ])
        motot_active = np.column_stack([
            np.where(i < motot_act, 1.0, 0.0).astype(np.float32) for i in range(n_mototaxis)
        ])
        self._skt_active = np.hstack([motos_active, motot_active]).astype(np.float32)
        self._skt_charging_power = np.hstack([motos_pw, motot_pw]).astype(np.float32)
        self._skt_charger_power = np.full((self._n, n_sockets), EV_CHARGER_KW, dtype=np.float32)
        self._skt_battery_kwh = np.hstack([
            np.full((self._n, n_motos), EV_MOTO_BAT_KWH, dtype=np.float32),
            np.full((self._n, n_mototaxis), EV_MOTOTAXI_BAT_KWH, dtype=np.float32),
        ])

        moto_soc = self._ev_motos_active_soc.astype(np.float32)
        motot_soc = self._ev_mototaxis_active_soc.astype(np.float32)
        self._skt_soc_arrival = np.hstack([
            np.tile(moto_soc[:, None], (1, n_motos)),
            np.tile(motot_soc[:, None], (1, n_mototaxis)),
        ]).astype(np.float32)
        self._skt_soc_target = np.full((self._n, n_sockets), EV_SOC_MAX, dtype=np.float32)
        self._skt_soc_current = np.where(
            self._skt_active > 0,
            0.5 * (self._skt_soc_arrival + self._skt_soc_target),
            EV_SOC_MIN,
        ).astype(np.float32)

    def _get_real_bess_soc(self) -> float:
        """Lee el SOC real del battery de CityLearn, corrigiendo el off-by-one.

        CityLearn escribe el SOC post-acción en ``bat.soc[time_step - 1]``
        (índice del paso ANTERIOR), pero la observación ``electrical_storage_soc``
        lee ``bat.soc[time_step]`` (el siguiente slot pre-allocado a 0).
        Esto causa que obs[9] = 0.0 para TODOS los pasos > 0, aunque la batería
        esté correctamente cargando/descargando internamente.

        Este método lee el índice correcto (``time_step - 1``) para obtener el
        SOC real y fraccionarlo entre 0 y 1.
        """
        try:
            bat = self.env.buildings[0].electrical_storage
            t = bat.time_step
            # CityLearn escribe el SOC en soc[t-1] después de ejecutar el step t
            real_soc = float(bat.soc[t - 1]) if t > 0 else float(bat.soc[0])
            return float(np.clip(real_soc, 0.0, 1.0))
        except (AttributeError, IndexError):
            return 0.5  # fallback seguro

    def _extract_base_obs(self, citylearn_obs: Any) -> np.ndarray:
        """Convierte la observación de CityLearn al formato flat numpy."""
        if isinstance(citylearn_obs, list):
            obs = citylearn_obs[0]
        else:
            obs = citylearn_obs
        if isinstance(obs, dict):
            return np.array(list(obs.values()), dtype=np.float32)
        return np.asarray(obs, dtype=np.float32).flatten()

    def _build_obs(self, base_obs_raw: Any) -> np.ndarray:
        """Construye obs extendida y normalizada (base[-1,1] + 5 EV dims)."""
        base = self._extract_base_obs(base_obs_raw)

        # CityLearn off-by-one bug: obs[9] = electrical_storage_soc siempre = 0
        # después del primer paso. Inyectar el SOC real antes de normalizar.
        if len(base) > 9:
            base = base.copy()
            base[9] = self._get_real_bess_soc()

        # Normalizar obs base CityLearn a [-1, 1] usando rangos físicos conocidos.
        # Las dims constantes (ej. carbon_intensity) se mapean a 0.0.
        base_norm = 2.0 * (base - self._base_obs_low) / self._base_obs_range - 1.0
        base_norm = np.where(self._base_obs_const_mask, 0.0, base_norm).astype(np.float32)
        base_norm = np.clip(base_norm, -1.0, 1.0)  # clamp ante valores fuera de rango

        hour = int(self._t % 24)
        day_idx = self._t // 24

        # Demanda EV normalizada para este paso
        motos_dem_norm = np.clip(
            self._ev_motos_demand[self._t] / max(EV_MOTOS_MAX_KW, 1.0), 0.0, 1.0
        )
        mototaxis_dem_norm = np.clip(
            self._ev_mototaxis_demand[self._t] / max(EV_MOTOTAXIS_MAX_KW, 1.0), 0.0, 1.0
        )

        # Deuda diaria normalizada
        motos_debt_norm = np.clip(self._ev_motos_debt / self._daily_motos_max, 0.0, 1.0)
        mototaxis_debt_norm = np.clip(self._ev_mototaxis_debt / self._daily_mototaxis_max, 0.0, 1.0)

        # Señal circular de hora (urgencia de fin de día)
        hour_sin = float(np.sin(2 * np.pi * hour / 24))

        # Señal tarifaria OSINERGMIN desde tariffs_osinergmin.csv
        t_idx = min(self._t, len(self._tarifa_total) - 1)
        tarifa_t      = float(self._tarifa_total[t_idx])
        tarifa_norm   = float(np.clip(
            (tarifa_t - TARIFA_ENERGIA_HFP_SOLES) / max(self._tarifa_range, 1e-6),
            0.0, 1.0,
        ))  # 0.0 = HFP barato, 1.0 = HP caro
        is_punta_t = float(self._mall_is_punta[min(self._t, len(self._mall_is_punta) - 1)])

        ev_obs = np.array(
            [motos_dem_norm, mototaxis_dem_norm, motos_debt_norm, mototaxis_debt_norm,
             hour_sin, tarifa_norm, is_punta_t],
            dtype=np.float32,
        )
        return np.concatenate([base_norm, ev_obs])

    def _dispatch_energy_step(
        self,
        solar_kw: float,
        bess_soc_frac: float,
        bess_action: float,
        ev_demand_kw: float,
        mall_kw: float,
    ) -> dict[str, float]:
        """Despacho horario por prioridad — espejo de simulate_bess_operation() en bess.py v5.3.

        Cadena de prioridad OE2:
          1. PV → EV       (prioridad máxima: carga solar directa a parque eléctrico)
          2. PV → BESS     (almacenar excedente solar si agente ordena cargar)
          3. PV → Mall     (cobertura solar al mall con PV remanente)
          4. Export        (excedente neto a red aislada Iquitos)
          5. BESS → EV     (descarga para cubrir déficit EV primero)
          5. BESS → Mall   (descarga para cubrir déficit mall segundo)
          6. Grid import   (importación residual de red diesel Iquitos)

        Parameters
        ----------
        solar_kw      : generación PV en esta hora (kW)
        bess_soc_frac : fracción SOC actual del BESS [0, 1]
        bess_action   : acción del agente [-1=descarga máx, +1=carga máx]
        ev_demand_kw  : kW totales de EVs a cargar (motos + mototaxis)
        mall_kw       : demanda del mall (kW)

        Returns
        -------
        dict con claves:
            pv_to_ev_kwh, pv_to_bess_kwh, pv_to_mall_kwh,
            grid_export_kwh, bess_to_ev_kwh, bess_to_mall_kwh,
            grid_to_ev_kwh, grid_to_mall_kwh, grid_import_kwh
        """
        eff = math.sqrt(BESS_EFF_ROUNDTRIP)  # ≈ 0.9747 (cada pierna charge/discharge)

        remaining_pv = solar_kw

        # ── 1. PV → EV ───────────────────────────────────────────────────────
        pv_to_ev = min(remaining_pv, ev_demand_kw)
        remaining_pv -= pv_to_ev
        ev_deficit = ev_demand_kw - pv_to_ev

        # ── 2. PV → BESS (cargar si agente ordena y hay capacidad disponible) ─
        pv_to_bess = 0.0
        if bess_action > 0.0 and remaining_pv > 0.0 and bess_soc_frac < BESS_SOC_MAX:
            max_charge_kw = min(
                BESS_MAX_KW * bess_action,                               # potencia fracción
                remaining_pv,                                            # PV disponible
                (BESS_SOC_MAX - bess_soc_frac) * BESS_CAPACITY_KWH,    # espacio libre (kWh)
            )
            pv_to_bess = max(max_charge_kw, 0.0)
            remaining_pv -= pv_to_bess

        # ── 2b. Grid → BESS (cuando agente ordena carga pero PV insuficiente) ──
        # CityLearn carga el BESS desde red cuando no hay solar suficiente.
        # CRÍTICO: sin este flujo, el reward underestima el grid_import nocturno.
        grid_to_bess = 0.0
        if bess_action > 0.0 and bess_soc_frac < BESS_SOC_MAX:
            requested_charge = BESS_MAX_KW * bess_action
            remaining_needed = max(requested_charge - pv_to_bess, 0.0)
            space_left = max(
                (BESS_SOC_MAX - bess_soc_frac) * BESS_CAPACITY_KWH - pv_to_bess,
                0.0,
            )
            grid_to_bess = min(remaining_needed, space_left)

        # ── 3. PV → Mall (con PV remanente tras EVs y BESS) ─────────────────
        pv_to_mall = min(remaining_pv, mall_kw)
        remaining_pv -= pv_to_mall
        mall_deficit = mall_kw - pv_to_mall

        # ── 4. Export sobrante ───────────────────────────────────────────────
        grid_export = max(remaining_pv, 0.0)

        # ── 5. BESS descarga → SOLO cuando el agente ordena descarga (bess_action < 0) ──
        # IMPORTANTE: NO auto-descargar por déficit EV/Mall. CityLearn sigue la acción
        # del agente exactamente: bess_action > 0 = carga, bess_action < 0 = descarga.
        # Auto-descarga aquí ≠ CityLearn → reward subestima grid_import real → agent
        # aprende que BESS ya cubre EV cuando en realidad importa de la red.
        bess_to_ev = 0.0
        bess_to_mall = 0.0
        if bess_soc_frac > BESS_SOC_MIN and bess_action < 0.0:
            # Potencia de descarga: sólo explícita (agente ordena descarga)
            max_discharge_kw = BESS_MAX_KW * (-bess_action)
            available_kwh = min(
                max_discharge_kw,
                (bess_soc_frac - BESS_SOC_MIN) * BESS_CAPACITY_KWH * eff,
            )
            bess_to_ev = min(available_kwh, ev_deficit)
            ev_deficit -= bess_to_ev
            bess_to_mall = min(available_kwh - bess_to_ev, mall_deficit)
            mall_deficit -= bess_to_mall

        # ── 6. Grid import residual (EV + Mall + BESS nocturno) ─────────────
        grid_to_ev = max(ev_deficit, 0.0)
        grid_to_mall = max(mall_deficit, 0.0)
        grid_import = grid_to_ev + grid_to_mall + grid_to_bess

        return {
            "pv_to_ev_kwh":    pv_to_ev,
            "pv_to_bess_kwh":  pv_to_bess,
            "pv_to_mall_kwh":  pv_to_mall,
            "grid_export_kwh": grid_export,
            "bess_to_ev_kwh":  bess_to_ev,
            "bess_to_mall_kwh": bess_to_mall,
            "grid_to_ev_kwh":  grid_to_ev,
            "grid_to_mall_kwh": grid_to_mall,
            "grid_to_bess_kwh": grid_to_bess,
            "grid_import_kwh": grid_import,
        }

    def _compute_reward(
        self,
        base_obs_raw: Any,
        ev_motos_actual: float,
        ev_mototaxis_actual: float,
        penalty_debt: float,
        grid_import_kw: float = 0.0,
        solar_autoconsumo_kw: float = -1.0,
        co2_factor: float = CO2_GRID_KG_PER_KWH,
        bess_action_raw: float = 0.0,
        solar_gen_kw: float = 0.0,
    ) -> float:
        """Calcula la recompensa multi-objetivo CO2_DUAL_FOCUS v7.2 BESS_DISPATCH_FOCUS + COST_AWARE.

        Componentes (pesos suman 1.0):
          r_direct_co2   0.20 — CO₂ directo evitado (moto/mototaxi vs gasolina)
          r_indirect_co2 0.30 — CO₂ indirecto por grid_import × factor horario
          r_ev_complete  0.35 — completar carga EV sin deuda operativa
          r_bess_solar   0.07 — BESS cargando con solar, no con diesel nocturno
          r_solar        0.04 — autoconsumo solar (evitar exportación)
          r_grid_stable  0.02 — penalizar rampas bruscas de importación
          r_cost         0.02 — costo tarifario OSINERGMIN HP/HFP

        Parameters
        ----------
        base_obs_raw : observaciones CityLearn internas
        ev_motos_actual : kWh cargados a motos en este paso
        ev_mototaxis_actual : kWh cargados a mototaxis en este paso
        penalty_debt : penalización adicional por deuda incumplida (fin día)
        grid_import_kw : importación de red calculada por _dispatch_energy_step()
        solar_autoconsumo_kw : kW solar usado localmente (no exportado); -1 = calcular desde obs
        """
        base_obs = self._extract_base_obs(base_obs_raw)
        # solar_gen: DIRECTAMENTE desde array OE2 cargado en __init__ (solar_generation.csv)
        # No usar obs CityLearn por índice — es frágil y puede no coincidir con OE2.
        solar_gen = float(self._solar_kw[self._t])

        # Importación de red (física, calculada en step() por _dispatch_energy_step)
        grid_import_real = grid_import_kw

        # ── r_direct_co2 — CO₂ directo evitado vs referencia per-cargador ────
        # Referencia = ICE equivalente de los vehículos realmente presentes × SoC llegada.
        # r = 1.0 cuando el agente carga toda la demanda; 0.0 cuando no carga nada.
        t = self._t
        co2_motos_saved = self._co2_motos[t] * (
            ev_motos_actual / max(self._ev_motos_demand[t], 0.001)
        ) if self._ev_motos_demand[t] > 0 else 0.0
        co2_mototaxis_saved = self._co2_mototaxis[t] * (
            ev_mototaxis_actual / max(self._ev_mototaxis_demand[t], 0.001)
        ) if self._ev_mototaxis_demand[t] > 0 else 0.0
        co2_direct_total = co2_motos_saved + co2_mototaxis_saved
        # Normalizar por referencia estocástica del episodio (no por constante fija)
        _co2_ref_t = max(float(self._co2_ref_direct_h[t]), 1e-6)
        r_direct_co2 = float(np.clip(co2_direct_total / _co2_ref_t, 0.0, 1.0))

        # ── r_indirect_co2 (peso 0.30) ────────────────────────────────────
        # CO₂ indirecto: importación de red × factor horario (diesel Iquitos)
        # Factor varía: HP(18-23h)=0.43-0.63 kg/kWh, HFP=0.39-0.43 kg/kWh (estacionalidad Loreto)
        _co2_indirect_kg = grid_import_real * co2_factor
        _max_co2_indirect = MAX_GRID_IMPORT_KW * float(self._co2_factor.max())  # peor caso anual
        r_indirect_co2 = -float(np.clip(_co2_indirect_kg / max(_max_co2_indirect, 1.0), 0.0, 1.0))

        # ── r_ev_complete (peso 0.35) ─────────────────────────────────────
        # Bonificar completar carga EV al día; penalizar deuda incumplida (fin día)
        hour = int(self._t % 24)
        day_start = (t // 24) * 24
        day_end = min(day_start + 24, self._n)
        daily_total = max(
            float(self._ev_motos_demand[day_start:day_end].sum()
                  + self._ev_mototaxis_demand[day_start:day_end].sum()),
            1.0,
        )
        debt_now = float(self._ev_motos_debt + self._ev_mototaxis_debt)
        debt_frac_now = penalty_debt if hour == 23 else float(np.clip(debt_now / daily_total, 0.0, 1.0))
        urgency = 0.0 if hour < 15 else (0.5 if hour < 18 else (1.0 if hour < 22 else 1.5))

        if hour == 23 and penalty_debt > 0.0:
            # Penalización fuerte al final del día por deuda no cumplida.
            r_ev_complete = -float(np.clip(0.5 + penalty_debt, 0.0, 1.0))
        else:
            # Bonus parcial por carga efectuada respecto a demanda esperada,
            # con presión creciente si se acumula deuda cerca del cierre.
            demand_hora = self._ev_motos_demand[t] + self._ev_mototaxis_demand[t]
            if demand_hora > 0.001:
                ev_total_actual = ev_motos_actual + ev_mototaxis_actual
                completion_frac = float(np.clip(ev_total_actual / demand_hora, 0.0, 1.0))
                r_ev_complete = completion_frac - 0.35 - urgency * debt_frac_now
            else:
                r_ev_complete = -0.25 * urgency * debt_frac_now
            if debt_frac_now > 0.10 and hour >= 18:
                r_ev_complete -= 0.50
            r_ev_complete = float(np.clip(r_ev_complete, -1.0, 1.0))

        # ── r_solar (peso 0.04) ───────────────────────────────────────────
        # Autoconsumo solar: penalizar si se exporta solar pudiendo usarse localmente
        # solar_autoconsumo_kw viene del dispatch (PV local = PV total - export)
        if solar_gen > 0.001:
            _solar_local = solar_autoconsumo_kw if solar_autoconsumo_kw >= 0.0 else solar_gen
            r_solar = float(np.clip(_solar_local / solar_gen, 0.0, 1.0) - 0.3)
        else:
            r_solar = 0.0

        # ── r_grid_stable (peso 0.05) ─────────────────────────────────────
        # Penalizar rampas bruscas de importación de red
        delta = abs(grid_import_real - self._prev_grid_import)
        r_grid_stable = -float(np.clip(delta / MAX_GRID_IMPORT_KW, 0.0, 1.0))
        self._prev_grid_import = grid_import_real

        # ── r_cost (peso 0.05) ────────────────────────────────────────────
        # Costo tarifario real del dataset OSINERGMIN (tarifa energía + AAPP):
        #   HP (18-23h): 0.45+0.0116=0.4616 S/./kWh | HFP: 0.28+0.0116=0.2916 S/./kWh
        t_idx = min(self._t, len(self._tarifa_total) - 1)
        tarifa_total_t = float(self._tarifa_total[t_idx])
        cost_step_soles = grid_import_real * tarifa_total_t
        r_cost = -float(np.clip(cost_step_soles / MAX_COST_PER_STEP_SOLES, 0.0, 1.0))

        # ── r_bess_solar (peso 0.07) — Regla operacional de flujo BESS ───
        # BESS debe cargarse con generación solar (6-18h) NO con diesel nocturno.
        # Flujo correcto: Solar → BESS (día) → BESS → EV (noche/pico).
        # bess_action_raw > 0 = cargando; < 0 = descargando.
        hour_t = int(self._t % 24)
        is_solar_hour = 6 <= hour_t < 18
        r_bess_solar: float
        if bess_action_raw > 0.05:   # BESS cargando (threshold mínimo para ignorar ruido)
            if is_solar_hour and solar_gen_kw >= _SOLAR_CHARGE_THRESHOLD_KW:  # noqa: F821
                # CORRECTO: carga BESS con solar disponible → bonus máximo
                solar_frac = float(np.clip(solar_gen_kw / max(BESS_MAX_KW, 1.0), 0.0, 1.0))
                r_bess_solar = +solar_frac   # ∈ [0, 1]
            elif not is_solar_hour:
                # INCORRECTO: carga BESS de noche con diesel → penalización
                r_bess_solar = -1.0
            else:
                # Solar insuficiente durante el día → penalización leve
                r_bess_solar = -0.3
        else:
            # BESS descargando o inactivo → neutral (no penalizar descarga)
            r_bess_solar = 0.0

        # ── Recompensa combinada ponderada v7.3 (suman 1.0) ─────────────
        reward = (
            _W_DIRECT_CO2  * r_direct_co2
            + _W_INDIRECT_CO2 * r_indirect_co2
            + _W_EV_COMPLETE  * r_ev_complete
            + _W_SOLAR        * r_solar
            + _W_GRID_STABLE  * r_grid_stable
            + _W_COST         * r_cost
            + _W_BESS_SOLAR   * r_bess_solar
        )
        return float(np.clip(reward, -1.0, 1.0))

    # ── Gymnasium API ─────────────────────────────────────────────────────────

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict | None = None,
    ) -> tuple[np.ndarray, dict]:
        """Reinicia el entorno y el estado EV interno."""
        self._t = 0
        self._ev_motos_debt = 0.0
        self._ev_mototaxis_debt = 0.0
        self._prev_grid_import = 0.0
        self._prev_bess_soc = -1.0  # -1 = no inicializado; se leerá del obs real en primer step

        # ── Modelo EV estocástico por episodio ────────────────────────────────
        # seed=None → episodio aleatorio; seed=k → evaluación reproducible.
        # La demanda ya no es fija: varían cantidad de EVs, llegada, SOC inicial,
        # tiempo disponible de carga y energía posible en tomas Modo 3 simultáneas.
        _ep_rng = np.random.default_rng(seed)
        _motos_ep = self._sample_stochastic_fleet_episode(
            base_counts=self._chr_motos_hora_base,
            battery_kwh=EV_MOTO_BAT_KWH,
            max_sockets=30,
            dwell_hours=EV_MOTO_DWELL_HOURS,
            rng=_ep_rng,
        )
        _mototaxis_ep = self._sample_stochastic_fleet_episode(
            base_counts=self._chr_mototaxis_hora_base,
            battery_kwh=EV_MOTOTAXI_BAT_KWH,
            max_sockets=8,
            dwell_hours=EV_MOTOTAXI_DWELL_HOURS,
            rng=_ep_rng,
        )

        self._ev_motos_demand = _motos_ep["demand"]
        self._ev_mototaxis_demand = _mototaxis_ep["demand"]
        self._chr_motos_hora = _motos_ep["arrivals"]
        self._chr_mototaxis_hora = _mototaxis_ep["arrivals"]
        self._chr_motos_active_sockets = _motos_ep["active_sockets"]
        self._chr_mototaxis_active_sockets = _mototaxis_ep["active_sockets"]
        self._ev_motos_arrival_soc = _motos_ep["arrival_soc"]
        self._ev_mototaxis_arrival_soc = _mototaxis_ep["arrival_soc"]
        self._ev_motos_active_soc = _motos_ep["active_soc"]
        self._ev_mototaxis_active_soc = _mototaxis_ep["active_soc"]
        self._ev_motos_charge_time_h = _motos_ep["charge_time_h"]
        self._ev_mototaxis_charge_time_h = _mototaxis_ep["charge_time_h"]
        self._ev_motos_dwell_h = _motos_ep["dwell_h"]
        self._ev_mototaxis_dwell_h = _mototaxis_ep["dwell_h"]
        self._refresh_ev_derived_arrays()
        self._refresh_socket_arrays()

        base_result = self.env.reset(seed=seed, options=options)
        # CityLearn puede devolver solo obs o (obs, info)
        if isinstance(base_result, tuple):
            base_obs, info = base_result[0], base_result[1] if len(base_result) > 1 else {}
        else:
            base_obs, info = base_result, {}

        # Inicializar _prev_bess_soc — en reset t=0, obs[9] SÍ es correcto (bat.soc[0]=initial_soc).
        # Usar _get_real_bess_soc() para consistencia total.
        self._prev_bess_soc = self._get_real_bess_soc()

        obs = self._build_obs(base_obs)
        return obs, info

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, SupportsFloat, bool, bool, dict]:
        """Ejecuta un paso de control con acción extendida [bess, motos_frac, mototaxis_frac].

        Parameters
        ----------
        action : np.ndarray, shape (3,)
            [0] bess_action       ∈ [-1, +1]  (-1 = descarga máx BESS, +1 = carga máx BESS)
            [1] ev_motos_frac     ∈ [ 0,  1]  (fracción de demanda de motos a cargar ahora)
            [2] ev_mototaxis_frac ∈ [ 0,  1]  (fracción de demanda de mototaxis a cargar ahora)

        Returns
        -------
        obs : np.ndarray, shape (obs_dim_base + 7,)
        reward : float
        terminated : bool
        truncated : bool
        info : dict  (ver claves CO₂ más abajo)

        Notes
        -----
        Sistema de 3 Fórmulas CO₂ — OE3 PVBESSCAR (Iquitos, Perú)
        ===========================================================
        Factores base:
            CO2_GRID         = 0.4521 kg CO₂/kWh  (red diesel aislada Iquitos, MINEM)
            CO2_FACTOR_MOTO  = 0.87   kg CO₂/kWh  (moto gasolina 125 cc, IPCC 2006)
            CO2_FACTOR_MOTOTAXI = 0.54 kg CO₂/kWh (mototaxi 150 cc, IPCC 2006)

        ─────────────────────────────────────────────────────────────────────────
        FÓRMULA 1 — BASELINE  (sin solar, sin BESS, sin agente RL)
        ─────────────────────────────────────────────────────────────────────────
        Escenario de referencia: red diesel cubre el 100 % de la demanda.

            baseline = [A] + [B] − [C]

            [A] CO₂_directa_combustion
                = motos_dem × 0.87 + mototaxis_dem × 0.54
                  Emisiones si el parque completo siguiera quemando gasolina.

            [B] CO₂_indirecta_red
                = (mall_kw + motos_dem + mototaxis_dem) × 0.4521
                  Red diesel suministra mall + carga EV (sin renovables ni BESS).

            [C] CO₂_reduccion_directa_elec
                = ev_motos_actual × 0.87 + ev_mototaxis_actual × 0.54
                  CO₂ evitado porque los EVs ya NO queman gasolina
                  (electrificación del parque ya implementada).

        ─────────────────────────────────────────────────────────────────────────
        FÓRMULA 2 — CONTROL INTELIGENTE  (solar 4,050 kWp + BESS 400 kW + agente RL)
        ─────────────────────────────────────────────────────────────────────────
        Emisión real bajo gestión inteligente:

            control = grid_import_residual × 0.4521
                Solo la importación de red que solar + BESS + agente NO cubrieron.

        Desglose de reducción por mecanismo (informativo, claves `co2_ctrl_reduc_*`):

            [D] Directa EVs  = ev_motos × 0.87 + ev_mototaxis × 0.54
                Parque eléctrico en carga → no quema combustible.

            [E] Indirecta solar (100 % generación PV acreditada, sin desperdicio):
                ├─ F6a → EVs    = solar_ev   × 0.4521  (solar directo a carga EV)
                ├─ F6b → Mall   = solar_mall × 0.4521  (solar directo a mall)
                ├─ F6c → BESS   = solar_bess × 0.4521  (solar almacenado en BESS)
                └─ F6d → Export = solar_exp  × 0.4521  (excedente a red aislada)
                Total E = solar_total × 0.4521  (F6a + F6b + F6c + F6d = 100 % PV)

            [F] Indirecta BESS = bess_discharge × 0.4521
                BESS libera energía solar diferida → corta pico de mall/EVs
                → desplaza importación de red diesel en hora de máxima demanda.

        ─────────────────────────────────────────────────────────────────────────
        FÓRMULA 3 — REDUCCIÓN NETA OE3  (métrica principal del proyecto)
        ─────────────────────────────────────────────────────────────────────────
            reduccion_directa   = [D]  = ev_motos × 0.87 + ev_mototaxis × 0.54
            reduccion_indirecta = max(0, baseline − control)
                (efecto neto combinado de solar + BESS + agente sobre la red)
            reduccion_total     = reduccion_directa + reduccion_indirecta

        Claves devueltas en `info`:
            Fórmulas principales:
                co2_total_baseline_kg        — F1 baseline
                co2_total_control_kg         — F2 control (grid residual)
                co2_reduccion_directa_kg     — F3 directa
                co2_reduccion_indirecta_kg   — F3 indirecta
                co2_total_sistema_evitado_kg — F3 reducción neta total
            Desglose solar/BESS (análisis):
                co2_ctrl_reduc_directa_kg    — [D]
                co2_ctrl_reduc_solar_ev_kg   — [E] F6a
                co2_ctrl_reduc_solar_mall_kg — [E] F6b
                co2_ctrl_reduc_solar_bess_kg — [E] F6c
                co2_ctrl_reduc_solar_exp_kg  — [E] F6d
                co2_ctrl_reduc_solar_total_kg — [E] 100 % PV
                co2_ctrl_reduc_bess_desc_kg  — [F]
            Balance energético:
                solar_generation_kwh, grid_import_kwh, grid_export_kwh,
                mall_demand_kwh, bess_discharge_kwh, bess_charge_kwh, bess_soc
        """
        action = np.asarray(action, dtype=np.float32).flatten()
        bess_action = float(np.clip(action[0], -1.0, 1.0))
        ev_motos_frac = float(np.clip(action[1], 0.0, 1.0))
        ev_mototaxis_frac = float(np.clip(action[2], 0.0, 1.0))

        t = self._t
        hour = t % 24
        # Factor CO₂ horario (todo el sistema: diesel Iquitos + ICE vehículos)
        # Cargado desde co2_emissions.csv: estacionalidad mensual Loreto + variación HP/HFP
        _co2_factor_t = float(self._co2_factor[min(t, len(self._co2_factor) - 1)])

        # ── Calcular despacho EV real ─────────────────────────────────────
        # Demanda estocástica de este paso (conteos, llegada, SOC y permanencia
        # remuestreados en reset()). Las tomas Modo 3 operan simultáneamente:
        # motos: 30×7.4 kW; mototaxis: 8×7.4 kW.
        motos_demand_t = float(self._ev_motos_demand[t])
        mototaxis_demand_t = float(self._ev_mototaxis_demand[t])

        # El agente controla la fracción a cargar AHORA.
        # RESTRICCIÓN FÍSICA: la carga real NO puede superar la demanda nominal
        # del paso (motos_demand_t / mototaxis_demand_t). Los EVs que llegaron
        # esta hora tienen una demanda finita; no se puede "recuperar" energía
        # de horas anteriores cargando de más ahora — esos vehículos ya se
        # fueron del parking y la generación (solar/BESS) ya fue contabilizada.
        # Superar el nominal requeriría energía de red (térmica → CO₂ indirecto).
        ev_motos_actual = min(
            motos_demand_t * ev_motos_frac,
            EV_MOTOS_MAX_KW,          # techo de potencia instalada (222 kW)
        )
        ev_mototaxis_actual = min(
            mototaxis_demand_t * ev_mototaxis_frac,
            EV_MOTOTAXIS_MAX_KW,      # techo de potencia instalada (59.2 kW)
        )

        # Actualizar deuda diaria (servicio perdido no recuperable intra-día)
        # La deuda acumula la energía NO entregada en cada paso; se usa como
        # señal de penalización al cierre del día (hora 23) y como observación.
        motos_not_charged = max(motos_demand_t - ev_motos_actual, 0.0)
        mototaxis_not_charged = max(mototaxis_demand_t - ev_mototaxis_actual, 0.0)
        self._ev_motos_debt += motos_not_charged
        self._ev_mototaxis_debt += mototaxis_not_charged

        # ── Forzar despacho pendiente al final del día (hora 23) ──────────
        penalty_debt_frac = 0.0
        if hour == 23:
            # Calcular la demanda diaria total para normalizar la penalización
            day_start = (t // 24) * 24
            day_end = min(day_start + 24, self._n)
            daily_motos = float(self._ev_motos_demand[day_start:day_end].sum())
            daily_mototaxis = float(self._ev_mototaxis_demand[day_start:day_end].sum())
            daily_total = max(daily_motos + daily_mototaxis, 1.0)
            debt_total = self._ev_motos_debt + self._ev_mototaxis_debt
            penalty_debt_frac = float(np.clip(debt_total / daily_total, 0.0, 1.0))
            # Resetear deuda al inicio del próximo día
            self._ev_motos_debt = 0.0
            self._ev_mototaxis_debt = 0.0

        # ── Llamar a CityLearn con acción BESS ────────────────────────────
        # CityLearn con central_agent=True espera List[List[float]] → [[bess_value]]
        bess_action_cl = [[bess_action]]

        base_result = self.env.step(bess_action_cl)
        # CityLearn puede devolver 4 o 5 elementos (gym antiguo o nuevo)
        if len(base_result) == 5:
            base_obs, _base_rew, terminated, truncated, info = base_result
        elif len(base_result) == 4:
            base_obs, _base_rew, terminated, info = base_result  # type: ignore[misc]
            truncated = False
        else:
            base_obs = base_result[0]
            _base_rew = 0.0
            terminated = False
            truncated = False
            info = {}

        # ── Extraer obs energéticas ANTES del reward (necesarias para dispatch) ─
        # NOTA: en lugar de extraer por índice frágil de obs CityLearn, usamos
        # directamente los arrays OE2 cargados en __init__ (solar_generation.csv
        # y mall_demand.csv). Esto garantiza que SIEMPRE usamos los datos reales
        # de OE2 sin depender de la indexación interna de CityLearn.
        _base_arr = self._extract_base_obs(base_obs).flatten()
        _solar_kw  = float(self._solar_kw[t])   # potencia_kw real OE2 (kW)
        _mall_kw   = float(self._mall_kw[t])     # mall_demand_kwh real OE2 (kWh/h)
        # net_electricity_consumption sí viene de CityLearn (balance interno)
        _net_kw    = float(_base_arr[10]) if len(_base_arr) > 10 else 0.0

        # ── SOC real: bypass del off-by-one bug de CityLearn ────────────────
        # obs[9] = electrical_storage_soc lee bat.soc[time_step] (slot futuro,
        # pre-allocado a 0). El SOC real post-acción está en bat.soc[time_step-1].
        _bess_soc = self._get_real_bess_soc()

        ev_total_kw = ev_motos_actual + ev_mototaxis_actual

        # ── Despacho energético por prioridad OE2/bess.py ──────────────────
        # Espejo de simulate_bess_operation(): PV→EV → PV→BESS → PV→Mall → Export
        #                                      → BESS→déficit EV → BESS→déficit Mall → Grid
        _dp = self._dispatch_energy_step(
            solar_kw=_solar_kw,
            bess_soc_frac=_bess_soc,
            bess_action=bess_action,
            ev_demand_kw=ev_total_kw,
            mall_kw=_mall_kw,
        )
        grid_import_kw    = _dp["grid_import_kwh"]
        grid_export_kw    = _dp["grid_export_kwh"]
        bess_discharge_kw = _dp["bess_to_ev_kwh"] + _dp["bess_to_mall_kwh"]
        bess_charge_kw    = _dp["pv_to_bess_kwh"]

        # ── Recompensa wrapper — usa grid_import físicamente correcto ──────
        reward = self._compute_reward(
            base_obs, ev_motos_actual, ev_mototaxis_actual, penalty_debt_frac,
            grid_import_kw=grid_import_kw,
            solar_autoconsumo_kw=_solar_kw - grid_export_kw,
            co2_factor=_co2_factor_t,
            bess_action_raw=float(bess_action),
            solar_gen_kw=float(_solar_kw),
        )

        # ── Construir observación extendida ───────────────────────────────
        self._t = min(self._t + 1, self._n - 1)
        obs = self._build_obs(base_obs)

        # ── F6: Fórmulas CO₂ — DEFINICIÓN ORIGINAL OE3 (separada del dispatch) ──
        # Las fórmulas CO₂ (F0/F1/F2/F3) mantienen su definición original OE3.
        # Son métricas de MEDICIÓN e investigación — independientes del dispatch.
        # El dispatch (_dp) controla SOLO el reward (señal de entrenamiento del agente).
        # NOTA: obs[10] (net_electricity_consumption) devuelve 0 siempre en CityLearn v2
        # (la energía de red se calcula internamente y no se expone via obs correctamente).
        # Usamos el dispatch model (físicamente correcto) para grid import/export.
        _co2_grid_export  = grid_export_kw                           # exportación neta (kWh dispatch)
        _co2_grid_import  = grid_import_kw                           # F2: importación real (mall+ev-solar-bess)
        # Métricas BESS físicas: usar salida del dispatch (SOC-constrained), no acción bruta.
        # max(-bess_action)*400 era ficticio (sobreestimaba ~5x la descarga real).
        _co2_bess_disc    = _dp["bess_to_ev_kwh"] + _dp["bess_to_mall_kwh"]   # descarga real (kWh)
        _co2_bess_chg     = _dp["pv_to_bess_kwh"] + _dp["grid_to_bess_kwh"]  # carga real (kWh)
        # F6: orden original OE3 — EV → Mall → BESS → export (no cambia)
        _f6a = min(_solar_kw, ev_total_kw)                           # Fase 1: solar → EVs
        _f6b = min(max(0.0, _solar_kw - _f6a), _mall_kw)            # Fase 2: solar → Mall
        _f6d = _co2_grid_export                                      # Fase 4: solar → export
        _f6c = max(0.0, _solar_kw - _f6a - _f6b - _f6d)             # Fase 3: solar → BESS

        # Factor CO₂ horario — Iquitos diesel: estacionalidad mensual + HP/HFP
        # HP(18-23h): factor_mes×1.35 | HFP: factor_mes×0.908  (0.43 lluv / 0.47 seca)
        co2_solar_f6_kg           = _solar_kw  * _co2_factor_t   # F6 total (CO₂ indirecto evitado por PV)
        co2_solar_ev_f6a_kg       = _f6a * _co2_factor_t         # F6a: solar → EV (directo)
        co2_solar_mall_f6b_kg     = _f6b * _co2_factor_t         # F6b: solar → Mall
        co2_solar_bess_f6c_kg     = _f6c * _co2_factor_t         # F6c: solar → BESS (diferido)
        co2_solar_export_f6d_kg   = _f6d * _co2_factor_t         # F6d: solar → export red

        # ── F7: BESS descarga → desplaza importación de red diesel (HP factor) ───
        co2_bess_discharge_f7_kg  = _co2_bess_disc * _co2_factor_t

        # [A] Directo combustión ICE
        co2_directo_combustion = (
            motos_demand_t    * CO2_FACTOR_MOTO         # 0.87 kg CO₂/kWh gasolina moto 125cc
            + mototaxis_demand_t * CO2_FACTOR_MOTOTAXI  # 0.54 kg CO₂/kWh gasolina mototaxi 150cc
        )

        # ── FÓRMULA 0 — SIN PROYECTO ────────────────────────────────────────────
        # Mall en red diesel + combustión ICE equivalente a la demanda EV
        # estocástica del episodio. Por tanto F0 también varía si cambian cantidad
        # de EVs, SOC de llegada y tiempo de carga/permanencia.
        co2_sinproyecto_mall_kg       = _mall_kw * _co2_factor_t
        co2_sinproyecto_combustion_kg = co2_directo_combustion
        co2_total_sinproyecto_kg      = co2_sinproyecto_mall_kg + co2_sinproyecto_combustion_kg

        # ── FÓRMULA 1 — BASELINE (sin solar, sin BESS, sin agente RL) ───────────
        # [B] Indirecto: red diesel Iquitos cubre mall + EV (sin solar ni BESS)
        co2_indirecto_red_base = (
            _mall_kw + motos_demand_t + mototaxis_demand_t
        ) * _co2_factor_t   # factor horario variable (0.39-0.63 kg CO₂/kWh según mes+periodo)
        # [C] Reducción directa: EVs ya electrificados no queman combustible
        co2_reduccion_directa_elec = (
            ev_motos_actual    * CO2_FACTOR_MOTO
            + ev_mototaxis_actual * CO2_FACTOR_MOTOTAXI
        )
        co2_total_baseline_kg = co2_directo_combustion + co2_indirecto_red_base - co2_reduccion_directa_elec

        # ── FÓRMULA 2 — CONTROL INTELIGENTE (solar+BESS+agente RL) ─────────────
        # Emisión residual: solo lo que solar+BESS+agente no pudieron cubrir
        co2_total_control_kg = _co2_grid_import * _co2_factor_t  # factor horario variable

        # ── [D] Reducción DIRECTA (EV eléctrico vs ICE gasolina) ────────────────
        co2_ctrl_reduc_directa_kg = (
            ev_motos_actual    * CO2_FACTOR_MOTO
            + ev_mototaxis_actual * CO2_FACTOR_MOTOTAXI
        )
        # ── [E] Reducción INDIRECTA — PV (100% generación acreditada) ───────────
        co2_ctrl_reduc_solar_ev_kg    = _f6a * _co2_factor_t   # solar → EV
        co2_ctrl_reduc_solar_mall_kg  = _f6b * _co2_factor_t   # solar → Mall
        co2_ctrl_reduc_solar_bess_kg  = _f6c * _co2_factor_t   # solar → BESS
        co2_ctrl_reduc_solar_exp_kg   = _f6d * _co2_factor_t   # solar → red aislada
        co2_ctrl_reduc_solar_total_kg = _solar_kw * _co2_factor_t  # total PV
        # ── [F] Reducción INDIRECTA — BESS descarga (energia solar diferida en HP) ─
        co2_ctrl_reduc_bess_desc_kg   = _co2_bess_disc * _co2_factor_t

        # ── FÓRMULA 3 — REDUCCIÓN NETA OE3 ─────────────────────────────────────
        co2_reduccion_directa_kg     = co2_ctrl_reduc_directa_kg
        co2_reduccion_indirecta_kg   = max(0.0, co2_total_baseline_kg - co2_total_control_kg)
        co2_total_sistema_evitado_kg = co2_reduccion_directa_kg + co2_reduccion_indirecta_kg

        # ── BESS real: calcular carga/descarga desde delta SOC (CityLearn truth) ─
        # Esto reemplaza los valores del dispatch model, que divergen por SOC sin estado.
        soc_delta = _bess_soc - self._prev_bess_soc
        _real_bess_disc = max(-soc_delta, 0.0) * BESS_CAPACITY_KWH  # kWh descargados (SOC bajó)
        _real_bess_chg  = max( soc_delta, 0.0) * BESS_CAPACITY_KWH  # kWh cargados (SOC subió)
        self._prev_bess_soc = _bess_soc

        # ── Info adicional para logging ───────────────────────────────────────────
        info.update({
            "ev_motos_actual_kwh": ev_motos_actual,
            "ev_mototaxis_actual_kwh": ev_mototaxis_actual,
            "ev_motos_demand_kwh":     motos_demand_t,
            "ev_mototaxis_demand_kwh": mototaxis_demand_t,
            "ev_motos_arrival_soc_avg": float(self._ev_motos_arrival_soc[t]),
            "ev_mototaxis_arrival_soc_avg": float(self._ev_mototaxis_arrival_soc[t]),
            "ev_motos_charge_time_h_avg": float(self._ev_motos_charge_time_h[t]),
            "ev_mototaxis_charge_time_h_avg": float(self._ev_mototaxis_charge_time_h[t]),
            "ev_motos_dwell_h_avg": float(self._ev_motos_dwell_h[t]),
            "ev_mototaxis_dwell_h_avg": float(self._ev_mototaxis_dwell_h[t]),
            "ev_motos_active_sockets": float(self._chr_motos_active_sockets[t]),
            "ev_mototaxis_active_sockets": float(self._chr_mototaxis_active_sockets[t]),
            "ev_charger_mode": "Modo 3",
            "ev_charger_kw_per_socket": EV_CHARGER_KW,
            "ev_motos_debt_kwh": self._ev_motos_debt,
            "ev_mototaxis_debt_kwh": self._ev_mototaxis_debt,
            "penalty_debt_frac": penalty_debt_frac,
            "bess_action": bess_action,
            "ev_motos_frac": ev_motos_frac,
            "ev_mototaxis_frac": ev_mototaxis_frac,
            "timestep": t,
            # ── Balance energético (valores originales OE3 — métricas multiagente) ──
            # IMPORTANTE: estas claves son las métricas que comparan SAC/PPO/A2C.
            # Deben usar la definición original (no el dispatch de reward).
            "solar_generation_kwh": _solar_kw,
            "grid_import_kwh":   _co2_grid_import,   # original: max(net_kw + ev_total, 0)
            "grid_export_kwh":   _co2_grid_export,    # original: max(-net_kw, 0)
            "mall_demand_kwh":   _mall_kw,
            "bess_discharge_kwh": _real_bess_disc,     # descarga real (kWh) desde SOC delta
            "bess_charge_kwh":   _real_bess_chg,      # carga real (kWh) desde SOC delta
            "bess_soc": _bess_soc,
            # ── Solar OE2: todas las columnas de solar_generation.csv ──────────
            "solar_energia_kwh":          float(self._solar_kwh[t]),
            "solar_irradiancia_ghi":      float(self._solar_ghi[t]),
            "solar_temperatura_c":        float(self._solar_temp[t]),
            "solar_viento_ms":            float(self._solar_viento[t]),
            "solar_co2_indirect_ref_kg":  float(self._solar_co2_indirect[t]),
            "solar_is_hora_punta":        int(self._solar_is_punta[t]),
            "solar_tarifa_soles":         float(self._solar_tarifa[t]),
            "solar_ahorro_soles":         float(self._solar_ahorro[t]),
            # ── Mall OE2: todas las columnas de mall_demand.csv ────────────────
            "mall_co2_indirect_kg":       float(self._mall_co2_indirect[t]),
            "mall_is_hora_punta":         int(self._mall_is_punta[t]),
            "mall_tarifa_soles_kwh":      float(self._mall_tarifa[t]),
            "mall_cost_soles":            float(self._mall_cost_soles[t]),
            # ── BESS OE2: todas las columnas de bess_timeseries.csv ────────────
            "bess_pv_kwh":               float(self._bess_pv_kwh[t]),
            "bess_ev_kwh":               float(self._bess_ev_kwh[t]),
            "bess_mall_kwh":             float(self._bess_mall_kwh[t]),
            "bess_load_kwh":             float(self._bess_load_kwh[t]),
            "bess_pv_to_ev_kwh":         float(self._bess_pv_to_ev[t]),
            "bess_pv_to_bess_kwh":       float(self._bess_pv_to_bess[t]),
            "bess_pv_to_mall_kwh":       float(self._bess_pv_to_mall[t]),
            "bess_pv_curtailed_kwh":     float(self._bess_pv_curtailed[t]),
            "bess_charge_ref_kwh":       float(self._bess_charge_kwh[t]),
            "bess_discharge_ref_kwh":    float(self._bess_discharge_kwh[t]),
            "bess_action_ref_kwh":       float(self._bess_action_kwh[t]),
            "bess_mode":                 int(self._bess_mode[t]),
            "bess_to_ev_kwh":            float(self._bess_to_ev[t]),
            "bess_to_mall_kwh":          float(self._bess_to_mall[t]),
            "bess_peak_shaving_kwh":     float(self._bess_peak_shaving[t]),
            "bess_total_discharge_kwh":  float(self._bess_total_disc[t]),
            "bess_grid_import_ev_kwh":   float(self._bess_grid_import_ev[t]),
            "bess_grid_import_mall_kwh": float(self._bess_grid_import_mall[t]),
            "bess_grid_import_ref_kwh":  float(self._grid_import_ref[t]),
            "bess_grid_export_ref_kwh":  float(self._bess_grid_export[t]),
            "bess_soc_ref_frac":         float(self._bess_soc_ref[t]),
            "bess_soc_kwh":              float(self._bess_soc_kwh[t]),
            "bess_co2_avoided_kg":       float(self._bess_co2_avoided[t]),
            "bess_cost_savings_soles":   float(self._bess_cost_savings[t]),
            "bess_ev_after_kwh":         float(self._bess_ev_after[t]),
            "bess_mall_after_kwh":       float(self._bess_mall_after[t]),
            "bess_load_after_kwh":       float(self._bess_load_after[t]),
            # ── Cargadores OE2: columnas resumen de chargers_timeseries.csv ────
            "chr_ev_total_kwh":          float(self._chr_ev_total_kwh[t]),
            "chr_costo_soles":           float(self._chr_costo_soles[t]),
            "chr_co2_directo_kg":        float(self._chr_co2_directo[t]),
            "chr_co2_acum_diario_kg":    float(self._chr_co2_acum_diario[t]),
            "chr_co2_por_vehiculo_kg":   float(self._chr_co2_por_vehiculo[t]),
            "chr_co2_acum_anual_kg":     float(self._chr_co2_acum_anual[t]),
            "chr_motos_hora":            float(self._chr_motos_hora[t]),
            "chr_mototaxis_hora":        float(self._chr_mototaxis_hora[t]),
            "chr_total_hora":            float(self._chr_total_hora[t]),
            "chr_motos_diario":          float(self._chr_motos_diario[t]),
            "chr_mototaxis_diario":      float(self._chr_mototaxis_diario[t]),
            "chr_total_diario":          float(self._chr_total_diario[t]),
            "chr_motos_mensual":         float(self._chr_motos_mensual[t]),
            "chr_mototaxis_mensual":     float(self._chr_mototaxis_mensual[t]),
            "chr_total_mensual":         float(self._chr_total_mensual[t]),
            "chr_motos_anual":           float(self._chr_motos_anual[t]),
            "chr_mototaxis_anual":       float(self._chr_mototaxis_anual[t]),
            "chr_total_anual":           float(self._chr_total_anual[t]),
            "chr_co2_grid_kwh":          float(self._chr_co2_grid_kwh[t]),
            "chr_co2_neto_hora_kg":      float(self._chr_co2_neto_hora[t]),
            "chr_ev_demand_kwh":         float(self._chr_ev_demand_kwh[t]),
            "chr_is_hora_punta":         int(self._chr_is_punta[t]),
            "chr_tarifa_soles":          float(self._chr_tarifa[t]),
            # Sockets 38: arrays numpy (38,) — acceso por índice socket
            "skt_charger_power_kw":      self._skt_charger_power[t],    # (38,)
            "skt_battery_kwh":           self._skt_battery_kwh[t],      # (38,)
            "skt_soc_current":           self._skt_soc_current[t],      # (38,)
            "skt_soc_arrival":           self._skt_soc_arrival[t],      # (38,)
            "skt_soc_target":            self._skt_soc_target[t],       # (38,)
            "skt_active":                self._skt_active[t],           # (38,)
            "skt_charging_power_kw":     self._skt_charging_power[t],   # (38,)
            # ── CO₂ F6: solar por fase (EV > Mall > BESS > export) ─────────────
            "co2_solar_f6_kg": co2_solar_f6_kg,
            "co2_solar_ev_f6a_kg": co2_solar_ev_f6a_kg,
            "co2_solar_mall_f6b_kg": co2_solar_mall_f6b_kg,
            "co2_solar_bess_f6c_kg": co2_solar_bess_f6c_kg,
            "co2_solar_export_f6d_kg": co2_solar_export_f6d_kg,
            # ── CO₂ F7: BESS descarga desplaza red ─────────────────────────────
            "co2_bess_discharge_f7_kg": co2_bess_discharge_f7_kg,
            # ── 3 Fórmulas OE3 ─────────────────────────────────────────────────
            "co2_total_baseline_kg": co2_total_baseline_kg,
            "co2_total_control_kg": co2_total_control_kg,
            "co2_reduccion_directa_kg": co2_reduccion_directa_kg,
            "co2_reduccion_indirecta_kg": co2_reduccion_indirecta_kg,
            "co2_total_sistema_evitado_kg": co2_total_sistema_evitado_kg,
            # ── Desglose control inteligente — reducción por mecanismo ──────────
            # [D] Directa: electrificación del parque de motos/mototaxis
            "co2_ctrl_reduc_directa_kg": co2_ctrl_reduc_directa_kg,
            # [E] Indirecta solar (100% generación PV acreditada sin desperdicio)
            "co2_ctrl_reduc_solar_ev_kg": co2_ctrl_reduc_solar_ev_kg,
            "co2_ctrl_reduc_solar_mall_kg": co2_ctrl_reduc_solar_mall_kg,
            "co2_ctrl_reduc_solar_bess_kg": co2_ctrl_reduc_solar_bess_kg,
            "co2_ctrl_reduc_solar_exp_kg": co2_ctrl_reduc_solar_exp_kg,
            "co2_ctrl_reduc_solar_total_kg": co2_ctrl_reduc_solar_total_kg,
            # [F] Indirecta BESS: descarga corta pico de mall/EVs (solar diferido)
            "co2_ctrl_reduc_bess_desc_kg": co2_ctrl_reduc_bess_desc_kg,
            # ── F0: situación actual sin proyecto (referencia OE2, parque sin EV) ─────
            "co2_total_sinproyecto_kg":      co2_total_sinproyecto_kg,
            "co2_sinproyecto_mall_kg":       co2_sinproyecto_mall_kg,
            "co2_sinproyecto_combustion_kg": co2_sinproyecto_combustion_kg,
            # ── Dispatch real: flujos de energía hacia cargadores EV (decisión agente) ────
            # _dp son los valores del dispatch horario real (no del CSV de referencia).
            # Permiten ver desde qué fuente (PV/BESS/Grid) el agente alimentó los cargadores.
            "dispatch_pv_to_ev_kwh":   _dp["pv_to_ev_kwh"],    # solar directo → cargadores
            "dispatch_bess_to_ev_kwh": _dp["bess_to_ev_kwh"],  # BESS descarga → cargadores
            "dispatch_grid_to_ev_kwh": _dp["grid_to_ev_kwh"],  # red diesel → cargadores
            # ── Tarifas OSINERGMIN + Mecanismo Compensación SSAA (Iquitos) ────────
            # Dataset tariffs_osinergmin.csv — Res. N° 047-2024-OS/CD + AAPP
            "tarifa_energia_soles_kwh":   float(self._tarifa_energia[min(t, len(self._tarifa_energia) - 1)]),
            "tarifa_total_soles_kwh":     float(self._tarifa_total[min(t, len(self._tarifa_total) - 1)]),
            "mecanismo_compensacion_soles_kwh": float(self._mecanismo_comp[min(t, len(self._mecanismo_comp) - 1)]),
            "ahorro_social_kwh_soles":    float(self._ahorro_social[min(t, len(self._ahorro_social) - 1)]),
            # ── Costo energético real del paso (importación red × tarifa total) ──
            # tarifa_total = energía HP/HFP + AAPP (dataset tariffs_osinergmin.csv)
            "cost_soles": _co2_grid_import * float(self._tarifa_total[min(t, len(self._tarifa_total) - 1)]),
            "cost_mecanismo_comp_soles": _co2_grid_import * float(self._mecanismo_comp[min(t, len(self._mecanismo_comp) - 1)]),
            "ahorro_social_total_soles":  _co2_grid_import * float(self._ahorro_social[min(t, len(self._ahorro_social) - 1)]),
            "cost_usd":   _co2_grid_import * float(self._mall_tarifa[t]) / 3.75,
        })

        return obs, reward, bool(terminated), bool(truncated), dict(info)
