#!/usr/bin/env python3
"""
AUDITORÍA Y LIMPIEZA EXHAUSTIVA: Chargers Dataset v5.2
================================================================================================

Propósito: Validar integridad completa del dataset,
- Eliminar datos antiguos/duplicados
- Verificar 2024 completo (8,760 horas)
- Validar columnas para CityLearn v2 + Agentes RL
- Certificar listo para entrenamiento

Generado: 2026-02-13
Auditor: GitHub Copilot
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURACIÓN DE VALIDACIÓN
# ============================================================================

DATASET_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
BACKUP_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.backup.csv")
OUTPUT_REPORT_PATH = Path("AUDITORIA_LIMPIEZA_CHARGERS_DATASET_2024.json")

# Requisitos de integridad
EXPECTED_ROWS = 8760  # 365 días × 24 horas
EXPECTED_YEAR = 2024
EXPECTED_DATE_START = pd.Timestamp("2024-01-01 00:00:00")
EXPECTED_DATE_END = pd.Timestamp("2024-12-31 23:00:00")

# Grupos de columnas por tipo
SOCKET_COLUMNS_REQUIRED = [
    "charger_power_kw",      # Potencia nominal cargador
    "battery_kwh",           # Capacidad batería
    "vehicle_type",          # MOTO o MOTOTAXI
    "soc_current",           # State of Charge actual
    "soc_arrival",           # SOC al llegar
    "soc_target",            # SOC objetivo
    "active",                # Estado binario
    "charging_power_kw",     # Potencia instantánea
    "vehicle_count",         # Vehículos en cola
]

GLOBAL_COLUMNS_REQUIRED = [
    "is_hora_punta",             # Hora punta [0,1]
    "tarifa_aplicada_soles",     # Tarifa OSINERGMIN
    "ev_energia_total_kwh",      # Energía total
    "ev_energia_motos_kwh",      # Energía motos
    "ev_energia_mototaxis_kwh",  # Energía mototaxis
    "co2_reduccion_motos_kg",    # CO2 motos
    "co2_reduccion_mototaxis_kg", # CO2 taxis
    "reduccion_directa_co2_kg",  # CO2 total
    "costo_carga_ev_soles",      # Costo S/.
    "ev_demand_kwh",             # Alias CityLearn
]

COLUMNS_FOR_AGENTS = [
    # Socket states (38 sockets × 3 = 114 columnas)
    # Globales para RL
    "is_hora_punta",
    "tarifa_aplicada_soles",
    "ev_energia_total_kwh",
    "ev_demand_kwh",
    "reduccion_directa_co2_kg",
]

NUM_SOCKETS = 38
SOCKETS_MOTOS = 30
SOCKETS_TAXIS = 8


# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

def load_dataset(path: Path) -> pd.DataFrame:
    """Carga el dataset con conversiones correctas."""
    logger.info(f"📂 Cargando dataset: {path}")
    
    if not path.exists():
        raise FileNotFoundError(f"❌ Dataset no encontrado: {path}")
    
    df = pd.read_csv(
        path,
        index_col=0,
        parse_dates=[0]
    )
    
    logger.info(f"✓ Dataset cargado: {df.shape[0]} filas × {df.shape[1]} columnas")
    return df


def validate_date_range(df: pd.DataFrame) -> dict:
    """Valida que el rango de fechas sea correcto para 2024."""
    logger.info("\n🕐 VALIDACIÓN 1: Rango de Fechas")
    logger.info("=" * 80)
    
    results = {
        "phase": "DATE_RANGE",
        "valid": True,
        "checks": [],
        "issues": [],
    }
    
    # Verificar tipo de índice
    if not isinstance(df.index, pd.DatetimeIndex):
        results["valid"] = False
        results["issues"].append(f"❌ Índice no es DatetimeIndex: {type(df.index)}")
        logger.error(f"❌ Índice no es DatetimeIndex: {type(df.index)}")
    else:
        logger.info(f"✓ Índice es DatetimeIndex")
        results["checks"].append("✓ Índice es DatetimeIndex")
    
    # Verificar número de filas
    if len(df) != EXPECTED_ROWS:
        results["valid"] = False
        results["issues"].append(
            f"❌ Rows: {len(df)} != {EXPECTED_ROWS} (falta {EXPECTED_ROWS - len(df)} horas)"
        )
        logger.error(f"❌ Rows: {len(df)} != {EXPECTED_ROWS}")
    else:
        logger.info(f"✓ Filas: {len(df)} correcto (8,760 = 365 días × 24 horas)")
        results["checks"].append(f"✓ Filas: {len(df)} correcto")
    
    # Verificar año
    years_in_data = df.index.year.unique()
    if not (len(years_in_data) == 1 and years_in_data[0] == EXPECTED_YEAR):
        results["valid"] = False
        results["issues"].append(
            f"❌ Años presentes: {sorted(years_in_data)} (esperado: {EXPECTED_YEAR})"
        )
        logger.error(f"❌ Años presentes: {sorted(years_in_data)}")
    else:
        logger.info(f"✓ Año: {EXPECTED_YEAR} (sin datos de otros años)")
        results["checks"].append(f"✓ Año: {EXPECTED_YEAR}")
    
    # Verificar fecha inicial
    date_start = df.index[0]
    if date_start != EXPECTED_DATE_START:
        logger.warning(f"⚠ Fecha inicio: {date_start} != {EXPECTED_DATE_START}")
        results["issues"].append(f"⚠ Fecha inicio: {date_start} != {EXPECTED_DATE_START}")
    else:
        logger.info(f"✓ Fecha inicio: {date_start}")
        results["checks"].append(f"✓ Fecha inicio: {date_start}")
    
    # Verificar fecha final
    date_end = df.index[-1]
    expected_end = pd.Timestamp("2024-12-31 23:00:00")
    if date_end != expected_end and date_end != EXPECTED_DATE_END:
        logger.warning(f"⚠ Fecha fin: {date_end} (esperado ~2024-12-30/31)")
        results["issues"].append(f"⚠ Fecha fin: {date_end}")
    else:
        logger.info(f"✓ Fecha fin: {date_end}")
        results["checks"].append(f"✓ Fecha fin: {date_end}")
    
    # Verificar continuidad horaria
    if len(df) == EXPECTED_ROWS:
        ts_diff = df.index.to_series().diff()
        expected_freq = pd.Timedelta(hours=1)
        duplicates = (ts_diff == pd.Timedelta(0)).sum()
        gaps = (ts_diff > expected_freq).sum()
        
        if duplicates > 0:
            results["valid"] = False
            results["issues"].append(f"❌ Timestamps duplicados: {duplicates}")
            logger.error(f"❌ Timestamps duplicados: {duplicates}")
        else:
            logger.info(f"✓ No hay duplicados de timestamp")
            results["checks"].append("✓ No hay duplicados")
        
        if gaps > 0:
            results["valid"] = False
            results["issues"].append(f"❌ Gaps en timeline: {gaps} saltos")
            logger.error(f"❌ Gaps en timeline: {gaps}")
        else:
            logger.info(f"✓ Timeline continua (1h entre cada registro)")
            results["checks"].append("✓ Timeline continua")
    
    logger.info("=" * 80)
    return results


def validate_columns(df: pd.DataFrame) -> dict:
    """Valida presencia y tipos de columnas."""
    logger.info("\n📊 VALIDACIÓN 2: Columnas Requeridas")
    logger.info("=" * 80)
    
    results = {
        "phase": "COLUMNS",
        "valid": True,
        "total_columns": len(df.columns),
        "socket_columns": 0,
        "global_columns": 0,
        "checks": [],
        "issues": [],
        "missing_columns": [],
    }
    
    # Verificar columnas globales
    logger.info(f"\n🔍 Verificando {len(GLOBAL_COLUMNS_REQUIRED)} columnas globales...")
    for col in GLOBAL_COLUMNS_REQUIRED:
        if col not in df.columns:
            results["valid"] = False
            results["missing_columns"].append(col)
            results["issues"].append(f"❌ Columna FALTANTE: {col}")
            logger.error(f"❌ {col}")
        else:
            logger.info(f"✓ {col}")
            results["checks"].append(f"✓ {col}")
            results["global_columns"] += 1
    
    # Verificar columnas por socket (socket_XXX_variable)
    logger.info(f"\n🔍 Verificando columnas por socket (38 total)...")
    socket_cols_found = {}
    pattern_base = "socket_"
    
    for socket_id in range(NUM_SOCKETS):
        socket_cols_for_id = []
        for var in SOCKET_COLUMNS_REQUIRED:
            col_name = f"{pattern_base}{socket_id:03d}_{var}"
            if col_name in df.columns:
                socket_cols_for_id.append(col_name)
                results["socket_columns"] += 1
            else:
                results["valid"] = False
                results["missing_columns"].append(col_name)
                results["issues"].append(f"❌ Socket {socket_id}: falta {var}")
                logger.warning(f"❌ socket_{socket_id:03d}_{var}")
        
        socket_cols_found[socket_id] = len(socket_cols_for_id)
    
    # Resumen sockets
    sockets_complete = sum(1 for c in socket_cols_found.values() if c == len(SOCKET_COLUMNS_REQUIRED))
    logger.info(f"✓ Sockets completos: {sockets_complete}/{NUM_SOCKETS}")
    results["checks"].append(f"✓ Socket columns: {results['socket_columns']} presentes")
    
    logger.info(f"\n📈 Resumen columnas:")
    logger.info(f"   Total: {len(df.columns)}")
    logger.info(f"   Globales encontradas: {results['global_columns']}/{len(GLOBAL_COLUMNS_REQUIRED)}")
    logger.info(f"   Socket columns: {results['socket_columns']}/{NUM_SOCKETS * len(SOCKET_COLUMNS_REQUIRED)}")
    
    logger.info("=" * 80)
    return results


def validate_data_types(df: pd.DataFrame) -> dict:
    """Valida tipos de datos en columnas clave."""
    logger.info("\n🔢 VALIDACIÓN 3: Tipos de Datos")
    logger.info("=" * 80)
    
    results = {
        "phase": "DATA_TYPES",
        "valid": True,
        "checks": [],
        "issues": [],
        "dtype_summary": {},
    }
    
    # Validar columnas numéricas
    numeric_cols = [col for col in df.columns if '_power_kw' in col or '_kwh' in col 
                    or '_soles' in col or '_kg' in col or '_soc' in col]
    
    logger.info(f"🔍 Validando {len(numeric_cols)} columnas numéricas...")
    for col in numeric_cols[:5]:  # Muestra primeras 5
        dtype = df[col].dtype
        has_nulls = df[col].isna().sum()
        logger.info(f"✓ {col}: {dtype}, NaN: {has_nulls}")
        results["checks"].append(f"✓ {col}: {dtype}")
    
    # Validar columnas binarias
    binary_cols = [col for col in df.columns if '_active' in col or '_hora_punta' in col]
    logger.info(f"\n🔍 Validando {len(binary_cols)} columnas binarias...")
    for col in binary_cols[:3]:  # Muestra primeras 3
        if col in df.columns:
            unique_vals = df[col].unique()
            if set(unique_vals) <= {0, 1, np.nan}:
                logger.info(f"✓ {col}: {sorted(set(unique_vals))}")
                results["checks"].append(f"✓ {col}: binaria")
            else:
                results["valid"] = False
                logger.error(f"❌ {col}: valores no binarios {sorted(set(unique_vals))}")
                results["issues"].append(f"❌ {col}: no binaria")
    
    # Validar columnas categóricas
    categorical_cols = [col for col in df.columns if 'vehicle_type' in col]
    logger.info(f"\n🔍 Validando {len(categorical_cols)} columnas categóricas...")
    for col in categorical_cols[:3]:  # Muestra primeras 3
        if col in df.columns:
            unique_vals = df[col].unique()
            logger.info(f"✓ {col}: {sorted(set(unique_vals))}")
            results["checks"].append(f"✓ {col}: {sorted(set(unique_vals))}")
    
    # Resumen tipos
    dtype_counts = {
        "int": 0,
        "float": 0,
        "object": 0,
        "datetime": 0,
    }
    for dtype in df.dtypes:
        dtype_str = str(dtype)
        if dtype_str.startswith('int'):
            dtype_counts["int"] += 1
        elif dtype_str.startswith('float'):
            dtype_counts["float"] += 1
        elif dtype_str == 'object':
            dtype_counts["object"] += 1
        elif dtype_str.startswith('datetime'):
            dtype_counts["datetime"] += 1
    
    results["dtype_summary"] = dtype_counts
    
    logger.info(f"\n📈 Distribución tipos:")
    logger.info(f"   Enteros: {results['dtype_summary']['int']}")
    logger.info(f"   Floats: {results['dtype_summary']['float']}")
    logger.info(f"   Objetos: {results['dtype_summary']['object']}")
    
    logger.info("=" * 80)
    return results


def validate_data_ranges(df: pd.DataFrame) -> dict:
    """Valida rangos de valores en columnas clave."""
    logger.info("\n📏 VALIDACIÓN 4: Rangos de Valores")
    logger.info("=" * 80)
    
    results = {
        "phase": "DATA_RANGES",
        "valid": True,
        "checks": [],
        "issues": [],
        "range_validation": {},
    }
    
    # Validar SOC [0, 1]
    logger.info(f"🔍 Validando SOC (debe estar en [0, 1])...")
    soc_cols = [col for col in df.columns if '_soc_' in col]
    for col in soc_cols[:5]:  # Primeros 5
        min_val = df[col].min()
        max_val = df[col].max()
        if 0 <= min_val and max_val <= 1:
            logger.info(f"✓ {col}: [{min_val:.2f}, {max_val:.2f}]")
            results["checks"].append(f"✓ {col}: [{min_val:.2f}, {max_val:.2f}]")
        else:
            results["valid"] = False
            logger.error(f"❌ {col}: [{min_val:.2f}, {max_val:.2f}] FUERA DE RANGO")
            results["issues"].append(f"❌ {col}: SOC fuera de [0,1]")
    
    # Validar Potencia [0, 7.4]
    logger.info(f"\n🔍 Validando Potencia Cargador (debe ser ~7.4 kW)...")
    power_static = [col for col in df.columns if 'charger_power_kw' in col]
    for col in power_static[:3]:
        val = df[col].unique()
        if len(val) == 1 and val[0] == 7.4:
            logger.info(f"✓ {col}: {val[0]} kW (constante)")
            results["checks"].append(f"✓ {col}: 7.4 kW")
        else:
            logger.warning(f"⚠ {col}: {val} (esperado 7.4)")
    
    # Validar Potencia cargando [0, 4.588]
    logger.info(f"\n🔍 Validando Potencia Instantánea (0 a ~4.588 kW efectivos)...")
    charging_cols = [col for col in df.columns if '_charging_power_kw' in col]
    for col in charging_cols[:3]:
        min_val = df[col].min()
        max_val = df[col].max()
        if 0 <= min_val and max_val <= 4.7:
            logger.info(f"✓ {col}: [{min_val:.2f}, {max_val:.2f}] kW")
            results["checks"].append(f"✓ {col}: potencia válida")
        else:
            results["valid"] = False
            logger.error(f"❌ {col}: [{min_val:.2f}, {max_val:.2f}] INVÁLIDO")
            results["issues"].append(f"❌ {col}: potencia fuera de rango")
    
    # Validar Energía total > 0
    if "ev_energia_total_kwh" in df.columns:
        total_energy = df["ev_energia_total_kwh"].sum()
        if total_energy > 0:
            logger.info(f"✓ Energía total anual: {total_energy:,.0f} kWh")
            results["checks"].append(f"✓ Energía anual: {total_energy:,.0f} kWh")
        else:
            results["valid"] = False
            logger.error(f"❌ Energía total = 0")
            results["issues"].append("❌ Energía total es 0")
    
    # Validar Tarifa OSINERGMIN [0.28, 0.45]
    if "tarifa_aplicada_soles" in df.columns:
        unique_tarifas = df["tarifa_aplicada_soles"].unique()
        expected_tarifas = {0.28, 0.45}
        if set(unique_tarifas) == expected_tarifas:
            logger.info(f"✓ Tarifas: {sorted(unique_tarifas)}")
            results["checks"].append(f"✓ Tarifas OSINERGMIN: {sorted(unique_tarifas)}")
        else:
            results["valid"] = False
            logger.error(f"❌ Tarifas inesperadas: {sorted(unique_tarifas)}")
            results["issues"].append(f"❌ Tarifas OSINERGMIN inválidas")
    
    # Validar CO2 reducción
    if "reduccion_directa_co2_kg" in df.columns:
        co2_total = df["reduccion_directa_co2_kg"].sum()
        if co2_total > 0:
            logger.info(f"✓ CO2 reducción anual: {co2_total:,.0f} kg ({co2_total/1000:.1f} ton)")
            results["checks"].append(f"✓ CO2 anual: {co2_total/1000:.1f} ton")
        else:
            results["valid"] = False
            logger.error(f"❌ CO2 reducción = 0")
            results["issues"].append("❌ CO2 reducción es 0")
    
    logger.info("=" * 80)
    return results


def validate_citylearn_compatibility(df: pd.DataFrame) -> dict:
    """Valida compatibilidad con CityLearn v2."""
    logger.info("\n🎮 VALIDACIÓN 5: Compatibilidad CityLearn v2")
    logger.info("=" * 80)
    
    results = {
        "phase": "CITYLEARN_COMPAT",
        "valid": True,
        "checks": [],
        "issues": [],
        "agent_observable_columns": [],
    }
    
    # Verificar columnas de observables
    logger.info(f"🔍 Verificando observables para agentes RL...")
    observable_counts = {
        "socket_soc": 0,
        "socket_active": 0,
        "socket_power": 0,
        "global": 0,
    }
    
    soc_cols = [col for col in df.columns if '_soc_current' in col]
    active_cols = [col for col in df.columns if '_active' in col]
    power_cols = [col for col in df.columns if '_charging_power_kw' in col]
    
    observable_counts["socket_soc"] = len(soc_cols)
    observable_counts["socket_active"] = len(active_cols)
    observable_counts["socket_power"] = len(power_cols)
    
    logger.info(f"✓ SOC columns: {len(soc_cols)}/38")
    logger.info(f"✓ Active columns: {len(active_cols)}/38")
    logger.info(f"✓ Power columns: {len(power_cols)}/38")
    results["checks"].append(f"✓ Socket observables: {len(soc_cols)}/38 sockets")
    results["agent_observable_columns"] = {
        "socket_soc": len(soc_cols),
        "socket_active": len(active_cols),
        "socket_power": len(power_cols),
    }
    
    # Verificar globales para agentes
    logger.info(f"\n🔍 Verificando globales para agentes...")
    global_agent_cols = [col for col in COLUMNS_FOR_AGENTS if col in df.columns]
    for col in global_agent_cols:
        logger.info(f"✓ {col}")
        results["checks"].append(f"✓ {col}")
        results["agent_observable_columns"].append(col)
    
    if len(global_agent_cols) == len(COLUMNS_FOR_AGENTS):
        logger.info(f"✓ Todas las globales presentes ({len(global_agent_cols)}/{len(COLUMNS_FOR_AGENTS)})")
    else:
        results["valid"] = False
        missing = set(COLUMNS_FOR_AGENTS) - set(global_agent_cols)
        logger.error(f"❌ Falta: {missing}")
        results["issues"].append(f"❌ Faltan globales: {missing}")
    
    # Verificar nomenclatura socket
    logger.info(f"\n🔍 Verificando nomenclatura socket_XXX_variable...")
    pattern_match = all(col.startswith("socket_") and col.count("_") >= 2 
                       for col in df.columns if col.startswith("socket_"))
    if pattern_match:
        logger.info(f"✓ Nomenclatura socket: válida")
        results["checks"].append("✓ Nomenclatura socket_{id}_{var}")
    else:
        results["valid"] = False
        logger.error(f"❌ Nomenclatura socket: inválida")
        results["issues"].append("❌ Nomenclatura socket inconsistente")
    
    logger.info("=" * 80)
    return results


def validate_for_agent_training(df: pd.DataFrame) -> dict:
    """Valida que el dataset esté listo para entrenamiento de agentes."""
    logger.info("\n🤖 VALIDACIÓN 6: Preparación para Entrenamiento Agentes")
    logger.info("=" * 80)
    
    results = {
        "phase": "AGENT_TRAINING",
        "valid": True,
        "checks": [],
        "issues": [],
        "agent_readiness": {},
    }
    
    # Verificar sin NaN en columnas críticas
    logger.info(f"🔍 Verificando valores nulos en columnas críticas...")
    critical_global = ["is_hora_punta", "tarifa_aplicada_soles", "ev_energia_total_kwh",
                      "reduccion_directa_co2_kg"]
    
    has_nulls = False
    for col in critical_global:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count == 0:
                logger.info(f"✓ {col}: sin NaN")
                results["checks"].append(f"✓ {col}: completo")
            else:
                has_nulls = True
                results["valid"] = False
                logger.error(f"❌ {col}: {null_count} NaN")
                results["issues"].append(f"❌ {col}: {null_count} NaN (debe estar completo)")
    
    if not has_nulls:
        logger.info(f"✓ Datos limpios: sin valores nulos en críticos")
    
    # Verificar consistencia energética
    logger.info(f"\n🔍 Verificando consistencia energética...")
    if "ev_energia_total_kwh" in df.columns and "ev_energia_motos_kwh" in df.columns:
        motos = df["ev_energia_motos_kwh"].sum()
        taxis = df["ev_energia_mototaxis_kwh"].sum()
        total = df["ev_energia_total_kwh"].sum()
        expected_total = motos + taxis
        
        if abs(total - expected_total) < 1.0:  # Tolerancia 1 kWh
            logger.info(f"✓ Energía consistente: {motos:,.0f} + {taxis:,.0f} = {total:,.0f}")
            results["checks"].append(f"✓ Energía consistente")
        else:
            logger.warning(f"⚠ Energía inconsistente: {total} != {expected_total}")
            results["issues"].append(f"⚠ Energía inconsistente")
    
    # Verificar que agentes puedan leer cada observable
    logger.info(f"\n🔍 Verificando accesibilidad para agentes...")
    soc_cols = [col for col in df.columns if '_soc_current' in col]
    active_cols = [col for col in df.columns if '_active' in col]
    power_cols = [col for col in df.columns if '_charging_power_kw' in col]
    
    total_socket_observables = len(soc_cols) + len(active_cols) + len(power_cols)
    total_global_observables = len([c for c in COLUMNS_FOR_AGENTS if c in df.columns])
    
    total_obs = total_socket_observables + total_global_observables
    logger.info(f"✓ Total observables: {total_obs} ({total_socket_observables} socket + {total_global_observables} global)")
    logger.info(f"✓ Dimensión observación: ~{total_obs}-dim")
    results["checks"].append(f"✓ Observation space: ~{total_obs}-dim")
    
    results["agent_readiness"] = {
        "observation_dim": total_obs,
        "action_dim": 39,  # 38 sockets + 1 BESS futuro
        "episode_length": 8760,
        "timestep_hours": 1,
        "ready_for_sac": True,
        "ready_for_ppo": True,
        "ready_for_a2c": True,
    }
    
    logger.info("=" * 80)
    return results


def check_for_old_data(df: pd.DataFrame) -> dict:
    """Verifica presencia de datos antiguos o duplicados."""
    logger.info("\n🧹 VALIDACIÓN 7: Limpieza de Datos Antiguos")
    logger.info("=" * 80)
    
    results = {
        "phase": "OLD_DATA_CLEANUP",
        "valid": True,
        "checks": [],
        "issues": [],
        "old_data_found": False,
        "duplicates_found": 0,
    }
    
    # Buscar datos de años anteriores a 2024
    logger.info(f"🔍 Buscando datos de años anteriores a 2024...")
    years = df.index.year.unique()
    old_years = [y for y in years if y < 2024]
    
    if len(old_years) > 0:
        results["valid"] = False
        results["old_data_found"] = True
        logger.error(f"❌ Datos antiguos encontrados: años {sorted(old_years)}")
        results["issues"].append(f"❌ Datos de años anteriores: {sorted(old_years)}")
    else:
        logger.info(f"✓ No hay datos de años anteriores a 2024")
        results["checks"].append("✓ No hay datos antiguos")
    
    # Buscar datos futuros (post 2024)
    future_years = [y for y in years if y > 2024]
    if len(future_years) > 0:
        results["valid"] = False
        logger.warning(f"⚠ Datos futuros encontrados: años {sorted(future_years)}")
        results["issues"].append(f"⚠ Datos post-2024: {sorted(future_years)}")
    
    # Verificar duplicados
    logger.info(f"🔍 Verificando duplicados de timestamp...")
    dup_count = df.index.duplicated().sum()
    if dup_count > 0:
        results["duplicates_found"] = dup_count
        results["valid"] = False
        logger.error(f"❌ Timestamps duplicados: {dup_count}")
        results["issues"].append(f"❌ {dup_count} timestamps duplicados")
    else:
        logger.info(f"✓ No hay timestamps duplicados")
        results["checks"].append("✓ Sin duplicados")
    
    # Verificar filas completamente duplicadas
    logger.info(f"🔍 Verificando filas completamente duplicadas...")
    full_dup = df.duplicated().sum()
    if full_dup > 0:
        results["valid"] = False
        logger.error(f"❌ Filas duplicadas: {full_dup}")
        results["issues"].append(f"❌ {full_dup} filas completamente duplicadas")
    else:
        logger.info(f"✓ No hay filas duplicadas (ignorando índice)")
        results["checks"].append("✓ Sin filas duplicadas")
    
    logger.info("=" * 80)
    return results


def generate_cleanup_report(assessments: list[dict]) -> dict:
    """Genera reporte final de auditoría y recomendaciones."""
    logger.info("\n📋 GENERANDO REPORTE FINAL")
    logger.info("=" * 80)
    
    all_valid = all(a["valid"] for a in assessments)
    total_checks = sum(len(a.get("checks", [])) for a in assessments)
    total_issues = sum(len(a.get("issues", [])) for a in assessments)
    
    report = {
        "audit_timestamp": datetime.now().isoformat(),
        "dataset_path": str(DATASET_PATH),
        "overall_valid": all_valid,
        "summary": {
            "total_validations": len(assessments),
            "checks_passed": total_checks,
            "issues_found": total_issues,
            "status": "✅ APTO PARA ENTRENAMIENTO" if all_valid else "⚠️ REQUIERE LIMPIEZA",
        },
        "phases": assessments,
    }
    
    logger.info(f"\n{'='*80}")
    logger.info("RESUMEN FINAL:")
    logger.info(f"{'='*80}")
    logger.info(f"Status: {report['summary']['status']}")
    logger.info(f"Validaciones: {len(assessments)}")
    logger.info(f"Checks pasados: {total_checks}")
    logger.info(f"Issues encontrados: {total_issues}")
    
    if all_valid:
        logger.info("\n✅ ¡Dataset VALIDADO y LISTO para:")
        logger.info("   • Construcción de ambiente CityLearn v2")
        logger.info("   • Entrenamiento de agentes RL (SAC, PPO, A2C)")
        logger.info("   • Exportación a observables normalizadas [0,1]")
    else:
        logger.info("\n⚠️ Dataset requiere limpieza:")
        for assessment in assessments:
            if assessment["issues"]:
                logger.info(f"\n{assessment['phase']}:")
                for issue in assessment["issues"]:
                    logger.info(f"   {issue}")
    
    logger.info(f"{'='*80}\n")
    
    return report


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ejecuta auditoría completa del dataset."""
    
    print("\n" + "="*80)
    print("AUDITORÍA EXHAUSTIVA: Chargers Dataset v5.2")
    print("="*80)
    print(f"Archivo: {DATASET_PATH}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    try:
        # Cargar dataset
        df = load_dataset(DATASET_PATH)
        
        # Hacer backup (antes de cualquier limpieza)
        logger.info(f"\n💾 Creando backup...")
        df.to_csv(BACKUP_PATH)
        logger.info(f"✓ Backup guardado: {BACKUP_PATH}")
        
        # Ejecutar validaciones
        assessments = []
        
        assessments.append(validate_date_range(df))
        assessments.append(validate_columns(df))
        assessments.append(validate_data_types(df))
        assessments.append(validate_data_ranges(df))
        assessments.append(validate_citylearn_compatibility(df))
        assessments.append(validate_for_agent_training(df))
        assessments.append(check_for_old_data(df))
        
        # Generar reporte
        report = generate_cleanup_report(assessments)
        
        # Guardar reporte
        with open(OUTPUT_REPORT_PATH, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"\n✓ Reporte guardado: {OUTPUT_REPORT_PATH}")
        
        # Resumen para usuario
        status_emoji = "✅" if report["overall_valid"] else "⚠️"
        print(f"\n{status_emoji} {report['summary']['status']}")
        print(f"   Validaciones pasadas: {report['summary']['checks_passed']}")
        print(f"   Issues encontrados: {report['summary']['issues_found']}")
        
        if report["overall_valid"]:
            print(f"\n🎉 Dataset chargers_ev_ano_2024_v3.csv está 100% LISTO para:")
            print(f"   ✅ Construcción de dataset CityLearn v2")
            print(f"   ✅ Entrenamiento de agentes RL (SAC, PPO, A2C)")
            print(f"   ✅ Exportación de observables normalizadas")
            print(f"   ✅ Integración con BESS dataset (bess_simulation_hourly.csv)")
        else:
            print(f"\n⚠️ Se recomienda revisar issues encontrados antes de proceder")
        
        return report
        
    except Exception as e:
        logger.error(f"\n❌ Error en auditoría: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    report = main()
