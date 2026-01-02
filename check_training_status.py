#!/usr/bin/env python3
"""Verificación en tiempo real del estado del entrenamiento."""
import json
import logging
from pathlib import Path
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_training_status():
    """Verifica estado actual del entrenamiento."""
    
    out_dir = Path("outputs/oe3/simulations")
    training_dir = Path("analyses/oe3/training")
    
    logger.info("\n" + "=" * 80)
    logger.info("ESTADO DEL ENTRENAMIENTO")
    logger.info("=" * 80)
    
    # Verificar archivos de resultado
    logger.info("\nArchivos de resultado generados:")
    for result_file in sorted(out_dir.glob("result_*.json")):
        try:
            data = json.loads(result_file.read_text())
            steps = data.get("total_steps", "?")
            reward = data.get("cumulative_reward", "?")
            logger.info(f"  ✓ {result_file.name}: {steps} steps, reward={reward}")
        except Exception as e:
            logger.warning(f"  ✗ {result_file.name}: {e}")
    
    # Verificar CSV de métricas
    logger.info("\nArchivos de métricas CSV:")
    for metrics_file in sorted(training_dir.glob("*_training_metrics.csv")):
        lines = metrics_file.read_text().strip().split("\n")
        logger.info(f"  {metrics_file.name}: {len(lines)-1} registros (1 header)")
    
    # Verificar checkpoints (CRÍTICO)
    logger.info("\nArchivos de checkpoint (.zip):")
    checkpoint_base = training_dir / "checkpoints"
    if checkpoint_base.exists():
        zips = list(checkpoint_base.rglob("*.zip"))
        if zips:
            logger.info(f"  ✓ {len(zips)} checkpoints encontrados:")
            for z in sorted(zips)[:10]:  # Mostrar primeros 10
                size_kb = z.stat().st_size / 1024
                logger.info(f"    - {z.relative_to(checkpoint_base)}: {size_kb:.1f} KB")
            if len(zips) > 10:
                logger.info(f"    ... y {len(zips)-10} más")
        else:
            logger.warning(f"  ✗ Directorio existe pero SIN checkpoints: {checkpoint_base}")
    else:
        logger.warning(f"  ✗ Directorio de checkpoints NO existe: {checkpoint_base}")
    
    # Verificar si training está en progreso
    logger.info("\nProcesos Python activos:")
    import subprocess
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"], 
                          capture_output=True, text=True)
    if "python.exe" in result.stdout:
        logger.info("  ✓ Training aún en ejecución")
    else:
        logger.info("  ✓ Training completado (no hay procesos Python)")
    
    logger.info("\n" + "=" * 80)

if __name__ == "__main__":
    check_training_status()
