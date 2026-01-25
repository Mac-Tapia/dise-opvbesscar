"""Baseline: Cálculo simple de referencia sin control para comparación."""

import sys
import json
from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.iquitos_citylearn.config import load_config, load_paths

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def main():
    logger.info("\n" + "=" * 80)
    logger.info("BASELINE: Simulación de referencia (SIN CONTROL)")
    logger.info("=" * 80)

    cfg = load_config()
    rp = load_paths(cfg)

    logger.info("\n✓ Cargando dataset construido...")
    import pandas as pd

    # Cargar datos del dataset
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"

    if not dataset_dir.exists():
        logger.error(f"❌ Dataset no encontrado en {dataset_dir}")
        return

    # Buscar archivos charger_simulation_*.csv (están en buildings/Mall_Iquitos/)
    charger_files = list((dataset_dir / "buildings" / "Mall_Iquitos").glob("charger_simulation_*.csv"))

    # Fallback: si no están ahí, buscar en raíz
    if not charger_files:
        charger_files = list(dataset_dir.glob("charger_*.csv"))

    if not charger_files:
        logger.error(f"❌ No se encontraron archivos charger_*.csv en {dataset_dir}")
        return

    logger.info(f"✓ Encontrados {len(charger_files)} chargers en dataset")

    # Cargar y sumar demanda de todos los chargers
    total_energy_kwh = 0.0

    for charger_file in sorted(charger_files):
        try:
            df = pd.read_csv(charger_file)
            # Suma de energía de este charger (en kWh)
            if 'demand_kw' in df.columns:
                charger_energy = df['demand_kw'].sum()  # kW × 1h timestep = kWh
            elif 'power_kw' in df.columns:
                charger_energy = df['power_kw'].sum()
            else:
                # Tomar primera columna numérica disponible
                charger_energy = df.iloc[:, 0].sum()

            total_energy_kwh += charger_energy
        except Exception as e:
            logger.warning(f"Advertencia al leer {charger_file.name}: {e}")
            continue

    # Parámetros de grid
    carbon_intensity = cfg['oe3']['grid']['carbon_intensity_kg_per_kwh']
    tariff = cfg['oe3']['grid']['tariff_usd_per_kwh']

    # Cálculos basados en dataset real
    co2_kg = total_energy_kwh * carbon_intensity
    cost_usd = total_energy_kwh * tariff
    _ = total_energy_kwh / 8760  # Potencia promedio

    metrics = {
        "scenario": "baseline_no_control",
        "source": "dataset_constructed",
        "num_chargers": len(charger_files),
        "timesteps": 8760,
        "energy_kwh": total_energy_kwh,
        "co2_total_kg": co2_kg,
        "cost_total_usd": cost_usd,
        "grid_import_kwh": total_energy_kwh,
        "carbon_intensity_kg_per_kwh": carbon_intensity,
        "tariff_usd_per_kwh": tariff,
    }

    output_dir = rp.oe3_simulations_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_file = output_dir / "baseline_reference.json"
    baseline_file.write_text(json.dumps(metrics, indent=2))

    logger.info("\n" + "=" * 80)
    logger.info("✅ BASELINE COMPLETADO")
    logger.info("=" * 80)
    logger.info(f"\n📊 REFERENCIA (SIN CONTROL):")
    logger.info(f"   Chargers encontrados: {len(charger_files)} (desde dataset)")
    logger.info(f"   Energía/año: {total_energy_kwh:.2f} kWh (suma real de demanda)")
    logger.info(f"   CO2 anual: {co2_kg:.2f} kg")
    logger.info(f"   Costo anual: ${cost_usd:.2f}")
    logger.info(f"   Grid import: {total_energy_kwh:.2f} kWh")
    logger.info(f"\n💾 Guardado: {baseline_file}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
