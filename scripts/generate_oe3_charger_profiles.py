#!/usr/bin/env python
"""
SCRIPT: Generar 128 perfiles anuales para CityLearn v2 (OE3 FIJO).

Uso:
    python scripts/generate_oe3_charger_profiles.py

Output:
    - data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv (matriz 8760×128)
    - data/interim/oe2/chargers/charger_simulation_001.csv to 128.csv
    - data/interim/oe2/chargers/charger_generation_log.json

Configuración OE3 FIJA:
    - 32 cargadores físicos (28 motos @ 2kW + 4 mototaxis @ 3kW)
    - 128 tomas (4 por cargador, control individual)
    - Modo 3 (AC trifásico)
    - Sesión: 30 minutos
    - Horario: 09:00-22:00 (13 horas/día)
    - Pico: 18:00-22:00 (4 horas/día)
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar desde oe2
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.iquitos_citylearn.oe2.chargers import generate_oe3_annual_charger_profiles

def main():
    """Ejecuta generación de 128 perfiles anuales."""
    logger.info("")
    logger.info("🔋 GENERADOR OE3: 128 PERFILES ANUALES PARA CITYLEARN V2")
    logger.info("=" * 80)

    output_dir = Path("data/interim/oe2/chargers")

    try:
        # Generar 128 perfiles
        log_result = generate_oe3_annual_charger_profiles(
            output_dir=output_dir,
            year=2024,
            seed=42,
        )

        logger.info("")
        logger.info("✅ GENERACIÓN EXITOSA")
        logger.info("=" * 80)
        logger.info(f"📊 Statisticas:")
        logger.info(f"   • Energía anual: {log_result['statistics']['total_energy_kwh']:,.0f} kWh")
        logger.info(f"   • Energía por toma: {log_result['statistics']['energy_per_socket_kwh']:,.0f} kWh")
        logger.info(f"   • Potencia promedio: {log_result['statistics']['avg_power_kw']:.2f} kW")
        logger.info(f"   • Potencia máxima: {log_result['statistics']['max_power_kw']:.2f} kW")
        logger.info("")
        logger.info(f"📁 Output:")
        logger.info(f"   • Matriz anual: {output_dir}/chargers_hourly_profiles_annual.csv")
        logger.info(f"   • Archivos de tomas: {output_dir}/charger_simulation_001.csv to 128.csv")
        logger.info(f"   • Registro: {output_dir}/charger_generation_log.json")
        logger.info("")
        logger.info("PRÓXIMO PASO: Ejecutar dataset_builder.py para generar CityLearn schema")
        logger.info("")

        return 0

    except Exception as e:
        logger.error(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
