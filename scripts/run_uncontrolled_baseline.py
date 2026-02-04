"""
Ejecuta construccion de dataset + calculo baseline sin agentes.

Fases:
1. Construye dataset desde artefactos OE2
2. Calcula baseline sin control inteligente (1 ano completo)

Genera:
- Schema CityLearn
- CSV de timeseries
- Metricas baseline: grid import, CO2, PV utilization
"""

import sys
from pathlib import Path
import json
import logging
import pandas as pd
import numpy as np
import traceback
from datetime import datetime

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts._common import load_all
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset

logger = logging.getLogger(__name__)


def extract_baseline_diagnostics(results_dir: Path, agent_name: str = "uncontrolled") -> pd.DataFrame:
    """
    Extrae diagnósticos del archivo de resultados de simulación.

    Retorna DataFrame con columnas:
    - hour: hora del día (0-23)
    - day: día del año (1-365)
    - timestamp: timestamp completo
    - ev_power_total_kw: potencia EV total [kW]
    - ev_power_playa1_kw: potencia EV playa 1 [kW]
    - ev_power_playa2_kw: potencia EV playa 2 [kW]
    - grid_import_kw: importación de red [kW]
    - grid_import_hourly_kwh: importación horaria [kWh]
    - grid_import_daily_kwh: importación acumulada del día [kWh]
    - bess_soc_percent: SOC del BESS [%]
    - bess_power_kw: potencia BESS [kW] (- descarga, + carga)
    - pv_power_kw: potencia solar [kW]
    - is_peak_hour: 1 si está en 18-21h, 0 c.c.
    - sessions_served_peak_playa1: sesiones atendidas en pico (playa 1)
    - sessions_served_peak_playa2: sesiones atendidas en pico (playa 2)
    """

    # Buscar archivo de resultados
    results_file = results_dir / f"{agent_name}_simulation_results.json"
    if not results_file.exists():
        raise FileNotFoundError(f"No se encontró {results_file}")

    logger.info(f"Cargando resultados desde {results_file}")
    with open(results_file, "r") as f:
        results = json.load(f)

    # Extraer datos por timestep
    timesteps = results.get("timesteps", [])
    if not timesteps:
        raise ValueError("No hay datos de timesteps en los resultados")

    rows = []
    daily_import_kwh = 0.0
    prev_hour = 0

    for ts_idx, ts_data in enumerate(timesteps):
        # Hora y día del año
        # Suponiendo que los timesteps están en orden secuencial (1 hora cada uno)
        hour_of_year = ts_idx
        hour = hour_of_year % 24
        day = hour_of_year // 24 + 1  # 1-indexed

        # Si el día cambió, reiniciar acumulador
        if hour < prev_hour:
            daily_import_kwh = 0.0
        prev_hour = hour

        # Es hora pico (18-21h)
        is_peak = 1 if 18 <= hour <= 21 else 0

        # Extraer potencias
        ev_power_total = ts_data.get("ev_power_total_kw", 0.0)
        ev_power_playa1 = ts_data.get("ev_power_playa1_kw", 0.0)
        ev_power_playa2 = ts_data.get("ev_power_playa2_kw", 0.0)

        grid_import = ts_data.get("grid_import_kw", 0.0)
        grid_import_kwh = grid_import  # 1 hora = valor en kW es kWh
        daily_import_kwh += grid_import_kwh

        bess_soc = ts_data.get("bess_soc_percent", 0.0)
        bess_power = ts_data.get("bess_power_kw", 0.0)
        pv_power = ts_data.get("pv_power_kw", 0.0)

        # Sesiones en pico
        sessions_peak_p1 = ts_data.get("sessions_served_peak_playa1", 0)
        sessions_peak_p2 = ts_data.get("sessions_served_peak_playa2", 0)

        rows.append({
            "hour": hour,
            "day": day,
            "hour_of_year": hour_of_year,
            "timestamp": f"2024-{int(day//365.25*12)+1:02d}-{int(day%365/30.5)+1:02d}T{hour:02d}:00:00",
            "ev_power_total_kw": ev_power_total,
            "ev_power_playa1_kw": ev_power_playa1,
            "ev_power_playa2_kw": ev_power_playa2,
            "grid_import_kw": grid_import,
            "grid_import_hourly_kwh": grid_import_kwh,
            "grid_import_daily_kwh": daily_import_kwh,
            "bess_soc_percent": bess_soc,
            "bess_power_kw": bess_power,
            "pv_power_kw": pv_power,
            "is_peak_hour": is_peak,
            "sessions_served_peak_playa1": sessions_peak_p1,
            "sessions_served_peak_playa2": sessions_peak_p2,
        })

    df = pd.DataFrame(rows)
    logger.info(f"Extraídos {len(df)} timesteps")

    return df


def compute_baseline_summary(df: pd.DataFrame) -> dict:
    """
    Calcula métricas resumen del baseline.
    """

    summary = {
        # Potencia pico
        "ev_peak_power_max_kw": float(df["ev_power_total_kw"].max()),
        "ev_peak_power_mean_kw": float(df["ev_power_total_kw"].mean()),
        "ev_peak_power_std_kw": float(df["ev_power_total_kw"].std()),

        # Importación
        "grid_import_total_kwh": float(df["grid_import_hourly_kwh"].sum()),
        "grid_import_mean_kw": float(df["grid_import_kw"].mean()),
        "grid_import_peak_kw": float(df["grid_import_kw"].max()),

        # Importación en pico (18-21h)
        "grid_import_peak_hours_kwh": float(
            df[df["is_peak_hour"] == 1]["grid_import_hourly_kwh"].sum()
        ),
        "grid_import_peak_hours_mean_kw": float(
            df[df["is_peak_hour"] == 1]["grid_import_kw"].mean()
        ),

        # SOC BESS
        "bess_soc_min_percent": float(df["bess_soc_percent"].min()),
        "bess_soc_max_percent": float(df["bess_soc_percent"].max()),
        "bess_soc_mean_percent": float(df["bess_soc_percent"].mean()),

        # SOC en pico
        "bess_soc_during_peak_min": float(
            df[df["is_peak_hour"] == 1]["bess_soc_percent"].min()
        ),
        "bess_soc_during_peak_mean": float(
            df[df["is_peak_hour"] == 1]["bess_soc_percent"].mean()
        ),

        # Potencia por playa
        "ev_power_playa1_max_kw": float(df["ev_power_playa1_kw"].max()),
        "ev_power_playa2_max_kw": float(df["ev_power_playa2_kw"].max()),

        # Fairness (ratio máximo)
        "playa_power_ratio": float(
            df["ev_power_playa1_kw"].max() / max(df["ev_power_playa2_kw"].max(), 1.0)
        ),
    }

    return summary


def build_dataset_phase(cfg: dict, rp) -> bool:
    """Fase 1: Construir dataset desde artefactos OE2"""
    try:
        logger.info("=" * 80)
        logger.info("FASE 1: CONSTRUCCION DE DATASET")
        logger.info("=" * 80)

        logger.info("Construyendo dataset desde OE2 artifacts...")
        dataset = build_citylearn_dataset(
            cfg=cfg,
            _raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )

        logger.info(f"[OK] Dataset construido exitosamente")
        logger.info(f"[OK] Schema: {dataset.schema_path}")
        return True

    except Exception as e:
        logger.error(f"[ERROR] Dataset build fallo: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def run_baseline_calculation() -> dict:
    """
    Ejecuta cálculo real del baseline (sin control inteligente).

    Calcula:
    - CO₂ del grid sin optimización
    - Uso de solar sin control inteligente
    - Motos y mototaxis cargados (demanda base)
    - Comparación para reducción de CO₂
    """
    import numpy as np

    logger.info("[BASELINE] Iniciando cálculo baseline REAL...")

    # Cargar datos
    pv_path = PROJECT_ROOT / "data" / "interim" / "oe2" / "solar" / "pv_generation_timeseries.csv"
    charger_path = PROJECT_ROOT / "data" / "interim" / "oe2" / "chargers" / "chargers_hourly_profiles_annual.csv"
    mall_path = PROJECT_ROOT / "data" / "interim" / "oe2" / "demandamallkwh" / "demanda_mall_horaria_anual.csv"

    # PV Generation
    if pv_path.exists():
        pv_df = pd.read_csv(pv_path)
        # Buscar columna de generación
        gen_cols = [c for c in pv_df.columns if 'gen' in c.lower() or 'power' in c.lower() or 'kw' in c.lower() or 'ac' in c.lower()]
        if gen_cols:
            pv_gen = pv_df[gen_cols[0]].values
        else:
            numeric_cols = pv_df.select_dtypes(include=['number']).columns
            pv_gen = pv_df[numeric_cols[-1]].values if len(numeric_cols) > 0 else np.zeros(8760)
        logger.info(f"[OK] PV generation: {len(pv_gen)} rows, total={np.sum(pv_gen):,.0f} kWh")
    else:
        pv_gen = np.zeros(8760)
        logger.warning("[WARN] PV file not found, using zeros")

    # EV Charger Demand (128 chargers)
    if charger_path.exists():
        charger_df = pd.read_csv(charger_path)
        ev_demand = charger_df.sum(axis=1).values
        logger.info(f"[OK] EV demand: {len(ev_demand)} rows, total={np.sum(ev_demand):,.0f} kWh")
    else:
        ev_demand = np.full(8760, 96.33)  # Default
        logger.warning("[WARN] Charger profiles not found, using default")

    # Mall Load
    if mall_path.exists():
        mall_df = pd.read_csv(mall_path)
        numeric_cols = mall_df.select_dtypes(include=['number']).columns
        mall_load = mall_df[numeric_cols[0]].values if len(numeric_cols) > 0 else np.full(8760, 1411.88)
        logger.info(f"[OK] Mall load: {len(mall_load)} rows, total={np.sum(mall_load):,.0f} kWh")
    else:
        mall_load = np.full(8760, 1411.88)
        logger.warning("[WARN] Mall load not found, using default")

    # Asegurar longitud 8760
    if len(pv_gen) != 8760:
        pv_gen = np.resize(pv_gen, 8760)
    if len(ev_demand) != 8760:
        ev_demand = np.resize(ev_demand, 8760)
    if len(mall_load) != 8760:
        mall_load = np.resize(mall_load, 8760)

    # Parámetros CO₂
    carbon_intensity = 0.4521  # kg CO₂/kWh (Iquitos thermal grid)
    ev_co2_avoided_factor = 2.146  # kg CO₂ evitado por kWh EV vs gasolina

    # BESS parameters
    bess_capacity = 4520  # kWh
    bess_power = 2712  # kW
    bess_soc = bess_capacity * 0.50  # Start at 50%
    bess_min = bess_capacity * 0.10
    bess_max = bess_capacity * 0.95
    bess_eff = 0.95

    # Simulación baseline (sin control inteligente)
    total_demand = ev_demand + mall_load
    grid_import = np.zeros(8760)
    pv_used = np.zeros(8760)
    pv_curtailed = np.zeros(8760)

    for h in range(8760):
        pv = pv_gen[h]
        demand = total_demand[h]

        # 1. PV directo a cargas
        pv_to_load = min(pv, demand)
        pv_used[h] = pv_to_load
        pv_remaining = pv - pv_to_load
        demand_remaining = demand - pv_to_load

        # 2. PV exceso a BESS
        if pv_remaining > 0 and bess_soc < bess_max:
            charge = min(pv_remaining, bess_power, (bess_max - bess_soc) / bess_eff)
            bess_soc += charge * bess_eff
            pv_remaining -= charge

        # 3. BESS descarga para demanda
        if demand_remaining > 0 and bess_soc > bess_min:
            discharge = min(demand_remaining, bess_power, (bess_soc - bess_min) * bess_eff)
            bess_soc -= discharge / bess_eff
            demand_remaining -= discharge

        # 4. Grid import para resto
        grid_import[h] = demand_remaining

        # 5. Curtail excess
        pv_curtailed[h] = pv_remaining

    # Calcular métricas
    total_pv_gen = np.sum(pv_gen)
    total_pv_used = np.sum(pv_used)
    total_pv_curtailed = np.sum(pv_curtailed)
    total_grid_import = np.sum(grid_import)
    total_ev_demand = np.sum(ev_demand)
    total_mall_load = np.sum(mall_load)

    # CO₂ calculations
    co2_grid_kg = total_grid_import * carbon_intensity
    co2_avoided_ev_kg = total_ev_demand * ev_co2_avoided_factor  # vs gasolina
    co2_avoided_solar_kg = total_pv_used * carbon_intensity  # vs grid

    # Motos y mototaxis (OE3 REAL - 2026-02-04)
    # DIARIO: 1,800 motos + 260 mototaxis = 2,060 vehículos/día
    # ANUAL: 657,000 motos + 94,900 mototaxis = 751,900 vehículos/año
    motos_per_day = 1800
    mototaxis_per_day = 260
    total_motos = motos_per_day * 365
    total_mototaxis = mototaxis_per_day * 365

    results = {
        "type": "baseline_uncontrolled",
        "timestamp": datetime.now().isoformat(),
        "duration_hours": 8760,
        "energy": {
            "pv_generation_kwh": float(total_pv_gen),
            "pv_used_kwh": float(total_pv_used),
            "pv_curtailed_kwh": float(total_pv_curtailed),
            "ev_demand_kwh": float(total_ev_demand),
            "mall_load_kwh": float(total_mall_load),
            "total_demand_kwh": float(np.sum(total_demand)),
            "grid_import_kwh": float(total_grid_import),
        },
        "emissions": {
            "co2_grid_kg": float(co2_grid_kg),
            "co2_avoided_ev_kg": float(co2_avoided_ev_kg),
            "co2_avoided_solar_kg": float(co2_avoided_solar_kg),
            "co2_net_kg": float(co2_grid_kg - co2_avoided_solar_kg),
            "carbon_intensity_kg_kwh": carbon_intensity,
        },
        "ev_fleet": {
            "motos_charged_annual": int(total_motos),
            "mototaxis_charged_annual": int(total_mototaxis),
            "total_sessions_annual": int(total_motos + total_mototaxis),
            "motos_per_day": motos_per_day,
            "mototaxis_per_day": mototaxis_per_day,
        },
        "efficiency": {
            "pv_utilization_pct": float(total_pv_used / max(total_pv_gen, 1) * 100),
            "grid_dependency_pct": float(total_grid_import / max(np.sum(total_demand), 1) * 100),
            "self_sufficiency_pct": float((np.sum(total_demand) - total_grid_import) / max(np.sum(total_demand), 1) * 100),
        }
    }

    logger.info("")
    logger.info("=" * 80)
    logger.info("BASELINE RESULTS (Sin Control Inteligente)")
    logger.info("=" * 80)
    logger.info(f"  PV Generado:        {total_pv_gen:>15,.0f} kWh")
    logger.info(f"  PV Utilizado:       {total_pv_used:>15,.0f} kWh ({results['efficiency']['pv_utilization_pct']:.1f}%)")
    logger.info(f"  PV Descartado:      {total_pv_curtailed:>15,.0f} kWh")
    logger.info(f"  Grid Import:        {total_grid_import:>15,.0f} kWh")
    logger.info(f"  Demanda EV:         {total_ev_demand:>15,.0f} kWh")
    logger.info(f"  Demanda Mall:       {total_mall_load:>15,.0f} kWh")
    logger.info("")
    logger.info(f"  CO₂ Grid:           {co2_grid_kg:>15,.0f} kg")
    logger.info(f"  CO₂ Evitado (EV):   {co2_avoided_ev_kg:>15,.0f} kg")
    logger.info(f"  CO₂ Evitado (Solar):{co2_avoided_solar_kg:>15,.0f} kg")
    logger.info("")
    logger.info(f"  Motos/año:          {total_motos:>15,}")
    logger.info(f"  Mototaxis/año:      {total_mototaxis:>15,}")
    logger.info("=" * 80)

    return results


def main():
    """Pipeline: Dataset build + Baseline calculation"""
    try:
        # Cargar config
        cfg, rp = load_all("configs/default.yaml")
        rp.ensure()

        logger.info("\n")
        logger.info("=" * 80)
        logger.info("PIPELINE COMPLETO: DATASET BUILD + BASELINE CALCULATION")
        logger.info("=" * 80)
        logger.info(f"Inicio: {datetime.now().isoformat()}")
        logger.info("Configuracion: Sin entrenamiento de agentes (SAC/PPO/A2C saltados)")
        logger.info("=" * 80)

        # Fase 1: Dataset
        if not build_dataset_phase(cfg, rp):
            logger.error("\n[FATAL] Dataset build fallo. Abortando.")
            return False

        # Fase 2: Baseline calculation (REAL)
        logger.info("\n")
        logger.info("=" * 80)
        logger.info("FASE 2: CALCULO DE BASELINE (SIN CONTROL INTELIGENTE)")
        logger.info("=" * 80)

        baseline_results = run_baseline_calculation()

        # Guardar resultados
        output_path = PROJECT_ROOT / "outputs" / "baseline_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(baseline_results, f, indent=2)
        logger.info(f"[OK] Baseline guardado en: {output_path}")

        logger.info("\n")
        logger.info("=" * 80)
        logger.info("PIPELINE COMPLETO [OK]")
        logger.info("=" * 80)
        logger.info(f"Finalizacion: {datetime.now().isoformat()}")
        logger.info("\nProximos pasos:")
        logger.info("  1. Revisar metricas en outputs/baseline_results.json")
        logger.info("  2. Comparar con agentes entrenados (SAC/PPO/A2C)")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error(f"\n[FATAL] Pipeline fallo: {str(e)}")
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    main()
