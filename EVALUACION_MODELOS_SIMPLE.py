#!/usr/bin/env python
"""
EVALUACIÓN SIMPLE DE MODELOS - PPO vs A2C vs SAC
Verifica que los modelos se cargan correctamente
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from stable_baselines3 import PPO, A2C, SAC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("\n" + "="*80)
    logger.info("VERIFICACIÓN DE MODELOS ENTRENADOS".center(80))
    logger.info("="*80 + "\n")
    
    models_to_check = [
        ("PPO", "analyses/oe3/training/checkpoints/ppo_gpu/ppo_final.zip", PPO),
        ("A2C", "analyses/oe3/training/checkpoints/a2c_gpu/a2c_final.zip", A2C),
        ("SAC", "analyses/oe3/training/checkpoints/sac/sac_final.zip", SAC),
    ]
    
    results = {}
    
    for agent_name, model_path, ModelClass in models_to_check:
        logger.info(f"\n[*] Verificando {agent_name}")
        logger.info(f"    Ruta: {model_path}")
        
        path = Path(model_path)
        
        if not path.exists():
            logger.error(f"    ❌ Archivo NO encontrado")
            results[agent_name] = "NO_ENCONTRADO"
            continue
        
        file_size = path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"    Tamaño: {file_size:.2f} MB")
        
        try:
            logger.info(f"    Intentando cargar...")
            model = ModelClass.load(str(path))
            logger.info(f"    ✓ Cargado exitosamente")
            
            # Información del modelo
            logger.info(f"    - Policy type: {type(model.policy).__name__}")
            logger.info(f"    - Timesteps: {model.num_timesteps:,}")
            
            results[agent_name] = "OK"
            
        except Exception as e:
            logger.error(f"    ❌ Error al cargar: {type(e).__name__}: {e}")
            results[agent_name] = f"ERROR: {type(e).__name__}"
    
    # Resumen
    logger.info("\n" + "="*80)
    logger.info("RESUMEN".center(80))
    logger.info("="*80)
    
    for agent, status in results.items():
        emoji = "✓" if status == "OK" else "❌"
        logger.info(f"{emoji} {agent:6} : {status}")
    
    logger.info("\n" + "="*80)

if __name__ == "__main__":
    main()
