from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import shutil
import logging
import re

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class BuiltDataset:
    dataset_dir: Path
    schema_path: Path
    building_name: str

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
        out["_charger_list"] = charger_paths
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
    
    # === CHARGERS RESULTS (dimensionamiento OE2) ===
    chargers_results = interim_dir / "oe2" / "chargers" / "chargers_results.json"
    if chargers_results.exists():
        artifacts["chargers_results"] = json.loads(chargers_results.read_text(encoding="utf-8"))
        logger.info(f"Cargados resultados de chargers OE2: {artifacts['chargers_results'].get('n_chargers_recommended', 0)} chargers")
    
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

def build_citylearn_dataset(
    cfg: Dict[str, Any],
    raw_dir: Path,
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
        from citylearn.data import DataSet  # type: ignore
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
    logger.info(f"Using CityLearn template from: {template_dir}")

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
        logger.info(f"Preservando {len(electric_vehicles_def)} definiciones de EVs del template")

    # === CREAR 2 BUILDINGS: Playa_Motos y Playa_Mototaxis ===
    # Cada playa tiene su propia infraestructura de carga
    bname_template, b_template = _find_first_building(schema)
    
    # Crear building para Playa de Motos
    b_motos = json.loads(json.dumps(b_template))
    b_motos["name"] = "Playa_Motos"
    if isinstance(b_motos.get("electric_vehicle_storage"), dict):
        b_motos["electric_vehicle_storage"]["active"] = True
    else:
        b_motos["electric_vehicle_storage"] = {"active": True}
    
    # Crear building para Playa de Mototaxis
    b_mototaxis = json.loads(json.dumps(b_template))
    b_mototaxis["name"] = "Playa_Mototaxis"
    if isinstance(b_mototaxis.get("electric_vehicle_storage"), dict):
        b_mototaxis["electric_vehicle_storage"]["active"] = True
    else:
        b_mototaxis["electric_vehicle_storage"] = {"active": True}
    
    # Configurar schema con ambos buildings
    schema["buildings"] = {
        "Playa_Motos": b_motos,
        "Playa_Mototaxis": b_mototaxis,
    }
    logger.info("Creados 2 buildings separados: Playa_Motos y Playa_Mototaxis")
    
    # Referencia al primer building para compatibilidad (se usará para PV/BESS compartido)
    b = b_motos
    bname = "Playa_Motos"
    
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
        logger.info(f"Usando parametros solares de OE2: {pv_dc_kw} kWp")
    
    # Preferir resultados BESS actualizados; si no existen, usar parámetros del schema
    if "bess" in artifacts:
        bess_cap = float(artifacts["bess"].get("capacity_kwh", 0.0))
        bess_pow = float(artifacts["bess"].get("nominal_power_kw", 0.0))
        logger.info(f"Usando resultados BESS de OE2: {bess_cap} kWh, {bess_pow} kW")
    elif "bess_params" in artifacts:
        bess_params = artifacts["bess_params"]
        bess_cap = float(bess_params.get("electrical_storage", {}).get("capacity", 0.0))
        bess_pow = float(bess_params.get("electrical_storage", {}).get("nominal_power", 0.0))
        logger.info(f"Usando parametros BESS de OE2 (schema): {bess_cap} kWh, {bess_pow} kW")

    # === ACTUALIZAR PV Y BESS EN AMBOS BUILDINGS ===
    # El sistema PV+BESS es compartido entre ambas playas
    for building_name, building in schema["buildings"].items():
        # Actualizar/Crear PV - SIEMPRE crear si no existe y tenemos potencia > 0
        if pv_dc_kw > 0:
            # Distribuir PV proporcionalmente: 87.5% motos (112/128), 12.5% mototaxis (16/128)
            pv_share = 0.875 if building_name == "Playa_Motos" else 0.125
            building_pv_kw = pv_dc_kw * pv_share
            
            if not isinstance(building.get("pv"), dict):
                # Crear configuración PV desde cero
                building["pv"] = {
                    "type": "citylearn.energy_model.PV",
                    "autosize": False,
                    "nominal_power": building_pv_kw,
                    "attributes": {
                        "nominal_power": building_pv_kw,
                    }
                }
                logger.info(f"{building_name}: CREADO pv con nominal_power = {building_pv_kw:.1f} kWp")
            else:
                # Actualizar existente
                building["pv"]["nominal_power"] = building_pv_kw
                if isinstance(building["pv"].get("attributes"), dict):
                    building["pv"]["attributes"]["nominal_power"] = building_pv_kw
                else:
                    building["pv"]["attributes"] = {"nominal_power": building_pv_kw}
                logger.info(f"{building_name}: Actualizado pv.nominal_power = {building_pv_kw:.1f} kWp")
        
        if isinstance(building.get("photovoltaic"), dict):
            if isinstance(building["photovoltaic"].get("attributes"), dict):
                building["photovoltaic"]["attributes"]["nominal_power"] = building_pv_kw
            building["photovoltaic"]["nominal_power"] = building_pv_kw
        
        # Actualizar BESS - Distribuir proporcionalmente entre playas
        if bess_cap is not None and bess_cap > 0:
            bess_share = 0.875 if building_name == "Playa_Motos" else 0.125
            building_bess_cap = bess_cap * bess_share
            building_bess_pow = bess_pow * bess_share if bess_pow else None
            
            if not isinstance(building.get("electrical_storage"), dict):
                building["electrical_storage"] = {
                    "type": "citylearn.energy_model.Battery",
                    "autosize": False,
                    "capacity": building_bess_cap,
                    "attributes": {"capacity": building_bess_cap}
                }
            else:
                building["electrical_storage"]["capacity"] = building_bess_cap
                if building_bess_pow is not None:
                    building["electrical_storage"]["nominal_power"] = building_bess_pow
                if isinstance(building["electrical_storage"].get("attributes"), dict):
                    building["electrical_storage"]["attributes"]["capacity"] = building_bess_cap
                    if building_bess_pow is not None:
                        building["electrical_storage"]["attributes"]["nominal_power"] = building_bess_pow
            logger.info(f"{building_name}: BESS {building_bess_cap:.1f} kWh, {building_bess_pow:.1f} kW")

    # === CREAR CHARGERS DESDE OE2 (usando chargers_citylearn per-toma) ===
    # Distribuir chargers entre Playa_Motos y Playa_Mototaxis
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

            # === SEPARAR CHARGERS POR TIPO: MOTO vs MOTOTAXI ===
            chargers_motos: Dict[str, Any] = {}
            chargers_mototaxis: Dict[str, Any] = {}
            
            for idx, row in chargers_df.iterrows():
                charger_name = str(row.get("charger_id", f"charger_mall_{idx+1}"))
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

                # Clasificar por tipo: MOTO (2kW) vs MOTOTAXI (3kW)
                # Los chargers MOTO tienen nombres como MOTO_CH_* y power_kw=2.0
                # Los chargers MOTOTAXI tienen nombres como MOTO_TAXI_CH_* y power_kw=3.0
                if "TAXI" in charger_name.upper() or power_kw >= 2.5:
                    chargers_mototaxis[charger_name] = new_charger
                else:
                    chargers_motos[charger_name] = new_charger

            # Asignar chargers a cada building
            b_motos = schema["buildings"]["Playa_Motos"]
            b_mototaxis = schema["buildings"]["Playa_Mototaxis"]
            
            b_motos["chargers"] = chargers_motos
            b_mototaxis["chargers"] = chargers_mototaxis
            
            # Limpiar inactive_actions en ambos buildings
            for building in [b_motos, b_mototaxis]:
                inactive_actions = building.get("inactive_actions", [])
                ev_actions = ["electric_vehicle_storage", "electric_vehicle_charger"]
                for ev_act in ev_actions:
                    if ev_act in inactive_actions:
                        inactive_actions.remove(ev_act)
                building["inactive_actions"] = inactive_actions

            power_motos = sum(c.get("attributes", {}).get("nominal_power", 0) for c in chargers_motos.values())
            power_mototaxis = sum(c.get("attributes", {}).get("nominal_power", 0) for c in chargers_mototaxis.values())
            
            logger.info(f"Playa_Motos: {len(chargers_motos)} chargers, {power_motos:.1f} kW")
            logger.info(f"Playa_Mototaxis: {len(chargers_mototaxis)} chargers, {power_mototaxis:.1f} kW")
            logger.info(f"Total: {total_devices} chargers, {power_motos + power_mototaxis:.1f} kW")
        else:
            logger.warning("No se pudo leer chargers_citylearn.csv; se mantiene la configuración existente.")

    if "charger_profile_variants" in artifacts:
        variant_meta = artifacts["charger_profile_variants"]
        variant_dir = artifacts.get("charger_profile_variants_dir")
        if variant_dir is not None:
            target_variants_dir = out_dir / "charger_profile_variants"
            target_variants_dir.mkdir(parents=True, exist_ok=True)
            schema_variants: List[Dict[str, Any]] = []
            for variant in variant_meta.get("variants", []):
                profile_name = variant.get("profile_path")
                if not profile_name:
                    continue
                source_path = variant_dir / profile_name
                if not source_path.exists():
                    logger.warning(f"Falta el perfil {profile_name} en {variant_dir}")
                    continue
                dest_path = target_variants_dir / profile_name
                shutil.copy2(source_path, dest_path)
                variant_record = variant.copy()
                variant_record["profile_path"] = str(Path("charger_profile_variants") / profile_name)
                schema_variants.append(variant_record)
            if schema_variants:
                schema["charger_profile_variants"] = schema_variants
                logger.info(f"Copiados {len(schema_variants)} perfiles estocásticos a {target_variants_dir}")
        else:
            logger.warning("No se encontró el directorio de perfiles de cargadores para los escenarios estocásticos")

    # Discover and overwrite relevant CSVs
    paths = _discover_csv_paths(schema, out_dir)
    energy_path = paths.get("energy_simulation")
    if energy_path is None or not energy_path.exists():
        raise FileNotFoundError("Could not locate energy_simulation CSV in template dataset.")

    df_energy = pd.read_csv(energy_path)
    n = len(df_energy)

    # Build mall load and PV generation series for length n
    # Usar datos de CityLearn preparados si existen
    mall_series = None
    if "building_load_citylearn" in artifacts:
        building_load = artifacts["building_load_citylearn"]
        if len(building_load) >= n:
            mall_series = building_load['non_shiftable_load'].values[:n]
            logger.info(f"Usando demanda de building_load preparado: {len(mall_series)} registros")
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
                    logger.info(f"Usando demanda real del mall: {len(mall_series)} registros")
                else:
                    hourly_profile = series.groupby(series.index.hour).mean()
                    hourly_profile = hourly_profile.reindex(range(24), fill_value=0.0)
                    mall_series = _repeat_24h_to_length(hourly_profile.values, n)
                    logger.info("Demanda real incompleta, repitiendo perfil horario promedio")

    if mall_series is None:
        mall_energy_day = float(cfg["oe2"]["mall"]["energy_kwh_day"])
        mall_shape = cfg["oe2"]["mall"].get("shape_24h")  # may be None
        if mall_shape is None:
            # Default same as OE2 bess module
            from iquitos_citylearn.oe2.bess import default_mall_shape_24h  # local import
            mall_shape_arr = default_mall_shape_24h()
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
            logger.info(f"Usando solar_generation preparado: {len(pv_per_kwp)} registros")
    
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
                logger.info(f"Usando solar_ts [{col}]: {len(pv_per_kwp)} registros")
                break
    
    if pv_per_kwp is None or len(pv_per_kwp) < n:
        # fallback: repeat mean 24h from template solar column if it exists
        pv_per_kwp = np.zeros(n, dtype=float)
        logger.warning("No se encontraron datos solares de OE2, usando ceros")

    pv_per_kwp = pv_per_kwp[:n]
    # CityLearn expects inverter AC power per kW in W/kW.
    if dt_hours > 0:
        pv_per_kwp = pv_per_kwp / dt_hours * 1000.0

    # Identify columns to overwrite in energy_simulation (template-dependent names)
    def find_col(regex_list: List[str]) -> Optional[str]:
        for col in df_energy.columns:
            for rgx in regex_list:
                if re.search(rgx, col, re.IGNORECASE):
                    return col
        return None

    load_col = find_col([r"non[_ ]?shiftable", r"electricity[_ ]?load"])
    solar_col = find_col([r"solar[_ ]?generation"])

    if load_col is None:
        raise ValueError("Template energy_simulation file does not include a non_shiftable_load-like column.")
    df_energy[load_col] = mall_series

    if solar_col is not None:
        df_energy[solar_col] = pv_per_kwp
    else:
        # If no solar column exists, leave template as-is (PV device may be absent).
        logger.warning("No solar_generation-like column found; PV may be ignored by this dataset.")

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
    charger_list: List[Path] = []
    if "_charger_list" in paths:
        charger_list = paths["_charger_list"]
    # Build a generic daily charger simulation for the same length n
    opening = int(cfg["oe2"]["ev_fleet"]["opening_hour"])
    closing = int(cfg["oe2"]["ev_fleet"]["closing_hour"])

    # EV daily energy requirement from OE2 recommended profile, else 0
    ev_energy_day = 0.0
    if "ev_profile_24h" in artifacts and "energy_kwh" in artifacts["ev_profile_24h"].columns:
        ev_energy_day = float(artifacts["ev_profile_24h"]["energy_kwh"].sum())

    steps_per_hour = int(round(1.0 / dt_hours))
    steps_per_day = int(round(24.0 / dt_hours))

    # Arrival/departure steps within a day
    arrival_step = opening * steps_per_hour
    departure_step = (closing + 1) * steps_per_hour  # depart after closing hour
    departure_step = min(departure_step, steps_per_day)  # clamp

    # Build schedule arrays - usar NaN para valores no aplicables (formato CityLearn)
    state = np.full(n, 3, dtype=int)  # 3 = commuting/sin EV
    ev_names = list(schema.get("electric_vehicles_def", {}).keys())
    ev_id = np.full(n, np.nan, dtype=object)  # NaN cuando no hay EV
    dep_time = np.full(n, np.nan, dtype=float)  # NaN cuando no hay EV
    req_soc = np.full(n, np.nan, dtype=float)  # NaN cuando no hay EV
    arr_time = np.full(n, np.nan, dtype=float)  # NaN cuando hay EV conectado
    arr_soc = np.full(n, np.nan, dtype=float)  # NaN cuando hay EV conectado

    # SOC de llegada y salida requerido (en %)
    soc_arr = 20.0  # 20% SOC al llegar
    soc_req = 90.0  # 90% SOC requerido al salir

    for t in range(n):
        day_step = t % steps_per_day
        if arrival_step <= day_step < departure_step:
            # EV conectado (state=1)
            state[t] = 1
            if ev_names:
                ev_id[t] = ev_names[t % len(ev_names)]
            dep_time[t] = float(departure_step - day_step)  # Horas hasta salida
            req_soc[t] = soc_req  # SOC requerido al salir (%)
            arr_time[t] = np.nan  # No aplica cuando está conectado
            arr_soc[t] = np.nan  # No aplica cuando está conectado
        else:
            # Sin EV (state=3 = commuting)
            state[t] = 3
            ev_id[t] = np.nan  # NaN = sin EV
            dep_time[t] = np.nan  # No aplica
            req_soc[t] = np.nan  # No aplica
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

    # === GENERAR CSVs PARA TODOS LOS CHARGERS DE TODOS LOS BUILDINGS ===
    n_chargers_oe2 = 31  # default
    if "chargers_results" in artifacts:
        n_chargers_oe2 = int(artifacts["chargers_results"].get("n_chargers_recommended", 31))
    
    # Iterar sobre TODOS los buildings para generar CSVs de chargers
    total_chargers_generated = 0
    for building_name, building_cfg in schema["buildings"].items():
        chargers_in_building = building_cfg.get("chargers", {})
        for charger_name, charger_cfg in chargers_in_building.items():
            charger_csv = charger_cfg.get("charger_simulation", f"{charger_name}.csv")
            charger_path = out_dir / charger_csv
            
            # Distribuir EVs entre chargers - algunos activos, otros esperando
            charger_idx = int(charger_name.split("_")[-1]) if "_" in charger_name else 1
            
            # Crear variación para simular distribución de carga
            if charger_idx <= n_chargers_oe2 // 3:
                # Chargers principales: más activos
                charger_df.to_csv(charger_path, index=False)
            else:
                # Chargers secundarios: menos activos (estado alternado)
                # Usar vectorización en lugar de bucle for (mucho más rápido)
                secondary_df = charger_df.copy()
                # Crear máscara para filas que deben estar desconectadas
                t_arr = np.arange(len(secondary_df) - 1)  # Excluir la fila adicional
                mask = ((t_arr // 2) % 2) == (charger_idx % 2)
                # Extender mask para incluir la última fila
                mask = np.concatenate([mask, [mask[-1] if len(mask) > 0 else False]])
                secondary_df.loc[mask, "electric_vehicle_charger_state"] = 3
                secondary_df.loc[mask, "electric_vehicle_id"] = np.nan
                secondary_df.loc[mask, "electric_vehicle_departure_time"] = np.nan
                secondary_df.loc[mask, "electric_vehicle_required_soc_departure"] = np.nan
                secondary_df.to_csv(charger_path, index=False)
            total_chargers_generated += 1
        
        logger.info(f"{building_name}: Generados {len(chargers_in_building)} archivos CSV de chargers")
    
    logger.info(f"Total: Generados {total_chargers_generated} archivos CSV de simulación de chargers")

    # También generar para chargers del template original si existen
    for i, cp in enumerate(charger_list):
        if not cp.exists():
            continue
        # If multiple chargers exist, only the first is active; others always disconnected.
        if i == 0:
            charger_df.to_csv(cp, index=False)
        else:
            # Charger sin EV conectado (state=3, todo NaN)
            disconnected_df = pd.DataFrame({
                "electric_vehicle_charger_state": np.full(n+1, 3, dtype=int),
                "electric_vehicle_id": np.full(n+1, np.nan, dtype=object),
                "electric_vehicle_departure_time": np.full(n+1, np.nan, dtype=float),
                "electric_vehicle_required_soc_departure": np.full(n+1, np.nan, dtype=float),
                "electric_vehicle_estimated_arrival_time": np.concatenate([arr_time, [arr_time[-1]]]),
                "electric_vehicle_estimated_soc_arrival": np.concatenate([arr_soc, [arr_soc[-1]]]),
            })
            disconnected_df.to_csv(cp, index=False)

    # Save schema
    schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")


    # --- Schema variants for emissions comparison ---
    # 1) PV+BESS (current schema.json)
    (out_dir / "schema_pv_bess.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")

    # 2) Grid-only variant: disable PV and BESS by setting nominal values to 0.
    schema_grid = json.loads(json.dumps(schema))
    
    # Desactivar PV y BESS en TODOS los buildings
    for bname_grid, b_grid in schema_grid.get("buildings", {}).items():
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
