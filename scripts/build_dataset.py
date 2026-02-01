"""
Build Dataset Script
Construye el dataset completo desde artefactos OE2:
- Solar generation: PVGIS/pvlib (8,760 hourly values)
- Chargers: 128 sockets (32 chargers × 4 sockets)
- BESS: 4,520 kWh / 2,712 kW (OE2 Real)
"""

import sys
import json
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.iquitos_citylearn.config import load_config
from src.iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 80)
    logger.info("📊 CONSTRUCCIÓN DE DATASET DESDE ARTEFACTOS OE2")
    logger.info("=" * 80)

    # Cargar configuración
    logger.info("\n✓ Cargando configuración...")
    config = load_config("configs/default.yaml")
    from src.iquitos_citylearn.config import load_paths
    rp = load_paths(config)

    # Verificar artefactos OE2 existen
    logger.info("\n✓ Verificando artefactos OE2...")

    solar_file = rp.interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
    chargers_file = rp.interim_dir / "oe2" / "chargers" / "individual_chargers.json"
    bess_config = rp.interim_dir / "oe2" / "bess" / "bess_config.json"

    if not solar_file.exists():
        logger.error(f"❌ Solar timeseries no encontrado: {solar_file}")
        return 1
    logger.info(f"   ✓ Solar: {solar_file.name} ({solar_file.stat().st_size:,} bytes)")

    if not chargers_file.exists():
        logger.error(f"❌ Chargers config no encontrado: {chargers_file}")
        return 1
    logger.info(f"   ✓ Chargers: {chargers_file.name} ({chargers_file.stat().st_size:,} bytes)")

    if not bess_config.exists():
        logger.error(f"❌ BESS config no encontrado: {bess_config}")
        return 1
    logger.info(f"   ✓ BESS: {bess_config.name} ({bess_config.stat().st_size:,} bytes)")

    # Cargar specs OE2
    logger.info("\n✓ Verificando especificaciones OE2...")
    with open(chargers_file) as f:
        chargers_data = json.load(f)
    num_chargers = len(chargers_data)
    num_sockets = num_chargers * 4
    logger.info(f"   ✓ Chargers: {num_chargers} chargers × 4 sockets = {num_sockets} outlets")

    with open(bess_config) as f:
        bess_data = json.load(f)
    capacity_mwh = bess_data.get("energy_capacity_kwh", 2000000) / 1000
    power_mw = bess_data.get("power_capacity_kw", 1200) / 1000
    logger.info(f"   ✓ BESS: {capacity_mwh:.1f} MWh / {power_mw:.2f} MW")

    # Construir dataset
    logger.info("\n✓ Construyendo dataset CityLearn...")
    try:
        build_citylearn_dataset(
            cfg=config,
            _raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )
    except Exception as e:
        logger.error(f"❌ Error construyendo dataset: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Verificar dataset construido
    logger.info("\n✓ Verificando dataset construido...")
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"

    if not dataset_dir.exists():
        logger.error(f"❌ Dataset directory no encontrado: {dataset_dir}")
        return 1

    # Contar charger files
    charger_files = list(dataset_dir.glob("charger_*.csv"))
    logger.info(f"   ✓ Charger files: {len(charger_files)} archivos")

    # Verificar schema.json
    schema_file = dataset_dir / "schema.json"
    if schema_file.exists():
        logger.info(f"   ✓ Schema: schema.json ({schema_file.stat().st_size:,} bytes)")
    else:
        logger.warning(f"   ⚠️  Schema no encontrado: {schema_file}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ DATASET CONSTRUIDO EXITOSAMENTE")
    logger.info("=" * 80)
    logger.info(f"\nUbicación: {dataset_dir}")
    logger.info(f"   - {len(charger_files)} charger timeseries (8,760 timesteps c/u)")
    logger.info(f"   - {num_sockets} sockets controllables (128 chargers, 129 acciones)")
    logger.info(f"   - Listo para baseline y entrenamiento\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
