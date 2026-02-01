#!/usr/bin/env python
"""
Quick Baseline Calculator - Entrenamiento sin control inteligente (uncontrolled)
Calcula métricas de referencia para comparación con agentes RL
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_baseline():
    """Calcular baseline sin control: todas las cargas conectadas siempre activas"""

    logger.info("=" * 80)
    logger.info("CÁLCULO DE BASELINE (UNCONTROLLED) - Iquitos EV Mall 2026")
    logger.info("=" * 80)

    # Rutas
    data_dir = Path("data/processed/citylearn/iquitos_ev_mall")
    output_dir = Path("outputs/oe3")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Cargar datos de solar PV
    solar_file = data_dir / "weather.csv"
    if not solar_file.exists():
        logger.error(f"❌ No encontrado: {solar_file}")
        raise FileNotFoundError(f"{solar_file}")

    logger.info(f"✓ Cargando solar desde {solar_file}")
    df_weather = pd.read_csv(solar_file)

    if len(df_weather) != 8760:
        logger.error(f"❌ Solar debe tener 8760 filas (hourly), tiene {len(df_weather)}")
        raise ValueError("Datos solares inválidos")

    # Extraer solar generation (PV) - combinar difusa y directa (W/m2 -> kW)
    direct_irr = np.asarray(df_weather['direct_solar_irradiance'].values)  # W/m2
    diffuse_irr = np.asarray(df_weather['diffuse_solar_irradiance'].values)  # W/m2
    total_irr = direct_irr + diffuse_irr  # W/m2
    pv_power = total_irr * 4162 / 1000  # Convertir a kW usando capacidad OE2 (4162 kWp)

    logger.info(f"✓ Solar PV cargado: {len(pv_power)} timesteps, promedio={np.mean(pv_power):.2f} kW")

    # Cargar demanda de carga de EVs
    charger_profile_file = Path("data/interim/oe2/chargers/perfil_horario_carga.csv")
    if not charger_profile_file.exists():
        logger.error(f"❌ No encontrado: {charger_profile_file}")
        raise FileNotFoundError(f"{charger_profile_file}")

    logger.info(f"✓ Cargando demanda de cargadores desde {charger_profile_file}")
    df_profile: pd.DataFrame = pd.read_csv(charger_profile_file)

    # Agrupar por hora (hay 2 filas por hora: 0min y 30min)
    # Usar promedio por hora
    df_hourly = df_profile.groupby('hour_of_day')[['total_demand_kw']].mean()
    hourly_demand = np.asarray(df_hourly['total_demand_kw'].values)  # kW por hora

    logger.info(f"✓ Demanda de cargadores: prom={np.mean(hourly_demand):.2f} kW, pico={np.max(hourly_demand):.2f} kW")

    # Parámetros BESS (OE2)
    bess_capacity_kwh: float = 4520.0  # kWh
    bess_power_kw: float = 2712.0      # kW
    bess_min_soc: float = 0.1          # 10% SOC mínimo
    bess_max_soc: float = 0.95         # 95% SOC máximo
    bess_efficiency: float = 0.95      # 95% round-trip

    # Grid carbon intensity (Iquitos - generación térmica)
    grid_ci: float = 0.4521  # kg CO₂/kWh

    logger.info(f"✓ BESS: {bess_capacity_kwh:.0f} kWh / {bess_power_kw:.0f} kW, {bess_min_soc*100:.0f}%-{bess_max_soc*100:.0f}% SOC")

    # Simulación baseline: sin control inteligente
    # Regla simple: cargar EVs siempre que sea posible, sin control de timing
    logger.info("\n" + "=" * 80)
    logger.info("SIMULACIÓN: Todas las cargas EVs activas continuamente (sin control)")
    logger.info("=" * 80)

    results = {
        "timesteps": [],
        "summary": {}
    }

    bess_soc = bess_capacity_kwh * 0.5  # Iniciar al 50%
    grid_import_total_kwh = 0.0
    bess_charge_total_kwh = 0.0
    bess_discharge_total_kwh = 0.0
    ev_demand_total_kwh = 0.0
    pv_used_direct_kwh = 0.0
    pv_curtailed_kwh = 0.0

    for hour in range(8760):
        pv_gen = pv_power[hour]  # kW
        ev_demand = hourly_demand[hour % 24]  # kW (repetir patrón 24h cada día)

        # Despacho sin control:
        # 1. PV directo a EVs
        pv_to_ev = min(pv_gen, ev_demand)
        pv_to_bess = max(0, pv_gen - pv_to_ev)

        # 2. Cargar BESS si hay PV excedente y SOC < max
        if pv_to_bess > 0 and bess_soc < bess_capacity_kwh * bess_max_soc:
            bess_charge = min(pv_to_bess, bess_power_kw,
                            (bess_capacity_kwh * bess_max_soc - bess_soc) / bess_efficiency)
            bess_soc += bess_charge * bess_efficiency
            bess_charge_total_kwh += bess_charge
            pv_curtailed_kwh += max(0, pv_to_bess - bess_charge)
        else:
            pv_curtailed_kwh += pv_to_bess

        # 3. Usar BESS para complementar EVs si falta demanda
        ev_deficit: float = float(max(0, ev_demand - pv_to_ev))
        bess_to_ev_max: float = float(bess_soc - bess_capacity_kwh * bess_min_soc)
        bess_to_ev: float = float(min(ev_deficit, bess_power_kw, bess_to_ev_max))

        if bess_to_ev > 0:
            bess_soc -= bess_to_ev
            bess_discharge_total_kwh += bess_to_ev
            ev_deficit -= bess_to_ev

        # 4. Importar grid para cubrir déficit
        grid_import = max(0, ev_deficit)
        grid_import_total_kwh += grid_import

        pv_used_direct_kwh += pv_to_ev
        ev_demand_total_kwh += ev_demand

        # Guardar timestep
        bess_soc_percent: float = (bess_soc / bess_capacity_kwh) * 100
        results["timesteps"].append({
            "hour": hour % 24,
            "day": hour // 24 + 1,
            "pv_generation_kw": float(pv_gen),
            "ev_demand_kw": float(ev_demand),
            "grid_import_kw": float(grid_import),
            "bess_soc_kwh": float(bess_soc),
            "bess_soc_percent": bess_soc_percent,
            "pv_to_ev_kw": float(pv_to_ev),
            "pv_to_bess_kw": float(pv_to_bess),
            "bess_to_ev_kw": float(bess_to_ev),
        })

    # Resumen
    co2_emissions = grid_import_total_kwh * grid_ci  # kg CO₂
    pv_utilization = (pv_used_direct_kwh / np.sum(pv_power)) * 100 if np.sum(pv_power) > 0 else 0

    summary = {
        "total_timesteps": 8760,
        "grid_import_total_kwh": round(grid_import_total_kwh, 2),
        "grid_import_avg_kw": round(grid_import_total_kwh / 8760, 2),
        "co2_emissions_kg": round(co2_emissions, 2),
        "ev_demand_total_kwh": round(ev_demand_total_kwh, 2),
        "pv_generation_total_kwh": round(np.sum(pv_power), 2),
        "pv_used_direct_kwh": round(pv_used_direct_kwh, 2),
        "pv_utilization_percent": round(pv_utilization, 2),
        "pv_curtailed_kwh": round(pv_curtailed_kwh, 2),
        "bess_charge_total_kwh": round(bess_charge_total_kwh, 2),
        "bess_discharge_total_kwh": round(bess_discharge_total_kwh, 2),
        "grid_carbon_intensity_kg_per_kwh": grid_ci,
    }

    results["summary"] = summary

    logger.info("\n" + "=" * 80)
    logger.info("RESULTADOS BASELINE (SIN CONTROL INTELIGENTE)")
    logger.info("=" * 80)
    logger.info(f"\n📊 ENERGÍA:")
    logger.info(f"   Total demanda EV:        {summary['ev_demand_total_kwh']:>12.2f} kWh")
    logger.info(f"   Total PV generado:       {summary['pv_generation_total_kwh']:>12.2f} kWh")
    logger.info(f"   PV usado directo:        {summary['pv_used_direct_kwh']:>12.2f} kWh ({summary['pv_utilization_percent']:.1f}%)")
    logger.info(f"   PV descartado:           {summary['pv_curtailed_kwh']:>12.2f} kWh")
    logger.info(f"   Importación grid:        {summary['grid_import_total_kwh']:>12.2f} kWh")
    logger.info(f"   BESS cargado:            {summary['bess_charge_total_kwh']:>12.2f} kWh")
    logger.info(f"   BESS descargado:         {summary['bess_discharge_total_kwh']:>12.2f} kWh")

    logger.info(f"\n🌍 EMISIONES:")
    logger.info(f"   Intensidad carbono:      {summary['grid_carbon_intensity_kg_per_kwh']:.4f} kg CO₂/kWh")
    logger.info(f"   Emisiones totales:       {summary['co2_emissions_kg']:>12.2f} kg CO₂")
    logger.info(f"   Promedio diario:         {summary['co2_emissions_kg']/365:>12.2f} kg CO₂/día")

    logger.info(f"\n⚡ POTENCIA:")
    logger.info(f"   Importación promedio:    {summary['grid_import_avg_kw']:>12.2f} kW")
    logger.info(f"   Demanda pico (24h):      {np.max(hourly_demand):>12.2f} kW")

    # Guardar resultados
    baseline_file = output_dir / "baseline_summary.json"
    with open(baseline_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n✓ Resultados guardados en {baseline_file}")
    logger.info("\n" + "=" * 80)
    logger.info("BASELINE COMPLETADO - Lista para comparación con agentes RL")
    logger.info("=" * 80)

    return results


if __name__ == "__main__":
    try:
        calculate_baseline()
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        exit(1)
