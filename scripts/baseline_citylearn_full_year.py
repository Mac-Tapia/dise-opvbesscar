#!/usr/bin/env python3
"""
BASELINE FULL YEAR SIMULATION - Iquitos EV Mall
================================================
Simulates 8,760 hours (1 year) without intelligent control.
All EV chargers are always ON, no optimization.

Duration: ~30-45 minutes
Output: Detailed hourly metrics for comparison with RL agents

Author: OE3 Pipeline
Date: 2026-01-29
"""

import sys
import os
import json
import logging
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / 'baseline_full_year_simulation.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

def load_data():
    """Load all required data for baseline simulation."""
    logger.info("=" * 80)
    logger.info("CARGANDO DATOS PARA BASELINE FULL YEAR (8,760 horas)")
    logger.info("=" * 80)

    data = {}

    # 1. Solar PV timeseries
    solar_path = project_root / "data" / "processed" / "citylearn" / "iquitos_ev_mall" / "weather.csv"
    if solar_path.exists():
        solar_df = pd.read_csv(solar_path)
        # Get direct_solar_irradiance or similar column
        if 'direct_solar_irradiance' in solar_df.columns:
            data['solar_irradiance'] = solar_df['direct_solar_irradiance'].values
        elif 'diffuse_solar_irradiance' in solar_df.columns:
            data['solar_irradiance'] = solar_df['diffuse_solar_irradiance'].values
        else:
            # Use first numeric column after time columns
            numeric_cols = solar_df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                data['solar_irradiance'] = solar_df[numeric_cols[0]].values
            else:
                data['solar_irradiance'] = np.zeros(8760)
        logger.info(f"[OK] Solar irradiance loaded: {len(data['solar_irradiance'])} hours")
    else:
        logger.warning(f"Solar file not found: {solar_path}")
        data['solar_irradiance'] = np.zeros(8760)

    # 2. PV generation from interim
    pv_path = project_root / "data" / "interim" / "oe2" / "solar" / "pv_generation_timeseries.csv"
    if pv_path.exists():
        pv_df = pd.read_csv(pv_path)
        # Find the generation column
        gen_cols = [c for c in pv_df.columns if 'gen' in c.lower() or 'power' in c.lower() or 'kw' in c.lower()]
        if gen_cols:
            data['pv_generation'] = pv_df[gen_cols[0]].values
        else:
            # Use last numeric column
            numeric_cols = pv_df.select_dtypes(include=[np.number]).columns
            data['pv_generation'] = pv_df[numeric_cols[-1]].values if len(numeric_cols) > 0 else np.zeros(8760)
        logger.info(f"[OK] PV generation loaded: {len(data['pv_generation'])} hours, avg={np.mean(data['pv_generation']):.2f} kW")
    else:
        # Estimate from irradiance * capacity
        pv_capacity = 4162  # kWp
        data['pv_generation'] = data['solar_irradiance'] * pv_capacity / 1000 * 0.85  # 85% efficiency
        logger.info(f"[OK] PV generation estimated from irradiance: avg={np.mean(data['pv_generation']):.2f} kW")

    # 3. EV charger demand profile (full year 8760 hourly data)
    charger_path = project_root / "data" / "interim" / "oe2" / "chargers" / "perfil_horario_carga.csv"
    if charger_path.exists():
        charger_df = pd.read_csv(charger_path)
        # Use total_demand_kw column if exists (pre-computed total)
        if 'total_demand_kw' in charger_df.columns:
            ev_raw = charger_df['total_demand_kw'].values
        else:
            # Sum only toma_*_kw columns (individual charger columns)
            toma_cols = [c for c in charger_df.columns if c.startswith('toma_') and c.endswith('_kw')]
            if toma_cols:
                ev_raw = charger_df[toma_cols].sum(axis=1).values
            else:
                ev_raw = np.full(8760, 96.33)  # Default

        # Resample if needed (data might be 30-min intervals = 17520 rows)
        if len(ev_raw) == 17520:  # 30-min data for 1 year
            # Average every 2 rows to get hourly data
            ev_raw = ev_raw.reshape(-1, 2).mean(axis=1)
            logger.info(f"[OK] EV demand resampled from 30-min to hourly: {len(ev_raw)} rows")

        data['ev_demand'] = ev_raw
        logger.info(f"[OK] EV demand loaded: {len(data['ev_demand'])} rows")
        logger.info(f"     Avg={np.mean(data['ev_demand']):.2f} kW, Peak={np.max(data['ev_demand']):.2f} kW")
    else:
        data['ev_demand'] = np.full(8760, 96.33)  # Default avg from OE2
        logger.info(f"[OK] EV demand using default: 96.33 kW constant")

    # 4. Mall building load
    building_path = project_root / "data" / "processed" / "citylearn" / "iquitos_ev_mall" / "Building_1.csv"
    if building_path.exists():
        building_df = pd.read_csv(building_path)
        if 'Equipment Electric Power [kWh]' in building_df.columns:
            data['mall_load'] = building_df['Equipment Electric Power [kWh]'].values
        elif 'non_shiftable_load' in building_df.columns:
            data['mall_load'] = building_df['non_shiftable_load'].values
        else:
            # Use first numeric column that looks like load
            load_cols = [c for c in building_df.columns if 'load' in c.lower() or 'power' in c.lower() or 'kwh' in c.lower()]
            if load_cols:
                data['mall_load'] = building_df[load_cols[0]].values
            else:
                data['mall_load'] = np.full(8760, 1411.88)  # Default avg
        logger.info(f"[OK] Mall load loaded: {len(data['mall_load'])} hours, avg={np.mean(data['mall_load']):.2f} kW")
    else:
        data['mall_load'] = np.full(8760, 1411.88)
        logger.info(f"[OK] Mall load using default: 1411.88 kW")

    # 5. BESS configuration
    bess_path = project_root / "data" / "interim" / "oe2" / "bess" / "bess_config.json"
    if bess_path.exists():
        with open(bess_path) as f:
            bess_config = json.load(f)
        data['bess_capacity'] = bess_config.get('capacity_kwh', 4520)
        data['bess_power'] = bess_config.get('power_kw', 2712)
    else:
        data['bess_capacity'] = 4520
        data['bess_power'] = 2712
    logger.info(f"[OK] BESS config: {data['bess_capacity']} kWh / {data['bess_power']} kW")

    # Ensure all arrays are 8760 length
    for key in ['solar_irradiance', 'pv_generation', 'ev_demand', 'mall_load']:
        if key in data and len(data[key]) != 8760:
            if len(data[key]) > 8760:
                data[key] = data[key][:8760]
            else:
                # Repeat to fill
                repeats = 8760 // len(data[key]) + 1
                data[key] = np.tile(data[key], repeats)[:8760]
            logger.info(f"  Adjusted {key} to 8760 hours")

    return data


def simulate_baseline(data: dict, progress_interval: int = 500) -> dict:
    """
    Simulate full year baseline (uncontrolled scenario).

    In baseline:
    - All EV chargers are always ON when demand exists
    - BESS operates in simple mode (charge when PV excess, discharge when deficit)
    - No intelligent control or optimization

    Returns dict with hourly results.
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("INICIANDO SIMULACIÓN BASELINE - 8,760 HORAS (1 AÑO)")
    logger.info("=" * 80)
    logger.info("Escenario: Sin control inteligente - todas las cargas EV activas")
    logger.info("")

    n_hours = 8760

    # Get data arrays
    pv_gen = data['pv_generation']
    ev_demand = data['ev_demand']
    mall_load = data['mall_load']
    bess_capacity = data['bess_capacity']
    bess_power = data['bess_power']

    # BESS parameters
    bess_soc_min = 0.10  # 10%
    bess_soc_max = 0.95  # 95%
    bess_efficiency = 0.95

    # Initialize BESS at 50% SOC
    bess_soc = bess_capacity * 0.50

    # Results arrays
    results = {
        'hour': np.arange(n_hours),
        'pv_generation': np.zeros(n_hours),
        'ev_demand': np.zeros(n_hours),
        'mall_load': np.zeros(n_hours),
        'total_demand': np.zeros(n_hours),
        'pv_to_load': np.zeros(n_hours),
        'pv_to_bess': np.zeros(n_hours),
        'pv_curtailed': np.zeros(n_hours),
        'bess_charge': np.zeros(n_hours),
        'bess_discharge': np.zeros(n_hours),
        'bess_soc': np.zeros(n_hours),
        'grid_import': np.zeros(n_hours),
        'grid_export': np.zeros(n_hours),
        'co2_emissions': np.zeros(n_hours),
    }

    # Carbon intensity for Iquitos (thermal grid)
    carbon_intensity = 0.4521  # kg CO2/kWh

    start_time = time.time()
    last_progress = time.time()

    for h in range(n_hours):
        # Get current values
        pv = pv_gen[h]
        ev = ev_demand[h]
        mall = mall_load[h]
        total_demand = ev + mall

        # Store basic values
        results['pv_generation'][h] = pv
        results['ev_demand'][h] = ev
        results['mall_load'][h] = mall
        results['total_demand'][h] = total_demand

        # Energy balance
        pv_available = pv
        demand_remaining = total_demand

        # Step 1: Use PV directly for load
        pv_to_load = min(pv_available, demand_remaining)
        results['pv_to_load'][h] = pv_to_load
        pv_available -= pv_to_load
        demand_remaining -= pv_to_load

        # Step 2: Excess PV to BESS
        if pv_available > 0 and bess_soc < bess_capacity * bess_soc_max:
            max_charge = min(
                pv_available,
                bess_power,
                (bess_capacity * bess_soc_max - bess_soc) / bess_efficiency
            )
            bess_charge = max_charge * bess_efficiency
            results['pv_to_bess'][h] = max_charge
            results['bess_charge'][h] = bess_charge
            bess_soc += bess_charge
            pv_available -= max_charge

        # Step 3: Remaining demand from BESS
        if demand_remaining > 0 and bess_soc > bess_capacity * bess_soc_min:
            max_discharge = min(
                demand_remaining,
                bess_power,
                (bess_soc - bess_capacity * bess_soc_min) * bess_efficiency
            )
            bess_discharge = max_discharge
            results['bess_discharge'][h] = bess_discharge
            bess_soc -= bess_discharge / bess_efficiency
            demand_remaining -= bess_discharge

        # Step 4: Grid import for remaining demand
        if demand_remaining > 0:
            results['grid_import'][h] = demand_remaining
            results['co2_emissions'][h] = demand_remaining * carbon_intensity

        # Step 5: Curtail excess PV
        if pv_available > 0:
            results['pv_curtailed'][h] = pv_available

        # Store BESS SOC
        results['bess_soc'][h] = bess_soc

        # Progress reporting
        if (h + 1) % progress_interval == 0 or h == n_hours - 1:
            elapsed = time.time() - start_time
            progress = (h + 1) / n_hours * 100
            eta = elapsed / (h + 1) * (n_hours - h - 1)

            # Calculate cumulative stats
            cum_pv = np.sum(results['pv_generation'][:h+1])
            cum_grid = np.sum(results['grid_import'][:h+1])
            cum_co2 = np.sum(results['co2_emissions'][:h+1])
            cum_curtailed = np.sum(results['pv_curtailed'][:h+1])

            logger.info(
                f"[BASELINE] hora {h+1:>5}/{n_hours} ({progress:5.1f}%) | "
                f"PV={cum_pv/1000:,.0f} MWh | Grid={cum_grid:,.0f} kWh | "
                f"CO2={cum_co2:,.0f} kg | Curtailed={cum_curtailed/1000:,.0f} MWh | "
                f"ETA={eta/60:.1f} min"
            )

    total_time = time.time() - start_time
    logger.info("")
    logger.info(f"[OK] Simulation completed in {total_time/60:.2f} minutes")

    return results


def calculate_summary(results: dict) -> dict:
    """Calculate summary statistics from hourly results."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("CALCULANDO RESUMEN ESTADÍSTICO")
    logger.info("=" * 80)

    summary = {
        'simulation_type': 'baseline_uncontrolled',
        'timestamp': datetime.now().isoformat(),
        'duration_hours': 8760,
        'energy': {
            'pv_generation_kwh': float(np.sum(results['pv_generation'])),
            'ev_demand_kwh': float(np.sum(results['ev_demand'])),
            'mall_load_kwh': float(np.sum(results['mall_load'])),
            'total_demand_kwh': float(np.sum(results['total_demand'])),
            'pv_to_load_kwh': float(np.sum(results['pv_to_load'])),
            'pv_to_bess_kwh': float(np.sum(results['pv_to_bess'])),
            'pv_curtailed_kwh': float(np.sum(results['pv_curtailed'])),
            'grid_import_kwh': float(np.sum(results['grid_import'])),
            'bess_charged_kwh': float(np.sum(results['bess_charge'])),
            'bess_discharged_kwh': float(np.sum(results['bess_discharge'])),
        },
        'emissions': {
            'total_co2_kg': float(np.sum(results['co2_emissions'])),
            'daily_avg_co2_kg': float(np.sum(results['co2_emissions']) / 365),
            'carbon_intensity_kg_per_kwh': 0.4521,
        },
        'efficiency': {
            'pv_utilization_pct': float(
                (np.sum(results['pv_to_load']) + np.sum(results['pv_to_bess'])) /
                max(np.sum(results['pv_generation']), 1) * 100
            ),
            'pv_curtailed_pct': float(
                np.sum(results['pv_curtailed']) /
                max(np.sum(results['pv_generation']), 1) * 100
            ),
            'grid_dependency_pct': float(
                np.sum(results['grid_import']) /
                max(np.sum(results['total_demand']), 1) * 100
            ),
            'self_consumption_pct': float(
                (np.sum(results['pv_to_load']) + np.sum(results['bess_discharge'])) /
                max(np.sum(results['total_demand']), 1) * 100
            ),
        },
        'power': {
            'pv_avg_kw': float(np.mean(results['pv_generation'])),
            'pv_max_kw': float(np.max(results['pv_generation'])),
            'demand_avg_kw': float(np.mean(results['total_demand'])),
            'demand_max_kw': float(np.max(results['total_demand'])),
            'grid_import_avg_kw': float(np.mean(results['grid_import'])),
            'grid_import_max_kw': float(np.max(results['grid_import'])),
        },
        'bess': {
            'final_soc_kwh': float(results['bess_soc'][-1]),
            'avg_soc_kwh': float(np.mean(results['bess_soc'])),
            'cycles_approx': float(np.sum(results['bess_charge']) / 4520),  # Capacity
        }
    }

    return summary


def print_summary(summary: dict):
    """Print formatted summary to log."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("RESULTADOS BASELINE (SIN CONTROL INTELIGENTE) - 1 AÑO COMPLETO")
    logger.info("=" * 80)

    e = summary['energy']
    em = summary['emissions']
    ef = summary['efficiency']
    p = summary['power']

    logger.info("")
    logger.info("[ENERGY] ENERGIA (kWh/year):")
    logger.info(f"   PV Generado:           {e['pv_generation_kwh']:>15,.0f} kWh")
    logger.info(f"   Demanda EV:            {e['ev_demand_kwh']:>15,.0f} kWh")
    logger.info(f"   Demanda Mall:          {e['mall_load_kwh']:>15,.0f} kWh")
    logger.info(f"   Demanda Total:         {e['total_demand_kwh']:>15,.0f} kWh")
    logger.info(f"   PV → Cargas Directo:   {e['pv_to_load_kwh']:>15,.0f} kWh")
    logger.info(f"   PV → BESS:             {e['pv_to_bess_kwh']:>15,.0f} kWh")
    logger.info(f"   PV Descartado:         {e['pv_curtailed_kwh']:>15,.0f} kWh ({ef['pv_curtailed_pct']:.1f}%)")
    logger.info(f"   Grid Import:           {e['grid_import_kwh']:>15,.0f} kWh")

    logger.info("")
    logger.info("[EMISSIONS] EMISIONES CO2:")
    logger.info(f"   Total Anual:           {em['total_co2_kg']:>15,.0f} kg CO₂")
    logger.info(f"   Promedio Diario:       {em['daily_avg_co2_kg']:>15,.1f} kg CO₂/día")
    logger.info(f"   Intensidad Carbono:    {em['carbon_intensity_kg_per_kwh']:>15.4f} kg CO₂/kWh")

    logger.info("")
    logger.info("[EFFICIENCY] EFICIENCIA:")
    logger.info(f"   Utilización PV:        {ef['pv_utilization_pct']:>15.1f}%")
    logger.info(f"   PV Descartado:         {ef['pv_curtailed_pct']:>15.1f}%")
    logger.info(f"   Dependencia Grid:      {ef['grid_dependency_pct']:>15.1f}%")
    logger.info(f"   Auto-consumo:          {ef['self_consumption_pct']:>15.1f}%")

    logger.info("")
    logger.info("[POWER] POTENCIA (kW):")
    logger.info(f"   PV Promedio:           {p['pv_avg_kw']:>15.2f} kW")
    logger.info(f"   PV Máximo:             {p['pv_max_kw']:>15.2f} kW")
    logger.info(f"   Demanda Promedio:      {p['demand_avg_kw']:>15.2f} kW")
    logger.info(f"   Demanda Máximo:        {p['demand_max_kw']:>15.2f} kW")
    logger.info(f"   Grid Import Promedio:  {p['grid_import_avg_kw']:>15.2f} kW")

    logger.info("")
    logger.info("=" * 80)


def save_results(results: dict, summary: dict, output_dir: Path):
    """Save results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save summary JSON
    summary_path = output_dir / "baseline_full_year_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"[OK] Summary saved: {summary_path}")

    # Save hourly results CSV
    results_df = pd.DataFrame(results)
    results_path = output_dir / "baseline_full_year_hourly.csv"
    results_df.to_csv(results_path, index=False)
    logger.info(f"[OK] Hourly results saved: {results_path}")

    return summary_path, results_path


def main():
    """Main entry point."""
    logger.info("")
    logger.info("+" + "=" * 78 + "+")
    logger.info("|" + " BASELINE FULL YEAR SIMULATION - IQUITOS EV MALL ".center(78) + "|")
    logger.info("|" + " Sin Control Inteligente - 8,760 horas (1 year) ".center(78) + "|")
    logger.info("+" + "=" * 78 + "+")
    logger.info("")

    start_time = time.time()

    try:
        # Load data
        data = load_data()

        # Run simulation
        results = simulate_baseline(data, progress_interval=500)

        # Calculate summary
        summary = calculate_summary(results)

        # Print summary
        print_summary(summary)

        # Save results
        output_dir = project_root / "outputs" / "oe3"
        save_results(results, summary, output_dir)

        total_time = time.time() - start_time

        logger.info("")
        logger.info("+" + "=" * 78 + "+")
        logger.info("|" + f" BASELINE COMPLETED IN {total_time/60:.2f} MINUTES ".center(78) + "|")
        logger.info("|" + " Ready for comparison with RL agents ".center(78) + "|")
        logger.info("+" + "=" * 78 + "+")

        return 0

    except Exception as e:
        logger.error(f"Error in simulation: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
