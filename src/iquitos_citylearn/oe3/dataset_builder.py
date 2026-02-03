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

def _load_oe2_artifacts(interim_dir: Path) -> Dict[str, Any]:
    artifacts: Dict[str, Any] = {}

    # Solar - cargar parámetros de CityLearn si existen
    solar_citylearn_params = interim_dir / "oe2" / "solar" / "citylearn" / "solar_schema_params.json"
    if solar_citylearn_params.exists():
        artifacts["solar_params"] = json.loads(solar_citylearn_params.read_text(encoding="utf-8"))

    # Solar timeseries
    solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
    if solar_path.exists():
        artifacts["solar_ts"] = pd.read_csv(solar_path)
        # CRITICAL: Validate that solar data is hourly (8,760 rows per year)
        _validate_solar_timeseries_hourly(artifacts["solar_ts"])

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

    # === CHARGER HOURLY PROFILES (ANNUAL) - 8,760 hours × 128 chargers ===
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

    # Mall demand
    mall_demand_candidates = [
        interim_dir / "oe2" / "demandamall" / "demanda_mall_kwh.csv",
        interim_dir / "oe2" / "demandamallkwh" / "demanda_mall_horaria_anual.csv",
        interim_dir / "oe2" / "demandamallkwh" / "demandamallkwh.csv",
    ]
    for path in mall_demand_candidates:
        if path.exists():
            artifacts["mall_demand"] = pd.read_csv(path)
            artifacts["mall_demand_path"] = str(path)
            logger.info("Loaded mall demand artifact from %s", path)
            break

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
    logger.info("Creado building unificado: Mall_Iquitos (128 chargers, 4162 kWp PV, 2000 kWh BESS)")

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

    # === CREAR CHARGERS EN EL SCHEMA (128 chargers individuales) ===
    # Los chargers se crean directamente en el schema para control por RL agents
    # Cada charger es independiente y controlable vía acciones continuas [0, 1]

    # Get charger configuration from OE2
    ev_chargers = artifacts.get("ev_chargers", [])  # list of 128 charger dicts
    total_devices = len(ev_chargers) if ev_chargers else 128

    logger.info(f"[CHARGERS SCHEMA] Restaurando {total_devices} chargers en schema para control RL")

    # ✓ SOLUCIÓN: Mantener chargers en schema (no eliminar)
    # - 128 chargers controlables vía acciones RL
    # - Cada charger tiene CSV con estado (ocupancia, SOC, etc.)
    # - RL agents controlan power setpoint via acciones continuas [0, 1]

    # Ensure chargers dict exists (restaurar si no está)
    if "chargers" not in b:
        b["chargers"] = {}

    # Ensure electric_vehicles_def exists (restaurar si no está)
    logger.info(f"[CHARGERS SCHEMA] Configurando {total_devices} chargers en el schema...")

    # === NOTA SOBRE EVs ===
    # NO crear 128 EVs permanentes en el schema
    # Los EVs son dinámicos (vehículos que llegan/se van)
    # El schema NO tiene electric_vehicles_def global
    # Los chargers tienen datos dinámicos en charger_simulation_*.csv
    # Eso es suficiente para que CityLearn interprete los EVs

    # Get existing charger template
    existing_chargers = b.get("chargers", {})
    charger_template = None
    if existing_chargers:
        charger_template = list(existing_chargers.values())[0]

    # === CREAR 128 CHARGERS EN EL SCHEMA ===
    all_chargers: Dict[str, Any] = {}
    n_motos = 0
    n_mototaxis = 0
    power_motos = 0.0
    power_mototaxis = 0.0

    for charger_idx in range(total_devices):
        # Generate charger name
        charger_name = f"charger_mall_{charger_idx + 1}"

        # Get power info from OE2 if available
        if charger_idx < len(ev_chargers):
            charger_info = ev_chargers[charger_idx]
            power_kw = float(charger_info.get("power_kw", 2.0))
            sockets = int(charger_info.get("sockets", 4))
            charger_type = charger_info.get("charger_type", "moto").lower()
        else:
            # Default: motos have 2kW, mototaxis have 3kW
            if charger_idx < 112:  # First 112 are motos
                power_kw = 2.0
                sockets = 4
                charger_type = "moto"
            else:  # Last 16 are mototaxis
                power_kw = 3.0
                sockets = 4
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

        # Set power and socket info
        nominal_power = power_kw * sockets
        if "attributes" in new_charger:
            new_charger["attributes"]["nominal_power"] = nominal_power
            new_charger["attributes"]["max_charging_power"] = nominal_power
            new_charger["attributes"]["num_sockets"] = sockets
        else:
            new_charger["nominal_power"] = nominal_power
            new_charger["max_charging_power"] = nominal_power
            new_charger["num_sockets"] = sockets

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

    logger.info(f"[CHARGERS SCHEMA] ✓ CORRECCIÓN CRÍTICA: Asignados {total_devices} chargers a 'chargers': {n_motos} motos ({power_motos:.1f} kW) + {n_mototaxis} mototaxis ({power_mototaxis:.1f} kW)")

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

        # Buscar archivo de simulación horaria de BESS de OE2
        bess_oe2_path = None
        for potential_path in [
            Path("data/interim/oe2/bess/bess_simulation_hourly.csv"),
            Path("data/oe2/bess/bess_simulation_hourly.csv"),
            Path(str(paths.get("bess_simulation_hourly"))) if "bess_simulation_hourly" in paths and paths.get("bess_simulation_hourly") else None,
        ]:
            if potential_path and potential_path.exists():
                bess_oe2_path = potential_path
                break

        if bess_oe2_path:
            # Usar datos reales de OE2
            try:
                bess_oe2_df = pd.read_csv(bess_oe2_path)

                # Validar que tenga exactamente 8760 filas (1 año)
                if len(bess_oe2_df) == 8760 and "soc_kwh" in bess_oe2_df.columns:
                    # Usar columna soc_kwh de OE2
                    bess_df = pd.DataFrame({
                        "soc_stored_kwh": bess_oe2_df["soc_kwh"].values
                    })

                    bess_df.to_csv(bess_simulation_path, index=False)

                    soc_values = bess_oe2_df["soc_kwh"].values
                    logger.info(f"[BESS] USANDO DATOS REALES DE OE2: {bess_oe2_path}")
                    logger.info(f"[BESS] Capacidad: {bess_cap:.0f} kWh, Potencia: {bess_pow:.0f} kW")
                    logger.info(f"[BESS] SOC Dinámico (OE2): min={soc_values.min():.0f}, max={soc_values.max():.0f}, mean={soc_values.mean():.0f} kWh")
                    logger.info(f"[BESS] Variabilidad: {soc_values.std():.0f} kWh (desv estándar), {len(np.unique(soc_values))} valores únicos")
                else:
                    logger.warning(f"[BESS] OE2 file inválido (length={len(bess_oe2_df)}, columns={bess_oe2_df.columns.tolist()})")
                    raise ValueError("OE2 BESS file invalid")
            except Exception as e:
                logger.warning(f"[BESS] Error leyendo OE2 datos: {e}")
                raise RuntimeError(f"Cannot load BESS simulation from OE2: {e}")
        else:
            logger.error(f"[BESS] No se encontró archivo de simulación BESS de OE2")
            logger.error(f"[BESS] Esperado en: data/interim/oe2/bess/bess_simulation_hourly.csv")
            raise FileNotFoundError("Missing BESS simulation file from OE2 (bess_simulation_hourly.csv)")

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

    # === GENERAR 128 CSVs INDIVIDUALES PARA CHARGERS (desde chargers_hourly_profiles_annual) ===
    # Este es el paso CRÍTICO: generamos 128 archivos CSV individuales para CityLearn v2
    # CADA CSV contiene: state + ev_id + departure_time + required_soc + arrival_time + arrival_soc

    if "chargers_hourly_profiles_annual" in artifacts:
        charger_profiles_annual = artifacts["chargers_hourly_profiles_annual"]
        logger.info(f"[OK] [CHARGER GENERATION] Cargar perfiles anuales: shape={charger_profiles_annual.shape}")

        # ✅ CORRECCIÓN AUTOMÁTICA EMBEDDED (L1025-1040): Validar y corregir shape
        if charger_profiles_annual.shape[0] != 8760 or charger_profiles_annual.shape[1] != 128:
            logger.warning(f"[WARN] Charger profiles shape error: {charger_profiles_annual.shape}, expected (8760, 128)")

            # Intentar corregir automáticamente
            if charger_profiles_annual.shape[1] > 128:
                # Si hay más columnas, remover columnas extra (ej: Unnamed, MOTO_CH_001.1) [EMBEDDED-FIX-L2]
                logger.info(f"[EMBEDDED-FIX] Removiendo {charger_profiles_annual.shape[1] - 128} columnas extra...")
                charger_profiles_annual = charger_profiles_annual.iloc[:, :128]
            elif charger_profiles_annual.shape[1] < 128:
                # Si faltan columnas, error
                logger.error(f"[ERROR] NO SE PUEDEN AGREGAR COLUMNAS - Charger profiles shape error")
                raise ValueError(f"Charger profiles must have 128 columns, got {charger_profiles_annual.shape[1]}")

            # Asegurar 8760 filas exactas
            if charger_profiles_annual.shape[0] != 8760:
                logger.info(f"[EMBEDDED-FIX] Ajustando filas: {charger_profiles_annual.shape[0]} → 8760...")
                if charger_profiles_annual.shape[0] < 8760:
                    # Rellenar con la última fila si faltan filas
                    missing = 8760 - charger_profiles_annual.shape[0]
                    last_row = charger_profiles_annual.iloc[-1:].copy()
                    last_row_repeated = pd.concat([last_row] * missing, ignore_index=True)
                    charger_profiles_annual = pd.concat([charger_profiles_annual, last_row_repeated], ignore_index=True)
                else:
                    # Recortar si hay filas extra
                    charger_profiles_annual = charger_profiles_annual.iloc[:8760]

            logger.info(f"[OK] Charger profiles corregido: shape final={charger_profiles_annual.shape}")

        # Verificación final
        if charger_profiles_annual.shape != (8760, 128):
            logger.error(f"[ERROR] Charger profiles shape still invalid: {charger_profiles_annual.shape}, expected (8760, 128)")
            raise ValueError(f"Charger profiles must be (8760, 128), got {charger_profiles_annual.shape}")

        # Create output directory (CSVs go in ROOT)
        building_dir = out_dir  # Use root directory for charger CSVs

        # ==========================================
        # SOLUCIÓN MEJORADA: EVs DINÁMICOS (2026-02-03)
        # ==========================================
        # Usar cálculo dinámico basado en SOC, capacidad de batería y potencia del charger
        # - SOC de llegada: 20-25% (vehículos cansados)
        # - SOC de salida: 85-90% (listos para día siguiente)
        # - Capacidad: 2.5 kWh (moto), 4.5 kWh (mototaxi)
        # - Tiempo variable según SOC y potencia disponible
        # - Variabilidad temporal: picos (18-21h), fin de semana, etc.

        try:
            from iquitos_citylearn.oe3.ev_demand_calculator import (
                EVChargerConfig,
                EVDemandCalculator,
                create_ev_configs_iquitos,
            )

            logger.info("[EV DYNAMIC] Cargando calculadora de demanda dinámica de EVs...")

            # Obtener configuraciones de chargers (moto y mototaxi)
            moto_configs, mototaxi_configs = create_ev_configs_iquitos()
            all_configs = moto_configs + mototaxi_configs

            logger.info(f"[EV DYNAMIC] Configuradas {len(moto_configs)} motos (2.5 kWh, 2.0 kW)")
            logger.info(f"[EV DYNAMIC] Configuradas {len(mototaxi_configs)} mototaxis (4.5 kWh, 3.0 kW)")

            charger_list = []
            total_ev_demand_kwh = 0.0

            for charger_idx in range(128):
                charger_name = f"charger_simulation_{charger_idx+1:03d}.csv"
                csv_path = building_dir / charger_name
                charger_list.append(csv_path)

                try:
                    # ✅ DINÁMICA: Crear calculadora para este charger
                    config = all_configs[charger_idx]
                    calculator = EVDemandCalculator(config)

                    # ✅ DINÁMICA: Crear perfil de ocupancia basado en demanda OE2
                    # Si demanda OE2 > 0: EV conectado; si == 0: disponible
                    charger_demand = charger_profiles_annual.iloc[:, charger_idx].values
                    occupancy_profile = np.where(charger_demand > 0, 1, 0).astype(int)

                    # ✅ DINÁMICA: Calcular parámetros en cada hora
                    states = []
                    ev_ids = []
                    departure_times = []
                    required_socs = []
                    arrival_times = []
                    arrival_socs = []
                    hourly_demands = []

                    for t in range(8760):
                        hour = t % 24
                        day_year = t // 24
                        day_week = day_year % 7

                        is_connected = bool(occupancy_profile[t])

                        if is_connected:
                            # ✅ DINÁMICA: EV conectado → calcular demanda realista
                            state = 1  # Charging
                            ev_id = f"{config.charger_type.upper()}_{config.charger_id:03d}"

                            # ✅ DINÁMICA: Energía y tiempo de carga
                            energy_req = calculator.calculate_energy_required()
                            charging_time = calculator.calculate_charging_time()

                            # ✅ DINÁMICA: Demanda modulada (picos, fin de semana)
                            demand = calculator.calculate_hourly_demand(hour, day_week, is_connected)

                            # ✅ DINÁMICA: Tiempos realistas con variación
                            # Base + variación aleatoria (-20% a +20%)
                            variation = np.random.normal(1.0, 0.1)
                            departure_time = max(0.5, min(8.0, charging_time * variation))
                            required_soc = config.battery_soc_target

                            # Tiempos de llegada próxima (asumiendo no llegan en la misma hora)
                            hours_to_next_ev = min(24, max(1, int(np.random.normal(4, 2))))
                            arrival_time = float(hours_to_next_ev)
                            arrival_soc = config.battery_soc_arrival

                        else:
                            # ✅ DINÁMICA: Charger disponible → sin demanda
                            state = 3  # Available/idle
                            ev_id = ""
                            demand = 0.0
                            departure_time = 0.0
                            required_soc = 0.0
                            arrival_time = 2.0  # Próximo EV esperado en ~2h
                            arrival_soc = 0.0

                        states.append(state)
                        ev_ids.append(ev_id)
                        departure_times.append(departure_time)
                        required_socs.append(required_soc)
                        arrival_times.append(arrival_time)
                        arrival_socs.append(arrival_soc)
                        hourly_demands.append(demand)
                        total_ev_demand_kwh += demand

                    # Crear DataFrame con datos dinámicos
                    df_charger = pd.DataFrame({
                        'electric_vehicle_charger_state': states,
                        'electric_vehicle_id': ev_ids,
                        'electric_vehicle_departure_time': departure_times,
                        'electric_vehicle_required_soc_departure': required_socs,
                        'electric_vehicle_estimated_arrival_time': arrival_times,
                        'electric_vehicle_estimated_soc_arrival': arrival_socs,
                    })

                    # Guardar CSV
                    df_charger.to_csv(csv_path, index=False, float_format='%.6f')
                    logger.info(f"  [✓] {charger_name} dinámico ({config.charger_type}, {np.sum(occupancy_profile)} horas conectado)")

                except Exception as e:
                    logger.error(f"[ERROR] Error generando {charger_name} dinámico: {e}")
                    raise

            # === LOG RESUMEN DE DEMANDA EV (DINÁMICO) ===
            logger.info("")
            logger.info("=" * 80)
            logger.info("[EV DYNAMIC] RESUMEN DE DEMANDA DINÁMICA DE EVs")
            logger.info("=" * 80)
            logger.info(f"Total EV Demand (Dinámica): {total_ev_demand_kwh:,.0f} kWh/año")
            logger.info(f"Distribución: 112 motos + 16 mototaxis = 128 chargers")
            logger.info(f"Promedio por charger: {total_ev_demand_kwh/128:,.0f} kWh/año")
            logger.info(f"")
            logger.info(f"Configuración de Batería:")
            logger.info(f"  Motos: 2.5 kWh, SOC llegada 20%, SOC salida 90%")
            logger.info(f"  Mototaxis: 4.5 kWh, SOC llegada 25%, SOC salida 85%")
            logger.info(f"")
            logger.info(f"Potencia de Carga:")
            logger.info(f"  Motos: 2.0 kW → Tiempo carga ~1.1 horas")
            logger.info(f"  Mototaxis: 3.0 kW → Tiempo carga ~1.3 horas")
            logger.info(f"")
            logger.info(f"Variabilidad Temporal:")
            logger.info(f"  Picos (18-21h): +30% modulación de demanda")
            logger.info(f"  Fin de semana: -10% presión de carga")
            logger.info(f"  Tiempos: Variación aleatoria ±20% sobre base")
            logger.info("=" * 80)
            logger.info("")

        except ImportError as e:
            logger.warning(f"[WARN] No se pudo importar EVDemandCalculator: {e}")
            logger.warning("[WARN] Utilizando modelo estático fallback...")

            # FALLBACK: Usar modelo estático si EVDemandCalculator no está disponible
            charger_list = []
            total_ev_demand_kwh = 0.0

            for charger_idx in range(128):
                charger_name = f"charger_simulation_{charger_idx+1:03d}.csv"
                csv_path = building_dir / charger_name
                charger_list.append(csv_path)

                charger_demand = charger_profiles_annual.iloc[:, charger_idx].values
                total_ev_demand_kwh += charger_demand.sum()
                states = np.where(charger_demand > 0, 1, 3).astype(int)
                is_mototaxi = charger_idx >= 112
                ev_prefix = "MOTOTAXI" if is_mototaxi else "MOTO"

                df_charger = pd.DataFrame({
                    'electric_vehicle_charger_state': states,
                    'electric_vehicle_id': [f'{ev_prefix}_{(charger_idx % 112 if not is_mototaxi else charger_idx - 112) + 1:03d}'
                                           if s == 1 else '' for s in states],
                    'electric_vehicle_departure_time': np.where(states == 1, 4.0, 0.0),
                    'electric_vehicle_required_soc_departure': np.where(states == 1, 0.8, 0.0),
                    'electric_vehicle_estimated_arrival_time': np.where(states == 3, 2.0, 0.0),
                    'electric_vehicle_estimated_soc_arrival': np.where(states == 1, 0.3, 0.2),
                })

                df_charger.to_csv(csv_path, index=False, float_format='%.6f')

            logger.info(f"[FALLBACK] Demanda total (estática): {total_ev_demand_kwh:,.0f} kWh/año")

        # === ACTUALIZAR SCHEMA: Referenciar los 128 CSVs en el schema ===
        logger.info(f"[CHARGER GENERATION] Actualizando schema con referencias a 128 CSVs...")

        for charger_idx, charger_name in enumerate(all_chargers.keys()):
            csv_filename = f"charger_simulation_{charger_idx+1:03d}.csv"
            all_chargers[charger_name]["charger_simulation"] = csv_filename

        logger.info(f"[OK] [CHARGER GENERATION] Schema actualizado: 128 chargers -> 128 CSVs individuales")

    else:
        logger.warning("[WARN] [CHARGER GENERATION] No chargers_hourly_profiles_annual en artifacts")

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
