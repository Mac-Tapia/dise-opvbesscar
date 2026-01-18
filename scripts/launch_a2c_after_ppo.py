#!/usr/bin/env python3
"""
Script para lanzar A2C después de que PPO completar sus 5 episodios.
Monitorea el progreso de PPO y lanza A2C automáticamente cuando termina.

Uso: python scripts/launch_a2c_after_ppo.py
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def get_latest_checkpoint(checkpoint_dir: Path) -> dict | None:
    """Obtiene el checkpoint más reciente de PPO."""
    if not checkpoint_dir.exists():
        return None
    
    checkpoints = sorted(checkpoint_dir.glob("ppo_step_*.zip"), key=lambda x: int(x.stem.split("_")[2]))
    if checkpoints:
        return {"path": checkpoints[-1], "step": int(checkpoints[-1].stem.split("_")[2])}
    
    return None

def is_ppo_finished(checkpoint_dir: Path, target_timesteps: int = 43800) -> bool:
    """
    Verifica si PPO ha completado entrenamiento.
    
    PPO: 5 episodios = 43,800 timesteps
    Checkpoint se guarda cada 1,000 pasos
    → Si checkpoint_step >= 43,000 → probable que haya terminado
    """
    latest = get_latest_checkpoint(checkpoint_dir)
    if not latest:
        return False
    
    step = latest["step"]
    logger.info(f"📊 PPO Checkpoint más reciente: paso {step}/{target_timesteps}")
    
    return step >= (target_timesteps - 800)  # Margen de 800 pasos

def wait_for_ppo_completion(checkpoint_dir: Path, config: str, poll_interval: int = 30) -> None:
    """
    Espera a que PPO complete entrenamiento.
    
    Poll cada N segundos para revisar progreso.
    """
    logger.info("⏳ Esperando que PPO complete 5 episodios (43,800 timesteps)...")
    
    prev_step = 0
    stalled_count = 0
    max_stalls = 20  # Si no avanza por 20 polls (~10 min), asumir que algo falló
    
    while True:
        latest = get_latest_checkpoint(checkpoint_dir)
        
        if not latest:
            logger.warning("⚠️ No hay checkpoints de PPO aún. Esperando...")
            time.sleep(poll_interval)
            continue
        
        current_step = latest["step"]
        
        if current_step == prev_step:
            stalled_count += 1
            logger.warning(f"⚠️ PPO no ha avanzado ({stalled_count}/{max_stalls})")
            
            if stalled_count >= max_stalls:
                logger.error("❌ PPO parece estar estancado. Verifique manualmente.")
                sys.exit(1)
        else:
            stalled_count = 0
        
        prev_step = current_step
        
        if is_ppo_finished(checkpoint_dir):
            logger.info("✅ PPO HA COMPLETADO 5 EPISODIOS!")
            break
        
        logger.info(f"📈 Progreso: {current_step} / 43,800 pasos")
        time.sleep(poll_interval)

def launch_a2c_training(config: str) -> None:
    """Lanza entrenamiento de A2C."""
    logger.info("\n" + "="*60)
    logger.info("🚀 INICIANDO A2C TRAINING")
    logger.info("="*60)
    
    cmd = [sys.executable, "-m", "scripts.continue_a2c_training", "--config", config]
    logger.info(f"Comando: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        logger.info("✅ A2C COMPLETADO")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ A2C falló con código: {e.returncode}")
        sys.exit(e.returncode)

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Lanza A2C después de que PPO complete sus 5 episodios"
    )
    ap.add_argument("--config", default="configs/default.yaml", help="Path a config YAML")
    ap.add_argument("--poll-interval", type=int, default=30, help="Intervalo de polling en segundos")
    ap.add_argument("--checkpoint-dir", default="analyses/oe3/training/checkpoints/ppo")
    args = ap.parse_args()
    
    checkpoint_dir = Path(args.checkpoint_dir)
    
    logger.info(f"Monitoreando checkpoints en: {checkpoint_dir}")
    logger.info(f"Poll interval: {args.poll_interval}s")
    
    # Esperar a que PPO termine
    wait_for_ppo_completion(checkpoint_dir, args.config, args.poll_interval)
    
    # Lanzar A2C
    time.sleep(5)  # Pequeña pausa
    launch_a2c_training(args.config)

if __name__ == "__main__":
    main()
