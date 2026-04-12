"""
schema_builder.py — Generador de datos y schema CityLearn v2 para Iquitos.

Genera a partir de los datos OE2 reales:
  data/interim/citylearn_v2/
    energy_simulation.csv   — non_shiftable_load, solar_generation, temp, etc.
    weather.csv             — irradiancia, temperatura, predicciones
    carbon_intensity.csv    — 0.4521 kg CO₂/kWh (constante Iquitos)
    schema_iquitos.json     — schema completo para CityLearnEnv

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
_OUTPUT_DIR = _PROJECT_ROOT / "data" / "interim" / "citylearn_v2"

# === Constantes del sistema Iquitos ===
PV_NOMINAL_KWP: float = 4050.0          # kWp instalados
BESS_CAPACITY_KWH: float = 2000.0       # kWh capacidad BESS
BESS_NOMINAL_POWER_KW: float = 400.0    # kW potencia nominal BESS
BESS_EFFICIENCY: float = 0.95           # eficiencia round-trip
CO2_GRID_KG_PER_KWH: float = 0.4521    # kg CO₂/kWh (MINEM 2024, Iquitos)
SECONDS_PER_TIMESTEP: int = 3600        # 1 hora
N_TIMESTEPS: int = 8760                 # 1 año horario


def build_citylearn_schema(
    output_dir: Optional[Path] = None,
    data_dir: Optional[Path] = None,
) -> Path:
    """Genera CSVs y schema JSON para CityLearnEnv.

    Parameters
    ----------
    output_dir : Path, optional
        Directorio de salida. Default: data/interim/citylearn_v2/
    data_dir : Path, optional
        Directorio de datos fuente. Default: data/iquitos_ev_mall/

    Returns
    -------
    Path
        Ruta al schema JSON generado.
    """
    out = output_dir or _OUTPUT_DIR
    src = data_dir or _DATA_IQUITOS
    out.mkdir(parents=True, exist_ok=True)

    logger.info("Cargando datos Iquitos desde %s", src)

    # --- 1. Cargar datos fuente ---
    solar_df = pd.read_csv(src / "solar_generation.csv")
    bess_df = pd.read_csv(src / "bess_timeseries.csv")
    mall_df = pd.read_csv(src / "mall_demand.csv")
    chargers_df = pd.read_csv(src / "chargers_timeseries.csv")

    n = len(solar_df)
    assert n == N_TIMESTEPS, f"Solar CSV: esperado {N_TIMESTEPS} filas, encontrado {n}"

    # Extraer datetime para reconstruir month/hour/day_type
    datetime_series = pd.to_datetime(solar_df["datetime"]) if "datetime" in solar_df.columns else pd.date_range("2024-01-01", periods=n, freq="h")

    month = datetime_series.dt.month.to_numpy(dtype=np.int32)      # 1-12
    hour = datetime_series.dt.hour.to_numpy(dtype=np.int32)        # 0-23 → CityLearn usa 0-23
    # day_type: 1=lunes ... 7=domingo, 8=feriado (CityLearn convention)
    day_type = (datetime_series.dt.dayofweek + 1).to_numpy(dtype=np.int32)  # 1-7

    # --- 2. non_shiftable_load: mall + EV desglosado (kWh/h) ---
    # Mall demand real desde mall_demand.csv
    mall_kwh = mall_df["mall_demand_kwh"].to_numpy(dtype=np.float32)

    # Energía EV real por tipo de vehículo desde chargers_timeseries.csv
    # cargadores 00-14: motos (15 cargadores × 2 sockets = 30 sockets)
    # cargadores 15-18: mototaxis (4 cargadores × 2 sockets = 8 sockets)
    ev_motos_kwh = chargers_df["ev_energia_motos_kwh"].to_numpy(dtype=np.float32)
    ev_mototaxis_kwh = chargers_df["ev_energia_mototaxis_kwh"].to_numpy(dtype=np.float32)
    ev_kwh = ev_motos_kwh + ev_mototaxis_kwh

    non_shiftable_load = mall_kwh + ev_kwh  # kWh/h total (mall + motos + mototaxis)

    # --- 2b. CO₂ directo evitado por tipo (para reward y métricas) ---
    # Salvar como columnas adicionales en energy_simulation para acceso en reward
    co2_motos_kg = chargers_df["co2_reduccion_motos_kg"].to_numpy(dtype=np.float32)
    co2_mototaxis_kg = chargers_df["co2_reduccion_mototaxis_kg"].to_numpy(dtype=np.float32)
    co2_directo_kg = chargers_df["reduccion_directa_co2_kg"].to_numpy(dtype=np.float32)
    motos_por_hora = chargers_df["motos_cargadas_hora"].to_numpy(dtype=np.float32)
    mototaxis_por_hora = chargers_df["mototaxis_cargadas_hora"].to_numpy(dtype=np.float32)

    logger.info(
        "Demanda: mall=%.1f kWh/año | motos=%.1f kWh/año | mototaxis=%.1f kWh/año | CO₂ directo=%.1f kg/año",
        mall_kwh.sum(), ev_motos_kwh.sum(), ev_mototaxis_kwh.sum(), co2_directo_kg.sum(),
    )

    # --- 3. solar_generation: W/kW (inverter output per 1 kWp) ---
    # potencia_kw total del parque → dividir por potencia nominal total
    solar_kwh = solar_df["potencia_kw"].to_numpy(dtype=np.float32)
    # Convertir: [kW total] → [W/kW] = kW_total * 1000 / kWp_nominal
    solar_generation_w_per_kw = (solar_kwh * 1000.0 / PV_NOMINAL_KWP).astype(np.float32)

    # --- 4. Temperatura interior (approx = temperatura ambiente en Iquitos) ---
    temp_c = solar_df["temperatura_c"].to_numpy(dtype=np.float32) if "temperatura_c" in solar_df.columns else np.full(n, 28.0, dtype=np.float32)

    # --- 5. energy_simulation.csv ---
    # non_shiftable_load = SOLO MALL.
    # Los EVs (motos + mototaxis) son controlados paso a paso por
    # IquitosEVChargingWrapper según las acciones del agente.
    # Las columnas ev_* se guardan para que el wrapper las cargue.
    energy_sim_df = pd.DataFrame({
        "month": month,
        "hour": hour,
        "day_type": day_type,
        "indoor_dry_bulb_temperature": temp_c,
        "non_shiftable_load": mall_kwh,         # SOLO MALL (EVs → wrapper)
        "dhw_demand": np.zeros(n, dtype=np.float32),
        "cooling_demand": np.zeros(n, dtype=np.float32),
        "heating_demand": np.zeros(n, dtype=np.float32),
        "solar_generation": solar_generation_w_per_kw,
    })
    es_path = out / "energy_simulation.csv"
    energy_sim_df.to_csv(es_path, index=False)
    logger.info("Guardado: %s", es_path)

    # --- 5b. ev_demand.csv — datos EV para IquitosEVChargingWrapper ---
    # El wrapper carga este archivo para controlar el scheduling de EVs
    ev_demand_df = pd.DataFrame({
        "ev_motos_kwh": ev_motos_kwh,               # kWh/h demanda motos (carg 00-14)
        "ev_mototaxis_kwh": ev_mototaxis_kwh,       # kWh/h demanda mototaxis (carg 15-18)
        "co2_motos_kg": co2_motos_kg,               # kg CO₂ directo evitado motos
        "co2_mototaxis_kg": co2_mototaxis_kg,       # kg CO₂ directo evitado mototaxis
        "co2_directo_kg": co2_directo_kg,           # kg CO₂ directo total (motos+mototaxis)
        "motos_cargadas_hora": motos_por_hora,      # nº motos cargadas/hora
        "mototaxis_cargadas_hora": mototaxis_por_hora,  # nº mototaxis cargadas/hora
    })
    ev_path = out / "ev_demand.csv"
    ev_demand_df.to_csv(ev_path, index=False)
    logger.info(
        "EV demand guardado: %s | motos=%.0f kWh/año | mototaxis=%.0f kWh/año | CO₂ directo=%.0f kg/año",
        ev_path, ev_motos_kwh.sum(), ev_mototaxis_kwh.sum(), co2_directo_kg.sum(),
    )
    # Irradiancia: GHI ≈ 50% difusa + 50% directa para Iquitos tropical
    ghi = solar_df["irradiancia_ghi"].to_numpy(dtype=np.float32) if "irradiancia_ghi" in solar_df.columns else (solar_generation_w_per_kw * 0.9)
    diffuse = ghi * 0.45
    direct = ghi * 0.55
    humidity = np.full(n, 82.0, dtype=np.float32)   # Iquitos ~82% HR anual

    # Predicciones: desplazamiento del propio array (6h, 12h, 24h)
    def _shift(arr: np.ndarray, h: int) -> np.ndarray:
        return np.roll(arr, -h)

    weather_df = pd.DataFrame({
        "outdoor_dry_bulb_temperature": temp_c,
        "outdoor_relative_humidity": humidity,
        "diffuse_solar_irradiance": diffuse,
        "direct_solar_irradiance": direct,
        "outdoor_dry_bulb_temperature_predicted_1": _shift(temp_c, 6),
        "outdoor_dry_bulb_temperature_predicted_2": _shift(temp_c, 12),
        "outdoor_dry_bulb_temperature_predicted_3": _shift(temp_c, 24),
        "outdoor_relative_humidity_predicted_1": _shift(humidity, 6),
        "outdoor_relative_humidity_predicted_2": _shift(humidity, 12),
        "outdoor_relative_humidity_predicted_3": _shift(humidity, 24),
        "diffuse_solar_irradiance_predicted_1": _shift(diffuse, 6),
        "diffuse_solar_irradiance_predicted_2": _shift(diffuse, 12),
        "diffuse_solar_irradiance_predicted_3": _shift(diffuse, 24),
        "direct_solar_irradiance_predicted_1": _shift(direct, 6),
        "direct_solar_irradiance_predicted_2": _shift(direct, 12),
        "direct_solar_irradiance_predicted_3": _shift(direct, 24),
    })
    w_path = out / "weather.csv"
    weather_df.to_csv(w_path, index=False)
    logger.info("Guardado: %s", w_path)

    # --- 7. carbon_intensity.csv ---
    ci_df = pd.DataFrame({
        "carbon_intensity": np.full(n, CO2_GRID_KG_PER_KWH, dtype=np.float32),
    })
    ci_path = out / "carbon_intensity.csv"
    ci_df.to_csv(ci_path, index=False)
    logger.info("Guardado: %s", ci_path)

    # --- 8. schema_iquitos.json ---
    # Usar ruta relativa al directorio de trabajo para evitar problemas
    # con caracteres no-ASCII (ñ) en rutas absolutas en Windows
    try:
        root_dir = str(out.relative_to(Path.cwd()))
    except ValueError:
        # Si no es posible la ruta relativa (discos distintos), usar la absoluta
        root_dir = str(out.resolve())

    schema = {
        "root_directory": root_dir,
        "central_agent": True,
        "buildings": {
            "IquitosEVMall": {
                "include": True,
                "energy_simulation": "energy_simulation.csv",
                "weather": "weather.csv",
                "carbon_intensity": "carbon_intensity.csv",
                "electrical_storage": {
                    "type": "citylearn.energy_model.Battery",
                    "attributes": {
                        "capacity": BESS_CAPACITY_KWH,
                        "nominal_power": BESS_NOMINAL_POWER_KW,
                        "efficiency": BESS_EFFICIENCY,
                        "loss_coefficient": 0.0001,
                        "initial_soc": 0.5,
                    },
                },
                "pv": {
                    "type": "citylearn.energy_model.PV",
                    "attributes": {
                        "nominal_power": PV_NOMINAL_KWP,
                    },
                },
            }
        },
        "observations": {
            "month": {"active": True, "shared_in_central_agent": True},
            "hour": {"active": True, "shared_in_central_agent": True},
            "day_type": {"active": True, "shared_in_central_agent": True},
            "outdoor_dry_bulb_temperature": {"active": True, "shared_in_central_agent": True},
            "diffuse_solar_irradiance": {"active": True, "shared_in_central_agent": True},
            "direct_solar_irradiance": {"active": True, "shared_in_central_agent": True},
            "carbon_intensity": {"active": True, "shared_in_central_agent": True},
            "indoor_dry_bulb_temperature": {"active": False},
            "non_shiftable_load": {"active": True},
            "solar_generation": {"active": True},
            "electrical_storage_soc": {"active": True},
            "net_electricity_consumption": {"active": True},
            "electricity_pricing": {"active": False},
        },
        "actions": {
            "electrical_storage": {"active": True},
        },
        "reward_function": {
            "type": "src.citylearnv2.reward_co2.IquitosCO2Reward",
            "attributes": {
                "w_co2": 0.40,
                "w_solar": 0.25,
                "w_bess": 0.20,
                "w_grid_stable": 0.15,
                "co2_factor": CO2_GRID_KG_PER_KWH,
            },
        },
        "simulation_start_time_step": 0,
        "simulation_end_time_step": N_TIMESTEPS - 1,
        "seconds_per_time_step": SECONDS_PER_TIMESTEP,
        "random_seed": 42,
    }

    schema_path = out / "schema_iquitos.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    logger.info("Schema guardado: %s", schema_path)

    return schema_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    path = build_citylearn_schema()
    print(f"Schema generado: {path}")
