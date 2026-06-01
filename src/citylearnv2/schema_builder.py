"""
schema_builder.py — Generador de datasets CityLearn v2 para Iquitos.

Pipeline de datos:
    OE2 raw (data/iquitos_ev_mall/)
        ↓  build_citylearn_schema()
    CityLearn v2 datasets (data/interim/citylearn_v2/)
        ├── energy_simulation.csv    — edificio: mall demand + solar + tarifas OSINERGMIN
        ├── weather.csv              — temperatura, irradiancia + predicciones 6/12/24h
        ├── carbon_intensity.csv     — 0.4521 kg CO₂/kWh constante (MINEM 2024)
        ├── ev_charger_motos.csv     — ChargerSimulation 30 sockets (motos)
        ├── ev_charger_mototaxis.csv — ChargerSimulation 8 sockets (mototaxis)
        └── schema_iquitos.json      — schema completo: BESS + ev_chargers + PV + obs/actions

El IquitosEVChargingWrapper lee EXCLUSIVAMENTE de data/interim/citylearn_v2/.
Los archivos OE2 de data/iquitos_ev_mall/ son la fuente primaria pero NO
se acceden directamente durante el entrenamiento.

Uso:
    python -m src.citylearnv2.schema_builder
    o
    from src.citylearnv2.schema_builder import build_citylearn_schema
    build_citylearn_schema()
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# === Rutas del proyecto ===
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_IQUITOS = _PROJECT_ROOT / "data" / "iquitos_ev_mall"
_OUTPUT_DIR   = _PROJECT_ROOT / "data" / "interim" / "citylearn_v2"

# === Constantes del sistema — leídas automáticamente de los JSONs OE2 ===
# Cada vez que solar_pvlib.py / bess.py / chargers.py regeneran datos, los
# valores se actualizan automáticamente al importar este módulo.
try:
    from src.dimensionamiento.oe2.oe2_metadata import get_metadata as _get_oe2_meta
    _oe2 = _get_oe2_meta()
    PV_NOMINAL_KWP: float         = _oe2.pv_kwp_dc
    BESS_CAPACITY_KWH: float      = _oe2.bess_capacity_kwh
    BESS_NOMINAL_POWER_KW: float  = _oe2.bess_nominal_power_kw
    BESS_EFFICIENCY: float        = _oe2.bess_efficiency
    BESS_MIN_SOC: float           = _oe2.bess_soc_min
    CO2_GRID_KG_PER_KWH: float   = _oe2.co2_factor_kg_kwh
    N_SOCKETS_MOTOS: int          = _oe2.n_sockets_motos
    N_SOCKETS_MOTOTAXIS: int      = _oe2.n_sockets_mototaxis
    CHARGER_POWER_KW: float       = _oe2.charger_power_kw
    EV_MOTO_BAT_KWH: float        = _oe2.ev_moto_bat_kwh
    EV_MOTOTAXI_BAT_KWH: float    = _oe2.ev_mototaxi_bat_kwh
    EV_SOC_MIN_PCT: float         = _oe2.ev_soc_min * 100.0
    EV_SOC_MAX_PCT: float         = _oe2.ev_soc_max * 100.0
    logger.info("schema_builder: constantes cargadas desde JSONs OE2 reales (pv_kwp=%.0f)", PV_NOMINAL_KWP)
except Exception as _meta_exc:
    logger.warning("schema_builder: no se pudo leer OE2Metadata (%s) — usando fallbacks", _meta_exc)
    PV_NOMINAL_KWP: float         = 4162.0
    BESS_CAPACITY_KWH: float      = 2000.0
    BESS_NOMINAL_POWER_KW: float  = 400.0
    BESS_EFFICIENCY: float        = 0.95
    BESS_MIN_SOC: float           = 0.20
    CO2_GRID_KG_PER_KWH: float   = 0.4521
    N_SOCKETS_MOTOS: int          = 30
    N_SOCKETS_MOTOTAXIS: int      = 8
    CHARGER_POWER_KW: float       = 7.4
    EV_MOTO_BAT_KWH: float        = 4.6
    EV_MOTOTAXI_BAT_KWH: float    = 7.4
    EV_SOC_MIN_PCT: float         = 20.0
    EV_SOC_MAX_PCT: float         = 80.0

CHARGER_EFF: float        = 0.95    # eficiencia cargador (fijo diseño)
SECONDS_PER_TIMESTEP: int = 3600    # 1 hora
N_TIMESTEPS: int          = 8760    # 1 año horario

# Potencia máxima agregada por tipo (derivada de constantes leídas)
MAX_POWER_MOTOS_KW: float     = N_SOCKETS_MOTOS * CHARGER_POWER_KW
MAX_POWER_MOTOTAXIS_KW: float = N_SOCKETS_MOTOTAXIS * CHARGER_POWER_KW
TOTAL_BAT_MOTOS_KWH: float    = N_SOCKETS_MOTOS * EV_MOTO_BAT_KWH
TOTAL_BAT_MOTOTAXIS_KWH: float = N_SOCKETS_MOTOTAXIS * EV_MOTOTAXI_BAT_KWH
MALL_CLOSE_HOUR: int = 22


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _shift(arr: np.ndarray, h: int) -> np.ndarray:
    """Desplaza array h posiciones (predicción circular)."""
    return np.roll(arr, -h)


def _compute_arrival_time(active: np.ndarray, max_lookahead: int = 25) -> np.ndarray:
    """Para cada timestep inactivo, calcula cuántos pasos hasta el siguiente activo."""
    n = len(active)
    arrival = np.full(n, -1, dtype=np.int32)
    for t in range(n):
        if active[t] == 0:
            for dt in range(1, min(max_lookahead, n - t)):
                if active[t + dt] > 0:
                    arrival[t] = dt
                    break
    return arrival


# ────────────────────────────────────────────────────────────────────────────
# Generadores de datasets individuales
# ────────────────────────────────────────────────────────────────────────────

def _build_energy_simulation(
    mall_df: pd.DataFrame,
    solar_df: pd.DataFrame,
    month: np.ndarray,
    hour: np.ndarray,
    day_type: np.ndarray,
    out: Path,
    co2_df: pd.DataFrame | None = None,
    tariffs_df: pd.DataFrame | None = None,
) -> Path:
    """Genera energy_simulation.csv — dataset de edificio para CityLearn v2.

    Columnas requeridas por EnergySimulation (CityLearn v2):
      month, hour, day_type, indoor_dry_bulb_temperature,
      non_shiftable_load [kWh/h], dhw_demand, cooling_demand, heating_demand,
      solar_generation [W/kWp]

    Archivo auxiliar tariffs_osinergmin.csv (leído solo por el wrapper):
      is_hora_punta, tarifa_soles_kwh (tarifa_total con AAPP), mall_cost_soles,
      mall_co2_indirect_kg (variable × co2_factor horario)
    """
    n = len(mall_df)
    mall_kwh = mall_df["mall_demand_kwh"].to_numpy(dtype=np.float32)
    temp_c   = (solar_df["temperatura_c"].to_numpy(dtype=np.float32)
                if "temperatura_c" in solar_df.columns
                else np.full(n, 28.0, dtype=np.float32))
    # solar_generation: W por kWp instalado (CityLearn v2 convention)
    solar_gen_w_per_kwp = (solar_df["potencia_kw"].to_numpy(dtype=np.float32)
                           * 1000.0 / PV_NOMINAL_KWP)

    # ── Tarifas OSINERGMIN: usar tarifa_total (energía + AAPP) del dataset completo ─
    # tarifa_soles_kwh = tarifa_total (incluye cargo AAPP 0.0116 S/./kWh)
    # mall_co2_indirect_kg = mall_kwh × co2_factor horario variable
    if tariffs_df is not None and "tarifa_total_soles_kwh" in tariffs_df.columns:
        tarifa_arr = tariffs_df["tarifa_total_soles_kwh"].to_numpy(dtype=np.float32)
    else:
        tarifa_arr = mall_df["tarifa_soles_kwh"].to_numpy(dtype=np.float32)

    # ── CityLearn v2 standard columns (ONLY — no extras, EnergySimulation is strict) ─
    # electricity_pricing NO se incluye aquí: CityLearn v2.5.0 no lo acepta en
    # energy_simulation.csv (TypeError). Se inyecta como obs extra en el wrapper
    # (tarifa_norm, is_hora_punta) desde tariffs_osinergmin.csv.
    es_df = pd.DataFrame({
        "month":                         month,
        "hour":                          hour,
        "day_type":                      day_type,
        "indoor_dry_bulb_temperature":   temp_c,
        "non_shiftable_load":            mall_kwh,   # SOLO MALL — EVs van en charger CSVs
        "dhw_demand":                    np.zeros(n, dtype=np.float32),
        "cooling_demand":                np.zeros(n, dtype=np.float32),
        "heating_demand":                np.zeros(n, dtype=np.float32),
        "solar_generation":              solar_gen_w_per_kwp,
    })
    path = out / "energy_simulation.csv"
    es_df.to_csv(path, index=False)

    if co2_df is not None and "co2_factor_kg_kwh" in co2_df.columns:
        co2_factor_arr = co2_df["co2_factor_kg_kwh"].to_numpy(dtype=np.float32)
    else:
        co2_factor_arr = np.full(n, CO2_GRID_KG_PER_KWH, dtype=np.float32)

    is_punta_arr = mall_df["is_hora_punta"].to_numpy(dtype=np.int32)
    mall_cost_arr  = mall_kwh * tarifa_arr
    mall_co2_arr   = mall_kwh * co2_factor_arr

    # ── Archivo auxiliar del wrapper — NO forma parte del schema CityLearn ────
    tariff_df = pd.DataFrame({
        "is_hora_punta":        is_punta_arr,
        "tarifa_soles_kwh":     tarifa_arr,       # tarifa_total (energía + AAPP)
        "mall_cost_soles":      mall_cost_arr,    # coste real mall × tarifa_total
        "mall_co2_indirect_kg": mall_co2_arr,     # CO₂ indirecto variable (estacionalidad)
    })
    tariff_path = out / "tariffs_osinergmin.csv"
    tariff_df.to_csv(tariff_path, index=False)

    logger.info(
        "energy_simulation.csv: mall=%.0f kWh/año | solar=%.0f kWh/año equiv.",
        mall_kwh.sum(),
        solar_df["potencia_kw"].sum(),
    )
    logger.info(
        "tariffs_osinergmin.csv: tarifa_total HP=%.4f HFP=%.4f S/./kWh | "
        "co2_factor %.4f–%.4f kg/kWh | costo mall=%.0f S/./año",
        float(tarifa_arr.max()), float(tarifa_arr.min()),
        float(co2_factor_arr.min()), float(co2_factor_arr.max()),
        float(mall_cost_arr.sum()),
    )
    return path


def _build_weather(solar_df: pd.DataFrame, out: Path) -> Path:
    """Genera weather.csv — datos meteorológicos + predicciones 6/12/24h."""
    n = len(solar_df)
    ghi      = (solar_df["irradiancia_ghi"].to_numpy(dtype=np.float32)
                if "irradiancia_ghi" in solar_df.columns
                else np.zeros(n, dtype=np.float32))
    temp_c   = (solar_df["temperatura_c"].to_numpy(dtype=np.float32)
                if "temperatura_c" in solar_df.columns
                else np.full(n, 28.0, dtype=np.float32))
    humidity = np.full(n, 82.0, dtype=np.float32)   # ~82% HR anual, Iquitos tropical
    # GHI split: Iquitos nublado (45% difusa, 55% directa aproximado)
    diffuse = ghi * 0.45
    direct  = ghi * 0.55

    df = pd.DataFrame({
        "outdoor_dry_bulb_temperature":        temp_c,
        "outdoor_relative_humidity":           humidity,
        "diffuse_solar_irradiance":            diffuse,
        "direct_solar_irradiance":             direct,
        "outdoor_dry_bulb_temperature_predicted_1": _shift(temp_c, 6),
        "outdoor_dry_bulb_temperature_predicted_2": _shift(temp_c, 12),
        "outdoor_dry_bulb_temperature_predicted_3": _shift(temp_c, 24),
        "outdoor_relative_humidity_predicted_1": _shift(humidity, 6),
        "outdoor_relative_humidity_predicted_2": _shift(humidity, 12),
        "outdoor_relative_humidity_predicted_3": _shift(humidity, 24),
        "diffuse_solar_irradiance_predicted_1": _shift(diffuse, 6),
        "diffuse_solar_irradiance_predicted_2": _shift(diffuse, 12),
        "diffuse_solar_irradiance_predicted_3": _shift(diffuse, 24),
        "direct_solar_irradiance_predicted_1":  _shift(direct, 6),
        "direct_solar_irradiance_predicted_2":  _shift(direct, 12),
        "direct_solar_irradiance_predicted_3":  _shift(direct, 24),
    })
    path = out / "weather.csv"
    df.to_csv(path, index=False)
    logger.info("weather.csv: GHI_max=%.0f W/m² | T_avg=%.1f°C", ghi.max(), temp_c.mean())
    return path


def _build_carbon_intensity(co2_df: pd.DataFrame, out: Path) -> Path:
    """Genera carbon_intensity.csv — factor CO₂ variable por hora (sistema aislado diesel Loreto).

    Fuente real: co2_emissions.csv (data/iquitos_ev_mall/)
    Valores MINEM 2024 para red aislada Iquitos (generación 100% diesel):
      Temporada lluviosa dic-may: base ~0.39 kg CO₂/kWh (caudal ríos alto, plantas diesel optimizadas)
      Temporada seca    jun-nov:  base ~0.47 kg CO₂/kWh (demanda eléctrica máxima, más generadores)
      Hora punta HP 18-23h:       factor × 1.35 (arranque adicional de grupos electrógenos)
      Fuera de punta HFP:         factor × 0.908 (generadores al mínimo)
    Media anual: ~0.4521 kg CO₂/kWh (MINEM 2024, Electro Oriente Loreto)
    Rango: 0.3904–0.6345 kg CO₂/kWh (señal observable por el agente RL)
    """
    co2_arr = co2_df["co2_factor_kg_kwh"].to_numpy(dtype=np.float32)
    df = pd.DataFrame({"carbon_intensity": co2_arr})
    path = out / "carbon_intensity.csv"
    df.to_csv(path, index=False)
    logger.info(
        "carbon_intensity.csv: %.4f-%.4f kg CO2/kWh (diesel Iquitos: lluviosa/seca × HP/HFP, MINEM 2024)",
        float(co2_arr.min()), float(co2_arr.max()),
    )
    return path


def _build_pricing(tariffs_df: pd.DataFrame, out: Path) -> Path:
    """Genera pricing.csv — tarifas OSINERGMIN HP/HFP para CityLearn v2.

    Fuente real: tariffs_osinergmin.csv (data/iquitos_ev_mall/)
    Columna `electricity_pricing` requerida por CityLearn v2 (S./kWh):
      HP  18-23h: tarifa_total_soles_kwh ≈ 0.4616 S./kWh (energía + cargo AAPP)
      HFP 00-17h, 23h: tarifa_total_soles_kwh ≈ 0.2916 S./kWh
    También incluye `electricity_pricing_predicted_*` para forecasting.
    Señal usada por W_COST (0.02) en la función de recompensa multiobjetivo.
    """
    if "tarifa_total_soles_kwh" in tariffs_df.columns:
        price_arr = tariffs_df["tarifa_total_soles_kwh"].to_numpy(dtype=np.float32)
    elif "tarifa_energia_soles_kwh" in tariffs_df.columns:
        price_arr = tariffs_df["tarifa_energia_soles_kwh"].to_numpy(dtype=np.float32)
    else:
        price_arr = tariffs_df.select_dtypes(include=[np.number]).iloc[:, 0].to_numpy(dtype=np.float32)

    df = pd.DataFrame({
        "electricity_pricing":             price_arr,
        "electricity_pricing_predicted_1": np.roll(price_arr, -6),   # +6h ahead
        "electricity_pricing_predicted_2": np.roll(price_arr, -12),  # +12h ahead
        "electricity_pricing_predicted_3": np.roll(price_arr, -24),  # +24h ahead
    })
    path = out / "pricing.csv"
    df.to_csv(path, index=False)
    logger.info(
        "pricing.csv: HP=%.4f HFP=%.4f S./kWh (OSINERGMIN Res. N 047-2024-OS/CD, Electro Oriente)",
        float(price_arr.max()), float(price_arr.min()),
    )
    return path


def _build_ev_charger_datasets(
    chargers_df: pd.DataFrame,
    hour: np.ndarray,
    out: Path,
) -> tuple[Path, Path]:
    """Genera ev_charger_motos.csv y ev_charger_mototaxis.csv en formato CityLearn v2.

    Formato compatible con ChargerSimulation (citylearn.data.ChargerSimulation):
      electric_vehicle_charger_state : 1=parked/plugged, 2=incoming, 3=commuting/idle
      electric_vehicle_id            : identificador de flota
      electric_vehicle_departure_time: pasos hasta salida (-1 si no aplica)
      electric_vehicle_required_soc_departure: SOC objetivo al salir [0-100] (-0.1 si N/A)
      electric_vehicle_estimated_arrival_time: pasos hasta próxima llegada (-1 si N/A)
      electric_vehicle_estimated_soc_arrival : SOC estimado al llegar [0-100] (-0.1 si N/A)

    Columnas adicionales (usadas por IquitosEVChargingWrapper):
      ev_demand_kwh    : kWh/h demanda agregada de la flota
      active_sockets   : número de sockets activos en este timestep
      vehicles_per_hour: vehículos cargados en este timestep

    Arquitectura de sockets (OE2 chargers.py v5.4):
      Motos    : socket_000 … socket_029 (15 carg × 2 sock = 30 sockets, bat 4.6 kWh)
      Mototaxis: socket_030 … socket_037 ( 4 carg × 2 sock =  8 sockets, bat 7.4 kWh)

    Fuente: chargers_timeseries.csv (OE2 simulación estocástica anual)
    """
    n = len(chargers_df)

    # ── 1. Aggregate activity per vehicle type ────────────────────────────────
    motos_active_arr = np.stack([
        chargers_df[f"socket_{i:03d}_active"].to_numpy(dtype=np.float32)
        for i in range(N_SOCKETS_MOTOS)
    ], axis=1).sum(axis=1)   # (n,) — número de sockets motos activos

    mototaxis_active_arr = np.stack([
        chargers_df[f"socket_{i:03d}_active"].to_numpy(dtype=np.float32)
        for i in range(N_SOCKETS_MOTOS, N_SOCKETS_MOTOS + N_SOCKETS_MOTOTAXIS)
    ], axis=1).sum(axis=1)   # (n,) — número de sockets mototaxis activos

    motos_demand    = chargers_df["ev_energia_motos_kwh"].to_numpy(dtype=np.float32)
    mototaxis_demand = chargers_df["ev_energia_mototaxis_kwh"].to_numpy(dtype=np.float32)
    motos_veh_hora  = chargers_df["motos_cargadas_hora"].to_numpy(dtype=np.float32)
    mototaxis_veh_hora = chargers_df["mototaxis_cargadas_hora"].to_numpy(dtype=np.float32)

    # ── 2. ChargerSimulation fields ───────────────────────────────────────────
    # State: 1 = charging/parked, 3 = idle/commuting (no state 2 in aggregate)
    motos_state     = np.where(motos_active_arr > 0, 1, 3).astype(np.int32)
    mototaxis_state = np.where(mototaxis_active_arr > 0, 1, 3).astype(np.int32)

    # departure_time: hours until mall closes (hour 22) — only when state=1
    hours_left       = np.maximum(0, MALL_CLOSE_HOUR - hour).astype(np.int32)
    motos_dep_time   = np.where(motos_state == 1,    hours_left, -1).astype(np.int32)
    mototaxis_dep_time = np.where(mototaxis_state == 1, hours_left, -1).astype(np.int32)

    # required_soc_departure: EV_SOC_MAX_PCT when active, -0.1 otherwise
    motos_soc_dep   = np.where(motos_state == 1,     EV_SOC_MAX_PCT, -0.1).astype(np.float32)
    mototaxis_soc_dep = np.where(mototaxis_state == 1, EV_SOC_MAX_PCT, -0.1).astype(np.float32)

    # arrival_time: steps until next active slot (for idle steps)
    logger.info("Calculando arrival_time motos (puede tardar ~10s)...")
    motos_arr_time   = _compute_arrival_time(motos_active_arr)
    logger.info("Calculando arrival_time mototaxis...")
    mototaxis_arr_time = _compute_arrival_time(mototaxis_active_arr)

    # soc_arrival: EV_SOC_MIN_PCT when next arrival known, -0.1 otherwise
    motos_soc_arr   = np.where(motos_arr_time >= 0,    EV_SOC_MIN_PCT, -0.1).astype(np.float32)
    mototaxis_soc_arr = np.where(mototaxis_arr_time >= 0, EV_SOC_MIN_PCT, -0.1).astype(np.float32)

    # ── 3. Escribir CSVs ──────────────────────────────────────────────────────
    motos_df = pd.DataFrame({
        # ChargerSimulation columns (CityLearn v2 spec)
        "electric_vehicle_charger_state":          motos_state,
        "electric_vehicle_id":                     ["moto_fleet"] * n,
        "electric_vehicle_departure_time":         motos_dep_time,
        "electric_vehicle_required_soc_departure": motos_soc_dep,
        "electric_vehicle_estimated_arrival_time": motos_arr_time,
        "electric_vehicle_estimated_soc_arrival":  motos_soc_arr,
        # Extended columns for IquitosEVChargingWrapper
        "ev_demand_kwh":     motos_demand,       # kWh/h demanda agregada
        "active_sockets":    motos_active_arr.astype(np.int32),  # nº sockets activos
        "vehicles_per_hour": motos_veh_hora,     # vehículos cargados/hora
    })
    motos_path = out / "ev_charger_motos.csv"
    motos_df.to_csv(motos_path, index=False)

    mototaxis_df = pd.DataFrame({
        "electric_vehicle_charger_state":          mototaxis_state,
        "electric_vehicle_id":                     ["mototaxi_fleet"] * n,
        "electric_vehicle_departure_time":         mototaxis_dep_time,
        "electric_vehicle_required_soc_departure": mototaxis_soc_dep,
        "electric_vehicle_estimated_arrival_time": mototaxis_arr_time,
        "electric_vehicle_estimated_soc_arrival":  mototaxis_soc_arr,
        "ev_demand_kwh":     mototaxis_demand,
        "active_sockets":    mototaxis_active_arr.astype(np.int32),
        "vehicles_per_hour": mototaxis_veh_hora,
    })
    mototaxis_path = out / "ev_charger_mototaxis.csv"
    mototaxis_df.to_csv(mototaxis_path, index=False)

    logger.info(
        "ev_charger_motos.csv: %.0f kWh/año | active_max=%d sockets | veh/año=%.0f",
        motos_demand.sum(), motos_active_arr.max(), motos_veh_hora.sum(),
    )
    logger.info(
        "ev_charger_mototaxis.csv: %.0f kWh/año | active_max=%d sockets | veh/año=%.0f",
        mototaxis_demand.sum(), mototaxis_active_arr.max(), mototaxis_veh_hora.sum(),
    )
    return motos_path, mototaxis_path


def _build_schema_json(root_dir: str, out: Path) -> Path:
    """Genera schema_iquitos.json — schema completo CityLearn v2 Iquitos.

    Declara:
      - Edificio IquitosEVMall: energy_simulation + weather + carbon_intensity
      - BESS: 2000 kWh / 400 kW (OE2 bess.py v5.3)
      - PV: 4162 kWp DC (OE2 solar_pvlib, Jinko Tiger Neo JKM580N-72HL4-BDV)
      - EV chargers: motos_aggregate (222 kW, 30 sockets) + mototaxis_aggregate (59.2 kW, 8 sockets)
      - Observaciones activas para entrenamiento RL
      - Acción: electrical_storage (BESS)
    """
    schema = {
        "root_directory": root_dir,
        "central_agent": True,
        "buildings": {
            "IquitosEVMall": {
                "include": True,
                "energy_simulation": "energy_simulation.csv",
                "weather":           "weather.csv",
                "carbon_intensity":  "carbon_intensity.csv",
                "pricing":           "pricing.csv",
                # BESS: OE2 bess.py v5.3 — 2000 kWh / 400 kW / DoD 80%
                # depth_of_discharge=0.8 → min SOC = 20% (CityLearn v2 Battery API)
                # BESS: OE2 bess.py v5.7 — 2000 kWh / 400 kW LFP
                # CityLearn v2 Battery API (citylearn.energy_model.Battery):
                #   depth_of_discharge=0.80 → min SOC = 1.0 - 0.80 = 0.20 (20%)
                #   capacity_loss_coefficient=5e-5: degradación media (~mid-range LFP)
                # Ref: Haarnoja 2018; Raffin 2022 (arXiv:2005.05719); CityLearn GitHub
                "electrical_storage": {
                    "type": "citylearn.energy_model.Battery",
                    "attributes": {
                        "capacity":                  BESS_CAPACITY_KWH,
                        "nominal_power":             BESS_NOMINAL_POWER_KW,
                        "depth_of_discharge":        1.0 - BESS_MIN_SOC,  # 0.80
                        "capacity_loss_coefficient": 5e-5,                 # mid-range LFP degradation
                        "initial_soc":               0.5,
                    },
                },
                # PV: 4162 kWp DC (OE2 solar_pvlib, Iquitos 3.73°S 73.25°O)
                "pv": {
                    "type": "citylearn.energy_model.PV",
                    "attributes": {
                        "nominal_power": PV_NOMINAL_KWP,
                    },
                },
                # EV chargers: representación agregada por tipo de flota
                # motos_aggregate: 15 cargadores × 2 sockets = 30 sockets (bat 4.6 kWh)
                # mototaxis_aggregate: 4 cargadores × 2 sockets = 8 sockets (bat 7.4 kWh)
                "ev_chargers": {
                    "motos_aggregate": {
                        "include": True,
                        "charger_simulation": "ev_charger_motos.csv",
                        "attributes": {
                            "charger_id":           "motos_aggregate",
                            "max_charging_power":   MAX_POWER_MOTOS_KW,    # 222.0 kW
                            "min_charging_power":   0.0,
                            "efficiency":           CHARGER_EFF,
                        },
                        "electric_vehicle": {
                            "battery_capacity":   TOTAL_BAT_MOTOS_KWH,    # 138.0 kWh (30 × 4.6)
                            "min_battery_soc":    EV_SOC_MIN_PCT / 100.0,  # 0.20
                            "max_battery_soc":    EV_SOC_MAX_PCT / 100.0,  # 0.80
                            "charger_power_kw":   CHARGER_POWER_KW,        # 7.4 kW/socket
                            "n_sockets":          N_SOCKETS_MOTOS,          # 30
                        },
                    },
                    "mototaxis_aggregate": {
                        "include": True,
                        "charger_simulation": "ev_charger_mototaxis.csv",
                        "attributes": {
                            "charger_id":           "mototaxis_aggregate",
                            "max_charging_power":   MAX_POWER_MOTOTAXIS_KW,  # 59.2 kW
                            "min_charging_power":   0.0,
                            "efficiency":           CHARGER_EFF,
                        },
                        "electric_vehicle": {
                            "battery_capacity":   TOTAL_BAT_MOTOTAXIS_KWH,  # 59.2 kWh (8 × 7.4)
                            "min_battery_soc":    EV_SOC_MIN_PCT / 100.0,
                            "max_battery_soc":    EV_SOC_MAX_PCT / 100.0,
                            "charger_power_kw":   CHARGER_POWER_KW,
                            "n_sockets":          N_SOCKETS_MOTOTAXIS,       # 8
                        },
                    },
                },
            }
        },
        # ── Observaciones activas para el agente RL ───────────────────────────
        "observations": {
            "month":                        {"active": True,  "shared_in_central_agent": True},
            "hour":                         {"active": True,  "shared_in_central_agent": True},
            "day_type":                     {"active": True,  "shared_in_central_agent": True},
            "outdoor_dry_bulb_temperature": {"active": True,  "shared_in_central_agent": True},
            "diffuse_solar_irradiance":     {"active": True,  "shared_in_central_agent": True},
            "direct_solar_irradiance":      {"active": True,  "shared_in_central_agent": True},
            "carbon_intensity":             {"active": True,  "shared_in_central_agent": True},
            "indoor_dry_bulb_temperature":  {"active": False},
            "non_shiftable_load":           {"active": True},
            "solar_generation":             {"active": True},
            "electrical_storage_soc":       {"active": True},
            "net_electricity_consumption":  {"active": True},
            "electricity_pricing":          {"active": True, "shared_in_central_agent": True},
        },
        # ── Acción: sólo BESS (EVs controlados por el wrapper 3D) ────────────
        "actions": {
            "electrical_storage": {"active": True},
        },
        # ── Función de recompensa interna CityLearn (reemplazada por wrapper) ─
        # IquitosEVChargingWrapper._compute_reward() sustituye esta función.
        # Se mantiene IquitosCO2Reward por compatibilidad con el API de CityLearn.
        "reward_function": {
            "type": "src.citylearnv2.reward_co2.IquitosCO2Reward",
            "attributes": {
                "w_co2":        0.40,
                "w_solar":      0.25,
                "w_bess":       0.20,
                "w_grid_stable": 0.15,
                "co2_factor":   CO2_GRID_KG_PER_KWH,
            },
        },
        "simulation_start_time_step": 0,
        "simulation_end_time_step":   N_TIMESTEPS - 1,
        "seconds_per_time_step":      SECONDS_PER_TIMESTEP,
        "random_seed":                42,
    }

    schema_path = out / "schema_iquitos.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    logger.info("schema_iquitos.json: BESS + PV + 2 EV charger groups (motos + mototaxis)")
    return schema_path


# ────────────────────────────────────────────────────────────────────────────
# Entry point principal
# ────────────────────────────────────────────────────────────────────────────

def build_citylearn_schema(
    output_dir: Optional[Path] = None,
    data_dir: Optional[Path] = None,
) -> Path:
    """Genera todos los datasets CityLearn v2 a partir de datos OE2 reales.

    Lee de data/iquitos_ev_mall/ (fuentes OE2) y escribe en data/interim/citylearn_v2/:

      Datasets CityLearn v2 (todos vinculados al schema):
        energy_simulation.csv    ← solar_generation.csv + mall_demand.csv + weather
        weather.csv              ← solar_generation.csv (GHI, temperatura, viento)
        carbon_intensity.csv     ← co2_emissions.csv (factor CO₂ diesel Iquitos, 0.3904-0.6345)
        pricing.csv              ← tariffs_osinergmin.csv (HP=0.46/HFP=0.29 S./kWh OSINERGMIN)
        ev_charger_motos.csv     ← chargers_timeseries.csv (30 sockets, 270 motos/día)
        ev_charger_mototaxis.csv ← chargers_timeseries.csv (8 sockets, 39 mototaxis/día)
        schema_iquitos.json      — schema completo: BESS + PV + 2 EV charger groups

      Datasets leídos por wrapper directamente (no en schema):
        bess_timeseries.csv      ← data/iquitos_ev_mall/ (SOC ref, dispatch, co2_avoided)
        tariffs_osinergmin.csv   ← data/interim/citylearn_v2/ (tarifa_soles, mall_cost)

      Valores del sistema leídos de JSONs OE2 reales (OE2Metadata):
        pv_kwp=4162 ← CERTIFICACION_SOLAR.json | bess=2000kWh/400kW ← bess_results.json
        n_sockets=38 ← ESPECIFICACION_CARGADORES.json | co2_factor=0.4521 ← bess_results.json

    Parameters
    ----------
    output_dir : Path, optional
        Directorio de salida. Default: data/interim/citylearn_v2/
    data_dir : Path, optional
        Directorio fuente OE2. Default: data/iquitos_ev_mall/

    Returns
    -------
    Path
        Ruta al schema_iquitos.json generado.
    """
    out = output_dir or _OUTPUT_DIR
    src = data_dir or _DATA_IQUITOS
    out.mkdir(parents=True, exist_ok=True)

    logger.info("=== build_citylearn_schema: cargando OE2 desde %s ===", src)

    # ── 1. Cargar datos fuente OE2 ────────────────────────────────────────────
    solar_df    = pd.read_csv(src / "solar_generation.csv")
    mall_df     = pd.read_csv(src / "mall_demand.csv")
    chargers_df = pd.read_csv(src / "chargers_timeseries.csv")

    # Datasets de emisiones y tarifas (generados por data_loader)
    co2_path     = src / "co2_emissions.csv"
    tariffs_path = src / "tariffs_osinergmin.csv"
    co2_df     = pd.read_csv(co2_path)     if co2_path.exists()     else None
    tariffs_df = pd.read_csv(tariffs_path) if tariffs_path.exists() else None
    if co2_df is None:
        logger.warning("co2_emissions.csv no encontrado en %s — usando factor fijo %.4f", src, CO2_GRID_KG_PER_KWH)
    if tariffs_df is None:
        logger.warning("tariffs_osinergmin.csv no encontrado en %s — usando tarifas simples HP/HFP", src)

    n = len(solar_df)
    assert n == N_TIMESTEPS, f"solar_generation.csv: esperado {N_TIMESTEPS} filas, encontrado {n}"
    assert len(mall_df) == n, "mall_demand.csv: número de filas no coincide con solar"
    assert len(chargers_df) == n, "chargers_timeseries.csv: número de filas no coincide"
    if co2_df is not None:
        assert len(co2_df) == n, "co2_emissions.csv: número de filas no coincide"
    if tariffs_df is not None:
        assert len(tariffs_df) == n, "tariffs_osinergmin.csv: número de filas no coincide"

    # Extraer datetime → month / hour / day_type
    if "datetime" in solar_df.columns:
        dt = pd.DatetimeIndex(pd.to_datetime(solar_df["datetime"]))
    else:
        dt = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=n, freq="h"))
    month    = dt.month.to_numpy(dtype=np.int32)            # 1-12
    hour     = dt.hour.to_numpy(dtype=np.int32)             # 0-23
    day_type = (dt.dayofweek + 1).to_numpy(dtype=np.int32)  # 1=lunes … 7=domingo

    # ── 2. energy_simulation.csv + tariffs_osinergmin.csv (wrapper aux) ──────
    _build_energy_simulation(mall_df, solar_df, month, hour, day_type, out,
                             co2_df=co2_df, tariffs_df=tariffs_df)

    # ── 3. weather.csv ────────────────────────────────────────────────────────
    _build_weather(solar_df, out)

    # ── 4. carbon_intensity.csv — factor CO₂ variable (estacionalidad Loreto) ─
    if co2_df is not None:
        _build_carbon_intensity(co2_df, out)
    else:
        # fallback: factor constante si co2_emissions.csv no disponible
        import pandas as _pd
        _ci_df = _pd.DataFrame({"carbon_intensity": np.full(n, CO2_GRID_KG_PER_KWH, dtype=np.float32)})
        (_OUTPUT_DIR / "carbon_intensity.csv" if out == _OUTPUT_DIR else out / "carbon_intensity.csv").parent.mkdir(parents=True, exist_ok=True)
        _ci_df.to_csv(out / "carbon_intensity.csv", index=False)
        logger.info("carbon_intensity.csv: %.4f kg CO₂/kWh constante (fallback)", CO2_GRID_KG_PER_KWH)

    # ── 5. pricing.csv — tarifas OSINERGMIN HP/HFP (señal W_COST del reward) ──
    if tariffs_df is not None:
        _build_pricing(tariffs_df, out)
    else:
        # fallback: tarifa binaria HP/HFP desde mall_demand.csv
        from src.dimensionamiento.oe2.oe2_metadata import get_metadata as _gm2
        _m2 = _gm2()
        _price_hp  = np.float32(_m2.tarifa_hp_soles_kwh)
        _price_hfp = np.float32(_m2.tarifa_hfp_soles_kwh)
        _is_punta  = mall_df["is_hora_punta"].to_numpy(dtype=np.int32)
        _price_arr = np.where(_is_punta, _price_hp, _price_hfp).astype(np.float32)
        _pr_df = pd.DataFrame({
            "electricity_pricing":             _price_arr,
            "electricity_pricing_predicted_1": np.roll(_price_arr, -6),
            "electricity_pricing_predicted_2": np.roll(_price_arr, -12),
            "electricity_pricing_predicted_3": np.roll(_price_arr, -24),
        })
        _pr_df.to_csv(out / "pricing.csv", index=False)
        logger.info("pricing.csv: fallback HP=%.4f HFP=%.4f S./kWh", _price_hp, _price_hfp)

    # ── 6. ev_charger_motos.csv + ev_charger_mototaxis.csv ───────────────────
    _build_ev_charger_datasets(chargers_df, hour, out)

    # ── 7. schema_iquitos.json ────────────────────────────────────────────────
    try:
        root_dir = out.relative_to(Path.cwd()).as_posix()
    except ValueError:
        root_dir = out.resolve().as_posix()

    schema_path = _build_schema_json(root_dir, out)

    logger.info("=== CityLearn v2 datasets generados en %s ===", out)
    return schema_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    path = build_citylearn_schema()
    print(f"Schema generado: {path}")
