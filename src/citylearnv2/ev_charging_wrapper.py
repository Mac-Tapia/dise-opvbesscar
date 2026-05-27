"""
ev_charging_wrapper.py — IquitosEVChargingWrapper
=====================================================================
Wrapper Gymnasium sobre CityLearnEnv que amplía el espacio de acciones
para incluir el control de cargadores EV de motos y mototaxis.

OBJETIVO OE3: Seleccionar el agente IA para gestión de recarga de motos
y mototaxis que contribuye cuantificablemente a la reducción de CO₂ en
Iquitos (0.4521 kg CO₂/kWh, 0.87/0.54 kg CO₂/L gasolina).

INFRAESTRUCTURA v5.7:
  - Cargadores motos     : 15 × 2 sockets × 7.4 kW = 222 kW max
  - Cargadores mototaxis : 4  × 2 sockets × 7.4 kW = 59.2 kW max
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

ESPACIO DE OBSERVACIÓN EXTENDIDO (16D = CityLearn 11D + EV 5D):
  [0-10]  obs CityLearn estándar (month, hour, day_type, temp, irradiancia,
          carbon_intensity, non_shiftable_load, solar_gen, bess_soc,
          net_electricity_consumption, ...)
  [11]  ev_motos_demand_norm    — demanda motos hora actual (normaliz. 0-1)
  [12]  ev_mototaxis_demand_norm — demanda mototaxis hora actual
  [13]  ev_motos_debt_norm      — energía motos pendiente del día (0-1)
  [14]  ev_mototaxis_debt_norm  — energía mototaxis pendiente del día (0-1)
  [15]  hour_sin                — sin(2π·hour/24), señal periódica para urgencia

RECOMPENSA MULTI-OBJETIVO (CO2_DUAL_FOCUS v7.0, pesos OE3):
  r_direct_co2   0.35  — CO₂ directo evitado: motos+mototaxis vs gasolina
  r_indirect_co2 0.30  — CO₂ indirecto: grid_import × 0.4521 kg/kWh
  r_ev_complete  0.25  — penalizar deuda EV incumplida al fin del día
  r_solar        0.05  — maximizar autoconsumo solar
  r_grid_stable  0.05  — penalizar rampas bruscas de importación de red

Uso:
    from src.citylearnv2.ev_charging_wrapper import IquitosEVChargingWrapper
    from src.citylearnv2.env_factory import create_iquitos_env

    base_env = create_iquitos_env()   # CityLearnEnv (solo BESS + mall, sin EVs)
    env = IquitosEVChargingWrapper(base_env)
    # → obs_dim = 16, action_dim = 3

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

logger = logging.getLogger(__name__)

# ── Rutas ─────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_EV_DEMAND_CSV     = _PROJECT_ROOT / "data" / "interim" / "citylearn_v2" / "ev_demand.csv"
# Fuentes OE2 originales — cargadas DIRECTAMENTE por el wrapper (no vía CityLearn obs)
_OE2_DATA_DIR      = _PROJECT_ROOT / "data" / "iquitos_ev_mall"
_SOLAR_CSV         = _OE2_DATA_DIR / "solar_generation.csv"       # potencia_kw (8760h)
_MALL_CSV          = _OE2_DATA_DIR / "mall_demand.csv"            # mall_demand_kwh (8760h)
_BESS_CSV          = _OE2_DATA_DIR / "bess_timeseries.csv"        # soc_percent, grid_import_kwh, …
_CHARGERS_CSV      = _OE2_DATA_DIR / "chargers_timeseries.csv"   # ev_energia_motos_kwh, co2_reduccion_motos_kg, …

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
BESS_SOC_MIN: float = 0.20                 # SOC mínimo BESS — 20% (DoD 80%), igual que EV_SOC_MIN
BESS_SOC_MAX: float = 1.00                 # SOC máximo BESS
BESS_MAX_KW: float = 400.0                 # Potencia máxima BESS (kW)
BESS_CAPACITY_KWH: float = 2000.0          # Capacidad energética BESS (kWh) — OE2 v5.3
BESS_EFF_ROUNDTRIP: float = 0.95           # Eficiencia round-trip lithium-ion (OE2 bess.py)

# Pesos de recompensa OE3 CO2_DUAL_FOCUS v7.0
# Pesos v7.1 BESS_DISPATCH_FOCUS:
# _W_DIRECT_CO2 reducido (0.35→0.10): r_direct_co2 es casi constante
# (EVs siempre sustituyen ICE), no guía el despacho de BESS. Un peso
# alto crea baseline positivo que cancela la penalización de grid_import.
# _W_INDIRECT_CO2 aumentado (0.30→0.55): señal primaria para que el agente
# aprenda a descargar BESS en lugar de importar de red.
_W_DIRECT_CO2: float = 0.10
_W_INDIRECT_CO2: float = 0.55
_W_EV_COMPLETE: float = 0.25
_W_SOLAR: float = 0.05
_W_GRID_STABLE: float = 0.05


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
        non_shiftable_load debe contener solo la demanda del mall.
    ev_demand_csv : Path, optional
        Ruta al archivo ev_demand.csv generado por schema_builder.
        Contiene demanda horaria de motos, mototaxis y CO₂ directo.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        env: Any,
        ev_demand_csv: Path | None = None,
    ) -> None:
        super().__init__(env)

        # ── Cargar demanda EV horaria DIRECTAMENTE desde chargers_timeseries.csv (OE2) ──
        # Fuente primaria: data/iquitos_ev_mall/chargers_timeseries.csv
        # (ev_demand_csv se ignora — siempre cargamos desde OE2 directo)
        import pandas as _pd
        if not _CHARGERS_CSV.exists():
            raise FileNotFoundError(
                f"chargers_timeseries.csv no encontrado en {_CHARGERS_CSV}. "
                "Verifica que la ruta data/iquitos_ev_mall/ existe con los datasets OE2."
            )
        _CHARGERS_COLS = [
            "ev_energia_motos_kwh", "ev_energia_mototaxis_kwh",
            "ev_energia_total_kwh", "co2_directo_anual_acumulado_kg",
            "motos_cargadas_hora", "mototaxis_cargadas_hora",
            "total_vehiculos_cargados_hora", "motos_acumulado_diario",
            "mototaxis_acumulado_diario", "total_acumulado_diario",
            "motos_acumulado_mensual", "mototaxis_acumulado_mensual",
            "total_acumulado_mensual", "motos_acumulado_anual",
            "mototaxis_acumulado_anual", "total_acumulado_anual",
        ]
        for _si in range(38):  # 38 sockets
            for _sf in ("charger_power_kw", "battery_kwh", "soc_current",
                        "soc_arrival", "soc_target", "active", "charging_power_kw"):
                _CHARGERS_COLS.append(f"socket_{_si:03d}_{_sf}")
        chargers_df = _pd.read_csv(_CHARGERS_CSV, usecols=_CHARGERS_COLS)
        self._n = len(chargers_df)

        # Arrays horarios (8760 filas) — columnas de chargers_timeseries.csv OE2
        self._ev_motos_demand: np.ndarray = chargers_df["ev_energia_motos_kwh"].to_numpy(dtype=np.float64)
        self._ev_mototaxis_demand: np.ndarray = chargers_df["ev_energia_mototaxis_kwh"].to_numpy(dtype=np.float64)
        # CO2 directo: energía EV × factor (combustible desplazado) — computed from energia_kwh
        self._co2_motos: np.ndarray = self._ev_motos_demand * CO2_FACTOR_MOTO
        self._co2_mototaxis: np.ndarray = self._ev_mototaxis_demand * CO2_FACTOR_MOTOTAXI

        # Máximos del año para normalizar observaciones de deuda
        self._daily_motos_max: float = float(
            max(self._ev_motos_demand.reshape(365, 24).sum(axis=1).max(), 1.0)
        )
        self._daily_mototaxis_max: float = float(
            max(self._ev_mototaxis_demand.reshape(365, 24).sum(axis=1).max(), 1.0)
        )

        logger.info(
            "EV demand cargado: motos=%.0f kWh/año | mototaxis=%.0f kWh/año | "
            "CO₂ directo=%.0f kg/año",
            self._ev_motos_demand.sum(),
            self._ev_mototaxis_demand.sum(),
            (self._co2_motos + self._co2_mototaxis).sum(),
        )

        # ── Datos OE2 reales — cargados DIRECTAMENTE (no via obs CityLearn) ────
        # solar_generation.csv — TODAS las columnas OE2 (8760 filas)
        if not _SOLAR_CSV.exists():
            raise FileNotFoundError(f"solar_generation.csv no encontrado en {_SOLAR_CSV}")
        solar_src = _pd.read_csv(_SOLAR_CSV)
        # Columnas numéricas OE2 solar (excluye datetime y hora_tipo categórico)
        _SOLAR_REQUIRED = ["irradiancia_ghi", "temperatura_c", "velocidad_viento_ms",
                           "potencia_kw", "energia_kwh"]
        for _col in _SOLAR_REQUIRED:
            if _col not in solar_src.columns:
                raise KeyError(f"Columna '{_col}' no encontrada en {_SOLAR_CSV}. "
                               f"Columnas disponibles: {list(solar_src.columns)}")
        # Arrays principales
        self._solar_kw: np.ndarray          = solar_src["potencia_kw"].to_numpy(dtype=np.float64)
        self._solar_kwh: np.ndarray          = solar_src["energia_kwh"].to_numpy(dtype=np.float64)
        self._solar_ghi: np.ndarray          = solar_src["irradiancia_ghi"].to_numpy(dtype=np.float64)
        self._solar_temp: np.ndarray         = solar_src["temperatura_c"].to_numpy(dtype=np.float64)
        self._solar_viento: np.ndarray       = solar_src["velocidad_viento_ms"].to_numpy(dtype=np.float64)
        # CO2 indirecto solar: energia × factor grid (columna eliminada del CSV, se computa aquí)
        self._solar_co2_indirect: np.ndarray = self._solar_kwh * CO2_GRID_KG_PER_KWH
        # Columnas opcionales (pueden no estar en versiones antiguas del dataset)
        self._solar_is_punta: np.ndarray     = (solar_src["is_hora_punta"].to_numpy(dtype=np.float64)
                                                 if "is_hora_punta" in solar_src.columns
                                                 else np.zeros(self._n, dtype=np.float64))
        self._solar_tarifa: np.ndarray       = (solar_src["tarifa_aplicada_soles"].to_numpy(dtype=np.float64)
                                                 if "tarifa_aplicada_soles" in solar_src.columns
                                                 else np.zeros(self._n, dtype=np.float64))
        self._solar_ahorro: np.ndarray       = (solar_src["ahorro_solar_soles"].to_numpy(dtype=np.float64)
                                                 if "ahorro_solar_soles" in solar_src.columns
                                                 else np.zeros(self._n, dtype=np.float64))

        # ── mall_demand.csv — TODAS las columnas OE2 ─────────────────────
        if not _MALL_CSV.exists():
            raise FileNotFoundError(f"mall_demand.csv no encontrado en {_MALL_CSV}")
        mall_src = _pd.read_csv(_MALL_CSV)
        self._mall_kw: np.ndarray               = mall_src["mall_demand_kwh"].to_numpy(dtype=np.float64)
        self._mall_co2_indirect: np.ndarray     = mall_src["mall_co2_indirect_kg"].to_numpy(dtype=np.float64)
        self._mall_is_punta: np.ndarray         = mall_src["is_hora_punta"].to_numpy(dtype=np.float64)
        self._mall_tarifa: np.ndarray           = mall_src["tarifa_soles_kwh"].to_numpy(dtype=np.float64)
        self._mall_cost_soles: np.ndarray       = mall_src["mall_cost_soles"].to_numpy(dtype=np.float64)

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

        # ── chargers_timeseries.csv — columnas resumen + sockets 2D ──────
        # (los 38 sockets se almacenan en arrays 2D: shape (8760, 38))
        _N_SOCKETS = 38
        # Arrays resumen (globales del parque)
        self._chr_ev_total_kwh: np.ndarray      = chargers_df["ev_energia_total_kwh"].to_numpy(dtype=np.float64)
        self._chr_costo_soles: np.ndarray       = np.zeros(self._n, dtype=np.float64)   # computed in loader
        self._chr_co2_directo: np.ndarray       = self._co2_motos + self._co2_mototaxis
        self._chr_co2_acum_diario: np.ndarray   = np.zeros(self._n, dtype=np.float64)   # not in CSV schema
        self._chr_co2_por_vehiculo: np.ndarray  = np.zeros(self._n, dtype=np.float64)   # not in CSV schema
        self._chr_co2_acum_anual: np.ndarray    = chargers_df["co2_directo_anual_acumulado_kg"].to_numpy(dtype=np.float64)
        self._chr_motos_hora: np.ndarray        = chargers_df["motos_cargadas_hora"].to_numpy(dtype=np.float64)
        self._chr_mototaxis_hora: np.ndarray    = chargers_df["mototaxis_cargadas_hora"].to_numpy(dtype=np.float64)
        self._chr_total_hora: np.ndarray        = chargers_df["total_vehiculos_cargados_hora"].to_numpy(dtype=np.float64)
        self._chr_motos_diario: np.ndarray      = chargers_df["motos_acumulado_diario"].to_numpy(dtype=np.float64)
        self._chr_mototaxis_diario: np.ndarray  = chargers_df["mototaxis_acumulado_diario"].to_numpy(dtype=np.float64)
        self._chr_total_diario: np.ndarray      = chargers_df["total_acumulado_diario"].to_numpy(dtype=np.float64)
        self._chr_motos_mensual: np.ndarray     = chargers_df["motos_acumulado_mensual"].to_numpy(dtype=np.float64)
        self._chr_mototaxis_mensual: np.ndarray = chargers_df["mototaxis_acumulado_mensual"].to_numpy(dtype=np.float64)
        self._chr_total_mensual: np.ndarray     = chargers_df["total_acumulado_mensual"].to_numpy(dtype=np.float64)
        self._chr_motos_anual: np.ndarray       = chargers_df["motos_acumulado_anual"].to_numpy(dtype=np.float64)
        self._chr_mototaxis_anual: np.ndarray   = chargers_df["mototaxis_acumulado_anual"].to_numpy(dtype=np.float64)
        self._chr_total_anual: np.ndarray       = chargers_df["total_acumulado_anual"].to_numpy(dtype=np.float64)
        self._chr_co2_grid_kwh: np.ndarray      = np.zeros(self._n, dtype=np.float64)   # not in CSV schema
        self._chr_co2_neto_hora: np.ndarray     = self._co2_motos + self._co2_mototaxis
        self._chr_ev_demand_kwh: np.ndarray     = self._chr_ev_total_kwh
        self._chr_is_punta: np.ndarray          = np.zeros(self._n, dtype=np.float64)   # not in CSV schema
        self._chr_tarifa: np.ndarray            = np.zeros(self._n, dtype=np.float64)   # not in CSV schema
        # Sockets 2D: shape (8760, 38) — una fila por hora, una columna por socket
        self._skt_charger_power: np.ndarray = np.stack(
            [chargers_df[f"socket_{i:03d}_charger_power_kw"].to_numpy(dtype=np.float32)
             for i in range(_N_SOCKETS)], axis=1)   # (8760, 38)
        self._skt_battery_kwh: np.ndarray = np.stack(
            [chargers_df[f"socket_{i:03d}_battery_kwh"].to_numpy(dtype=np.float32)
             for i in range(_N_SOCKETS)], axis=1)
        self._skt_soc_current: np.ndarray = np.stack(
            [chargers_df[f"socket_{i:03d}_soc_current"].to_numpy(dtype=np.float32)
             for i in range(_N_SOCKETS)], axis=1)
        self._skt_soc_arrival: np.ndarray = np.stack(
            [chargers_df[f"socket_{i:03d}_soc_arrival"].to_numpy(dtype=np.float32)
             for i in range(_N_SOCKETS)], axis=1)
        self._skt_soc_target: np.ndarray = np.stack(
            [chargers_df[f"socket_{i:03d}_soc_target"].to_numpy(dtype=np.float32)
             for i in range(_N_SOCKETS)], axis=1)
        self._skt_active: np.ndarray = np.stack(
            [chargers_df[f"socket_{i:03d}_active"].to_numpy(dtype=np.float32)
             for i in range(_N_SOCKETS)], axis=1)
        self._skt_charging_power: np.ndarray = np.stack(
            [chargers_df[f"socket_{i:03d}_charging_power_kw"].to_numpy(dtype=np.float32)
             for i in range(_N_SOCKETS)], axis=1)

        # Validar longitudes (todos deben ser 8760)
        for _name, _arr in [
            ("mall_kw",         self._mall_kw),
            ("bess_soc_ref",    self._bess_soc_ref),
            ("grid_import_ref", self._grid_import_ref),
            ("chr_motos_hora",  self._chr_motos_hora),
            ("skt_active",      self._skt_active),
        ]:
            if len(_arr) != self._n:
                raise ValueError(
                    f"OE2 dataset '{_name}' tiene {len(_arr)} filas, "
                    f"esperado {self._n}. Regenera los datasets OE2."
                )

        logger.info(
            "OE2 (4 datasets) cargado directamente:\n"
            "  solar  : %.1f MWh/año | irradiancia_max=%.0f W/m²\n"
            "  mall   : %.1f MWh/año | costo_total=%.0f soles/año\n"
            "  BESS   : SOC_ref_avg=%.0f%% | grid_import_total=%.1f MWh/año\n"
            "  cargas : motos=%.0f kWh/año | mototaxis=%.0f kWh/año | "
            "sockets=%d | CO₂_directo_total=%.0f kg/año",
            self._solar_kw.sum() / 1000,
            self._solar_ghi.max(),
            self._mall_kw.sum() / 1000,
            self._mall_cost_soles.sum(),
            self._bess_soc_ref.mean() * 100,
            self._grid_import_ref.sum() / 1000,  # nansum no necesario — fillna a 0
            self._ev_motos_demand.sum(),
            self._ev_mototaxis_demand.sum(),
            _N_SOCKETS,
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

        ev_low = np.array([0.0, 0.0, 0.0, 0.0, -1.0], dtype=np.float32)
        ev_high = np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32)

        # Obs space normalizado: base en [-1, 1]; EV dims en [-1, 1] (hour_sin) u [0, 1]
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

        logger.info(
            "IquitosEVChargingWrapper listo: obs_dim=%d (base=%d + ev=5), action_dim=3",
            self._obs_dim_base + 5,
            self._obs_dim_base,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

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

        ev_obs = np.array(
            [motos_dem_norm, mototaxis_dem_norm, motos_debt_norm, mototaxis_debt_norm, hour_sin],
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
    ) -> float:
        """Calcula la recompensa multi-objetivo CO2_DUAL_FOCUS v7.0.

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

        # ── r_direct_co2 (peso 0.35) ──────────────────────────────────────
        # CO₂ directo evitado: EVs reemplazando motos/mototaxis de gasolina
        t = self._t
        co2_motos_saved = self._co2_motos[t] * (
            ev_motos_actual / max(self._ev_motos_demand[t], 0.001)
        ) if self._ev_motos_demand[t] > 0 else 0.0
        co2_mototaxis_saved = self._co2_mototaxis[t] * (
            ev_mototaxis_actual / max(self._ev_mototaxis_demand[t], 0.001)
        ) if self._ev_mototaxis_demand[t] > 0 else 0.0
        co2_direct_total = co2_motos_saved + co2_mototaxis_saved
        r_direct_co2 = float(np.clip(co2_direct_total / MAX_CO2_DIRECT_PER_HOUR, 0.0, 1.0))

        # ── r_indirect_co2 (peso 0.30) ────────────────────────────────────
        # CO₂ indirecto: importación de red × factor emisión Iquitos
        r_indirect_co2 = -float(np.clip(grid_import_real / MAX_GRID_IMPORT_KW, 0.0, 1.0))

        # ── r_ev_complete (peso 0.25) ─────────────────────────────────────
        # Bonificar completar carga EV al día; penalizar deuda incumplida (fin día)
        hour = int(self._t % 24)
        if hour == 23 and penalty_debt > 0.0:
            # Penalización fuerte al final del día por deuda no cumplida
            r_ev_complete = -float(np.clip(penalty_debt, 0.0, 1.0))
        else:
            # Bonus parcial por carga efectuada respecto a demanda esperada
            demand_hora = self._ev_motos_demand[t] + self._ev_mototaxis_demand[t]
            if demand_hora > 0.001:
                ev_total_actual = ev_motos_actual + ev_mototaxis_actual
                completion_frac = np.clip(ev_total_actual / demand_hora, 0.0, 1.0)
                r_ev_complete = float(completion_frac - 0.5)  # centrado en 0
            else:
                r_ev_complete = 0.0

        # ── r_solar (peso 0.05) ───────────────────────────────────────────
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

        # ── Recompensa combinada ponderada ─────────────────────────────────
        reward = (
            _W_DIRECT_CO2 * r_direct_co2
            + _W_INDIRECT_CO2 * r_indirect_co2
            + _W_EV_COMPLETE * r_ev_complete
            + _W_SOLAR * r_solar
            + _W_GRID_STABLE * r_grid_stable
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
        obs : np.ndarray, shape (obs_dim_base + 5,)
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

        # ── Calcular despacho EV real ─────────────────────────────────────
        # Demanda base de este paso (del perfil histórico)
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
        motos_not_charged = motos_demand_t * (1.0 - ev_motos_frac)
        mototaxis_not_charged = mototaxis_demand_t * (1.0 - ev_mototaxis_frac)
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

        co2_solar_f6_kg           = _solar_kw  * CO2_GRID_KG_PER_KWH  # F6 total
        co2_solar_ev_f6a_kg       = _f6a * CO2_GRID_KG_PER_KWH        # F6a
        co2_solar_mall_f6b_kg     = _f6b * CO2_GRID_KG_PER_KWH        # F6b
        co2_solar_bess_f6c_kg     = _f6c * CO2_GRID_KG_PER_KWH        # F6c
        co2_solar_export_f6d_kg   = _f6d * CO2_GRID_KG_PER_KWH        # F6d = F8

        # ── F7: BESS descarga → desplaza importación de red dísel ────────────────────────
        co2_bess_discharge_f7_kg  = _co2_bess_disc * CO2_GRID_KG_PER_KWH  # definición original

        # ── FÓRMULA 0 — SIN PROYECTO (estado actual antes de implementar OE2/OE3) ──
        # Referencia: mall en red pública diesel + parque completo de combustión sin EVs.
        # Motos y mototaxis estacionadas en playa del mall (ref. OE2), sin cargadores instalados.
        # → Cuantifica las emisiones ACTUALES que el proyecto eliminará (impacto TOTAL del proyecto).
        co2_sinproyecto_mall_kg       = _mall_kw             * CO2_GRID_KG_PER_KWH  # indirecta: mall en red diesel
        co2_sinproyecto_combustion_kg = _F0_CO2_COMBUSTION_PER_H                    # directa FIJA: OE2 — 900 motos+130 mototaxis ICE
        co2_total_sinproyecto_kg      = co2_sinproyecto_mall_kg + co2_sinproyecto_combustion_kg

        # ── FÓRMULA 1 — BASELINE (sin solar, sin BESS, sin agente RL) ───────────
        # baseline = CO₂ directa (combustión) + CO₂ indirecta (red diesel) − reducción directa (electrificación)
        #
        # [A] Directa: CO₂ del parque asumiendo combustión interna (referencia preelectrificación)
        co2_directo_combustion = (
            motos_demand_t    * CO2_FACTOR_MOTO        # 0.87 kg CO₂/kWh gasolina moto
            + mototaxis_demand_t * CO2_FACTOR_MOTOTAXI  # 0.54 kg CO₂/kWh gasolina mototaxi
        )
        # [B] Indirecta: red pública diesel cubre mall + carga EV (sin solar ni BESS)
        co2_indirecto_red_base = (
            _mall_kw + motos_demand_t + mototaxis_demand_t
        ) * CO2_GRID_KG_PER_KWH  # 0.4521 kg CO₂/kWh red aislada Iquitos
        # [C] Reducción directa: CO₂ evitado porque los EVs ya no queman combustible
        co2_reduccion_directa_elec = (
            ev_motos_actual    * CO2_FACTOR_MOTO
            + ev_mototaxis_actual * CO2_FACTOR_MOTOTAXI
        )
        co2_total_baseline_kg = co2_directo_combustion + co2_indirecto_red_base - co2_reduccion_directa_elec

        # ── FÓRMULA 2 — CONTROL INTELIGENTE (con solar+BESS+agente RL) ──────────
        # Emisión residual: única fuente de CO₂ que solar+BESS+agente no pudieron cubrir
        # Definición original OE3: importación de red = net_consum CityLearn + EVs
        co2_total_control_kg = _co2_grid_import * CO2_GRID_KG_PER_KWH

        # Desglose cuantificado de CO₂ evitado por cada mecanismo del proyecto:
        # ── [D] Reducción DIRECTA: EVs en carga → parque no quema combustible fósil ──
        co2_ctrl_reduc_directa_kg = (
            ev_motos_actual    * CO2_FACTOR_MOTO        # motos eléctricas vs 125cc gasolina
            + ev_mototaxis_actual * CO2_FACTOR_MOTOTAXI  # mototaxis eléctricas vs 150cc gasolina
        )
        # ── [E] Reducción INDIRECTA — solar PV (100% acreditado, sin desperdicio): ──
        #       F6a: solar → carga EVs directamente   (desplaza red diesel en EVs)
        co2_ctrl_reduc_solar_ev_kg    = _f6a * CO2_GRID_KG_PER_KWH
        #       F6b: solar → mall directamente        (desplaza red diesel en mall)
        co2_ctrl_reduc_solar_mall_kg  = _f6b * CO2_GRID_KG_PER_KWH
        #       F6c: solar → BESS almacenado          (energía limpia guardada para cortar pico)
        co2_ctrl_reduc_solar_bess_kg  = _f6c * CO2_GRID_KG_PER_KWH
        #       F6d: solar exportado a red aislada    (desplaza diesel en red Iquitos)
        co2_ctrl_reduc_solar_exp_kg   = _f6d * CO2_GRID_KG_PER_KWH
        #       Total solar = F6a + F6b + F6c + F6d = 100% generación PV acreditada
        co2_ctrl_reduc_solar_total_kg = _solar_kw * CO2_GRID_KG_PER_KWH
        # ── [F] Reducción INDIRECTA — BESS descarga corta pico (tiempo diferido): ──
        #       BESS libera energía solar almacenada (F6c previo) en hora de máxima demanda
        #       → desplaza importación de red diesel en mall y carga EV
        co2_ctrl_reduc_bess_desc_kg   = _co2_bess_disc * CO2_GRID_KG_PER_KWH    # definición original

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
            # ── Costo energético real del paso (importación red × tarifa) ──────────
            # Usado por EVMetricsCallback en scripts de entrenamiento SAC/PPO/A2C
            "cost_soles": _co2_grid_import * float(self._mall_tarifa[t]),
            "cost_usd":   _co2_grid_import * float(self._mall_tarifa[t]) / 3.75,
        })

        return obs, reward, bool(terminated), bool(truncated), dict(info)
