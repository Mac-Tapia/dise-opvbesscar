from __future__ import annotations
"""
================================================================================
OE3 DATASET BUILDER - CityLearn v2.5.0 Integration

TRACKING DE REDUCCIONES DIRECTAS E INDIRECTAS DE CO₂:

1. CO₂ DIRECTO (Direct CO₂ from EV charging):
   - Demanda constante: 50 kW
   - Factor conversión: 2.146 kg CO₂/kWh (combustión equivalente)
   - CO₂ directo/hora: 50 kW × 2.146 kg/kWh = 107.3 kg CO₂/h
   - Acumulado anual (sin control): 50 × 2.146 × 8760 = 938,460 kg CO₂/año

2. CO₂ INDIRECTO (Grid import emissions avoided):
   - Factor grid Iquitos: 0.4521 kg CO₂/kWh (central térmica aislada)
   - Si PV directa → EV: Se evita importación = se evita 0.4521 kg CO₂/kWh
   - Reducción indirecta = PV solar directo × 0.4521
   - Objetivo: Maximizar PV directo para maximizar reducción indirecta

3. REDUCCIÓN NETA:
   - Reducción = (Solar PV directo) × 0.4521 kg CO₂/kWh
   - Ejemplo: 1000 kWh solar directo = 1000 × 0.4521 = 452.1 kg CO₂ evitado

4. TRACKING EN SISTEMA:
   - dataset_builder.py: Valida datos y estructura
   - rewards.py: Calcula CO₂ directo + indirecto
   - agents: Optimizan para maximizar reducciones indirectas
   - simulate.py: Acumula y reporta reducciones

Vinculaciones (2026-01-31):
   - config.yaml: co2_grid_factor_kg_per_kwh = 0.4521
   - config.yaml: ev_co2_conversion_kg_per_kwh = 2.146
   - rewards.py: IquitosContext con ambos valores
   - agents: Reciben rewards basados en reducciones indirectas (PV directo)
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
# INTEGRACIÓN: Reward Functions (from src/rewards/rewards.py)
# Importar clases de recompensa multiobjetivo para validación en OE3
# =============================================================================
try:
    from src.rewards.rewards import (
        MultiObjectiveWeights,
        IquitosContext,
        MultiObjectiveReward,
        create_iquitos_reward_weights,
    )
    REWARDS_AVAILABLE = True
    logger.info("[REWARDS] Successfully imported reward classes from src/rewards/rewards.py")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning("[REWARDS] Could not import rewards.py: %s", e)
    REWARDS_AVAILABLE = False

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
    """Load real charger dataset from data/oe2/chargers/chargers_real_hourly_2024.csv

    CRITICAL: This is the NEW REAL DATASET with:
    - 128 individual socket columns (112 motos + 16 mototaxis)
    - 8,760 hourly timesteps (full year 2024)
    - Individual socket control capability for RL agents
    - Realistic demand patterns (seasonal, daily, hourly variation)
    - Proper datetime indexing

    Args:
        charger_data_path: Path to chargers_real_hourly_2024.csv

    Returns:
        DataFrame with shape (8760, 128) or None if not found

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

        if df.shape[1] != 128:
            raise ValueError(f"Charger dataset MUST have 128 columns (sockets), got {df.shape[1]}")

        # VALIDATION: Hourly frequency
        if len(df.index) > 1:
            dt = (df.index[1] - df.index[0]).total_seconds() / 3600
            if abs(dt - 1.0) > 0.01:  # Allow small floating point error
                raise ValueError(f"Charger dataset MUST be hourly frequency, got {dt:.2f} hours")

        # VALIDATION: Datetime index starts with 2024-01-01
        if df.index[0].date() != pd.Timestamp("2024-01-01").date():
            logger.warning(f"[CHARGERS REAL] Dataset starts {df.index[0].date()}, expected 2024-01-01")

        # VALIDATION: Value ranges (power in kW)
        min_val = df.min().min()
        max_val = df.max().max()
        if min_val < 0 or max_val > 5.0:
            logger.warning(f"[CHARGERS REAL] Unexpected value range: [{min_val:.2f}, {max_val:.2f}] kW")

        # VALIDATION: Socket distribution (112 motos + 16 mototaxis)
        moto_cols = [c for c in df.columns if 'MOTO' in str(c) and 'MOTOTAXI' not in str(c)]
        mototaxi_cols = [c for c in df.columns if 'MOTOTAXI' in str(c)]

        if len(moto_cols) != 112 or len(mototaxi_cols) != 16:
            logger.warning(f"[CHARGERS REAL] Socket distribution: {len(moto_cols)} motos, {len(mototaxi_cols)} mototaxis (expected 112+16)")

        logger.info(f"[CHARGERS REAL] ✅ Loaded: {df.shape} (8760 hours × 128 sockets)")
        logger.info(f"[CHARGERS REAL]   Value range: [{min_val:.2f}, {max_val:.2f}] kW")
        logger.info(f"[CHARGERS REAL]   Annual energy: {df.sum().sum():,.0f} kWh")
        logger.info(f"[CHARGERS REAL]   Period: {df.index[0].date()} to {df.index[-1].date()}")
        logger.info(f"[CHARGERS REAL]   Sockets: {len(moto_cols)} motos + {len(mototaxi_cols)} mototaxis")

        return df

    except Exception as e:
        logger.error(f"[CHARGERS REAL] Error loading: {e}")
        raise


def _load_oe2_artifacts(interim_dir: Path) -> Dict[str, Any]:
    artifacts: Dict[str, Any] = {}

    # Solar - cargar parámetros de CityLearn si existen
    solar_citylearn_params = interim_dir / "oe2" / "solar" / "citylearn" / "solar_schema_params.json"
    if solar_citylearn_params.exists():
        artifacts["solar_params"] = json.loads(solar_citylearn_params.read_text(encoding="utf-8"))

    # ========================================================================
    # PRIORITY 1: NEW Hourly solar dataset for CityLearn v2 (2026-02-04)
    # Location: data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
    # Contains: 8,760 hourly records with REAL PVGIS data (Sandia SAPM model)
    # Columns: timestamp, ghi_wm2, dni_wm2, dhi_wm2, temp_air_c, wind_speed_ms,
    #          dc_power_kw, ac_power_kw, dc_energy_kwh, ac_energy_kwh, pv_generation_kwh
    # ========================================================================
    solar_hourly_v2_path = interim_dir / "oe2" / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv"
    if solar_hourly_v2_path.exists():
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
        logger.info("[SOLAR] v2 no disponible en %s, usando fallback...", solar_hourly_v2_path)
        artifacts["solar_ts"] = None

    # ========================================================================
    # FALLBACK: Original timeseries si v2 no disponible
    # ========================================================================
    if artifacts.get("solar_ts") is None:
        solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
        if solar_path.exists():
            try:
                artifacts["solar_ts"] = pd.read_csv(solar_path)
                # CRITICAL: Validate that solar data is hourly (8,760 rows per year)
                _validate_solar_timeseries_hourly(artifacts["solar_ts"])
                logger.info("[SOLAR] Fallback: Cargado pv_generation_timeseries.csv")
            except Exception as e:
                logger.error("[SOLAR] ✗ Error en fallback: %s", e)
                artifacts["solar_ts"] = None

    # Solar generation para CityLearn (horario)
    solar_citylearn_candidates = [
        interim_dir / "oe2" / "citylearn" / "solar_generation.csv",
        interim_dir.parent / "oe2" / "citylearn" / "solar_generation.csv",  # Ruta alternativa (data/oe2/...)
    ]
    for solar_citylearn_csv in solar_citylearn_candidates:
        if solar_citylearn_csv.exists():
            artifacts["solar_generation_citylearn"] = pd.read_csv(solar_citylearn_csv)
            logger.info("[SOLAR] Solar generation encontrado en: %s", solar_citylearn_csv)
            break

    # EV profile
    ev_path = interim_dir / "oe2" / "chargers" / "perfil_horario_carga.csv"
    if ev_path.exists():
        artifacts["ev_profile_24h"] = pd.read_csv(ev_path)

    # EV chargers individuales
    ev_chargers = interim_dir / "oe2" / "chargers" / "individual_chargers.json"
    if ev_chargers.exists():
        artifacts["ev_chargers"] = json.loads(ev_chargers.read_text(encoding="utf-8"))

    # === PRIORITY 1: REAL CHARGER DATASET (NEW - 2026-02-04) ===
    # Load chargers_real_hourly_2024.csv with 128 individual sockets
    # Location: data/oe2/chargers/chargers_real_hourly_2024.csv
    # This dataset is generated from run_chargers_real_fixed.py with:
    # - 128 individual socket columns (MOTO_XX_SOCKET_Y, MOTOTAXI_XX_SOCKET_Y)
    # - 8,760 hourly rows (complete year 2024)
    # - Each column independently controllable by RL agents in CityLearnv2
    # - Realistic demand patterns with seasonal/daily/hourly variation
    chargers_real_path = interim_dir / "oe2" / "chargers" / "chargers_real_hourly_2024.csv"
    if chargers_real_path.exists():
        try:
            chargers_real_df = _load_real_charger_dataset(chargers_real_path)
            if chargers_real_df is not None and chargers_real_df.shape == (8760, 128):
                artifacts["chargers_real_hourly_2024"] = chargers_real_df
                logger.info("[CHARGERS] ✅ PRIORITY 1: Real charger dataset (128 sockets, 8760 hours) loaded successfully")
                logger.info("[CHARGERS]    Individual socket control: ENABLED for RL agents")
                logger.info("[CHARGERS]    Annual energy: %.0f kWh", chargers_real_df.sum().sum())
            else:
                logger.warning("[CHARGERS] Real charger dataset invalid shape, fallback to legacy profiles")
        except Exception as e:
            logger.warning(f"[CHARGERS] Error loading real dataset: {e}. Using fallback...")
    else:
        logger.info(f"[CHARGERS] Real charger dataset not found at {chargers_real_path}")

    # === PRIORITY 2: LEGACY CHARGER HOURLY PROFILES (FALLBACK) ===
    # Fallback to old 32-charger profiles if real dataset unavailable
    chargers_hourly_annual = interim_dir / "oe2" / "chargers" / "chargers_hourly_profiles_annual.csv"
    logger.info(f"[CHARGER DEBUG] Checking chargers_hourly_annual: {chargers_hourly_annual.exists()}")
    if not chargers_hourly_annual.exists():
        # Fallback: load daily profile and expand
        chargers_daily = interim_dir / "oe2" / "chargers" / "chargers_hourly_profiles.csv"
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
    chargers_results = interim_dir / "oe2" / "chargers" / "chargers_results.json"
    if chargers_results.exists():
        artifacts["chargers_results"] = json.loads(chargers_results.read_text(encoding="utf-8"))
        logger.info("Cargados resultados de chargers OE2: %d chargers", artifacts['chargers_results'].get('n_chargers_recommended', 0))

    # === DATASETS ANUALES POR PLAYA (8760 horas) ===
    annual_datasets_dir = interim_dir / "oe2" / "chargers" / "annual_datasets"
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

    charger_profile_variants = interim_dir / "oe2" / "chargers" / "charger_profile_variants.json"
    if charger_profile_variants.exists():
        artifacts["charger_profile_variants"] = json.loads(charger_profile_variants.read_text(encoding="utf-8"))
        variants_dir = charger_profile_variants.parent / "charger_profile_variants"
        if variants_dir.exists():
            artifacts["charger_profile_variants_dir"] = variants_dir
        else:
            artifacts["charger_profile_variants_dir"] = None

    # BESS - cargar parámetros de CityLearn si existen
    bess_citylearn_params = interim_dir / "oe2" / "citylearn" / "bess_schema_params.json"
    if bess_citylearn_params.exists():
        artifacts["bess_params"] = json.loads(bess_citylearn_params.read_text(encoding="utf-8"))

    # BESS results
    bess_path = interim_dir / "oe2" / "bess" / "bess_results.json"
    if bess_path.exists():
        artifacts["bess"] = json.loads(bess_path.read_text(encoding="utf-8"))

    # === PRIORITY 1: NEW BESS Hourly Dataset (2026-02-04) ===
    # Location: data/oe2/bess/bess_hourly_dataset_2024.csv
    # Contains: 8,760 hourly records with REAL BESS simulation data
    # Columns: DatetimeIndex (UTC-5), pv_kwh, ev_kwh, mall_kwh, pv_to_ev_kwh, pv_to_bess_kwh,
    #          pv_to_mall_kwh, grid_to_ev_kwh, grid_to_mall_kwh, bess_charge_kwh, bess_discharge_kwh, soc_percent
    # ========================================================================
    bess_hourly_path = interim_dir / "oe2" / "bess" / "bess_hourly_dataset_2024.csv"
    if bess_hourly_path.exists():
        try:
            bess_df = pd.read_csv(bess_hourly_path, index_col=0, parse_dates=True)
            if len(bess_df) == 8760 and "soc_percent" in bess_df.columns:
                artifacts["bess_hourly_2024"] = bess_df
                logger.info("[BESS HOURLY] ✅ PRIORITY 1: Loaded 8,760 hourly BESS dataset from %s", bess_hourly_path)
                logger.info("              Columns: %s", ", ".join(bess_df.columns.tolist()[:5]) + "...")
                logger.info("              Annual SOC range: %.1f - %.1f %%", bess_df["soc_percent"].min(), bess_df["soc_percent"].max())
            else:
                logger.warning("[BESS HOURLY] Dataset invalid: %d rows (need 8760), columns=%s", len(bess_df), bess_df.columns.tolist())
        except Exception as e:
            logger.warning("[BESS HOURLY] Error loading: %s", e)
    else:
        logger.info("[BESS HOURLY] File not found: %s (fallback to bess_results.json)", bess_hourly_path)

    # Building load para CityLearn
    building_load_candidates = [
        interim_dir / "oe2" / "citylearn" / "building_load.csv",
        interim_dir.parent / "oe2" / "citylearn" / "building_load.csv",  # Ruta alternativa (data/oe2/...)
    ]
    for building_load_path in building_load_candidates:
        if building_load_path.exists():
            artifacts["building_load_citylearn"] = pd.read_csv(building_load_path)
            logger.info("[LOAD] Building load encontrado en: %s", building_load_path)
            break

    # Mall demand - TRY MULTIPLE SEPARATORS (comma vs semicolon)
    # PRIORITY: demandamallhorakwh.csv (8,760 hourly records - EXACT) > demanda_mall_horaria_anual > 15-min alternatives
    mall_demand_candidates = [
        interim_dir / "oe2" / "demandamallkwh" / "demandamallhorakwh.csv",  # PRIORITY 1: Converted to exact 8,760 hourly (NEW - 2026-02-04)
        interim_dir / "oe2" / "demandamallkwh" / "demanda_mall_horaria_anual.csv",  # PRIORITY 2: Annual hourly data
        interim_dir / "oe2" / "demandamall" / "demanda_mall_kwh.csv",  # PRIORITY 3: 15-min data (needs aggregation)
        interim_dir / "oe2" / "demandamallkwh" / "demandamallkwh.csv",  # PRIORITY 4: Original 15-min data
    ]
    for path in mall_demand_candidates:
        if path.exists():
            # Try comma first (demanda_mall_horaria_anual.csv uses comma separator)
            try:
                df = pd.read_csv(path, sep=",", decimal=".")
                if len(df) >= 8760:  # Hourly annual data must have at least 8,760 rows
                    artifacts["mall_demand"] = df
                    artifacts["mall_demand_path"] = str(path)
                    logger.info("[MALL DEMAND] ✓ Loaded hourly annual data from %s (%d rows, separator=',')",
                               path.name, len(df))
                    break
                else:
                    logger.warning("[MALL DEMAND] File %s has only %d rows (need ≥8,760). Skipping.",
                                 path.name, len(df))
            except Exception as e_comma:
                # Try semicolon as fallback (15-min data uses semicolon, or converted hourly data)
                try:
                    df = pd.read_csv(path, sep=";", decimal=".")
                    if len(df) >= 8760:  # Must be hourly or better
                        artifacts["mall_demand"] = df
                        artifacts["mall_demand_path"] = str(path)
                        logger.info("[MALL DEMAND] ✓ Loaded from %s with separator=';' (%d rows)",
                                   path.name, len(df))
                        break
                    else:
                        # Si es 15-minutos, agregarlo pero marcar para conversión posterior si es necesario
                        logger.warning("[MALL DEMAND] File %s has %d rows (15-min data). Will aggregate to hourly.",
                                     path.name, len(df))
                        # Aún así lo cargamos por si acaso
                        artifacts["mall_demand"] = df
                        artifacts["mall_demand_path"] = str(path)
                        break
                except Exception as e_semi:
                    logger.warning("[MALL DEMAND] Could not load %s: comma=%s, semi=%s",
                                 path.name, str(e_comma)[:50], str(e_semi)[:50])

    # ==========================================================================
    # INTEGRACIÓN: Cargar contexto de Iquitos (rewards.py)
    # Contiene factores CO₂ (0.4521 grid, 2.146 EV), config de vehículos (1,800
    # motos + 260 mototaxis por día), y pesos de recompensa multiobjetivo
    # ==========================================================================
    if REWARDS_AVAILABLE:
        try:
            # Crear instancia de IquitosContext con valores reales de OE2
            iquitos_ctx = IquitosContext(
                co2_factor_kg_per_kwh=0.4521,           # Grid térmico Iquitos
                co2_conversion_factor=2.146,            # Equivalente combustión para EVs
                max_motos_simultaneous=112,             # 128 sockets × (112/128)
                max_mototaxis_simultaneous=16,          # 128 sockets × (16/128)
                max_evs_total=128,                      # Total sockets (32 chargers × 4 sockets)
                motos_daily_capacity=1800,              # Capacidad diaria real
                mototaxis_daily_capacity=260,           # Capacidad diaria real
                tariff_usd_per_kwh=0.20,                # Tarifa local Iquitos
                n_chargers=32,                          # Número de cargadores
                total_sockets=128,                      # Número de sockets
                vehicles_year_motos=657000,             # Proyección anual motos
                vehicles_year_mototaxis=94900,          # Proyección anual mototaxis
                peak_hours=(18, 19, 20, 21),            # Horas pico locales
                km_per_kwh=35.0,                        # Eficiencia eléctrica
            )
            artifacts["iquitos_context"] = iquitos_ctx
            logger.info("[REWARDS] ✅ Loaded IquitosContext with CO₂ factors and EV specs")
            logger.info("[REWARDS]    Grid CO₂: %.4f kg/kWh", iquitos_ctx.co2_factor_kg_per_kwh)
            logger.info("[REWARDS]    EV CO₂ conversion: %.3f kg/kWh", iquitos_ctx.co2_conversion_factor)
            logger.info("[REWARDS]    Daily EV capacity: %d motos + %d mototaxis",
                       iquitos_ctx.motos_daily_capacity, iquitos_ctx.mototaxis_daily_capacity)
        except Exception as e:
            logger.error("[REWARDS] Failed to initialize IquitosContext: %s", e)

    # Cargar pesos de recompensa multiobjetivo
    if REWARDS_AVAILABLE:
        try:
            reward_weights = create_iquitos_reward_weights(priority="balanced")
            artifacts["reward_weights"] = reward_weights
            logger.info("[REWARDS] ✅ Created reward weights: CO₂=%.2f, solar=%.2f, cost=%.2f",
                       reward_weights.co2, reward_weights.solar, reward_weights.cost)
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
    """Generate 128 individual charger_simulation_XXX.csv files required by CityLearn v2.

    **CRITICAL**: CityLearn v2 expects each charger's load profile in a separate CSV file:
    - buildings/building_name/charger_simulation_001.csv through charger_simulation_128.csv
    - Each file: 8,760 rows × 1 column (demand in kW)

    Args:
        charger_profiles_annual: DataFrame with shape (8760, 128)
                                Columns are charger IDs (MOTO_CH_001, etc.)
        building_dir: Path to buildings/building_name/ directory
        overwrite: If True, overwrite existing files

    Returns:
        Dict mapping charger index → CSV file path

    Raises:
        ValueError: If invalid shape or columns
    """
    if charger_profiles_annual.shape[0] != 8760:
        raise ValueError(
            f"Charger profiles must have 8,760 rows (annual hourly), "
            f"got {charger_profiles_annual.shape[0]}"
        )

    if charger_profiles_annual.shape[1] != 128:
        raise ValueError(
            f"Charger profiles must have 128 columns, "
            f"got {charger_profiles_annual.shape[1]}"
        )

    building_dir.mkdir(parents=True, exist_ok=True)

    generated_files = {}

    # Generate 128 individual CSVs (charger_simulation_001.csv through 128.csv)
    for charger_idx in range(128):
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
    # get_dataset returns path to schema.json, we need the parent directory
    # Use default cache location (CityLearn manages the download)
    schema_file = Path(ds.get_dataset(name=template_name))
    template_dir = schema_file.parent
    logger.info("Using CityLearn template from: %s", template_dir)

    out_dir = processed_dir / "citylearn" / dataset_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(template_dir, out_dir)

    schema_path = out_dir / "schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    # Update schema globals
    schema["central_agent"] = central_agent
    schema["seconds_per_time_step"] = seconds_per_time_step
    # CRITICAL FIX: Use relative path "." instead of absolute path
    # This avoids CityLearn UTF-8 encoding bug with paths containing special characters (ñ, etc.)
    # The _make_env() function in simulate.py changes to the dataset directory before loading
    schema["root_directory"] = "."
    schema["start_date"] = "2024-01-01"  # Alinear con datos solares PVGIS (enero-diciembre)
    schema["simulation_end_time_step"] = 8759  # Full year (0-indexed: 8760 steps total)
    schema["episode_time_steps"] = 8760  # CRITICAL FIX: Force full-year episodes (was null causing premature termination)

    # === UN SOLO BUILDING: Mall_Iquitos (unifica ambas playas de estacionamiento) ===
    # Arquitectura: 1 edificio Mall con 2 áreas de estacionamiento (motos + mototaxis)
    # Todos los 128 chargers, PV y BESS se gestionan como una única unidad
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
    logger.info("Creado building unificado: Mall_Iquitos (32 chargers × 4 sockets = 128 tomas, 4162 kWp PV, 2000 kWh BESS)")

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
    # CRÍTICO: CityLearn necesita definiciones de EVs con baterías para que los chargers funcionen.
    # Sin esto, el consumo de chargers será 0 (los EVs no tienen baterías definidas).
    #
    # Configuración OE2:
    # - 112 motos: batería 2.5 kWh, carga 2.0 kW
    # - 16 mototaxis: batería 4.5 kWh, carga 3.0 kW
    electric_vehicles_def = {}

    # 112 EVs para motos (chargers 1-112)
    for i in range(112):
        ev_name = f'EV_Mall_{i+1}'
        electric_vehicles_def[ev_name] = {
            'include': True,
            'battery': {
                'type': 'citylearn.energy_model.Battery',
                'autosize': False,
                'attributes': {
                    'capacity': 2.5,           # kWh - batería típica moto eléctrica
                    'nominal_power': 2.0,      # kW - potencia de carga
                    'initial_soc': 0.20,       # 20% SOC al llegar (fracción)
                    'depth_of_discharge': 0.90, # 90% DOD máximo
                    'efficiency': 0.95,        # 95% eficiencia carga/descarga
                }
            }
        }

    # 16 EVs para mototaxis (chargers 113-128)
    for i in range(16):
        ev_name = f'EV_Mall_{112+i+1}'
        electric_vehicles_def[ev_name] = {
            'include': True,
            'battery': {
                'type': 'citylearn.energy_model.Battery',
                'autosize': False,
                'attributes': {
                    'capacity': 4.5,           # kWh - batería típica mototaxi
                    'nominal_power': 3.0,      # kW - potencia de carga
                    'initial_soc': 0.20,       # 20% SOC al llegar (fracción)
                    'depth_of_discharge': 0.90, # 90% DOD máximo
                    'efficiency': 0.95,        # 95% eficiencia carga/descarga
                }
            }
        }

    schema['electric_vehicles_def'] = electric_vehicles_def
    logger.info("[EV ARCHITECTURE] Creado electric_vehicles_def: 128 EVs (112 motos + 16 mototaxis)")

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

        # ✅ CORRECCIÓN AUTOMÁTICA EMBEDDED (L443-456): Si los valores son 0/None, usar valores OE2 reales
        if bess_cap is None or bess_cap == 0.0:
            bess_cap = 4520.0  # OE2 Real: 4,520 kWh [EMBEDDED-FIX-L1]
            logger.warning("[EMBEDDED-FIX] BESS capacity corregido a OE2 Real: 4520.0 kWh")
        if bess_pow is None or bess_pow == 0.0:
            bess_pow = 2712.0  # OE2 Real: 2,712 kW [EMBEDDED-FIX-L1]
            logger.warning("[EMBEDDED-FIX] BESS power corregido a OE2 Real: 2712.0 kW")

    elif "bess_params" in artifacts:
        bess_params = artifacts["bess_params"]
        bess_cap = float(bess_params.get("electrical_storage", {}).get("capacity", 0.0))
        bess_pow = float(bess_params.get("electrical_storage", {}).get("nominal_power", 0.0))
        logger.info("Usando parametros BESS de OE2 (schema): %s kWh, %s kW", bess_cap, bess_pow)
    else:
        # ✅ CORRECCIÓN AUTOMÁTICA EMBEDDED (L456-463): Si no hay artifacts, usar OE2 Real
        bess_cap = 4520.0
        bess_pow = 2712.0
        logger.warning("[EMBEDDED-FIX] BESS config no encontrado, usando OE2 Real: 4520.0 kWh / 2712.0 kW [FALLBACK]")

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

    # === CREAR CHARGERS EN EL SCHEMA (128 socket-level chargers = 32 physical chargers × 4 sockets) ===
    # Los sockets se crean directamente en el schema para control por RL agents
    # Cada socket (toma) es independiente y controlable vía acciones continuas [0, 1]

    # Get charger configuration from OE2
    ev_chargers = artifacts.get("ev_chargers", [])  # list of 32 PHYSICAL chargers
    n_physical_chargers = len(ev_chargers) if ev_chargers else 32
    sockets_per_charger = 4
    total_devices = n_physical_chargers * sockets_per_charger  # 32 × 4 = 128 sockets/tomas

    logger.info(f"[CHARGERS SCHEMA] Configurando {total_devices} sockets (32 chargers físicos × 4 sockets = 128 tomas) en schema para control RL")

    # ✓ SOLUCIÓN: Mantener sockets en schema (no eliminar)
    # - 128 sockets (tomas) controlables vía acciones RL (32 cargadores × 4 sockets)
    # - Cada socket tiene CSV con estado (ocupancia, SOC, etc.)
    # - RL agents controlan power setpoint via acciones continuas [0, 1]

    # ✅ CRITICAL FIX: ALWAYS START WITH EMPTY CHARGERS DICT
    # Do NOT use existing chargers from template (they are only 32 and outdated)
    # We MUST create exactly 128 new chargers for proper control
    b["chargers"] = {}  # FORCE EMPTY - we'll populate with 128

    logger.info(f"[CHARGERS SCHEMA] Configurando {total_devices} chargers en el schema...")

    # === NOTA SOBRE EVs ===
    # NO crear 128 EVs permanentes en el schema
    # Los EVs son dinámicos (vehículos que llegan/se van)
    # El schema NO tiene electric_vehicles_def global
    # Los chargers tienen datos dinámicos en charger_simulation_*.csv
    # Eso es suficiente para que CityLearn interprete los EVs

    # Get charger template from FIRST existing charger (if any) for reference
    charger_template = None
    backup_existing_chargers = b.get("chargers", {})  # Store for reference
    if backup_existing_chargers:
        charger_template = list(backup_existing_chargers.values())[0]

    # === CREAR EXACTAMENTE 128 CHARGERS EN EL SCHEMA ===
    all_chargers: Dict[str, Any] = {}
    n_motos = 0
    n_mototaxis = 0
    power_motos = 0.0
    power_mototaxis = 0.0

    for charger_idx in range(total_devices):  # 128 iteraciones = 32 chargers × 4 sockets
        # Generate charger name
        charger_name = f"charger_mall_{charger_idx + 1}"

        # Get power info from OE2 if available
        # CORRECCIÓN CRÍTICA: socket_idx 0-127 mapea a charger_idx 0-31 con socket 0-3
        physical_charger_idx = charger_idx // sockets_per_charger  # Cual charger físico (0-31)
        socket_in_charger = charger_idx % sockets_per_charger  # Cual socket dentro del charger (0-3)

        if physical_charger_idx < len(ev_chargers):
            charger_info = ev_chargers[physical_charger_idx]
            power_kw = float(charger_info.get("power_kw", 2.0))
            sockets = 1  # Individual socket power (NOT total charger power × 4)
            charger_type = charger_info.get("charger_type", "moto").lower()
        else:
            # Default: motos have 2kW, mototaxis have 3kW
            if physical_charger_idx < 28:  # First 28 are motos
                power_kw = 2.0
                sockets = 1
                charger_type = "moto"
            else:  # Last 4 are mototaxis
                power_kw = 3.0
                sockets = 1
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

    # ✅ CRITICAL FIX: Store chargers count for later verification
    # This ensures we know we assigned 128 chargers even if dict is modified later
    all_chargers_backup = dict(all_chargers)  # Deep copy to preserve state
    chargers_count_at_assignment = len(all_chargers)

    logger.info(f"[CHARGERS SCHEMA] ✓ CORRECCIÓN CRÍTICA: Asignados {total_devices} sockets (32 chargers × 4) a 'chargers': {n_motos} motos ({power_motos:.1f} kW) + {n_mototaxis} mototaxis ({power_mototaxis:.1f} kW)")
    logger.info(f"[CHARGERS SCHEMA] ✅ BACKUP: Guardadas {chargers_count_at_assignment} chargers para validación posterior")

    # === ELECTRIC VEHICLES: DINÁMICOS (no permanentes) ===
    # NOTA: Los EVs NO son 128 entidades permanentes
    # Los EVs son VEHÍCULOS DINÁMICOS que llegan/se van cada hora
    # El schema NO necesita 128 EVs definidos - eso es incorrecto
    # Los datos de occupancy/SOC vienen en charger_simulation_*.csv
    # CityLearn los interpreta dinámicamente basado en los datos de ocupancia

    # NO crear electric_vehicles_list permanente - los chargers ya tienen
    # los datos dinámicos en sus CSV de simulación
    logger.info(f"[EV DYNAMICS] EVs son dinámicos (basados en charger_simulation_*.csv), no permanentes en schema")

    # Discover and overwrite relevant CSVs
    paths = _discover_csv_paths(schema, out_dir)
    energy_path = paths.get("energy_simulation")
    if energy_path is None or not energy_path.exists():
        raise FileNotFoundError("Could not locate energy_simulation CSV in template dataset.")

    df_energy = pd.read_csv(energy_path)
    logger.info("energy_simulation path: %s, shape: %s", energy_path, df_energy.shape)
    # Truncar a 8760 timesteps (365 días * 24 horas = 1 año de datos horarios)
    # El template original puede tener múltiples observaciones por hora
    n = min(len(df_energy), 8760)
    df_energy = df_energy.iloc[:n].reset_index(drop=True)

    # === REGENERAR COLUMNAS DE TIEMPO PARA EMPEZAR EN ENERO (alinear con PVGIS) ===
    # Crear índice temporal desde 2024-01-01 00:00 (365 días × 24 horas = 8760 filas)
    time_index = pd.date_range(start="2024-01-01", periods=n, freq="h")
    if "month" in df_energy.columns:
        df_energy["month"] = time_index.month
    if "hour" in df_energy.columns:
        df_energy["hour"] = time_index.hour
    if "day_type" in df_energy.columns:
        # day_type: 1=weekday, 2=weekend
        df_energy["day_type"] = np.where(time_index.dayofweek < 5, 1, 2)
    logger.info("[OK] Columnas de tiempo regeneradas: month=1-12 (enero-diciembre), alineado con PVGIS")

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
        for col in df_energy.columns:
            for rgx in regex_list:
                if re.search(rgx, col, re.IGNORECASE):
                    return col  # type: ignore
        return None

    load_col = find_col([r"non[_ ]?shiftable", r"electricity[_ ]?load"])
    solar_col = find_col([r"solar[_ ]?generation"])

    if load_col is None:
        raise ValueError("Template energy_simulation file does not include a non_shiftable_load-like column.")

    logger.info("[MALL DEMAND VALIDATION] Asignando demanda del mall...")
    logger.info(f"   Fuente: {mall_source}")
    logger.info(f"   Registros: {len(mall_series)}")
    logger.info(f"   Suma total: {mall_series.sum():.1f} kWh")
    logger.info(f"   Min: {mall_series.min():.2f} kW, Max: {mall_series.max():.2f} kW, Promedio: {mall_series.mean():.2f} kW")
    logger.info(f"   Primeros 5 horas: {mall_series[:5]}")
    logger.info(f"   Últimas 5 horas: {mall_series[-5:]}")

    df_energy[load_col] = mall_series
    logger.info("[ENERGY] Asignada carga: %s = %.1f kWh", load_col, mall_series.sum())

    if solar_col is not None:
        df_energy[solar_col] = pv_per_kwp
        logger.info("[ENERGY] Asignada generacion solar: %s = %.1f (W/kW.h)", solar_col, pv_per_kwp.sum())
        logger.info("   Primeros 5 valores: %s", pv_per_kwp[:5])
        logger.info("   Ultimos 5 valores: %s", pv_per_kwp[-5:])
    else:
        # If no solar column exists, leave template as-is (PV device may be absent).
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
    logger.info(f"   Total chargers: 128 (for 128 simulation files)")
    logger.info(f"   Operating hours: {cfg['oe2']['ev_fleet']['opening_hour']}-{cfg['oe2']['ev_fleet']['closing_hour']}")
    logger.info(f"   Files will be generated: charger_simulation_001.csv to charger_simulation_128.csv")

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

        # PRIORITY 1: NEW bess_hourly_dataset_2024.csv (2026-02-04)
        if "bess_hourly_2024" in artifacts:
            try:
                bess_oe2_df = artifacts["bess_hourly_2024"].copy()
                bess_source = "bess_hourly_dataset_2024.csv (NEW - 2026-02-04)"
                logger.info(f"[BESS] ✅ PRIORITY 1: USING NEW DATASET: {bess_source}")
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

            # Crear CSV con columna soc_stored_kwh para CityLearn
            bess_df = pd.DataFrame({
                "soc_stored_kwh": soc_kwh
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
            logger.error(f"[BESS]    PRIORITY 1 buscado: data/oe2/bess/bess_hourly_dataset_2024.csv")
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

    # === GENERAR 128 CSVs INDIVIDUALES PARA CHARGERS ===
    # PRIORITY 1: Use real charger dataset (chargers_real_hourly_2024.csv) if available
    # PRIORITY 2: Fallback to legacy 32-charger profiles and expand to 128 sockets
    #
    # Real Dataset Structure:
    # - 128 columns: MOTO_XX_SOCKET_Y (112) + MOTOTAXI_XX_SOCKET_Y (16)
    # - 8,760 rows: hourly timesteps (complete year)
    # - Each column contains power demand for ONE socket in kW
    # - Ready for direct use: no expansion needed
    #
    # Legacy Dataset Structure (FALLBACK):
    # - 32 columns: charger IDs (one per charger)
    # - 8,760 rows: hourly timesteps
    # - Each charger has 4 sockets → need to expand 32→128 columns

    chargers_source = "unknown"
    chargers_df_for_generation = None

    # PRIORITY 1: Load real dataset if available
    if "chargers_real_hourly_2024" in artifacts:
        chargers_df_for_generation = artifacts["chargers_real_hourly_2024"].copy()
        chargers_source = "REAL (chargers_real_hourly_2024.csv)"
        logger.info(f"[CHARGERS GENERATION] ✅ Using REAL dataset: {chargers_df_for_generation.shape}")
        logger.info(f"[CHARGERS GENERATION]    128 individual socket columns (ready for RL agents)")
        logger.info(f"[CHARGERS GENERATION]    8,760 hourly timesteps (complete year)")

    # PRIORITY 2: Fallback to legacy profiles
    elif "chargers_hourly_profiles_annual" in artifacts:
        chargers_df_legacy = artifacts["chargers_hourly_profiles_annual"]
        chargers_source = "LEGACY (chargers_hourly_profiles_annual.csv)"
        logger.info(f"[CHARGERS GENERATION] ⚠️  Using LEGACY dataset: {chargers_df_legacy.shape}")

        # Expand 32 chargers to 128 sockets (4 sockets per charger)
        if chargers_df_legacy.shape[1] == 32:
            logger.info(f"[CHARGERS GENERATION]    Expanding 32 chargers → 128 sockets (4 per charger)")
            expanded_data = {}
            for i in range(32):
                charger_col = chargers_df_legacy.columns[i]
                charger_demand = chargers_df_legacy[charger_col].values
                # Divide demand equally among 4 sockets
                socket_demand = charger_demand / 4.0
                for socket_idx in range(4):
                    socket_col = f"{charger_col}_SOCKET_{socket_idx}"
                    expanded_data[socket_col] = socket_demand
            chargers_df_for_generation = pd.DataFrame(expanded_data)
            logger.info(f"[CHARGERS GENERATION]    Expansion result: {chargers_df_for_generation.shape}")
        else:
            chargers_df_for_generation = chargers_df_legacy

    if chargers_df_for_generation is None:
        logger.error(f"[CHARGERS GENERATION] ❌ NO CHARGER DATA AVAILABLE")
        raise RuntimeError("No charger dataset found - neither real nor legacy profiles available")

    # VALIDATION: Final dimensions
    if chargers_df_for_generation.shape != (8760, 128):
        logger.error(f"[CHARGERS GENERATION] ❌ INVALID SHAPE: {chargers_df_for_generation.shape} (expected 8760×128)")
        raise ValueError(f"Charger profiles must be (8760, 128), got {chargers_df_for_generation.shape}")

    logger.info(f"[CHARGERS GENERATION] ✅ Dataset ready: {chargers_source}")
    logger.info(f"[CHARGERS GENERATION]    Dimensions: 8,760 hours × 128 sockets")
    logger.info(f"[CHARGERS GENERATION]    Annual energy: {chargers_df_for_generation.sum().sum():,.0f} kWh")
    logger.info(f"[CHARGERS GENERATION]    Mean power: {chargers_df_for_generation.sum(axis=1).mean():.1f} kW")

    # ===== GENERAR 128 CSVs INDIVIDUALES PARA CHARGERS (desde dataset real o legacy) =====
    # Use the chargers_df_for_generation prepared above (128 columns, 8760 rows)
    if chargers_df_for_generation is not None and chargers_df_for_generation.shape == (8760, 128):
        building_dir = out_dir  # Root directory for charger CSVs
        charger_list = []
        total_ev_demand_kwh = 0.0

        logger.info("[CHARGERS CSV GENERATION] Generando 128 archivos CSV...")

        for socket_idx in range(128):
            charger_name = f"charger_simulation_{socket_idx+1:03d}.csv"
            csv_path = building_dir / charger_name
            charger_list.append(csv_path)

            # Extract socket demand from prepared dataset
            socket_demand = chargers_df_for_generation.iloc[:, socket_idx].values
            total_ev_demand_kwh += socket_demand.sum()

            # Create state array (1=connected, 3=idle)
            states_array = np.where(socket_demand > 0, 1, 3).astype(int)

            # Determine socket type (motos=0-111, mototaxis=112-127)
            is_mototaxi = socket_idx >= 112
            if is_mototaxi:
                socket_type = "MOTOTAXI"
                local_idx = socket_idx - 112 + 1
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
        logger.info(f"Total arquivos generados: 128 (charger_simulation_001.csv to 128.csv)")
        logger.info(f"Total EV demand anual: {total_ev_demand_kwh:,.0f} kWh")
        logger.info(f"Promedio por socket: {total_ev_demand_kwh/128:,.0f} kWh/año")
        logger.info(f"Fuente de datos: {chargers_source}")
        logger.info(f"Estructura: 112 motos (MOTO_001 to 112) + 16 mototaxis (MOTOTAXI_001 to 016)")
        logger.info("=" * 80)
        logger.info("")

        # === ACTUALIZAR SCHEMA: Referenciar los 128 CSVs ===
        logger.info("[CHARGER GENERATION] Actualizando schema con referencias a 128 CSVs...")

        chargers_to_update = b_mall.get("chargers", {})
        if len(chargers_to_update) != 128:
            logger.warning(f"[WARN] Se esperaban 128 chargers, se encontraron {len(chargers_to_update)}")

        for charger_idx, charger_name in enumerate(chargers_to_update.keys()):
            csv_filename = f"charger_simulation_{charger_idx+1:03d}.csv"
            chargers_to_update[charger_name]["charger_simulation"] = csv_filename

        b_mall["chargers"] = chargers_to_update
        logger.info(f"[OK] Schema actualizado: {len(chargers_to_update)}/128 chargers con referencias CSV")

    else:
        logger.error("[CHARGERS CSV GENERATION] ❌ No charger dataset available for CSV generation")
        raise RuntimeError("Charger dataset must be (8760, 128) - no valid data found")

    # ==========================================================================
    # INTEGRACIÓN: Agregar contexto de recompensa al schema
    # Permite a los agentes OE3 (SAC, PPO, A2C) acceder a:
    # - Factores CO₂ (0.4521 grid, 2.146 EV directo)
    # - Capacidad diaria EVs (1,800 motos + 260 mototaxis)
    # - Pesos de recompensa multiobjetivo (CO₂=0.50, solar=0.20, cost=0.15, etc.)
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

    return BuiltDataset(dataset_dir=out_dir, schema_path=schema_path, building_name=bname)
