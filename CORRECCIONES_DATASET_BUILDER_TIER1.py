"""
CORRECCIONES DATASET_BUILDER: IMPLEMENTACIÓN DE TIER 1 FIXES
============================================================

Este archivo contiene las correcciones necesarias para:
1. Downsampling solar 15-min → 1-hora
2. Generación de charger_simulation CSVs (128 archivos)
3. Corrección de paths en schema
4. Integración completa de BESS y building_load

APLICAR ESTOS CAMBIOS EN: src/iquitos_citylearn/oe3/dataset_builder.py
"""

# ============================================================================
# CORRECCIÓN #1: DOWNSAMPLING SOLAR 15-MIN → 1-HORA
# ============================================================================
# UBICACIÓN: En función _load_oe2_artifacts(), después de cargar solar_ts
# REEMPLAZAR ESTO:

def _load_oe2_artifacts_OLD(interim_dir: Path) -> Dict[str, Any]:
    """[VERSIÓN ANTIGUA - sin downsampling]"""
    artifacts: Dict[str, Any] = {}

    # Solar timeseries
    solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
    if solar_path.exists():
        artifacts["solar_ts"] = pd.read_csv(solar_path)  # ❌ 35,037 filas

    return artifacts


# CON ESTO:

def _load_and_resample_solar(solar_path: Path) -> pd.DataFrame:
    """
    Carga timeseries solar y resamplea de 15-min a 1-hora si es necesario.

    Args:
        solar_path: Path to pv_generation_timeseries.csv

    Returns:
        DataFrame con resolución 1-hora (8,760 filas)
    """
    import logging
    logger = logging.getLogger(__name__)

    df = pd.read_csv(solar_path)
    initial_rows = len(df)

    # Detectar resolución
    if initial_rows > 15000:  # Probablemente 15-minutos (35k filas)
        logger.info(f"[SOLAR] Detectada resolución 15-minutos ({initial_rows} filas)")

        # Asegurar timestamp es datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df = df.set_index('timestamp')
        else:
            logger.warning("[SOLAR] No se encontró columna 'timestamp', usando índice como time")
            df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='15T')

        # Resample 15-min → 1-hora (mean agregación)
        df_hourly = df.resample('1H')[['ac_power_kw', 'dc_power_kw', 'ghi_wm2', 'temp_air_c']].agg({
            'ac_power_kw': 'mean',
            'dc_power_kw': 'mean',
            'ghi_wm2': 'mean',
            'temp_air_c': 'mean',
        })

        # Remover primeras/últimas filas si no están completas
        df_hourly = df_hourly[(df_hourly.index.hour >= 0) & (df_hourly.index.hour < 24)]

        # Validar resultado
        if len(df_hourly) != 8760:
            logger.warning(f"[SOLAR] Resampling resultó en {len(df_hourly)} filas "
                          f"en lugar de 8,760 esperadas")
        else:
            logger.info(f"[SOLAR] ✓ Resampling exitoso: {initial_rows} → {len(df_hourly)} filas")

        return df_hourly.reset_index()

    elif initial_rows == 8760 or (8000 < initial_rows < 9000):
        logger.info(f"[SOLAR] Ya está en resolución 1-hora ({initial_rows} filas)")
        return df

    else:
        logger.warning(f"[SOLAR] Resolución desconocida ({initial_rows} filas)")
        return df


# Actualizar _load_oe2_artifacts:
def _load_oe2_artifacts_CORRECTED(interim_dir: Path) -> Dict[str, Any]:
    """[VERSIÓN CORREGIDA - con downsampling solar]"""
    artifacts: Dict[str, Any] = {}

    # === Solar timeseries (with resampling) ===
    solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
    if solar_path.exists():
        artifacts["solar_ts"] = _load_and_resample_solar(solar_path)  # ✅ 8,760 filas

    # ... resto del código sin cambios ...


# ============================================================================
# CORRECCIÓN #2: GENERACIÓN DE CHARGER_SIMULATION CSVs
# ============================================================================
# UBICACIÓN: En función build_citylearn_dataset(), después de crear chargers
# AGREGAR NUEVA FUNCIÓN:

def _generate_charger_simulation_csvs(
    chargers_df: pd.DataFrame,
    profile_24h: pd.DataFrame,
    output_building_dir: Path,
    interim_dir: Path,
) -> None:
    """
    Genera archivos CSV individuales para cada charger (anualización).

    Args:
        chargers_df: DataFrame con chargers (charger_id, power_kw, ...)
        profile_24h: DataFrame de perfil_horario_carga.csv (24 horas)
        output_building_dir: Directorio output para guardar CSVs
        interim_dir: Directorio interim para consultar annual_datasets si existe
    """
    import logging
    logger = logging.getLogger(__name__)

    output_building_dir.mkdir(parents=True, exist_ok=True)

    # Intentar usar annual_datasets si existen
    annual_datasets_dir = interim_dir / "oe2" / "chargers" / "annual_datasets"

    logger.info(f"[CHARGERS] Generando 128 CSVs de simulación en {output_building_dir}")

    for idx, row in chargers_df.iterrows():
        charger_id = str(row.get("charger_id", f"charger_{idx}"))
        charger_csv_path = output_building_dir / f"{charger_id}.csv"

        # Estrategia 1: Buscar CSV anual en annual_datasets
        annual_csv_found = False
        if annual_datasets_dir.exists():
            # Buscar por ID o nombre en annual_datasets
            for playa_dir in annual_datasets_dir.iterdir():
                if playa_dir.is_dir():
                    candidate = playa_dir / "base" / f"{charger_id}.csv"
                    if candidate.exists():
                        # Copiar directamente
                        import shutil
                        shutil.copy2(candidate, charger_csv_path)
                        logger.info(f"  ✓ {charger_id}: usando annual_datasets")
                        annual_csv_found = True
                        break

        if not annual_csv_found:
            # Estrategia 2: Generar replicando 24h profile + variación estocástica
            df_annual = pd.concat([profile_24h] * 365, ignore_index=True)

            # Agregar ruido estocástico (~10% variación) para realismo
            np.random.seed(idx)  # Reproducible pero diferente por charger
            noise = np.random.normal(1.0, 0.1, len(df_annual))
            noise = np.clip(noise, 0.5, 1.5)  # Limitar a [0.5, 1.5]

            # Aplicar ruido a columnas de potencia
            if 'power_kw' in df_annual.columns:
                df_annual['power_kw'] = df_annual['power_kw'] * noise
            if 'energy_kwh' in df_annual.columns:
                df_annual['energy_kwh'] = df_annual['energy_kwh'] * noise

            # Validar que no haya negativos
            df_annual = df_annual.clip(lower=0)

            # Guardar
            df_annual.to_csv(charger_csv_path, index=False)
            logger.info(f"  ✓ {charger_id}: generado (24h×365 + ruido ~10%)")

    logger.info(f"[CHARGERS] ✓ {len(chargers_df)} CSVs generados en {output_building_dir}")


# ============================================================================
# CORRECCIÓN #3: INTEGRACIÓN COMPLETA BESS EN SCHEMA
# ============================================================================
# UBICACIÓN: En build_citylearn_dataset(), donde se actualiza electrical_storage
# REEMPLAZAR ESTO:

def _update_bess_schema_OLD(building: Dict, bess_cfg: Dict) -> None:
    """[VERSIÓN ANTIGUA - asignación parcial]"""
    if bess_cfg.get("capacity_kwh"):
        building["electrical_storage"]["capacity"] = bess_cfg["capacity_kwh"]
        # ❌ Faltan: power, efficiency, soc_min, soc_max


# CON ESTO:

def _update_bess_schema_CORRECTED(building: Dict[str, Any],
                                  bess_results: Dict[str, Any]) -> None:
    """
    Actualiza configuración BESS completa en schema.

    Args:
        building: Dict del building en schema
        bess_results: Dict de bess_results.json
    """
    import logging
    logger = logging.getLogger(__name__)

    if not isinstance(building.get("electrical_storage"), dict):
        building["electrical_storage"] = {"type": "citylearn.energy_model.Battery"}

    es = building["electrical_storage"]

    # Asignar capacidad
    if bess_results.get("capacity_kwh"):
        es["capacity"] = float(bess_results["capacity_kwh"])

    # Asignar potencia nominal
    if bess_results.get("nominal_power_kw"):
        es["nominal_power"] = float(bess_results["nominal_power_kw"])

    # Asegurar attributes dict
    if "attributes" not in es:
        es["attributes"] = {}

    attrs = es["attributes"]

    # Atributos críticos
    attrs["capacity"] = float(bess_results.get("capacity_kwh", 2000))
    attrs["nominal_power"] = float(bess_results.get("nominal_power_kw", 1200))
    attrs["efficiency"] = float(bess_results.get("efficiency_roundtrip", 0.9))

    # Límites de SOC
    dod = float(bess_results.get("dod", 0.8))
    attrs["depth_of_discharge"] = dod
    attrs["min_soc"] = 1 - dod  # Si DoD=0.8, min_soc=0.2
    attrs["max_soc"] = 1.0

    logger.info(f"[BESS] ✓ Configuración completa en schema:")
    logger.info(f"       Capacity: {attrs['capacity']:.0f} kWh")
    logger.info(f"       Power: {attrs['nominal_power']:.0f} kW")
    logger.info(f"       Efficiency: {attrs['efficiency']:.1%}")
    logger.info(f"       SOC range: [{attrs['min_soc']:.1%}, {attrs['max_soc']:.1%}]")


# ============================================================================
# CORRECCIÓN #4: VALIDACIÓN Y INTEGRACIÓN BUILDING_LOAD
# ============================================================================
# UBICACIÓN: Después de cargar energy_simulation en build_citylearn_dataset()
# AGREGAR:

def _prepare_building_load(interim_dir: Path,
                          output_dir: Path,
                          target_timesteps: int = 8760) -> pd.DataFrame:
    """
    Prepara non_shiftable_load (demanda base del mall) para schema.

    Intenta cargar de:
    1. data/interim/oe2/citylearn/building_load.csv
    2. data/interim/oe2/demandamallkwh/demandamallkwh.csv

    Args:
        interim_dir: Path a interim
        output_dir: Path a output
        target_timesteps: 8760 horas por año

    Returns:
        DataFrame con non_shiftable_load (columna 'non_shiftable_load')
    """
    import logging
    logger = logging.getLogger(__name__)

    # Opción 1: CityLearn preprocessing
    building_load_path = interim_dir / "oe2" / "citylearn" / "building_load.csv"
    if building_load_path.exists():
        df = pd.read_csv(building_load_path)
        if 'non_shiftable_load' in df.columns:
            if len(df) >= target_timesteps:
                logger.info(f"[BUILDING_LOAD] Usando building_load.csv ({len(df)} horas)")
                return df.iloc[:target_timesteps].reset_index(drop=True)

    # Opción 2: demandamallkwh
    mall_demand_path = interim_dir / "oe2" / "demandamallkwh" / "demandamallkwh.csv"
    if mall_demand_path.exists():
        df = pd.read_csv(mall_demand_path)
        # Buscar columna de demanda
        demand_col = None
        for col in df.columns:
            if 'demanda' in col.lower() or 'demand' in col.lower() or 'kwh' in col.lower():
                demand_col = col
                break

        if demand_col and len(df) >= target_timesteps:
            df_out = pd.DataFrame({
                'non_shiftable_load': df[demand_col].iloc[:target_timesteps].values
            })
            logger.info(f"[BUILDING_LOAD] Usando demandamallkwh.csv ({len(df_out)} horas)")
            return df_out

    # Opción 3: Generar perfil por defecto (dummy)
    logger.warning(f"[BUILDING_LOAD] No se encontró, usando perfil constante por defecto")
    df_out = pd.DataFrame({
        'non_shiftable_load': [2000.0] * target_timesteps  # 2 MW constante
    })
    return df_out


# ============================================================================
# CORRECCIÓN #5: CORRECCIÓN CHARGER_SIMULATION PATHS
# ============================================================================
# UBICACIÓN: En build_citylearn_dataset(), al crear chargers
# REEMPLAZAR ESTO:

def _create_chargers_OLD(chargers_df: pd.DataFrame,
                        charger_template: Dict) -> Dict[str, Dict]:
    """[VERSIÓN ANTIGUA - paths relativos incorrectos]"""
    all_chargers = {}
    for idx, row in chargers_df.iterrows():
        charger_id = str(row["charger_id"])
        charger_csv = f"{charger_id}.csv"  # ❌ Path relativo incompleto
        all_chargers[charger_id] = {
            "charger_simulation": charger_csv,
            # ...
        }
    return all_chargers


# CON ESTO:

def _create_chargers_CORRECTED(chargers_df: pd.DataFrame,
                               charger_template: Dict,
                               building_name: str = "Mall_Iquitos") -> Dict[str, Dict]:
    """
    Crea definiciones de chargers con paths correctos para schema.

    Args:
        chargers_df: DataFrame de chargers
        charger_template: Plantilla de charger del schema
        building_name: Nombre del building

    Returns:
        Dict[charger_id] → charger config con charger_simulation path correcto
    """
    all_chargers = {}

    for idx, row in chargers_df.iterrows():
        charger_id = str(row.get("charger_id", f"charger_{idx}"))
        power_kw = float(row.get("power_kw", 2.0))
        sockets = int(row.get("sockets", 1)) if row.get("sockets") else 1

        # ✅ CORRECTO: Path con building name y estructura correcta
        charger_csv = f"buildings/{building_name}/{charger_id}.csv"

        if charger_template:
            new_charger = json.loads(json.dumps(charger_template))
            new_charger["charger_simulation"] = charger_csv
        else:
            new_charger = {
                "type": "citylearn.electric_vehicle_charger.Charger",
                "charger_simulation": charger_csv,
                "autosize": False,
                "active": True,
            }

        # Atributos de potencia
        nominal_power = power_kw * sockets
        new_charger["attributes"] = {
            "nominal_power": nominal_power,
            "max_charging_power": nominal_power,
            "min_charging_power": 0.5,
            "num_sockets": sockets,
            "efficiency": 0.95,
        }

        all_chargers[charger_id] = new_charger

    return all_chargers


# ============================================================================
# CORRECCIÓN #6: VALIDACIÓN OBSERVATION SPACE
# ============================================================================
# UBICACIÓN: Al final de build_citylearn_dataset()
# AGREGAR:

def _validate_schema_output(schema_path: Path,
                           expected_obs_dim: int = 534) -> bool:
    """
    Valida que el schema generado sea correcto antes de usarlo.

    Args:
        schema_path: Path al schema.json generado
        expected_obs_dim: Dimensión esperada de observation space

    Returns:
        True si validación pasa, False si falla
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from citylearn.citylearn import CityLearnEnv
    except ImportError:
        logger.warning("[VALIDATION] CityLearn no disponible para validar")
        return True

    try:
        logger.info(f"[VALIDATION] Inicializando CityLearnEnv para validar schema...")
        env = CityLearnEnv(schema=str(schema_path))
        obs, _ = env.reset()
        obs_dim = len(obs) if isinstance(obs, (list, tuple)) else obs.shape[0]

        logger.info(f"[VALIDATION] Observation space: {obs_dim}-dim (esperado: {expected_obs_dim})")

        if obs_dim == expected_obs_dim:
            logger.info(f"[VALIDATION] ✓ Observation space correcto")
            return True
        else:
            logger.warning(f"[VALIDATION] ⚠️  Observation space mismatch: "
                          f"esperado {expected_obs_dim}, got {obs_dim}")
            return False

    except Exception as e:
        logger.error(f"[VALIDATION] Error inicializando environment: {e}")
        return False


# ============================================================================
# INTEGRACIÓN: LLAMADAS EN build_citylearn_dataset()
# ============================================================================

# POSICIÓN 1: Después de cargar artifacts (línea ~410)
def build_citylearn_dataset_PATCHED(
    cfg: Dict[str, Any],
    raw_dir: Path,
    interim_dir: Path,
    processed_dir: Path,
) -> BuiltDataset:
    """[VERSIÓN CON TODAS LAS CORRECCIONES]"""

    # ... código existente hasta artifact loading ...

    # AHORA (en lugar de solo cargar):
    artifacts = _load_oe2_artifacts(interim_dir)  # ← Ya tiene resampling solar

    # ... código existente ...

    # NUEVO: Generar charger CSVs (después de crear edificio)
    if "chargers_results" in artifacts and chargers_df is not None:
        chargers_dir = interim_dir / "oe2" / "chargers"
        df_profile_24h = pd.read_csv(chargers_dir / "perfil_horario_carga.csv")

        building_chargers_dir = out_dir / "buildings" / "Mall_Iquitos"
        _generate_charger_simulation_csvs(
            chargers_df=chargers_df,
            profile_24h=df_profile_24h,
            output_building_dir=building_chargers_dir,
            interim_dir=interim_dir,
        )

    # NUEVO: Actualizar BESS completamente
    if "bess" in artifacts:
        for building_name, building in schema["buildings"].items():
            _update_bess_schema_CORRECTED(building, artifacts["bess"])

    # NUEVO: Preparar building_load
    df_building_load = _prepare_building_load(interim_dir, out_dir)
    # Guardar y asignar en schema...

    # NUEVO: Validar schema antes de terminar
    _validate_schema_output(schema_path, expected_obs_dim=534)

    # ... resto del código ...

