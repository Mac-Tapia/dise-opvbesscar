#!/usr/bin/env python3
"""
Script para monitorear PPO y lanzar automáticamente A2C después de completar.
Ejecuta: python scripts/auto_ppo_then_a2c.py
"""

import subprocess
import sys
import time
from pathlib import Path

def get_latest_checkpoint_step(agent: str) -> int:
    """Obtiene el número del paso del checkpoint más reciente."""
    checkpoint_dir = Path(f"analyses/oe3/training/checkpoints/{agent}")
    if not checkpoint_dir.exists():
        return 0
    
    checkpoints = list(checkpoint_dir.glob(f"{agent}_step_*.zip"))
    if not checkpoints:
        return 0
    
    steps = []
    for ckpt in checkpoints:
        try:
            step = int(ckpt.stem.split("_")[-1])
            steps.append(step)
        except (IndexError, ValueError):
            continue
    
    return max(steps) if steps else 0

def is_training_complete(agent: str, target_steps: int = 87600) -> bool:
    """Verifica si el entrenamiento está completo."""
    step = get_latest_checkpoint_step(agent)
    return step >= (target_steps - 1000)  # Margen de 1000 pasos

def wait_for_ppo():
    """Espera a que PPO complete."""
    print("\n" + "="*60)
    print("⏳ ESPERANDO A QUE PPO COMPLETE (87,600 pasos)")
    print("="*60)
    
    prev_step = 0
    no_progress_count = 0
    
    while True:
        current_step = get_latest_checkpoint_step("ppo")
        
        if current_step > prev_step:
            print(f"📊 PPO Paso: {current_step} / 87,600 ({100*current_step/87600:.1f}%)")
            no_progress_count = 0
            prev_step = current_step
        else:
            no_progress_count += 1
            if no_progress_count > 1:
                print(f"⏳ Sin cambios detectados... Esperando...")
            
            if no_progress_count > 180:  # 30 min sin cambios
                print("⚠️ PPO parece estancado. Verifique manualmente.")
                return False
        
        if is_training_complete("ppo"):
            print("\n✅ PPO HA COMPLETADO 87,600 PASOS")
            return True
        
        time.sleep(10)  # Check every 10 seconds

def launch_a2c():
    """Lanza A2C training."""
    print("\n" + "="*60)
    print("🚀 LANZANDO A2C TRAINING")
    print("="*60)
    
    cmd = [sys.executable, "-m", "scripts.continue_a2c_training", "--config", "configs/default.yaml"]
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ A2C COMPLETADO")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ A2C Falló: {e}")
        sys.exit(1)

def main():
    print("\n" + "="*70)
    print("🔄 PIPELINE AUTOMÁTICO: PPO → A2C")
    print("="*70)
    
    # Esperar a PPO
    if not wait_for_ppo():
        sys.exit(1)
    
    # Pausa
    print("\n⏳ Pausa de 5 segundos antes de lanzar A2C...")
    time.sleep(5)
    
    # Lanzar A2C
    launch_a2c()
    
    print("\n" + "="*70)
    print("✅ PIPELINE COMPLETO: PPO Y A2C TERMINADOS")
    print("="*70)

if __name__ == "__main__":
    main()
