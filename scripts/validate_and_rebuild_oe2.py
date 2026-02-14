#!/usr/bin/env python3
"""🔄 Reconstrucción Completa de Datasets OE2 v5.2 sin Duplicidad.

Ejecuta validación y reconstrucción limpia de:
- Solar (4,050 kWp)
- BESS (1,700 kWh)
- Chargers (38 sockets / 19 chargers)
- Mall Demand (100 kW nominal)

Evita duplicidad limpiando versiones antiguas en data/interim/oe2/ si existen.

Uso:
    python scripts/validate_and_rebuild_oe2.py [--cleanup]
    
Opciones:
    --cleanup    Elimina archivos duplicados en data/interim/oe2/ después de validar
    --no-cleanup No limpia duplicados (default)
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dimensionamiento.oe2.disenocargadoresev.data_loader import (
    rebuild_oe2_datasets_complete,
    OE2ValidationError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Ejecutar reconstrucción completa de datasets OE2."""
    
    # Parse arguments
    cleanup = "--cleanup" in sys.argv
    
    logger.info("\n" + "="*80)
    logger.info(" 🚀 RECONSTRUCCIÓN COMPLETA DE DATASETS OE2 v5.2")
    logger.info("="*80)
    logger.info(f"\nOpciones:")
    logger.info(f"  • Limpieza de duplicados: {'✓ ACTIVADA' if cleanup else '✗ DESACTIVADA'}")
    logger.info(f"  • Proyecto: pvbesscar (Iquitos, Peru)")
    logger.info(f"  • Versión: OE2 v5.2 (Infrastructure Dimensioning)")
    logger.info(f"  • Target: CityLearn v2 RL Environment")
    logger.info("")
    
    try:
        # Ejecutar reconstrucción
        result = rebuild_oe2_datasets_complete(cleanup_interim=cleanup)
        
        # Reportar resultados
        if result["is_valid"]:
            logger.info("\n✅ ESTADO FINAL: EXITOSO\n")
            logger.info("📋 DATASETS VALIDADOS:")
            logger.info(f"  ✓ Solar: {result['solar']['capacity_kwp']} kWp, {result['solar']['mean_kw']:.1f} kW promedio")
            logger.info(f"  ✓ BESS: {result['bess']['capacity_kwh']} kWh, POW={result['bess']['power_kw']} kW")
            logger.info(f"  ✓ Chargers: {result['chargers']['total_units']} cargadores × 2 sockets = {result['chargers']['total_sockets']} tomas")
            logger.info(f"        - Motos: {result['chargers']['motos']} cargadores")
            logger.info(f"        - Mototaxis: {result['chargers']['mototaxis']} cargadores")
            logger.info(f"  ✓ Mall Demand: {result['mall_demand']['mean_kw']:.1f} kW promedio")
            logger.info(f"  ✓ Timesteps: {result['solar']['timesteps']} horas (1 año)")
            
            if result.get("cleanup"):
                logger.info(f"\n🧹 LIMPIEZA COMPLETADA:")
                for dataset, cleanup_res in result["cleanup"].items():
                    if cleanup_res.get("interim_removed"):
                        logger.info(f"  ✓ {dataset}: Eliminado {len(cleanup_res['interim_removed'])} archivo(s) duplicado(s)")
            
            logger.info(f"\n🎯 LISTO PARA ENTRENAR: SAC | PPO | A2C")
            logger.info("="*80 + "\n")
            return 0
            
        else:
            logger.error("\n❌ ESTADO FINAL: FALLIDO\n")
            logger.error("⚠️  ERRORES ENCONTRADOS:")
            for error in result["errors"]:
                logger.error(f"  ✗ {error}")
            logger.error("\n" + "="*80 + "\n")
            return 1
            
    except OE2ValidationError as e:
        logger.error(f"\n❌ ERROR DE VALIDACIÓN OE2:\n  {e}\n")
        logger.error("="*80 + "\n")
        return 1
    except Exception as e:
        logger.error(f"\n❌ ERROR INESPERADO:\n  {type(e).__name__}: {e}\n")
        logger.error("="*80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
