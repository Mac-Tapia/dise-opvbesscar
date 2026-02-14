"""Test script para validar que data_loader carga datasets reales correctamente."""

from __future__ import annotations

import logging
from pathlib import Path
from src.dimensionamiento.oe2.disenocargadoresev.data_loader import validate_oe2_complete

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Test principal: validar todos los datasets OE2 reales v5.2."""
    
    logger.info("═" * 80)
    logger.info("TEST: Validando datos OE2 REALES v5.2")
    logger.info("═" * 80)
    
    # Ejecutar validación completa (usa rutas por defecto)
    results = validate_oe2_complete()
    
    # Imprimir resumen
    logger.info("")
    logger.info("RESUMEN DE VALIDACIÓN:")
    logger.info("-" * 80)
    
    if results["is_valid"]:
        logger.info("✓ VALIDACIÓN EXITOSA - Todos los datos están disponibles y correctos")
        logger.info("")
        logger.info("Datasets cargados:")
        if results["solar"]:
            logger.info(f"  📊 Solar: {results['solar']['capacity_kwp']} kWp")
            logger.info(f"     - Timesteps: {results['solar']['timesteps']}")
            logger.info(f"     - Mean: {results['solar']['mean_kw']:.1f} kW")
            logger.info(f"     - Max: {results['solar']['max_kw']:.1f} kW")
        
        if results["bess"]:
            logger.info(f"  🔋 BESS: {results['bess']['capacity_kwh']} kWh")
            logger.info(f"     - Power: {results['bess']['power_kw']} kW")
            logger.info(f"     - Efficiency: {results['bess']['efficiency']*100:.0f}%")
            logger.info(f"     - Timesteps: {results['bess']['timesteps']}")
        
        if results["chargers"]:
            logger.info(f"  🔌 Chargers: {results['chargers']['total_units']} units")
            logger.info(f"     - Sockets: {results['chargers']['total_sockets']}")
            logger.info(f"     - Motos: {results['chargers']['motos']}")
            logger.info(f"     - Mototaxis: {results['chargers']['mototaxis']}")
            logger.info(f"     - Timesteps: {results['chargers']['timesteps']}")
        
        if results["mall_demand"]:
            logger.info(f"  🏬 Mall Demand: ")
            logger.info(f"     - Timesteps: {results['mall_demand']['timesteps']}")
            logger.info(f"     - Mean: {results['mall_demand']['mean_kw']:.1f} kW")
            logger.info(f"     - Max: {results['mall_demand']['max_kw']:.1f} kW")
        
        logger.info("")
        logger.info("✓ Todos los datasets listos para OE3 (CityLearn v2) training")
        return 0
    else:
        logger.error("✗ VALIDACIÓN FALLIDA")
        logger.error("")
        logger.error("Errores encontrados:")
        for err in results["errors"]:
            logger.error(f"  ✗ {err}")
        return 1

if __name__ == "__main__":
    exit(main())
