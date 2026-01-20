#!/usr/bin/env python3
"""
PPO + A2C Training Only (Skip SAC and Baseline)
Lanza PPO y A2C secuencialmente sin interrupciones ni esperas
"""

import os
import sys
import subprocess
import platform
import numpy as np
from pathlib import Path

def run_ppo_training():
    """Ejecuta entrenamiento PPO acumulable con checkpoints"""
    print("\n" + "="*80)
    print(">> INICIANDO ENTRENAMIENTO PPO (ACUMULABLE)")
    print("="*80 + "\n")
    
    script_path = Path(__file__).parent / "scripts" / "train_ppo_acumulable.py"
    cmd = [sys.executable, str(script_path)]
    
    result = subprocess.run(cmd)
    return result.returncode == 0

def run_a2c_training():
    """Ejecuta entrenamiento A2C acumulable con checkpoints"""
    print("\n" + "="*80)
    print(">> INICIANDO ENTRENAMIENTO A2C (ACUMULABLE)")
    print("="*80 + "\n")
    
    script_path = Path(__file__).parent / "scripts" / "train_a2c_acumulable.py"
    
    if not script_path.exists():
        print("W Script A2C no encontrado")
        print("X Error: train_a2c_acumulable.py debe existir")
        return False
    
    cmd = [sys.executable, str(script_path)]
    result = subprocess.run(cmd)
    return result.returncode == 0

def create_a2c_script(output_path):
    """Crea script A2C basado en PPO - YA NO NECESARIO"""
    pass

def main():
    """Main orchestrator"""
    print("\n" + "="*80)
    print("ENTRENAMIENTO PPO + A2C (ACUMULABLE - CON CHECKPOINTS)")
    print("="*80)
    print("\nLos modelos guardaran checkpoints cada 2,048 timesteps")
    print("Pueden continuar desde checkpoint si se interrumpen")
    print("reset_num_timesteps=False para acumular episodios\n")
    
    # Run PPO
    ppo_success = run_ppo_training()
    if not ppo_success:
        print("\nX PPO training fallo")
        sys.exit(1)
    
    print("\n[OK] PPO entrenamiento completado")
    print("V Checkpoints guardados en analyses/oe3/training/checkpoints/ppo/")
    
    # Run A2C immediately without waiting
    a2c_success = run_a2c_training()
    if not a2c_success:
        print("\nX A2C training fallo")
        sys.exit(1)
    
    print("\n[OK] A2C entrenamiento completado")
    print("V Checkpoints guardados en analyses/oe3/training/checkpoints/a2c/")
    
    print("\n" + "="*80)
    print("[OK] TODOS LOS ENTRENAMIENTOS COMPLETADOS EXITOSAMENTE")
    print("="*80)
    print("\nResumen de archivos guardados:")
    print("  * PPO checkpoints: analyses/oe3/training/checkpoints/ppo/")
    print("  * A2C checkpoints: analyses/oe3/training/checkpoints/a2c/")
    print("  * Modelos finales: [*_final.zip]")
    print("\nPara continuar entrenamiento despues, solo relanza este script\n")

if __name__ == "__main__":
    main()
