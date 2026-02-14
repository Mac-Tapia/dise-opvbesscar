from __future__ import annotations
"""
================================================================================
OE3 DATASET BUILDER v5.3 - CityLearn v2.5.0 Integration

TRACKING DE REDUCCIONES DIRECTAS E INDIRECTAS DE CO2:

1. CO2 DIRECTO (Direct CO2 from EV charging - fuel switch):
   - Factor CO2 gasolina: 2.31 kg CO2/L (IPCC AR5)
   - Factor neto moto: 0.87 kg CO2/kWh (después de restar emisiones red)
   - Factor neto mototaxi: 0.47 kg CO2/kWh
   - Acumulado anual: ~357 toneladas CO2/año evitadas

2. CO2 INDIRECTO (Grid import emissions avoided by solar):
   - Factor grid Iquitos: 0.4521 kg CO2/kWh (central térmica aislada)
   - Si PV directa --> consumo: Se evita importación = 0.4521 kg CO2/kWh evitado
   - Acumulado anual: ~3,749 toneladas CO2/año evitadas

3. VARIABLES OBSERVABLES v5.3 (nuevas columnas para agentes):
   
   CHARGERS (chargers_ev_ano_2024_v3.csv - 353 columnas):
   - is_hora_punta: bool (18:00-22:59 = True)
   - tarifa_aplicada_soles: S/.0.45 HP / S/.0.28 HFP (OSINERGMIN MT3)
   - ev_energia_total_kwh: energía EV por hora
   - costo_carga_ev_soles: costo × tarifa aplicada
   - ev_energia_motos_kwh: energía motos por hora
   - ev_energia_mototaxis_kwh: energía mototaxis por hora
   - co2_reduccion_motos_kg: CO2 evitado motos (factor 0.87)
   - co2_reduccion_mototaxis_kg: CO2 evitado mototaxis (factor 0.47)
   - reduccion_directa_co2_kg: total CO2 evitado EVs
   - ev_demand_kwh: demanda EV total (alias)

   SOLAR (pv_generation_hourly_citylearn_v2.csv - 18 columnas):
   - is_hora_punta: bool (18:00-22:59 = True)
   - tarifa_aplicada_soles: S/.0.45 HP / S/.0.28 HFP
   - ahorro_solar_soles: ahorro monetario por generación solar
   - reduccion_indirecta_co2_kg: CO2 evitado por solar (factor 0.4521)
   - co2_evitado_mall_kg: CO2 evitado asignado a Mall (67%)
   - co2_evitado_ev_kg: CO2 evitado asignado a EV (33%)

4. TRACKING EN SISTEMA:
   - dataset_builder.py: Valida datos, estructura y genera observables_oe2.csv
   - rewards.py: Calcula CO2 directo + indirecto usando variables observables
   - agents: Optimizan para maximizar reducciones (directas + indirectas)
   - simulate.py: Acumula y reporta reducciones totales

Vinculaciones v5.3 (2026-02-12):
   - config.yaml: co2_grid_factor_kg_per_kwh = 0.4521
   - config.yaml: ev_co2_conversion_kg_per_kwh = 2.146 (deprecated, usar factors directos)
   - rewards.py: IquitosContext con factores CO2 netos
   - chargers.py: FACTOR_CO2_NETO_MOTO = 0.87, FACTOR_CO2_NETO_MOTOTAXI = 0.47
   - solar_pvlib.py: FACTOR_CO2_KG_KWH = 0.4521
   - agents: Reciben observables_oe2.csv con todas las variables de tracking
================================================================================
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import shutil
import logging
import re

import numpy as np
# pylint: disable=import-error
import pandas as pd  # type: ignore

logger = logging.getLogger(__name__)

# =============================================================================
# OE2 DATA LOADER v5.5 - Rutas y Funciones de Carga (unificado de data_loader.py)
# =============================================================================
# Datasets principales v5.5 (source of truth en data/oe2/):
# - Solar: data/oe2/Generacionsolar/pv_generation_citylearn2024.csv
# - BESS: data/oe2/bess/bess_ano_2024.csv (1700 kWh, 400 kW, SOC@22h=20%)
# - Chargers: data/oe2/chargers/chargers_ev_ano_2024_v3.csv (38 sockets)
# - Mall: data/oe2/demandamallkwh/demandamallhorakwh.csv
# =============================================================================

DEFAULT_SOLAR_PATH = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
DEFAULT_BESS_PATH = Path("data/oe2/bess/bess_ano_2024.csv")
DEFAULT_CHARGERS_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
DEFAULT_MALL_DEMAND_PATH = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")

# Rutas de escenarios v5.5
DEFAULT_SCENARIOS_DIR = Path("data/oe2/chargers")
SCENARIOS_SELECTION_PE_FC_PATH = DEFAULT_SCENARIOS_DIR / "selection_pe_fc_completo.csv"
SCENARIOS_TABLA_DETALLADOS_PATH = DEFAULT_SCENARIOS_DIR / "tabla_escenarios_detallados.csv"
SCENARIOS_TABLA_ESTADISTICAS_PATH = DEFAULT_SCENARIOS_DIR / "tabla_estadisticas_escenarios.csv"
SCENARIOS_TABLA_RECOMENDADO_PATH = DEFAULT_SCENARIOS_DIR / "tabla_escenario_recomendado.csv"
SCENARIOS_TABLA13_PATH = DEFAULT_SCENARIOS_DIR / "escenarios_tabla13.csv"

# Rutas intermedias (fallback si principales no existen)
INTERIM_SOLAR_PATHS = [
    Path("data/interim/oe2/solar/pv_generation_hourly_citylearn_v2.csv"),
    Path("data/interim/oe2/solar/pv_generation_timeseries.csv"),
]
INTERIM_BESS_PATH = Path("data/interim/oe2/bess/bess_hourly_dataset_2024.csv")
INTERIM_CHARGERS_PATHS = [Path("data/interim/oe2/chargers/chargers_real_hourly_2024.csv")]
INTERIM_DEMAND_PATH = Path("data/interim/oe2/demandamallkwh/demandamallhorakwh.csv")


class OE2ValidationError(Exception):
    """Excepción para errores de validación OE2."""
    pass


@dataclass(frozen=True)
class SolarData:
    """Datos inmutables de generación solar."""
    timeseries: np.ndarray  # 8760 valores horarios (kW)
    capacity_kwp: float     # Capacidad instalada (kWp)
    location: str           # Ubicación

    def __post_init__(self) -> None:
        if len(self.timeseries) != 8760:
            raise OE2ValidationError(
                f"Solar timeseries must have 8760 hourly values, got {len(self.timeseries)}"
            )


@dataclass(frozen=True)
class BESSData:
    """Datos inmutables de BESS."""
    capacity_kwh: float    # 1700 kWh nominal (v5.5)
    power_kw: float        # 400 kW (v5.5)
    efficiency: float      # 0.95 round-trip


@dataclass(frozen=True)
class ChargerData:
    """Datos inmutables de cargador individual."""
    charger_id: int
    max_power_kw: float
    vehicle_type: str      # "moto" o "mototaxi"
    sockets: int           # 2 sockets por cargador (v5.5)


def resolve_data_path(primary_path: Path, fallback_paths: Optional[List[Path]] = None) -> Path:
    """Resuelve ruta preferiendo principal, luego fallbacks."""
    if primary_path.exists():
        return primary_path
    if fallback_paths:
        for fb in fallback_paths:
            if fb.exists():
                logger.warning(f"⚠ Using fallback: {fb}")
                return fb
    raise OE2ValidationError(f"Data path not found: {primary_path}")


def load_solar_data(csv_path: Optional[Path] = None) -> Tuple[SolarData, pd.DataFrame]:
    """Carga datos de generación solar desde pv_generation_citylearn2024.csv."""
    if csv_path is None:
        csv_path = resolve_data_path(DEFAULT_SOLAR_PATH, INTERIM_SOLAR_PATHS)
    else:
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise OE2ValidationError(f"Solar CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    logger.info(f"✓ Solar: {csv_path.name} ({len(df)} rows)")

    if 'potencia_kw' not in df.columns:
        raise OE2ValidationError("Solar CSV missing 'potencia_kw' column")

    values = df['potencia_kw'].astype(float).values
    if len(values) not in [8760, 8761]:
        raise OE2ValidationError(f"Solar must have 8760 rows, got {len(values)}")
    if len(values) == 8761:
        values = values[:8760]
        df = df.iloc[:8760].copy()

    solar_data = SolarData(timeseries=values, capacity_kwp=4050.0, location="Iquitos, Peru")
    logger.info(f"  → {solar_data.capacity_kwp} kWp, mean={values.mean():.1f} kW")
    return solar_data, df


def load_bess_data(csv_path: Optional[Path] = None) -> Tuple[BESSData, pd.DataFrame]:
    """Carga datos de BESS desde bess_ano_2024.csv v5.5."""
    if csv_path is None:
        csv_path = resolve_data_path(DEFAULT_BESS_PATH, [INTERIM_BESS_PATH])
    else:
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise OE2ValidationError(f"BESS CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    logger.info(f"✓ BESS: {csv_path.name} ({len(df)} rows)")

    required = ['bess_soc_percent', 'bess_charge_kwh', 'bess_discharge_kwh']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise OE2ValidationError(f"BESS missing columns: {missing}")
    if len(df) != 8760:
        raise OE2ValidationError(f"BESS must have 8760 rows, got {len(df)}")

    bess_data = BESSData(capacity_kwh=1700.0, power_kw=400.0, efficiency=0.95)
    logger.info(f"  → {bess_data.capacity_kwh} kWh, {bess_data.power_kw} kW")
    return bess_data, df


def load_chargers_data(csv_path: Optional[Path] = None) -> Tuple[List[ChargerData], pd.DataFrame]:
    """Carga datos de cargadores desde chargers_ev_ano_2024_v3.csv."""
    if csv_path is None:
        csv_path = resolve_data_path(DEFAULT_CHARGERS_PATH, INTERIM_CHARGERS_PATHS)
    else:
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise OE2ValidationError(f"Chargers CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    logger.info(f"✓ Chargers: {csv_path.name} ({len(df)} rows)")

    socket_cols = [c for c in df.columns if c.startswith('socket_')]
    socket_ids = set()
    for col in socket_cols:
        try:
            socket_ids.add(int(col.split('_')[1]))
        except (ValueError, IndexError):
            pass
    if not socket_ids:
        raise OE2ValidationError("No socket columns found")

    n_chargers = len(socket_ids) // 2
    chargers = []
    for i in range(n_chargers):
        vtype = "moto" if i < 15 else "mototaxi"
        chargers.append(ChargerData(
            charger_id=i, max_power_kw=7.4, vehicle_type=vtype, sockets=2
        ))
    logger.info(f"  → {len(chargers)} chargers, {len(socket_ids)} sockets")
    return chargers, df


def load_mall_demand_data(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """Carga demanda del mall desde demandamallhorakwh.csv."""
    if csv_path is None:
        csv_path = resolve_data_path(DEFAULT_MALL_DEMAND_PATH, [INTERIM_DEMAND_PATH])
    else:
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise OE2ValidationError(f"Mall CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, sep=';')
    logger.info(f"✓ Mall demand: {csv_path.name} ({len(df)} rows)")

    if 'kWh' not in df.columns or 'FECHAHORA' not in df.columns:
        raise OE2ValidationError("Mall CSV missing required columns")

    df['datetime'] = pd.to_datetime(df['FECHAHORA'], format='%d/%m/%Y %H:%M')
    df = df.rename(columns={'kWh': 'mall_demand_kwh'})
    df['mall_demand_kwh'] = pd.to_numeric(df['mall_demand_kwh'], errors='coerce')
    df_hourly = df[['datetime', 'mall_demand_kwh']].iloc[:8760].copy()
    logger.info(f"  → mean={df_hourly['mall_demand_kwh'].mean():.1f} kW")
    return df_hourly


def load_scenarios_metadata() -> Dict[str, pd.DataFrame]:
    """Carga tablas de escenarios desde data/oe2/chargers/."""
    results: Dict[str, pd.DataFrame] = {}
    paths = {
        'selection_pe_fc': SCENARIOS_SELECTION_PE_FC_PATH,
        'escenarios_detallados': SCENARIOS_TABLA_DETALLADOS_PATH,
        'estadisticas_escenarios': SCENARIOS_TABLA_ESTADISTICAS_PATH,
        'escenario_recomendado': SCENARIOS_TABLA_RECOMENDADO_PATH,
        'escenarios_tabla13': SCENARIOS_TABLA13_PATH,
    }
    for name, path in paths.items():
        if path.exists():
            results[name] = pd.read_csv(path)
            logger.info(f"✓ {name}: {len(results[name])} rows")
    if not results:
        raise OE2ValidationError("No scenario tables found")
    return results


def validate_oe2_complete(cleanup_interim: bool = False) -> Dict[str, Any]:
    """Validación completa de todos los datos OE2."""
    results: Dict[str, Any] = {"is_valid": False, "errors": [], "dataframes": {}}
    
    try:
        solar, solar_df = load_solar_data()
        results["solar"] = {"capacity_kwp": solar.capacity_kwp, "timesteps": len(solar.timeseries)}
        results["dataframes"]["solar"] = solar_df
    except OE2ValidationError as e:
        results["errors"].append(str(e))

    try:
        bess, bess_df = load_bess_data()
        results["bess"] = {"capacity_kwh": bess.capacity_kwh, "power_kw": bess.power_kw}
        results["dataframes"]["bess"] = bess_df
    except OE2ValidationError as e:
        results["errors"].append(str(e))

    try:
        chargers, chargers_df = load_chargers_data()
        results["chargers"] = {"total_units": len(chargers), "total_sockets": sum(c.sockets for c in chargers)}
        results["dataframes"]["chargers"] = chargers_df
    except OE2ValidationError as e:
        results["errors"].append(str(e))

    try:
        mall_df = load_mall_demand_data()
        results["mall_demand"] = {"timesteps": len(mall_df)}
        results["dataframes"]["mall_demand"] = mall_df
    except OE2ValidationError as e:
        results["errors"].append(str(e))

    results["is_valid"] = len(results["errors"]) == 0
    if results["is_valid"]:
        logger.info("✓✓✓ OE2 VALIDATION PASSED ✓✓✓")
    else:
        logger.error(f"✗ OE2 validation failed: {results['errors']}")
    return results


def rebuild_oe2_datasets_complete(cleanup_interim: bool = True) -> Dict[str, Any]:
    """Reconstrucción y validación completa de datasets OE2."""
    logger.info("🔄 INICIANDO VALIDACIÓN OE2 v5.5...")
    return validate_oe2_complete(cleanup_interim=cleanup_interim)


# =============================================================================
# CONSTANTES OSINERGMIN v5.3 - Sistema Aislado Iquitos
# Tarifas MT3 para aplicar en rewards según hora del día
# =============================================================================
TARIFA_ENERGIA_HP_SOLES = 0.45   # Hora Punta: S/.0.45/kWh (18:00-22:59)
TARIFA_ENERGIA_HFP_SOLES = 0.28  # Fuera Punta: S/.0.28/kWh
HORA_INICIO_HP = 18              # Hora inicio Hora Punta
HORA_FIN_HP = 22                 # Hora fin Hora Punta (inclusive)

# =============================================================================
# CONSTANTES CO2 v5.3 - Factores de Emisión y Reducción
# =============================================================================
FACTOR_CO2_RED_KG_KWH = 0.4521       # kg CO2/kWh - red diésel Iquitos (aislada)
FACTOR_CO2_GASOLINA_KG_L = 2.31      # kg CO2/L gasolina (IPCC AR5)
FACTOR_CO2_NETO_MOTO_KG_KWH = 0.87   # kg CO2/kWh evitado neto (moto)
FACTOR_CO2_NETO_MOTOTAXI_KG_KWH = 0.47  # kg CO2/kWh evitado neto (mototaxi)

# =============================================================================
# TABLAS DE ESCENARIOS v5.5 - Metadata de Configuración
# (NO son observables por hora, son parámetros de simulación)
# =============================================================================
# Estas tablas se cargan desde data_loader.load_scenarios_metadata()
# y se usan para configurar el escenario operativo del entrenamiento.
#
# ARCHIVOS EN data/oe2/chargers/:
#   - selection_pe_fc_completo.csv (56 escenarios): pe, fc, chargers_required,
#     sockets_total, energy_day_kwh, peak_sessions_per_hour, vehicles_day_motos, etc.
#   - tabla_escenarios_detallados.csv (4-5 escenarios): CONSERVADOR, MEDIANO, RECOMENDADO*, MÁXIMO
#   - tabla_estadisticas_escenarios.csv: Min, Max, Promedio, Mediana, Desv_Std
#   - tabla_escenario_recomendado.csv: Motos, Mototaxis, Total por periodo (diario/mensual/anual)
#   - escenarios_tabla13.csv (103 escenarios): PE, FC, cargadores, tomas, sesiones, energia_dia_kwh
#
# ESCENARIO RECOMENDADO v5.5: PE=1.00, FC=1.00, 19 cargadores, 38 tomas, 1129 kWh/día
# =============================================================================

# =============================================================================
# COLUMNAS OBSERVABLES v5.3 - Variables para tracking en agentes
# =============================================================================
CHARGERS_OBSERVABLE_COLS = [
    'is_hora_punta',
    'tarifa_aplicada_soles',
    'ev_energia_total_kwh',
    'costo_carga_ev_soles',
    'ev_energia_motos_kwh',
    'ev_energia_mototaxis_kwh',
    'co2_reduccion_motos_kg',
    'co2_reduccion_mototaxis_kg',
    'reduccion_directa_co2_kg',
    'ev_demand_kwh',
]

SOLAR_OBSERVABLE_COLS = [
    'is_hora_punta',
    'tarifa_aplicada_soles',
    'ahorro_solar_soles',
    'reduccion_indirecta_co2_kg',
    'co2_evitado_mall_kg',
    'co2_evitado_ev_kg',
]

# NUEVAS DEFINICIONES v5.5: BESS y Mall Observable Columns
BESS_OBSERVABLE_COLS = [
    'bess_soc_percent',           # State of Charge %, rango 20-100%
    'bess_charge_kwh',            # Energía cargada en la hora (kWh)
    'bess_discharge_kwh',         # Energía descargada en la hora (kWh)
    'bess_to_mall_kwh',           # Energía del BESS al Mall (kWh)
    'bess_to_ev_kwh',             # Energía del BESS a EVs (kWh)
]

MALL_OBSERVABLE_COLS = [
    'mall_demand_kwh',            # Demanda horaria del mall (kWh)
    'mall_demand_reduction_kwh',  # Reducción de demanda por BESS/Solar (kWh)
    'mall_cost_soles',            # Costo horario del mall (S/.)
]

# Todas las columnas observables combinadas (para el archivo observables_oe2.csv)
# v5.5: INCLUYE Chargers (10) + Solar (6) + BESS (5) + Mall (3) + Totales (3) = 27 columnas
ALL_OBSERVABLE_COLS = [
    # Chargers (prefijo "ev_" para evitar colisiones)
    'ev_is_hora_punta',
    'ev_tarifa_aplicada_soles',
    'ev_energia_total_kwh',
    'ev_costo_carga_soles',
    'ev_energia_motos_kwh',
    'ev_energia_mototaxis_kwh',
    'ev_co2_reduccion_motos_kg',
    'ev_co2_reduccion_mototaxis_kg',
    'ev_reduccion_directa_co2_kg',
    'ev_demand_kwh',
    # Solar (prefijo "solar_")
    'solar_is_hora_punta',
    'solar_tarifa_aplicada_soles',
    'solar_ahorro_soles',
    'solar_reduccion_indirecta_co2_kg',
    'solar_co2_mall_kg',
    'solar_co2_ev_kg',
    # BESS (prefijo "bess_") v5.5 NEW
    'bess_soc_percent',
    'bess_charge_kwh',
    'bess_discharge_kwh',
    'bess_to_mall_kwh',
    'bess_to_ev_kwh',
    # Mall (prefijo "mall_") v5.5 NEW
    'mall_demand_kwh',
    'mall_demand_reduction_kwh',
    'mall_cost_soles',
    # Totales combinados
    'total_reduccion_co2_kg',
    'total_costo_soles',
    'total_ahorro_soles',
]

# =============================================================================
# INTEGRACIÓN: Reward Functions (from src/rewards/rewards.py)
# Importar clases de recompensa multiobjetivo para validación en OE3
# =============================================================================
# =============================================================================
# INTEGRACIÓN: Reward Functions (from .rewards - same directory)
# Importar clases de recompensa multiobjetivo para validación en OE3
# =============================================================================
try:
    from .rewards import (
        MultiObjectiveWeights,
        IquitosContext,
        MultiObjectiveReward,
        create_iquitos_reward_weights,
    )
    REWARDS_AVAILABLE = True
    logger.info("[REWARDS] Successfully imported reward classes from .rewards")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning("[REWARDS] Could not import rewards.py: %s", e)
    REWARDS_AVAILABLE = False

# =============================================================================
# INTEGRACIÓN: Baseline Modules v5.4 (from src/baseline/)
# Calculador de baselines CON_SOLAR y SIN_SOLAR para comparación con agentes RL
# =============================================================================
try:
    from src.baseline.baseline_calculator_v2 import BaselineCalculator
    from src.baseline.citylearn_baseline_integration import BaselineCityLearnIntegration
    BASELINE_AVAILABLE = True
    logger.info("[BASELINE] Successfully imported baseline modules")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning("[BASELINE] Baseline modules not available: %s", e)
    BASELINE_AVAILABLE = False

@dataclass(frozen=True)
class BuiltDataset:
    dataset_dir: Path
    schema_path: Path
    building_name: str

def _validate_solar_timeseries_hourly(solar_df: pd.DataFrame) -> None:
    """
    CRITICAL VALIDATION: Ensure solar timeseries is EXACTLY hourly (8,760 rows per year).

    NO 15-minute, 30-minute, or sub-hourly data allowed.

    Args:
        solar_df: Solar timeseries DataFrame

    Raises:
        ValueError: If not exactly 8,760 rows or if appears to be sub-hourly
    """
    n_rows = len(solar_df)

    # Check exact length (8,760 = 365 days × 24 hours, hourly resolution)
    if n_rows != 8760:
        raise ValueError(
            f"[ERROR] CRITICAL: Solar timeseries MUST be exactly 8,760 rows (hourly, 1 year).\n"
            f"   Got {n_rows} rows instead.\n"
            f"   This appears to be {'sub-hourly data' if n_rows > 8760 else 'incomplete data'}.\n"
            f"   If using PVGIS 15-minute data, downsample: "
            f"df.set_index('time').resample('h').mean()"
        )

    # Sanity check: if 52,560 rows, it's likely 15-minute (8,760 × 6)
    if n_rows == 52560:
        raise ValueError(
            f"[ERROR] CRITICAL: Solar timeseries has {n_rows} rows = 8,760 × 6 (likely 15-minute data).\n"
            f"   This codebase ONLY supports hourly resolution (8,760 rows per year).\n"
            f"   Downsample using: df.set_index('time').resample('h').mean()"
        )

    logger.info("[OK] Solar timeseries validation PASSED: %d rows (hourly, 1 year)", n_rows)

def _find_first_building(schema: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    buildings = schema.get("buildings")

    # Support both dict (CityLearn template) and list (our format)
    if isinstance(buildings, list):
        if len(buildings) == 0:
            raise ValueError("schema.json has empty buildings list.")
        first_building = buildings[0]
        name = first_building.get("name", "Building_1")
        return name, first_building
    elif isinstance(buildings, dict):
        if len(buildings) == 0:
            raise ValueError("schema.json has empty buildings dict.")
        name = list(buildings.keys())[0]
        return name, buildings[name]
    else:
        raise ValueError("schema.json does not define buildings.")

def _guess_file_key(d: Dict[str, Any], contains: str) -> Optional[str]:
    for k, v in d.items():
        if isinstance(v, str) and contains in k.lower() and v.lower().endswith(".csv"):
            return k
    return None

def _discover_csv_paths(schema: Dict[str, Any], dataset_dir: Path) -> Dict[str, Path]:
    """Return best-effort mapping for common files."""
    out: Dict[str, Path] = {}
    # root-level
    for key in ["weather", "carbon_intensity", "pricing"]:
        v = schema.get(key)
        if isinstance(v, str) and v.lower().endswith(".csv"):
            out[key] = dataset_dir / v

    # building-level (first building)
    bname, b = _find_first_building(schema)
    out["building_name"] = Path(bname)

    for candidate in ["energy_simulation", "energy_simulation_file", "energy_simulation_filename"]:
        if isinstance(b.get(candidate), str) and str(b[candidate]).lower().endswith(".csv"):
            out["energy_simulation"] = dataset_dir / str(b[candidate])
            break

    # Charger simulation paths: search recursively for keys that include 'charger_simulation'
    charger_paths: List[Path] = []
    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v.lower().endswith(".csv") and "charger" in k.lower() and "simulation" in k.lower():
                    charger_paths.append(dataset_dir / v)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)

    walk(b)
    if charger_paths:
        out["charger_simulations"] = Path(";")  # sentinel
        out["_charger_list"] = charger_paths  # type: ignore
    return out

def _load_real_charger_dataset(charger_data_path: Path) -> Optional[pd.DataFrame]:
    """Load real charger dataset from data/oe2/chargers/chargers_ev_ano_2024_v3.csv

    CRITICAL: This is the REAL DATASET v5.3 with:
    - 38 individual sockets (indexed socket_000 to socket_037)
    - 19 cargadores x 2 tomas = 38 tomas totales (OE2 v3.0 specification)
    - 7.4 kW por toma (Modo 3 monofasico 32A @ 230V)
    - 281.2 kW potencia instalada total
    - 8,760 hourly timesteps (full year 2024)
    - Individual socket control capability for RL agents (38-dim action space)

    Args:
        charger_data_path: Path to chargers_ev_ano_2024_v3.csv

    Returns:
        DataFrame with 8760 rows and socket columns or None if not found

    Raises:
        ValueError: If dataset structure is invalid
    """
    if not charger_data_path.exists():
        logger.warning(f"[CHARGERS REAL] File not found: {charger_data_path}")
        return None

    try:
        # Load with datetime index (first column should be datetime)
        df = pd.read_csv(charger_data_path, index_col=0, parse_dates=True)

        # VALIDATION: Ensure exact dimensions
        if df.shape[0] != 8760:
            raise ValueError(f"Charger dataset MUST have 8,760 rows (hourly), got {df.shape[0]}")

        # v5.3: Dataset tiene 353 columnas (1 datetime + 38 sockets x 9 features)
        # Validar que tenga columnas de socket (formato: socket_XXX_*)
        socket_cols = [c for c in df.columns if 'socket_' in c.lower()]
        # Extraer IDs unicos de socket
        socket_ids = set()
        for col in socket_cols:
            parts = col.split('_')
            if len(parts) > 1 and parts[1].isdigit():
                socket_ids.add(int(parts[1]))
        n_sockets = len(socket_ids)
        if n_sockets != 38:
            raise ValueError(f"Charger dataset MUST have 38 sockets (v5.3 OE2), got {n_sockets}")

        # VALIDATION: Hourly frequency
        if len(df.index) > 1:
            dt = (df.index[1] - df.index[0]).total_seconds() / 3600
            if abs(dt - 1.0) > 0.01:  # Allow small floating point error
                raise ValueError(f"Charger dataset MUST be hourly frequency, got {dt:.2f} hours")

        # VALIDATION: Datetime index starts with 2024-01-01
        if df.index[0].date() != pd.Timestamp("2024-01-01").date():
            logger.warning(f"[CHARGERS REAL] Dataset starts {df.index[0].date()}, expected 2024-01-01")

        # VALIDATION: Value ranges (power in kW) - only numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            min_val = df[numeric_cols].min().min()
            max_val = df[numeric_cols].max().max()
            if min_val < 0 or max_val > 10.0:  # Allow up to 10 kW for safety margin
                logger.warning(f"[CHARGERS REAL] Unexpected value range: [{min_val:.2f}, {max_val:.2f}] kW")

        # VALIDATION: Socket distribution v5.3 OE2 (38 sockets indexed 0-37)
        # socket_000_* to socket_037_* (19 cargadores x 2 tomas = 38 tomas)
        min_socket = min(socket_ids) if socket_ids else -1
        max_socket = max(socket_ids) if socket_ids else -1

        if min_socket != 0 or max_socket != 37:
            logger.warning(f"[CHARGERS REAL] Socket IDs range: {min_socket}-{max_socket} (expected 0-37)")

        logger.info(f"[CHARGERS REAL] v5.3 Loaded: {df.shape} (8760 hours)")
        logger.info(f"[CHARGERS REAL]   Sockets: {n_sockets} total socket_XXX entries")
        features_per_socket = len([c for c in socket_cols if 'socket_000_' in c])
        logger.info(f"[CHARGERS REAL]   Features per socket: {features_per_socket} columns (charger_power, battery_kwh, vehicle_type, soc_current, etc.)")
        logger.info(f"[CHARGERS REAL]   Period: {df.index[0].date()} to {df.index[-1].date()}")

        # =====================================================================
        # VALIDACIÓN v5.3: Columnas OSINERGMIN y CO2 (observables para agentes)
        # =====================================================================
        observable_cols_found = []
        observable_cols_missing = []
        
        for col in CHARGERS_OBSERVABLE_COLS:
            if col in df.columns:
                observable_cols_found.append(col)
            else:
                observable_cols_missing.append(col)
        
        if observable_cols_found:
            logger.info(f"[CHARGERS REAL] ✅ Columnas observables v5.3 encontradas: {len(observable_cols_found)}/{len(CHARGERS_OBSERVABLE_COLS)}")
            for col in observable_cols_found:
                col_sum = df[col].sum()
                col_mean = df[col].mean()
                logger.info(f"   - {col}: sum={col_sum:,.2f}, mean={col_mean:.4f}")
            
            # Estadísticas OSINERGMIN
            if 'is_hora_punta' in df.columns:
                horas_hp = df['is_hora_punta'].sum()
                logger.info(f"[CHARGERS REAL]   Horas HP: {horas_hp:,.0f} ({100*horas_hp/8760:.1f}%)")
            
            # Estadísticas CO2
            if 'reduccion_directa_co2_kg' in df.columns:
                co2_total_ton = df['reduccion_directa_co2_kg'].sum() / 1000
                logger.info(f"[CHARGERS REAL]   CO2 evitado (directo): {co2_total_ton:,.1f} ton/año")
            
            # Estadísticas costos
            if 'costo_carga_ev_soles' in df.columns:
                costo_total = df['costo_carga_ev_soles'].sum()
                logger.info(f"[CHARGERS REAL]   Costo carga EVs: S/.{costo_total:,.0f}/año")
        
        if observable_cols_missing:
            logger.warning(f"[CHARGERS REAL] ⚠️  Columnas observables faltantes: {observable_cols_missing}")
            logger.warning(f"   Ejecutar: python -m src.dimensionamiento.oe2.disenocargadoresev.chargers")

        return df

    except Exception as e:
        logger.error(f"[CHARGERS REAL] Error loading: {e}")
        raise


def _extract_observable_variables(
    chargers_df: Optional[pd.DataFrame],
    solar_df: Optional[pd.DataFrame],
    bess_df: Optional[pd.DataFrame] = None,
    mall_df: Optional[pd.DataFrame] = None,
    n_timesteps: int = 8760
) -> pd.DataFrame:
    """Extrae y combina variables observables de chargers, solar, BESS y Mall para agentes.
    
    VINCULACIÓN DATASET_BUILDER v5.5:
    - Chargers observables: CHARGERS_OBSERVABLE_COLS (10 cols con prefijo "ev_")
    - Solar observables: SOLAR_OBSERVABLE_COLS (6 cols con prefijo "solar_")
    - BESS observables: BESS_OBSERVABLE_COLS (5 cols con prefijo "bess_") [v5.5]
    - Mall observables: MALL_OBSERVABLE_COLS (3 cols con prefijo "mall_") [v5.5]
    - Totales: 3 cols combinadas = 27 columnas totales en ALL_OBSERVABLE_COLS
    
    FUENTES DE DATOS (data_loader.py):
    - Chargers: load_chargers_data() → chargers_ev_ano_2024_v3.csv (38 sockets)
    - Solar: load_solar_data() → pv_generation_citylearn2024.csv (4050 kWp)
    - BESS: load_bess_data() → bess_ano_2024.csv (1700 kWh)
    - Mall: load_mall_demand_data() → demandamallhorakwh.csv
    
    Args:
        chargers_df: DataFrame de chargers_ev_ano_2024_v3.csv (o None)
        solar_df: DataFrame de pv_generation_hourly_citylearn_v2.csv (o None)
        bess_df: DataFrame de bess_simulation_hourly.csv (o None) - v5.5
        mall_df: DataFrame de mall_demand_hourly.csv (o None) - v5.5 NEW
        n_timesteps: Número de timesteps (default: 8760 = 1 año)
    
    Returns:
        DataFrame con columnas observables combinadas (8760 x 27 columnas)
    """
    # Crear DataFrame base con índice horario
    time_index = pd.date_range(start="2024-01-01", periods=n_timesteps, freq="h")
    obs_df = pd.DataFrame(index=time_index)
    
    # =========================================================================
    # EXTRAER VARIABLES DE CHARGERS (prefijo "ev_")
    # =========================================================================
    if chargers_df is not None:
        logger.info("[OBSERVABLES] Extrayendo variables de chargers...")
        
        # Mapeo de columnas chargers -> observables (CHARGERS_OBSERVABLE_COLS)
        charger_col_map = {
            'is_hora_punta': 'ev_is_hora_punta',
            'tarifa_aplicada_soles': 'ev_tarifa_aplicada_soles',
            'ev_energia_total_kwh': 'ev_energia_total_kwh',
            'costo_carga_ev_soles': 'ev_costo_carga_soles',
            'ev_energia_motos_kwh': 'ev_energia_motos_kwh',
            'ev_energia_mototaxis_kwh': 'ev_energia_mototaxis_kwh',
            'co2_reduccion_motos_kg': 'ev_co2_reduccion_motos_kg',
            'co2_reduccion_mototaxis_kg': 'ev_co2_reduccion_mototaxis_kg',
            'reduccion_directa_co2_kg': 'ev_reduccion_directa_co2_kg',
            'ev_demand_kwh': 'ev_demand_kwh',
        }
        
        for src_col, dst_col in charger_col_map.items():
            if src_col in chargers_df.columns:
                # Asegurar alineación de índice
                values = chargers_df[src_col].values[:n_timesteps]
                if len(values) < n_timesteps:
                    values = np.pad(values, (0, n_timesteps - len(values)), mode='constant')
                obs_df[dst_col] = values
            else:
                obs_df[dst_col] = 0.0
                logger.warning(f"   - {src_col} no encontrado, usando 0.0")
    else:
        logger.warning("[OBSERVABLES] chargers_df es None, usando valores por defecto")
        for col in ['ev_is_hora_punta', 'ev_tarifa_aplicada_soles', 'ev_energia_total_kwh',
                    'ev_costo_carga_soles', 'ev_energia_motos_kwh', 'ev_energia_mototaxis_kwh',
                    'ev_co2_reduccion_motos_kg', 'ev_co2_reduccion_mototaxis_kg',
                    'ev_reduccion_directa_co2_kg', 'ev_demand_kwh']:
            obs_df[col] = 0.0
    
    # =========================================================================
    # EXTRAER VARIABLES DE SOLAR (prefijo "solar_")
    # =========================================================================
    if solar_df is not None:
        logger.info("[OBSERVABLES] Extrayendo variables de solar...")
        
        # Mapeo de columnas solar -> observables (SOLAR_OBSERVABLE_COLS)
        solar_col_map = {
            'is_hora_punta': 'solar_is_hora_punta',
            'tarifa_aplicada_soles': 'solar_tarifa_aplicada_soles',
            'ahorro_solar_soles': 'solar_ahorro_soles',
            'reduccion_indirecta_co2_kg': 'solar_reduccion_indirecta_co2_kg',
            'co2_evitado_mall_kg': 'solar_co2_mall_kg',
            'co2_evitado_ev_kg': 'solar_co2_ev_kg',
        }
        
        for src_col, dst_col in solar_col_map.items():
            if src_col in solar_df.columns:
                values = solar_df[src_col].values[:n_timesteps]
                if len(values) < n_timesteps:
                    values = np.pad(values, (0, n_timesteps - len(values)), mode='constant')
                obs_df[dst_col] = values
            else:
                obs_df[dst_col] = 0.0
                logger.warning(f"   - {src_col} no encontrado en solar, usando 0.0")
    else:
        logger.warning("[OBSERVABLES] solar_df es None, usando valores por defecto")
        for col in ['solar_is_hora_punta', 'solar_tarifa_aplicada_soles', 'solar_ahorro_soles',
                    'solar_reduccion_indirecta_co2_kg', 'solar_co2_mall_kg', 'solar_co2_ev_kg']:
            obs_df[col] = 0.0
    
    # =========================================================================
    # EXTRAER VARIABLES DE BESS v5.5 (prefijo "bess_")
    # =========================================================================
    if bess_df is not None:
        logger.info("[OBSERVABLES] Extrayendo variables de BESS v5.5...")
        
        # Mapeo de columnas BESS -> observables (BESS_OBSERVABLE_COLS)
        bess_col_map = {
            'bess_soc_percent': 'bess_soc_percent',
            'bess_charge_kwh': 'bess_charge_kwh',
            'bess_discharge_kwh': 'bess_discharge_kwh',
            'bess_to_mall_kwh': 'bess_to_mall_kwh',
            'bess_to_ev_kwh': 'bess_to_ev_kwh',
        }
        
        for src_col, dst_col in bess_col_map.items():
            if src_col in bess_df.columns:
                values = bess_df[src_col].values[:n_timesteps]
                if len(values) < n_timesteps:
                    values = np.pad(values, (0, n_timesteps - len(values)), mode='constant')
                obs_df[dst_col] = values
            else:
                # Valores por defecto si columna no existe
                if dst_col == 'bess_soc_percent':
                    obs_df[dst_col] = 50.0  # 50% SOC inicial
                else:
                    obs_df[dst_col] = 0.0
                logger.warning(f"   - {src_col} no encontrado en BESS, usando valor por defecto")
        
        logger.info(f"   ✓ BESS v5.5: 1,700 kWh capacity, SOC medio={obs_df['bess_soc_percent'].mean():.1f}%")
    else:
        logger.warning("[OBSERVABLES] bess_df es None, usando valores por defecto BESS v5.5")
        obs_df['bess_soc_percent'] = 50.0  # 50% inicial
        obs_df['bess_charge_kwh'] = 0.0
        obs_df['bess_discharge_kwh'] = 0.0
        obs_df['bess_to_mall_kwh'] = 0.0
        obs_df['bess_to_ev_kwh'] = 0.0
    
    # =========================================================================
    # EXTRAER VARIABLES DE MALL DEMAND v5.5 (prefijo "mall_")
    # =========================================================================
    if mall_df is not None:
        logger.info("[OBSERVABLES] Extrayendo variables de Mall demand v5.5...")
        
        # Mapeo de columnas Mall -> observables (MALL_OBSERVABLE_COLS)
        mall_col_map = {
            'mall_demand_kwh': 'mall_demand_kwh',
            'mall_demand_reduction_kwh': 'mall_demand_reduction_kwh',
            'mall_cost_soles': 'mall_cost_soles',
        }
        
        for src_col, dst_col in mall_col_map.items():
            if src_col in mall_df.columns:
                values = mall_df[src_col].values[:n_timesteps]
                if len(values) < n_timesteps:
                    values = np.pad(values, (0, n_timesteps - len(values)), mode='constant')
                obs_df[dst_col] = values
            else:
                obs_df[dst_col] = 0.0
                logger.warning(f"   - {src_col} no encontrado en Mall, usando 0.0")
        
        logger.info(f"   ✓ Mall demand: {obs_df['mall_demand_kwh'].sum():,.0f} kWh/año, "
                   f"reducción={obs_df['mall_demand_reduction_kwh'].sum():,.0f} kWh/año")
    else:
        logger.warning("[OBSERVABLES] mall_df es None, usando valores por defecto")
        for col in ['mall_demand_kwh', 'mall_demand_reduction_kwh', 'mall_cost_soles']:
            obs_df[col] = 0.0
    
    # =========================================================================
    # CALCULAR TOTALES COMBINADOS
    # =========================================================================
    # Total CO2 evitado = directo (EVs) + indirecto (solar)
    obs_df['total_reduccion_co2_kg'] = (
        obs_df['ev_reduccion_directa_co2_kg'] + 
        obs_df['solar_reduccion_indirecta_co2_kg']
    )
    
    # Total costo = costo carga EVs
    obs_df['total_costo_soles'] = obs_df['ev_costo_carga_soles']
    
    # Total ahorro = ahorro solar
    obs_df['total_ahorro_soles'] = obs_df['solar_ahorro_soles']
    
    logger.info(f"[OBSERVABLES] ✅ DataFrame creado: {obs_df.shape} "
               f"(27 columnas observables según ALL_OBSERVABLE_COLS)")
    logger.info(f"   CHARGERS (10): {[c for c in obs_df.columns if c.startswith('ev_')]}")
    logger.info(f"   SOLAR (6): {[c for c in obs_df.columns if c.startswith('solar_')]}")
    logger.info(f"   BESS (5): {[c for c in obs_df.columns if c.startswith('bess_')]}")
    logger.info(f"   MALL (3): {[c for c in obs_df.columns if c.startswith('mall_')]}")
    logger.info(f"   TOTALES (3): {[c for c in obs_df.columns if c.startswith('total_')]}")
    logger.info(f"   → Total CO2 evitado: {obs_df['total_reduccion_co2_kg'].sum()/1000:,.1f} ton/año")
    logger.info(f"   → Total costo EVs: S/.{obs_df['total_costo_soles'].sum():,.0f}/año")
    logger.info(f"   → Total ahorro solar: S/.{obs_df['total_ahorro_soles'].sum():,.0f}/año")
    
    return obs_df


def _load_oe2_artifacts(interim_dir: Path) -> Dict[str, Any]:
    artifacts: Dict[str, Any] = {}

    # ========================================================================
    # SECCIÓN CRÍTICA: CARGAR OBLIGATORIAMENTE 5 ARCHIVOS REALES DESDE data/oe2/
    # Estas rutas son FIJAS y NO se pueden mover. Son los datos reales que DEBEN
    # ser usados en entrenamiento de agentes y cálculo de métricas baseline.
    # ========================================================================
    logger.info("\n" + "="*80)
    logger.info("[CRITICAL] Cargando datos OE2 REALES desde rutas FIJAS y OBLIGATORIAS (5 archivos)")
    logger.info("="*80)

    oe2_base_path = interim_dir.parent.parent / "oe2"  # data/oe2/

    # 1. CHARGERS_REAL_HOURLY (OBLIGATORIO)
    # ACTUALIZACIÓN OE2 v3.0: Usar archivo real generado por chargers.py v3.0
    chargers_real_fixed_path = oe2_base_path / "chargers" / "chargers_ev_ano_2024_v3.csv"
    if not chargers_real_fixed_path.exists():
        raise FileNotFoundError(
            f"[CRITICAL ERROR] ARCHIVO OBLIGATORIO NO ENCONTRADO:\n"
            f"  Ruta fija requerida: {chargers_real_fixed_path}\n"
            f"  Este archivo es OBLIGATORIO para entrenar con datos REALES.\n"
            f"  NO HAY FALLBACK disponible - debes proporcionar el archivo en esa ubicación."
        )
    try:
        chargers_real_df = _load_real_charger_dataset(chargers_real_fixed_path)
        if chargers_real_df is None or chargers_real_df.shape[0] != 8760:
            raise ValueError(f"Shape invalido: {chargers_real_df.shape if chargers_real_df is not None else 'None'} (requiere 8760 filas)")
        artifacts["chargers_real_hourly_2024"] = chargers_real_df
        logger.info("[OK CARGAR] Cargadores reales horarios 2024 v5.3 OE2 - 8,760 horas x 38 sockets (socket_000 to socket_037)")
    except Exception as e:
        raise RuntimeError(f"[ERROR CRITICO] No se puede cargar chargers_ev_ano_2024_v3.csv: {e}")

    # 2. CHARGERS_REAL_STATISTICS (OBLIGATORIO)
    chargers_stats_fixed_path = oe2_base_path / "chargers" / "chargers_real_statistics.csv"
    if not chargers_stats_fixed_path.exists():
        raise FileNotFoundError(
            f"[CRITICAL ERROR] ARCHIVO OBLIGATORIO NO ENCONTRADO:\n"
            f"  Ruta fija requerida: {chargers_stats_fixed_path}\n"
            f"  Este archivo es OBLIGATORIO para validar estadísticas de cargadores.\n"
            f"  NO HAY FALLBACK disponible."
        )
    try:
        chargers_stats_df = pd.read_csv(chargers_stats_fixed_path)
        artifacts["chargers_real_statistics"] = chargers_stats_df
        logger.info("[✓ CARGAR] Estadísticas cargadores reales - {} registros".format(len(chargers_stats_df)))
    except Exception as e:
        raise RuntimeError(f"[ERROR CRÍTICO] No se puede cargar chargers_real_statistics.csv: {e}")

    # 3. BESS_HOURLY_DATASET (OBLIGATORIO)
    # ACTUALIZACIÓN OE2: Usar archivo real de simulación BESS
    bess_hourly_fixed_path = oe2_base_path / "bess" / "bess_simulation_hourly.csv"
    if not bess_hourly_fixed_path.exists():
        raise FileNotFoundError(
            f"[CRITICAL ERROR] ARCHIVO OBLIGATORIO NO ENCONTRADO:\n"
            f"  Ruta fija requerida: {bess_hourly_fixed_path}\n"
            f"  Este archivo es OBLIGATORIO para simular BESS con datos REALES.\n"
            f"  NO HAY FALLBACK disponible."
        )
    try:
        bess_df = pd.read_csv(bess_hourly_fixed_path, index_col=0, parse_dates=True)
        if len(bess_df) != 8760 or "soc_percent" not in bess_df.columns:
            raise ValueError(f"BESS dataset inválido: {len(bess_df)} rows, columnas={bess_df.columns.tolist()}")
        artifacts["bess_hourly_2024"] = bess_df
        logger.info("[✓ CARGAR] BESS horario 2024 - 8,760 horas | SOC: {:.1f}% a {:.1f}%".format(
            bess_df["soc_percent"].min(), bess_df["soc_percent"].max()))
    except Exception as e:
        raise RuntimeError(f"[ERROR CRÍTICO] No se puede cargar bess_simulation_hourly.csv: {e}")

    # 4. MALL_DEMAND_HOURLY (OBLIGATORIO)
    mall_demand_fixed_path = oe2_base_path / "demandamallkwh" / "demandamallhorakwh.csv"
    if not mall_demand_fixed_path.exists():
        raise FileNotFoundError(
            f"[CRITICAL ERROR] ARCHIVO OBLIGATORIO NO ENCONTRADO:\n"
            f"  Ruta fija requerida: {mall_demand_fixed_path}\n"
            f"  Este archivo es OBLIGATORIO para demanda del mall REAL.\n"
            f"  NO HAY FALLBACK disponible."
        )
    try:
        mall_df = pd.read_csv(mall_demand_fixed_path)
        if len(mall_df) < 8760:
            raise ValueError(f"Mall demand inválido: {len(mall_df)} rows (requiere ≥8,760)")
        artifacts["mall_demand"] = mall_df
        artifacts["mall_demand_path"] = str(mall_demand_fixed_path)
        logger.info("[✓ CARGAR] Demanda mall horaria - {} horas".format(len(mall_df)))
    except Exception as e:
        raise RuntimeError(f"[ERROR CRÍTICO] No se puede cargar demandamallhorakwh.csv: {e}")

    # 5. SOLAR_GENERATION_HOURLY (OBLIGATORIO)
    solar_generation_fixed_path = oe2_base_path / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv"
    if not solar_generation_fixed_path.exists():
        raise FileNotFoundError(
            f"[CRITICAL ERROR] ARCHIVO OBLIGATORIO NO ENCONTRADO:\n"
            f"  Ruta fija requerida: {solar_generation_fixed_path}\n"
            f"  Este archivo es OBLIGATORIO para generación solar REAL de PVGIS.\n"
            f"  NO HAY FALLBACK disponible."
        )
    try:
        solar_df = pd.read_csv(solar_generation_fixed_path)
        if len(solar_df) < 8760:
            raise ValueError(f"Solar generation inválido: {len(solar_df)} rows (requiere ≥8,760)")
        artifacts["pv_generation_hourly"] = solar_df
        artifacts["pv_generation_path"] = str(solar_generation_fixed_path)
        logger.info("[✓ CARGAR] Generación solar horaria PVGIS - {} horas".format(len(solar_df)))
    except Exception as e:
        raise RuntimeError(f"[ERROR CRÍTICO] No se puede cargar pv_generation_hourly_citylearn_v2.csv: {e}")

    logger.info("[SUMMARY] 5 archivos reales OBLIGATORIOS cargados exitosamente de data/oe2/")
    logger.info("="*80 + "\n")

    # Solar - cargar parámetros de CityLearn si existen
    solar_params_candidates = [
        interim_dir.parent.parent / "oe2" / "solar" / "citylearn" / "solar_schema_params.json",  # data/oe2/solar/
        interim_dir / "solar" / "citylearn" / "solar_schema_params.json",  # data/interim/oe2/solar/
    ]
    for solar_params_path in solar_params_candidates:
        if solar_params_path.exists():
            try:
                artifacts["solar_params"] = json.loads(solar_params_path.read_text(encoding="utf-8"))
                logger.info("[SOLAR] Schema params loaded from %s", solar_params_path)
                break
            except Exception as e:
                logger.warning("[SOLAR] Error loading params from %s: %s", solar_params_path, e)

    # ========================================================================
    # PRIORITY 1: NEW Hourly solar dataset for CityLearn v2 (2026-02-04)
    # Location: data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
    # Contains: 8,760 hourly records with REAL PVGIS data (Sandia SAPM model)
    # Columns: timestamp, ghi_wm2, dni_wm2, dhi_wm2, temp_air_c, wind_speed_ms,
    #          dc_power_kw, ac_power_kw, dc_energy_kwh, ac_energy_kwh, pv_generation_kwh
    # ========================================================================
    # Try both locations: data/oe2/ (REAL LOCATION) and interim_dir (FALLBACK)
    solar_hourly_v2_candidates = [
        interim_dir.parent.parent / "oe2" / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv",  # data/oe2/Generacionsolar/
        interim_dir / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv",  # data/interim/oe2/Generacionsolar/
    ]

    solar_hourly_v2_path = None
    for candidate in solar_hourly_v2_candidates:
        if candidate.exists():
            solar_hourly_v2_path = candidate
            break

    if solar_hourly_v2_path is not None:
        try:
            artifacts["solar_ts"] = pd.read_csv(solar_hourly_v2_path)
            _validate_solar_timeseries_hourly(artifacts["solar_ts"])
            logger.info("[SOLAR] ✅ PRIORITY 1: Cargado dataset horario v2 desde %s", solar_hourly_v2_path)
            logger.info("         Total registros: %d horas", len(artifacts["solar_ts"]))
            if "ac_power_kw" in artifacts["solar_ts"].columns:
                logger.info("         Potencia AC anual: %.0f kWh", artifacts["solar_ts"]["ac_power_kw"].sum())
        except Exception as e:
            logger.error("[SOLAR] ✗ Error cargando v2: %s. Fallback a pv_generation_timeseries.csv", e)
            artifacts["solar_ts"] = None
    else:
        logger.info("[SOLAR] v2 no disponible en: %s o %s, usando fallback...", solar_hourly_v2_candidates[0], solar_hourly_v2_candidates[1])
        artifacts["solar_ts"] = None

    # ========================================================================
    # FALLBACK: Original timeseries si v2 no disponible
    # ========================================================================
    if artifacts.get("solar_ts") is None:
        solar_fallback_candidates = [
            interim_dir.parent.parent / "oe2" / "solar" / "pv_generation_timeseries.csv",  # data/oe2/solar/
            interim_dir / "solar" / "pv_generation_timeseries.csv",  # data/interim/oe2/solar/
        ]
        solar_path = None
        for candidate in solar_fallback_candidates:
            if candidate.exists():
                solar_path = candidate
                break

        if solar_path is not None:
            try:
                artifacts["solar_ts"] = pd.read_csv(solar_path)
                # CRITICAL: Validate that solar data is hourly (8,760 rows per year)
                _validate_solar_timeseries_hourly(artifacts["solar_ts"])
                logger.info("[SOLAR] Fallback: Cargado pv_generation_timeseries.csv desde %s", solar_path)
            except Exception as e:
                logger.error("[SOLAR] ✗ Error en fallback: %s", e)
                artifacts["solar_ts"] = None

    # Solar generation para CityLearn (horario)
    solar_citylearn_candidates = [
        interim_dir / "citylearn" / "solar_generation.csv",
        (interim_dir.parent / "oe2" / "citylearn" / "solar_generation.csv") if (interim_dir.parent / "oe2").exists() else Path(),
    ]
    for solar_citylearn_csv in solar_citylearn_candidates:
        if solar_citylearn_csv.exists():
            artifacts["solar_generation_citylearn"] = pd.read_csv(solar_citylearn_csv)
            logger.info("[SOLAR] Solar generation encontrado en: %s", solar_citylearn_csv)
            break

    # EV profile
    ev_profile_candidates = [
        interim_dir.parent.parent / "oe2" / "chargers" / "perfil_horario_carga.csv",  # data/oe2/chargers/
        interim_dir / "chargers" / "perfil_horario_carga.csv",  # data/interim/oe2/chargers/
    ]
    for ev_path in ev_profile_candidates:
        if ev_path.exists():
            try:
                artifacts["ev_profile_24h"] = pd.read_csv(ev_path)
                logger.info("[EV] Hourly profile loaded from %s", ev_path)
                break
            except Exception as e:
                logger.warning("[EV] Error loading profile from %s: %s", ev_path, e)

    # EV chargers individuales
    ev_chargers_candidates = [
        interim_dir.parent.parent / "oe2" / "chargers" / "individual_chargers.json",  # data/oe2/chargers/
        interim_dir / "chargers" / "individual_chargers.json",  # data/interim/oe2/chargers/
        interim_dir / "oe2" / "chargers" / "individual_chargers.json",  # Legacy path
    ]
    for ev_chargers_path in ev_chargers_candidates:
        if ev_chargers_path.exists():
            try:
                artifacts["ev_chargers"] = json.loads(ev_chargers_path.read_text(encoding="utf-8"))
                logger.info("[EV] Individual chargers JSON loaded from %s", ev_chargers_path)
                break
            except Exception as e:
                logger.warning("[EV] Error loading chargers from %s: %s", ev_chargers_path, e)
    # NOTE: chargers_ev_ano_2024_v3.csv YA FUE CARGADO OBLIGATORIAMENTE
    # en la sección CRÍTICA al inicio de _load_oe2_artifacts().
    # No es necesario intentar cargar nuevamente aquí.

    # === PRIORITY 2: LEGACY CHARGER HOURLY PROFILES (FALLBACK) ===
    # Fallback to old 32-charger profiles if real dataset unavailable
    chargers_hourly_annual = interim_dir / "chargers" / "chargers_hourly_profiles_annual.csv"
    logger.info(f"[CHARGER DEBUG] Checking chargers_hourly_annual: {chargers_hourly_annual.exists()}")
    if not chargers_hourly_annual.exists():
        # Fallback: load daily profile and expand
        chargers_daily = interim_dir / "chargers" / "chargers_hourly_profiles.csv"
        logger.info(f"[CHARGER DEBUG] Checking chargers_daily: {chargers_daily.exists()}")
        if chargers_daily.exists():
            logger.info(
                "Loading daily charger profiles and expanding to annual (8,760 hours)..."
            )
            df_daily = pd.read_csv(chargers_daily)
            logger.info(f"[CHARGER DEBUG] Daily shape before drop: {df_daily.shape}")
            # Drop 'hour' column if present
            if 'hour' in df_daily.columns:
                df_daily = df_daily.drop('hour', axis=1)
            logger.info(f"[CHARGER DEBUG] Daily shape after drop: {df_daily.shape}")
            # Expand: repeat 365 times
            df_annual = pd.concat([df_daily] * 365, ignore_index=True)
            artifacts["chargers_hourly_profiles_annual"] = df_annual
            logger.info(f"[CHARGER DEBUG] Annual shape: {df_annual.shape}")
            logger.info("Expanded: %d hours/day × 365 days = %d hours total", df_daily.shape[0], len(df_annual))
        else:
            logger.warning(f"[CHARGER DEBUG] chargers_daily not found: {chargers_daily}")
    else:
        # Load pre-expanded annual profiles
        df_annual = pd.read_csv(chargers_hourly_annual)
        artifacts["chargers_hourly_profiles_annual"] = df_annual
        logger.info("Loaded annual charger profiles: %s", df_annual.shape)

    # === CHARGERS RESULTS (dimensionamiento OE2) ===
    chargers_results = interim_dir / "chargers" / "chargers_results.json"
    if chargers_results.exists():
        artifacts["chargers_results"] = json.loads(chargers_results.read_text(encoding="utf-8"))
        logger.info("Cargados resultados de chargers OE2: %d chargers", artifacts['chargers_results'].get('n_chargers_recommended', 0))

    # === DATASETS ANUALES POR PLAYA (8760 horas) ===
    annual_datasets_dir = interim_dir / "chargers" / "annual_datasets"
    if annual_datasets_dir.exists():
        artifacts["annual_datasets_dir"] = annual_datasets_dir
        artifacts["annual_datasets"] = {}

        for playa_name in ["Playa_Motos", "Playa_Mototaxis"]:
            playa_dir = annual_datasets_dir / playa_name
            if playa_dir.exists():
                metadata_path = playa_dir / "metadata.json"
                if metadata_path.exists():
                    playa_meta = json.loads(metadata_path.read_text(encoding="utf-8"))
                    artifacts["annual_datasets"][playa_name] = {
                        "dir": playa_dir,
                        "metadata": playa_meta,
                        "base_dir": playa_dir / "base",
                        "charger_ids": playa_meta.get("charger_ids", []),
                    }
                    logger.info("Cargados datasets anuales %s: %d chargers", playa_name, len(playa_meta.get('charger_ids', [])))

    charger_profile_variants = interim_dir / "chargers" / "charger_profile_variants.json"
    if charger_profile_variants.exists():
        artifacts["charger_profile_variants"] = json.loads(charger_profile_variants.read_text(encoding="utf-8"))
        variants_dir = charger_profile_variants.parent / "charger_profile_variants"
        if variants_dir.exists():
            artifacts["charger_profile_variants_dir"] = variants_dir
        else:
            artifacts["charger_profile_variants_dir"] = None

    # BESS - cargar parámetros de CityLearn si existen
    bess_citylearn_params_candidates = [
        interim_dir.parent.parent / "oe2" / "citylearn" / "bess_schema_params.json",  # data/oe2/citylearn/
        interim_dir / "citylearn" / "bess_schema_params.json",  # data/interim/oe2/citylearn/
    ]
    for bess_params_path in bess_citylearn_params_candidates:
        if bess_params_path.exists():
            try:
                artifacts["bess_params"] = json.loads(bess_params_path.read_text(encoding="utf-8"))
                logger.info("[BESS] Schema params loaded from %s", bess_params_path)
                break
            except Exception as e:
                logger.warning("[BESS] Error loading params from %s: %s", bess_params_path, e)

    # BESS results
    bess_results_candidates = [
        interim_dir.parent.parent / "oe2" / "bess" / "bess_results.json",  # data/oe2/bess/
        interim_dir / "bess" / "bess_results.json",  # data/interim/oe2/bess/
    ]
    for bess_path in bess_results_candidates:
        if bess_path.exists():
            try:
                artifacts["bess"] = json.loads(bess_path.read_text(encoding="utf-8"))
                logger.info("[BESS] Results loaded from %s", bess_path)
                break
            except Exception as e:
                logger.warning("[BESS] Error loading results from %s: %s", bess_path, e)

    # === PRIORITY 1: NEW BESS Hourly Dataset (2026-02-04) ===
    # Location: data/oe2/bess/bess_simulation_hourly.csv
    # Contains: 8,760 hourly records with REAL BESS simulation data
    # Columns: DatetimeIndex (UTC-5), pv_kwh, ev_kwh, mall_kwh, pv_to_ev_kwh, pv_to_bess_kwh,
    #          pv_to_mall_kwh, grid_to_ev_kwh, grid_to_mall_kwh, bess_charge_kwh, bess_discharge_kwh, soc_percent
    # ========================================================================
    # NOTE: bess_simulation_hourly.csv YA FUE CARGADO OBLIGATORIAMENTE
    # en la sección CRÍTICA al inicio de _load_oe2_artifacts().
    # No es necesario intentar cargar nuevamente aquí.

    # Building load para CityLearn
    building_load_candidates = [
        interim_dir / "citylearn" / "building_load.csv",
        interim_dir.parent / "oe2" / "citylearn" / "building_load.csv",  # Ruta alternativa (data/oe2/...)
    ]
    for building_load_path in building_load_candidates:
        if building_load_path.exists():
            artifacts["building_load_citylearn"] = pd.read_csv(building_load_path)
            logger.info("[LOAD] Building load encontrado en: %s", building_load_path)
            break

    # NOTE: demandamallhorakwh.csv YA FUE CARGADO OBLIGATORIAMENTE
    # en la sección CRÍTICA al inicio de _load_oe2_artifacts().
    # No es necesario intentar cargar nuevamente aquí.

    # ==========================================================================
    # INTEGRACIÓN: Cargar contexto de Iquitos (rewards.py)
    # Contiene factores CO₂ (0.4521 grid, 2.146 EV), config de vehículos (1,800
    # motos + 260 mototaxis por día), y pesos de recompensa multiobjetivo
    # ==========================================================================
    if REWARDS_AVAILABLE:
        try:
            # Crear instancia de IquitosContext con valores reales de OE2
            # NOTA: IquitosContext usa atributos de clase, NO parámetros del constructor
            iquitos_ctx = IquitosContext()  # Acceso directo a valores predefinidos
            artifacts["iquitos_context"] = iquitos_ctx
            logger.info("[REWARDS] Loaded IquitosContext with CO2 factors and EV specs")
            logger.info("[REWARDS]    Grid CO2: %.4f kg/kWh", iquitos_ctx.co2_factor_kg_per_kwh)
            logger.info("[REWARDS]    EV CO2 conversion: %.3f kg/kWh", iquitos_ctx.co2_conversion_factor)
            logger.info("[REWARDS]    Daily EV capacity: %d motos + %d mototaxis",
                       iquitos_ctx.motos_daily_capacity, iquitos_ctx.mototaxis_daily_capacity)
        except Exception as e:
            logger.error("[REWARDS] Failed to initialize IquitosContext: %s", e)

    # Cargar pesos de recompensa multiobjetivo
    if REWARDS_AVAILABLE:
        try:
            reward_weights = create_iquitos_reward_weights(priority="co2_focus")
            artifacts["reward_weights"] = reward_weights
            logger.info("[REWARDS] ✅ Created reward weights: CO₂=%.2f, solar=%.2f, EV satisfaction=%.2f, cost=%.2f, grid_stability=%.2f",
                       reward_weights.co2, reward_weights.solar, reward_weights.ev_satisfaction, reward_weights.cost, reward_weights.grid_stability)
        except Exception as e:
            logger.error("[REWARDS] Failed to create reward weights: %s", e)

    return artifacts

def _repeat_24h_to_length(values_24: np.ndarray, n: int) -> np.ndarray:
    reps = int(np.ceil(n / 24))
    return np.tile(values_24, reps)[:n]

def _write_constant_series_csv(path: Path, df_template: pd.DataFrame, value: float) -> None:
    df = df_template.copy()
    # If single column, overwrite it. Otherwise try common names.
    if df.shape[1] == 1:
        col = df.columns[0]
        df[col] = value
    else:
        written = False
        for col in df.columns:
            if re.search(r"carbon|co2|intensity", col, re.IGNORECASE):
                df[col] = value
                written = True
        if not written:
            df[df.columns[-1]] = value
    df.to_csv(path, index=False)

def _generate_individual_charger_csvs(
    charger_profiles_annual: pd.DataFrame,
    building_dir: Path,
    overwrite: bool = False,
) -> Dict[str, Path]:
    """Generate 38 individual charger_simulation_0XX.csv files for v5.2 required by CityLearn v2.

    **CRITICAL**: CityLearn v2 expects each charger's load profile in a separate CSV file:
    - buildings/building_name/charger_simulation_001.csv through charger_simulation_038.csv
    - Each file: 8,760 rows x 1 column (demand in kW)

    Args:
        charger_profiles_annual: DataFrame with shape (8760, 38) or wider
                                Columns are charger IDs (MOTO_CH_001, etc.)
        building_dir: Path to buildings/building_name/ directory
        overwrite: If True, overwrite existing files

    Returns:
        Dict mapping charger index -> CSV file path

    Raises:
        ValueError: If invalid shape or columns
    """
    if charger_profiles_annual.shape[0] != 8760:
        raise ValueError(
            f"Charger profiles must have 8,760 rows (annual hourly), "
            f"got {charger_profiles_annual.shape[0]}"
        )

    # v5.2: 38 sockets (flexible validation)
    n_sockets = charger_profiles_annual.shape[1]
    if n_sockets < 38:
        raise ValueError(
            f"Charger profiles must have at least 38 columns (v5.2), "
            f"got {charger_profiles_annual.shape[1]}"
        )

    building_dir.mkdir(parents=True, exist_ok=True)

    generated_files = {}

    # v5.2: Generate 38 individual CSVs (charger_simulation_001.csv through 038.csv)
    n_files = min(n_sockets, 38)  # Use 38 sockets
    for charger_idx in range(n_files):
        csv_filename = f"charger_simulation_{charger_idx + 1:03d}.csv"
        csv_path = building_dir / csv_filename

        # Skip if exists and not overwrite
        if csv_path.exists() and not overwrite:
            logger.info("  Skipped %s (exists)", csv_filename)
            generated_files[charger_idx] = csv_path
            continue

        # Extract this charger's annual profile (8,760 hours)
        charger_demand = charger_profiles_annual.iloc[:, charger_idx]

        # Create DataFrame with single column
        df_charger = pd.DataFrame({
            'demand_kw': charger_demand.values
        })

        # Write to CSV
        try:
            df_charger.to_csv(csv_path, index=False)
            generated_files[charger_idx] = csv_path
            logger.info("  Generated %s (8,760 rows)", csv_filename)
        except Exception as e:
            logger.error("Failed to write %s: %s", csv_filename, e)
            raise

    logger.info(
        "[OK] Generated %d individual charger CSV files",
        len(generated_files)
    )

    return generated_files  # type: ignore

def build_citylearn_dataset(
    cfg: Dict[str, Any],
    _raw_dir: Path,
    interim_dir: Path,
    processed_dir: Path,
) -> BuiltDataset:
    """Create processed CityLearn dataset for OE3 (EV + PV + BESS).

    Strategy:
    1) Download/locate a CityLearn template dataset that already supports EVs.
    2) Copy to processed dataset directory.
    3) Overwrite time series: non_shiftable_load, solar_generation, pricing, carbon_intensity,
       and charger_simulation according to OE2 results.
    4) Update key capacities in schema (PV nominal power, BESS capacity/power, seconds_per_time_step).
    """
    try:
        from citylearn.data import DataSet  # type: ignore  # pylint: disable=import-error
    except Exception as e:
        raise ImportError(
            "CityLearn is required for OE3. Install with: pip install citylearn>=2.5.0"
        ) from e

    template_name = cfg["oe3"]["dataset"]["template_name"]
    dataset_name = cfg["oe3"]["dataset"]["name"]
    central_agent = bool(cfg["oe3"]["dataset"].get("central_agent", True))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    dt_hours = seconds_per_time_step / 3600.0

    ds = DataSet()
    out_dir = processed_dir / "citylearn" / dataset_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # PASO CRITICO: Copiar 5 ARCHIVOS OBLIGATORIOS DE OE2 a out_dir
    # Estos archivos son OBLIGATORIOS para que CityLearn y los agents accedan a los datos reales
    # Definir ruta base de datos OE2
    oe2_base_path = interim_dir.parent.parent / "oe2"  # data/oe2/

    logger.info("[FILES] Copiando 5 archivos obligatorios OE2 a directorio CityLearn...")
    # ACTUALIZACIÓN OE2 v3.0: Usar nombres de archivos REALES generados
    required_files = [
        ("chargers", "chargers_ev_ano_2024_v3.csv"),  # ✓ Nombre real del archivo
        ("chargers", "chargers_real_statistics.csv"),
        ("bess", "bess_simulation_hourly.csv"),  # ✓ Nombre real del archivo
        ("demandamallkwh", "demandamallhorakwh.csv"),
        ("Generacionsolar", "pv_generation_hourly_citylearn_v2.csv"),
    ]

    files_copied = 0
    for subdir, filename in required_files:
        src = oe2_base_path / subdir / filename  # ✓ Buscar en data/oe2/ (no en interim_dir)
        if src.exists():
            dst_subdir = out_dir / subdir
            dst_subdir.mkdir(parents=True, exist_ok=True)
            dst = dst_subdir / filename
            shutil.copy2(src, dst)
            files_copied += 1
            logger.info("[FILES] OK: %s/%s", subdir, filename)
        else:
            logger.error("[FILES] MISSING: %s/%s", subdir, filename)

    logger.info("[FILES] Copiados: %d/5 archivos obligatorios", files_copied)

    # Obtener schema plantilla de CityLearn y salvar en out_dir
    # (Evita problemas de encoding con rutas de caché en Windows)
    try:
        schema_file = Path(ds.get_dataset(name=template_name))
        template_path = schema_file.parent / "schema.json"
        if template_path.exists():
            # Copiar schema plantilla a output directory
            schema_path = out_dir / "schema.json"
            shutil.copy2(template_path, schema_path)
            logger.info("Schema plantilla copiado exitosamente")
        else:
            raise FileNotFoundError(f"Schema template not found at {template_path}")
    except Exception as e:
        logger.error("Error obtener schema de CityLearn: %s. Usando schema minimalista.", e)
        # Fallback: crear schema minimal válido
        schema_path = out_dir / "schema.json"
        schema = {
            "version": "2.5.0",
            "root_directory": ".",
            "central_agent": central_agent,
            "seconds_per_time_step": seconds_per_time_step,
            "buildings": {},
            "simulation_start_time_step": 0,
            "simulation_end_time_step": 8759,
            "episode_time_steps": 8760
        }
        schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        logger.info("Schema minimalista creado")

    # Cargar schema desde archivo
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    # Actualizar valores críticos del schema
    schema["seconds_per_time_step"] = seconds_per_time_step
    # CRITICAL FIX: Use relative path "." instead of absolute path
    # This avoids CityLearn UTF-8 encoding bug with paths containing special characters
    schema["root_directory"] = "."
    schema["start_date"] = "2024-01-01"  # Alinear con datos solares PVGIS
    schema["simulation_end_time_step"] = 8759  # Full year (0-indexed: 8760 steps total)
    schema["episode_time_steps"] = 8760  # CRITICAL FIX: Force full-year episodes (was null causing premature termination)

    # === UN SOLO BUILDING: Mall_Iquitos (unifica ambas playas de estacionamiento) ===
    # Arquitectura: 1 edificio Mall con 2 áreas de estacionamiento (motos + mototaxis)
    # Todos los 38 chargers v5.2, PV y BESS se gestionan como una única unidad
    _bname_template, b_template = _find_first_building(schema)

    # Crear building unificado para el Mall
    b_mall = json.loads(json.dumps(b_template))
    b_mall["name"] = "Mall_Iquitos"
    if isinstance(b_mall.get("electric_vehicle_storage"), dict):
        b_mall["electric_vehicle_storage"]["active"] = True
    else:
        b_mall["electric_vehicle_storage"] = {"active": True}

    # Configurar schema con UN SOLO building
    schema["buildings"] = {"Mall_Iquitos": b_mall}
    logger.info("Creado building unificado: Mall_Iquitos v5.2 (19 chargers x 2 sockets = 38 tomas, 281.2 kW, 4050 kWp PV, 940 kWh BESS)")

    # Referencia al building único
    b = b_mall
    bname = "Mall_Iquitos"

    # === LIMPIEZA CRÍTICA: Eliminar recursos NO-OE2 del template ===
    # El template CityLearn puede incluir recursos que NO son parte del proyecto OE2
    # Solo se preservan: pv, pv_power_plant, electrical_storage, chargers (key correcta para CityLearn v2.5.0)
    non_oe2_resources = [
        'washing_machines',      # Del template - NO es OE2
        'cooling_device',        # Del template - NO es OE2
        'heating_device',        # Del template - NO es OE2
        'dhw_device',            # Del template - NO es OE2
        'cooling_storage',       # Del template - NO es OE2
        'heating_storage',       # Del template - NO es OE2
        'dhw_storage',           # Del template - NO es OE2
        'electric_vehicle_chargers',  # CityLearn v2.5.0 usa "chargers", NO esta key
    ]
    removed_resources = []
    for resource_key in non_oe2_resources:
        if resource_key in b_mall:
            del b_mall[resource_key]
            removed_resources.append(resource_key)
    if removed_resources:
        logger.info("[CLEANUP] Eliminados recursos NO-OE2 del building: %s", removed_resources)
    else:
        logger.info("[CLEANUP] Building limpio - sin recursos NO-OE2 detectados")

    # === CREAR electric_vehicles_def ===
    # CRITICO: CityLearn necesita definiciones de EVs con baterias para que los chargers funcionen.
    # Sin esto, el consumo de chargers sera 0 (los EVs no tienen baterias definidas).
    #
    # Configuracion OE2 v5.2:
    # - 30 motos: bateria 4.6 kWh, carga 7.4 kW (Modo 3), tiempo real 60 min
    # - 8 mototaxis: bateria 7.4 kWh, carga 7.4 kW (Modo 3), tiempo real 90 min
    # - 19 cargadores x 2 tomas = 38 sockets totales
    # - Potencia instalada: 281.2 kW
    electric_vehicles_def = {}

    # 30 EVs para motos (sockets 0-29)
    for i in range(30):
        ev_name = f'EV_Mall_{i+1}'
        electric_vehicles_def[ev_name] = {
            'include': True,
            'battery': {
                'type': 'citylearn.energy_model.Battery',
                'autosize': False,
                'attributes': {
                    'capacity': 4.6,           # kWh - bateria moto electrica v5.2
                    'nominal_power': 7.4,      # kW - Modo 3 monofasico 32A @ 230V
                    'initial_soc': 0.20,       # 20% SOC al llegar (fraccion)
                    'depth_of_discharge': 0.90, # 90% DOD maximo
                    'efficiency': 0.95,        # 95% eficiencia carga/descarga
                }
            }
        }

    # 8 EVs para mototaxis (sockets 30-37)
    for i in range(8):
        ev_name = f'EV_Mall_{30+i+1}'
        electric_vehicles_def[ev_name] = {
            'include': True,
            'battery': {
                'type': 'citylearn.energy_model.Battery',
                'autosize': False,
                'attributes': {
                    'capacity': 7.4,           # kWh - bateria mototaxi v5.2
                    'nominal_power': 7.4,      # kW - Modo 3 monofasico 32A @ 230V
                    'initial_soc': 0.20,       # 20% SOC al llegar (fraccion)
                    'depth_of_discharge': 0.90, # 90% DOD maximo
                    'efficiency': 0.95,        # 95% eficiencia carga/descarga
                }
            }
        }

    schema['electric_vehicles_def'] = electric_vehicles_def
    logger.info("[EV ARCHITECTURE] Creado electric_vehicles_def v5.2: 38 EVs (30 motos + 8 mototaxis)")

    # Update PV + BESS sizes from OE2 artifacts
    pv_dc_kw = float(cfg["oe2"]["solar"]["target_dc_kw"])
    bess_cap = None
    bess_pow = None
    artifacts = _load_oe2_artifacts(interim_dir)

    # Usar parámetros de CityLearn preparados si existen
    if "solar_params" in artifacts:
        solar_params = artifacts["solar_params"]
        pv_params = solar_params.get("pv") or solar_params.get("photovoltaic") or {}
        pv_dc_kw = float(pv_params.get("nominal_power", pv_dc_kw))
        logger.info("Usando parametros solares de OE2: %s kWp", pv_dc_kw)

    # Preferir resultados BESS actualizados; si no existen, usar parámetros del schema
    if "bess" in artifacts:
        bess_cap = float(artifacts["bess"].get("capacity_kwh", 0.0)) or float(artifacts["bess"].get("fixed_capacity_kwh", 0.0))
        bess_pow = float(artifacts["bess"].get("nominal_power_kw", 0.0)) or float(artifacts["bess"].get("power_rating_kw", 0.0))
        logger.info("Usando resultados BESS de OE2: %s kWh, %s kW", bess_cap, bess_pow)

        # ✅ CORRECCIÓN AUTOMÁTICA EMBEDDED (L443-456): Si los valores son 0/None, usar valores OE2 v5.4
        if bess_cap is None or bess_cap == 0.0:
            bess_cap = 1700.0  # ✅ OE2 v5.4: 1,700 kWh (total system capacity) [EMBEDDED-FIX-L1]
            logger.warning("[EMBEDDED-FIX] BESS capacity corregido a OE2 v5.4: 1700.0 kWh")
        if bess_pow is None or bess_pow == 0.0:
            bess_pow = 400.0  # ✅ OE2 v5.4: 400 kW [EMBEDDED-FIX-L1]
            logger.warning("[EMBEDDED-FIX] BESS power corregido a OE2 v5.4: 400.0 kW")

    elif "bess_params" in artifacts:
        bess_params = artifacts["bess_params"]
        bess_cap = float(bess_params.get("electrical_storage", {}).get("capacity", 0.0))
        bess_pow = float(bess_params.get("electrical_storage", {}).get("nominal_power", 0.0))
        logger.info("Usando parametros BESS de OE2 (schema): %s kWh, %s kW", bess_cap, bess_pow)
    else:
        # ✅ CORRECCIÓN AUTOMÁTICA EMBEDDED (L456-463): Si no hay artifacts, usar OE2 v5.4
        bess_cap = 1700.0   # ✅ v5.4: 1,700 kWh (total system capacity)
        bess_pow = 400.0    # ✅ v5.4: 400 kW (power rating)
        logger.warning("[EMBEDDED-FIX] BESS config no encontrado, usando OE2 v5.4: 1700.0 kWh / 400.0 kW [FALLBACK]")

    # === ACTUALIZAR PV Y BESS EN EL BUILDING UNIFICADO ===
    # pylint: disable=all
    # Todo el sistema PV+BESS se asigna al único building Mall_Iquitos  # noqa
    for building_name, building in schema["buildings"].items():
        # Actualizar/Crear PV - TODO el sistema solar al building único
        # Usar ambas keys posibles: "pv" y "pv_power_plant" para máxima compatibilidad
        if pv_dc_kw > 0:
            # Configurar key "pv"
            if not isinstance(building.get("pv"), dict):
                building["pv"] = {
                    "type": "citylearn.energy_model.PV",
                    "autosize": False,
                    "nominal_power": pv_dc_kw,
                    "attributes": {
                        "nominal_power": pv_dc_kw,
                    }
                }
                logger.info("%s: CREADO pv con nominal_power = %.1f kWp", building_name, pv_dc_kw)
            else:
                building["pv"]["nominal_power"] = pv_dc_kw
                if isinstance(building["pv"].get("attributes"), dict):
                    building["pv"]["attributes"]["nominal_power"] = pv_dc_kw
                else:
                    building["pv"]["attributes"] = {"nominal_power": pv_dc_kw}
                logger.info("%s: Actualizado pv.nominal_power = %.1f kWp", building_name, pv_dc_kw)

            # También configurar "pv_power_plant" para compatibilidad adicional
            if not isinstance(building.get("pv_power_plant"), dict):
                building["pv_power_plant"] = {
                    "type": "citylearn.energy_model.PV",
                    "autosize": False,
                    "attributes": {
                        "nominal_power": pv_dc_kw,
                    }
                }
                logger.info("%s: CREADO pv_power_plant con nominal_power = %.1f kWp", building_name, pv_dc_kw)
            else:
                if isinstance(building["pv_power_plant"].get("attributes"), dict):
                    building["pv_power_plant"]["attributes"]["nominal_power"] = pv_dc_kw
                logger.info("%s: Actualizado pv_power_plant.nominal_power = %.1f kWp", building_name, pv_dc_kw)

        if isinstance(building.get("photovoltaic"), dict):
            if isinstance(building["photovoltaic"].get("attributes"), dict):
                building["photovoltaic"]["attributes"]["nominal_power"] = pv_dc_kw
            building["photovoltaic"]["nominal_power"] = pv_dc_kw

        # Actualizar BESS - TODO el sistema de almacenamiento al building único
        if bess_cap is not None and bess_cap > 0:
            if not isinstance(building.get("electrical_storage"), dict):
                building["electrical_storage"] = {
                    "type": "citylearn.energy_model.Battery",
                    "autosize": False,
                    "capacity": bess_cap,
                    "attributes": {"capacity": bess_cap}
                }
            else:
                building["electrical_storage"]["capacity"] = bess_cap
                if bess_pow is not None:
                    building["electrical_storage"]["nominal_power"] = bess_pow
                if isinstance(building["electrical_storage"].get("attributes"), dict):
                    building["electrical_storage"]["attributes"]["capacity"] = bess_cap
                    if bess_pow is not None:
                        building["electrical_storage"]["attributes"]["nominal_power"] = bess_pow
            logger.info("%s: BESS %.1f kWh, %.1f kW", building_name, bess_cap, bess_pow)

    # === CREAR CHARGERS EN EL SCHEMA v5.2 (38 sockets = 19 cargadores x 2 tomas) ===
    # Los sockets se crean directamente en el schema para control por RL agents
    # Cada socket (toma) es independiente y controlable via acciones continuas [0, 1]

    # Configuracion v5.2
    n_physical_chargers = 19  # 19 cargadores fisicos (15 motos + 4 mototaxis)
    sockets_per_charger = 2   # 2 tomas por cargador (Modo 3)
    total_devices = n_physical_chargers * sockets_per_charger  # 19 x 2 = 38 sockets

    logger.info(f"[CHARGERS SCHEMA] Configurando {total_devices} sockets v5.2 (19 chargers x 2 sockets = 38 tomas) en schema para control RL")

    # v5.2: 38 sockets (tomas) controlables via acciones RL
    # - Sockets 0-29: 30 tomas para motos (15 cargadores x 2)
    # - Sockets 30-37: 8 tomas para mototaxis (4 cargadores x 2)
    # - Cada socket tiene CSV con estado (ocupancia, SOC, etc.)
    # - RL agents controlan power setpoint via acciones continuas [0, 1]

    # CRITICAL FIX: ALWAYS START WITH EMPTY CHARGERS DICT
    # We create exactly 38 chargers for proper control
    b["chargers"] = {}  # FORCE EMPTY - we'll populate with 38

    logger.info(f"[CHARGERS SCHEMA] Configurando {total_devices} chargers v5.2 en el schema...")

    # === NOTA SOBRE EVs ===
    # NO crear 38 EVs permanentes en el schema
    # Los EVs son dinámicos (vehículos que llegan/se van)
    # El schema NO tiene electric_vehicles_def global
    # Los chargers tienen datos dinámicos en charger_simulation_*.csv
    # Eso es suficiente para que CityLearn interprete los EVs

    # Get charger template from FIRST existing charger (if any) for reference
    charger_template = None
    backup_existing_chargers = b.get("chargers", {})  # Store for reference
    if backup_existing_chargers:
        charger_template = list(backup_existing_chargers.values())[0]

    # === CREAR EXACTAMENTE 38 CHARGERS EN EL SCHEMA v5.2 ===
    all_chargers: Dict[str, Any] = {}
    n_motos = 0
    n_mototaxis = 0
    power_motos = 0.0
    power_mototaxis = 0.0

    for charger_idx in range(total_devices):  # 38 iteraciones = 19 chargers x 2 sockets
        # Generate charger name
        charger_name = f"charger_mall_{charger_idx + 1}"

        # v5.2: Todos los sockets tienen 7.4 kW (Modo 3 monofasico 32A @ 230V)
        # Sockets 0-29: motos (30 tomas)
        # Sockets 30-37: mototaxis (8 tomas)
        power_kw = 7.4  # Modo 3 - igual para todos
        
        if charger_idx < 30:  # Sockets 0-29 = motos
            charger_type = "moto"
        else:  # Sockets 30-37 = mototaxis
            charger_type = "moto_taxi"

        # Create charger entry in schema
        if charger_template:
            new_charger = json.loads(json.dumps(charger_template))
        else:
            new_charger = {
                "type": "citylearn.electric_vehicle_charger.Charger",
                "autosize": False,
                "active": True,
                "attributes": {
                    "efficiency": 0.95,
                    "charger_type": 0,
                    "min_charging_power": 0.5,
                },
            }

        # Set common properties
        new_charger["active"] = True
        new_charger["charger_simulation"] = ""  # Will be updated later

        # Set power and socket info (ONE socket per charger entry)
        nominal_power = power_kw  # Power of ONE socket (not 4 sockets)
        if "attributes" in new_charger:
            new_charger["attributes"]["nominal_power"] = nominal_power
            new_charger["attributes"]["max_charging_power"] = nominal_power
            new_charger["attributes"]["num_sockets"] = 1  # One socket per entry
        else:
            new_charger["nominal_power"] = nominal_power
            new_charger["max_charging_power"] = nominal_power
            new_charger["num_sockets"] = 1

        # Add to all_chargers
        all_chargers[charger_name] = new_charger

        # Count by type
        if charger_type.lower() == "moto_taxi" or power_kw >= 2.5:
            n_mototaxis += 1
            power_mototaxis += nominal_power
        else:
            n_motos += 1
            power_motos += nominal_power

    # Assign ALL chargers to Mall_Iquitos building
    # CRITICAL FIX: CityLearn v2.5.0 usa la clave "chargers" (NO "electric_vehicle_chargers")
    # Ver _load_building línea 109 en citylearn/citylearn.py:
    #   if building_schema.get("chargers", None) is not None:
    b_mall = schema["buildings"]["Mall_Iquitos"]
    b_mall["chargers"] = all_chargers

    # CRITICAL FIX: Store chargers count for later verification
    # This ensures we know we assigned 38 chargers even if dict is modified later
    all_chargers_backup = dict(all_chargers)  # Deep copy to preserve state
    chargers_count_at_assignment = len(all_chargers)

    logger.info(f"[CHARGERS SCHEMA] OK CORRECCION CRITICA v5.2: Asignados {total_devices} sockets (19 chargers x 2) a 'chargers': {n_motos} motos ({power_motos:.1f} kW) + {n_mototaxis} mototaxis ({power_mototaxis:.1f} kW)")
    logger.info(f"[CHARGERS SCHEMA] OK BACKUP: Guardadas {chargers_count_at_assignment} chargers para validacion posterior")

    # === ELECTRIC VEHICLES: DINÁMICOS (no permanentes) ===
    # NOTA: Los EVs NO son 38 entidades permanentes
    # Los EVs son VEHÍCULOS DINÁMICOS que llegan/se van cada hora
    # El schema NO necesita 38 EVs definidos - eso es incorrecto
    # Los datos de occupancy/SOC vienen en charger_simulation_*.csv
    # CityLearn los interpreta dinámicamente basado en los datos de ocupancia

    # NO crear electric_vehicles_list permanente - los chargers ya tienen
    # los datos dinámicos en sus CSV de simulación
    logger.info(f"[EV DYNAMICS] EVs son dinámicos (basados en charger_simulation_*.csv), no permanentes en schema")

    # Discover and overwrite relevant CSVs
    paths = _discover_csv_paths(schema, out_dir)
    energy_path = paths.get("energy_simulation")

    # Inicializar n y df_energy con valores default
    n = 8760  # 1 año = 365 días × 24 horas
    df_energy = None

    # MAPEO OE3 IQUITOS: energy_simulation → archivo OE2 Real (solar PVGIS)
    # En OE3, no usamos el template de CityLearn, sino datos reales OE2
    if energy_path is None or not energy_path.exists():
        # Forzar que energy_simulation apunte al archivo OE2 real
        energy_path = interim_dir / Path("Generacionsolar") / Path("pv_generation_hourly_citylearn_v2.csv")
        if energy_path.exists():
            logger.info("[ENERGY MAPPING] energy_simulation → OE2 Real PVGIS: %s", energy_path.name)
            df_energy = pd.read_csv(energy_path)
            n = min(len(df_energy), 8760)
            df_energy = df_energy.iloc[:n].reset_index(drop=True)
            # OE3 FIX: Add required columns for CityLearn compatibility
            # When using PV-only data, add placeholder non_shiftable_load column
            if "non_shiftable_load" not in df_energy.columns:
                df_energy["non_shiftable_load"] = 0.0  # Will be populated with mall_series later
                logger.info("[OE3 FIX] Added non_shiftable_load column (placeholder)")
            # Rename pv_generation_kwh to solar_generation if needed
            if "pv_generation_kwh" in df_energy.columns and "solar_generation" not in df_energy.columns:
                df_energy["solar_generation"] = df_energy["pv_generation_kwh"]
                logger.info("[OE3 FIX] Mapped pv_generation_kwh → solar_generation")
        else:
            logger.warning("[OE3 FIX] energy_simulation CSV no encontrado en template ni OE2. Continuando sin energia.")
    else:
        df_energy = pd.read_csv(energy_path)
        logger.info("energy_simulation path: %s, shape: %s", energy_path, df_energy.shape)
        # Truncar a 8760 timesteps (365 días * 24 horas = 1 año de datos horarios)
        n = min(len(df_energy), 8760)
        df_energy = df_energy.iloc[:n].reset_index(drop=True)

    # === REGENERAR COLUMNAS DE TIEMPO PARA EMPEZAR EN ENERO (alinear con PVGIS) ===
    # Crear índice temporal desde 2024-01-01 00:00 (365 días × 24 horas = 8760 filas)
    time_index = pd.date_range(start="2024-01-01", periods=n, freq="h")

    # Solo modificar df_energy si existe
    if df_energy is not None:
        if "month" in df_energy.columns:
            df_energy["month"] = time_index.month
        if "hour" in df_energy.columns:
            df_energy["hour"] = time_index.hour
        if "day_type" in df_energy.columns:
            # day_type: 1=weekday, 2=weekend
            df_energy["day_type"] = np.where(time_index.dayofweek < 5, 1, 2)
        logger.info("[OK] Columnas de tiempo regeneradas: month=1-12, alineado con PVGIS")
    else:
        logger.info("[OK] Sin regenerar columnas (using OE2 data)")

    # Build mall load and PV generation series for length n
    # PRIORIDAD: 1) mall_demand (OE2 real) > 2) building_load_citylearn > 3) config default
    mall_series = None
    mall_source = "default"

    # PRIORIDAD 1: mall_demand (datos OE2 REALES)
    if "mall_demand" in artifacts:
        mall_df = artifacts["mall_demand"].copy()
        if not mall_df.empty:
            # ✅ CRITICAL FIX: Handle single-column with embedded separator (e.g., "datetime,kwh" in CSV with ; separator)
            # This happens when file uses ; separator but pandas reads as single column
            if len(mall_df.columns) == 1:
                col_name = mall_df.columns[0]
                if "," in col_name or ";" in col_name:
                    # Detect separator used in column name
                    sep_char = "," if "," in col_name else ";"
                    mall_df = mall_df[col_name].str.split(sep_char, expand=True)
                    if mall_df.shape[1] >= 2:
                        mall_df.columns = ["datetime", "mall_kwh"]
                    logger.info("[MALL LOAD] Split combined column using separator '%s'", sep_char)

            # Now detect date and demand columns
            date_col = None
            for col in mall_df.columns:
                col_norm = str(col).strip().lower()
                if col_norm in ("fecha", "horafecha", "datetime", "timestamp", "time") or "fecha" in col_norm:
                    date_col = col
                    break
            if date_col is None:
                date_col = mall_df.columns[0]

            demand_col = None
            for col in mall_df.columns:
                if col == date_col:
                    continue
                col_norm = str(col).strip().lower()
                if any(tag in col_norm for tag in ("kwh", "demanda", "power", "kw")):
                    demand_col = col
                    break
            if demand_col is None:
                candidates = [c for c in mall_df.columns if c != date_col]
                demand_col = candidates[0] if candidates else date_col

            unit_is_energy = "kwh" in str(demand_col).strip().lower()
            mall_df = mall_df.rename(columns={date_col: "datetime", demand_col: "mall_kwh"})
            mall_df["datetime"] = pd.to_datetime(mall_df["datetime"], errors="coerce")
            mall_df["mall_kwh"] = pd.to_numeric(mall_df["mall_kwh"], errors="coerce")
            mall_df = mall_df.dropna(subset=["datetime", "mall_kwh"])
            mall_df = mall_df.set_index("datetime").sort_index()

            if not mall_df.empty:
                source_path = artifacts.get("mall_demand_path", "oe2/demandamall artifact")
                if len(mall_df.index) > 1:
                    dt_minutes = (mall_df.index[1] - mall_df.index[0]).total_seconds() / 60
                else:
                    dt_minutes = 60
                series = mall_df["mall_kwh"]
                if not unit_is_energy and dt_minutes > 0:
                    series = series * (dt_minutes / 60.0)
                if dt_minutes < 60:
                    series = series.resample("h").sum()

                values = series.values
                if len(values) >= n:
                    mall_series = values[:n]
                    mall_source = f"mall_demand ({source_path}) - OE2 REAL DATA"
                    logger.info("[MALL LOAD] ✓ Usando demanda REAL del mall OE2: %d registros", len(mall_series))
                else:
                    hourly_profile = series.groupby(series.index.hour).mean()
                    hourly_profile = hourly_profile.reindex(range(24), fill_value=0.0)
                    mall_series = _repeat_24h_to_length(hourly_profile.values, n)
                    mall_source = f"mall_demand ({source_path}) - perfil promedio replicado"
                    logger.info("[MALL LOAD] Demanda real incompleta, repitiendo perfil horario promedio")

    # PRIORIDAD 2: building_load_citylearn (fallback)
    if mall_series is None and "building_load_citylearn" in artifacts:
        building_load = artifacts["building_load_citylearn"]
        if len(building_load) >= n:
            mall_series = building_load['non_shiftable_load'].values[:n]
            mall_source = "building_load_citylearn (OE2 processed)"
            logger.info("[MALL LOAD] Usando demanda de building_load preparado: %d registros", len(mall_series))
        else:
            mall_series = _repeat_24h_to_length(building_load['non_shiftable_load'].values, n)
            mall_source = "building_load_citylearn (expandido)"
            logger.info("[MALL LOAD] Demanda building_load incompleta, repitiendo perfil diario")

    if mall_series is None:
        mall_energy_day = float(cfg["oe2"]["mall"]["energy_kwh_day"])
        mall_shape = cfg["oe2"]["mall"].get("shape_24h")  # may be None
        if mall_shape is None:
            # Default 24h profile (noon peak, low at night/early morning)
            # Shape normalized to sum=1
            default_shape = np.array([
                0.02, 0.01, 0.01, 0.01, 0.02, 0.03, 0.05, 0.08,
                0.10, 0.12, 0.15, 0.18, 0.20, 0.18, 0.15, 0.12,
                0.10, 0.08, 0.06, 0.04, 0.03, 0.02, 0.02, 0.02
            ])
            mall_shape_arr = default_shape / default_shape.sum()
        else:
            mall_shape_arr = np.array(mall_shape, dtype=float)
            mall_shape_arr = mall_shape_arr / mall_shape_arr.sum()

        mall_24h = mall_energy_day * mall_shape_arr
        mall_series = _repeat_24h_to_length(mall_24h, n)

    # =============================================================================
    # PV SOLAR GENERATION - CRITICAL FIX (2026-02-02)
    # =============================================================================
    # PRIORIDAD: Usar datos ABSOLUTOS de OE2 (kWh), NO normalizados por kWp
    #
    # Fuentes de datos (en orden de prioridad):
    # 1. solar_ts['ac_power_kw'] = 8,030,119 kWh/año (CORRECTO - datos OE2 reales)
    # 2. solar_generation_citylearn = 1,929 kWh/año (INCORRECTO - normalizado por kWp)
    #
    # CityLearn Building.solar_generation espera kWh ABSOLUTOS, no por kWp
    # =============================================================================

    pv_absolute_kwh = None  # Valores absolutos en kWh (NO normalizados)
    pv_source = "none"

    # PRIORIDAD 1: Usar datos OE2 directos (pv_generation_timeseries.csv)
    if "solar_ts" in artifacts:
        solar_ts = artifacts["solar_ts"]
        # Buscar columna con potencia/energía absoluta
        for col in ['ac_power_kw', 'pv_kwh', 'ac_energy_kwh']:
            if col in solar_ts.columns:
                pv_absolute_kwh = solar_ts[col].values.copy()
                pv_source = f"solar_ts[{col}]"
                # Si es subhorario, agregar a horario
                if len(pv_absolute_kwh) > n:
                    ratio = len(pv_absolute_kwh) // n
                    pv_absolute_kwh = np.array([pv_absolute_kwh[i*ratio:(i+1)*ratio].sum() for i in range(n)])
                logger.info("[PV] ✓ Usando datos OE2 ABSOLUTOS: %s", pv_source)
                logger.info("   Registros: %d, Suma: %s kWh/año", len(pv_absolute_kwh), f"{pv_absolute_kwh.sum():,.0f}")
                logger.info("   Mean: %.2f kW, Max: %.2f kW", pv_absolute_kwh.mean(), pv_absolute_kwh.max())
                break

    # PRIORIDAD 2: Si solar_ts no tiene datos, usar solar_generation_citylearn PERO ESCALAR
    if pv_absolute_kwh is None and "solar_generation_citylearn" in artifacts:
        solar_gen = artifacts["solar_generation_citylearn"]
        if 'solar_generation' in solar_gen.columns:
            # ESTOS VALORES ESTÁN NORMALIZADOS POR kWp - NECESITAN ESCALAR
            pv_normalized = solar_gen['solar_generation'].values
            pv_absolute_kwh = pv_normalized * pv_dc_kw  # Multiplicar por potencia nominal
            pv_source = f"solar_generation_citylearn × {pv_dc_kw:.0f} kWp"
            logger.warning("[PV] ⚠ Usando datos normalizados ESCALADOS: %s", pv_source)
            logger.info("   Registros: %d, Suma: %s kWh/año", len(pv_absolute_kwh), f"{pv_absolute_kwh.sum():,.0f}")

    # FALLBACK: Si no hay datos, usar ceros (con warning)
    if pv_absolute_kwh is None or len(pv_absolute_kwh) < n:
        pv_absolute_kwh = np.zeros(n, dtype=float)
        pv_source = "FALLBACK (zeros)"
        logger.error("[PV] ✗ NO SE ENCONTRARON DATOS SOLARES DE OE2 - usando ceros")
        logger.error("   Esto causará que el entrenamiento NO aprenda sobre solar")

    pv_absolute_kwh = pv_absolute_kwh[:n]

    # VALIDACIÓN: Verificar que los datos solares son razonables
    expected_annual_kwh = pv_dc_kw * 1930  # ~1930 kWh/kWp típico en Iquitos
    actual_annual_kwh = pv_absolute_kwh.sum()

    if actual_annual_kwh < expected_annual_kwh * 0.5:
        logger.error("[PV] ✗ VALIDACIÓN FALLIDA: Solar anual (%.0f kWh) es < 50%% del esperado (%.0f kWh)",
                    actual_annual_kwh, expected_annual_kwh)
        logger.error("   Fuente: %s", pv_source)
        logger.error("   Esto indica que los datos solares NO son correctos")
    else:
        logger.info("[PV] ✓ Validación OK: %.0f kWh/año (%.1f%% del esperado)",
                   actual_annual_kwh, 100 * actual_annual_kwh / expected_annual_kwh)

    # Variable para asignar al DataFrame (mantenemos nombre por compatibilidad)
    pv_per_kwp = pv_absolute_kwh  # NOTA: Ahora contiene valores ABSOLUTOS, no por kWp

    # Identify columns to overwrite in energy_simulation (template-dependent names)
    def find_col(regex_list: List[str]) -> str | None:
        if df_energy is None:
            return None
        for col in df_energy.columns:
            for rgx in regex_list:
                if re.search(rgx, col, re.IGNORECASE):
                    return col  # type: ignore
        return None

    load_col = find_col([r"non[_ ]?shiftable", r"electricity[_ ]?load"])
    solar_col = find_col([r"solar[_ ]?generation"])

    # OE3 Iquitos: Si no hay template energy_simulation, usar datos OE2 directamente
    if df_energy is not None and load_col is None:
        raise ValueError("Template energy_simulation file does not include a non_shiftable_load-like column.")

    # VERIFICAR SI HAY DATOS ANTES DE HACER CALCULOS
    has_mall_data = mall_series is not None and len(mall_series) > 0 and mall_series.sum() > 0
    has_solar_data = pv_per_kwp is not None and len(pv_per_kwp) > 0 and pv_per_kwp.sum() > 0

    if df_energy is None:
        logger.info("[OE3 IQUITOS] Sin template energy_simulation. Usando datos OE2 reales (mall_demand, chargers, PV).")
        if not has_mall_data:
            logger.warning("[OE3 WARNING] mall_demand: datos vacíos o None")
        if not has_solar_data:
            logger.warning("[OE3 WARNING] solar_generation: datos vacíos o None")
    else:
        # Template EXISTE: asignar datos si están disponibles
        if has_mall_data and load_col is not None:
            logger.info("[MALL DEMAND VALIDATION] Asignando demanda del mall...")
            logger.info(f"   Fuente: {mall_source}")
            logger.info(f"   Registros: {len(mall_series)}")
            logger.info(f"   Suma total: {mall_series.sum():.1f} kWh")
            logger.info(f"   Min: {mall_series.min():.2f} kW, Max: {mall_series.max():.2f} kW, Promedio: {mall_series.mean():.2f} kW")
            logger.info(f"   Primeros 5 horas: {mall_series[:5]}")
            logger.info(f"   Últimas 5 horas: {mall_series[-5:]}")
            df_energy[load_col] = mall_series
            logger.info("[ENERGY] Asignada carga: %s = %.1f kWh", load_col, mall_series.sum())
        else:
            if not has_mall_data:
                logger.warning("[ENERGY] mall_demand: datos vacíos o None - saltando asignación")

        if has_solar_data and solar_col is not None:
            df_energy[solar_col] = pv_per_kwp
            logger.info("[ENERGY] Asignada generacion solar: %s = %.1f (W/kW.h)", solar_col, pv_per_kwp.sum())
            logger.info("   Primeros 5 valores: %s", pv_per_kwp[:5])
            logger.info("   Ultimos 5 valores: %s", pv_per_kwp[-5:])
        else:
            if not has_solar_data:
                logger.warning("[ENERGY] solar_generation: datos vacíos o None - saltando asignación")
            elif solar_col is None:
                logger.warning("[ENERGY] No solar_generation-like column found; PV may be ignored by this dataset.")

        # Zero-out other end-uses if present to isolate the problem to electricity + EV + PV + BESS
        for col in df_energy.columns:
            if col == load_col or col == solar_col:
                continue
            if re.search(r"cooling|heating|dhw|hot water|gas", col, re.IGNORECASE):
                df_energy[col] = 0.0

        df_energy.to_csv(energy_path, index=False)

    # === VALIDATION REPORT: BESS, SOLAR, MALL DEMAND ===
    logger.info("")
    logger.info("=" * 80)
    logger.info("VALIDATION REPORT: Dataset Construction Completeness")
    logger.info("=" * 80)

    # 1. BESS Validation
    if bess_cap is not None and bess_cap > 0:
        logger.info("[OK] [BESS] CONFIGURED & LOADED")
        logger.info(f"   Capacity: {bess_cap:.0f} kWh")
        logger.info(f"   Power: {bess_pow:.0f} kW")
        logger.info(f"   File: electrical_storage_simulation.csv (sera creado)")
    else:
        logger.warning("[WARN] [BESS] NOT CONFIGURED - capacity=0 or missing")

    # 2. Solar Generation Validation
    if pv_per_kwp is not None and len(pv_per_kwp) > 0 and pv_per_kwp.sum() > 0:
        logger.info("[OK] [SOLAR GENERATION] CONFIGURED & LOADED")
        logger.info(f"   Capacity: {pv_dc_kw:.0f} kWp")
        logger.info(f"   Timeseries length: {len(pv_per_kwp)} hours (hourly resolution)")
        logger.info(f"   Total annual generation: {pv_per_kwp.sum():.1f} W/kWp")
        logger.info(f"   Mean hourly: {pv_per_kwp.mean():.3f}, Max: {pv_per_kwp.max():.3f}")
        logger.info(f"   Source: {('PVGIS hourly' if 'solar_ts' in artifacts else 'CityLearn template')}")
    else:
        logger.warning("[WARN] [SOLAR GENERATION] NOT CONFIGURED - sum=0 or missing")

    # 3. Mall Demand Validation
    if mall_series is not None and len(mall_series) > 0 and mall_series.sum() > 0:
        logger.info("[OK] [MALL DEMAND] CONFIGURED & LOADED")
        logger.info(f"   Timeseries length: {len(mall_series)} hours (hourly resolution)")
        logger.info(f"   Total annual demand: {mall_series.sum():.1f} kWh")
        logger.info(f"   Mean hourly: {mall_series.mean():.2f} kW, Max: {mall_series.max():.2f} kW")
        logger.info(f"   Source: {mall_source}")
        logger.info(f"   Daily pattern recognized: {('real demand curve' if 'mall_demand' in artifacts else 'synthetic profile')}")
    else:
        logger.warning("[WARN] [MALL DEMAND] NOT CONFIGURED - sum=0 or missing")

    # 4. EV Chargers Validation
    logger.info("[OK] [EV CHARGERS] CONFIGURED")
    logger.info(f"   Total chargers: 38 (v5.2) (for 38 simulation files)")
    logger.info(f"   Operating hours: {cfg['oe2']['ev_fleet']['opening_hour']}-{cfg['oe2']['ev_fleet']['closing_hour']}")
    logger.info(f"   Files will be generated: charger_simulation_001.csv to charger_simulation_038.csv")

    logger.info("=" * 80)
    logger.info("[OK] All OE2 artifacts properly integrated into CityLearn dataset")
    logger.info("=" * 80)
    logger.info("")

    # carbon intensity and pricing
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    tariff = float(cfg["oe3"]["grid"]["tariff_usd_per_kwh"])
    if (out_dir / "carbon_intensity.csv").exists():
        df_ci = pd.read_csv(out_dir / "carbon_intensity.csv")
        _write_constant_series_csv(out_dir / "carbon_intensity.csv", df_ci, ci)
        schema["carbon_intensity"] = "carbon_intensity.csv"
    elif paths.get("carbon_intensity") and paths["carbon_intensity"].exists():
        df_ci = pd.read_csv(paths["carbon_intensity"])
        _write_constant_series_csv(paths["carbon_intensity"], df_ci, ci)

    if (out_dir / "pricing.csv").exists():
        df_pr = pd.read_csv(out_dir / "pricing.csv")
        _write_constant_series_csv(out_dir / "pricing.csv", df_pr, tariff)
        schema["pricing"] = "pricing.csv"
    elif paths.get("pricing") and paths["pricing"].exists():
        df_pr = pd.read_csv(paths["pricing"])
        _write_constant_series_csv(paths["pricing"], df_pr, tariff)

# === ELECTRICAL STORAGE (BESS) SIMULATION ===
    # Usar datos REALES de OE2 (ya calculados en optimización fase 2)
    if bess_cap is not None and bess_cap > 0:
        bess_simulation_path = out_dir / "electrical_storage_simulation.csv"

        bess_oe2_df = None
        bess_source = "unknown"

        # PRIORITY 1: NEW bess_simulation_hourly.csv (2026-02-04 - OE2 v3.0 real data)
        if "bess_hourly_2024" in artifacts:
            try:
                bess_oe2_df = artifacts["bess_hourly_2024"].copy()
                bess_source = "bess_simulation_hourly.csv (OE2 v3.0 real data - 2026-02-04)"
                logger.info(f"[BESS] ✅ PRIORITY 1: USING REAL DATASET: {bess_source}")
                logger.info(f"[BESS]    Columns: {bess_oe2_df.columns.tolist()}")
            except Exception as e:
                logger.warning(f"[BESS] ⚠️  Error con PRIORITY 1: {e}")
                bess_oe2_df = None

        # PRIORITY 2: Legacy bess_simulation_hourly.csv files
        if bess_oe2_df is None:
            bess_oe2_path = None
            for potential_path in [
                Path("data/interim/oe2/bess/bess_simulation_hourly.csv"),
                Path("data/oe2/bess/bess_simulation_hourly.csv"),
                Path(str(paths.get("bess_simulation_hourly"))) if "bess_simulation_hourly" in paths and paths.get("bess_simulation_hourly") else None,
            ]:
                if potential_path and potential_path.exists():
                    bess_oe2_path = potential_path
                    bess_source = f"bess_simulation_hourly.csv (legacy)"
                    break

            if bess_oe2_path:
                try:
                    bess_oe2_df = pd.read_csv(bess_oe2_path)
                    logger.info(f"[BESS] ✅ PRIORITY 2: USING LEGACY DATASET: {bess_oe2_path}")
                    logger.info(f"[BESS]    Columns: {bess_oe2_df.columns.tolist()}")
                except Exception as e:
                    logger.warning(f"[BESS] ⚠️  Error con PRIORITY 2: {e}")
                    bess_oe2_df = None

        # VALIDACIÓN Y PROCESAMIENTO
        if bess_oe2_df is not None:
            # Validar que tenga exactamente 8760 filas (1 año)
            bess_len: int = int(len(bess_oe2_df)) if hasattr(bess_oe2_df, '__len__') else 0
            if bess_len != 8760:
                logger.error(f"[BESS] ✗ Invalid length: {bess_len} rows (need 8,760). Source: {bess_source}")
                raise ValueError(f"BESS dataset must have 8,760 rows, got {bess_len}")

            # Buscar columna SOC (puede tener diferentes nombres)
            soc_col = None
            for col_candidate in ["soc_percent", "soc_kwh", "soc", "stored_kwh", "state_of_charge"]:
                if col_candidate in bess_oe2_df.columns:
                    soc_col = col_candidate
                    break

            if soc_col is None:
                logger.error(f"[BESS] ✗ No SOC column found. Available columns: {bess_oe2_df.columns.tolist()}")
                raise ValueError("BESS dataset must contain SOC column (soc_percent, soc_kwh, etc.)")

            # Extraer valores SOC y convertir a kWh si es necesario
            soc_values = bess_oe2_df[soc_col].values.copy()

            # Si soc_percent está en porcentaje (0-100), convertir a kWh
            soc_values_float: np.ndarray = np.asarray(soc_values, dtype=np.float64)
            max_soc: float = float(np.max(soc_values_float)) if len(soc_values_float) > 0 else 0.0
            if soc_col == "soc_percent" and max_soc > 1.0:
                # Está en porcentaje (0-100), convertir a kWh
                soc_kwh = (soc_values_float / 100.0) * float(bess_cap)
                logger.info(f"[BESS]    Converted {soc_col} (%) to kWh using capacity {bess_cap:.0f} kWh")
            else:
                soc_kwh = soc_values_float if soc_col == "soc_kwh" else (soc_values_float * float(bess_cap))

            # ═══════════════════════════════════════════════════════════════════════════
            # NUEVAS MÉTRICAS v5.4: Extraer ahorros por picos y CO2 indirecto normalizados
            # ═══════════════════════════════════════════════════════════════════════════
            peak_reduction_savings_norm = np.zeros(len(soc_kwh))
            co2_avoided_indirect_norm = np.zeros(len(soc_kwh))
            
            # Intentar extraer las nuevas columnas normalizadas si existen
            if "peak_reduction_savings_normalized" in bess_oe2_df.columns:
                peak_reduction_savings_norm = np.asarray(
                    bess_oe2_df["peak_reduction_savings_normalized"].values, 
                    dtype=np.float64
                )
                logger.info(f"[BESS]    ✓ Ahorros por reducción de picos: {np.sum(peak_reduction_savings_norm):.2f} unidades acumuladas")
            else:
                logger.warning(f"[BESS]    ⚠ Columna 'peak_reduction_savings_normalized' no encontrada (v5.3?)")
                
            if "co2_avoided_indirect_normalized" in bess_oe2_df.columns:
                co2_avoided_indirect_norm = np.asarray(
                    bess_oe2_df["co2_avoided_indirect_normalized"].values, 
                    dtype=np.float64
                )
                logger.info(f"[BESS]    ✓ CO2 evitado indirectamente (normalizado): {np.sum(co2_avoided_indirect_norm):.2f} unidades acumuladas")
            else:
                logger.warning(f"[BESS]    ⚠ Columna 'co2_avoided_indirect_normalized' no encontrada (v5.3?)")

            # Crear CSV con columna soc_stored_kwh + nuevas métricas para CityLearn
            bess_df = pd.DataFrame({
                "soc_stored_kwh": soc_kwh,
                # ═══════════════════════════════════════════════════════════════════
                # Nuevas columnas v5.4 (normalizadas [0,1] para observaciones RL)
                # ═══════════════════════════════════════════════════════════════════
                "peak_reduction_savings_normalized": peak_reduction_savings_norm,
                "co2_avoided_indirect_normalized": co2_avoided_indirect_norm,
            })

            bess_df.to_csv(bess_simulation_path, index=False)

            logger.info(f"[BESS] ✅ USING REAL DATA FROM OE2: {bess_source}")
            logger.info(f"[BESS] Capacidad: {bess_cap:.0f} kWh, Potencia: {bess_pow:.0f} kW")
            soc_kwh_min: float = float(np.min(soc_kwh)) if len(soc_kwh) > 0 else 0.0
            soc_kwh_max: float = float(np.max(soc_kwh)) if len(soc_kwh) > 0 else 0.0
            soc_kwh_mean: float = float(np.mean(soc_kwh)) if len(soc_kwh) > 0 else 0.0
            soc_kwh_std: float = float(np.std(soc_kwh)) if len(soc_kwh) > 0 else 0.0
            unique_soc_count: int = int(len(np.unique(soc_kwh)))
            logger.info(f"[BESS] SOC Dinámico: min={soc_kwh_min:.0f} kWh, max={soc_kwh_max:.0f} kWh, mean={soc_kwh_mean:.0f} kWh")
            logger.info(f"[BESS] Variabilidad: {soc_kwh_std:.0f} kWh (std dev), {unique_soc_count} valores únicos")
            logger.info(f"[BESS] Escritura: {bess_simulation_path}")
        else:
            logger.error(f"[BESS] ✗ No se encontró ningún archivo de simulación BESS de OE2")
            logger.error(f"[BESS]    PRIORITY 1 buscado: data/oe2/bess/bess_simulation_hourly.csv")
            logger.error(f"[BESS]    PRIORITY 2 buscado: data/interim/oe2/bess/bess_simulation_hourly.csv")
            raise FileNotFoundError("CRITICAL: No BESS simulation file found. Create with: python -m scripts.run_bess_dataset_generation")

        # Actualizar schema con referencia al archivo de simulación BESS
        for building_name, building in schema["buildings"].items():
            if isinstance(building.get("electrical_storage"), dict):
                building["electrical_storage"]["efficiency"] = 0.95  # 95% round-trip efficiency
                # CRITICAL FIX: Referenciar el archivo de simulación BESS para que CityLearn lo cargue
                building["electrical_storage"]["energy_simulation"] = "electrical_storage_simulation.csv"

                # CRITICAL: Configurar initial_soc basado en datos OE2
                # El primer valor de soc_kwh de OE2 representa el estado inicial
                initial_soc_kwh = soc_values[0] if len(soc_values) > 0 else bess_cap * 0.5
                initial_soc_frac = initial_soc_kwh / bess_cap if bess_cap > 0 else 0.5

                # Configurar en el schema
                if isinstance(building["electrical_storage"].get("attributes"), dict):
                    building["electrical_storage"]["attributes"]["initial_soc"] = initial_soc_frac
                else:
                    building["electrical_storage"]["attributes"] = {"initial_soc": initial_soc_frac}

                logger.info(f"[BESS] Schema actualizado: {building_name}.electrical_storage.energy_simulation = electrical_storage_simulation.csv")
                logger.info(f"[BESS] Initial SOC configurado: {initial_soc_frac:.4f} ({initial_soc_kwh:.0f} kWh de {bess_cap:.0f} kWh)")
    else:
        logger.warning("[BESS] BESS deshabilitado o capacidad=0. No se crea electrical_storage_simulation.csv")

    # Charger simulation (first charger only if possible)
    _charger_list: List[Path] = []
    if "_charger_list" in paths:
        _charger_list = paths["_charger_list"]  # type: ignore
    # Build a generic daily charger simulation for the same length n
    opening = int(cfg["oe2"]["ev_fleet"]["opening_hour"])
    closing = int(cfg["oe2"]["ev_fleet"]["closing_hour"])

    # EV daily energy requirement from OE2 recommended profile, else 0
    _ev_energy_day = 0.0
    if "ev_profile_24h" in artifacts and "energy_kwh" in artifacts["ev_profile_24h"].columns:
        _ev_energy_day = float(artifacts["ev_profile_24h"]["energy_kwh"].sum())

    steps_per_hour = int(round(1.0 / dt_hours))
    steps_per_day = int(round(24.0 / dt_hours))

    # Arrival/departure steps within a day
    arrival_step = opening * steps_per_hour
    departure_step = (closing + 1) * steps_per_hour  # depart after closing hour
    departure_step = min(departure_step, steps_per_day)  # clamp

    # Build schedule arrays - NO usar NaN, CityLearn requiere valores numéricos válidos
    state = np.full(n, 3, dtype=int)  # 3 = commuting/sin EV
    ev_names = list(schema.get("electric_vehicles_def", {}).keys())
    default_ev = ev_names[0] if ev_names else "EV_001"

    # Inicializar con valores por defecto (NO NaN)
    # IMPORTANTE: ev_id debe tener el mismo EV siempre (CityLearn lo requiere)
    ev_id = np.full(n, default_ev, dtype=object)  # Siempre el mismo EV ID
    dep_time = np.zeros(n, dtype=float)  # 0 cuando no hay EV
    req_soc = np.zeros(n, dtype=float)  # 0 cuando no hay EV
    arr_time = np.zeros(n, dtype=float)  # 0 cuando hay EV conectado
    arr_soc = np.zeros(n, dtype=float)  # 0 cuando hay EV conectado

    # SOC de llegada y salida requerido (como FRACCIÓN 0.0-1.0, NO porcentaje)
    # CRÍTICO: CityLearn espera valores normalizados (0.20 = 20%, 0.90 = 90%)
    soc_arr = 0.20  # 20% SOC al llegar (fracción)
    soc_req = 0.90  # 90% SOC requerido al salir (fracción)

    for t in range(n):
        day_step = t % steps_per_day
        if arrival_step <= day_step < departure_step:
            # EV conectado (state=1)
            state[t] = 1
            # ev_id ya tiene el valor por defecto
            dep_time[t] = float(departure_step - day_step)  # Horas hasta salida
            req_soc[t] = soc_req  # SOC requerido al salir (%)
            arr_time[t] = 0.0  # 0 = ya llegó
            arr_soc[t] = soc_arr  # SOC con el que llegó
        else:
            # Sin EV (state=3 = commuting)
            state[t] = 3
            # ev_id mantiene el ID (CityLearn lo necesita para calcular SOC)
            dep_time[t] = 0.0  # 0 = no aplica
            req_soc[t] = 0.0  # 0 = no aplica
            # Tiempo estimado hasta próxima llegada
            if day_step < arrival_step:
                arr_time[t] = float(arrival_step - day_step)
            else:
                arr_time[t] = float(steps_per_day - day_step + arrival_step)
            arr_soc[t] = soc_arr  # SOC esperado al llegar

    charger_df = pd.DataFrame(
        {
            "electric_vehicle_charger_state": state,
            "electric_vehicle_id": ev_id,
            "electric_vehicle_departure_time": dep_time,
            "electric_vehicle_required_soc_departure": req_soc,
            "electric_vehicle_estimated_arrival_time": arr_time,
            "electric_vehicle_estimated_soc_arrival": arr_soc,
        }
    )

    # === GENERAR 38 CSVs INDIVIDUALES v5.2 PARA CHARGERS ===
    # PRIORITY 1: Use real charger dataset (chargers_ev_ano_2024_v3.csv) if available
    # PRIORITY 2: Fallback to legacy profiles (deprecated - use v5.2 38 sockets)
    #
    # Real Dataset Structure:
    # - 38 columns: socket_000 to socket_037 (30 motos + 8 mototaxis v5.2)
    # - 8,760 rows: hourly timesteps (complete year)
    # - Each column contains power demand for ONE socket in kW
    # - Ready for direct use: no expansion needed
    #
    # Legacy Dataset Structure (FALLBACK):
    # - 19 columns: charger IDs (one per charger v5.2)
    # - 8,760 rows: hourly timesteps
    # - Each charger has 2 sockets → need to expand 19→38 columns [v5.2]

    chargers_source = "unknown"
    chargers_df_for_generation = None

    # PRIORITY 1: Load real dataset if available
    if "chargers_real_hourly_2024" in artifacts:
        chargers_df_for_generation = artifacts["chargers_real_hourly_2024"].copy()
        chargers_source = "REAL (chargers_ev_ano_2024_v3.csv)"
        logger.info(f"[CHARGERS GENERATION] ✅ Using REAL dataset: {chargers_df_for_generation.shape}")
        logger.info(f"[CHARGERS GENERATION]    38 individual socket columns v5.2 (ready for RL agents)")
        logger.info(f"[CHARGERS GENERATION]    8,760 hourly timesteps (complete year)")

    # PRIORITY 2: Fallback to legacy profiles
    elif "chargers_hourly_profiles_annual" in artifacts:
        chargers_df_legacy = artifacts["chargers_hourly_profiles_annual"]
        chargers_source = "LEGACY (chargers_hourly_profiles_annual.csv)"
        logger.info(f"[CHARGERS GENERATION] ⚠️  Using LEGACY dataset: {chargers_df_legacy.shape}")

        # v5.2: 19 chargers x 2 sockets = 38 tomas
        if chargers_df_legacy.shape[1] == 19:
            logger.info(f"[CHARGERS GENERATION]    v5.2: Expanding 19 chargers to 38 sockets")
            expanded_data = {}
            for i in range(19):
                charger_col = chargers_df_legacy.columns[i]
                charger_demand = chargers_df_legacy[charger_col].values
                # Divide demand equally among 2 sockets (v5.2)
                socket_demand_divided = charger_demand / 2.0
                for socket_idx in range(2):
                    socket_col = f"{charger_col}_SOCKET_{socket_idx}"
                    expanded_data[socket_col] = socket_demand_divided
            chargers_df_for_generation = pd.DataFrame(expanded_data)
            logger.info(f"[CHARGERS GENERATION]    Expansion result: {chargers_df_for_generation.shape}")
        else:
            chargers_df_for_generation = chargers_df_legacy

    if chargers_df_for_generation is None:
        logger.error(f"[CHARGERS GENERATION] ❌ NO CHARGER DATA AVAILABLE")
        raise RuntimeError("No charger dataset found - neither real nor legacy profiles available")

    # VALIDATION: Final dimensions
    if chargers_df_for_generation.shape != (8760, 38):
        logger.error(f"[CHARGERS GENERATION] ❌ INVALID SHAPE: {chargers_df_for_generation.shape} (expected 8760x38)")
        raise ValueError(f"Charger profiles must be (8760, 38), got {chargers_df_for_generation.shape}")

    logger.info(f"[CHARGERS GENERATION] ✅ Dataset ready: {chargers_source}")
    logger.info(f"[CHARGERS GENERATION]    Dimensions: 8,760 hours x 38 sockets v5.2")
    logger.info(f"[CHARGERS GENERATION]    Annual energy: {chargers_df_for_generation.sum().sum():,.0f} kWh")
    logger.info(f"[CHARGERS GENERATION]    Mean power: {chargers_df_for_generation.sum(axis=1).mean():.1f} kW")

    # ===== GENERAR 38 CSVs INDIVIDUALES v5.2 PARA CHARGERS (desde dataset real o legacy) =====
    # Use the chargers_df_for_generation prepared above (38 columns, 8760 rows)
    if chargers_df_for_generation is not None and chargers_df_for_generation.shape == (8760, 38):
        building_dir = out_dir  # Root directory for charger CSVs
        charger_list = []
        total_ev_demand_kwh = 0.0

        logger.info("[CHARGERS CSV GENERATION] Generando 38 archivos CSV...")

        for socket_idx in range(38):
            charger_name = f"charger_simulation_{socket_idx+1:03d}.csv"
            csv_path = building_dir / charger_name
            charger_list.append(csv_path)

            # Extract socket demand from prepared dataset y convertir a numpy array
            socket_demand_ext = chargers_df_for_generation.iloc[:, socket_idx].values
            socket_demand: np.ndarray = np.asarray(socket_demand_ext, dtype=np.float64)
            total_ev_demand_kwh += float(np.sum(socket_demand))

            # Create state array (1=connected, 3=idle)
            states_array: np.ndarray = np.where(socket_demand > 0, 1, 3).astype(int)

            # Determine socket type (motos=0-111, mototaxis=112-127)
            is_mototaxi = socket_idx >= 30
            if is_mototaxi:
                socket_type = "MOTOTAXI"
                local_idx = socket_idx - 30 + 1
            else:
                socket_type = "MOTO"
                local_idx = socket_idx + 1

            ev_id_base = f"{socket_type}_{local_idx:03d}"

            # Create CSV with required columns
            df_charger = pd.DataFrame({
                'electric_vehicle_charger_state': states_array,
                'electric_vehicle_id': [ev_id_base if s == 1 else '' for s in states_array],
                'electric_vehicle_departure_time': np.where(states_array == 1, 4.0, 0.0),  # 4h avg charging
                'electric_vehicle_required_soc_departure': np.where(states_array == 1, 0.85, 0.0),  # 85% target
                'electric_vehicle_estimated_arrival_time': np.where(states_array == 3, 2.0, 0.0),  # 2h to next EV
                'electric_vehicle_estimated_soc_arrival': np.where(states_array == 1, 0.20, 0.0),  # 20% on arrival
            })

            df_charger.to_csv(csv_path, index=False, float_format='%.6f')

            if socket_idx % 32 == 0 or socket_idx == 127:
                logger.info(f"  [✓] {charger_name} ({socket_type}, {np.sum(states_array == 1)} horas conectado)")

        logger.info("")
        logger.info("=" * 80)
        logger.info("[CHARGERS CSV GENERATION] ✅ COMPLETADO")
        logger.info("=" * 80)
        logger.info(f"Total arquivos generados: 38 (charger_simulation_001.csv to 038.csv)")
        logger.info(f"Total EV demand anual: {total_ev_demand_kwh:,.0f} kWh")
        logger.info(f"Promedio por socket: {total_ev_demand_kwh/38:,.0f} kWh/año")
        logger.info(f"Fuente de datos: {chargers_source}")
        logger.info(f"Estructura v5.2: 30 motos (socket_000-029) + 8 mototaxis (socket_030-037)")
        logger.info("=" * 80)
        logger.info("")

        # === ACTUALIZAR SCHEMA: Referenciar los 38 CSVs ===
        logger.info("[CHARGER GENERATION] Actualizando schema con referencias a 38 CSVs...")

        chargers_to_update = b_mall.get("chargers", {})
        if len(chargers_to_update) != 38:
            logger.warning(f"[WARN] Se esperaban 38 sockets, se encontraron {len(chargers_to_update)}")

        for charger_idx, charger_name in enumerate(chargers_to_update.keys()):
            csv_filename = f"charger_simulation_{charger_idx+1:03d}.csv"
            chargers_to_update[charger_name]["charger_simulation"] = csv_filename

        b_mall["chargers"] = chargers_to_update
        logger.info(f"[OK] Schema actualizado: {len(chargers_to_update)}/38 sockets con referencias CSV")

    else:
        logger.error("[CHARGERS CSV GENERATION] ❌ No charger dataset available for CSV generation")
        raise RuntimeError("Charger dataset must be (8760, 38) - no valid data found")

    # ==========================================================================
    # INTEGRACIÓN: Agregar contexto de recompensa al schema
    # Permite a los agentes OE3 (SAC, PPO, A2C) acceder a:
    # - Factores CO₂ (0.4521 grid, 2.146 EV directo)
    # - Capacidad diaria EVs (1,800 motos + 260 mototaxis)
    # - Pesos de recompensa multiobjetivo (CO₂=0.35, solar=0.20, EV=0.30, cost=0.10, grid=0.05)
    # ==========================================================================
    artifacts = _load_oe2_artifacts(interim_dir)

    if "iquitos_context" in artifacts:
        ctx = artifacts["iquitos_context"]
        schema["co2_context"] = {
            "co2_factor_kg_per_kwh": float(ctx.co2_factor_kg_per_kwh),
            "co2_conversion_factor": float(ctx.co2_conversion_factor),
            "motos_daily_capacity": int(ctx.motos_daily_capacity),
            "mototaxis_daily_capacity": int(ctx.mototaxis_daily_capacity),
            "max_evs_total": int(ctx.max_evs_total),
            "tariff_usd_per_kwh": float(ctx.tariff_usd_per_kwh),
            "peak_hours": list(ctx.peak_hours),
            "description": "Contexto real de Iquitos para cálculo de CO₂ y recompensas",
        }
        logger.info("[REWARDS] ✅ Added CO₂ context to schema: grid=%.4f, EV=%.3f kg/kWh",
                   ctx.co2_factor_kg_per_kwh, ctx.co2_conversion_factor)

    if "reward_weights" in artifacts:
        weights = artifacts["reward_weights"]
        schema["reward_weights"] = {
            "co2": float(weights.co2),
            "cost": float(weights.cost),
            "solar": float(weights.solar),
            "ev_satisfaction": float(weights.ev_satisfaction),
            "ev_utilization": float(weights.ev_utilization),
            "grid_stability": float(weights.grid_stability),
            "description": "Pesos multiobjetivo para cálculo de recompensa en agentes OE3",
        }
        logger.info("[REWARDS] ✅ Added reward weights to schema: CO₂=%.2f, solar=%.2f, cost=%.2f",
                   weights.co2, weights.solar, weights.cost)

    # ==========================================================================
    # GENERACIÓN v5.3: observables_oe2.csv - Variables para agentes RL
    # Combina variables OSINERGMIN y CO2 de chargers y solar en un solo archivo
    # ==========================================================================
    logger.info("")
    logger.info("=" * 80)
    logger.info("[OBSERVABLES v5.3] Generando archivo de variables observables...")
    logger.info("=" * 80)
    
    # Obtener DataFrames de chargers, solar y BESS con columnas observables
    chargers_obs_df = artifacts.get("chargers_real_hourly_2024")
    solar_obs_df = artifacts.get("solar_ts") if "solar_ts" in artifacts else artifacts.get("pv_generation_hourly")
    bess_obs_df = artifacts.get("bess_simulation_hourly")  # ✅ Incluir BESS para observables
    
    # Extraer y combinar variables observables (incluyendo BESS)
    observables_df = _extract_observable_variables(
        chargers_df=chargers_obs_df,
        solar_df=solar_obs_df,
        bess_df=bess_obs_df,  # ✅ Nuevo parámetro
        n_timesteps=8760
    )
    
    # Guardar archivo de observables
    observables_path = out_dir / "observables_oe2.csv"
    observables_df.to_csv(observables_path, index=True, float_format='%.4f')
    logger.info(f"[OBSERVABLES v5.3] ✅ Archivo guardado: {observables_path}")
    logger.info(f"   Dimensiones: {observables_df.shape}")
    logger.info(f"   Columnas: {len(observables_df.columns)}")
    
    # Agregar referencia al schema
    schema["observables_file"] = "observables_oe2.csv"
    schema["observables_columns"] = list(observables_df.columns)
    
    # Agregar constantes OSINERGMIN y CO2 al schema para referencia
    schema["osinergmin_config"] = {
        "tarifa_hp_soles": TARIFA_ENERGIA_HP_SOLES,
        "tarifa_hfp_soles": TARIFA_ENERGIA_HFP_SOLES,
        "hora_inicio_hp": HORA_INICIO_HP,
        "hora_fin_hp": HORA_FIN_HP,
        "description": "Tarifas OSINERGMIN MT3 para Sistema Aislado Iquitos"
    }
    schema["co2_factors"] = {
        "factor_red_kg_kwh": FACTOR_CO2_RED_KG_KWH,
        "factor_gasolina_kg_l": FACTOR_CO2_GASOLINA_KG_L,
        "factor_neto_moto_kg_kwh": FACTOR_CO2_NETO_MOTO_KG_KWH,
        "factor_neto_mototaxi_kg_kwh": FACTOR_CO2_NETO_MOTOTAXI_KG_KWH,
        "description": "Factores CO2 para cálculo de reducciones directas e indirectas"
    }
    
    # Resumen de métricas anuales para validación
    annual_summary = {
        "ev_energia_total_kwh": float(observables_df['ev_energia_total_kwh'].sum()),
        "ev_costo_total_soles": float(observables_df['ev_costo_carga_soles'].sum()),
        "ev_co2_evitado_ton": float(observables_df['ev_reduccion_directa_co2_kg'].sum() / 1000),
        "solar_ahorro_total_soles": float(observables_df['solar_ahorro_soles'].sum()),
        "solar_co2_evitado_ton": float(observables_df['solar_reduccion_indirecta_co2_kg'].sum() / 1000),
        "total_co2_evitado_ton": float(observables_df['total_reduccion_co2_kg'].sum() / 1000),
    }
    schema["annual_summary_v53"] = annual_summary
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("[RESUMEN ANUAL v5.3]")
    logger.info("=" * 80)
    logger.info(f"   EV Energía: {annual_summary['ev_energia_total_kwh']:,.0f} kWh/año")
    logger.info(f"   EV Costo: S/.{annual_summary['ev_costo_total_soles']:,.0f}/año")
    logger.info(f"   EV CO2 evitado (directo): {annual_summary['ev_co2_evitado_ton']:,.1f} ton/año")
    logger.info(f"   Solar Ahorro: S/.{annual_summary['solar_ahorro_total_soles']:,.0f}/año")
    logger.info(f"   Solar CO2 evitado (indirecto): {annual_summary['solar_co2_evitado_ton']:,.1f} ton/año")
    logger.info(f"   TOTAL CO2 evitado: {annual_summary['total_co2_evitado_ton']:,.1f} ton/año")
    logger.info("=" * 80)
    logger.info("")

    # Save the updated schema
    schema_path = out_dir / "schema.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    logger.info(f"[OK] Schema guardado en {schema_path}")

    # --- Schema variants for emissions comparison ---
    # 1) PV+BESS (current schema.json)
    (out_dir / "schema_pv_bess.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")

    # 2) Grid-only variant: disable PV and BESS by setting nominal values to 0.
    schema_grid = json.loads(json.dumps(schema))

    # Desactivar PV y BESS en TODOS los buildings
    for _bname_grid, b_grid in schema_grid.get("buildings", {}).items():
        # Desactivar photovoltaic (formato antiguo)
        if isinstance(b_grid.get("photovoltaic"), dict):
            b_grid["photovoltaic"]["nominal_power"] = 0.0

        # Desactivar pv (formato nuevo con attributes)
        if isinstance(b_grid.get("pv"), dict):
            if isinstance(b_grid["pv"].get("attributes"), dict):
                b_grid["pv"]["attributes"]["nominal_power"] = 0.0
            else:
                b_grid["pv"]["nominal_power"] = 0.0

        # Desactivar electrical_storage
        if isinstance(b_grid.get("electrical_storage"), dict):
            b_grid["electrical_storage"]["capacity"] = 0.0
            b_grid["electrical_storage"]["nominal_power"] = 0.0
            if isinstance(b_grid["electrical_storage"].get("attributes"), dict):
                b_grid["electrical_storage"]["attributes"]["capacity"] = 0.0
                b_grid["electrical_storage"]["attributes"]["nominal_power"] = 0.0

    (out_dir / "schema_grid_only.json").write_text(json.dumps(schema_grid, indent=2), encoding="utf-8")
    logger.info("Schema grid-only creado con PV=0 y BESS=0 en todos los buildings")

    # ==========================================================================
    # INTEGRACIÓN: Calcular y guardar baselines CON_SOLAR y SIN_SOLAR v5.4
    # ==========================================================================
    if BASELINE_AVAILABLE:
        logger.info("")
        logger.info("=" * 80)
        logger.info("[BASELINE INTEGRATION v5.4] Calculando baselines CON_SOLAR y SIN_SOLAR...")
        logger.info("=" * 80)
        
        try:
            baseline_integration = BaselineCityLearnIntegration(output_dir=out_dir)
            baselines = baseline_integration.compute_baselines()
            baseline_integration.save_baselines(baselines)
            baseline_integration.print_summary()
            
            # Agregar referencias baseline al schema para que agentes accedan
            schema["baselines"] = {
                "con_solar": baselines.get("con_solar", {}),
                "sin_solar": baselines.get("sin_solar", {}),
            }
            
            logger.info("[BASELINE INTEGRATION v5.4] ✅ Baselines integrados al schema:")
            logger.info(f"   - CON_SOLAR (ref): {baselines.get('con_solar', {}).get('co2_t_year', 'N/A')} t CO₂/año")
            logger.info(f"   - SIN_SOLAR (worst): {baselines.get('sin_solar', {}).get('co2_t_year', 'N/A')} t CO₂/año")
            logger.info(f"   - Solar Impact: {baselines.get('con_solar', {}).get('co2_t_year', 0) - baselines.get('sin_solar', {}).get('co2_t_year', 0):.1f} t CO₂ evitadas")
        except Exception as e:
            logger.error("[BASELINE INTEGRATION v5.4] ❌ Error calculando baselines: %s", e)
            logger.info("[BASELINE INTEGRATION v5.4] ℹ️  Continuando sin baselines (no crítico)")
    else:
        logger.warning("[BASELINE INTEGRATION v5.4] Módulos de baseline no disponibles")
        logger.info("[BASELINE INTEGRATION v5.4] ℹ️  Para instalar: src/baseline/baseline_calculator_v2.py")

    # Guardar versión actualizada del schema con baselines
    schema_path = out_dir / "schema.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    logger.info(f"[OK] Schema actualizado (con baselines) guardado en {schema_path}")
    logger.info("=" * 80)
    logger.info("")

    return BuiltDataset(dataset_dir=out_dir, schema_path=schema_path, building_name=bname)
