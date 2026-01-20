#!/usr/bin/env python
"""
ENTRENAMIENTO SECUENCIAL: PPO → A2C
Ejecuta PPO, luego A2C automáticamente
"""
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

def run_training(script_name, agent_name):
    """Ejecuta un script de entrenamiento y espera a que termine"""
    logger.info("="*100)
    logger.info(f"[{agent_name}] INICIANDO ENTRENAMIENTO")
    logger.info(f"Script: {script_name}")
    logger.info(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*100)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            cwd="d:\\diseñopvbesscar",
            check=True,
            capture_output=False
        )
        logger.info(f"\n✅ [{agent_name}] COMPLETADO EXITOSAMENTE")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"\n❌ [{agent_name}] ERROR: {e}")
        return False
    except Exception as e:
        logger.error(f"\n❌ [{agent_name}] ERROR INESPERADO: {e}")
        return False

def main():
    logger.info("\n")
    logger.info("╔" + "="*98 + "╗")
    logger.info("║" + " "*98 + "║")
    logger.info("║" + "ENTRENAMIENTO SECUENCIAL: PPO → A2C".center(98) + "║")
    logger.info("║" + "MALL IQUITOS - 128 TOMAS - 17,520 TIMESTEPS CADA UNO".center(98) + "║")
    logger.info("║" + " "*98 + "║")
    logger.info("╚" + "="*98 + "╝")
    logger.info("\n")
    
    start_time = datetime.now()
    
    # 1. ENTRENAR PPO
    logger.info("\n[PASO 1/2] Entrenando PPO...")
    ppo_success = run_training("scripts/train_ppo_gpu_fixed.py", "PPO")
    
    if not ppo_success:
        logger.error("PPO falló. Abortando...")
        sys.exit(1)
    
    logger.info("\n" + "-"*100)
    logger.info("PPO completado. Iniciando A2C...")
    logger.info("-"*100 + "\n")
    
    # 2. ENTRENAR A2C
    logger.info("\n[PASO 2/2] Entrenando A2C...")
    a2c_success = run_training("scripts/train_a2c_gpu_fixed.py", "A2C")
    
    if not a2c_success:
        logger.error("A2C falló. Pero PPO se completó exitosamente.")
        sys.exit(1)
    
    # Resumen
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds() / 60
    
    logger.info("\n")
    logger.info("╔" + "="*98 + "╗")
    logger.info("║" + " "*98 + "║")
    logger.info("║" + "✅ ENTRENAMIENTO SECUENCIAL COMPLETADO".center(98) + "║")
    logger.info("║" + f"Tiempo total: {total_time:.1f} minutos".center(98) + "║")
    logger.info("║" + " "*98 + "║")
    logger.info("║" + "Próximo: Ejecutar COMPARATIVA_TRES_AGENTES.py".center(98) + "║")
    logger.info("║" + " "*98 + "║")
    logger.info("╚" + "="*98 + "╝")
    logger.info("\n")

if __name__ == "__main__":
    main()
