#!/usr/bin/env python3
"""
PPO + A2C Training Orchestrator - DEBUG VERSION
Con validacion de schema, metricas y parametros visibles
"""

import os
import sys
import subprocess
from pathlib import Path

def run_ppo_training():
    """Ejecuta entrenamiento PPO con debug detallado"""
    print("\n" + "="*100)
    print(">> INICIANDO ENTRENAMIENTO PPO (DEBUG - CON METRICAS Y VALIDACION)")
    print("="*100 + "\n")
    
    script_path = Path(__file__).parent / "scripts" / "train_ppo_debug.py"
    cmd = [sys.executable, str(script_path)]
    
    result = subprocess.run(cmd)
    return result.returncode == 0

def run_a2c_training():
    """Ejecuta entrenamiento A2C con debug detallado"""
    print("\n" + "="*100)
    print(">> INICIANDO ENTRENAMIENTO A2C (DEBUG - CON METRICAS Y VALIDACION)")
    print("="*100 + "\n")
    
    script_path = Path(__file__).parent / "scripts" / "train_a2c_debug.py"
    
    if not script_path.exists():
        print("ERROR: train_a2c_debug.py no existe")
        return False
    
    cmd = [sys.executable, str(script_path)]
    result = subprocess.run(cmd)
    return result.returncode == 0

def main():
    """Main orchestrator"""
    print("\n" + "="*100)
    print("ENTRENAMIENTO MULTI-AGENTE PPO + A2C (DEBUG VERSION)")
    print("="*100)
    print("\nCONFIGURACION:")
    print("  - Agentes: 17 edificios/agentes")
    print("  - Acciones: 26 dimensiones (flattened)")
    print("  - Observaciones: 534 dimensiones (flattened)")
    print("  - Timesteps por agente: 17,520")
    print("  - Checkpoints: cada 2,048 timesteps")
    print("  - Acumulable: reset_num_timesteps=False (para agregar mas episodios)")
    print("\nLOG FILES:")
    print("  - analyses/logs/ppo_debug.log")
    print("  - analyses/logs/a2c_debug.log")
    print("\n")
    
    # Run PPO
    ppo_success = run_ppo_training()
    if not ppo_success:
        print("\nERROR: PPO training fallo")
        sys.exit(1)
    
    print("\n[OK] PPO entrenamiento completado")
    print("    Checkpoints guardados en: analyses/oe3/training/checkpoints/ppo/")
    
    # Run A2C immediately without waiting
    a2c_success = run_a2c_training()
    if not a2c_success:
        print("\nERROR: A2C training fallo")
        sys.exit(1)
    
    print("\n[OK] A2C entrenamiento completado")
    print("    Checkpoints guardados en: analyses/oe3/training/checkpoints/a2c/")
    
    print("\n" + "="*100)
    print("[OK] TODOS LOS ENTRENAMIENTOS COMPLETADOS EXITOSAMENTE")
    print("="*100)
    print("\nRESUMEN DE ARCHIVOS:")
    print("  * PPO checkpoints: analyses/oe3/training/checkpoints/ppo/")
    print("  * A2C checkpoints: analyses/oe3/training/checkpoints/a2c/")
    print("  * Modelos finales: [*_final.zip]")
    print("\nPara continuar entrenamiento despues, solo relanza este script")
    print("(Detectara automaticamente los checkpoints previos)\n")

if __name__ == "__main__":
    main()
