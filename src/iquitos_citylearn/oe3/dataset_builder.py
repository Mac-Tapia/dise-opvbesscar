from __future__ import annotations

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
            f"❌ CRITICAL: Solar timeseries MUST be exactly 8,760 rows (hourly, 1 year).\n"
            f"   Got {n_rows} rows instead.\n"
            f"   This appears to be {'sub-hourly data' if n_rows > 8760 else 'incomplete data'}.\n"
            f"   If using PVGIS 15-minute data, downsample: "
            f"df.set_index('time').resample('h').mean()"
        )

    # Sanity check: if 52,560 rows, it's likely 15-minute (8,760 × 6)
    if n_rows == 52560:
        raise ValueError(
            f"❌ CRITICAL: Solar timeseries has {n_rows} rows = 8,760 × 6 (likely 15-minute data).\n"
            f"   This codebase ONLY supports hourly resolution (8,760 rows per year).\n"
            f"   Downsample using: df.set_index('time').resample('h').mean()"
        )

    logger.info("✅ Solar timeseries validation PASSED: %d rows (hourly, 1 year)", n_rows)

def _find_first_building(schema: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    buildings = schema.get("buildings")
    if not isinstance(buildings, dict) or len(buildings) == 0:
        raise ValueError("schema.json does not define buildings.")
    name = list(buildings.keys())[0]
    return name, buildings[name]

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
    solar_citylearn_csv = interim_dir / "oe2" / "citylearn" / "solar_generation.csv"
    if solar_citylearn_csv.exists():
        artifacts["solar_generation_citylearn"] = pd.read_csv(solar_citylearn_csv)

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
    if not chargers_hourly_annual.exists():
        # Fallback: load daily profile and expand
        chargers_daily = interim_dir / "oe2" / "chargers" / "chargers_hourly_profiles.csv"
        if chargers_daily.exists():
            logger.info(
                "Loading daily charger profiles and expanding to annual (8,760 hours)..."
            )
            df_daily = pd.read_csv(chargers_daily)
            # Drop 'hour' column if present
            if 'hour' in df_daily.columns:
                df_daily = df_daily.drop('hour', axis=1)
            # Expand: repeat 365 times
            df_annual = pd.concat([df_daily] * 365, ignore_index=True)
            artifacts["chargers_hourly_profiles_annual"] = df_annual
            logger.info("Expanded: %d hours/day × 365 days = %d hours total", df_daily.shape[0], len(df_annual))
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
    building_load_path = interim_dir / "oe2" / "citylearn" / "building_load.csv"
    if building_load_path.exists():
        artifacts["building_load_citylearn"] = pd.read_csv(building_load_path)

    # Mall demand
    mall_demand_path = interim_dir / "oe2" / "demandamall" / "demanda_mall_kwh.csv"
    if mall_demand_path.exists():
        artifacts["mall_demand"] = pd.read_csv(mall_demand_path, parse_dates=['FECHA'])

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
        "✅ Generated %d individual charger CSV files",
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

    # === PRESERVAR DEFINICIONES DE EVs ===
    # Copiar electric_vehicles_def del template si existe
    electric_vehicles_def = schema.get("electric_vehicles_def", {})
    if electric_vehicles_def:
        logger.info("Preservando %d definiciones de EVs del template", len(electric_vehicles_def))

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
    schema["buildings"] = {
        "Mall_Iquitos": b_mall,
    }
    logger.info("Creado building unificado: Mall_Iquitos (128 chargers, 4162 kWp PV, 2000 kWh BESS)")

    # Referencia al building único
    b = b_mall
    bname = "Mall_Iquitos"

    # Asegurar que electric_vehicles_def se mantiene en el schema
    if electric_vehicles_def:
        schema["electric_vehicles_def"] = electric_vehicles_def

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
        bess_cap = float(artifacts["bess"].get("capacity_kwh", 0.0))
        bess_pow = float(artifacts["bess"].get("nominal_power_kw", 0.0))
        logger.info("Usando resultados BESS de OE2: %s kWh, %s kW", bess_cap, bess_pow)
    elif "bess_params" in artifacts:
        bess_params = artifacts["bess_params"]
        bess_cap = float(bess_params.get("electrical_storage", {}).get("capacity", 0.0))
        bess_pow = float(bess_params.get("electrical_storage", {}).get("nominal_power", 0.0))
        logger.info("Usando parametros BESS de OE2 (schema): %s kWh, %s kW", bess_cap, bess_pow)

    # === ACTUALIZAR PV Y BESS EN EL BUILDING UNIFICADO ===
    # pylint: disable=all
    # Todo el sistema PV+BESS se asigna al único building Mall_Iquitos  # noqa
    for building_name, building in schema["buildings"].items():
        # Actualizar/Crear PV - TODO el sistema solar al building único
        if pv_dc_kw > 0:
            if not isinstance(building.get("pv"), dict):
                # Crear configuración PV desde cero
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
                # Actualizar existente
                building["pv"]["nominal_power"] = pv_dc_kw
                if isinstance(building["pv"].get("attributes"), dict):
                    building["pv"]["attributes"]["nominal_power"] = pv_dc_kw
                else:
                    building["pv"]["attributes"] = {"nominal_power": pv_dc_kw}
                logger.info("%s: Actualizado pv.nominal_power = %.1f kWp", building_name, pv_dc_kw)

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

    # === CREAR CHARGERS DESDE OE2 (usando chargers_citylearn per-toma) ===
    # Todos los 128 chargers van al building unificado Mall_Iquitos
    if "chargers_results" in artifacts:
        chargers_cfg = artifacts["chargers_results"]
        citylearn_path = chargers_cfg.get("chargers_citylearn_path")
        chargers_df = None
        if citylearn_path and Path(citylearn_path).exists():
            chargers_df = pd.read_csv(citylearn_path)
        elif "chargers_citylearn_path" in chargers_cfg:
            alt = Path(chargers_cfg["chargers_citylearn_path"])
            if alt.exists():
                chargers_df = pd.read_csv(alt)

        if chargers_df is not None and not chargers_df.empty:
            # Cada fila es una toma controlable
            total_devices = len(chargers_df)
            # Asegurar definiciones EV que coincidan con los IDs del charger_simulation.
            ev_defs: Dict[str, Any] = {}
            if isinstance(electric_vehicles_def, dict):
                ev_defs = json.loads(json.dumps(electric_vehicles_def))

            base_ev_def = None
            if ev_defs:
                base_ev_def = next(iter(ev_defs.values()))
            else:
                base_ev_def = {
                    "include": True,
                    "battery": {
                        "type": "citylearn.energy_model.Battery",
                        "autosize": False,
                        "attributes": {
                            "capacity": 40,
                            "nominal_power": 50,
                            "initial_soc": 0.25,
                            "depth_of_discharge": 0.85,
                        },
                    },
                }

            ev_names = [f"EV_Mall_{i}" for i in range(1, total_devices + 1)]
            ev_defs = {name: json.loads(json.dumps(base_ev_def)) for name in ev_names}
            schema["electric_vehicles_def"] = ev_defs

            existing_chargers = b.get("chargers", {})
            charger_template = None
            if existing_chargers:
                charger_template = list(existing_chargers.values())[0]

            # === TODOS LOS CHARGERS VAN AL BUILDING UNIFICADO ===
            all_chargers: Dict[str, Any] = {}
            n_motos = 0
            n_mototaxis = 0
            power_motos = 0.0
            power_mototaxis = 0.0

            for idx, row in chargers_df.iterrows():
                # Convertir idx a int para operaciones aritméticas
                idx_int: int = int(idx) if isinstance(idx, (int, float)) else 0
                charger_name = str(row.get("charger_id", f"charger_mall_{idx_int + 1}"))
                power_kw = float(row.get("power_kw", 2.0))
                sockets = int(row.get("sockets", 1)) if row.get("sockets", 1) else 1
                charger_csv = f"{charger_name}.csv"

                if charger_template:
                    new_charger = json.loads(json.dumps(charger_template))
                    new_charger["charger_simulation"] = charger_csv
                else:
                    new_charger = {
                        "type": "citylearn.electric_vehicle_charger.Charger",
                        "charger_simulation": charger_csv,
                        "autosize": False,
                        "active": True,
                        "attributes": {
                            "nominal_power": power_kw * sockets,
                            "efficiency": 0.95,
                            "charger_type": 0,
                            "max_charging_power": power_kw * sockets,
                            "min_charging_power": 0.5,
                            "num_sockets": sockets,
                        }
                    }

                new_charger["active"] = True
                if "attributes" in new_charger:
                    new_charger["attributes"]["nominal_power"] = power_kw * sockets
                    new_charger["attributes"]["max_charging_power"] = power_kw * sockets
                    new_charger["attributes"]["num_sockets"] = sockets
                else:
                    new_charger["nominal_power"] = power_kw * sockets
                    new_charger["max_charging_power"] = power_kw * sockets
                    new_charger["num_sockets"] = sockets

                # Agregar a la lista unificada y contar por tipo
                all_chargers[charger_name] = new_charger
                if "TAXI" in charger_name.upper() or power_kw >= 2.5:
                    n_mototaxis += 1
                    power_mototaxis += power_kw * sockets
                else:
                    n_motos += 1
                    power_motos += power_kw * sockets

            # Asignar TODOS los chargers al building unificado Mall_Iquitos
            b_mall = schema["buildings"]["Mall_Iquitos"]
            b_mall["chargers"] = all_chargers

            # MANTENER EVs ACTIVOS - Son el core del proyecto
            total_power = power_motos + power_mototaxis
            logger.info("Mall_Iquitos: %d motos (%.1f kW) + %d mototaxis (%.1f kW)", n_motos, power_motos, n_mototaxis, power_mototaxis)
            logger.info("Total: %d chargers, %.1f kW en building unificado", total_devices, total_power)

            # === GENERATE 128 INDIVIDUAL CHARGER CSVs FOR CityLearn v2 ===
            # **CRITICAL**: CityLearn v2 requires separate CSV files for each charger
            # This step converts annual aggregated charger profiles (128 columns) into 128 individual files
            logger.info("\n🔴 CRÍTICO: Generando 128 archivos CSV individuales de cargadores...")

            if "chargers_hourly_profiles_annual" in artifacts:
                charger_profiles_annual = artifacts["chargers_hourly_profiles_annual"]
                building_dir = out_dir / "buildings" / "Mall_Iquitos"

                try:
                    generated_chargers = _generate_individual_charger_csvs(
                        charger_profiles_annual,
                        building_dir,
                        overwrite=True
                    )
                    logger.info("✅ Exitosamente generados %d archivos CSV de chargers para CityLearn v2", len(generated_chargers))
                except Exception as e:
                    logger.error("❌ Error generando charger CSVs: %s", e)
                    raise
            else:
                logger.warning("⚠️ No se encontraron perfiles horarios anuales de chargers en artifacts")
                logger.warning("   Los perfiles de cargadores se deben cargar desde OE2")
            # NOTE: charger_profile_variants section commented - variables not in scope
            # This requires additional refactoring to properly handle variant profiles
            # target_variants_dir.mkdir(parents=True, exist_ok=True)
            # ... variant handling code ...
        else:
            logger.warning("No se encontró el directorio de perfiles de cargadores para los escenarios estocásticos")

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

    # Build mall load and PV generation series for length n
    # Usar datos de CityLearn preparados si existen
    mall_series = None
    if "building_load_citylearn" in artifacts:
        building_load = artifacts["building_load_citylearn"]
        if len(building_load) >= n:
            mall_series = building_load['non_shiftable_load'].values[:n]
            logger.info("Usando demanda de building_load preparado: %d registros", len(mall_series))
        else:
            mall_series = _repeat_24h_to_length(building_load['non_shiftable_load'].values, n)
            logger.info("Demanda building_load incompleta, repitiendo perfil diario")
    elif "mall_demand" in artifacts:
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
                    logger.info("Usando demanda real del mall: %d registros", len(mall_series))
                else:
                    hourly_profile = series.groupby(series.index.hour).mean()
                    hourly_profile = hourly_profile.reindex(range(24), fill_value=0.0)
                    mall_series = _repeat_24h_to_length(hourly_profile.values, n)
                    logger.info("Demanda real incompleta, repitiendo perfil horario promedio")

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

    # PV series - Usar solar_generation de CityLearn si existe
    pv_per_kwp = None
    if "solar_generation_citylearn" in artifacts:
        solar_gen = artifacts["solar_generation_citylearn"]
        if 'solar_generation' in solar_gen.columns:
            pv_per_kwp = solar_gen['solar_generation'].values
            logger.info("[PV] Usando solar_generation preparado: %d registros", len(pv_per_kwp))
            logger.info("   Min: %.6f, Max: %.6f, Mean: %.6f, Sum: %.1f", pv_per_kwp.min(), pv_per_kwp.max(), pv_per_kwp.mean(), pv_per_kwp.sum())

    if pv_per_kwp is None and "solar_ts" in artifacts:
        solar_ts = artifacts["solar_ts"]
        # Resamplear a horario si es necesario
        for col in ['pv_kwh', 'ac_energy_kwh']:
            if col in solar_ts.columns:
                pv_values = solar_ts[col].values
                # Normalizar por kWp
                pv_per_kwp = pv_values / pv_dc_kw if pv_dc_kw > 0 else pv_values
                # Si es subhorario, agregar a horario
                if len(pv_per_kwp) > n:
                    ratio = len(pv_per_kwp) // n
                    pv_per_kwp = np.array([pv_per_kwp[i*ratio:(i+1)*ratio].sum() for i in range(n)])
                logger.info("✅ [PV] Usando solar_ts [%s]: %d registros", col, len(pv_per_kwp))
                logger.info("   Min: %.6f, Max: %.6f, Mean: %.6f, Sum: %.1f", pv_per_kwp.min(), pv_per_kwp.max(), pv_per_kwp.mean(), pv_per_kwp.sum())
                break

    if pv_per_kwp is None or len(pv_per_kwp) < n:
        # fallback: repeat mean 24h from template solar column if it exists
        pv_per_kwp = np.zeros(n, dtype=float)
        logger.warning("[PV] No se encontraron datos solares de OE2, usando ceros")

    pv_per_kwp = pv_per_kwp[:n]
    logger.info("[PV] ANTES transformación: %d registros, suma=%.1f", len(pv_per_kwp), pv_per_kwp.sum())

    # CityLearn expects inverter AC power per kW in W/kW.
    if dt_hours > 0:
        pv_per_kwp = pv_per_kwp / dt_hours * 1000.0
        logger.info("[PV] DESPUES transformación (dt_hours=%s): suma=%.1f", dt_hours, pv_per_kwp.sum())

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

    # SOC de llegada y salida requerido (en %)
    soc_arr = 20.0  # 20% SOC al llegar
    soc_req = 90.0  # 90% SOC requerido al salir

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

    # Agregar una fila adicional al final para evitar indexación fuera de rango
    # CityLearn intenta acceder a t+1 en el último timestep
    last_row = charger_df.iloc[-1:].copy()
    charger_df = pd.concat([charger_df, last_row], ignore_index=True)

    # === GENERAR CSVs PARA CHARGERS USANDO DATASETS ANUALES POR PLAYA ===
    total_chargers_generated = 0
    annual_datasets = artifacts.get("annual_datasets", {})

    # Mapeo de building a playa para datasets anuales
    playa_mapping = {
        "Playa_Motos": "Playa_Motos",
        "Playa_Mototaxis": "Playa_Mototaxis",
    }

    for building_name, building_cfg in schema["buildings"].items():
        chargers_in_building = building_cfg.get("chargers", {})
        playa_name = playa_mapping.get(building_name, building_name)
        playa_data = annual_datasets.get(playa_name, {})
        playa_base_dir = playa_data.get("base_dir")

        for charger_name, charger_cfg in chargers_in_building.items():
            charger_csv = charger_cfg.get("charger_simulation", f"{charger_name}.csv")
            charger_path = out_dir / charger_csv

            # Intentar usar dataset anual si existe
            if playa_base_dir and playa_base_dir.exists():
                annual_csv = playa_base_dir / f"{charger_name}.csv"
                if annual_csv.exists():
                    # Cargar perfil anual de energía del charger
                    annual_df = pd.read_csv(annual_csv)

                    # Truncar a exactamente n timesteps (8760 horarios)
                    annual_df = annual_df.iloc[:n].reset_index(drop=True)

                    # Convertir perfil de energía a formato de simulación CityLearn
                    # CityLearn necesita: state, ev_id, departure_time, req_soc, arrival_time, arrival_soc
                    n_rows = len(annual_df)  # Ahora n_rows == n == 8760

                    # Determinar estado basado en si hay energía (power_kw > 0)
                    power_values = annual_df['power_kw'].values
                    # Castear a float array para operación de comparación
                    power_array: np.ndarray[Any, Any] = np.asarray(power_values, dtype=float)
                    charger_state = np.where(power_array > 0, 1, 3)  # 1=conectado, 3=sin EV

                    # Get power rating from charger specs
                    power_kw = 3.0 if 'MOTO_TAXI' in charger_name else 2.0

                    # Crear DataFrame para CityLearn
                    citylearn_df = pd.DataFrame({
                        "electric_vehicle_charger_state": charger_state,
                        "electric_vehicle_charger_power": np.where(charger_state == 1, power_kw, 0.0),
                        "electric_vehicle_id": np.full(n_rows, default_ev, dtype=object),
                        "electric_vehicle_departure_time": np.where(charger_state == 1,
                            float(departure_step - arrival_step), 0.0),
                        "electric_vehicle_required_soc_departure": np.where(charger_state == 1,
                            soc_req, 0.0),
                        "electric_vehicle_estimated_arrival_time": np.where(charger_state == 3,
                            1.0, 0.0),
                        "electric_vehicle_estimated_soc_arrival": np.full(n_rows, soc_arr),
                    })

                    # Truncar a exactamente 8760 timesteps (1 por hora en un año)
                    # y agregar 1 fila extra para CityLearn (para acceso a t+1)
                    if len(citylearn_df) > 8760:
                        citylearn_df = citylearn_df.iloc[:8760].reset_index(drop=True)

                    last_row_annual = citylearn_df.iloc[-1:].copy()
                    citylearn_df = pd.concat([citylearn_df, last_row_annual], ignore_index=True)

                    citylearn_df.to_csv(charger_path, index=False)
                    total_chargers_generated += 1
                    continue

            # Fallback: usar template genérico
            charger_idx = int(charger_name.split("_")[-1]) if "_" in charger_name else 1
            n_chargers_oe2 = artifacts.get("chargers_results", {}).get("n_chargers_recommended", 128)
            logger.info("[DEBUG FALLBACK] %s: len(charger_df)=%d, n=%d, n+1=%d", charger_name, len(charger_df), n, n+1)

            if charger_idx <= n_chargers_oe2 // 3:
                # Truncar a n+1 antes de guardar
                charger_df_save = charger_df.iloc[:n+1].copy()
                charger_df_save.to_csv(charger_path, index=False)
            else:
                secondary_df = charger_df.copy()
                t_arr = np.arange(len(secondary_df) - 1)
                mask = ((t_arr // 2) % 2) == (charger_idx % 2)
                mask = np.concatenate([mask, [mask[-1] if len(mask) > 0 else False]])
                secondary_df.loc[mask, "electric_vehicle_charger_state"] = 3
                # NO cambiar ev_id - CityLearn lo necesita siempre
                secondary_df.loc[mask, "electric_vehicle_departure_time"] = 0.0
                secondary_df.loc[mask, "electric_vehicle_required_soc_departure"] = 0.0
                # Truncar a n+1 antes de guardar
                secondary_df = secondary_df.iloc[:n+1].copy()
                secondary_df.to_csv(charger_path, index=False)
            total_chargers_generated += 1

        logger.info("%s: Generados %d archivos CSV de chargers", building_name, len(chargers_in_building))

    logger.info("Total: Generados %d archivos CSV de simulación de chargers", total_chargers_generated)

    # NOTA: NO sobrescribir chargers del template original - ya generamos desde OE2
    # El loop anterior ya generó todos los CSVs necesarios usando los datasets anuales
    # El siguiente código está comentado para evitar sobrescribir los valores correctos
    #
    # for i, cp in enumerate(charger_list):
    #     if not cp.exists():
    #         continue
    #     ...

    # Save schema
    schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")


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
