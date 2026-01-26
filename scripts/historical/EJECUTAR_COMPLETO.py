#!/usr/bin/env python
"""
SCRIPT MAESTRO - EJECUTAR TODO EN ORDEN:
1. Transformar demanda mall (15min → 1hora)
2. Cargar OE2 (Solar, Chargers, BESS, Mall)
3. Construir Dataset
4. Calcular Baseline
5. Entrenar Agentes (SAC → PPO → A2C)
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def print_banner(text):
    """Print formatted banner."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

# ==============================================================================
# FASE 0: TRANSFORMAR DEMANDA MALL (15MIN → 1HORA)
# ==============================================================================

def phase_0_transform_mall():
    """Transform 15-minute mall demand to 1-hour resolution."""
    print_banner("FASE 0: TRANSFORMAR DEMANDA MALL (15MIN → 1HORA)")

    input_file = Path("data/interim/oe2/demandamallkwh/demandamallkwh.csv")
    output_dir = Path("data/interim/oe2/demandamallkwh")
    output_file = output_dir / "demanda_mall_horaria_anual.csv"

    if not input_file.exists():
        logger.error(f"❌ Archivo no encontrado: {input_file}")
        return False

    try:
        # Load 15-minute data (separador ';')
        df = pd.read_csv(input_file, sep=';', header=None, names=['datetime', 'kWh'])
        logger.info(f"✓ Archivo 15min cargado: {len(df)} registros")

        # Parse datetime and resample to hourly
        df['datetime'] = pd.to_datetime(df['datetime'], format='%d/%m/%Y %H:%M')
        df_hourly = df.set_index('datetime')['kWh'].resample('h').mean()
        # Ensure 8760 hours (1 year)
        if len(df_hourly) < 8760:
            df_hourly = df_hourly.iloc[:8760]
        elif len(df_hourly) > 8760:
            df_hourly = df_hourly.iloc[:8760]

        # Save (single column: kW)
        pd.DataFrame({'kW': df_hourly.values}).to_csv(output_file, index=False)
        logger.info(f"✓ Demanda mall transformada: {len(df_hourly)} registros")
        logger.info(f"✓ Archivo guardado: {output_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Error transformando demanda: {e}")
        return False

# ==============================================================================
# FASE 1: CARGAR OE2
# ==============================================================================

def phase_1_load_oe2():
    """Load OE2 data (Solar, Chargers, BESS, Mall)."""
    print_banner("FASE 1: CARGAR OE2 (SOLAR, CHARGERS, BESS, MALL)")

    data = {}

    # Solar
    solar_file = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
    if solar_file.exists():
        solar = pd.read_csv(solar_file, index_col=0)
        data['solar'] = solar.iloc[:, 0].values if isinstance(solar, pd.DataFrame) else solar.values
        logger.info(f"✓ Solar: {len(data['solar'])} horas, min={data['solar'].min():.1f}, max={data['solar'].max():.1f}, mean={data['solar'].mean():.1f}")
    else:
        logger.error(f"❌ Solar no encontrado: {solar_file}")
        return None

    # Chargers (128 perfiles individuales)
    chargers_dir = Path("data/interim/oe2/chargers")
    chargers_csv_files = list(chargers_dir.glob("charger_*.csv"))

    if len(chargers_csv_files) == 0:
        logger.error(f"❌ No chargers encontrados en {chargers_dir}")
        return None

    chargers_data = []
    for i, csv_file in enumerate(sorted(chargers_csv_files)[:128]):
        df = pd.read_csv(csv_file, index_col=0)
        charger_profile = df.iloc[:, 0].values if isinstance(df, pd.DataFrame) else df.values
        chargers_data.append(charger_profile[:8760])

    data['chargers'] = np.array(chargers_data)
    logger.info(f"✓ Chargers: {data['chargers'].shape[0]} cargadores, {data['chargers'].shape[1]} horas")

    # BESS config
    bess_file = Path("data/interim/oe2/bess/bess_config.json")
    if bess_file.exists():
        with open(bess_file) as f:
            bess_cfg = json.load(f)
            data['bess'] = bess_cfg
            logger.info(f"✓ BESS: {bess_cfg['capacity']} kWh, {bess_cfg['power']} kW, η={bess_cfg['efficiency']}%")

    # Mall demand (1-hour)
    mall_file = Path("data/interim/oe2/demandamallkwh/demanda_mall_horaria_anual.csv")
    if mall_file.exists():
        mall = pd.read_csv(mall_file, index_col=0)
        data['mall'] = mall.iloc[:, 0].values if isinstance(mall, pd.DataFrame) else mall.values
        logger.info(f"✓ Mall: {len(data['mall'])} horas, min={data['mall'].min():.1f}, max={data['mall'].max():.1f}, mean={data['mall'].mean():.1f}")

    # Summary
    logger.info(f"\n✓ OE2 COMPLETO:")
    solar_annual = data['solar'].sum()
    mall_annual = data['mall'].sum() if 'mall' in data else 0
    chargers_annual = data['chargers'].sum()
    logger.info(f"   Solar generación: {solar_annual:,.0f} kWh/año")
    logger.info(f"   Chargers demanda: {chargers_annual:,.0f} kWh/año")
    logger.info(f"   Mall demanda: {mall_annual:,.0f} kWh/año")
    logger.info(f"   BESS: {data['bess']['capacity']} kWh")

    return data

# ==============================================================================
# FASE 2: CONSTRUIR DATASET
# ==============================================================================

def phase_2_build_dataset(oe2_data):
    """Build training dataset from OE2 data."""
    print_banner("FASE 2: CONSTRUIR DATASET")

    if oe2_data is None:
        return False

    try:
        solar = oe2_data['solar']
        chargers = oe2_data['chargers']
        mall = oe2_data['mall']

        n_hours = 8760
        n_chargers = chargers.shape[0]

        # Build observations
        obs = []
        for h in range(n_hours):
            hour_of_day = h % 24
            day_of_year = h // 24
            month = (h // (24 * 30)) % 12

            obs_h = {
                'solar': solar[h],
                'charger_demand': chargers[:, h],
                'mall': mall[h],
                'hour_of_day': hour_of_day,
                'day_of_year': day_of_year,
                'month': month,
            }
            obs.append(obs_h)

        logger.info(f"✓ Dataset construido: {n_hours} horas × {n_chargers} chargers")

        # Save dataset
        output_dir = Path("data/processed/dataset")
        output_dir.mkdir(parents=True, exist_ok=True)

        np.save(output_dir / "solar.npy", solar)
        np.save(output_dir / "chargers.npy", chargers)
        np.save(output_dir / "mall.npy", mall)

        logger.info(f"✓ Dataset guardado en {output_dir}")

        return True
    except Exception as e:
        logger.error(f"❌ Error construyendo dataset: {e}")
        return False

# ==============================================================================
# FASE 3: CALCULAR BASELINE
# ==============================================================================

def phase_3_baseline(oe2_data):
    """Calculate baseline (no control)."""
    print_banner("FASE 3: CALCULAR BASELINE (SIN CONTROL)")

    if oe2_data is None:
        return None

    try:
        solar = oe2_data['solar']
        chargers = oe2_data['chargers']
        mall = oe2_data['mall']

        n_hours = len(solar)

        # Baseline: all demand from grid
        chargers_demand = chargers.sum(axis=0)
        total_demand = chargers_demand + mall

        # Grid import = demand - solar (solar can't meet all demand)
        grid_import = np.maximum(0, total_demand - solar)

        # Metrics
        solar_annual = solar.sum()
        chargers_annual = chargers_demand.sum()
        mall_annual = mall.sum()
        grid_import_total = grid_import.sum()

        # CO2 (0.4521 kg CO2/kWh, diesel termoelectric)
        co2_kg = grid_import_total * 0.4521
        co2_t = co2_kg / 1000

        # Cost (0.20 USD/kWh)
        cost = grid_import_total * 0.20

        # Peak demand
        peak_demand = total_demand.max()
        avg_demand = total_demand.mean()

        # Solar utilization
        solar_utilized = solar.sum() - np.maximum(0, solar - total_demand).sum()
        solar_util_pct = (solar_utilized / solar_annual * 100) if solar_annual > 0 else 0

        baseline = {
            'solar_annual': solar_annual,
            'chargers_annual': chargers_annual,
            'mall_annual': mall_annual,
            'grid_import_total': grid_import_total,
            'co2_t': co2_t,
            'cost': cost,
            'peak_demand': peak_demand,
            'avg_demand': avg_demand,
            'solar_utilization_pct': solar_util_pct,
        }

        logger.info(f"\n✓ BASELINE KPIs:")
        logger.info(f"   Solar generación: {baseline['solar_annual']:,.0f} kWh/año")
        logger.info(f"   Chargers demanda: {baseline['chargers_annual']:,.0f} kWh/año")
        logger.info(f"   Mall demanda: {baseline['mall_annual']:,.0f} kWh/año")
        logger.info(f"   Grid import: {baseline['grid_import_total']:,.0f} kWh/año")
        logger.info(f"   CO₂ emissions: {baseline['co2_t']:.1f} t/año")
        logger.info(f"   Costo: ${baseline['cost']:,.0f}/año")
        logger.info(f"   Peak demand: {baseline['peak_demand']:.1f} kW")
        logger.info(f"   Solar utilization: {baseline['solar_utilization_pct']:.1f}%")

        # Save baseline
        output_dir = Path("data/processed/training")
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "baseline.json", "w") as f:
            json.dump(baseline, f, indent=2)

        logger.info(f"\n✓ Baseline guardado: {output_dir / 'baseline.json'}")

        return baseline
    except Exception as e:
        logger.error(f"❌ Error calculando baseline: {e}")
        return None

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Execute full pipeline."""
    print_banner("INICIO: PIPELINE COMPLETO (DATASET + BASELINE + ENTRENAMIENTO)")

    # Phase 0: Transform
    if not phase_0_transform_mall():
        logger.error("❌ Fase 0 falló")
        return

    # Phase 1: Load OE2
    oe2_data = phase_1_load_oe2()
    if oe2_data is None:
        logger.error("❌ Fase 1 falló")
        return

    # Phase 2: Build Dataset
    if not phase_2_build_dataset(oe2_data):
        logger.error("❌ Fase 2 falló")
        return

    # Phase 3: Baseline
    baseline = phase_3_baseline(oe2_data)
    if baseline is None:
        logger.error("❌ Fase 3 falló")
        return

    print_banner("✅ PIPELINE COMPLETADO EXITOSAMENTE")
    logger.info("Dataset construido ✓")
    logger.info("Baseline calculado ✓")
    logger.info(f"CO₂ baseline: {baseline['co2_t']:.1f} t/año")
    logger.info(f"Costo baseline: ${baseline['cost']:,.0f}/año")
    logger.info(f"Grid import baseline: {baseline['grid_import_total']:,.0f} kWh/año")
    logger.info("\nListo para entrenar agentes RL")

if __name__ == "__main__":
    main()
