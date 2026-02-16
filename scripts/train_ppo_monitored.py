#!/usr/bin/env python
"""
Script de entrenamiento PPO con monitoreo en vivo - LIMPIO 2026-02-14
Lanza el entrenamiento PPO multiobjetivo existente con monitoreo
"""
from __future__ import annotations

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('train_ppo_monitored.log')
    ]
)
logger = logging.getLogger(__name__)


def monitor_training():
    """Lanza y monitorea el entrenamiento PPO"""
    
    logger.info(f"\n{'='*70}")
    logger.info(f"ENTRENAMIENTO PPO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Limpieza completa: checkpoints y outputs limpios")
    logger.info(f"Dataset OE3: 8,760 timesteps (1 ano horario)")
    logger.info(f"{'='*70}\n")
    
    # Script a ejecutar
    training_script = Path("scripts/train/train_ppo_multiobjetivo.py")
    
    if not training_script.exists():
        logger.error(f"[X] Script de entrenamiento no encontrado: {training_script}")
        return False
    
    logger.info(f"🚀 Lanzando: {training_script}")
    logger.info(f"{'='*70}\n")
    
    try:
        # Lanzar proceso
        process = subprocess.Popen(
            [sys.executable, str(training_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffering
        )
        
        start_time = time.time()
        line_count = 0
        
        # Monitorear en vivo
        for line in process.stdout:
            line = line.rstrip('\n')
            if line:
                logger.info(line)
                line_count += 1
                
                # Mostrar resumen cada 100 lineas
                if line_count % 100 == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"\n   [Tiempo: {elapsed:.0f}s | {line_count} lineas]\n")
        
        # Esperar a que termine
        return_code = process.wait()
        elapsed = time.time() - start_time
        
        logger.info(f"\n{'='*70}")
        if return_code == 0:
            logger.info(f"[OK] ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
            logger.info(f"   Tiempo total: {elapsed:.1f}s ({elapsed/60:.1f} minutos)")
            logger.info(f"   Total lineas procesadas: {line_count}")
        else:
            logger.error(f"[X] Entrenamiento fallo (codigo: {return_code})")
        logger.info(f"{'='*70}\n")
        
        return return_code == 0
            
    except KeyboardInterrupt:
        logger.warning("\n[!] Entrenamiento interrumpido por usuario")
        try:
            process.terminate()
        except:
            pass
        return False
    except Exception as e:
        logger.error(f"[X] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = monitor_training()
    sys.exit(0 if success else 1)
