"""
Ejecuta el agente Uncontrolled para capturar baseline de diagnóstico.

Extrae:
- Potencia pico EV (por playa y total)
- Importación de red horaria y diaria
- SOC BESS por hora
- Sesiones atendidas en pico por playa

Genera: uncontrolled_diagnostics.csv
"""

import sys
from pathlib import Path
from dataclasses import asdict
import json
import logging
import numpy as np
import pandas as pd

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts._common import load_all, setup_logging
from iquitos_citylearn.oe3.simulate import run_single_simulation

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


def main():
    setup_logging(level=logging.INFO)
    
    # Cargar config
    cfg, rp = load_all("configs/default.yaml")
    rp.ensure()
    
    logger.info("=" * 80)
    logger.info("FASE 1: Captura de Baseline Uncontrolled (Sin Control)")
    logger.info("=" * 80)
    
    # Ejecutar Uncontrolled
    logger.info("\n[1] Ejecutando agente Uncontrolled...")
    results = run_single_simulation(
        cfg=cfg,
        agent_type="uncontrolled",
        checkpoint_path=None,
        output_dir=rp.oe3_simulations_dir,
    )
    
    logger.info(f"Simulación completada. Resultados guardados en {rp.oe3_simulations_dir}")
    
    # Extraer diagnósticos
    logger.info("\n[2] Extrayendo diagnósticos...")
    df_diagnostics = extract_baseline_diagnostics(
        results_dir=rp.oe3_simulations_dir,
        agent_name="uncontrolled"
    )
    
    # Guardar CSV de diagnóstico
    diagnostics_file = rp.oe3_diagnostics_dir / "uncontrolled_diagnostics.csv"
    diagnostics_file.parent.mkdir(parents=True, exist_ok=True)
    df_diagnostics.to_csv(diagnostics_file, index=False)
    logger.info(f"✓ Diagnósticos guardados en {diagnostics_file}")
    
    # Resumen estadístico
    logger.info("\n[3] Estadísticas de baseline...")
    summary = compute_baseline_summary(df_diagnostics)
    
    # Guardar resumen
    summary_file = rp.oe3_diagnostics_dir / "uncontrolled_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"✓ Resumen guardado en {summary_file}")
    
    # Imprimir resumen
    logger.info("\n" + "=" * 80)
    logger.info("RESUMEN DE BASELINE UNCONTROLLED")
    logger.info("=" * 80)
    logger.info(f"Potencia pico EV total: {summary['ev_peak_power_max_kw']:.2f} kW")
    logger.info(f"Potencia pico EV playa 1: {summary['ev_power_playa1_max_kw']:.2f} kW")
    logger.info(f"Potencia pico EV playa 2: {summary['ev_power_playa2_max_kw']:.2f} kW")
    logger.info(f"Desequilibrio entre playas (ratio): {summary['playa_power_ratio']:.2f}")
    logger.info(f"\nImportación anual: {summary['grid_import_total_kwh']:.0f} kWh")
    logger.info(f"Importación en pico (18-21h): {summary['grid_import_peak_hours_kwh']:.0f} kWh")
    logger.info(f"Potencia importación máxima: {summary['grid_import_peak_kw']:.2f} kW")
    logger.info(f"\nSOC BESS mínimo: {summary['bess_soc_min_percent']:.1f}%")
    logger.info(f"SOC BESS promedio: {summary['bess_soc_mean_percent']:.1f}%")
    logger.info(f"SOC BESS en pico (mínimo): {summary['bess_soc_during_peak_min']:.1f}%")
    logger.info("=" * 80)
    
    return df_diagnostics, summary


if __name__ == "__main__":
    main()
